@echo off
rem Double-click to start TwiBench. Your browser opens automatically.
rem Close this window to stop the app.
cd /d "%~dp0"
if not exist "web\dist\index.html" (
  echo Building the web app for the first time...
  pushd web
  call npm install --prefer-offline --no-audit --no-fund
  call npm run build
  popd
)
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" server\app.py
pause
