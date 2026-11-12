# AutoClean

LLM-driven automated data cleaning. Profiles your dataset statistically, sends
a compact summary to Groq's free-tier LLM to decide what cleaning actions to
take, validates those decisions, then executes them deterministically with
pandas. Produces a cleaned file plus a markdown audit report.

See `architecture.md` for the full design.

## Setup

```bash
cd autoclean
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste your free Groq API key (https://console.groq.com/keys)
```

## Usage

```bash
python cli.py data.csv
```

Optional flags:

```bash
python cli.py data.csv --output cleaned.csv --report report.md
```

This produces:
- `data_cleaned.csv` — the cleaned dataset
- `data_report.md` — what was changed and why (LLM's stated reasoning per action)
- `data_removed_rows.csv` — full copies of every row dropped by row-wise cleaning (only if any were removed; path via `--removed-rows`)

Supports `.csv`, `.xlsx`/`.xls`, and `.json` input files.

## How it works

1. **Load** — reads the file into a DataFrame.
2. **Profile** — computes per-column stats (missing %, dtype, outliers, samples) — no raw rows leave this step.
   A **row-wise analysis** (`row_analyzer.py`) also summarises rows: fully empty, sparse, exact/near duplicates, and rows with extreme values in several numeric columns. Row-counter columns like `Unnamed: 0` are ignored so they don't hide duplicates.
3. **Detect** — rule-based checks flag candidate issues (duplicates, mixed types, inconsistent dates/casing, outliers).
4. **LLM decision** — the profile + issues (not the raw data) are sent to Groq (`openai/gpt-oss-20b` by default), which returns a structured JSON cleaning plan.
5. **Validate** — every proposed action is checked against a strict schema and an allow-list of implemented operations before anything runs.
6. **Execute** — validated actions are applied with plain pandas. Row-wise actions always run first
   (so blank rows are removed rather than imputed into fake records, and outlier rows are judged before clipping).
7. **Report** — a markdown report records every action taken, the LLM's reasoning, and anything rejected.

## Robustness

- **Fallback plan:** if the Groq key is missing or the call fails, a conservative rule-based plan runs instead
  (blank/duplicate rows, whitespace, case variants, numbers with units, light imputation; never drops columns
  or clips outliers). The report says it was used. Disable with `FALLBACK_ON_LLM_FAILURE=false`.
- **Re-prompt:** actions the validator rejects are sent back to the LLM once for correction; anything still
  invalid is listed in the report.
- **Post-clean check:** the cleaned data is profiled again and any remaining issues (duplicates, blanks,
  mixed types, units, ...) are listed in the report.
- **Large datasets:** profiles over `MAX_PROMPT_CHARS` (default 20000) are split into column batches, and a
  413 "payload too large" reply is retried with the request split in half.
- **Privacy:** the LLM never receives full rows, but by default it does receive up to 5 sample cell values
  per column. Set `SEND_SAMPLE_VALUES=false` to send only statistics and issue tags.
- **Files:** `.xls` can be read (needs `xlrd`) but not written; output defaults to `.xlsx`.

Development: `pip install -r requirements-dev.txt && pytest` (tested on pandas 2.2 and 3.x).

## Project structure

```
autoclean/
├── autoclean/
│   ├── loader.py          # file reading/writing
│   ├── profiler.py        # stats generation
│   ├── row_analyzer.py    # row-wise flags + row selectors
│   ├── issue_detector.py  # rule-based flags
│   ├── llm_engine.py       # Groq API calls + prompt
│   ├── validator.py        # pydantic schema + action allow-list
│   ├── executor.py         # cleaning operations
│   ├── fallback.py         # rule-based plan when the LLM fails
│   ├── placeholders.py     # '?' / 'N/A' -> missing
│   ├── postcheck.py        # re-check after cleaning
│   └── pipeline.py         # orchestration
├── cli.py                  # CLI entry point
├── config.py                # env/config loading
├── tests/
├── .env.example
├── requirements.txt
└── architecture.md
```

## Supported cleaning actions

`drop_duplicates`, `drop_rows_if_missing`, `impute_mean`, `impute_median`,
`impute_mode`, `impute_constant`, `clip_outliers`, `drop_column`,
`strip_whitespace`, `normalize_casing`, `standardize_date_format`, `fix_dtype`,
`no_action`.

Also: `extract_number` turns values like `8GB` / `1.37kg` / `1TB` into numbers (converted to GB / kg; refuses columns with extra text such as `128GB SSD`).
`normalize_casing` defaults to `auto` (merges `Dell`/`DELL` into the most common spelling instead of blanket re-casing), and `clip_outliers` uses 3×IQR by default (`method` / `multiplier` configurable).
`standardize_date_format` infers day-first vs month-first from the data (or takes `dayfirst`), and the report flags dates that stay ambiguous. Supported targets: `YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY/MM/DD`, `DD-Mon-YYYY`. The validator rejects unsupported `target_format`, `target_dtype`, `casing` and `method` values. `drop_column` always runs after other column actions.
Placeholder strings such as `?`, `N/A`, `--` are converted to missing values before profiling (listed in the report).

Row-wise actions (use `"column": "*"`):

| Action | What it removes | Parameter |
|---|---|---|
| `drop_empty_rows` | rows where every cell is blank | — |
| `drop_sparse_rows` | rows with more than `threshold` of cells blank | `threshold` (0–1, default 0.5) |
| `drop_duplicates` | exact duplicates of an earlier row (first kept) | — |
| `drop_near_duplicate_rows` | duplicates after ignoring case, spacing and `8` vs `8.0` | — |
| `drop_outlier_rows` | rows with extreme (3×IQR) values in several numeric columns | `min_outlier_cols` (default 2) |

The LLM decides which row actions to use and how strict; the code selects the actual rows.
