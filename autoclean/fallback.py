"""Deterministic, conservative cleaning plan used when the LLM is unavailable or fails.

It only applies low-risk fixes derived from the rule-based issue tags: it never drops
columns, never clips outliers, never drops sparse/outlier rows and only imputes columns
with few missing values. Every action is labelled so the report shows it was rule-based.
"""
from __future__ import annotations

MAX_IMPUTE_MISSING_PCT = 20.0
_TAG = " (rule-based fallback)"


def build_fallback_plan(annotated_profile: dict) -> dict:
    actions: list[dict] = []
    row = annotated_profile.get("row_analysis") or {}
    empty_rows = row.get("fully_empty_rows", 0)

    def add(column: str, action: str, reason: str, **params):
        actions.append({"column": column, "action": action, "reason": reason + _TAG, **params})

    if row.get("fully_empty_rows"):
        add("*", "drop_empty_rows", f"{row['fully_empty_rows']} fully blank rows")
    if row.get("exact_duplicate_rows"):
        add("*", "drop_duplicates", f"{row['exact_duplicate_rows']} exact duplicate rows")

    for col in annotated_profile.get("columns", []):
        name, issues = col["column"], col.get("issues_detected", [])
        numeric_after = col.get("numeric_stats") is not None
        # Fully blank rows are dropped first, so they must not count towards a column's missing %.
        remaining_rows = max(annotated_profile.get("row_count", 0) - empty_rows, 0)
        missing = max(col.get("missing_count", 0) - empty_rows, 0)
        missing_pct = round(missing / remaining_rows * 100, 2) if remaining_rows else 0.0
        missing_ok = 0 < missing_pct <= MAX_IMPUTE_MISSING_PCT

        if "leading_trailing_whitespace" in issues:
            add(name, "strip_whitespace", "leading/trailing whitespace")
        if "inconsistent_casing" in issues:
            add(name, "normalize_casing", "same values differ only by letter case", casing="auto")
        if "numeric_values_with_units" in issues:
            add(name, "extract_number", "numbers stored with units as text")
            numeric_after = True
        elif "numeric_stored_as_text" in issues or (
            "mixed_types_numeric_and_text" in issues and col.get("looks_numeric_pct", 0) >= 90
        ):
            add(name, "fix_dtype", "mostly numeric values stored as text", target_dtype="float")
            numeric_after = True
        if "inconsistent_date_format" in issues:
            add(name, "standardize_date_format", "mixed date formats", target_format="YYYY-MM-DD")
            numeric_after = False

        if missing_ok:
            if numeric_after:
                add(name, "impute_median", f"{missing_pct}% missing numeric values")
            elif "inconsistent_date_format" not in issues:
                add(name, "impute_mode", f"{missing_pct}% missing categorical values")
    return {"actions": actions}
