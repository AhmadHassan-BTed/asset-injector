@echo off
cd /d "%~dp0"

:menu
cls
echo ========================================================
echo               EQOA DECOUPLED CUSTOM PATCH MASTER TOOL
echo ========================================================
echo.
echo Please select a modular pipeline phase to run:
echo.
echo   [1] Phase 1: Initialize Patched ISO (Sterile base copy)
echo       - Copies the clean unmodified Frontiers ISO to start the patch workspace.
echo.
echo   [2] Phase 2: Extract Sterile Database Assets from original ISOs
echo       - Extracts CHAR.ESF databases and baseline character select screen files
echo         from both Original and Frontiers unmodified ISOs.
echo.
echo   [3] Phase 3: Merge and Compile Custom Mod Payloads
echo       - Performs low-level active model grafting and selective Vanilla character
echo         selection screen overlays, writing to staging folders.
echo.
echo   [4] Phase 4: Paste custom Mod Payloads in Patched ISO
echo       - Surgically byte-patches UDF File Entries and ISO 9660 records to inject
echo         grafted models and select overlays in-place.
echo.
echo   [5] Run Complete Modular Pipeline Sequentially (All Phases)
echo   [6] Launch Patched ISO in PCSX2 Emulator
echo   [7] Exit
echo.
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto phase1
if "%choice%"=="2" goto phase2
if "%choice%"=="3" goto phase3
if "%choice%"=="4" goto phase4
if "%choice%"=="5" goto runall
if "%choice%"=="6" goto launch_emulator
if "%choice%"=="7" goto end
goto menu

:phase1
echo.
echo [*] Running Phase 1: Initialize Patched ISO (Sterile base copy)...
set "iso_clean=iso\unpatched\EQOA_Frontiers.iso"
set "iso_patched=iso\patched\EQOA_Frontiers_Patched.iso"
if not exist "%iso_clean%" (
    echo [-] Error: Original clean ISO not found at %iso_clean%!
    pause
    goto menu
)
echo [*] Copying base Frontiers ISO: %iso_clean% -> %iso_patched% ...
if not exist "iso\patched" mkdir "iso\patched"
copy /Y "%iso_clean%" "%iso_patched%" >nul
if %errorlevel% neq 0 (
    echo [-] Failed to copy base ISO. Make sure PCSX2 is closed!
    pause
    goto menu
)
echo [SUCCESS] Phase 1 Completed Successfully! Patched ISO is initialized.
pause
goto menu

:phase2
echo.
echo [*] Running Phase 2: Extract Sterile Database Assets...
echo [*] Step 2.1: Extracting CHAR.ESF databases from clean Original and Frontiers ISOs...
python -m core.extract_databases
if %errorlevel% neq 0 (
    echo [-] Failed to extract base ESF databases!
    pause
    goto menu
)
echo [*] Step 2.2: Extracting Frontiers select database assets...
python -m phase3_patch_character_selection.step3_preserve_baseline.preserve_frontiers_baseline
if %errorlevel% neq 0 (
    echo [-] Failed to extract baseline character select screens!
    pause
    goto menu
)
echo.
echo [SUCCESS] Phase 2 Completed Successfully! Staged databases are extracted.
pause
goto menu

:phase3
echo.
echo ========================================================
echo RUNNING PHASE 3: MERGE AND COMPILE MOD PAYLOADS
echo ========================================================
echo.
echo [*] Step 3.1: Running baseline extraction ^& preservation...
python -m phase3_patch_character_selection.step3_preserve_baseline.preserve_frontiers_baseline
if %errorlevel% neq 0 (
    echo [-] Failed baseline preservation!
    pause
    goto menu
)
echo.
echo [*] Step 3.2: Running active player model graft compiler (grafts Vanilla to Frontiers)...
python -m phase3_patch_character_selection.step2_ingame_models.patch_ingame_models --skip-inject-database
if %errorlevel% neq 0 (
    echo [-] Failed model grafting!
    pause
    goto menu
)
echo.
echo [*] Step 3.3: Running character selection screen database merger (overlays Vanilla databases)...
python -m phase3_patch_character_selection.step1_character_selection.patch_character_selection --skip-inject-databases
if %errorlevel% neq 0 (
    echo [-] Failed select overlays!
    pause
    goto menu
)
echo.
echo [SUCCESS] Phase 3 Completed Successfully! All mod payloads are compiled and merged.
pause
goto menu

