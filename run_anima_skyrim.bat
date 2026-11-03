@echo off
setlocal
title ANIMA - Skyrim Dialogue
cd /d "%~dp0"
call run_skyrim_connector.bat --local-speech --provider-profile configs/providers/gemini.yaml --log-file output/skyrim/anima-console.log %*
