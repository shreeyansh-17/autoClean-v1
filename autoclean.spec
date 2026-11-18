# -*- mode: python ; coding: utf-8 -*-
"""
autoclean.spec — PyInstaller ONEDIR specification file for AutoClean Desktop.

Builds a self-contained Windows application directory containing:
  - Python runtime (no Python needed on host machine)
  - Precompiled React + Vite frontend (in frontend/dist)
  - PyWebView + Edge Chromium (WebView2) interop libraries
  - AutoClean core cleaning pipeline and CLI engine
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

BASE_DIR = Path.cwd()

# 1. Static Assets & Dependencies
# Crucial: NEVER bundle .env files or raw secrets
datas = [
    (str(BASE_DIR / 'frontend' / 'dist'), 'frontend/dist'),
]

datas += collect_data_files('webview')
datas += collect_data_files('pythonnet')
datas += collect_data_files('clr_loader')

# 2. Hidden Imports
hiddenimports = [
    # Windows & .NET runtime
    'clr',
    'pythonnet',
    'clr_loader',
    # PyWebView
    'webview',
    'webview.platforms.winforms',
    'webview.platforms.edgechromium',
    'webview.platforms.mshtml',
    'bottle',
    'proxy_tools',
    # Data Processing
    'pandas',
    'numpy',
    'openpyxl',
    'openpyxl.cell._writer',
    'xlrd',
    'chardet',
    # AI & CLI
    'groq',
    'pydantic',
    'typer',
    'rich',
    'rich.table',
    'rich.console',
    # AutoClean Modules
    'desktop.api',
    'config',
    'cli',
    'autoclean',
    'autoclean.loader',
    'autoclean.placeholders',
    'autoclean.profiler',
    'autoclean.row_analyzer',
    'autoclean.issue_detector',
    'autoclean.llm_engine',
    'autoclean.validator',
    'autoclean.fallback',
    'autoclean.executor',
    'autoclean.postcheck',
    'autoclean.report',
    'autoclean.pipeline',
]

hiddenimports += collect_submodules('webview')
hiddenimports += collect_submodules('clr_loader')
hiddenimports += collect_submodules('pythonnet')
hiddenimports += collect_submodules('autoclean')

# 3. Analysis
a = Analysis(
    ['app.py'],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=list(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        '.env',
        # Unused UI & DB engines (saves ~3 MB)
        'tkinter',
        '_tkinter',
        'tcl',
        'tk',
        'sqlite3',
        '_sqlite3',
        # Build tools and test suites (saves ~2 MB)
        'setuptools',
        'distutils',
        'pkg_resources',
        'unittest',
        'doctest',
        'pydoc',
        'pdb',
        'test',
        'scipy',
        'matplotlib',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 4. Standalone Executable Definition
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoClean',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Native desktop window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 5. ONEDIR Collection
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AutoClean',
)

