"""Row-wise analysis: flags problematic *rows* (as opposed to columns).

Used in two places:
- pipeline.py: `analyze_rows` summarises the dataset's rows into a compact dict
  that is sent to the LLM (counts only, no raw rows) and shown in the report.
- executor.py: the row-level `find_*` helpers pick which rows a validated action
  removes, so the LLM only chooses *whether/how strictly*, never *which rows*.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

DEFAULT_SPARSE_THRESHOLD = 0.5   # row is "sparse" if > 50% of its cells are blank
DEFAULT_MIN_OUTLIER_COLS = 2     # row is an outlier row if >= 2 numeric cols are extreme
EXTREME_IQR_MULT = 3.0           # 3*IQR fences (more conservative than the 1.5 used per-column)
MIN_NUMERIC_PARSE_PCT = 0.9      # a column counts as numeric if >= 90% of its non-blank cells parse


def blank_mask(df: pd.DataFrame) -> pd.DataFrame:
    """True where a cell is NaN/None or an empty / whitespace-only string."""
    mask = df.isna()
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
            mask[col] = mask[col] | s.astype("string").str.strip().eq("").fillna(False).astype(bool)
    return mask


def index_like_columns(df: pd.DataFrame) -> list[str]:
    """Columns that merely number the rows (e.g. pandas' 'Unnamed: 0' or an 'id' 0..n).

    They make every row look unique, so they must be ignored when comparing rows.
    """
    found = []
    for col in df.columns:
        name = str(col).strip().lower()
        if name.startswith("unnamed:") or name in ("index", "level_0"):
            found.append(col)
            continue
        numeric = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(numeric) > 1 and numeric.is_unique and (numeric % 1 == 0).all():
            diffs = np.diff(numeric.to_numpy())
            if (diffs == 1).all():  # strictly consecutive integers -> a row counter
                found.append(col)
    return found


def _content_columns(df: pd.DataFrame) -> list[str]:
    skip = set(index_like_columns(df))
    return [c for c in df.columns if c not in skip]


def _numeric_columns(df: pd.DataFrame, cols: list[str], blanks: pd.DataFrame) -> dict[str, pd.Series]:
    """Return {col: numeric Series} for columns that are (mostly) numeric."""
    out = {}
    for col in cols:
        present = ~blanks[col]
        if present.sum() < 4:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric[present].notna().mean() >= MIN_NUMERIC_PARSE_PCT and numeric.nunique() > 2:
            out[col] = numeric
    return out


def _normalize_cell(v) -> str:
    if pd.isna(v):
        return ""
    s = re.sub(r"\s+", " ", str(v).strip().lower())
    try:  # "8", "8.0", "8.00" are the same value
        return repr(round(float(s), 6))
    except ValueError:
        return s


def _normalized_frame(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df[cols].apply(lambda col: col.map(_normalize_cell))


# --------------------------------------------------------------------------- #
# Row selectors (return a boolean Series aligned to df.index; True = remove)
# --------------------------------------------------------------------------- #
def find_empty_rows(df: pd.DataFrame) -> pd.Series:
    cols = _content_columns(df)
    if not cols:
        return pd.Series(False, index=df.index)
    return blank_mask(df[cols]).all(axis=1)


def find_sparse_rows(df: pd.DataFrame, threshold: float = DEFAULT_SPARSE_THRESHOLD) -> pd.Series:
    """Rows where the fraction of blank cells exceeds `threshold` (includes empty rows)."""
    cols = _content_columns(df)
    if not cols:
        return pd.Series(False, index=df.index)
    return blank_mask(df[cols]).mean(axis=1) > threshold


def find_duplicate_rows(df: pd.DataFrame) -> pd.Series:
    """Exact duplicates of an earlier row, ignoring index-like columns. First occurrence is kept.
    Blank rows are not counted here — drop_empty_rows owns those.
    """
    cols = _content_columns(df)
    if not cols:
        return pd.Series(False, index=df.index)
    return df.duplicated(subset=cols, keep="first") & ~find_empty_rows(df)


def find_near_duplicate_rows(df: pd.DataFrame) -> pd.Series:
    """Rows equal to an earlier row after normalising case, whitespace and number formatting
    ('8GB ' vs '8gb', 8 vs 8.0). Exact duplicates are included. Blank rows are not duplicates
    of each other here — drop_empty_rows owns those.
    """
    cols = _content_columns(df)
    if not cols:
        return pd.Series(False, index=df.index)
    norm = _normalized_frame(df, cols)
    dup = norm.duplicated(keep="first")
    return dup & ~find_empty_rows(df)


def outlier_scores(df: pd.DataFrame) -> pd.Series:
    """Per-row count of numeric columns whose value lies beyond 3*IQR of that column."""
    cols = _content_columns(df)
    blanks = blank_mask(df[cols]) if cols else pd.DataFrame(index=df.index)
    numeric_cols = _numeric_columns(df, cols, blanks)
    score = pd.Series(0, index=df.index, dtype="int64")
    for col, numeric in numeric_cols.items():
        q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lo, hi = q1 - EXTREME_IQR_MULT * iqr, q3 + EXTREME_IQR_MULT * iqr
        score += ((numeric < lo) | (numeric > hi)).fillna(False).astype("int64")
    return score


def find_outlier_rows(df: pd.DataFrame, min_outlier_cols: int = DEFAULT_MIN_OUTLIER_COLS) -> pd.Series:
    return outlier_scores(df) >= max(int(min_outlier_cols), 1)


# --------------------------------------------------------------------------- #
# Whole-dataset row analysis
# --------------------------------------------------------------------------- #
def row_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Per-row audit table (one line per row of `df`, same index)."""
    cols = _content_columns(df)
    blanks = blank_mask(df[cols]) if cols else pd.DataFrame(index=df.index)
    missing_count = blanks.sum(axis=1) if cols else pd.Series(0, index=df.index)
    return pd.DataFrame({
        "blank_cells": missing_count,
        "blank_pct": (missing_count / max(len(cols), 1) * 100).round(1),
        "is_empty": find_empty_rows(df),
        "is_sparse": find_sparse_rows(df),
        "is_exact_duplicate": find_duplicate_rows(df),
        "is_near_duplicate": find_near_duplicate_rows(df),
        "outlier_cols": outlier_scores(df),
    })


def analyze_rows(df: pd.DataFrame, max_examples: int = 5) -> dict:
    """Compact, LLM-friendly row-level summary. Counts and row positions only — no cell values."""
    flags = row_flags(df)
    ignored = index_like_columns(df)
    cols = _content_columns(df)
    non_empty = flags[~flags["is_empty"]]

    def examples(mask: pd.Series) -> list:
        return [int(i) if isinstance(i, (int, np.integer)) else str(i) for i in flags.index[mask][:max_examples]]

    score_hist = {int(k): int(v) for k, v in flags["outlier_cols"].value_counts().sort_index().items() if k > 0}
    blank_hist = {int(k): int(v) for k, v in flags["blank_cells"].value_counts().sort_index().items() if k > 0}

    return {
        "rows_analyzed": int(len(df)),
        "columns_considered": len(cols),
        "index_like_columns_ignored": [str(c) for c in ignored],
        "fully_empty_rows": int(flags["is_empty"].sum()),
        "sparse_rows_over_50pct_blank": int(flags["is_sparse"].sum()),
        "non_empty_rows_with_any_blank": int((non_empty["blank_cells"] > 0).sum()),
        "rows_by_blank_cell_count": blank_hist,
        "exact_duplicate_rows": int(flags["is_exact_duplicate"].sum()),
        "near_duplicate_rows_incl_exact": int(flags["is_near_duplicate"].sum()),
        "rows_by_extreme_outlier_column_count": score_hist,
        "example_row_labels": {
            "empty": examples(flags["is_empty"]),
            "duplicate": examples(flags["is_exact_duplicate"]),
            "outlier": examples(flags["outlier_cols"] >= DEFAULT_MIN_OUTLIER_COLS),
        },
    }
