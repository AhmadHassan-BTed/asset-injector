# EQOA Character Restoration & Hybrid Graft Pipeline

![Platform](https://img.shields.io/badge/Platform-PS2%20(PCSX2)-blue)
![Language](https://img.shields.io/badge/Language-Python%203.12-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

A highly specialized reverse-engineering pipeline designed to structurally transplant original Vanilla character models into the *EverQuest Online Adventures: Frontiers* (PS2) game engine, resolving complex Vector Unit 1 (VU1) shader bugs, Emotion Engine (EE) memory overflows, and PS2 CDVDman hardware faults.

## Current Status: Solved (The Geometry-Only Macro-Node Transplant)

The invisible character bug and the subsequent `0x0` TLB Miss CPU crashes have been completely resolved.

Through aggressive live RAM tracing and binary auditing, we discovered the precise causes of the rendering rejections and memory faults, and have successfully developed a reliable injection pipeline that produces bootable, 100% playable ISOs with restored Vanilla character geometry.

## The Context & Technical Problem

When attempting to inject original EQOA Vanilla character models into the *Frontiers* client, the game engine repeatedly crashed with a `TLB Miss at pc=0x0`, or the character rendered completely invisible. The investigation uncovered three massive architectural hurdles:

1. **The Emotion Engine (EE) Skeleton Overflow:** Vanilla Ogre models use a 32-bone skeleton, while Frontiers uses a 43-bone skeleton. When we injected the Vanilla `0x0B070` Skeleton Node, the hard-coded Frontiers Animation Controller continued to generate 43 matrices per frame. This caused a catastrophic buffer overflow in the EE Main RAM, overwriting the virtual function table for the `CharacterModel` object and causing the CPU to dereference a NULL pointer (`pc=0x80005558 addr=0x0`).
2. **Frankenstein DMA Tag Misalignment:** Early attempts to splice Vanilla floating point arrays into Frontiers DMA packets broke the rigid 16-byte DMA tag alignment required by the PS2's Graphics Synthesizer. The VU1 parser read vertex floats as DMA headers, aborted the display list generation, and rejected the model.
3. **ADC Bit Destruction:** In PS2 VU1 programming, the `W` component of a `V4-32` vertex structure contains the Anti-Double-Clipping (ADC) bit in the sign bit. Early attempts to clamp bone indices by zeroing the `W` component utterly destroyed the geometry payload.
4. **State-Dependent Rendering Rejection:** The Frontiers engine uses updated Material definitions. If a model was injected with Vanilla `0x11110` material headers, the GS rejected the texture mapping and rendered nothing (the "Invisible Character" bug).

## The Solution: Geometry-Only Macro-Node Transplant

To completely bypass these architecture mismatches, we implemented the **Geometry-Only Macro-Node Transplant**:

1. **Retain Frontiers Headers:** We extract the native Frontiers `0x72700` model wrapper to serve as a structurally pristine base.
2. **Preserve EE Buffer Allocation:** We **RETAIN** the Frontiers `0x0B070` Skeleton Node and `0x02800` Bone Matrices. This provides the Animation Controller with the exact 43-bone array memory allocation it expects, completely preventing the EE buffer overflow.
3. **Preserve Material State:** We **RETAIN** the Frontiers `0x11110` Material Node to prevent the renderer from rejecting the mesh.
4. **Pristine DMA Injection:** We swap the **ENTIRE** `0x02610` Geometry Node from the Vanilla payload directly into the Frontiers tree. By moving the macro-node whole, we preserve the original Vanilla DMA chain logic and VU1 microprogram instructions perfectly, without breaking 16-byte alignment.
5. **In-Place Binary ISO Repacking:** Standard ISO builders like `pycdlib` destroy the LBA directory records expected by the PS2's `cdvdman` driver, resulting in a black screen at `Sector 257`. Instead, we use `core/repack_iso.py` to byte-patch the new `CHAR.ESF` payload **directly** into the original, unmodified PS2 ISO, and patch the UDF Allocation Descriptors to point to the new lengths.

## Features & Tooling

- **`core/clean_transplant_geom_only.py`**: The ultimate reverse-engineering script that handles the Macro-Node Graft Logic.
- **`core/repack_iso.py` & `core/patch_udf_char_esf_v2.py`**: The In-Place Binary Sector repacker and UDF descriptor patcher.
- **`core/validate_dma.py`**: A low-level DMA tag integrity verifier.
- **`core/audit_materials.py` & `core/w_component_audit.py`**: Raw Hex/Float array validation scripts.

## Utilities

External EQOA tools and reference implementations are kept under `UTILITIES/`. These projects were authored and maintained by their respective creators; this repository keeps them organized as utility references for asset research, format inspection, server behavior, ISO patching, and workflow automation.

See `CHANGELOG.md` for the utility rename and attribution notes.

## Getting Started & Environment Setup

1. Clone or download this repository.
2. Double-click **`setup_environment.bat`**.
3. The script will automatically download the required baseline ISOs directly into the correct folders:
   - `iso/unpatched/EQOA_Original.iso` (Vanilla)
   - `iso/unpatched/EQOA_Frontiers.iso` (Expansion)

Once the setup script finishes, you are ready to patch!

## Usage

The entire suite is abstracted into a single automated interface.

1. Ensure you have run `setup_environment.bat`.
2. Double-click **`EQOA_MASTER_TOOL.bat`**.

### Options:

- **[1] Patch Game ISO**: Executes the pristine Geometry-Only Macro-Node Transplant. It parses the databases, surgically upgrades the target character assets, repacks the `CHAR.ESF` using the In-Place Binary Patcher, and generates a bootable `iso/patched/EQOA_Frontiers_Patched.iso`.

*(Ensure your emulator is CLOSED before running the patcher to prevent file lock `[Errno 13] Permission Denied` errors).*