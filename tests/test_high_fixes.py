import numpy as np
import pandas as pd

from autoclean.executor import execute_plan
from autoclean.issue_detector import _detect_casing_inconsistency, detect_column_issues
from autoclean.placeholders import normalize_placeholders
from autoclean.validator import CleaningAction, validate_plan


def run(df, **kw):
    cleaned, log = execute_plan(df, [CleaningAction(reason="t", **kw)])
    return cleaned, log[0]


# --- 5: casing no longer mangles values
def test_auto_casing_merges_variants_without_touching_others():
    df = pd.DataFrame({"c": ["Intel Core i5 2.3GHz", "Dell", "DELL", "Dell", "dell", None]})
    cleaned, log = run(df, column="c", action="normalize_casing")
    assert cleaned["c"].tolist()[:5] == ["Intel Core i5 2.3GHz", "Dell", "Dell", "Dell", "Dell"]
    assert log["detail"]["casing"] == "auto" and log["detail"]["values_changed"] == 2


def test_explicit_title_casing_still_works():
    cleaned, _ = run(pd.DataFrame({"c": ["new york"]}), column="c", action="normalize_casing", casing="title")
    assert cleaned["c"].tolist() == ["New York"]


# --- 6: detector no longer flags high-cardinality columns with no case variants
def test_casing_detector_no_false_positive_on_many_unique_values():
    s = pd.Series([f"value{i}" for i in range(500)])
    assert _detect_casing_inconsistency(s) is False
    assert _detect_casing_inconsistency(pd.Series(["a", "A", "b"])) is True
    s2 = pd.Series([f"v{i}" for i in range(300)] + ["V5"])  # variant beyond the first 200 uniques
    assert _detect_casing_inconsistency(s2) is True


# --- 7: placeholders
def test_placeholders_become_missing_conservatively():
    df = pd.DataFrame({"w": ["1.3kg", "?", " N/A ", "--"], "region": ["NA", "none", "EU", "unknown"], "n": [1, 2, 3, 4]})
    out, counts = normalize_placeholders(df)
    assert out["w"].isna().tolist() == [False, True, True, True]
    assert out["region"].notna().all()           # NA / none / unknown may be real categories
    assert counts == {"w": 3}
    assert df["w"].notna().all()                  # input not mutated


# --- 8: numbers with units
def test_extract_number_ram_weight_and_storage_units():
    ram, log = run(pd.DataFrame({"Ram": ["8GB", "16GB", None, "512MB"]}), column="Ram", action="extract_number")
    assert ram["Ram"].tolist()[:2] == [8.0, 16.0] and ram["Ram"].iloc[3] == 0.5 and np.isnan(ram["Ram"].iloc[2])
    assert log["detail"]["unit"] == "GB"
    w, log = run(pd.DataFrame({"W": ["1.37kg", "500g", "2 kg"]}), column="W", action="extract_number")
    assert w["W"].tolist() == [1.37, 0.5, 2.0] and log["detail"]["unit"] == "kg"
    tb, _ = run(pd.DataFrame({"S": ["1TB", "256GB"]}), column="S", action="extract_number")
    assert tb["S"].tolist() == [1024.0, 256.0]


def test_extract_number_refuses_composite_values_and_keeps_data():
    df = pd.DataFrame({"Memory": ["128GB SSD", "1TB HDD", "256GB SSD", "512GB SSD"]})
    cleaned, log = run(df, column="Memory", action="extract_number")
    assert log["status"] == "failed" and "refused" in log["detail"]["error"]
    assert cleaned["Memory"].tolist()[0] == "128GB SSD"


def test_extract_number_refuses_mixed_unit_families():
    _, log = run(pd.DataFrame({"x": ["1kg", "2GB"]}), column="x", action="extract_number")
    assert log["status"] == "failed"


def test_detector_flags_numeric_with_units():
    s = pd.Series(["8GB", "16GB", "4GB", None])
    issues = detect_column_issues(s, {"missing_pct": 25.0, "unique_count": 3, "looks_numeric_pct": 0})
    assert "numeric_values_with_units" in issues


# --- 9: clip_outliers
def test_clip_default_is_3_iqr_and_keeps_genuine_high_values():
    prices = list(range(30000, 90000, 1000)) + [150000]   # a pricey-but-real laptop
    cleaned, log = run(pd.DataFrame({"p": prices}), column="p", action="clip_outliers")
    assert cleaned["p"].max() == 150000 and log["detail"]["values_clipped"] == 0
    cleaned, log = run(pd.DataFrame({"p": prices}), column="p", action="clip_outliers", method="iqr", multiplier=1.5)
    assert cleaned["p"].max() < 150000 and log["detail"]["values_clipped"] >= 1


def test_clip_zscore_is_honoured():
    vals = [10, 11, 12, 10, 11, 12, 10, 11, 12, 10, 11, 12, 10, 11, 12, 1000]
    cleaned, log = run(pd.DataFrame({"v": vals}), column="v", action="clip_outliers", method="zscore", multiplier=3)
    assert log["detail"]["method"] == "zscore" and cleaned["v"].max() < 1000


def test_clip_refuses_text_column():
    _, log = run(pd.DataFrame({"v": ["a", "b"]}), column="v", action="clip_outliers")
    assert log["status"] == "failed"


def test_validator_rejects_bad_parameters():
    raw = {"actions": [
        {"column": "a", "action": "clip_outliers", "reason": "r", "method": "median"},
        {"column": "a", "action": "normalize_casing", "reason": "r", "casing": "banana"},
        {"column": "a", "action": "clip_outliers", "reason": "r", "method": "ZScore", "multiplier": 2.5},
        {"column": "a", "action": "extract_number", "reason": "r"},
    ]}
    res = validate_plan(raw, ["a"])
    assert len(res.rejected) == 2 and [a.action for a in res.valid_actions] == ["clip_outliers", "extract_number"]
    assert res.valid_actions[0].method == "zscore"
