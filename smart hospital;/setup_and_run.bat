@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo   CareBed - Smart Hospital Bed Allocator
echo ==============================================
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=py"
) else (
  set "PYTHON=python"
)
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating Python virtual environment...
  %PYTHON% -m venv .venv
  if errorlevel 1 goto failed
)
echo [2/3] Installing required packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo [3/3] Starting CareBed...
echo Open your browser at http://127.0.0.1:5000
echo Demo admin login: admin / Admin@12345
echo Keep this window open while using the app.
echo Press Ctrl+C to stop the server.
echo.
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto failed
goto end
:failed
echo.
echo Setup failed. Check the error above and ensure Python is installed.
pause
:end
endlocal
