@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo The virtual environment was not found. Run 01_SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 echo One or more tests failed. Review the error output above.
pause
