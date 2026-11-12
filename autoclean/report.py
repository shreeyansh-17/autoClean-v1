"""Generates a human-readable markdown report of a cleaning run."""
from __future__ import annotations

from datetime import datetime

import pandas as pd


def _row_analysis_section(ra: dict, removed_rows: pd.DataFrame | None) -> list[str]:
    out = ["\n## Row-wise Analysis (before cleaning)"]
    out.append(f"- Rows analyzed: {ra['rows_analyzed']} (across {ra['columns_considered']} content columns)")
    if ra["index_like_columns_ignored"]:
        names = ", ".join(f"`{c}`" for c in ra["index_like_columns_ignored"])
        out.append(f"- Row-counter columns ignored when comparing rows: {names}")
    out.append(f"- Fully empty rows: {ra['fully_empty_rows']}")
    out.append(f"- Sparse rows (>50% blank): {ra['sparse_rows_over_50pct_blank']}")
    out.append(f"- Non-empty rows with at least one blank cell: {ra['non_empty_rows_with_any_blank']}")
    out.append(f"- Exact duplicate rows: {ra['exact_duplicate_rows']}")
    out.append(f"- Near-duplicate rows (case/whitespace/number-format, incl. exact): {ra['near_duplicate_rows_incl_exact']}")
    hist = ra["rows_by_extreme_outlier_column_count"]
    if hist:
        out.append("- Rows with extreme (3×IQR) values: " + ", ".join(f"{n} col(s): {c} rows" for n, c in hist.items()))
    else:
        out.append("- Rows with extreme (3×IQR) values: none")

    if removed_rows is not None and not removed_rows.empty:
        out.append("\n### Rows removed")
        counts = removed_rows["removed_by"].value_counts()
        for action, n in counts.items():
            out.append(f"- `{action}`: {n} rows")
        out.append(f"- Total: {len(removed_rows)} rows (full copies saved in the removed-rows CSV)")
    return out


def generate_report(
    original_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    execution_log: list[dict],
    rejected_actions: list[dict],
    llm_error: str | None,
    row_analysis: dict | None = None,
    removed_rows: pd.DataFrame | None = None,
    placeholder_counts: dict | None = None,
    post_check: dict | None = None,
    plan_source: str = "llm",
) -> str:
    lines = []
    lines.append("# AutoClean Report")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    lines.append("## Summary")
    lines.append(f"- Rows before: {len(original_df)}")
    lines.append(f"- Rows after: {len(cleaned_df)}")
    lines.append(f"- Columns before: {len(original_df.columns)}")
    lines.append(f"- Columns after: {len(cleaned_df.columns)}")
    if plan_source == "fallback":
        lines.append(f"- **LLM warning:** {llm_error}. A conservative rule-based plan was applied instead; "
                     "review the actions below.")
    elif llm_error:
        lines.append(f"- **LLM warning:** {llm_error} (partial plan; affected columns were not cleaned)")
    if plan_source == "llm+repair":
        lines.append("- Some LLM actions were rejected and re-requested once; repaired actions are included below.")

    if placeholder_counts:
        lines.append("\n## Placeholder Values Converted to Missing")
        lines.append("_Text such as `?` or `N/A` that stands for 'no value' was turned into a real missing value before cleaning._")
        for col, n in placeholder_counts.items():
            lines.append(f"- `{col}`: {n}")

    if row_analysis:
        lines.extend(_row_analysis_section(row_analysis, removed_rows))

    lines.append("\n## Actions Applied")
    applied = [e for e in execution_log if e["status"] == "applied"]
    if not applied:
        lines.append("_No actions were applied._")
    for e in applied:
        lines.append(f"\n### `{e['column']}` — {e['action']}")
        lines.append(f"- **Reason (LLM):** {e['reason']}")
        detail_str = ", ".join(f"{k}={v}" for k, v in e["detail"].items() if not k.startswith("_"))
        lines.append(f"- **Result:** {detail_str}")

    skipped_or_failed = [e for e in execution_log if e["status"] != "applied"]
    if skipped_or_failed:
        lines.append("\n## Actions Skipped or Failed")
        for e in skipped_or_failed:
            lines.append(
                f"- `{e['column']}` — {e['action']} — **{e['status']}**: {e['detail'].get('error', '')}"
            )

    if rejected_actions:
        lines.append("\n## Actions Rejected by Validator")
        lines.append("_These were proposed by the LLM but rejected before execution "
                      "(invalid schema, unknown column, or disallowed action)._")
        for r in rejected_actions:
            lines.append(f"- Raw: `{r['raw']}` — Error: {r['error']}")

    if post_check is not None:
        lines.append("\n## Post-clean Check")
        if post_check.get("note"):
            lines.append(f"- {post_check['note']}")
        elif post_check.get("clean"):
            lines.append("_No remaining issues detected by the rule-based checks._")
        else:
            lines.append("_Issues still detected after cleaning (not necessarily errors — review them):_")
            for k, v in post_check.get("row_issues", {}).items():
                lines.append(f"- Rows: {k.replace('_', ' ')} = {v}")
            for col, tags in post_check.get("column_issues", {}).items():
                lines.append(f"- `{col}`: {', '.join(tags)}")

    return "\n".join(lines)
