import json

import pandas as pd
import pytest

import autoclean.llm_engine as le
import autoclean.pipeline as pl
import config
from autoclean.fallback import build_fallback_plan
from autoclean.loader import load_data, save_data
from autoclean.postcheck import check_cleaned
from autoclean.report import generate_report
from autoclean.validator import validate_plan


# ---------- fake Groq client -------------------------------------------------
class _Resp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


class FakeStatusError(Exception):
    def __init__(self, status):
        super().__init__(f"status {status}")
        self.status_code = status


def install_fake_groq(monkeypatch, replies):
    """replies: list of str (JSON content) or int (HTTP status to raise); consumed in order."""
    calls = []

    class FakeClient:
        def __init__(self, api_key):
            self.chat = type("Chat", (), {"completions": self})()

        def create(self, **kw):
            calls.append(kw)
            r = replies.pop(0) if replies else json.dumps({"actions": []})
            if isinstance(r, int):
                raise FakeStatusError(r)
            return _Resp(r)

    monkeypatch.setattr(le, "Groq", FakeClient)
    monkeypatch.setattr(le, "APIStatusError", FakeStatusError)
    monkeypatch.setattr(le.time, "sleep", lambda s: None)
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    return calls


def _profile(n_cols=3):
    return {"row_count": 10, "column_count": n_cols, "duplicate_row_count": 0, "dataset_issues": [],
            "row_analysis": {"fully_empty_rows": 0},
            "columns": [{"column": f"c{i}", "dtype": "str", "sample_values": ["x" * 50] * 5, "issues_detected": []}
                        for i in range(n_cols)]}


# ---------- llm_engine ---------------------------------------------------------
def test_llm_success_and_code_fence(monkeypatch):
    install_fake_groq(monkeypatch, ['```json\n{"actions": [{"column": "c0", "action": "no_action", "reason": "r"}]}\n```'])
    plan = le.get_cleaning_plan(_profile())
    assert plan["actions"][0]["column"] == "c0" and "error" not in plan


def test_llm_missing_key_returns_error(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    assert le.get_cleaning_plan(_profile()) == {"actions": [], "error": "GROQ_API_KEY not set"}


def test_llm_retries_on_429_then_succeeds(monkeypatch):
    calls = install_fake_groq(monkeypatch, [429, 429, json.dumps({"actions": []})])
    plan = le.get_cleaning_plan(_profile())
    assert len(calls) == 3 and "error" not in plan


def test_llm_gives_up_after_max_retries_on_bad_json(monkeypatch):
    calls = install_fake_groq(monkeypatch, ["not json"] * 5)
    plan = le.get_cleaning_plan(_profile())
    assert len(calls) == config.LLM_MAX_RETRIES and "Malformed JSON" in plan["error"]


def test_llm_non_retryable_error_stops_immediately(monkeypatch):
    calls = install_fake_groq(monkeypatch, [401])
    plan = le.get_cleaning_plan(_profile())
    assert len(calls) == 1 and "error" in plan


def test_large_profile_is_split_into_batches_and_row_analysis_sent_once(monkeypatch):
    calls = install_fake_groq(monkeypatch, [])
    monkeypatch.setattr(config, "MAX_PROMPT_CHARS", 1500)
    le.get_cleaning_plan(_profile(n_cols=20))
    assert len(calls) > 1
    prompts = [c["messages"][1]["content"] for c in calls]
    assert sum("row_analysis" in p for p in prompts) == 1
    sent_cols = [name for p in prompts for name in [f"c{i}" for i in range(20)] if f'"column": "{name}"' in p]
    assert sorted(sent_cols) == sorted(f"c{i}" for i in range(20))          # every column covered exactly once


def test_413_splits_the_request_and_merges_results(monkeypatch):
    act = lambda col: json.dumps({"actions": [{"column": col, "action": "strip_whitespace", "reason": "r"}]})
    calls = install_fake_groq(monkeypatch, [413, act("c0"), act("c2")])
    plan = le.get_cleaning_plan(_profile(n_cols=4))
    assert len(calls) == 3 and [a["column"] for a in plan["actions"]] == ["c0", "c2"]


def test_repair_call_contains_errors_and_valid_columns(monkeypatch):
    calls = install_fake_groq(monkeypatch, [json.dumps({"actions": []})])
    le.repair_rejected_actions(_profile(), [{"raw": {"column": "ghost"}, "error": "Unknown column 'ghost'"}])
    text = calls[0]["messages"][1]["content"]
    assert "Unknown column" in text and '"c0"' in text


# ---------- pipeline: fallback, repair, privacy ----------------------------------
def _csv(tmp_path, text):
    f = tmp_path / "d.csv"
    f.write_text(text)
    return str(f)


MESSY = "name,ram,age\n Dell ,8GB,30\nDELL,16GB,\ndell,8GB,40\n,,\nHP,8GB,50\nHP,8GB,50\n"


def test_pipeline_falls_back_to_rules_when_llm_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda p: {"actions": [], "error": "GROQ_API_KEY not set"})
    r = pl.run_pipeline(_csv(tmp_path, MESSY))
    assert r.plan_source == "fallback"
    assert len(r.cleaned_df) == 4                                  # blank row and duplicate row dropped
    assert r.cleaned_df["ram"].tolist() == [8.0, 16.0, 8.0, 8.0]    # units extracted
    assert r.cleaned_df["age"].isna().sum() == 0                    # imputed
    assert "rule-based fallback" in r.report_markdown


