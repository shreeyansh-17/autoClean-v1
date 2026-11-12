"""Handles the Groq API call: builds the prompt from the issue-annotated profile,
requests a structured JSON cleaning plan, and retries on rate limits or bad JSON.
"""
from __future__ import annotations

import json
import time

from groq import Groq, APIStatusError

import config
from autoclean.validator import ALLOWED_ACTIONS

SYSTEM_PROMPT = f"""You are a data cleaning assistant. You will be given a JSON \
profile of a dataset (column stats and detected issues, NOT raw data).

Decide what cleaning actions to take. Respond with ONLY a JSON object, no \
preamble, no markdown code fences, in exactly this shape:

{{
  "actions": [
    {{
      "column": "<column name>",
      "action": "<one of: {', '.join(sorted(ALLOWED_ACTIONS))}>",
      "reason": "<short reason, one sentence>",
      "target_format": "<optional, one of: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, DD-MM-YYYY, YYYY/MM/DD, DD-Mon-YYYY; only for standardize_date_format>",
      "dayfirst": "<optional true/false, only for standardize_date_format; omit to infer from the data>",
      "method": "<optional, 'iqr' or 'zscore', only for clip_outliers>",
      "multiplier": "<optional number > 0, only for clip_outliers; default 3 (IQR multiplier or z cutoff)>",
      "fill_value": "<optional, only for impute_constant>",
      "target_dtype": "<optional, one of: int, float, str, bool; only for fix_dtype>",
      "casing": "<optional, 'auto'|'lower'|'upper'|'title', only for normalize_casing; prefer 'auto'>",
      "threshold": "<optional number 0-1, only for drop_sparse_rows: max fraction of blank cells a row may have>",
      "min_outlier_cols": "<optional integer >= 1, only for drop_outlier_rows>"
    }}
  ]
}}

Row-wise actions work on whole rows, so set "column" to "*" for them:
drop_empty_rows, drop_sparse_rows, drop_duplicates, drop_near_duplicate_rows, \
drop_outlier_rows. The profile includes a "row_analysis" section with row-level \
counts (fully empty rows, sparse rows, duplicates, outlier rows). You choose \
which row actions to apply and their strictness; the code picks the exact rows.

Rules:
- Only propose one action per column per pass unless clearly independent (e.g. \
strip_whitespace AND normalize_casing can both apply to the same text column).
- If a column has no real issues, either omit it or use "no_action".
- Prefer imputation over dropping rows unless the column looks like a required \
identifier (email, id, key) with missing values.
- Use "drop_rows_if_missing" sparingly — it deletes data.
- Keep "reason" short and specific to the stats/issues given for that column.
- Do not invent columns that are not in the profile.
- normalize_casing: use casing "auto" (merges case-variants such as Dell/DELL into the \
most common spelling). Never use "title"/"upper"/"lower" on columns holding codes, model \
names or units (CPU/GPU strings, SKUs) since that corrupts them.
- If a column has the issue "numeric_stored_as_text" use fix_dtype with target_dtype "float" \
(or "int" for whole numbers).
- If a column has the issue "numeric_values_with_units" (e.g. 8GB, 1.37kg) use \
extract_number to turn it into a number; do NOT drop the column.
- clip_outliers is lossy: only use it when outliers look like errors, not genuine \
high values (prices, salaries); otherwise leave the column alone.
- Row-wise rules: always use drop_empty_rows when row_analysis shows fully empty \
rows (never impute them into fake records). Use drop_duplicates for exact \
duplicates and drop_near_duplicate_rows only if near-duplicates exceed exact ones. \
Use drop_sparse_rows only when non-empty rows are mostly blank (see \
rows_by_blank_cell_count); prefer imputing a few missing cells over dropping the row. \
Use drop_outlier_rows only with min_outlier_cols >= 2 unless the data is clearly corrupt, \
since it deletes whole records."""


def _build_user_prompt(annotated_profile: dict) -> str:
    return (
        "Dataset profile (stats and detected issues only, no raw rows):\n\n"
        + json.dumps(annotated_profile, indent=2)
    )


