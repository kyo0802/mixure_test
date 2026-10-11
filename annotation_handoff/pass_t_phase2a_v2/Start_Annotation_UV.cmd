@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem UV entrypoint for the unchanged, checksum-protected annotation handoff.
rem uv manages Python automatically; no py launcher or system Python is required.

set "UV_EXE=uv"
where uv >nul 2>&1
if errorlevel 1 (
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
    ) else (
        echo [ERROR] uv was not found.
        echo Install uv once from PowerShell:
        echo   winget install --id astral-sh.uv -e
        echo Then close and reopen the terminal before retrying.
        goto failed
    )
)

echo [1/4] Preparing the Python environment with uv...
if not exist ".venv\Scripts\python.exe" (
    "%UV_EXE%" venv --python 3.13 ".venv"
    if errorlevel 1 goto failed
)

rem Do not overwrite or delete an existing environment or any human responses.
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info.major == 3 and 10 <= sys.version_info.minor <= 14" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] The existing .venv is unusable or has an unsupported Python version.
    echo Preserve the responses, validated, and returns folders.
    echo Rename ONLY .venv to .venv_old, then rerun this launcher.
    goto failed
)

echo [2/4] Installing the frozen dependency versions with uv...
"%UV_EXE%" pip sync --python ".venv\Scripts\python.exe" -r requirements.txt
if errorlevel 1 goto failed

echo [3/4] Checking Tkinter and the unchanged handoff integrity...
".venv\Scripts\python.exe" -c "import tkinter; root=tkinter.Tk(); root.withdraw(); root.destroy()"
if errorlevel 1 (
    echo [ERROR] Tkinter/Tcl is not working in the chosen Python runtime.
    echo Preserve annotation responses. Rename ONLY .venv and retry.
    goto failed
)
".venv\Scripts\python.exe" -B review.py check
if errorlevel 1 goto failed

echo [4/4] Starting the annotation GUI...
".venv\Scripts\python.exe" -B review.py gui
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo Unable to launch FindMind annotation. No response files were deleted.
echo See UV_QUICKSTART.md for setup and troubleshooting.
pause
exit /b 1
