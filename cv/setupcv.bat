@echo off
setlocal
cd /d "%~dp0.."
call setup.bat --no-update
if errorlevel 1 exit /b 1
if not exist "cv\backend\.env" copy "cv\backend\.env.example" "cv\backend\.env" >nul
echo CV uses the root .venv and requirements.txt. No model is downloaded automatically.
echo Install Ollama and explicitly run: ollama pull qwen2.5vl:3b
echo Start the service with run_cv.bat. See cv\SETUP.md.
