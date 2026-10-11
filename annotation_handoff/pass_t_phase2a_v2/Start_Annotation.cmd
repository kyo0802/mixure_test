@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import PIL, jsonschema; from importlib.metadata import version; assert version('Pillow') == '11.3.0' and version('jsonschema') == '4.26.0'" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -B review.py gui
if errorlevel 1 goto failed
exit /b 0
:failed
echo Annotation could not start. Install Python 3.12 with Tcl/Tk and read README.md.
pause
exit /b 1
