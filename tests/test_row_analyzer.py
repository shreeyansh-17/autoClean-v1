import numpy as np
import pandas as pd

from autoclean import row_analyzer as ra
from autoclean.executor import execute_plan
from autoclean.validator import CleaningAction, validate_plan


def _df():
    return pd.DataFrame({
        "Unnamed: 0": [0, 1, 2, 3, 4, 5, np.nan],
        "name": ["a", "b", "b", " B ", None, "c", None],
        "qty": [1, 2, 2, 2.0, None, 3, None],
        "price": [10, 20, 20, 20, None, 30, None],
    })


def test_index_like_column_detected_and_ignored():
    df = _df()
    assert "Unnamed: 0" in ra.index_like_columns(df)
    # rows 1 and 2 differ only in the counter column -> still exact duplicates
    assert ra.find_duplicate_rows(df).tolist() == [False, False, True, False, False, False, False]


def test_consecutive_integer_column_is_index_like():
    df = pd.DataFrame({"id": [1, 2, 3], "x": ["a", "a", "a"]})
    assert ra.index_like_columns(df) == ["id"]
    assert ra.find_duplicate_rows(df).tolist() == [False, True, True]


def test_empty_rows_ignore_counter_and_blank_strings():
    df = _df()
    df.loc[5, ["name", "qty", "price"]] = ["  ", None, None]
    flags = ra.find_empty_rows(df)
    assert flags.tolist() == [False, False, False, False, True, True, True]


def test_sparse_rows_threshold():
    df = pd.DataFrame({"a": [1, None, 3], "b": [1, None, None], "c": [1, None, None], "d": [5, 9, 7]})
    assert ra.find_sparse_rows(df, 0.5).tolist() == [False, True, False]   # row2: 2/4 blank, not > 0.5
    assert ra.find_sparse_rows(df, 0.4).tolist() == [False, True, True]


def test_near_duplicates_normalise_case_space_and_numbers():
    df = _df()
    near = ra.find_near_duplicate_rows(df)
    assert near.tolist()[3] is True or near.iloc[3]          # " B " / 2.0 matches "b" / 2
    assert not near.iloc[4] and not near.iloc[6]             # blank rows are not "duplicates"


def test_outlier_rows_need_min_columns():
    base = list(range(1, 21))
    df = pd.DataFrame({"x": base + [10_000, 10_000, 21], "y": base + [10_000, 22, 10_000]})
    scores = ra.outlier_scores(df)
    assert scores.iloc[20] == 2 and scores.iloc[21] == 1 and scores.iloc[22] == 1
    assert ra.find_outlier_rows(df, 2).sum() == 1
    assert ra.find_outlier_rows(df, 1).sum() == 3


def test_executor_row_actions_and_removed_index():
    df = _df()
    plan = [
        CleaningAction(column="qty", action="impute_median", reason="fill"),   # must run AFTER row drops
        CleaningAction(column="*", action="drop_duplicates", reason="dups"),
        CleaningAction(column="*", action="drop_empty_rows", reason="blank"),
    ]
    cleaned, log = execute_plan(df, plan)
    assert [e["action"] for e in log] == ["drop_empty_rows", "drop_duplicates", "impute_median"]
    assert log[0]["detail"]["_removed_index"] == [4, 6]
    assert len(cleaned) == 4
    assert cleaned["qty"].isna().sum() == 0 and 4 not in cleaned.index   # no fabricated rows


def test_validator_accepts_star_only_for_row_actions():
    raw = {"actions": [
        {"column": "*", "action": "drop_empty_rows", "reason": "r"},
        {"column": "*", "action": "impute_mean", "reason": "r"},
        {"column": "*", "action": "drop_sparse_rows", "reason": "r", "threshold": 1.5},
        {"column": "*", "action": "drop_outlier_rows", "reason": "r", "min_outlier_cols": 2},
    ]}
    res = validate_plan(raw, ["a", "b"])
    assert [a.action for a in res.valid_actions] == ["drop_empty_rows", "drop_outlier_rows"]
    assert len(res.rejected) == 2


def test_analyze_rows_summary_has_counts_not_values():
    summary = ra.analyze_rows(_df())
    assert summary["fully_empty_rows"] == 2
    assert summary["exact_duplicate_rows"] == 1
    assert summary["index_like_columns_ignored"] == ["Unnamed: 0"]
