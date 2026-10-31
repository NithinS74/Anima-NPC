@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Project venv missing. Follow SETUP.md first.
  pause
  exit /b 1
)
echo Starting the NPC lab. Default: LIVE Gemini calls. Pass --offline for the fake provider.
echo Keys stay in the local .env. Live calls may incur API charges.
echo Default: 30-second manual-testing deadline. Use --realtime to test the 3-second target.
".venv\Scripts\python.exe" -m tools.npc_lab --live --open %*
if errorlevel 1 (
  echo Lab stopped with an error. Check the message above and SETUP.md.
  pause
)
