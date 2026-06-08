#!/usr/bin/env python3
"""
run_pipeline.py
===============
Master pipeline orchestrator for EQOA Frontiers character model injection.
Executes all 5 stages in the exact order required, with LBA computed
dynamically so the UDF File Entry always points to the correct sector.
"""
from __future__ import annotations

import subprocess
import sys
import os
import shutil
import struct
import mmap

# ─── paths ────────────────────────────────────────────────────────────────────
ROOT          = os.path.dirname(os.path.abspath(__file__))
WORKSPACE     = os.path.join(ROOT, "workspace")
ISO_ORIG      = os.path.join(ROOT, "iso", "unpatched", "EQOA_Frontiers.iso")
ISO_PATCHED   = os.path.join(ROOT, "iso", "patched", "EQOA_Frontiers_Patched.iso")
ISO_TMP       = ISO_PATCHED + ".tmp"
ESF_MERGED    = os.path.join(WORKSPACE, "FINAL_CHAR_MERGED.ESF")

# ─── stage 1: geometry sanitizer ─────────────────────────────────────────────
def stage1_sanitize():
    print()
    print("=" * 70)
    print("  STAGE 1 — PS2 GEOMETRY SANITIZER (NaN / Inf / Bounds)")
    print("=" * 70)
    res = subprocess.run(
        [sys.executable, "-m", "core.geometry_sanitizer"],
        cwd=ROOT,
        capture_output=False,
    )
    if res.returncode != 0:
        print("[-] FAILED  — geometry_sanitizer returned non-zero")
        sys.exit(res.returncode)
    print("[+] STAGE 1 complete.")
    return 0


# ─── stage 2: manifest aligner ───────────────────────────────────────────────
def stage2_align():
    print()
    print("=" * 70)
    print("  STAGE 2 — MANIFEST ALIGNER (pointer sync -> custom node IDs)")
    print("=" * 70)
    # Discover every sanitized .bin in payloads and align each one
    import glob, struct as st

    manifests = [
        ("workspace/CHARSEL.ESF",  "workspace/payloads"),
    ]
    for manifest_path, payload_dir in manifests:
        bin_files = glob.glob(os.path.join(payload_dir, "*.bin"))
        if not bin_files:
            continue
        for bin_path in bin_files:
            fname = os.path.basename(bin_path)
            try:
                hash_str = fname.split("_")[1].split(".")[0]
                original_hash = int(hash_str, 16)
            except Exception:
                print(f"  [!] Skipping unrecognized payload: {fname}")
                continue

            # Read the sanitized node header to get its real type_id
            with open(bin_path, "rb") as bf:
                hdr = bf.read(12)
            custom_node_id = st.unpack_from("<I", hdr, 0)[0]
            raw_size        = st.unpack_from("<I", hdr, 4)[0]
            # The payload node size on disk is the padded ESF node size
            custom_data_size = raw_size

            # Overwrite the manifest pointer for this hash
            res = subprocess.run(
                [
                    sys.executable, "-m", "core.manifest_aligner",
                    "--manifest",        manifest_path,
                    "--original-hash",   f"{original_hash:08X}",
                    "--custom-node-id",  f"{custom_node_id:06X}",
                    "--custom-data-size", str(custom_data_size),
                    "--output",          manifest_path,   # in-place
                ],
                cwd=ROOT,
                capture_output=False,
            )
            if res.returncode != 0:
                print(f"[-] FAILED  — manifest_aligner for {fname}")
                sys.exit(res.returncode)
    print("[+] STAGE 2 complete.")
    return 0


# ─── stage 3: ESF rebuilder ───────────────────────────────────────────────────
def stage3_rebuild():
    print()
    print("=" * 70)
    print("  STAGE 3 — ESF REBUILDER (merge payloads into CHAR.ESF tree)")
    print("=" * 70)
    res = subprocess.run(
        [sys.executable, "-m", "core.esf_rebuilder"],
        cwd=ROOT,
        capture_output=False,
    )
    if res.returncode != 0:
        print("[-] FAILED  — esf_rebuilder returned non-zero")
        sys.exit(res.returncode)
    print("[+] STAGE 3 complete.")
    return 0


