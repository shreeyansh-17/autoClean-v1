"""
desktop/api.py — Complete Python API class exposed to the React frontend via PyWebView js_api.

Every public method on AutoCleanAPI is callable from JavaScript as:
    const result = await window.pywebview.api.method_name(args)

Rules:
  - Preserves all existing autoclean backend logic (loader, profiler, row_analyzer,
    issue_detector, llm_engine, validator, fallback, executor, report, pipeline).
  - Never exposes Groq API keys to JavaScript.
  - Runs long-running tasks (LLM planning, dataset execution) in background threads
    with non-blocking task status polling.
  - Converts all Pandas/NumPy objects (including NaN, Inf, Timestamps) to clean JSON primitives.
  - Maintains persistent cleaning history in .autoclean_history.json.
"""

from __future__ import annotations

import datetime
import json
import logging
import math
import os
import platform
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Existing autoclean backend imports
from autoclean.loader import load_data, save_data
from autoclean.placeholders import normalize_placeholders
from autoclean.profiler import profile_dataframe
from autoclean.row_analyzer import analyze_rows
from autoclean.issue_detector import detect_issues
from autoclean.llm_engine import get_cleaning_plan, repair_rejected_actions
from autoclean.validator import validate_plan, CleaningAction
from autoclean.fallback import build_fallback_plan
from autoclean.executor import execute_plan
from autoclean.postcheck import check_cleaned
from autoclean.report import generate_report
import config

log = logging.getLogger("autoclean.api")
HISTORY_FILE = Path.cwd() / ".autoclean_history.json"


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively clean data structures so they serialize to valid JSON without NaN/Inf/Timestamp errors."""
    if obj is None:
        return None
    if isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, pd.Series, np.ndarray)):
        return [_sanitize_for_json(v) for v in obj]
    if pd.isna(obj):
        return None
    return str(obj)


class DatasetSession:
    """Holds the active in-memory dataset, analysis, recommendations, and execution artifacts."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.file_path: str | None = None
        self.file_name: str | None = None
        self.file_size_kb: float = 0.0
        self.file_format: str | None = None
        self.original_df: pd.DataFrame | None = None
        self.normalized_df: pd.DataFrame | None = None
        self.placeholder_counts: dict | None = None
        self.profile: dict | None = None
        self.row_analysis: dict | None = None
        self.annotated_profile: dict | None = None
        self.recommendations: list[dict] = []  # list of action dicts with unique id & approved status
        self.cleaned_df: pd.DataFrame | None = None
        self.execution_log: list[dict] = []
        self.rejected_actions: list[dict] = []
        self.removed_rows: pd.DataFrame | None = None
        self.post_check: dict | None = None
        self.report_markdown: str | None = None
        self.plan_source: str = "llm"
        self.llm_error: str | None = None


