import pandas as pd

from autoclean.executor import execute_plan
from autoclean.validator import CleaningAction, validate_plan


def run(df, **kw):
    cleaned, log = execute_plan(df, [CleaningAction(reason="t", **kw)])
    return cleaned, log[0]


# --- 10: fix_dtype
def test_bool_keeps_missing_missing_and_maps_spellings():
    df = pd.DataFrame({"b": ["Yes", "no", None, "TRUE", "0"]})
    cleaned, log = run(df, column="b", action="fix_dtype", target_dtype="bool")
    assert cleaned["b"].tolist()[0:2] == [True, False] and pd.isna(cleaned["b"].iloc[2])
    assert cleaned["b"].tolist()[3:] == [True, False] and log["status"] == "applied"


def test_bool_refuses_unrecognised_values():
    df = pd.DataFrame({"b": ["yes", "maybe"]})
    cleaned, log = run(df, column="b", action="fix_dtype", target_dtype="bool")
    assert "error" in log["detail"] and cleaned["b"].tolist() == ["yes", "maybe"]


def test_str_dtype_does_not_turn_missing_into_text():
    cleaned, _ = run(pd.DataFrame({"x": [1, None, 3]}), column="x", action="fix_dtype", target_dtype="str")
    assert cleaned["x"].isna().tolist() == [False, True, False]
    assert "nan" not in [str(v).lower() for v in cleaned["x"].dropna()]


# --- 11: parameter validation
def test_validator_rejects_unsupported_formats_and_dtypes():
    raw = {"actions": [
        {"column": "a", "action": "standardize_date_format", "reason": "r", "target_format": "DD.MM.YY"},
        {"column": "a", "action": "fix_dtype", "reason": "r", "target_dtype": "complex"},
        {"column": "a", "action": "standardize_date_format", "reason": "r", "target_format": "dd-mm-yyyy"},
        {"column": "a", "action": "fix_dtype", "reason": "r", "target_dtype": "Float"},
    ]}
    res = validate_plan(raw, ["a"])
    assert len(res.rejected) == 2
    assert res.valid_actions[0].target_format == "DD-MM-YYYY" and res.valid_actions[1].target_dtype == "float"


def test_impute_constant_keeps_numeric_column_numeric():
    cleaned, log = run(pd.DataFrame({"n": [1.0, None]}), column="n", action="impute_constant", fill_value="0")
    assert cleaned["n"].tolist() == [1.0, 0.0] and pd.api.types.is_numeric_dtype(cleaned["n"])
    cleaned, log = run(pd.DataFrame({"n": [1.0, None]}), column="n", action="impute_constant", fill_value="abc")
    assert log["status"] == "failed" and cleaned["n"].isna().sum() == 1


def test_impute_constant_text_column_unchanged_behaviour():
    cleaned, _ = run(pd.DataFrame({"t": ["a", None]}), column="t", action="impute_constant", fill_value="unknown")
    assert cleaned["t"].tolist() == ["a", "unknown"]


# --- 12: dates
def test_dayfirst_inferred_from_unambiguous_values():
    cleaned, log = run(pd.DataFrame({"d": ["03/04/2023", "13/04/2023"]}), column="d", action="standardize_date_format")
    assert cleaned["d"].tolist() == ["2023-04-03", "2023-04-13"]
    assert log["detail"]["day_first"] is True and "ambiguous_dates_assumed_month_first" not in log["detail"]


def test_monthfirst_inferred():
    cleaned, _ = run(pd.DataFrame({"d": ["03/04/2023", "04/13/2023"]}), column="d", action="standardize_date_format")
    assert cleaned["d"].tolist() == ["2023-03-04", "2023-04-13"]


def test_fully_ambiguous_dates_are_reported_not_hidden():
    cleaned, log = run(pd.DataFrame({"d": ["03/04/2023", "05/06/2023"]}), column="d", action="standardize_date_format")
    assert log["detail"]["ambiguous_dates_assumed_month_first"] == 2


def test_explicit_dayfirst_wins():
    cleaned, log = run(pd.DataFrame({"d": ["03/04/2023"]}), column="d", action="standardize_date_format", dayfirst=True)
    assert cleaned["d"].tolist() == ["2023-04-03"] and log["detail"]["order"] == "specified"


def test_new_target_format_works():
    cleaned, _ = run(pd.DataFrame({"d": ["2023-01-05"]}), column="d", action="standardize_date_format", target_format="DD-MM-YYYY")
    assert cleaned["d"].tolist() == ["05-01-2023"]


# --- 13: action ordering / dropped columns
def test_drop_column_runs_last_and_nothing_fails():
    df = pd.DataFrame({"a": [1.0, None, 3.0], "b": [1, 2, 3]})
    plan = [
        CleaningAction(column="a", action="drop_column", reason="r"),
        CleaningAction(column="a", action="impute_mean", reason="r"),
    ]
    cleaned, log = execute_plan(df, plan)
    assert [e["action"] for e in log] == ["impute_mean", "drop_column"]
    assert all(e["status"] == "applied" for e in log) and list(cleaned.columns) == ["b"]


def test_action_on_already_missing_column_is_skipped_not_failed():
    df = pd.DataFrame({"b": [1, 2]})
    _, log = execute_plan(df, [CleaningAction(column="ghost", action="strip_whitespace", reason="r")])
    assert log[0]["status"] == "skipped"
