@echo off
REM ============================================================
REM  IronPulse Fitness - First-time setup + start the API server
REM  Run this once on a new machine, then use start_site.bat
REM  in a second Command Prompt window to launch the website.
REM ============================================================

cd /d "%~dp0"

echo.
echo === [1/5] Removing any old virtual environment ===
rmdir /s /q .venv 2>nul

echo.
echo === [2/5] Creating a fresh virtual environment ===
python -m venv .venv
if errorlevel 1 (
    echo.
    echo ERROR: Python was not found. Install Python 3.11 or 3.12 from
    echo        https://www.python.org/downloads/ and tick "Add Python to PATH".
    pause
    exit /b 1
)

echo.
echo === [3/5] Activating the virtual environment ===
call .venv\Scripts\activate.bat

echo.
echo === [4/5] Installing all Python dependencies (this can take 1-2 minutes) ===
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. Check the messages above.
    pause
    exit /b 1
)

REM Copy the .env file if it doesn't exist yet
if not exist ".env" (
    echo.
    echo === Copying .env.example to .env ===
    copy .env.example .env >nul
)

REM Seed the demo data if the SQLite DB is missing
if not exist "data\gym.db" (
    echo.
    echo === Seeding demo data (40 members, 4 trainers, 65 plans, 1000+ check-ins) ===
    python seed.py --reset
)

echo.
echo === [5/5] Starting the IronPulse API on http://localhost:8000 ===
echo.
echo ============================================================
echo   API will be live at:   http://localhost:8000/docs
echo.
echo   Now open a SECOND Command Prompt in this folder and run:
echo       start_site.bat
echo   to launch the website at http://localhost:8501
echo.
echo   Press Ctrl+C to stop the API.
echo ============================================================
echo.

python main.py
