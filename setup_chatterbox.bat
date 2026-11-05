@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call setup.bat --no-update --no-pause
  if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" scripts\setup_chatterbox.py %*
set "chatterbox_result=%errorlevel%"
if not "%chatterbox_result%"=="0" echo Setup incomplete. See the message above; existing data was preserved.
pause
exit /b %chatterbox_result%
