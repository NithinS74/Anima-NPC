@echo off
setlocal
cd /d "%~dp0"
set "anima_no_pause="
set "anima_setup_args="
:parse_options
if "%~1"=="" goto setup_start
if /i "%~1"=="--no-pause" (
  set "anima_no_pause=1"
  shift
  goto parse_options
)
if /i "%~1"=="--sync-media" (
  set "anima_setup_args=%anima_setup_args% --sync-media"
  shift
  goto parse_options
)
if /i "%~1"=="--no-update" (
  set "anima_setup_args=%anima_setup_args% --no-update"
  shift
  goto parse_options
)
echo Usage: setup.bat [--no-pause] [--sync-media] [--no-update]
exit /b 2
:setup_start
echo Setting up Anima with Python 3.11 in .venv...
py -3.11 -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if not errorlevel 1 (
  py -3.11 scripts\setup_environment.py %anima_setup_args%
  goto finished
)
python -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if not errorlevel 1 (
  python scripts\setup_environment.py %anima_setup_args%
  goto finished
)
echo Python 3.11 was not found. Install Python 3.11 from python.org, then rerun setup.bat.
set "anima_setup_result=1"
goto result
:finished
set "anima_setup_result=%errorlevel%"
:result
if not "%anima_setup_result%"=="0" echo Setup stopped. Read the error above; existing keys and data were preserved.
if not defined anima_no_pause pause
exit /b %anima_setup_result%
