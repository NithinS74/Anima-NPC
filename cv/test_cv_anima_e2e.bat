@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo CV virtual environment is missing. Run setupcv.bat first.
  exit /b 1
)
.venv\Scripts\python.exe scripts\test_cv_anima_e2e.py %*
