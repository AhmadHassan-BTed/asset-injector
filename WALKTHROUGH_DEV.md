# EQOA Developer Walkthrough: Sector-Level Multi-Asset Patcher

This walkthrough details the low-level binary surgery, UDF structure patching, and architectural implementation of the custom asset injection pipeline designed to bypass PS2 disc driver limitations.

## 🧠 Architectural Overview & Problem Statement

Standard ISO builders like `mkisofs` or Python's `pycdlib` library reorganize sector layouts on disc. While this produces valid standard UDF/ISO 9660 filesystems, the PlayStation 2's custom `cdvdman` driver and hardcoded Emotion Engine game executables expect files at **exact sector positions (LBAs)**. Shifting these positions causes immediate black screens at `Sector 257` during boot.

To bypass this constraint, this pipeline implements **Zero-Reorganization Sector Binary Patching**:
1. Take the clean original PS2 ISO.
2. Align the end of the partition to a 2048-byte sector boundary.
3. Append new/updated files at the end of the ISO contiguously.
4. Surgically byte-patch both the **ISO 9660 directory records** and **UDF File Entries** to point to the new sectors.
5. Append the UDF Anchor Volume Descriptor Pointer (AVDP) sector as an extra final sector to preserve partition layout without overlapping file sectors.

## 📁 Parent Assets Folder Structure & Decoupled Overlay Pipeline

The repository organizes database and layout assets under a unified parent directory:
- **`assets/Frontiers/`**: Baseline folder where clean Frontiers base assets (character select screens, customization database, etc.) are extracted. These serve as our primary baseline to preserve Frontiers textures.
- **`assets/Vanilla/`**: Source folder containing original Vanilla EQOA model databases used for transplanting character models.

### 🔄 The Decoupled Merge Pipeline (`core/merge_assets.py`)
Decoupled from the initial database compilation, the merger script `core.merge_assets` is invoked as Step 3 in the pipeline. This script:
1. Clears and creates the temporary `assets/merged-assets/` folder (which is ignored by Git to avoid tracking transient compile artifacts).
2. Recursively copies the baseline files from `assets/Frontiers/` into `assets/merged-assets/` (excluding `CHAR.ESF` to preserve the surgically recompiled database in Step 4).
3. Surgically overlays Vanilla's `CHARSEL1.CSF`...`CHARSEL4.CSF` files on top of the Frontiers baseline. This inherits the 11 classic Vanilla character models (22 select screen versions) for character selection, while preserving Frontiers' original customization database (`CHARCUST.CSF`), face database (`CHARFACE.CSF`, `CHARFACE.ESF`), and UI textures completely intact.
4. The subsequent surgical patch step (`core/patch_placed_assets.py` as Step 4) reads these combined payloads from `assets/merged-assets/` and applies them directly.

## 💾 Sector Mapping & Offsets

The pipeline targets 8 primary assets, whose exact sector offsets in the original Frontiers disc and their UDF File Entry sectors are documented below:

| File Target | Original LBA | FE Sector | ISO 9660 Name Pattern |
|---|---|---|---|
| `/DATA/CHAR.ESF` | `3578` | `337` | `b'\x0ACHAR.ESF;1'` |
| `/DATA2/CHARCUST.CSF` | `83457` | `358` | `b'\x0ECHARCUST.CSF;1'` |
| `/DATA2/CHARFACE.CSF` | `79634` | `349` | `b'\x0ECHARFACE.CSF;1'` |
| `/DATA2/CHARFACE.ESF` | `78055` | `342` | `b'\x0ECHARFACE.ESF;1'` |
| `/DATA2/CHARSEL1.CSF` | `83792` | `359` | `b'\x0ECHARSEL1.CSF;1'` |
| `/DATA2/CHARSEL2.CSF` | `79104` | `348` | `b'\x0ECHARSEL2.CSF;1'` |
| `/DATA2/CHARSEL3.CSF` | `78486` | `345` | `b'\x0ECHARSEL3.CSF;1'` |
| `/DATA2/CHARSEL4.CSF` | `81087` | `352` | `b'\x0ECHARSEL4.CSF;1'` |

## 🛠️ Low-Level Surgical Logic (`core/patch_placed_assets.py`)

### 1. ISO 9660 Directory Record Patching
The script uses memory-mapped files (`mmap`) to search for the unique ISO 9660 record pattern `b'\x<LEN><NAME>;1'`. Once located, it offsets back 32 bytes to find the record start (`dr_start = idx - 32`) and surgically patches:
- **LBA**: 4-byte Little Endian at `dr_start + 2` and 4-byte Big Endian at `dr_start + 6`.
- **Size**: 4-byte Little Endian at `dr_start + 10` and 4-byte Big Endian at `dr_start + 14`.

### 2. UDF File Entry (FE) Sector Patching
Each file entry on a UDF partition has a dedicated UDF File Entry sector. The script reads this sector, verifies the Tag Identifier (`0x0105` at byte 0), and patches:
- **UDF Information Length**: 8-byte LE at `0x38` updated to the exact new size.
- **UDF Allocation Descriptor**: Located at `0xB0 + L_EA`. Upgraded to the new file size and the new **partition relative LBA** (`LBA - 278`), retaining the upper 2 bits of extent length flags.
- **Checksum**: The first 16 bytes of the descriptor tag are checksummed (`fe_raw[4] = sum(fe_raw[:16]) & 0xFF`), validating the modified tag structure.

### 3. Partition End & AVDP Splicing
Splicing the Anchor Volume Descriptor Pointer (AVDP) sector at the exact final sector (LBA `total_sectors - 1`) is mandatory for UDF volume compliance. The script:
- Aligns the ISO size to 2048 bytes after appending all files.
- Reads the AVDP sector from sector 256.
- Appends the 2048 bytes of AVDP to the end of the partition as a standalone sector, ensuring it does not overlap with `CHARSEL4.CSF`'s file data.
- Updates the total sector count in the Primary Volume Descriptor (PVD) at offset `16 * 2048 + 80`.

## 🧪 Verification & Integrity Checks

Developers can run `core/verify_final_patch.py` to bitwise-verify:
- UDF allocation descriptor size and relative LBA match current inputs.
- ISO 9660 directory record LBA and size values match physical disc LBAs.
- Magic signature (`FJBO` or `ECS\x1a`) exists at the modified starting LBA to confirm proper binary alignment.
