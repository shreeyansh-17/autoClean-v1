@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo  AutoClean Desktop — Windows ONEDIR Packaging Script
echo =====================================================================

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

REM 1. Verify Virtual Environment
if not exist "%ROOT_DIR%.venv\Scripts\pyinstaller.exe" (
    echo [ERROR] PyInstaller not found in .venv.
    echo Please install dependencies: .venv\Scripts\pip install pyinstaller pywebview
    exit /b 1
)

REM 2. Build Frontend Assets
echo.
echo [1/4] Compiling React frontend with Vite...
cd /d "%ROOT_DIR%frontend"
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed.
    cd /d "%ROOT_DIR%"
    exit /b 1
)
cd /d "%ROOT_DIR%"

REM 3. Verify dist exists
if not exist "%ROOT_DIR%frontend\dist\index.html" (
    echo [ERROR] frontend\dist\index.html was not generated.
    exit /b 1
)
echo [OK] Frontend bundle verified.

REM 4. Clean prior build outputs
echo.
echo [2/4] Cleaning previous build caches...
if exist "%ROOT_DIR%build" rmdir /s /q "%ROOT_DIR%build"
if exist "%ROOT_DIR%dist\AutoClean" rmdir /s /q "%ROOT_DIR%dist\AutoClean"

REM 5. Run PyInstaller
echo.
echo [3/4] Running PyInstaller build (autoclean.spec)...
"%ROOT_DIR%.venv\Scripts\pyinstaller.exe" --noconfirm "%ROOT_DIR%autoclean.spec"
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller compilation failed.
    exit /b 1
)

REM 6. Validate Output
echo.
echo [4/4] Verifying generated distribution...
if not exist "%ROOT_DIR%dist\AutoClean\AutoClean.exe" (
    echo [ERROR] Expected binary dist\AutoClean\AutoClean.exe was not found.
    exit /b 1
)

echo.
echo =====================================================================
echo  BUILD SUCCESSFUL!
echo =====================================================================
echo  Distribution Folder: %ROOT_DIR%dist\AutoClean
echo  Application Binary:  %ROOT_DIR%dist\AutoClean\AutoClean.exe
echo.
echo  To run the desktop application:
echo    "%ROOT_DIR%dist\AutoClean\AutoClean.exe"
echo.
echo  To run the CLI tool:
echo    "%ROOT_DIR%dist\AutoClean\AutoClean.exe" --cli --help
echo =====================================================================

exit /b 0

