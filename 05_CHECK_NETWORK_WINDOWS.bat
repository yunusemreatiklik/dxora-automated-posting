@echo off
cd /d "%~dp0"
echo This check only tests network connectivity. It does not publish messages.
".venv\Scripts\python.exe" -m tools.check_network
pause
