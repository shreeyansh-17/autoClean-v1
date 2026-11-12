# Architecture: AutoClean — LLM-Driven Automated Data Cleaning

## 1. Overview

AutoClean ingests a raw dataset (CSV/Excel/JSON), profiles it statistically — per column **and per row** — sends a **compact summary** of detected issues to an LLM (Groq's free API), receives a structured **cleaning plan** back, executes that plan with deterministic code, and outputs a cleaned dataset, an audit report, and a CSV of any rows it removed.

The LLM never receives the dataset. It sees aggregated statistics, issue tags, row-level *counts*, and (optionally) a handful of sample values per column, and it returns *decisions*. All data manipulation happens in pandas, which keeps the LLM cheap, fast, and free-tier-friendly, and makes every change auditable.

**Safety principle:** the LLM can *suggest*; only validated, allow-listed actions ever run, and the code — not the LLM — chooses which rows/values are touched.

---

## 2. High-Level Flow

```
Raw File (CSV/XLSX/JSON)
        │
        ▼
 [1] Loader               → DataFrame (encoding fallback chain)
        │
        ▼
 [1b] Placeholder step    → '?', 'N/A', '--' ... → real missing values
        │
        ▼
 [2] Profiler             → per-column stats, dtypes, outliers, samples
 [2b] Row Analyzer        → empty / sparse / duplicate / near-duplicate / outlier rows
        │
        ▼
 [3] Issue Detector       → rule-based issue tags per column
        │
        ▼
 [4] LLM Decision Engine  → compact JSON profile → Groq → JSON action plan
        │                    (batched for wide data; 429/413 handling)
        ▼
 [5] Plan Validator       → schema + allow-list + parameter checks
        │                    rejected actions → re-prompted once
        ▼                    LLM failed? → rule-based fallback plan
 [6] Cleaning Executor    → row actions first, then column actions (pandas)
        │
        ▼
 [7] Post-clean Check     → re-profile the result, list remaining issues
        │
        ▼
 [8] Report Generator     → markdown audit report
        │
        ▼
Cleaned file + report.md + removed_rows.csv
```

---

## 3. Components

### 3.1 Data Loader (`loader.py`)
- Reads CSV, XLSX/XLS (xlrd), or JSON into a DataFrame; writes CSV, XLSX, JSON (`.xls` output is rejected with a clear message).
- CSV: delimiter sniffing, and an encoding chain (`utf-8-sig` → chardet guess → `cp1252` → `latin-1`) tried against the **whole** file, because chardet only inspects the first 50 KB.
- The untouched original is kept for diffing and for the removed-rows file.

### 3.2 Placeholder normalisation (`placeholders.py`)
Converts strings that mean "no value" (`?`, `??`, `-`, `--`, `n/a`, `#n/a`, `null`, `nan`, `nil`, `missing`) to real NaN before anything else looks at the data. The list is deliberately conservative: `none`, `na`, `unknown` can be genuine categories and are left alone. Counts are listed in the report.

### 3.3 Profiler (`profiler.py`)
Per-column JSON: dtype, missing count/%, unique count, up to `MAX_SAMPLE_VALUES` sample values (can be disabled), numeric stats and outlier count, and how numeric-looking a text column is. Dataset-level: row count, duplicate count (ignoring row-counter columns).

### 3.4 Row Analyzer (`row_analyzer.py`)
Row-level view of the data, used both for the LLM summary (counts only) and by the executor to select rows:
- **Empty rows** (every cell blank) and **sparse rows** (> threshold blank).
- **Exact duplicates** and **near-duplicates** (ignoring case, spacing, `8` vs `8.0`).
- **Outlier rows**: rows with extreme (3×IQR) values in several numeric columns.
- Row-counter columns (`Unnamed: 0`, consecutive-integer ids) are ignored, otherwise they hide duplicates and blank rows.

### 3.5 Issue Detector (`issue_detector.py`)
Rule-based tags per column: `missing_values`, `constant_column`, `mixed_types_numeric_and_text`, `numeric_stored_as_text`, `numeric_values_with_units`, `inconsistent_date_format`, `inconsistent_casing`, `leading_trailing_whitespace`, `outliers_present`.

### 3.6 LLM Decision Engine (`llm_engine.py`)
- Sends the profile (+ row analysis) to Groq (`openai/gpt-oss-20b` by default, configurable) with JSON mode and low temperature.
- Returns `{"actions": [...]}`; a bare list of actions is accepted, anything else becomes an empty plan plus an error (never a crash).
- Retries with backoff on 429 and malformed JSON; no sleep after the last attempt; other API errors stop immediately.
- Profiles larger than `MAX_PROMPT_CHARS` are sent in column batches (row analysis only in the first); a 413 splits the request in half and retries; results are merged and de-duplicated.
- `repair_rejected_actions` asks once for corrected versions of rejected actions.

### 3.7 Plan Validator (`validator.py`)
Pydantic model + allow-list. Beyond "known action and known column" it checks parameters: `method` ∈ {iqr, zscore}, `casing` ∈ {auto, lower, upper, title}, `target_format` ∈ supported date formats, `target_dtype` ∈ supported dtypes, `multiplier > 0`, `0 ≤ threshold < 1`, `min_outlier_cols ≥ 1`. Row-level actions use `column: "*"` and skip the column-exists check. Invalid actions are rejected individually, never all-or-nothing.

### 3.8 Cleaning Executor (`executor.py`)
Pure pandas. **Row actions run first** (empty → sparse → duplicates → near-duplicates → outliers) so blank rows are removed instead of being imputed into fake records and outliers are judged before clipping. Then column actions in plan order, with `drop_column` last. Failures are logged per action and never abort the run.

| Action | Notes |
|---|---|
| `drop_empty_rows`, `drop_sparse_rows`, `drop_duplicates`, `drop_near_duplicate_rows`, `drop_outlier_rows` | row-level (`column: "*"`); removed row labels recorded for the audit file |
| `drop_rows_if_missing`, `drop_column` | |
| `impute_mean` / `impute_median` | refuse columns with non-numeric values (would wipe them) |
| `impute_mode` / `impute_constant` | `impute_constant` keeps numeric columns numeric or refuses |
| `clip_outliers` | `iqr` or `zscore`, default multiplier 3 (not 1.5) so genuine high values survive |
| `strip_whitespace`, `normalize_casing` | `auto` merges case-variants to the most common spelling; `lower/upper/title` are blanket changes |
| `standardize_date_format` | day-first/month-first inferred from the data or given; unresolved ambiguity is reported |
| `fix_dtype` | `int/float/str/bool`; missing stays missing; bool refuses unrecognised values |
| `extract_number` | `8GB`→8, `1TB`→1024 (GB), `500g`→0.5 (kg); refuses composite text like `128GB SSD` |

### 3.9 Fallback plan (`fallback.py`)
If the LLM is unavailable or returns nothing usable, a conservative deterministic plan is built from the issue tags and row analysis: blank/duplicate rows, whitespace, case variants, units, numbers stored as text, and imputation only where ≤ 20 % is missing (blank rows excluded from that %). It never drops columns, clips outliers, or drops sparse/outlier rows. Disable with `FALLBACK_ON_LLM_FAILURE=false`.

### 3.10 Post-clean Check (`postcheck.py`)
Re-runs the profiler, issue detector and row analyzer on the cleaned data and lists what is still flagged (e.g. outliers that were deliberately not clipped). It is advisory — a human reviews it.

### 3.11 Report Generator (`report.py`)
Markdown: row/column counts before and after, whether the LLM plan, a repaired plan, or the fallback was used, placeholder conversions, row-wise analysis and rows removed per action, every applied action with the stated reason and result, skipped/failed actions, validator rejections, and the post-clean check.

---

## 4. Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.10+ |
| Data handling | pandas (tested on 2.2 and 3.x), numpy |
| LLM provider | Groq API (free tier) — `groq` SDK, default model `openai/gpt-oss-20b` |
| Schema validation | pydantic v2 |
| CLI | Typer + Rich |
| File I/O | pandas + openpyxl (xlsx), xlrd (xls read), chardet |
| Config/secrets | `.env` + python-dotenv (never commit `.env`; see `.gitignore`) |
| Tests | pytest (`requirements-dev.txt`) |

---

## 5. Handling Groq Free-Tier Constraints

- **Rate limits:** one request per dataset where possible; exponential backoff on 429.
- **Context limits:** only aggregated stats and row counts are sent; large profiles are batched; a 413 splits the request.
- **Reliability:** output is parsed leniently (code fences, bare lists) and validated strictly; one repair re-prompt; deterministic fallback if the LLM fails entirely.
- **Privacy:** no raw rows are ever sent. Up to `MAX_SAMPLE_VALUES` (default 5) real cell values per column are included unless `SEND_SAMPLE_VALUES=false`.

---

## 6. Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | — | required for LLM planning |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | model id |
| `MAX_SAMPLE_VALUES` | 5 | sample values per column |
| `SEND_SAMPLE_VALUES` | true | false = stats and tags only |
| `MAX_PROMPT_CHARS` | 20000 | batch threshold |
| `LLM_TEMPERATURE` / `LLM_MAX_RETRIES` | 0.1 / 3 | |
| `FALLBACK_ON_LLM_FAILURE` | true | rule-based plan if the LLM fails |

---

## 7. Folder Structure

```
autoclean/
├── autoclean/
│   ├── loader.py          # file reading/writing, encoding chain
│   ├── placeholders.py    # '?' / 'N/A' -> missing
│   ├── profiler.py        # stats generation
│   ├── row_analyzer.py    # row-wise flags and row selectors
│   ├── issue_detector.py  # rule-based issue tags
│   ├── llm_engine.py      # Groq calls, batching, retry, repair
│   ├── validator.py       # pydantic schema + allow-list
│   ├── fallback.py        # rule-based plan when the LLM fails
│   ├── executor.py        # cleaning operations
│   ├── postcheck.py       # re-check after cleaning
│   ├── report.py          # markdown report
│   └── pipeline.py        # orchestration
├── cli.py
├── config.py
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt / requirements-dev.txt
├── pytest.ini
└── architecture.md
```

---

## 8. Known Limitations

- Cleaning decisions are heuristic; always review the report and `*_removed_rows.csv`.
- `extract_number` does not split composite values such as `128GB SSD` (it refuses rather than lose the drive type).
- Near-duplicate detection compares whole rows after normalisation; it does not do fuzzy matching.
- Fully ambiguous numeric dates (e.g. `03/04/2023` throughout) are read month-first and flagged in the report.
- The LLM's choices are not deterministic across runs.

## 9. Future Extensions
- Dry-run / human-in-the-loop approval of the plan (CLI `--review`, or a Streamlit UI).
- User-defined rules that override LLM suggestions.
- Splitting composite columns (`128GB SSD` → size + type).
- Caching LLM responses for identical profiles.
- Packaging (`pyproject.toml`) so `autoclean` installs as a command.
