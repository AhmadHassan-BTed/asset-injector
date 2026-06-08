# EQOA PS2 Frontiers Custom Patch Guide

This guide describes how to patch and restore original character models and custom assets into the PlayStation 2 *EverQuest Online Adventures: Frontiers* game ISO using this fully automated reverse-engineering toolkit.

## 🚀 Pre-requisites & Setup

1. **Python Environment**: Ensure you have Python installed (version 3.10 or higher is recommended).
2. **Setup Workspace**: Double-click **`setup_environment.bat`** to automatically create the folder structures and download the required baseline clean game ISO files:
   - `iso/unpatched/EQOA_Original.iso` (Original game disc)
   - `iso/unpatched/EQOA_Frontiers.iso` (Frontiers expansion disc)

*(Alternatively, if you already have clean unpatched copies of these ISOs, you can place them manually into the `iso/unpatched/` folder under these exact names).*

## 📁 Custom Assets & Baseline Merging Strategy

The pipeline uses the **Frontiers expansion assets** as the primary baseline to preserve Frontiers' high-quality textures, interfaces, customization menus, face databases, and character select screens.

* **`assets/Frontiers/`**: Contains the baseline Frontiers assets extracted in Step 2. These serve as the master baseline to ensure Frontiers' look and textures are fully preserved.
* **`assets/Vanilla/`**: Contains original Vanilla character databases. The 11 classic character models (Barbarian, Dark Elf, Dwarf, Elf, Erudite, Gnome, Halfling, Human-Eastern, Human-Western, Ogre, and Troll) are surgically grafted into the Frontiers database during Step 1, ensuring all 22 male/female versions are inherited cleanly without breaking Frontiers' layout or interface.

### Directory Structure & File Naming:
Within `assets/Frontiers/` (baseline) and `assets/Vanilla/` (sources), files reside in these locations:
* **`data/`**:
  - `CHAR.ESF` — Main character model database (the surgically grafted hybrid model database is fully preserved in the ISO).
  
* **`data2/`**:
  - `CHARCUST.CSF` — Compressed character customization database.
  - `CHARFACE.CSF` — Compressed character face database.
  - `CHARFACE.ESF` — Character face database.
  - `CHARSEL1.CSF`, `CHARSEL2.CSF`, `CHARSEL3.CSF`, `CHARSEL4.CSF` — Compressed character select files.

*(Note: Baseline Frontiers assets are extracted in Step 2 into `assets/Frontiers/` so that they can be used directly for character select interfaces).*

## ⚙️ Running the 4-Step Automated Patch Pipeline

To patch the game ISO and inject custom assets, run the following four batch scripts in order:

### 1️⃣ Step 1: Create Initial Frontiers Patched ISO (`steps/step1_create_patched_iso.bat`)
- **What it does**: Re-compiles the 11 native character model databases (Vanilla geometry grafted onto Frontiers skeleton for both male and female versions, 22 in total) and repacks them into a baseline frontiers ISO (`iso/patched/EQOA_Frontiers_Patched.iso`).

### 2️⃣ Step 2: Extract Baseline Frontiers Assets (`steps/step2_extract_assets.bat`)
- **What it does**: Automatically extracts baseline Frontiers CSF/ESF database files directly from your clean unpatched Frontiers ISO and saves them into the `assets/Frontiers/` directory.

### 3️⃣ Step 3: Merge Assets (`steps/step3_merge_assets.bat`)
- **What it does**: Copies the baseline Frontiers files from `assets/Frontiers/` into `assets/merged-assets/` (excluding `CHAR.ESF` to preserve the surgically patched database) and overlays Vanilla's `CHARSEL1.CSF`...`CHARSEL4.CSF` select screen database files. This inherits the 11 classic Vanilla character models (22 select screen versions) while keeping Frontiers' original customization databases, faces, and UI textures intact.

### 4️⃣ Step 4: Inject Assets (`steps/step4_inject_assets.bat`)
- **What it does**: Forcefully terminates any running `pcsx2-qt.exe` process (to prevent file lock conflicts), copies combined assets from `assets/merged-assets/` into the workspace folders, and surgically patches them in-place directly into the patched ISO. It concludes by running a high-integrity verification suite.

## 🎮 Playing the Game

Once the tool reports **`HIGH-FIDELITY STRUCTURAL TRANSPLANT PIPELINE EXECUTED SUCCESSFULLY`**:
1. Open the PCSX2 emulator.
2. Select and load: **`iso/patched/EQOA_Frontiers_Patched.iso`**.
3. The custom assets and character models will render in-game with zero visual artifacts or engine rendering crashes.
