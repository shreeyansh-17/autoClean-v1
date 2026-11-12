"""Validates LLM-generated cleaning plans against a strict schema and allow-list.

This is the safety boundary: the LLM may only request actions that are both
well-formed AND implemented in executor.py. Anything else is rejected.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ValidationError, field_validator

# Allow-list of actions the executor actually implements.
ALLOWED_ACTIONS = {
    "drop_duplicates",
    "drop_rows_if_missing",
    "impute_mean",
    "impute_median",
    "impute_mode",
    "impute_constant",
    "clip_outliers",
    "drop_column",
    "strip_whitespace",
    "normalize_casing",
    "standardize_date_format",
    "fix_dtype",
    "extract_number",
    "no_action",
    # row-wise actions (use column "*"; they act on whole rows, not one column)
    "drop_empty_rows",
    "drop_sparse_rows",
    "drop_near_duplicate_rows",
    "drop_outlier_rows",
}

# Actions that operate on rows rather than a single column. They don't need a real
# column name, so the unknown-column check is skipped for them.
ROW_ACTIONS = {
    "drop_duplicates",
    "drop_empty_rows",
    "drop_sparse_rows",
    "drop_near_duplicate_rows",
    "drop_outlier_rows",
}


# Supported values, shared with the executor so validation and execution can't drift apart.
DATE_FORMATS = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "MM/DD/YYYY": "%m/%d/%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "DD-MM-YYYY": "%d-%m-%Y",
    "YYYY/MM/DD": "%Y/%m/%d",
    "DD-Mon-YYYY": "%d-%b-%Y",
}
SUPPORTED_DTYPES = {"int", "int64", "float", "float64", "str", "string", "object", "bool", "boolean"}


class CleaningAction(BaseModel):
    column: str
    action: str
    reason: str
    # optional, action-specific parameters
    target_format: Optional[str] = None
    method: Optional[str] = None  # e.g. "iqr" or "zscore" for clip_outliers
    fill_value: Optional[str] = None  # for impute_constant
    target_dtype: Optional[str] = None  # for fix_dtype
    casing: Optional[str] = None  # "lower" | "upper" | "title" for normalize_casing
    dayfirst: Optional[bool] = None  # standardize_date_format: True for DD/MM, False for MM/DD (default: infer)
    multiplier: Optional[float] = None  # clip_outliers: IQR multiplier or z-score cutoff (default 3)
    threshold: Optional[float] = None  # drop_sparse_rows: max fraction of blank cells (0-1) a row may have
    min_outlier_cols: Optional[int] = None  # drop_outlier_rows: min # of extreme numeric columns

    @field_validator("method")
    @classmethod
    def method_known(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in ("iqr", "zscore"):
            raise ValueError("method must be 'iqr' or 'zscore'")
        return v.lower() if v else v

    @field_validator("casing")
    @classmethod
    def casing_known(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in ("auto", "lower", "upper", "title"):
            raise ValueError("casing must be 'auto', 'lower', 'upper' or 'title'")
        return v.lower() if v else v

    @field_validator("target_format")
    @classmethod
    def target_format_supported(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        for name in DATE_FORMATS:
            if v.strip().lower() == name.lower():
                return name
        raise ValueError(f"target_format must be one of {sorted(DATE_FORMATS)}")

    @field_validator("target_dtype")
    @classmethod
    def target_dtype_supported(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip().lower() not in SUPPORTED_DTYPES:
            raise ValueError(f"target_dtype must be one of {sorted(SUPPORTED_DTYPES)}")
        return v.strip().lower() if v else v

    @field_validator("multiplier")
    @classmethod
    def multiplier_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("multiplier must be > 0")
        return v

    @field_validator("threshold")
    @classmethod
    def threshold_in_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v < 1.0):
            raise ValueError("threshold must be a fraction in [0, 1)")
        return v

    @field_validator("min_outlier_cols")
    @classmethod
    def min_outlier_cols_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("min_outlier_cols must be >= 1")
        return v

    @field_validator("action")
    @classmethod
    def action_must_be_allowed(cls, v: str) -> str:
        if v not in ALLOWED_ACTIONS:
            raise ValueError(f"Action '{v}' is not in the allowed action list")
        return v


class CleaningPlan(BaseModel):
    actions: list[CleaningAction]


class ValidationResult(BaseModel):
    valid_actions: list[CleaningAction]
    rejected: list[dict]  # {"raw": ..., "error": ...}


def validate_plan(raw_plan: dict, known_columns: list[str]) -> ValidationResult:
    """Validate a raw LLM JSON plan.

    - Structurally invalid actions are rejected individually (not all-or-nothing).
    - Actions referencing unknown columns are rejected.
    - Returns both valid actions (ready to execute) and rejected ones (for the report).
    """
    valid_actions: list[CleaningAction] = []
    rejected: list[dict] = []

    actions_raw = raw_plan.get("actions", []) if isinstance(raw_plan, dict) else []
    if not isinstance(actions_raw, list):
        return ValidationResult(
            valid_actions=[],
            rejected=[{"raw": raw_plan, "error": "Top-level 'actions' is not a list"}],
        )

    for item in actions_raw:
        try:
            action = CleaningAction(**item)
        except ValidationError as e:
            rejected.append({"raw": item, "error": str(e)})
            continue

        if action.action not in ROW_ACTIONS and action.column not in known_columns:
            rejected.append(
                {"raw": item, "error": f"Unknown column '{action.column}'"}
            )
            continue

        valid_actions.append(action)

    return ValidationResult(valid_actions=valid_actions, rejected=rejected)
