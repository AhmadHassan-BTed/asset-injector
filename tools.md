# EQOA Repo Collection Tools

The `EQOA_REPO_COLLECTION` directory contains a variety of community-built and reverse-engineered utility tools for working with EverQuest Online Adventures assets, server emulation, and game data.

Below is a summary of the most useful utility tools available, specifically those found in the `eqoa-esf-tools` toolkit which are invaluable for asset manipulation.

## ESF/CSF Game Asset Tools (`eqoa-esf-tools`)

These Go-based CLI tools are used to parse, inspect, export, and modify zones, models, textures, animations, and spell effects from the PS2 game files.

### Inspection & Extraction
* **`esfextract`** — Browse the ESF object tree, list zones, export meshes to `.obj` format, and decompress `.csf` files.
* **`dumpskeleton`** — Dump the full bone tree (parent chains, positions, rotations, scale) from `CSprite` character models. Essential for debugging skeletal animation and attachment points.
* **`dumpanim`** — Reverse-engineer `HSpriteAnim` (0x2600) binary format. Dumps keyframe data, bone mappings, and playback parameters.
* **`playlist-dump`** — Dump `CPlayList` animation data from character models to see slot-to-animation mapping and speeds.
* **`dumpparticle`** — Parse `ParticleDefinition` and `ParticleDefData` from spell effect files.
* **`dumpvariants` / `variantdump`** — Analyze `CSpriteVariant` structures used for armor/equipment mesh swapping.
* **`dumptslot`** — Map `TSlotList` entries to material indices and equipment slots on character models (e.g. helm, chest, robe).
* **`survey_mp`** — Scan ESF/CSF files for MaterialPalette and Material object versions.

### Modification & Repacking
* **`esfpatch`** — Create zone overlay patches for the `eqoa-pipeline` server without modifying the base ISO (e.g., swapping actor models, scaling terrain).
* **`esfimport`** — Replace zone geometry with standard `.obj` meshes in-place.
* **`esfrebuild`** — Rebuild a complete ESF file adjusting all size headers automatically after replacements.

### Media Extraction
* **`bgmextract`** — Decode PS2 SPU2-ADPCM background music files to `.wav`.
* **`dataextract`** — Extract EQOA text data and `.pak` archives, converting PS2 UTF-16LE strings to UTF-8.
* **`imgextract`** — Convert PS2 raw framebuffer images (.16 ABGR1555, .RGB) to `.png`.
* **`dumpatlas`** — Extract and crop UI atlas textures from `UI.ESF`.
* **`helmcheck` / `helmdiag`** — Search for helmet textures across multiple files and export slot 7 materials.
* **`extract-armor-tex`** — Extract armor set textures from `CHARCUST.CSF` as `.png` files.

## Other Key Repositories & Tools

Beyond the ESF tools, the collection contains various server emulators, patches, and client addons:

### Core Formats and Decompilation Tools
* **`ESF-file-format` (Java)**
  * **Usage**: A Java library primarily used for the structural parsing and decompression of the game's assets. It is best used if you are building a server emulator or need to integrate game data into a Java application.
  * **Decompression**: You must use the included `CSFFile` class to strip the proprietary headers from `.csf` files and decompress the zlib streams into raw `.esf` files.
  * **Terrain & Collision**: It contains specific modules (Terrain Collision Buffers Loader) to read the invisible "physical" boundaries of the map (Tunaria), which is essential if you are trying to modify where players can walk or clip.
  * **Node Parsing**: It breaks down the binary file into a node tree (floats, integers, arrays), allowing you to inspect 3D object nodes programmatically.

* **`eqoa-esf-tools` (Go)**
  * **Usage**: A Command Line Interface (CLI) tool written in Go, designed for direct asset extraction and modification without writing your own code wrapper.
  * **Inspection**: You run the tool from a terminal to "dump" the contents of an ESF/CSF file into a human-readable format to see what assets are inside (textures, models, animations).
  * **ISO Interaction**: Uniquely, this tool can read data directly from the game's raw disc image (`.iso`), allowing you to pull assets without manually extracting the file system first.
  * **Exporting**: It is used to convert proprietary EQOA models and textures into standard formats that modern 3D software (like Blender) can read.

### Server Emulators
* **`Sandstorm / EQOA-Server` (Java)**
  * **Usage**: While primarily a server emulator, this repository contains the implementation logic for how `.esf` files are actually used by the game engine.
  * **Reference**: Use this if you have successfully modified an ESF file but the game crashes upon loading it. You can check this code to see exactly how the server expects the data to be formatted (e.g., verifying that your modified float values for a character's spawn point match the required byte alignment).

* **`EQOAGameServer`** — A modern C# .NET game server emulator implementation featuring Docker containerization, an Authentication Server, and an EQOA Crypto Library for handling packet encryption.
* **`ben_eqoa_c_server`** — A lightweight, C-based UDP server implementation focusing on raw packet handling (`UDPServer.c`) and CRC calculations (`crc_calc.c`).
* **`OpenEQOA` / `EQOA-server` / `bkr-original-server`** — Earlier iterations and forks of the EQOA server emulator logic (primarily Java/C based).
* **`EQOA_Creator`** / **`NPC Creator`** — A C++/Qt GUI application designed for database management, creating/managing NPC spawns, world mapping (`checkthezone.cpp`), and parsing opcodes/packets visually.

### Client Modifications & Addons
* **`EQOA-Frontiers-ISO-Patch`** — Contains a Python-based utility (`EQOA Frontiers ISO Patch.py`) for directly modifying and patching the game's `.iso` file.
* **`EQOA_Addons`** — A collection of Lua scripts (e.g., `InventoryManager.lua`, `XPPace.lua`, `CharStatsResistsXP.lua`) designed to be run alongside the game (likely via PCSX2's scripting engine) to track gear, calculate XP rates, and manage inventory.
* **`eqoa-pipeline`** — Tooling related to patching the game at runtime by serving zone/asset patches over the network dynamically without ISO modification.

> [!TIP]
> When performing hex edits or deep binary modifications (like our character transplant), referencing the Go structs in `eqoa-esf-tools/pkg/esf/types.go` and `sprites.go` is the most accurate way to map out the `CHAR.ESF` hierarchical node structure.
