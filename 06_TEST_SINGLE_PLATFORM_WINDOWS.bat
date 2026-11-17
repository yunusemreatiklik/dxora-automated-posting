@echo off
cd /d "%~dp0"
echo This tool can publish to ONE selected platform only.
echo An explicit PUBLISH confirmation is required before any live posting.
".venv\Scripts\python.exe" -m tools.test_one_platform
pause
