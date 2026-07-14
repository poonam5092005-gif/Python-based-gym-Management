@echo off
REM ============================================================
REM  IronPulse Fitness - Open BOTH the API and the website in
REM  two new terminal windows. Assumes install_and_run.bat has
REM  already been run at least once (i.e. .venv exists).
REM ============================================================

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo First-time setup needed. Running install_and_run.bat...
    echo.
    call install_and_run.bat
    exit /b 0
)

echo Starting IronPulse API in a new window...
start "IronPulse API"  cmd /k ".venv\Scripts\activate.bat && python main.py"

REM Give the API 3 seconds to boot before starting the site
timeout /t 3 /nobreak >nul

echo Starting IronPulse Website in a new window...
start "IronPulse Website"  cmd /k ".venv\Scripts\activate.bat && streamlit run dashboard/streamlit_app.py"

echo.
echo ============================================================
echo   Both servers launching in separate windows.
echo.
echo   API:      http://localhost:8000/docs
echo   Website:  http://localhost:8501
echo.
echo   Close each window (or press Ctrl+C in it) to stop.
echo ============================================================
echo.
pause
