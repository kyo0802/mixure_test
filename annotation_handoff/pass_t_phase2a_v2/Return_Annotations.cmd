@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -B review.py return
if errorlevel 1 (
    echo Return failed. Read the error above; do not edit existing annotations.
    pause
    exit /b 1
)
echo Send the new ZIP in the returns folder and its SHA256 to the project owner.
pause
