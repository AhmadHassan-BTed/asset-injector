#!/usr/bin/env python3
"""
patch_ingame_models.py
======================
Surgically grafts, sanitizes, and injects the 22 player character models into the active gameplay model database.
Responsible for:
1. Low-level structural model grafting (grafting Vanilla meshes/textures into Frontiers templates).
2. Purging float NaNs, normalizing vertex weights, and clamping bone indices (MIPS rendering compliance).
3. Compiling the database to FINAL_CHAR_MERGED.ESF.
4. Repacking and sector-patching CHAR.ESF in-place into the patched game ISO contiguously.
"""
import os
import sys
# Add repository root to python path for modular core imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import struct
import mmap
import json
import subprocess

def run_transplant_surgery():
    print("[*] Phase 1: Executing low-level model grafts...")
    # Import parser and pristine upgrade logic directly
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from core.esf_parser import ESFParser
    from core.pristine_structural_upgrade import pristine_structural_upgrade, parse_node
    
    json_path = 'workspace/target_assets.json'
    original_esf = 'workspace/original/CHAR.ESF'
    expansion_esf = 'workspace/expansion/CHAR.ESF'
    payloads_dir = 'workspace/payloads'
    
    # 0. Extract databases if necessary
    print("  [*] Extracting database templates...")
    subprocess.run([sys.executable, "-m", "core.extract_databases"], check=True)
    
    # 1. Load targets mapping
    if not os.path.exists(json_path):
        print(f"  [-] Error: Targets mapping {json_path} not found!")
        sys.exit(1)
        
    with open(json_path, 'r') as f:
        targets = json.load(f)
        
    with open(original_esf, 'rb') as f:
        van_esf_bytes = f.read()
    van_parser = ESFParser(van_esf_bytes).parse()
    van_map = {e.asset_id: e for e in van_parser.pointer_table if e.asset_id is not None}
    
    with open(expansion_esf, 'rb') as f:
        fro_esf_bytes = f.read()
    fro_parser = ESFParser(fro_esf_bytes).parse()
    fro_map = {e.asset_id: e for e in fro_parser.pointer_table if e.asset_id is not None}
    
    if os.path.exists(payloads_dir):
        shutil.rmtree(payloads_dir)
    os.makedirs(payloads_dir, exist_ok=True)
    
    for idx, t in enumerate(targets):
        h = int(t['expansion_hash'], 16)
        van_entry = van_map[h]
        vanilla_bytes = van_esf_bytes[van_entry.offset : van_entry.offset + van_entry.length]
        fro_entry = fro_map[h]
        frontiers_bytes = fro_esf_bytes[fro_entry.offset : fro_entry.offset + fro_entry.length]
        
        final_payload = pristine_structural_upgrade(vanilla_bytes, frontiers_bytes, f"0x{h:08X}")
        
        bin_path = os.path.join(payloads_dir, f"asset_0x{h:08X}.bin")
        with open(bin_path, 'wb') as f:
            f.write(final_payload)
            
    print("  [+] Low-level model surgery complete. Payload bins saved.")

def sanitize_mesh_payloads():
    print("\n[*] Phase 2: Purging corrupted vertex weight floats & index clamping...")
    from core.geometry_sanitizer import sanitize_buffer, parse_node, serialize_node
    import glob
    
    payloads = glob.glob("workspace/payloads/*.bin")
    if not payloads:
        print("  [-] Error: No payload files found! Please run the transplant phase first.")
        sys.exit(1)
        
    total_nans = 0
    total_weights = 0
    total_indices = 0
    
    for payload in payloads:
        with open(payload, 'rb') as f:
            data = bytearray(f.read())
            
        root, _ = parse_node(data, 0)
        
        def scrub_tree(node):
            nonlocal total_nans, total_weights, total_indices
            if node['child_count'] == 0 and node['inline_data']:
                if len(node['inline_data']) > 16:
                    buf = bytearray(node['inline_data'])
                    n, w, i = sanitize_buffer(buf)
                    node['inline_data'] = bytes(buf)
                    total_nans += n
                    total_weights += w
                    total_indices += i
            for child in node['children']:
                scrub_tree(child)
                
        scrub_tree(root)
        new_data = serialize_node(root)
        with open(payload, 'wb') as f:
            f.write(new_data)
            
    print(f"  [+] Purified {total_nans} corrupted NaN/Inf vertex floats.")
    print(f"  [+] Normalised {total_weights} vertex bones rigging weights.")
    print(f"  [+] Clamped {total_indices} out-of-bounds bone indices > 42.")
    
    print("  [*] Rebuilding ESF database...")
    subprocess.run([sys.executable, "-m", "core.esf_rebuilder"], check=True)
    print("  [+] Rebuilding complete -> workspace/FINAL_CHAR_MERGED.ESF")

