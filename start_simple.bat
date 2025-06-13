@echo off
echo Starting Simple Video Processing Dashboard...
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install simple dependencies
echo Installing dependencies...
pip install -r simple_requirements.txt

REM Create directories
if not exist "INPUT\" mkdir INPUT
if not exist "OUTPUT\" mkdir OUTPUT

echo.
echo ========================================
echo Simple Video Dashboard is starting!
echo ========================================
echo.
echo This is a simplified version that works without Redis/Celery
echo Open your browser and go to: http://localhost:5000
echo.
echo To stop the application, close this window or press Ctrl+C
echo.

REM Start the simple Flask application
python simple_run.py

pause
