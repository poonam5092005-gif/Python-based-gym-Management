@echo off
REM ============================================================
REM  IronPulse Fitness - Launch the Streamlit website
REM  Run install_and_run.bat first (in another window).
REM ============================================================

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo ERROR: .venv folder is missing. Run install_and_run.bat first.
    echo.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo.
echo ============================================================
echo   IronPulse Website starting on http://localhost:8501
echo   (Make sure the API is running from install_and_run.bat)
echo.
echo   Press Ctrl+C to stop.
echo ============================================================
echo.

streamlit run dashboard/streamlit_app.py