def _extract_json(text: str) -> dict:
    """Strip markdown fences if present and parse JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


def _normalize_plan(parsed) -> dict:
    """Coerce whatever JSON the model produced into {"actions": [...]}.

    A bare list of action objects is accepted; anything else (string, number,
    list of non-objects) becomes an empty plan with an error so the pipeline can
    continue instead of crashing.
    """
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list) and all(isinstance(a, dict) for a in parsed):
        return {"actions": parsed}
    return {"actions": [], "error": f"LLM returned unexpected JSON type: {type(parsed).__name__}"}


def _call_llm(system_prompt: str, user_prompt: str) -> dict:
    """One LLM round-trip with retries. Returns a plan dict, or
    {"actions": [], "error": "...", "status_code": int|None} on failure."""
    if not config.GROQ_API_KEY:
        return {"actions": [], "error": "GROQ_API_KEY not set", "status_code": None}

    client = Groq(api_key=config.GROQ_API_KEY)
    last_error, status = "unknown error", None
    for attempt in range(config.LLM_MAX_RETRIES):
        last_attempt = attempt == config.LLM_MAX_RETRIES - 1
        try:
            response = client.chat.completions.create(
                model=config.GROQ_MODEL,
                temperature=config.LLM_TEMPERATURE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            return _normalize_plan(_extract_json(response.choices[0].message.content))

        except APIStatusError as e:
            last_error, status = f"Groq API error: {e}", e.status_code
            if e.status_code == 429 and not last_attempt:
                time.sleep(2 ** attempt)  # rate limited: back off and retry
                continue
            break  # 429 on the last attempt, or any other API error (incl. 413): not retryable here

        except json.JSONDecodeError as e:
            last_error = f"Malformed JSON from LLM: {e}"
            if not last_attempt:
                time.sleep(1)

        except Exception as e:  # network errors, etc.
            last_error = f"Unexpected error calling Groq: {e}"
            if not last_attempt:
                time.sleep(1)

    return {"actions": [], "error": last_error, "status_code": status}


def _profile_size(profile: dict) -> int:
    return len(json.dumps(profile))


def _plan_columns(profile: dict, columns: list[dict], include_row_analysis: bool) -> dict:
    """Plan for a subset of columns. Splits in half and retries on 413 (payload too large)."""
    sub = {k: v for k, v in profile.items() if k not in ("columns", "row_analysis")}
    if include_row_analysis and "row_analysis" in profile:
        sub["row_analysis"] = profile["row_analysis"]
    sub["columns"] = columns
    result = _call_llm(SYSTEM_PROMPT, _build_user_prompt(sub))

    if result.get("status_code") == 413 and len(columns) > 1:
        mid = len(columns) // 2
        left = _plan_columns(profile, columns[:mid], include_row_analysis)
        right = _plan_columns(profile, columns[mid:], False)
        return _merge_plans([left, right])
    return result


def _merge_plans(plans: list[dict]) -> dict:
    actions, seen, errors = [], set(), []
    for plan in plans:
        for a in plan.get("actions", []):
            key = (str(a.get("column")), str(a.get("action")))
            if key in seen and a.get("action") != "no_action":
                continue  # e.g. drop_empty_rows proposed by several batches
            seen.add(key)
            actions.append(a)
        if plan.get("error"):
            errors.append(plan["error"])
    merged = {"actions": actions}
    if errors:
        merged["error"] = "; ".join(dict.fromkeys(errors))
    return merged


def get_cleaning_plan(annotated_profile: dict) -> dict:
    """Ask the LLM for a cleaning plan. Large profiles are sent in column batches
    (config.MAX_PROMPT_CHARS) so wide datasets stay within Groq's free-tier limits.

    On failure returns {"actions": [], "error": "<reason>"} (partial plans are kept when
    only some batches fail) so the pipeline can fall back instead of crashing.
    """
    if not config.GROQ_API_KEY:
        return {"actions": [], "error": "GROQ_API_KEY not set"}

    columns = annotated_profile.get("columns", [])
    if _profile_size(annotated_profile) <= config.MAX_PROMPT_CHARS or len(columns) <= 1:
        return _plan_columns(annotated_profile, columns, True)

    # Greedy batching by serialized size.
    batches, current, size = [], [], 0
    for col in columns:
        col_size = len(json.dumps(col))
        if current and size + col_size > config.MAX_PROMPT_CHARS:
            batches.append(current)
            current, size = [], 0
        current.append(col)
        size += col_size
    if current:
        batches.append(current)

    plans = [_plan_columns(annotated_profile, b, i == 0) for i, b in enumerate(batches)]
    return _merge_plans(plans)


def repair_rejected_actions(annotated_profile: dict, rejected: list[dict]) -> dict:
    """One follow-up call: show the LLM which of its actions were rejected and why, and ask
    for corrected versions only. Returns a plan dict (possibly empty)."""
    if not rejected or not config.GROQ_API_KEY:
        return {"actions": []}
    feedback = [{"rejected_action": r.get("raw"), "error": str(r.get("error"))[:300]} for r in rejected[:20]]
    columns = [c["column"] for c in annotated_profile.get("columns", [])]
    user = (
        "Some actions in your previous plan were rejected by the validator. Return ONLY corrected "
        "versions of those actions (same JSON shape), or omit one if it cannot be fixed.\n\n"
        f"Valid column names: {json.dumps(columns)}\n\n"
        f"Rejected actions and errors:\n{json.dumps(feedback, indent=2, default=str)}"
    )
    return _call_llm(SYSTEM_PROMPT, user)
