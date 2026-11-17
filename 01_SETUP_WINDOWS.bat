@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m venv .venv
) else (
  python -m venv .venv
)
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 goto error
if not exist .env copy .env.example .env >nul

echo.
echo SETUP COMPLETE. Configure your authorized API credentials in .env.
echo NEVER upload .env or .wordpress_oauth_token.json to GitHub.
pause
exit /b 0
:error
echo SETUP FAILED. Check Python 3.10+ and network connectivity.
pause
exit /b 1
