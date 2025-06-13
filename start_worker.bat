@echo off
echo Starting Celery Worker for Video Processing...
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo ========================================
echo Celery Worker is starting!
echo ========================================
echo.
echo This window processes video conversions in the background.
echo Keep this window open while using the dashboard.
echo.
echo To stop the worker, close this window or press Ctrl+C
echo.

REM Start Celery worker
celery -A celery_worker.celery worker --loglevel=info --pool=solo

pause