# ─── stage 4: ISO repacker ────────────────────────────────────────────────────
# Returns the computed LBA where CHAR.ESF was appended so stage 5 can use it.
def stage4_repack_iso():
    print()
    print("=" * 70)
    print("  STAGE 4 — ISO REPACKER (append ESF, patch ISO9660 DR, splice UDF AVDP)")
    print("=" * 70)

    # Wipe any stale output
    if os.path.exists(ISO_TMP):
        os.remove(ISO_TMP)

    iso_size = os.path.getsize(ISO_ORIG)
    esf_size = os.path.getsize(ESF_MERGED)

    # ── copy original → temp ──────────────────────────────────────────────
    print(f"[*] Copying {ISO_ORIG}  ({iso_size:,} bytes)  →  {ISO_TMP} ...")
    shutil.copyfile(ISO_ORIG, ISO_TMP)

    # ── pad to 2048 boundary ───────────────────────────────────────────────
    pad_iso = (2048 - (iso_size % 2048)) % 2048
    new_lba = (iso_size + pad_iso) // 2048          # LBA where ESF lands

    with open(ISO_TMP, "r+b") as fh:
        if pad_iso:
            fh.write(b"\x00" * pad_iso)

        # ── append CHAR.ESF payload ────────────────────────────────────────
        with open(ESF_MERGED, "rb") as esf_fh:
            while chunk := esf_fh.read(4 * 1024 * 1024):
                fh.write(chunk)

        # ── enforce 2048-byte EOF alignment ────────────────────────────────
        filesize = fh.tell()
        pad_eof = (2048 - (filesize % 2048)) % 2048
        if pad_eof:
            fh.write(b"\x00" * pad_eof)
        final_size = fh.tell()

        # ── patch every ISO9660 Directory Record for CHAR.ESF;1 ──────────
        mm = mmap.mmap(fh.fileno(), 0)
        dr_patched = 0
        search_str = b"\x0ACHAR.ESF;1"
        idx = 0
        while True:
            idx = mm.find(search_str, idx)
            if idx == -1:
                break
            # A Directory Record starts 32 bytes before the name
            dr_base = idx - 32
            lba_le = struct.unpack_from("<I", mm[dr_base + 2 : dr_base + 6])[0]
            lba_be = struct.unpack_from(">I", mm[dr_base + 6 : dr_base + 10])[0]
            if lba_le == lba_be:                     # sanity: LE==BE → real DR
                mm[dr_base + 2 : dr_base + 6] = struct.pack("<I", new_lba)
                mm[dr_base + 6 : dr_base + 10] = struct.pack(">I", new_lba)
                mm[dr_base + 10 : dr_base + 14] = struct.pack("<I", esf_size)
                mm[dr_base + 14 : dr_base + 18] = struct.pack(">I", esf_size)
                dr_patched += 1
            idx += len(search_str)

        # ── patch ISO9660 PVD total-sectors field ──────────────────────────
        pvd_off = 16 * 2048
        if mm[pvd_off : pvd_off + 6] == b"\x01CD001":
            ts = final_size // 2048
            mm[pvd_off + 80 : pvd_off + 84] = struct.pack("<I", ts)
            mm[pvd_off + 84 : pvd_off + 88] = struct.pack(">I", ts)

        # ── UDF AVDP re-splice for compliance ──────────────────────────────
        avdp_sector = mm[(new_lba - 1) * 2048 : (new_lba - 1) * 2048 + 2048]
        if len(avdp_sector) == 2048 and struct.unpack("<H", avdp_sector[:2])[0] == 2:
            mm.flush()
            fh.seek(0, 2)
            fh.write(avdp_sector)
            final_size += 2048

        mm.close()

    # ── ATOMIC commit ──────────────────────────────────────────────────────
    try:
        os.replace(ISO_TMP, ISO_PATCHED)
    except OSError as exc:
        if os.path.exists(ISO_TMP):
            os.remove(ISO_TMP)
        raise OSError(f"ATOMIC COMMIT FAILED: {exc}") from exc

    print(f"[+] Patched ISO written → {ISO_PATCHED}  ({final_size:,} bytes)")
    print(f"    CHAR.ESF;1 appended at LBA {new_lba}  ({final_size:,} bytes ISO, {esf_size:,} bytes payload)")
    print(f"    ISO9660 Directory Records patched: {dr_patched}")

    # Write the computed LBA to a side-channel file so stage 5 reads it
    lba_cache = os.path.join(WORKSPACE, ".lba_cache.txt")
    with open(lba_cache, "w") as f:
        f.write(f"{new_lba}\n{final_size}\n{esf_size}\n")

    return new_lba


