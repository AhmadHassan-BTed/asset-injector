@echo off
cd /d "%~dp0.."

echo ========================================================
echo STEP 3: MERGE VANILLA AND FRONTIERS ASSETS
echo ========================================================
echo.
echo This step merges baseline Vanilla assets and custom Frontiers overlays 
echo recursively, prioritizing custom Frontiers overlays when matching 
echo files exist, and outputs to the 'assets/merged-assets/' directory.
echo.
python -m step3_patch_character_selection.patch_character_selection --skip-merge-assets=%SKIP_MERGE_ASSETS% --skip-inject-databases=%SKIP_INJECT_DATABASES%
if %errorlevel% neq 0 (
    echo.
    echo [-] STEP 3 FAILED!
    pause
    exit /b %errorlevel%
)
echo.
echo [SUCCESS] STEP 3 COMPLETE!
echo Combined assets written to assets/merged-assets/ directory.
echo.
pause
