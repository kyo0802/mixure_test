@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Compatibility launcher. Existing frozen files and integrity receipts stay unchanged.
rem Supported: Python 3.10, 3.11, 3.12, 3.13 with Tcl/Tk.
echo FindMind Annotation - compatible Python launcher
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys,tkinter; assert sys.version_info.major == 3 and 10 <= sys.version_info.minor <= 13" >nul 2>&1
    if errorlevel 1 goto bad_venv
    goto install_requirements
)

set "PYTHON_CMD="
for %%V in (3.13 3.12 3.11 3.10) do (
    if not defined PYTHON_CMD (
        py -%%V -c "import tkinter,venv" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -%%V"
    )
)
if not defined PYTHON_CMD (
    python -c "import sys,tkinter,venv; assert sys.version_info.major == 3 and 10 <= sys.version_info.minor <= 13" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD goto missing_python

echo Using %PYTHON_CMD% to create .venv
%PYTHON_CMD% -m venv ".venv"
if errorlevel 1 goto failed

:install_requirements
".venv\Scripts\python.exe" -c "import PIL,jsonschema; from importlib.metadata import version; assert version('Pillow') == '11.3.0' and version('jsonschema') == '4.26.0'" >nul 2>&1
if errorlevel 1 (
    echo Installing pinned annotation dependencies...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 goto failed
)

echo Verifying the annotation handoff...
".venv\Scripts\python.exe" -B review.py check
if errorlevel 1 goto failed

echo Starting annotation GUI...
".venv\Scripts\python.exe" -B review.py gui
if errorlevel 1 goto failed
exit /b 0

:bad_venv
echo Existing .venv uses an unsupported Python version or has no Tkinter.
echo Keep all annotation responses safe. Rename only the .venv folder, then retry.
goto failed

:missing_python
echo No supported Python found. Install Python 3.10 through 3.13 with Tcl/Tk.
echo Detected Python installations:
py -0p
goto failed

:failed
echo.
echo Annotation could not start. Read the messages above.
pause
exit /b 1
