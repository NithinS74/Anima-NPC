@echo off
setlocal
cd /d "%~dp0"
py -3.11 -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.11 first. See INSTALL_SKYRIM.md.
  exit /b 1
)
py -3.11 scripts\setup_skyrim.py %*
set "anima_setup_result=%errorlevel%"
pause
exit /b %anima_setup_result%
