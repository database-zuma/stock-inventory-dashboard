@echo off
REM ========================================
REM ZUMA Dashboard - Open Dashboard
REM ========================================
REM Double-click to open dashboard with local server

cd /d "%~dp0"

echo.
echo ========================================
echo ZUMA Dashboard - Starting Server
echo ========================================
echo.

REM Start Python HTTP server
echo Starting local web server on port 8000...
start /B python -m http.server 8000

REM Wait 2 seconds for server to start
timeout /t 2 /nobreak >nul

REM Open Chrome to login page
echo Opening dashboard in Chrome...
start chrome "http://localhost:8000/login.html"

echo.
echo ========================================
echo Dashboard is now running!
echo ========================================
echo.
echo URL: http://localhost:8000/login.html
echo.
echo Login dengan:
echo - Email: wafi@zuma.id
echo - Password: ZumaDashboard2026!
echo.
echo Untuk stop server: Tutup command prompt ini
echo.
