@echo off
chcp 65001 >nul
echo ============================================
echo   UPDATE DASHBOARD INVENTORY - ZUMA
echo ============================================
echo.
echo Memproses data stock...
echo.

cd /d "%~dp0"
python generate_dashboard.py

echo.
echo ============================================
echo   SELESAI!
echo ============================================
echo.
echo Dashboard sudah diupdate.
echo File: dashboard_inventory.html
echo.

set /p buka="Buka dashboard sekarang? (Y/N): "
if /i "%buka%"=="Y" (
    start "" "dashboard_inventory.html"
)

pause
