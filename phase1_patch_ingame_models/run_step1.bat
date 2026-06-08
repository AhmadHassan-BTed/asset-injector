@echo off
cd /d "%~dp0.."
echo ========================================================
echo STEP 1: CREATE INITIAL FRONTIERS PATCHED ISO
echo ========================================================
echo.
echo This step compiles the 11 native character models (Vanilla geometry 
echo grafted onto Frontiers skeleton) and repacks them into a baseline 
echo frontiers ISO (EQOA_Frontiers_Patched.iso).
echo.
echo [*] Running Pristine Structural Transplant Pipeline...
python -m step1_patch_ingame_models.patch_ingame_models
if %errorlevel% neq 0 (
    echo.
    echo [-] STEP 1 FAILED!
    pause
    exit /b %errorlevel%
)
echo.
echo [SUCCESS] STEP 1 COMPLETE!
echo Initial patched game ISO compiled and verified successfully.
echo.
pause
