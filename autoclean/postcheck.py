"""Post-clean verification: re-run the profiler, issue detector and row analyzer on the
cleaned data and report what is still wrong, so a human can see the cleaning's limits."""
from __future__ import annotations

import pandas as pd

from autoclean.issue_detector import detect_issues
from autoclean.profiler import profile_dataframe
from autoclean.row_analyzer import analyze_rows


def check_cleaned(cleaned_df: pd.DataFrame) -> dict:
    """Returns {"row_issues": {...}, "column_issues": {col: [tags]}, "clean": bool}."""
    if cleaned_df.empty or len(cleaned_df.columns) == 0:
        return {"row_issues": {}, "column_issues": {}, "clean": False, "note": "cleaned data is empty"}

    rows = analyze_rows(cleaned_df)
    row_issues = {
        k: rows[k]
        for k in ("fully_empty_rows", "sparse_rows_over_50pct_blank", "exact_duplicate_rows",
                  "near_duplicate_rows_incl_exact")
        if rows.get(k)
    }
    annotated = detect_issues(cleaned_df, profile_dataframe(cleaned_df))
    column_issues = {c["column"]: c["issues_detected"] for c in annotated["columns"] if c["issues_detected"]}
    return {"row_issues": row_issues, "column_issues": column_issues,
            "clean": not row_issues and not column_issues}
