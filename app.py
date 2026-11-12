"""
AutoClean Desktop Application — PyWebView entry point.

Usage:
    # Development (loads from Vite dev server on :5173):
    python app.py --dev

    # Production (loads from frontend/dist):
    python app.py

The CLI (cli.py / `python -m cli`) remains completely unaffected.
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
import urllib.request
from pathlib import Path

import webview

import config
from desktop.api import AutoCleanAPI

# ---------------------------------------------------------------------------
# Logging (writes to both console and %LOCALAPPDATA%\AutoClean\autoclean.log)
# ---------------------------------------------------------------------------
log_file = config.USER_DATA_DIR / "autoclean.log"
handlers: list[logging.Handler] = []
try:
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8", mode="a")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s"))
    handlers.append(file_handler)
except Exception:
    pass

if sys.stdout is not None:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s"))
    handlers.append(console_handler)

logging.basicConfig(
    level=logging.INFO,
    handlers=handlers or None,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("autoclean.app")

# ---------------------------------------------------------------------------
# Base path resolution (works for standard Python & PyInstaller frozen bundles)
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # PyInstaller creates a temporary folder or extracts files in sys._MEIPASS
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_TITLE = "AutoClean Desktop"
APP_WIDTH = 1280
APP_HEIGHT = 800
MIN_WIDTH = 900
MIN_HEIGHT = 600
DEV_SERVER_URL = "http://localhost:5173"
DIST_DIR = BASE_DIR / "frontend" / "dist"
_DEV_SERVER_TIMEOUT = 30  # seconds to wait for Vite to be ready


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_dev_server(url: str, timeout: int = _DEV_SERVER_TIMEOUT) -> bool:
    """Block until the Vite dev server responds or timeout is reached."""
    log.info("Waiting for Vite dev server at %s ...", url)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                log.info("Dev server is up.")
                return True
        except Exception:
            time.sleep(0.5)
    return False


def _assert_dist_exists() -> None:
    """Raise a helpful error if the production build is missing."""
    if not (DIST_DIR / "index.html").exists():
        raise FileNotFoundError(
            f"Production build not found at '{DIST_DIR}'.\n"
            "Run  npm run build  inside the frontend/ directory first."
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # If invoked with --cli or cli subcommand, route to Typer CLI
    if "--cli" in sys.argv or (len(sys.argv) > 1 and sys.argv[1] in ("clean", "cli")):
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.kernel32.AttachConsole(-1)
            except Exception:
                pass
        import cli
        cli_args = [arg for arg in sys.argv[1:] if arg not in ("--cli", "cli")]
        sys.argv = [sys.argv[0]] + cli_args
        cli.app()
        return

    parser = argparse.ArgumentParser(
        prog="autoclean-desktop",
        description="AutoClean — native desktop application powered by PyWebView.",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Load the UI from the Vite dev server (http://localhost:5173).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Open PyWebView in debug mode (shows browser DevTools).",
    )
    args = parser.parse_args()

    # -- Instantiate the Python API ------------------------------------------
    api = AutoCleanAPI()

    # -- Decide URL / path to load -------------------------------------------
    if args.dev:
        log.info("Development mode: loading from %s", DEV_SERVER_URL)
        if not _wait_for_dev_server(DEV_SERVER_URL):
            log.error(
                "Vite dev server did not respond within %s s. "
                "Start it with  npm run dev  inside frontend/  and try again.",
                _DEV_SERVER_TIMEOUT,
            )
            sys.exit(1)
        load_target = DEV_SERVER_URL
    else:
        log.info("Production mode: loading from %s", DIST_DIR)
        try:
            _assert_dist_exists()
        except FileNotFoundError as exc:
            log.error("%s", exc)
            sys.exit(1)
        load_target = str(DIST_DIR / "index.html")

    # -- Create the WebView window -------------------------------------------
    log.info("Creating window: %s (%dx%d)", APP_TITLE, APP_WIDTH, APP_HEIGHT)

    window = webview.create_window(
        title=APP_TITLE,
        url=load_target,
        js_api=api,          # exposes api methods as window.pywebview.api.*
        width=APP_WIDTH,
        height=APP_HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        resizable=True,
        text_select=False,   # professional desktop feel
        confirm_close=False,
        background_color="#0d0d14",  # match --bg-base so no white flash
    )

    # Give the API a reference to the window so it can call window.evaluate_js
    api._window = window  # type: ignore[attr-defined]

    log.info("Starting PyWebView (debug=%s) ...", args.debug)
    webview.start(debug=args.debug)
    log.info("Window closed — exiting.")


if __name__ == "__main__":
    main()

