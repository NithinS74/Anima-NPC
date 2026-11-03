@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat to prepare the project environment first.
  exit /b 1
)
if not exist "configs\skyrim\connector.json" copy "configs\skyrim\connector.example.json" "configs\skyrim\connector.json" >nul
".venv\Scripts\python.exe" -m npc.adapters.skyrim %*
