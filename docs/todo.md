# EQOA Character Model Pipeline — High-Level Todo List

This checklist tracks high-level milestones and architectural deliverables required to complete the model restoration project successfully.

---

## High-Level Backlog & Milestones

- [x] **Phase 1: Engineering Infrastructure**
- [x] Create comprehensive engineering tracking files (`architecture.md`, `tech_stack.md`, `progress.md`, `tasks.md`, `todo.md`)
- [x] Establish a clean workspace and delete redundant, giant files

- [x] **Phase 2: Pristine Structural Upgrade Pipeline**
- [x] Implement `vanilla_to_frontiers_transplant.py` script
- [x] Extract the 11 target character models from Vanilla `CHAR.ESF`
- [x] Transform extracted models structurally:
- [x] Root node type: `0x62700` -> `0x72700`
- [x] Bone node type: `0x12400` -> `0x22400`
- [x] Expand child list (15 -> 17) and append Child 15 (`0x02950`) and Child 16 (`0x02960`)

- [x] Recursively update hierarchical node sizes and rebuild node buffers
- [x] Save hybrid model `.bin` payloads

- [x] **Phase 3: Database Merging, Asset Merging & ISO Repacking**
- [x] Run `esf_rebuilder.py` to merge the 11 upgraded `.bin` payloads into frontiers template
- [x] Run `repack_iso.py` to append the merged `CHAR.ESF` and patch ISO 9660 LBA/sizes
- [x] Run `patch_udf_char_esf_v2.py` with dynamic logical LBA calculation (`1,492,090`) and tag checksum computation
- [ ] Refactor `core/merge_assets.py` to copy Frontiers assets as baseline, exclude `CHAR.ESF` from copying, and overlay Vanilla's `CHARSEL1.CSF`...`CHARSEL4.CSF` select database files

- [x] **Phase 4: Robust Verification & Emulation Validation**
- [x] Validate ESF database structure has 0 parsing anomalies (using `verify_injected_models.py`)
- [x] Validate ISO file descriptors and binary sector matches (using `verify_final_patch.py` and `verify_final_iso.py`)
- [ ] Verify character select screen preserves Frontiers textures and looks
- [ ] Verify that only the 11 character models in their male/female versions (22 in total) are inherited from Vanilla
- [ ] Close emulator and verify character model visibility in-game _(Pending Phase 6 Manifest Alignment)_

- [x] **Phase 5: ISO Storage Reorganization & Path Restructuring**
- [x] Create distinct `iso/unmodified/` and `iso/patched/` directories
- [x] Migrate original game ISOs to `unmodified/` to preserve sterile base files
- [x] Update core Python scripts (`repack_iso.py`, `patch_udf_char_esf_v2.py`) to target the `patched/` output directory
- [x] Overhaul `run_patcher.bat` automation wrappers

- [ ] **Phase 6: Community Integration & Manifest Alignment (The Endgame)**
- [ ] Clone and link `EQOA_REPO_COLLECTION` to local `core/` path environment
- [ ] Run `geometry_sanitizer.py` to purge corrupted `NaN`/`Inf` floats and normalize VU1 vertex weights
- [ ] Implement `manifest_aligner.py` utilizing `DabDavis/eqoa-esf-tools`
- [ ] Map injected ESF structural IDs to the official target client schemas defined in `Jadiction/EQOA-Data`
- [ ] Perform a Full "Sterile" Boot in PCSX2 and successfully render the final integrated geometry in the live game world
