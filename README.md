# AutoClean Desktop

> LLM-driven automated data cleaning — native Windows desktop application powered by PyWebView + React.

AutoClean profiles your dataset statistically, asks Groq's free-tier LLM what cleaning actions to take, validates those decisions, then executes them deterministically with pandas. It ships as a **standalone Windows `.exe`** — no Python or Node.js needed on the target machine.

---

## Screenshots

> _Upload a dataset → see AI recommendations → review before/after → export cleaned file._

---

## Features

- 📂 **Dataset upload** — CSV, XLSX, XLS, JSON
- 🔍 **Automatic profiling** — missing values, duplicates, outliers, data types, sample values
- 🤖 **AI recommendations** — Groq LLM proposes a structured cleaning plan
- ✅ **Review & approve** — accept or reject each recommended action individually
- ⚙️ **Pipeline execution** — deterministic pandas-backed cleaning engine
- 📊 **Before / After comparison** — row-level diff of original vs. cleaned data
- 📤 **Export** — cleaned dataset, removed rows CSV, markdown audit report
- 🕐 **History** — persisted cleaning session log
- 🔧 **Settings** — configure Groq API key and model from inside the app
- 💻 **CLI mode** — full command-line interface preserved inside the same executable

---

## Table of Contents

1. [Quick Start — Run from Source](#1-quick-start--run-from-source)
2. [Get a Groq API Key](#2-get-a-groq-api-key)
3. [Run the Desktop GUI](#3-run-the-desktop-gui)
4. [Run the CLI](#4-run-the-cli)
5. [Build a Windows Executable](#5-build-a-windows-executable-pyinstaller)
6. [Run the Packaged Executable](#6-run-the-packaged-executable)
7. [Project Structure](#7-project-structure)
8. [Configuration Reference](#8-configuration-reference)
9. [How It Works](#9-how-it-works)
10. [Supported Cleaning Actions](#10-supported-cleaning-actions)
11. [Known Limitations](#11-known-limitations)

---

## 1. Quick Start — Run from Source

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | [pyenv-win](https://github.com/pyenv-win/pyenv-win) or [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Git | any | |

### Clone & set up

```bash
git clone https://github.com/YOUR_USERNAME/autoclean.git
cd autoclean
```

**Create and activate a virtual environment:**

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

**Install Python dependencies:**

```bash
pip install -r requirements.txt
```

**Install frontend dependencies:**

```bash
cd frontend
npm install
cd ..
```

---

## 2. Get a Groq API Key

AutoClean uses [Groq](https://groq.com) for free LLM inference.

1. Go to [console.groq.com/keys](https://console.groq.com/keys)
2. Create a free account and generate an API key (starts with `gsk_`)

**Option A — `.env` file (development only, never committed to Git):**

```bash
cp .env.example .env
# Open .env and paste your key:
# GROQ_API_KEY=gsk_your_key_here
```

**Option B — Inside the app (recommended for packaged builds):**

Open the desktop app → **Settings** → **AI Configuration** → paste your key → **Save Settings**.
The key is saved to `%LOCALAPPDATA%\AutoClean\settings.json` on your machine only.

> ⚠️ **Never commit your `.env` file or API key to Git.** The `.gitignore` already excludes `.env`.

---

## 3. Run the Desktop GUI

**Step 1 — Build the frontend** (only needed once, or after UI changes):

```bash
cd frontend
npm run build
cd ..
```

**Step 2 — Launch the desktop window:**

```bash
python app.py
```

**Development mode** (live-reload UI from Vite dev server):

```bash
# Terminal 1 — start Vite dev server
cd frontend
npm run dev

# Terminal 2 — launch app pointing at dev server
cd ..
python app.py --dev
```

**Debug mode** (opens browser DevTools inside the window):

```bash
python app.py --debug
```

---

## 4. Run the CLI

The command-line interface works independently from the GUI and uses the same cleaning pipeline:

```bash
python cli.py your_dataset.csv
```

**All options:**

```bash
python cli.py your_dataset.csv \
  --output cleaned.csv \
  --report report.md \
  --removed-rows removed_rows.csv
```

**Supported input formats:** `.csv`, `.xlsx`, `.xls`, `.json`

**Outputs:**

| File | Description |
|------|-------------|
| `*_cleaned.csv` | Cleaned dataset |
| `*_report.md` | Audit report (every action + LLM reasoning) |
| `*_removed_rows.csv` | Full copies of rows that were dropped |

---

## 5. Build a Windows Executable (PyInstaller)

This creates a self-contained `dist\AutoClean\` folder that runs on any Windows 10/11 machine without Python or Node.js.

### Prerequisites

```bash
pip install pyinstaller
```

### Run the build script

```bash
build_windows.bat
```

This script automatically:
1. Runs `npm run build` inside `frontend/`
2. Cleans prior `build/` and `dist/AutoClean/` folders
3. Runs PyInstaller using `autoclean.spec`
4. Verifies `dist\AutoClean\AutoClean.exe` was created

**Expected output:**

```
BUILD SUCCESSFUL!
Distribution Folder: ...\dist\AutoClean
Application Binary:  ...\dist\AutoClean\AutoClean.exe
Release Zip Package: ...\dist\AutoClean-Windows-x64.zip (~38 MB)
```

### Manual build (alternative)

```bash
cd frontend && npm run build && cd ..
.venv\Scripts\pyinstaller.exe --noconfirm autoclean.spec
```

---

## 6. Run the Packaged Executable

After building, the entire `dist\AutoClean\` folder is portable.

**Launch the desktop GUI:**

```
dist\AutoClean\AutoClean.exe
```

Or simply double-click `AutoClean.exe` in Explorer.

**Use the CLI from the packaged executable:**

```bash
dist\AutoClean\AutoClean.exe --cli your_dataset.csv
dist\AutoClean\AutoClean.exe --cli your_dataset.csv --output cleaned.csv
dist\AutoClean\AutoClean.exe --cli --help
```

**Set your Groq API key (first run):**

Open the app → **Settings** → **AI Configuration** → enter your Groq API key → **Save Settings**.

**Where application data is stored (Windows):**

```
%LOCALAPPDATA%\AutoClean\
  settings.json       ← Groq API key & model preferences
  history.json        ← Cleaning session history
  autoclean.log       ← Application log (for debugging)
```

> ℹ️ `%LOCALAPPDATA%` resolves to `C:\Users\<YourName>\AppData\Local\AutoClean`.

### System requirement: Microsoft Edge WebView2

AutoClean's GUI renders using **Edge WebView2**, which is built into Windows 11 and Windows 10 version 21H2 or later. If the window is blank on an older system, install the [WebView2 Evergreen Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section) (free, ~2 MB bootstrapper).

---

## 7. Project Structure

```
autoclean_src/
│
├── app.py                    # Desktop entry point (PyWebView)
├── cli.py                    # CLI entry point (Typer)
├── config.py                 # Settings & env loading
│
├── autoclean/                # Core cleaning pipeline (do not modify)
│   ├── loader.py             # File reading / writing
│   ├── profiler.py           # Statistical profiling
│   ├── row_analyzer.py       # Row-level flagging
│   ├── issue_detector.py     # Rule-based issue detection
│   ├── llm_engine.py         # Groq API calls & prompt engineering
│   ├── validator.py          # Pydantic schema + action allow-list
│   ├── executor.py           # Cleaning operations (pandas)
│   ├── fallback.py           # Rule-based plan when LLM unavailable
│   ├── placeholders.py       # Normalise placeholder strings → NaN
│   ├── postcheck.py          # Post-clean re-profiling
│   ├── pipeline.py           # End-to-end orchestration
│   └── report.py             # Markdown report generation
│
├── desktop/
│   └── api.py                # Python↔JavaScript bridge (PyWebView js_api)
│
├── frontend/                 # React + Vite UI
│   ├── src/
│   │   ├── pages/            # UploadPage, ProfilingPage, RecommendationsPage…
│   │   ├── components/       # Shared UI components
│   │   └── services/
│   │       └── pywebview.js  # JS wrappers for all Python API calls
│   ├── package.json
│   └── vite.config.js
│
├── autoclean.spec            # PyInstaller build spec
├── build_windows.bat         # Repeatable Windows build script
├── requirements.txt          # Python runtime dependencies
├── requirements-dev.txt      # Dev/test extras
└── .env.example              # Template — copy to .env and add your key
```

---

## 8. Configuration Reference

All settings can be configured in `.env` (development) or via **Settings → AI Configuration** in the app (production).

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | _(required)_ | Your Groq API key from console.groq.com |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Model used for cleaning recommendations |
| `LLM_TEMPERATURE` | `0.1` | Lower = more deterministic |
| `LLM_MAX_RETRIES` | `3` | Retry count on API failure |
| `SEND_SAMPLE_VALUES` | `true` | Set `false` to send only stats, not cell values, to the LLM |
| `MAX_PROMPT_CHARS` | `20000` | Splits large profiles into batches above this limit |
| `FALLBACK_ON_LLM_FAILURE` | `true` | Use rule-based fallback if Groq is unavailable |
| `MAX_SAMPLE_VALUES` | `5` | Sample values per column sent to the LLM |

---

## 9. How It Works

```
Upload CSV / XLSX / JSON
        │
        ▼
  Load → normalize placeholders (?, N/A, --)
        │
        ▼
  Profile  ──  per-column stats + row-level flags
        │
        ▼
  Detect issues  ──  rule-based candidate flags
        │
        ▼
  LLM decision  ──  Groq API → structured JSON cleaning plan
        │          (profile + issues sent; raw rows never leave)
        ▼
  Validate  ──  pydantic schema + action allow-list check
        │
        ▼
  Execute  ──  row-wise actions first, then column actions
        │
        ▼
  Post-check  ──  re-profile cleaned data, flag remaining issues
        │
        ▼
  Report  ──  markdown audit log of every action + reasoning
```

If the Groq API is unavailable or returns an error, AutoClean falls back to a **conservative rule-based plan** (drops empty/duplicate rows, strips whitespace, normalises casing, extracts numbers with units, light imputation). The report states which path was used.

---

## 10. Supported Cleaning Actions

**Column-level:**

| Action | What it does |
|--------|-------------|
| `impute_mean` / `impute_median` / `impute_mode` | Fill missing values |
| `impute_constant` | Fill missing with a fixed value |
| `clip_outliers` | Clip extreme values to 3×IQR fence (configurable) |
| `drop_column` | Remove the entire column |
| `strip_whitespace` | Remove leading/trailing whitespace |
| `normalize_casing` | Merge `Dell`/`DELL` → most common spelling |
| `standardize_date_format` | Unify date strings (auto day-first detection) |
| `fix_dtype` | Cast columns to their correct type |
| `extract_number` | Parse `8GB`, `1.37kg` → numeric (converts units) |
| `no_action` | Explicitly record that no change was needed |

**Row-level** (`"column": "*"`):

| Action | What it removes |
|--------|----------------|
| `drop_empty_rows` | Rows where every cell is blank |
| `drop_sparse_rows` | Rows with >50% blank cells (threshold configurable) |
| `drop_duplicates` | Exact duplicate rows (keeps first) |
| `drop_near_duplicate_rows` | Duplicates ignoring case, spacing, `8` vs `8.0` |
| `drop_outlier_rows` | Rows with extreme values in multiple numeric columns |

---

## 11. Known Limitations

- **WebView2 required** — Windows 10 older than 21H2 may need the [WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section) installed separately.
- **Windows only** — the packaged `.exe` and `build_windows.bat` target Windows x64. Running from source works on macOS/Linux with a different PyWebView backend.
- **Build must match OS** — PyInstaller bundles must be built on the same OS as the target.
- **Groq model availability** — Groq periodically changes available free-tier models. If recommendations fail, change the model in **Settings → AI Configuration**.
- **Large datasets** — profiling datasets >500K rows may be slow. The cleaning pipeline itself is fast.

---

## Development

```bash
# Install dev dependencies (pytest, etc.)
pip install -r requirements-dev.txt

# Run tests
pytest

# Frontend dev server (live reload)
cd frontend && npm run dev
```

---

## License

MIT
