@echo off
cd /d "%~dp0"
echo FastAPI documentation: http://localhost:4000/docs
echo Press Ctrl+C to stop the server.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 4000
pause
