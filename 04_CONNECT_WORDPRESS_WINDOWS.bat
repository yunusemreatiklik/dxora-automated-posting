@echo off
cd /d "%~dp0"
echo Start the FastAPI server before running this step.
echo Opening the WordPress.com OAuth2 authorization page...
start "" "http://localhost:4000/wordpress/connect"
echo If needed, open exactly: http://localhost:4000/wordpress/connect
pause
