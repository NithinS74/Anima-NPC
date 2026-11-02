@echo off
setlocal
cd /d "%~dp0"

echo === Skyrim CV setup ===
py -3.11 -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 was not found. Install it from python.org, then rerun setupcv.bat.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating project virtual environment...
  py -3.11 -m venv .venv
  if errorlevel 1 exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install -r backend\requirements.txt
if errorlevel 1 exit /b 1

if not exist "backend\.env" (
  copy /y backend\.env.example backend\.env >nul
  echo Created backend\.env from the safe defaults.
)

where ollama >nul 2>&1
if errorlevel 1 (
  echo Ollama is not installed. Install it from https://ollama.com/ then run setupcv.bat again.
  exit /b 1
)

echo Downloading/checking qwen2.5vl:3b. This is a one-time multi-GB download...
ollama pull qwen2.5vl:3b
if errorlevel 1 (
  echo Could not pull the VLM. Start the Ollama application/service, check your connection, then rerun setupcv.bat.
  exit /b 1
)

echo Downloading/checking the configured YOLO weights...
python backend\download_models.py
if errorlevel 1 exit /b 1

echo.
echo Setup complete.
echo Start the CV API: .venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000
echo Then from the repository root start Anima with:
echo   .\run_anima.bat --offline --rag-config configs/rag/dialogue.example.json --cv-url http://127.0.0.1:8000
pause
