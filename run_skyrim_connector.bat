@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call setup.bat --no-update --no-pause
  if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (
  call setup.bat --no-update --no-pause
  if errorlevel 1 exit /b 1
)
if not exist "configs\skyrim\connector.json" copy "configs\skyrim\connector.example.json" "configs\skyrim\connector.json" >nul
".venv\Scripts\python.exe" -m npc.adapters.skyrim %*