class AutoCleanAPI:
    """
    JavaScript-to-Python bridge for the AutoClean desktop application.
    Exposed to the frontend as window.pywebview.api.
    """

    _window = None  # Injected by app.py after window creation

    def __init__(self) -> None:
        self.session = DatasetSession()
        self._tasks: dict[str, dict] = {}
        self._ensure_history_file()

    def _ensure_history_file(self) -> None:
        if not HISTORY_FILE.exists():
            try:
                HISTORY_FILE.write_text(json.dumps([]), encoding="utf-8")
            except Exception as e:
                log.warning("Could not initialize history file: %s", e)

    # ------------------------------------------------------------------
    # 1. System & Connectivity Check
    # ------------------------------------------------------------------

    def ping(self) -> dict:
        log.info("ping() called from JavaScript")
        return {
            "message": "pong",
            "app": "AutoClean Desktop",
            "version": "0.1.0",
            "python": sys.version,
            "platform": platform.platform(),
            "arch": platform.machine(),
        }

    def get_app_info(self) -> dict:
        return {
            "name": "AutoClean Desktop",
            "version": "0.1.0",
            "description": "AI-powered automated data cleaning for CSV, XLSX, and JSON datasets.",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.system(),
            "platform_release": platform.release(),
            "cwd": str(Path.cwd()),
        }

    def echo(self, payload: object) -> dict:
        return {
            "payload": payload,
            "echoed_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": "AutoCleanAPI.echo",
        }

    def get_settings(self) -> dict:
        """Returns safe settings without exposing sensitive raw API keys."""
        has_key = bool(config.GROQ_API_KEY)
        masked_key = ""
        if has_key:
            masked_key = f"{config.GROQ_API_KEY[:4]}...{config.GROQ_API_KEY[-4:]}" if len(config.GROQ_API_KEY) > 8 else "sk-****"

        return {
            "status": "ok",
            "groq_model": config.GROQ_MODEL,
            "llm_temperature": config.LLM_TEMPERATURE,
            "llm_max_retries": config.LLM_MAX_RETRIES,
            "send_sample_values": config.SEND_SAMPLE_VALUES,
            "max_prompt_chars": config.MAX_PROMPT_CHARS,
            "fallback_on_llm_failure": config.FALLBACK_ON_LLM_FAILURE,
            "has_groq_api_key": has_key,
            "masked_api_key": masked_key,
        }

    # ------------------------------------------------------------------
    # 2. Native File Picker Dialogs
    # ------------------------------------------------------------------

    def open_file_dialog(self) -> dict:
        """Opens native file picker for dataset files (CSV, XLSX, XLS, JSON)."""
        log.info("open_file_dialog() called")
        if self._window is None:
            raise RuntimeError("Window reference not set.")

        file_types = (
            "Supported Datasets (*.csv;*.xlsx;*.xls;*.json)",
            "CSV files (*.csv)",
            "Excel files (*.xlsx;*.xls)",
            "JSON files (*.json)",
            "All files (*.*)",
        )
        try:
            import webview
            result = self._window.create_file_dialog(
                dialog_type=webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=file_types,
            )
        except Exception as e:
            log.error("File dialog failed: %s", e)
            raise RuntimeError(f"Failed to open native file dialog: {e}")

        if not result:
            return {}

        path = Path(result[0])
        return {
            "path": str(path.resolve()),
            "name": path.name,
            "stem": path.stem,
            "suffix": path.suffix.lower().lstrip("."),
            "size_bytes": path.stat().st_size,
            "size_kb": round(path.stat().st_size / 1024, 2),
        }

    def save_file_dialog(self, default_name: str = "cleaned_dataset.csv", file_type: str = "csv") -> str | None:
        """Opens native save file dialog to pick an export destination."""
        log.info("save_file_dialog() called for %s", default_name)
        if self._window is None:
            raise RuntimeError("Window reference not set.")

        ext = file_type.lower().lstrip(".")
        if ext == "xlsx":
            filters = ("Excel Workbook (*.xlsx)", "All files (*.*)")
        elif ext == "json":
            filters = ("JSON file (*.json)", "All files (*.*)")
        elif ext == "md":
            filters = ("Markdown Report (*.md)", "All files (*.*)")
        else:
            filters = ("CSV file (*.csv)", "All files (*.*)")

        try:
            import webview
            result = self._window.create_file_dialog(
                dialog_type=webview.SAVE_DIALOG,
                save_filename=default_name,
                file_types=filters,
            )
            if result:
                return str(Path(result if isinstance(result, str) else result[0]).resolve())
        except Exception as e:
            log.error("Save file dialog error: %s", e)
        return None

    # ------------------------------------------------------------------
    # 3. Dataset Loading & Previews
    # ------------------------------------------------------------------

    def load_dataset(self, file_path: str) -> dict:
        """
        Loads dataset using autoclean.loader.load_data.
        Computes basic metadata, normalizes placeholders, and returns summary info.
        """
        log.info("load_dataset() called for: %s", file_path)
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            df = load_data(str(path))
            normalized_df, placeholder_counts = normalize_placeholders(df)

            self.session.reset()
            self.session.file_path = str(path.resolve())
            self.session.file_name = path.name
            self.session.file_format = path.suffix.lower().lstrip(".")
            self.session.file_size_kb = round(path.stat().st_size / 1024, 2)
            self.session.original_df = df
            self.session.normalized_df = normalized_df
            self.session.placeholder_counts = placeholder_counts

            columns = [str(c) for c in df.columns]
            sample_preview = self.get_dataset_preview(offset=0, limit=10)

            return {
                "status": "success",
                "file_name": self.session.file_name,
                "file_path": self.session.file_path,
                "file_format": self.session.file_format,
                "file_size_kb": self.session.file_size_kb,
                "row_count": len(df),
                "column_count": len(columns),
                "columns": columns,
                "preview": sample_preview.get("rows", []),
            }
        except Exception as e:
            log.error("Failed to load dataset: %s", e, exc_info=True)
            return {"status": "error", "error": str(e)}

    def get_dataset_preview(self, offset: int = 0, limit: int = 50, which: str = "original") -> dict:
        """Returns paginated actual rows with their individual cell values."""
        df = self.session.cleaned_df if which == "cleaned" else self.session.original_df
        if df is None:
            return {"columns": [], "rows": [], "total_rows": 0, "offset": offset, "limit": limit}

        total_rows = len(df)
        safe_offset = max(0, min(offset, total_rows))
        slice_df = df.iloc[safe_offset : safe_offset + limit]

        # Convert records into clean primitives
        records = []
        for idx, row in slice_df.iterrows():
            row_dict = {"_row_id": str(idx)}
            for col in df.columns:
                row_dict[str(col)] = _sanitize_for_json(row[col])
            records.append(row_dict)

        return {
            "columns": [str(c) for c in df.columns],
            "rows": records,
            "total_rows": total_rows,
            "offset": safe_offset,
            "limit": limit,
        }

    # ------------------------------------------------------------------
    # 4. Data Profiling & Issue Detection
    # ------------------------------------------------------------------

    def profile_dataset(self) -> dict:
        """
        Executes real data profiling and row-level issue analysis on the loaded dataset.
        Returns missing values, duplicates, outliers, types, and column statistics.
        """
        if self.session.original_df is None:
            raise ValueError("No dataset loaded. Call load_dataset() first.")

        df = self.session.normalized_df if self.session.normalized_df is not None else self.session.original_df

        # 1. Profile dataframe
        dataset_profile = profile_dataframe(df)
        self.session.profile = dataset_profile

        # 2. Row-level analysis
        row_analysis = analyze_rows(df)
        self.session.row_analysis = row_analysis

        # 3. Issue detection
        annotated = detect_issues(df, dataset_profile)
        annotated_profile = {
            "row_count": dataset_profile["row_count"],
            "column_count": dataset_profile["column_count"],
            "duplicate_row_count": dataset_profile["duplicate_row_count"],
            "dataset_issues": annotated["dataset_issues"],
            "row_analysis": row_analysis,
            "columns": annotated["columns"],
        }
        self.session.annotated_profile = annotated_profile

        # Build column stats list
        cols_summary = []
        for col_data in annotated_profile["columns"]:
            num_stats = col_data.get("numeric_stats") or {}
            cols_summary.append({
                "name": col_data["column"],
                "dtype": col_data["dtype"],
                "missing_count": col_data["missing_count"],
                "missing_pct": col_data["missing_pct"],
                "unique_count": col_data["unique_count"],
                "issues": col_data.get("issues_detected", []),
                "sample_values": col_data.get("sample_values", []),
                "is_numeric": bool(num_stats),
                "numeric_stats": {
                    "mean": num_stats.get("mean"),
                    "std": num_stats.get("std"),
                    "min": num_stats.get("min"),
                    "max": num_stats.get("max"),
                    "outlier_count": num_stats.get("outlier_count", 0),
                } if num_stats else None,
            })

        # Calculate type distribution percentages
        type_counts: dict[str, int] = {}
        for c in cols_summary:
            dt = c["dtype"].lower()
            if "int" in dt:
                cat = "Integer"
            elif "float" in dt:
                cat = "Float"
            elif "date" in dt or "time" in dt:
                cat = "Date"
            else:
                cat = "String"
            type_counts[cat] = type_counts.get(cat, 0) + 1

        total_cols = len(cols_summary) or 1
        type_distribution = [
            {"label": k, "count": f"{v} cols", "pct": round(v / total_cols * 100), "raw_count": v}
            for k, v in type_counts.items()
        ]

        # Calculate total missing cells
        total_missing_cells = sum(c["missing_count"] for c in cols_summary)
        total_cells = (dataset_profile["row_count"] * dataset_profile["column_count"]) or 1
        missing_cells_pct = round((total_missing_cells / total_cells) * 100, 2)

        return _sanitize_for_json({
            "status": "success",
            "file_name": self.session.file_name,
            "total_rows": dataset_profile["row_count"],
            "total_columns": dataset_profile["column_count"],
            "total_missing_cells": total_missing_cells,
            "missing_cells_pct": missing_cells_pct,
            "exact_duplicate_rows": row_analysis.get("exact_duplicate_rows", 0),
            "near_duplicate_rows": row_analysis.get("near_duplicate_rows_incl_exact", 0),
            "fully_empty_rows": row_analysis.get("fully_empty_rows", 0),
            "sparse_rows": row_analysis.get("sparse_rows_over_50pct_blank", 0),
            "dataset_issues": annotated_profile["dataset_issues"],
            "type_distribution": type_distribution,
            "columns": cols_summary,
            "row_analysis": row_analysis,
        })

    # ------------------------------------------------------------------
    # 5. AI Recommendations (Groq + Fallback)
    # ------------------------------------------------------------------

    def generate_recommendations(self) -> dict:
        """
        Asynchronously generates cleaning recommendations using Groq or fallback.
        Returns a task_id immediately so the UI stays responsive.
        """
        if self.session.original_df is None:
            raise ValueError("No dataset loaded.")

        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {"status": "running", "progress": 10, "result": None, "error": None}

        def worker() -> None:
            try:
                # Ensure profiled first
                if self.session.annotated_profile is None:
                    self.profile_dataset()

                annotated = self.session.annotated_profile
                self._tasks[task_id]["progress"] = 30

                # Privacy check: omit sample values if configured
                llm_input_profile = dict(annotated)
                if not config.SEND_SAMPLE_VALUES:
                    llm_input_profile["columns"] = [
                        {k: v for k, v in c.items() if k != "sample_values"}
                        for c in llm_input_profile["columns"]
                    ]

                raw_plan = get_cleaning_plan(llm_input_profile)
                llm_error = raw_plan.get("error") if isinstance(raw_plan, dict) else "Non-JSON response"
                self._tasks[task_id]["progress"] = 65

                known_cols = list(self.session.original_df.columns)
                validation_result = validate_plan(raw_plan, known_cols)
                plan_source = "llm"

                # Repair pass if rejected actions exist
                if validation_result.rejected and not llm_error:
                    repair = repair_rejected_actions(llm_input_profile, validation_result.rejected)
                    if repair.get("actions"):
                        fixed = validate_plan(repair, known_cols)
                        validation_result.valid_actions.extend(fixed.valid_actions)
                        plan_source = "llm+repair"

                # Fallback to rule-based plan if LLM failed
                if config.FALLBACK_ON_LLM_FAILURE and (llm_error or not validation_result.valid_actions):
                    fallback_plan = build_fallback_plan(annotated)
                    validation_result = validate_plan(fallback_plan, known_cols)
                    plan_source = "fallback"

                self.session.plan_source = plan_source
                self.session.llm_error = llm_error

                # Transform valid actions into structured recommendation items
                recs = []
                for idx, act in enumerate(validation_result.valid_actions):
                    rec_id = f"act_{idx + 1}"
                    col = act.column
                    act_type = act.action

                    # Determine estimated affected rows
                    affected_rows = 0
                    if col == "*" or act_type.startswith("drop_"):
                        if act_type == "drop_empty_rows":
                            affected_rows = self.session.row_analysis.get("fully_empty_rows", 0) if self.session.row_analysis else 0
                        elif act_type in ("drop_duplicates", "drop_near_duplicate_rows"):
                            affected_rows = self.session.row_analysis.get("exact_duplicate_rows", 0) if self.session.row_analysis else 0
                        elif act_type == "drop_sparse_rows":
                            affected_rows = self.session.row_analysis.get("sparse_rows_over_50pct_blank", 0) if self.session.row_analysis else 0
                        else:
                            affected_rows = len(self.session.original_df)
                    else:
                        col_item = next((c for c in self.session.profile["columns"] if c["column"] == col), None) if self.session.profile else None
                        if col_item:
                            if "impute" in act_type:
                                affected_rows = col_item.get("missing_count", 0)
                            elif act_type == "clip_outliers":
                                affected_rows = (col_item.get("numeric_stats") or {}).get("outlier_count", 0)
                            else:
                                affected_rows = len(self.session.original_df)

                    # Determine priority
                    priority = "medium"
                    if act_type in ("drop_empty_rows", "drop_duplicates", "fix_dtype") or affected_rows > 100:
                        priority = "high"
                    elif act_type in ("strip_whitespace", "no_action"):
                        priority = "low"

                    rec_item = {
                        "id": rec_id,
                        "action": act.action,
                        "column": act.column,
                        "reason": act.reason,
                        "priority": priority,
                        "affected_rows": affected_rows,
                        "confidence": 95 if plan_source == "llm" else 88,
                        "approved": True,  # approved by default
                        "parameters": {
                            "target_format": act.target_format,
                            "target_dtype": act.target_dtype,
                            "method": act.method,
                            "multiplier": act.multiplier,
                            "casing": act.casing,
                            "fill_value": act.fill_value,
                            "threshold": act.threshold,
                            "min_outlier_cols": act.min_outlier_cols,
                        },
                        "action_model": act,
                    }
                    recs.append(rec_item)

                self.session.recommendations = recs
                self._tasks[task_id]["progress"] = 100
                self._tasks[task_id]["status"] = "completed"
                self._tasks[task_id]["result"] = _sanitize_for_json({
                    "plan_source": plan_source,
                    "llm_error": llm_error,
                    "recommendations": [
                        {k: v for k, v in r.items() if k != "action_model"}
                        for r in recs
                    ],
                })
            except Exception as e:
                log.error("Worker failed in generate_recommendations: %s", e, exc_info=True)
                self._tasks[task_id]["status"] = "failed"
                self._tasks[task_id]["error"] = str(e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return {"task_id": task_id, "status": "started"}

    def get_task_status(self, task_id: str) -> dict:
        """Polls status of asynchronous background tasks."""
        task = self._tasks.get(task_id)
        if not task:
            return {"status": "not_found", "error": "Invalid task ID"}
        return task

    def update_action_status(self, action_id: str, approved: bool) -> dict:
        """Toggles approval/rejection for an individual recommendation action."""
        for r in self.session.recommendations:
            if r["id"] == action_id:
                r["approved"] = approved
                return {"status": "success", "id": action_id, "approved": approved}
        return {"status": "error", "message": f"Action ID '{action_id}' not found"}

    # ------------------------------------------------------------------
    # 6. Cleaning Execution & Diffs
    # ------------------------------------------------------------------

    def execute_cleaning(self, selected_action_ids: list[str] | None = None) -> dict:
        """
        Executes approved cleaning actions in a background thread.
        Generates before/after slices, collects removed rows, and generates markdown report.
        """
        if self.session.original_df is None:
            raise ValueError("No dataset loaded.")

        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {"status": "running", "progress": 10, "result": None, "error": None}

        def worker() -> None:
            try:
                # 1. Determine actions to execute
                actions_to_execute = []
                for rec in self.session.recommendations:
                    is_selected = (
                        (selected_action_ids is None and rec.get("approved", True))
                        or (selected_action_ids is not None and rec["id"] in selected_action_ids)
                    )
                    if is_selected and "action_model" in rec:
                        actions_to_execute.append(rec["action_model"])

                self._tasks[task_id]["progress"] = 30

                # 2. Execute plan
                df_to_clean = self.session.normalized_df.copy() if self.session.normalized_df is not None else self.session.original_df.copy()
                cleaned_df, execution_log = execute_plan(df_to_clean, actions_to_execute)

                self._tasks[task_id]["progress"] = 65

                # 3. Collect removed rows
                from autoclean.pipeline import _collect_removed_rows
                removed_rows = _collect_removed_rows(self.session.original_df, execution_log)
                post_check = check_cleaned(cleaned_df)

                # 4. Generate report
                report_markdown = generate_report(
                    original_df=self.session.original_df,
                    cleaned_df=cleaned_df,
                    execution_log=execution_log,
                    rejected_actions=self.session.rejected_actions,
                    llm_error=self.session.llm_error,
                    row_analysis=self.session.row_analysis,
                    removed_rows=removed_rows,
                    placeholder_counts=self.session.placeholder_counts,
                    post_check=post_check,
                    plan_source=self.session.plan_source,
                )

                self.session.cleaned_df = cleaned_df
                self.session.execution_log = execution_log
                self.session.removed_rows = removed_rows
                self.session.post_check = post_check
                self.session.report_markdown = report_markdown

                # 5. Persist run to local history
                self._append_to_history(
                    file_name=self.session.file_name or "dataset",
                    original_rows=len(self.session.original_df),
                    cleaned_rows=len(cleaned_df),
                    issues_resolved=len([e for e in execution_log if e.get("status") == "applied"]),
                    removed_rows_count=len(removed_rows),
                    report_markdown=report_markdown,
                )

                self._tasks[task_id]["progress"] = 100
                self._tasks[task_id]["status"] = "completed"
                self._tasks[task_id]["result"] = self.get_cleaning_results()
            except Exception as e:
                log.error("Cleaning execution failed: %s", e, exc_info=True)
                self._tasks[task_id]["status"] = "failed"
                self._tasks[task_id]["error"] = str(e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return {"task_id": task_id, "status": "started"}

    def get_cleaning_results(self) -> dict:
        """Returns structured comparison of cleaning results."""
        if self.session.original_df is None or self.session.cleaned_df is None:
            return {"status": "none", "message": "No cleaning run completed yet."}

        orig_len = len(self.session.original_df)
        clean_len = len(self.session.cleaned_df)
        removed_count = len(self.session.removed_rows) if self.session.removed_rows is not None else 0
        applied_entries = [e for e in self.session.execution_log if e.get("status") == "applied"]

        # Build before/after comparison preview (first 5 rows)
        common_cols = [c for c in self.session.original_df.columns if c in self.session.cleaned_df.columns][:6]
        before_rows = []
        after_rows = []

        sample_indices = list(self.session.cleaned_df.index[:5])
        for idx in sample_indices:
            b_dict = {"_row_id": str(idx)}
            a_dict = {"_row_id": str(idx)}
            for col in common_cols:
                b_val = self.session.original_df.loc[idx, col] if idx in self.session.original_df.index else None
                a_val = self.session.cleaned_df.loc[idx, col]
                b_dict[col] = _sanitize_for_json(b_val)
                a_dict[col] = _sanitize_for_json(a_val)
            before_rows.append(b_dict)
            after_rows.append(a_dict)

        # Simplified change log
        change_log = []
        for entry in self.session.execution_log:
            change_log.append({
                "action": entry.get("action"),
                "column": entry.get("column"),
                "reason": entry.get("reason"),
                "status": entry.get("status"),
                "detail": {k: v for k, v in entry.get("detail", {}).items() if not str(k).startswith("_")},
            })

        return _sanitize_for_json({
            "status": "success",
            "file_name": self.session.file_name,
            "original_rows": orig_len,
            "cleaned_rows": clean_len,
            "rows_removed": removed_count,
            "issues_resolved": len(applied_entries),
            "execution_log": change_log,
            "before_rows": before_rows,
            "after_rows": after_rows,
            "columns": common_cols,
            "post_check": self.session.post_check,
            "report_markdown": self.session.report_markdown,
        })

    # ------------------------------------------------------------------
    # 7. Dataset Exporting & Reports
    # ------------------------------------------------------------------

    def export_dataset(self, export_type: str = "cleaned", target_path: str | None = None) -> dict:
        """
        Exports cleaned dataset, dropped rows, or markdown report to disk.
        If target_path is not given, prompts user with native save dialog.
        """
        if self.session.cleaned_df is None and export_type == "cleaned":
            raise ValueError("No cleaned dataset available to export.")

        stem = Path(self.session.file_path).stem if self.session.file_path else "dataset"

        if export_type == "cleaned":
            default_name = f"{stem}_cleaned.csv"
            ext = "csv"
            df_to_save = self.session.cleaned_df
        elif export_type == "removed_rows":
            default_name = f"{stem}_removed_rows.csv"
            ext = "csv"
            df_to_save = self.session.removed_rows
        elif export_type == "report":
            default_name = f"{stem}_report.md"
            ext = "md"
            df_to_save = None
        else:
            raise ValueError(f"Unknown export type: {export_type}")

        if not target_path:
            target_path = self.save_file_dialog(default_name=default_name, file_type=ext)
            if not target_path:
                return {"status": "cancelled"}

        dest = Path(target_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if export_type == "report":
            with open(dest, "w", encoding="utf-8") as f:
                f.write(self.session.report_markdown or "# AutoClean Report\nNo data.")
        else:
            if df_to_save is not None:
                save_data(df_to_save, str(dest))
            else:
                return {"status": "error", "message": "Nothing to save."}

        return {
            "status": "success",
            "saved_path": str(dest.resolve()),
            "file_size_kb": round(dest.stat().st_size / 1024, 2),
        }

    # ------------------------------------------------------------------
    # 8. History Persistence
    # ------------------------------------------------------------------

    def _append_to_history(
        self,
        file_name: str,
        original_rows: int,
        cleaned_rows: int,
        issues_resolved: int,
        removed_rows_count: int,
        report_markdown: str | None,
    ) -> None:
        history = []
        if HISTORY_FILE.exists():
            try:
                history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                history = []

        record = {
            "id": len(history) + 1,
            "name": file_name,
            "type": file_name.split(".")[-1].upper() if "." in file_name else "CSV",
            "original_rows": original_rows,
            "cleaned_rows": cleaned_rows,
            "issues": issues_resolved,
            "removed_rows": removed_rows_count,
            "status": "Completed",
            "date": datetime.datetime.now().strftime("%b %d, %Y %H:%M"),
            "report_summary": (report_markdown or "")[:500],
        }
        history.insert(0, record)
        try:
            HISTORY_FILE.write_text(json.dumps(history[:50], indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("Failed to write history: %s", e)

    def get_cleaning_history(self) -> dict:
        """Returns persisted cleaning history."""
        if HISTORY_FILE.exists():
            try:
                data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                return {"status": "success", "records": data}
            except Exception as e:
                return {"status": "error", "message": str(e), "records": []}
        return {"status": "success", "records": []}


# Deferred import for pywebview constants if installed
try:
    import webview  # noqa: F401
except ImportError:
    pass
