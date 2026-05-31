@echo off
cd /d "%~dp0.."

echo ========================================================
echo STEP 4: SURGICALLY PATCH ASSETS INTO EMULATOR ISO
echo ========================================================
echo.
echo This step copies the combined assets from 'assets/merged-assets/' to 
echo the workspace folders, and surgically patches them into the new 
echo game ISO (EQOA_Frontiers_Patched.iso) in-place without disc 
echo reorganization (bypassing black screen boot issues).
echo.
:: Check and close pcsx2 if running to prevent file locks
tasklist | findstr /I "pcsx2-qt.exe" >nul
if %errorlevel% equ 0 (
    echo [*] Detected running PCSX2 emulator. Closing it to prevent file locks...
    taskkill /F /IM pcsx2-qt.exe >nul
)

python -m step4_unified_patch.repack_and_patch_iso
if %errorlevel% neq 0 (
    echo.
    echo [-] STEP 4 FAILED!
    pause
    exit /b %errorlevel%
)

echo.
echo [*] Running high-integrity verification suite...
python -m core.verify_final_patch
if %errorlevel% neq 0 (
    echo.
    echo [-] VERIFICATION FAILED!
    pause
    exit /b %errorlevel%
)

echo.
echo [SUCCESS] STEP 4 COMPLETE!
echo ISO successfully patched, validated, and verified ready to run in PCSX2!
echo.
pause
