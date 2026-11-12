import json

import pandas as pd
import pytest

import autoclean.pipeline as pl
from autoclean.executor import execute_plan
from autoclean.llm_engine import _normalize_plan
from autoclean.loader import load_data
from autoclean.validator import CleaningAction


@pytest.mark.parametrize("action", ["impute_mean", "impute_median"])
def test_numeric_imputation_refuses_text_column_and_keeps_data(action):
    df = pd.DataFrame({"txt": ["a", "b", None, "c"]})
    cleaned, log = execute_plan(df, [CleaningAction(column="txt", action=action, reason="t")])
    assert log[0]["status"] == "failed" and "non-numeric" in log[0]["detail"]["error"]
    assert cleaned["txt"].tolist()[:2] == ["a", "b"]  # untouched


def test_numeric_imputation_still_works_on_numeric_text():
    df = pd.DataFrame({"n": ["1", "3", None]})   # numeric stored as text: nothing is lost
    cleaned, log = execute_plan(df, [CleaningAction(column="n", action="impute_mean", reason="t")])
    assert log[0]["status"] == "applied" and cleaned["n"].tolist() == [1.0, 3.0, 2.0]


def test_normalize_plan_shapes():
    assert _normalize_plan({"actions": []}) == {"actions": []}
    assert _normalize_plan([{"column": "a"}]) == {"actions": [{"column": "a"}]}
    for bad in ("oops", 5, [1, 2], None):
        out = _normalize_plan(bad)
        assert out["actions"] == [] and "error" in out


@pytest.mark.parametrize("bad", ["oops", [1, 2], [{"column": "a", "action": "no_action", "reason": "r"}]])
def test_pipeline_survives_non_dict_llm_output(tmp_path, monkeypatch, bad):
    f = tmp_path / "t.csv"
    f.write_text("a,b\n1,2\n3,4\n")
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda profile: bad)   # bypass _normalize_plan on purpose
    result = pl.run_pipeline(str(f))
    assert len(result.cleaned_df) == 2


def test_loader_handles_latin1_bytes_after_50kb(tmp_path):
    f = tmp_path / "late.csv"
    f.write_bytes(b"a,b\n" + b"x,1\n" * 30000 + "café,2\n".encode("latin-1"))
    df = load_data(str(f))
    assert len(df) == 30001 and df["a"].iloc[-1] == "café"


def test_loader_reads_utf8_with_bom(tmp_path):
    f = tmp_path / "bom.csv"
    f.write_bytes("﻿name,city\nA,Zürich\n".encode("utf-8"))
    df = load_data(str(f))
    assert list(df.columns) == ["name", "city"] and df["city"].iloc[0] == "Zürich"


def test_report_written_as_utf8(tmp_path, monkeypatch):
    f = tmp_path / "t.csv"
    f.write_text("a,b\n1,2\n3,4\n")
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda p: {"actions": [
        {"column": "a", "action": "no_action", "reason": "x"},
        {"column": "a", "action": "drop_column", "reason": "x"}]})
    pl.run_and_save(str(f), str(tmp_path / "o.csv"), str(tmp_path / "r.md"))
    assert "—" in (tmp_path / "r.md").read_text(encoding="utf-8")
