"""Loads raw data files (CSV, XLSX, JSON) into a pandas DataFrame."""
from pathlib import Path

import chardet
import pandas as pd


def _detect_encoding(path: Path) -> str:
    with open(path, "rb") as f:
        raw = f.read(50000)
    result = chardet.detect(raw)
    return result.get("encoding") or "utf-8"


def _read_csv_any_encoding(path: Path) -> pd.DataFrame:
    """Read a CSV, trying encodings until one decodes the *whole* file.

    chardet only sees the first 50 KB, so a file that looks like ASCII at the top
    can still contain latin-1/cp1252 bytes later. cp1252 then latin-1 are last-resort
    fallbacks (latin-1 accepts any byte, so it never fails).
    """
    guessed = _detect_encoding(path)
    candidates = []
    for enc in ("utf-8-sig", guessed, "cp1252", "latin-1"):
        if enc and enc.lower() not in [c.lower() for c in candidates]:
            candidates.append(enc)

    last_error: Exception | None = None
    for enc in candidates:
        try:
            try:
                return pd.read_csv(path, encoding=enc, sep=None, engine="python")
            except UnicodeDecodeError:
                raise
            except Exception:
                # delimiter sniffing failed; plain defaults with the same encoding
                return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError as e:
            last_error = e
    raise ValueError(f"Could not decode CSV with any supported encoding: {last_error}")


def load_data(file_path: str) -> pd.DataFrame:
    """Load a CSV, XLSX, or JSON file into a DataFrame.

    Raises:
        ValueError: unsupported file extension.
        FileNotFoundError: file does not exist.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = _read_csv_any_encoding(path)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    elif suffix == ".json":
        df = pd.read_json(path)
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported: .csv, .xlsx, .xls, .json"
        )

    if df.empty:
        raise ValueError("Loaded file contains no data.")

    return df


def save_data(df: pd.DataFrame, output_path: str) -> None:
    """Save a DataFrame back out, matching the extension of output_path."""
    path = Path(output_path)
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)

    if suffix == ".csv":
        df.to_csv(path, index=False)
    elif suffix == ".xlsx":
        df.to_excel(path, index=False)
    elif suffix == ".xls":
        raise ValueError("Writing legacy .xls is not supported; use an .xlsx output path")
    elif suffix == ".json":
        df.to_json(path, orient="records", indent=2)
    else:
        raise ValueError(f"Unsupported output file type '{suffix}'")
