@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py finalize_jdr_v141.py .
) else (
    python finalize_jdr_v141.py .
)
echo.
echo Appuyez sur une touche pour fermer.
pause >nul