:phase4
echo.
echo [*] Running Phase 4: Paste custom Mod Payloads in Patched ISO...
tasklist | findstr /I "pcsx2-qt.exe" >nul
if %errorlevel% equ 0 (
    echo [*] Detected running PCSX2 emulator. Closing it to prevent file locks...
    taskkill /F /IM pcsx2-qt.exe >nul
)
python -m phase4_unified_patch.repack_and_patch_iso
if %errorlevel% neq 0 (
    echo.
    echo [-] Phase 4 Injection Failed!
    pause
    goto menu
)
echo.
echo [*] Running high-integrity verification suite...
python -m core.verify_final_patch
if %errorlevel% neq 0 (
    echo.
    echo [-] High-integrity Verification Failed!
    goto menu
)
echo.
echo [SUCCESS] Phase 4 Completed Successfully! Custom payloads injected and verified in ISO.
pause
goto menu

:runall
echo.
echo ========================================================
echo RUNNING COMPLETE SEQUENTIAL DECOUPLED PIPELINE
echo ========================================================
echo.
echo [*] Starting Phase 1/4 (Initializing Patched ISO)...
set "iso_clean=iso\unpatched\EQOA_Frontiers.iso"
set "iso_patched=iso\patched\EQOA_Frontiers_Patched.iso"
if not exist "iso\patched" mkdir "iso\patched"
copy /Y "%iso_clean%" "%iso_patched%" >nul
if %errorlevel% neq 0 goto runall_failed

echo.
echo [*] Starting Phase 2/4 (Extracting Sterile Database Assets)...
python -m core.extract_databases
if %errorlevel% neq 0 goto runall_failed
python -m phase3_patch_character_selection.step3_preserve_baseline.preserve_frontiers_baseline
if %errorlevel% neq 0 goto runall_failed

echo.
echo [*] Starting Phase 3/4 (Merging and Compiling custom mod payloads)...
python -m phase3_patch_character_selection.step2_ingame_models.patch_ingame_models --skip-inject-database
if %errorlevel% neq 0 goto runall_failed
python -m phase3_patch_character_selection.step1_character_selection.patch_character_selection --skip-inject-databases
if %errorlevel% neq 0 goto runall_failed

echo.
echo [*] Starting Phase 4/4 (Pasting and Injecting custom mod payloads in ISO)...
tasklist | findstr /I "pcsx2-qt.exe" >nul
if %errorlevel% equ 0 (
    taskkill /F /IM pcsx2-qt.exe >nul
)
python -m phase4_unified_patch.repack_and_patch_iso
if %errorlevel% neq 0 goto runall_failed
python -m core.verify_final_patch
if %errorlevel% neq 0 goto runall_failed

echo.
echo ========================================================
echo [SUCCESS] ALL DECOUPLED STAGES EXECUTED SUCCESSFULLY!
echo ========================================================
pause
goto menu

:runall_failed
echo.
echo [-] Pipeline failed at one of the stages! Please inspect logs above.
pause
goto menu

:launch_emulator
echo.
echo [*] Launching EQOA Frontiers Patched in PCSX2 Emulator...
echo [*] Checking common emulator locations...

:: 1. Try local project root
if exist "pcsx2-qt.exe" (
    start "" "pcsx2-qt.exe" "%~dp0iso\patched\EQOA_Frontiers_Patched.iso"
    goto launch_success
)
if exist "pcsx2.exe" (
    start "" "pcsx2.exe" "%~dp0iso\patched\EQOA_Frontiers_Patched.iso"
    goto launch_success
)

:: 2. Try standard installation paths
if exist "%LocalAppData%\PCSX2\pcsx2-qt.exe" (
    start "" "%LocalAppData%\PCSX2\pcsx2-qt.exe" "%~dp0iso\patched\EQOA_Frontiers_Patched.iso"
    goto launch_success
)
if exist "C:\Program Files\PCSX2\pcsx2-qt.exe" (
    start "" "C:\Program Files\PCSX2\pcsx2-qt.exe" "%~dp0iso\patched\EQOA_Frontiers_Patched.iso"
    goto launch_success
)
if exist "C:\Program Files (x86)\PCSX2\pcsx2.exe" (
    start "" "C:\Program Files (x86)\PCSX2\pcsx2.exe" "%~dp0iso\patched\EQOA_Frontiers_Patched.iso"
    goto launch_success
)

:: 3. Try system PATH
start "" pcsx2-qt.exe "%~dp0iso\patched\EQOA_Frontiers_Patched.iso" 2>nul
if %errorlevel% equ 0 goto launch_success

start "" pcsx2.exe "%~dp0iso\patched\EQOA_Frontiers_Patched.iso" 2>nul
if %errorlevel% equ 0 goto launch_success

echo.
echo [-] Error: Could not locate PCSX2 executable in standard installation paths or PATH.
echo     Please ensure PCSX2 is installed and added to your system PATH,
echo     or copy your pcsx2-qt.exe / pcsx2.exe to the workspace root directory.
echo.
pause
goto menu

:launch_success
echo [SUCCESS] Emulator launched successfully!
timeout /t 2 >nul
goto menu

:end
exit