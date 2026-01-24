@echo off
REM ========================================
REM ZUMA Dashboard - Upload Data ke Supabase
REM ========================================
REM Double-click file ini untuk upload data

REM Change to script directory
cd /d "%~dp0"

echo.
echo ========================================
echo ZUMA Dashboard - Upload Data
echo ========================================
echo.
echo Working directory: %CD%
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python tidak ditemukan!
    echo.
    echo Silakan install Python terlebih dahulu:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Checking required libraries...
echo.

REM Install required libraries if not exists
pip show requests >nul 2>&1
if errorlevel 1 (
    echo Installing 'requests' library...
    pip install requests
)

pip show python-dotenv >nul 2>&1
if errorlevel 1 (
    echo Installing 'python-dotenv' library...
    pip install python-dotenv
)

echo.
echo Starting upload...
echo.

REM Run the upload script (from current directory)
python "%~dp0upload_to_supabase.py"

echo.
pause