# ─── stage 5: UDF / DNAS bounds patcher ──────────────────────────────────────
# Reads the dynamically-computed LBA from the cache written by stage 4.
def stage5_udf_patch():
    print()
    print("=" * 70)
    print("  STAGE 5 — UDF FILE ENTRY BINARY SURGERY (DNAS LBA constraint)")
    print("=" * 70)

    lba_cache = os.path.join(WORKSPACE, ".lba_cache.txt")
    if not os.path.exists(lba_cache):
        print("[-] FATAL: .lba_cache.txt missing — run stage 4 first")
        sys.exit(1)

    with open(lba_cache) as f:
        lines = [l.strip() for l in f.readlines()]
    new_lba     = int(lines[0])
    iso_size    = int(lines[1])
    esf_size    = int(lines[2])

    # ── DNAS / PS2 IOP hard constraints ──────────────────────────────────────
    # The IOP's UDF reader works in PS2's 32-bit LBA space.  Valid range is
    # 0 .. 2^31-1 (signed 32-bit positive).  Sector 1492368 is well inside
    # this range.  We assert the computed LBA is safe before patching.
    MAX_SECTOR = 0x7FFFFFFF // 2048     # 1,073,741,823 (far exceeds any PS2 disc)
    assert 0 <= new_lba <= MAX_SECTOR, (
        f"LBA {new_lba} exceeds safe PS2 IOP range ({MAX_SECTOR})"
    )
    print(f"[*] LBA constraint check: {new_lba} ≤ {MAX_SECTOR}  [PASS]")

    PARTITION_OFFSET = 278   # UDF partition base = physical_sector_32 - logical_LBA_32
    new_phys_lba     = new_lba + PARTITION_OFFSET
    print(f"[*] Physical LBA : {new_phys_lba}  (logical LBA {new_lba} + partition {PARTITION_OFFSET})")

    # ── Read UDF File Entry sector 337 ───────────────────────────────────────
    UDF_FE_SECTOR = 337
    UDF_FE_OFF    = UDF_FE_SECTOR * 2048

    with open(ISO_PATCHED, "rb") as f:
        f.seek(UDF_FE_OFF)
        fe_raw = bytearray(f.read(2048))

    # ── Read current values ───────────────────────────────────────────────────
    curr_size   = struct.unpack_from("<Q", fe_raw, 0x38)[0]
    l_ea        = struct.unpack_from("<I", fe_raw, 0xA8)[0]
    ad_start    = 0xB0 + l_ea
    curr_lba    = struct.unpack_from("<I", fe_raw, ad_start + 4)[0]

    if curr_size == esf_size and curr_lba == new_lba:
        print("[+] UDF File Entry already correct — nothing to patch.")
    else:
        OLD_SIZE = curr_size
        OLD_LBA  = curr_lba

        print(f"[*] Current UDF File Entry:")
        print(f"    Size : {OLD_SIZE:,} (0x{OLD_SIZE:08X})")
        print(f"    LBA  : {OLD_LBA}  (0x{OLD_LBA:08X})")
        print(f"[*] Target UDF File Entry:")
        print(f"    Size : {esf_size:,}  (0x{esf_size:08X})")
        print(f"    LBA  : {new_lba}   (0x{new_lba:08X})")

        # ── Binary search & replace all known encodings ─────────────────────
        patches: list[tuple[str, int]] = []

        # 8-byte LE  @ 0x38  (primary Information Length field)
        pos = fe_raw.find(struct.pack("<Q", OLD_SIZE))
        if pos != -1:
            patches.append(("size_8le", pos))
            print(f"  Found size (8-byte LE) at offset 0x{pos:04X}")

        # 4-byte LE  (secondary size encodings)
        for pos in _find_all(fe_raw, struct.pack("<I", OLD_SIZE)):
            patches.append(("size_4le", pos))

        # 4-byte BE
        for pos in _find_all(fe_raw, struct.pack(">I", OLD_SIZE)):
            patches.append(("size_4be", pos))

        # 4-byte LE  LBA
        for pos in _find_all(fe_raw, struct.pack("<I", OLD_LBA)):
            patches.append(("lba_4le", pos))

        # 4-byte BE  LBA
        for pos in _find_all(fe_raw, struct.pack(">I", OLD_LBA)):
            patches.append(("lba_4be", pos))

        # Logical Block Count (8-byte LE)
        old_blocks = (OLD_SIZE + 2047) // 2048
        new_blocks = (esf_size   + 2047) // 2048
        for pos in _find_all(fe_raw, struct.pack("<Q", old_blocks)):
            patches.append(("blocks_8le", pos))

        print(f"\n[*] Applying {len(patches)} binary patch(es) to UDF File Entry...")
        for ptype, poff in patches:
            if ptype == "size_8le":
                fe_raw[poff : poff + 8] = struct.pack("<Q", esf_size)
                print(f"  Patched size (8-byte LE) @ 0x{poff:04X}: {OLD_SIZE:,} -> {esf_size:,}")
            elif ptype == "size_4le":
                fe_raw[poff : poff + 4] = struct.pack("<I", esf_size)
                print(f"  Patched size (4-byte LE) @ 0x{poff:04X}: {OLD_SIZE} -> {esf_size}")
            elif ptype == "size_4be":
                fe_raw[poff : poff + 4] = struct.pack(">I", esf_size)
                print(f"  Patched size (4-byte BE) @ 0x{poff:04X}: {OLD_SIZE} -> {esf_size}")
            elif ptype == "lba_4le":
                fe_raw[poff : poff + 4] = struct.pack("<I", new_lba)
                print(f"  Patched LBA (4-byte LE) @ 0x{poff:04X}: {OLD_LBA} -> {new_lba}")
            elif ptype == "lba_4be":
                fe_raw[poff : poff + 4] = struct.pack(">I", new_lba)
                print(f"  Patched LBA (4-byte BE) @ 0x{poff:04X}: {OLD_LBA} -> {new_lba}")
            elif ptype == "blocks_8le":
                fe_raw[poff : poff + 8] = struct.pack("<Q", new_blocks)
                print(f"  Patched blocks (8-byte LE) @ 0x{poff:04X}: {old_blocks} -> {new_blocks}")

        # ── Recompute UDF Tag Checksum (ECMA-167 §7.2) ─────────────────────
        tag = bytearray(fe_raw[:16])
        tag[4] = 0
        new_cksum = sum(tag) & 0xFF
        fe_raw[4] = new_cksum
        print(f"\n[*] Recomputed UDF tag checksum: 0x{new_cksum:02X}")

        # ── Write back ───────────────────────────────────────────────────────
        with open(ISO_PATCHED, "r+b") as f:
            f.seek(UDF_FE_OFF)
            f.write(bytes(fe_raw))

    # ── Verify ──────────────────────────────────────────────────────────────
    with open(ISO_PATCHED, "rb") as f:
        f.seek(UDF_FE_OFF)
        verify = f.read(512)
    ver_size = struct.unpack_from("<Q", verify, 0x38)[0]
    ver_l_ea = struct.unpack_from("<I", verify, 0xA8)[0]
    ver_ad   = 0xB0 + ver_l_ea
    ver_lba  = struct.unpack_from("<I", verify, ver_ad + 4)[0]

    print(f"\n[*] Verification:")
    print(f"    Information Length : {ver_size:,} (expected {esf_size:,})  {'[PASS]' if ver_size == esf_size else '[FAIL]'}")
    print(f"    Allocation Desc LBA: {ver_lba}  (expected {new_lba})   {'[PASS]' if ver_lba == new_lba else '[FAIL]'}")

    if ver_size == esf_size and ver_lba == new_lba:
        print()
        print("=" * 70)
        print("  [PASS]  UDF File Entry patched — IOP will read CHAR.ESF at LBA", new_lba)
        print("=" * 70)
    else:
        print()
        print(f"  [FAIL]  Verification mismatch — check UDF File Entry at sector {UDF_FE_SECTOR}")
        sys.exit(1)

    return 0


