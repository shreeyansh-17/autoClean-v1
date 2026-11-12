"""Turns placeholder strings that really mean "missing" (e.g. '?') into real NaN.

Without this, a column like Weight = ['1.37kg', '?', ...] looks like clean text, so
nothing flags the '?' and numeric conversion later fails or silently drops the column.
The token list is deliberately conservative: words like 'none', 'na' or 'unknown'
can be legitimate category values, so they are NOT converted.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PLACEHOLDER_TOKENS = {"?", "??", "-", "--", "n/a", "#n/a", "null", "nan", "nil", "missing"}


def normalize_placeholders(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Return (copy of df with placeholders -> NaN, {column: count converted})."""
    out = df.copy()
    converted: dict[str, int] = {}
    for col in out.columns:
        s = out[col]
        if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
            continue
        mask = s.astype("string").str.strip().str.lower().isin(PLACEHOLDER_TOKENS).fillna(False).astype(bool)
        if mask.any():
            out[col] = s.mask(mask, np.nan)
            converted[str(col)] = int(mask.sum())
    return out, converted
