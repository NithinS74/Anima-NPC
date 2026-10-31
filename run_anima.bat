@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\launch_anima.py %*
  goto finished
)
py -3.11 -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if not errorlevel 1 (
  py -3.11 scripts\launch_anima.py %*
  goto finished
)
python -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if not errorlevel 1 (
  python scripts\launch_anima.py %*
  goto finished
)
echo Python 3.11 was not found. Install it from python.org, then rerun run_anima.bat.
exit /b 1
:finished
set "anima_launch_result=%errorlevel%"
if not "%anima_launch_result%"=="0" echo Anima stopped with an error. Read the message above and SETUP.md.
exit /b %anima_launch_result%