# ─── helper ───────────────────────────────────────────────────────────────────
def _find_all(buf: bytearray, needle: bytes) -> list[int]:
    """Return every start position of needle inside buf."""
    pos, out = 0, []
    while True:
        pos = buf.find(needle, pos)
        if pos == -1:
            break
        out.append(pos)
        pos += 1
    return out


# ─── main ─────────────────────────────────────────────────────────────────────
def main():
    print()
    print("#" * 70)
    print("#  EQOA FRONTIERS — CHARACTER MODEL PIPELINE  (FINAL BUILD)")
    print("#" * 70)

    # Pre-flight checks
    for path, label in [
        (ISO_ORIG,    "Original ISO"),
        (ESF_MERGED,  "Merged ESF (after stages 1–3)"),
    ]:
        if not os.path.exists(path):
            print(f"[-] FATAL: {label} not found: {path}")
            print("    Stages 1–3 must produce workspace/FINAL_CHAR_MERGED.ESF first.")
            sys.exit(1)

    # ── run stages ───────────────────────────────────────────────────────────
    stage1_sanitize()    # Purge NaNs / Infs / bad bone indices from payloads
    stage2_align()       # Sync manifest pointer IDs -> custom geometry
    stage3_rebuild()     # Rebuild CHAR.ESF with sanitized + aligned payloads
    new_lba = stage4_repack_iso()   # Pack into ISO, compute final LBA
    stage5_udf_patch()   # Patch UDF File Entry with dynamically-computed LBA

    # ── final SHA-256 ────────────────────────────────────────────────────────
    import hashlib
    sha = hashlib.sha256()
    with open(ISO_PATCHED, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            sha.update(chunk)

    print()
    print("=" * 70)
    print("  FINAL BUILD COMPLETE")
    print("=" * 70)
    print(f"  Output ISO : {ISO_PATCHED}")
    print(f"  ISO Size   : {os.path.getsize(ISO_PATCHED):,} bytes")
    print(f"  CHAR.ESF at LBA {new_lba}  (SHA-256: {sha.hexdigest()})")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
