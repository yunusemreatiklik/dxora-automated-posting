@echo off
cd /d "%~dp0"
echo READ-ONLY: verify an existing Discord message; no new messages will be sent.
".venv\Scripts\python.exe" -m tools.verify_existing_discord
pause