def inject_patched_models_database():
    print("\n[*] Phase 3: Injecting CHAR.ESF in-place into Patched ISO...")
    
    iso_clean = 'iso/unpatched/EQOA_Frontiers.iso'
    iso_patched = 'iso/patched/EQOA_Frontiers_Patched.iso'
    esf_path = 'workspace/FINAL_CHAR_MERGED.ESF'
    
    if not os.path.exists(iso_patched):
        print(f"  [*] Initializing clean base ISO...")
        os.makedirs(os.path.dirname(iso_patched), exist_ok=True)
        shutil.copyfile(iso_clean, iso_patched)
        
    tmp_path = iso_patched + '.tmp'
    shutil.copyfile(iso_patched, tmp_path)
    
    # Surgical contiguous repack configuration for CHAR.ESF
    search_str = b'\x0ACHAR.ESF;1'
    fe_sector = 337
    PARTITION_OFFSET = 278
    
    with open(tmp_path, 'r+b') as f:
        new_size = os.path.getsize(esf_path)
        
        # Enforce 2048 alignment at end of file partition
        f.seek(0, 2)
        curr_size = f.tell()
        remainder = curr_size % 2048
        if remainder != 0:
            f.write(b'\x00' * (2048 - remainder))
            curr_size = f.tell()
            
        new_phys_lba = curr_size // 2048
        new_relative_lba = new_phys_lba - PARTITION_OFFSET
        
        print(f"  Appending database payload:")
        print(f"    Phys LBA: {new_phys_lba} | Rel LBA: {new_relative_lba} | Size: {new_size:,} bytes")
        
        # Write ESF payload
        with open(esf_path, 'rb') as esf_f:
            shutil.copyfileobj(esf_f, f)
            
        f.seek(0, 2)
        end_size = f.tell()
        remainder = end_size % 2048
        if remainder != 0:
            f.write(b'\x00' * (2048 - remainder))
            
        # 1. Patch ISO 9660 Directory Records (all occurrences)
        f.seek(0)
        mm = mmap.mmap(f.fileno(), 0)
        search_limit = min(100 * 1024 * 1024, len(mm))
        idx = 0
        records_patched = 0
        
        while True:
            idx = mm.find(search_str, idx, search_limit)
            if idx == -1: break
            
            dr_start = idx - 32
            lba_le = struct.unpack('<I', mm[dr_start+2:dr_start+6])[0]
            lba_be = struct.unpack('>I', mm[dr_start+6:dr_start+10])[0]
            
            if lba_le == lba_be:
                mm[dr_start+2:dr_start+6] = struct.pack('<I', new_phys_lba)
                mm[dr_start+6:dr_start+10] = struct.pack('>I', new_phys_lba)
                mm[dr_start+10:dr_start+14] = struct.pack('<I', new_size)
                mm[dr_start+14:dr_start+18] = struct.pack('>I', new_size)
                records_patched += 1
            idx += len(search_str)
            
        print(f"  [+] Patched {records_patched} ISO9660 records.")
        
        # 2. Patch UDF File Entry Sector
        fe_off = fe_sector * 2048
        fe_raw = bytearray(mm[fe_off : fe_off + 2048])
        
        tag_id = struct.unpack('<H', fe_raw[:2])[0]
        if tag_id == 0x0105:
            struct.pack_into('<Q', fe_raw, 0x38, new_size)
            l_ea = struct.unpack('<I', fe_raw[0xA8:0xAC])[0]
            ad_start = 0xB0 + l_ea
            
            flags = struct.unpack('<I', fe_raw[ad_start : ad_start + 4])[0] & 0xC0000000
            struct.pack_into('<I', fe_raw, ad_start, new_size | flags)
            struct.pack_into('<I', fe_raw, ad_start + 4, new_relative_lba)
            
            # Recompute UDF checksum
            fe_raw[4] = 0
            new_cksum = sum(fe_raw[:16]) & 0xFF
            fe_raw[4] = new_cksum
            
            mm[fe_off : fe_off + 2048] = bytes(fe_raw)
            print("  [+] Patched UDF allocation tags successfully.")
            
        # 3. Patch final UDF AVDP sector and Primary Volume Descriptor
        f.seek(256 * 2048)
        avdp = f.read(2048)
        f.seek(0, 2)
        if len(avdp) == 2048 and struct.unpack('<H', avdp[:2])[0] == 2:
            f.write(avdp)
            
        total_sectors = f.tell() // 2048
        pvd_offset = 16 * 2048
        if mm[pvd_offset:pvd_offset+6] == b'\x01CD001':
            mm[pvd_offset+80:pvd_offset+84] = struct.pack('<I', total_sectors)
            mm[pvd_offset+84:pvd_offset+88] = struct.pack('>I', total_sectors)
            
        mm.close()
        
    try:
        if os.path.exists(iso_patched):
            os.remove(iso_patched)
        os.replace(tmp_path, iso_patched)
        print(f"[+] Contiguous inject complete -> {iso_patched}")
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise IOError(f"LOCK ERROR: Could not overwrite ISO. Close PCSX2! Details: {e}")

def main(skip_inject_database: bool = False):
    print("=" * 80)
    print("  EQOA DECOUPLED PHASE 1: SURGICAL IN-GAME PLAYABLE MODELS RESTORATION")
    print("=" * 80)
    
    # 1. Structural upgrade graft surgery
    run_transplant_surgery()
    
    # 2. Geometry sanitization, NaN purging, weight normalization
    sanitize_mesh_payloads()
    
    # 3. Contiguous repacking
    if not skip_inject_database:
        inject_patched_models_database()
        
        # 4. Verify results
        print("\n[*] Validating recompiled database allocation tags...")
        subprocess.run([sys.executable, "-m", "core.verify_final_patch"], check=True)
        print("\n[+] In-game models patched, sanitized, and successfully verified in ISO.")
    else:
        print("\n[+] In-game models grafted and sanitized successfully -> workspace/FINAL_CHAR_MERGED.ESF")
        print("[*] ISO injection skipped (--skip-inject-database=True).")
    print("=" * 80)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='EQOA Phase 2 — in-game playable models grafting')
    parser.add_argument('--skip-inject-database', action='store_true', help='Skip ISO injection/patching of the compiled models database')
    args = parser.parse_args()
    main(skip_inject_database=args.skip_inject_database)
