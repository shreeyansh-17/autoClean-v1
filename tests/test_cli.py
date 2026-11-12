from typer.testing import CliRunner

import autoclean.pipeline as pl
import cli

runner = CliRunner()
CSV = "name,age\nA,30\nA,30\n,\nB,\n"


def _run(tmp_path, monkeypatch, *extra, plan=None):
    f = tmp_path / "in.csv"
    f.write_text(CSV)
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda p: plan or {"actions": [], "error": "GROQ_API_KEY not set"})
    return runner.invoke(cli.app, [str(f), *extra]), f


def test_cli_writes_cleaned_report_and_removed_rows(tmp_path, monkeypatch):
    result, f = _run(tmp_path, monkeypatch)
    assert result.exit_code == 0, result.output
    assert (tmp_path / "in_cleaned.csv").exists() and (tmp_path / "in_report.md").exists()
    assert (tmp_path / "in_removed_rows.csv").exists()
    assert "LLM warning" in result.output and "Rows: 4 -> 2" in result.output.replace("\n", " ")


def test_cli_custom_paths(tmp_path, monkeypatch):
    result, _ = _run(tmp_path, monkeypatch, "-o", str(tmp_path / "o.csv"), "-r", str(tmp_path / "r.md"),
                     "--removed-rows", str(tmp_path / "rm.csv"))
    assert result.exit_code == 0 and (tmp_path / "o.csv").exists() and (tmp_path / "rm.csv").exists()


def test_cli_missing_file_exits_nonzero(tmp_path):
    result = runner.invoke(cli.app, [str(tmp_path / "nope.csv")])
    assert result.exit_code == 1 and "File not found" in result.output


def test_cli_xls_input_defaults_to_xlsx_output(tmp_path, monkeypatch):
    import pandas as pd
    monkeypatch.setattr(pl, "get_cleaning_plan", lambda p: {"actions": []})
    monkeypatch.setattr(pl, "load_data", lambda path: pd.DataFrame({"a": [1, 2]}))  # no xlrd needed in the test
    result = runner.invoke(cli.app, [str(tmp_path / "book.xls")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "book_cleaned.xlsx").exists()
