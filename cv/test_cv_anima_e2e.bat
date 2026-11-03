@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Project virtual environment is missing. Run setup.bat first.
  exit /b 1
)
.venv\Scripts\python.exe cv\scripts\test_cv_anima_e2e.py %*
