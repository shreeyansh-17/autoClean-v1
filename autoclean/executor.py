"""Applies validated cleaning actions to a DataFrame. Pure pandas, no LLM calls here."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from autoclean import row_analyzer as ra
from autoclean.validator import DATE_FORMATS, CleaningAction

class ExecutionLog(dict):
    """Simple record of what happened when applying one action."""


def _drop_rows_by_mask(df: pd.DataFrame, mask: pd.Series, **extra) -> tuple[pd.DataFrame, ExecutionLog]:
    """Remove rows where mask is True; record which row labels went (for the removed-rows audit file)."""
    removed = list(df.index[mask])
    detail = ExecutionLog(rows_removed=len(removed), **extra)
    detail["_removed_index"] = removed  # underscore keys are internal: not printed in report/CLI
    return df.loc[~mask].copy(), detail


def _drop_duplicates(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    # Ignores index-like columns (e.g. 'Unnamed: 0') which would make every row look unique.
    return _drop_rows_by_mask(df, ra.find_duplicate_rows(df))


def _drop_empty_rows(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    return _drop_rows_by_mask(df, ra.find_empty_rows(df))


def _drop_sparse_rows(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    threshold = action.threshold if action.threshold is not None else ra.DEFAULT_SPARSE_THRESHOLD
    return _drop_rows_by_mask(df, ra.find_sparse_rows(df, threshold), max_blank_fraction=threshold)


def _drop_near_duplicate_rows(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    return _drop_rows_by_mask(df, ra.find_near_duplicate_rows(df))


def _drop_outlier_rows(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    min_cols = action.min_outlier_cols if action.min_outlier_cols is not None else ra.DEFAULT_MIN_OUTLIER_COLS
    return _drop_rows_by_mask(df, ra.find_outlier_rows(df, min_cols), min_outlier_cols=min_cols)


def _drop_rows_if_missing(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    before = len(df)
    df = df.dropna(subset=[action.column])
    return df, ExecutionLog(rows_removed=before - len(df))


def _numeric_or_raise(df: pd.DataFrame, col: str) -> pd.Series:
    """Numeric view of a column, refusing if it would destroy non-numeric values.

    Coercing a text column would turn every value into NaN, so the imputed
    result would silently wipe the column. Fail loudly instead (logged as 'failed').
    """
    numeric = pd.to_numeric(df[col], errors="coerce")
    lost = int((numeric.isna() & df[col].notna()).sum())
    if lost:
        raise ValueError(
            f"column '{col}' has {lost} non-numeric value(s); mean/median imputation refused "
            "(use fix_dtype first, or impute_mode / impute_constant)"
        )
    return numeric


def _impute_mean(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    numeric = _numeric_or_raise(df, col)
    fill = numeric.mean()
    count = int(df[col].isna().sum())
    df[col] = numeric.fillna(fill)
    return df, ExecutionLog(values_filled=count, fill_value=round(float(fill), 4))


def _impute_median(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    numeric = _numeric_or_raise(df, col)
    fill = numeric.median()
    count = int(df[col].isna().sum())
    df[col] = numeric.fillna(fill)
    return df, ExecutionLog(values_filled=count, fill_value=round(float(fill), 4))


def _impute_mode(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    mode_vals = df[col].mode(dropna=True)
    if mode_vals.empty:
        return df, ExecutionLog(values_filled=0, note="no mode available")
    fill = mode_vals.iloc[0]
    count = int(df[col].isna().sum())
    df[col] = df[col].fillna(fill)
    return df, ExecutionLog(values_filled=count, fill_value=str(fill))


def _impute_constant(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    fill = action.fill_value if action.fill_value is not None else ""
    count = int(df[col].isna().sum())
    if pd.api.types.is_numeric_dtype(df[col]):
        # keep a numeric column numeric: convert the fill value or refuse
        try:
            fill = float(fill)
        except (TypeError, ValueError):
            raise ValueError(f"fill_value {fill!r} is not numeric but column '{col}' is numeric")
        if pd.api.types.is_integer_dtype(df[col]) and fill.is_integer():
            fill = int(fill)
    df[col] = df[col].fillna(fill)
    return df, ExecutionLog(values_filled=count, fill_value=fill)


def _clip_outliers(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    """Winsorise extreme values. Default is 3*IQR (or |z| > 3), not the textbook 1.5*IQR,
    because 1.5*IQR flattens genuine high values (e.g. premium laptop prices).
    """
    col = action.column
    method = (action.method or "iqr").lower()
    k = action.multiplier if action.multiplier is not None else 3.0
    numeric = _numeric_or_raise(df, col)
    if method == "zscore":
        mean, std = numeric.mean(), numeric.std()
        lower, upper = mean - k * std, mean + k * std
    else:
        q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - k * iqr, q3 + k * iqr
    clipped_count = int(((numeric < lower) | (numeric > upper)).sum())
    df[col] = numeric.clip(lower=lower, upper=upper)
    return df, ExecutionLog(
        method=method, multiplier=k, values_clipped=clipped_count,
        lower=round(float(lower), 4), upper=round(float(upper), 4),
    )


def _drop_column(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    df = df.drop(columns=[action.column])
    return df, ExecutionLog(column_dropped=action.column)


def _strip_whitespace(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    before = df[col].astype(str)
    df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)
    changed = int(((before != df[col].astype(str)) & df[col].notna()).sum())  # NaN != NaN must not count
    return df, ExecutionLog(values_changed=changed)


def _normalize_casing(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    """casing='auto' (default) merges case-variants of the same value to its most common
    spelling ('Dell'/'DELL'/'dell' -> 'Dell') and leaves everything else alone, so
    'Intel Core i5 2.3GHz' is not mangled into 'Intel Core I5 2.3Ghz'.
    'lower' / 'upper' / 'title' force a blanket case change.
    """
    col = action.column
    casing = (action.casing or "auto").lower()
    before = df[col].astype(str)

    if casing == "auto":
        s = df[col]
        non_null = s.dropna().astype(str)
        counts = non_null.value_counts()  # count desc, then first appearance
        canonical = {}
        for value in counts.index:
            canonical.setdefault(value.lower(), value)
        df[col] = s.map(lambda v: canonical.get(v.lower(), v) if isinstance(v, str) else v)
    else:
        def apply_case(v):
            if not isinstance(v, str):
                return v
            return {"upper": v.upper, "title": v.title}.get(casing, v.lower)()
        df[col] = df[col].apply(apply_case)

    changed = int(((before != df[col].astype(str)) & df[col].notna()).sum())  # NaN != NaN must not count
    return df, ExecutionLog(values_changed=changed, casing=casing)


_NUMERIC_DATE_RE = re.compile(r"^\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\s*$")


def _infer_dayfirst(values: pd.Series) -> tuple[bool, int]:
    """Decide DD/MM vs MM/DD from the data itself. Returns (dayfirst, ambiguous_count).

    A first part > 12 can only be a day; a second part > 12 can only be a day-in-second-place.
    If neither ever happens every numeric date is ambiguous and we fall back to month-first
    (pandas' default) — the caller reports the ambiguity instead of hiding it.
    """
    first_gt12 = second_gt12 = ambiguous = 0
    for v in values.dropna().astype(str):
        m = _NUMERIC_DATE_RE.match(v)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12:
            first_gt12 += 1
        elif b > 12:
            second_gt12 += 1
        elif a != b:
            ambiguous += 1
    if first_gt12 and not second_gt12:
        return True, 0
    if second_gt12 and not first_gt12:
        return False, 0
    return False, ambiguous


def _standardize_date_format(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    target = action.target_format or "YYYY-MM-DD"
    out_fmt = DATE_FORMATS[target]

    if action.dayfirst is not None:
        dayfirst, ambiguous, order = action.dayfirst, 0, "specified"
    else:
        dayfirst, ambiguous = _infer_dayfirst(df[col])
        order = "inferred"

    parsed = pd.to_datetime(df[col], errors="coerce", format="mixed", dayfirst=dayfirst)
    failed = int(parsed.isna().sum() - df[col].isna().sum())
    df[col] = parsed.dt.strftime(out_fmt)
    detail = ExecutionLog(
        target_format=target, day_first=dayfirst, order=order, unparseable_values=max(failed, 0),
    )
    if ambiguous:
        detail["ambiguous_dates_assumed_month_first"] = ambiguous
    return df, detail


_TRUE = {"true", "t", "yes", "y", "1", "1.0"}
_FALSE = {"false", "f", "no", "n", "0", "0.0"}


def _to_bool(series: pd.Series) -> tuple[pd.Series, int]:
    """Map common true/false spellings; missing stays missing (<NA>), never True."""
    present = series.notna()
    text = series[present].astype(str).str.strip().str.lower()
    result = pd.Series(pd.NA, index=series.index, dtype="boolean")
    result[text.index[text.isin(_TRUE)]] = True
    result[text.index[text.isin(_FALSE)]] = False
    unrecognised = int((present & result.isna()).sum())
    return result, unrecognised


def _fix_dtype(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    target = (action.target_dtype or "str").lower()
    before_na = int(df[col].isna().sum())

    try:
        if target in ("int", "int64"):
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        elif target in ("float", "float64"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif target in ("str", "string", "object"):
            # keep missing values missing (astype(str) would turn them into the text "nan")
            df[col] = df[col].map(lambda v: v if pd.isna(v) else str(v))
        elif target in ("bool", "boolean"):
            converted, bad = _to_bool(df[col])
            if bad:
                return df, ExecutionLog(error=f"{bad} value(s) in '{col}' are not recognisable true/false values; column left unchanged")
            df[col] = converted
        else:
            return df, ExecutionLog(error=f"Unsupported target_dtype '{target}'")
    except Exception as e:
        return df, ExecutionLog(error=f"fix_dtype failed: {e}")

    after_na = int(df[col].isna().sum())
    return df, ExecutionLog(target_dtype=target, new_nulls_introduced=max(after_na - before_na, 0))


_UNIT_RE = re.compile(r"^\s*([-+]?\d[\d,]*\.?\d*)\s*([A-Za-z]+)\s*$")
# unit -> (family, factor to the family's base unit)
_UNIT_FACTORS = {
    "kg": ("kg", 1.0), "g": ("kg", 0.001), "lb": ("kg", 0.45359237), "lbs": ("kg", 0.45359237),
    "mb": ("GB", 1 / 1024), "gb": ("GB", 1.0), "tb": ("GB", 1024.0),
}
_MAX_UNPARSEABLE_FRACTION = 0.05


def _extract_number(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    """'8GB' -> 8, '1TB' -> 1024 (GB), '1.37kg' -> 1.37. Known units are converted to one
    base unit per column (kg, GB); unknown units just keep the number.

    Refuses (and leaves the column untouched) when more than 5% of values don't fit the
    plain '<number><unit>' shape, e.g. '128GB SSD', so no information is thrown away.
    """
    col = action.column
    s = df[col]
    present = s.notna()
    parsed = s[present].astype(str).str.extract(_UNIT_RE)
    ok = parsed[0].notna()
    bad = int((~ok).sum())
    if present.sum() and bad / present.sum() > _MAX_UNPARSEABLE_FRACTION:
        raise ValueError(
            f"{bad} of {int(present.sum())} values in '{col}' are not plain '<number><unit>' "
            "(e.g. contain extra text); extract_number refused to avoid losing information"
        )
    nums = pd.to_numeric(parsed[0].str.replace(",", "", regex=False), errors="coerce")
    units = parsed[1].str.lower()
    families = {_UNIT_FACTORS[u][0] for u in units[ok].unique() if u in _UNIT_FACTORS}
    factor = units.map(lambda u: _UNIT_FACTORS[u][1] if u in _UNIT_FACTORS else 1.0)
    if len(families) > 1:
        raise ValueError(f"'{col}' mixes unit families {sorted(families)}; refused")
    result = pd.Series(np.nan, index=s.index, dtype="float64")
    result[present] = (nums * factor).where(ok)
    df[col] = result
    unit_label = next(iter(families)) if families else ",".join(sorted(units[ok].unique()))
    return df, ExecutionLog(unit=unit_label, values_converted=int(ok.sum()), unparseable_set_to_missing=bad)


def _no_action(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    return df, ExecutionLog(note="no action taken")


_ACTION_DISPATCH = {
    "drop_duplicates": _drop_duplicates,
    "drop_empty_rows": _drop_empty_rows,
    "drop_sparse_rows": _drop_sparse_rows,
    "drop_near_duplicate_rows": _drop_near_duplicate_rows,
    "drop_outlier_rows": _drop_outlier_rows,
    "drop_rows_if_missing": _drop_rows_if_missing,
    "impute_mean": _impute_mean,
    "impute_median": _impute_median,
    "impute_mode": _impute_mode,
    "impute_constant": _impute_constant,
    "clip_outliers": _clip_outliers,
    "drop_column": _drop_column,
    "strip_whitespace": _strip_whitespace,
    "normalize_casing": _normalize_casing,
    "standardize_date_format": _standardize_date_format,
    "fix_dtype": _fix_dtype,
    "extract_number": _extract_number,
    "no_action": _no_action,
}


# Row-wise actions run first, in this order, and always on the data as it arrived:
# blank rows must go before imputation (otherwise imputing "fills" them into fake
# rows), and outlier rows must be judged before clip_outliers flattens them.
_ROW_ACTION_ORDER = [
    "drop_empty_rows",
    "drop_sparse_rows",
    "drop_duplicates",
    "drop_near_duplicate_rows",
    "drop_outlier_rows",
]


def _order_actions(actions: list[CleaningAction]) -> list[CleaningAction]:
    """Stable sort: row-wise actions first (in _ROW_ACTION_ORDER), everything else keeps LLM order."""
    n = len(_ROW_ACTION_ORDER)

    def key(a: CleaningAction) -> int:
        if a.action in _ROW_ACTION_ORDER:
            return _ROW_ACTION_ORDER.index(a.action)
        # drop_column goes last so no earlier action targets a column that is already gone
        return n + 1 if a.action == "drop_column" else n
    return sorted(actions, key=key)


def execute_plan(df: pd.DataFrame, actions: list[CleaningAction]) -> tuple[pd.DataFrame, list[dict]]:
    """Apply each validated action in sequence. Returns (cleaned_df, execution_log).

    A failure in one action is caught and logged, not fatal to the rest of the plan.
    """
    execution_log = []

    for action in _order_actions(actions):
        handler = _ACTION_DISPATCH.get(action.action)
        if handler is None:
            execution_log.append({
                "column": action.column,
                "action": action.action,
                "reason": action.reason,
                "status": "skipped",
                "detail": {"error": "No executor implemented for this action"},
            })
            continue

        if action.action not in _ROW_ACTION_ORDER and action.column not in df.columns:
            execution_log.append({
                "column": action.column,
                "action": action.action,
                "reason": action.reason,
                "status": "skipped",
                "detail": {"error": "column no longer exists (dropped by an earlier action)"},
            })
            continue

        try:
            df, detail = handler(df, action)
            execution_log.append({
                "column": action.column,
                "action": action.action,
                "reason": action.reason,
                "status": "applied",
                "detail": dict(detail),
            })
        except Exception as e:
            execution_log.append({
                "column": action.column,
                "action": action.action,
                "reason": action.reason,
                "status": "failed",
                "detail": {"error": str(e)},
            })

    return df, execution_log
