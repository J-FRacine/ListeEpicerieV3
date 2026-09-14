@echo off
setlocal
cd /d "%~dp0"

echo Finalisation JDR V1.6.0...
echo.

python finalize_jdr_v160.py
if errorlevel 1 (
    echo.
    echo La finalisation a echoue. Aucun fichier final ne doit etre televerse.
    pause
    exit /b 1
)

echo.
echo Le fichier JDR_V160_FINAL_FICHIERS_A_UPLOADER.zip est pret.
pause
