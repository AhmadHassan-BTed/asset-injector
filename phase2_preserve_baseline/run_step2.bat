@echo off
cd /d "%~dp0.."

echo ========================================================
echo STEP 2: EXTRACT BASELINE FRONTIERS ASSETS
echo ========================================================
echo.
echo This step extracts the baseline Frontiers CSF/ESF database files 
echo directly from your clean unpatched Frontiers ISO and saves them 
echo into the 'assets/Frontiers/' folder.
echo.
python -m step2_preserve_baseline.preserve_frontiers_baseline
if %errorlevel% neq 0 (
    echo.
    echo [-] STEP 2 FAILED!
    pause
    exit /b %errorlevel%
)
echo.
echo [SUCCESS] STEP 2 COMPLETE!
echo Baseline assets successfully extracted to assets/Frontiers/.
echo.
pause
