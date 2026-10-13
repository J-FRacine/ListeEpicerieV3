@echo off
setlocal
cd /d "%~dp0"

echo.
echo === Recettes V1.8.0 - mesures, nutrition et PDF ===
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 INSTALLER_RECETTES_V1.8.0.py
) else (
    python INSTALLER_RECETTES_V1.8.0.py
)

set RESULT=%errorlevel%
echo.
if %RESULT%==0 (
    echo SUCCES - Recettes V1.8.0 installee et validee localement.
) else (
    echo ECHEC - consultez tests-resultats-recettes-v1.8.0.log si present.
)
echo.
pause
exit /b %RESULT%
