@echo off
echo Starting Video Processing Dashboard...
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

REM Install dependencies if needed
echo Installing/updating dependencies...
pip install -r requirements.txt

REM Create directories
if not exist "INPUT\" mkdir INPUT
if not exist "OUTPUT\" mkdir OUTPUT

echo.
echo ========================================
echo Video Processing Dashboard is starting!
echo ========================================
echo.
echo Open your browser and go to: http://localhost:5000
echo.
echo To stop the application, close this window or press Ctrl+C
echo.

REM Start the Flask application
python run.py

pause
