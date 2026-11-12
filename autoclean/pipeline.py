"""Orchestrates the full AutoClean pipeline: load -> profile -> detect -> LLM
plan -> validate -> execute -> report.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from autoclean.loader import load_data, save_data
from autoclean.placeholders import normalize_placeholders
from autoclean.profiler import profile_dataframe
from autoclean.row_analyzer import analyze_rows
from autoclean.issue_detector import detect_issues
from autoclean.fallback import build_fallback_plan
from autoclean.llm_engine import get_cleaning_plan, repair_rejected_actions
from autoclean.postcheck import check_cleaned
import config
from autoclean.validator import validate_plan
from autoclean.executor import execute_plan
from autoclean.report import generate_report


@dataclass
class PipelineResult:
    original_df: pd.DataFrame
    cleaned_df: pd.DataFrame
    report_markdown: str
    execution_log: list
    rejected_actions: list
    llm_error: str | None
    row_analysis: dict | None = None
    post_check: dict | None = None  # what is still wrong after cleaning (see postcheck.py)
    plan_source: str = "llm"  # "llm", "llm+repair" or "fallback"
    placeholder_counts: dict | None = None  # {column: n} placeholder strings converted to missing
    removed_rows: pd.DataFrame | None = None  # rows dropped by row-wise actions, with the action that removed them


def run_pipeline(input_path: str) -> PipelineResult:
    """Run the full cleaning pipeline on a file and return the result in-memory."""
    # 1. Load
    original_df = load_data(input_path)
    # placeholders like "?" become real NaN so profiling, row analysis and cleaning see them as missing
    df, placeholder_counts = normalize_placeholders(original_df)

    # 2. Profile
    dataset_profile = profile_dataframe(df)

    # 2b. Row-wise analysis (counts only; no raw rows leave this step)
    row_analysis = analyze_rows(df)

    # 3. Detect issues (rule-based, pre-LLM)
    annotated = detect_issues(df, dataset_profile)
    annotated_profile = {
        "row_count": dataset_profile["row_count"],
        "column_count": dataset_profile["column_count"],
        "duplicate_row_count": dataset_profile["duplicate_row_count"],
        "dataset_issues": annotated["dataset_issues"],
        "row_analysis": row_analysis,
        "columns": annotated["columns"],
    }
    if not config.SEND_SAMPLE_VALUES:
        # privacy mode: the LLM sees stats and issue tags only, never real cell values
        annotated_profile["columns"] = [
            {k: v for k, v in c.items() if k != "sample_values"} for c in annotated_profile["columns"]
        ]

    # 4. LLM decision engine
    raw_plan = get_cleaning_plan(annotated_profile)
    llm_error = raw_plan.get("error") if isinstance(raw_plan, dict) else "LLM plan was not a JSON object"

    # 5. Validate plan
    known_columns = list(df.columns)
    validation_result = validate_plan(raw_plan, known_columns)
    plan_source = "llm"

    # 5b. Re-prompt once for corrected versions of rejected actions (architecture: never silently guess)
    if validation_result.rejected and not llm_error:
        repair = repair_rejected_actions(annotated_profile, validation_result.rejected)
        if repair.get("actions"):
            fixed = validate_plan(repair, known_columns)
            # Each repaired action replaces one outstanding rejection of the same action type
            # (the column name may legitimately have changed, e.g. a corrected typo).
            still_rejected = list(validation_result.rejected)
            for new in fixed.valid_actions:
                for i, r in enumerate(still_rejected):
                    raw = r.get("raw")
                    if isinstance(raw, dict) and raw.get("action") == new.action:
                        del still_rejected[i]
                        break
            validation_result.valid_actions.extend(fixed.valid_actions)
            validation_result.rejected = still_rejected + fixed.rejected
            if fixed.valid_actions:
                plan_source = "llm+repair"

    # 5c. LLM unavailable/failed and nothing usable came back: safe rule-based plan
    if config.FALLBACK_ON_LLM_FAILURE and llm_error and not validation_result.valid_actions:
        validation_result = validate_plan(build_fallback_plan(annotated_profile), known_columns)
        plan_source = "fallback"

    # 6. Execute
    cleaned_df, execution_log = execute_plan(df, validation_result.valid_actions)

    removed_rows = _collect_removed_rows(original_df, execution_log)
    post_check = check_cleaned(cleaned_df)

    # 7. Report
    report_markdown = generate_report(
        original_df=original_df,
        cleaned_df=cleaned_df,
        execution_log=execution_log,
        rejected_actions=validation_result.rejected,
        llm_error=llm_error,
        row_analysis=row_analysis,
        removed_rows=removed_rows,
        placeholder_counts=placeholder_counts,
        post_check=post_check,
        plan_source=plan_source,
    )

    return PipelineResult(
        original_df=original_df,
        cleaned_df=cleaned_df,
        report_markdown=report_markdown,
        execution_log=execution_log,
        rejected_actions=validation_result.rejected,
        llm_error=llm_error,
        row_analysis=row_analysis,
        removed_rows=removed_rows,
        placeholder_counts=placeholder_counts,
        post_check=post_check,
        plan_source=plan_source,
    )


def _collect_removed_rows(original_df: pd.DataFrame, execution_log: list) -> pd.DataFrame:
    """Original rows removed by row-wise actions, tagged with the action that removed them."""
    parts = []
    for entry in execution_log:
        idx = entry.get("detail", {}).get("_removed_index")
        if entry["status"] == "applied" and idx:
            part = original_df.loc[idx].copy()
            part.insert(0, "removed_by", entry["action"])
            parts.append(part)
    if not parts:
        return original_df.iloc[0:0].assign(removed_by=pd.Series(dtype="object"))
    return pd.concat(parts)


def run_and_save(
    input_path: str, output_path: str, report_path: str, removed_rows_path: str | None = None
) -> PipelineResult:
    result = run_pipeline(input_path)
    save_data(result.cleaned_df, output_path)
    if removed_rows_path and result.removed_rows is not None and not result.removed_rows.empty:
        result.removed_rows.to_csv(removed_rows_path, index_label="original_row_label")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(result.report_markdown)
    return result