def test_fallback_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda p: {"actions": [], "error": "boom"})
    monkeypatch.setattr(config, "FALLBACK_ON_LLM_FAILURE", False)
    r = pl.run_pipeline(_csv(tmp_path, MESSY))
    assert r.plan_source == "llm" and len(r.cleaned_df) == len(r.original_df)


def test_fallback_plan_is_conservative():
    prof = _profile(2)
    prof["columns"][0].update(issues_detected=["constant_column", "outliers_present"], missing_count=6)
    prof["columns"][1].update(issues_detected=["missing_values"], missing_count=1)
    actions = build_fallback_plan(prof)["actions"]
    kinds = {a["action"] for a in actions}
    assert kinds == {"impute_mode"} and actions[0]["column"] == "c1"   # no drops/clips; 60% missing not imputed


def test_rejected_actions_are_repaired_once(tmp_path, monkeypatch):
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda p: {"actions": [
        {"column": "Name", "action": "strip_whitespace", "reason": "typo in column name"}]})
    seen = {}

    def repair(profile, rejected):
        seen["rejected"] = rejected
        return {"actions": [{"column": "name", "action": "strip_whitespace", "reason": "fixed"}]}

    monkeypatch.setattr(pl, "repair_rejected_actions", repair)
    r = pl.run_pipeline(_csv(tmp_path, MESSY))
    assert "Unknown column" in seen["rejected"][0]["error"]
    assert r.plan_source == "llm+repair" and r.rejected_actions == []
    assert r.cleaned_df["name"].iloc[0] == "Dell"


def test_unrepairable_rejection_stays_in_report(tmp_path, monkeypatch):
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda p: {"actions": [
        {"column": "ghost", "action": "strip_whitespace", "reason": "r"}]})
    monkeypatch.setattr(pl, "repair_rejected_actions", lambda p, r: {"actions": []})
    r = pl.run_pipeline(_csv(tmp_path, MESSY))
    assert len(r.rejected_actions) == 1 and "Rejected by Validator" in r.report_markdown


def test_sample_values_not_sent_in_privacy_mode(tmp_path, monkeypatch):
    sent = {}
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda p: sent.update(p) or {"actions": []})
    monkeypatch.setattr(config, "SEND_SAMPLE_VALUES", False)
    pl.run_pipeline(_csv(tmp_path, MESSY))
    assert all("sample_values" not in c for c in sent["columns"])
    monkeypatch.setattr(config, "SEND_SAMPLE_VALUES", True)
    pl.run_pipeline(_csv(tmp_path, MESSY))
    assert all("sample_values" in c for c in sent["columns"])


# ---------- post-check & report ----------------------------------------------------
def test_postcheck_reports_remaining_issues_and_clean_data():
    dirty = pd.DataFrame({"a": ["x", "x", None, " y"], "b": [1, 1, None, 3]})
    res = check_cleaned(dirty)
    assert not res["clean"] and res["row_issues"]["exact_duplicate_rows"] == 1 and "a" in res["column_issues"]
    assert check_cleaned(pd.DataFrame({"a": ["x", "y", "z", "w"], "b": [3, 1, 4, 9]}))["clean"] is True
    assert check_cleaned(pd.DataFrame())["clean"] is False


def test_pipeline_report_has_post_check_section(tmp_path, monkeypatch):
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda p: {"actions": []})
    r = pl.run_pipeline(_csv(tmp_path, MESSY))
    assert "## Post-clean Check" in r.report_markdown and r.post_check["row_issues"]


def test_report_without_optional_sections_still_renders():
    df = pd.DataFrame({"a": [1]})
    md = generate_report(df, df, [], [], None)
    assert md.startswith("# AutoClean Report") and "No actions were applied" in md


# ---------- loader ------------------------------------------------------------------
def test_loader_formats_roundtrip_and_errors(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    for name in ("t.csv", "t.xlsx", "t.json"):
        save_data(df, str(tmp_path / name))
        assert load_data(str(tmp_path / name)).shape == (2, 2)
    with pytest.raises(FileNotFoundError):
        load_data(str(tmp_path / "missing.csv"))
    (tmp_path / "x.txt").write_text("a")
    with pytest.raises(ValueError, match="Unsupported"):
        load_data(str(tmp_path / "x.txt"))
    (tmp_path / "empty.csv").write_text("a,b\n")
    with pytest.raises(ValueError, match="no data"):
        load_data(str(tmp_path / "empty.csv"))


def test_xls_output_gives_clear_error(tmp_path):
    with pytest.raises(ValueError, match="xlsx"):
        save_data(pd.DataFrame({"a": [1]}), str(tmp_path / "o.xls"))


def test_fully_numeric_text_column_is_detected_and_converted_by_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda p: {"actions": [], "error": "x"})
    f = tmp_path / "n.csv"
    f.write_text('size,label\n"13.3",a\n"15.6",b\n"14.0",c\n')
    f.write_text("size,label\n13.3 ,a\n15.6 ,b\n 14.0,c\n")   # padding keeps the column text-typed
    r = pl.run_pipeline(str(f))
    assert pd.api.types.is_numeric_dtype(r.cleaned_df["size"]) and r.cleaned_df["size"].tolist() == [13.3, 15.6, 14.0]
