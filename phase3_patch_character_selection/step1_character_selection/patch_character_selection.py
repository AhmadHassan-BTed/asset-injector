#!/usr/bin/env python3
"""
patch_character_selection.py
============================
Responsible for the character creation/selection database screen overlay.
Performs:
1. Copying Vanilla character select database files (selective CSF overlay) into the workspace.
2. Contiguously repacking and sector-patching CHARSEL1.CSF ... CHARSEL4.CSF,
   CHARCUST.CSF, CHARFACE.CSF, and CHARFACE.ESF in-place inside the patched ISO.
"""
import os
import sys
# Add repository root to python path for modular core imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import struct
import mmap
import subprocess

def merge_select_assets():
    print("[*] Phase 1: Merging Vanilla character select screen files (selective overlay)...")
    vanilla_dir = 'assets/Vanilla'
    frontiers_dir = 'assets/Frontiers'
    merged_dir = 'assets/merged-assets'
    
    if os.path.exists(merged_dir):
        shutil.rmtree(merged_dir)
    os.makedirs(merged_dir)
    
    # Helper to recursively copy directories
    def copy_assets_recursive(src, dst, exclude_files=None):
        if not os.path.exists(src): return
        if exclude_files is None: exclude_files = set()
            
        for root, dirs, files in os.walk(src):
            rel_path = os.path.relpath(root, src)
            target_dir = os.path.join(dst, rel_path) if rel_path != '.' else dst
            os.makedirs(target_dir, exist_ok=True)
            
            for file in files:
                if file == '.gitkeep' or file in exclude_files:
                    continue
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file)
                shutil.copy2(src_file, dst_file)
                
    # Copy Frontiers baseline (excluding CHAR.ESF)
    copy_assets_recursive(frontiers_dir, merged_dir, exclude_files={'CHAR.ESF'})
    
    # Selective Vanilla CSF overlays
    vanilla_select_files = {
        'CHARSEL1.CSF', 'CHARSEL2.CSF', 'CHARSEL3.CSF', 'CHARSEL4.CSF'
    }
    
    os.makedirs(os.path.join(merged_dir, 'data2'), exist_ok=True)
    for filename in vanilla_select_files:
        src_path = os.path.join(vanilla_dir, 'data2', filename)
        dst_path = os.path.join(merged_dir, 'data2', filename)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"  [+] Overlaid Vanilla selection file: {filename}")
            
    print("  [+] Selection overlay merged successfully -> assets/merged-assets/")

def inject_select_databases():
    print("\n[*] Phase 2: Copying select screen database assets to workspace...")
    
    assets_data2 = 'assets/merged-assets/data2'
    extracted_data2 = 'workspace/ISO_EXTRACTED/DATA2'
    os.makedirs(extracted_data2, exist_ok=True)
    
    csf_mapping = [
        ('CHARCUST.CSF', b'\x0ECHARCUST.CSF;1', 358),
        ('CHARFACE.CSF', b'\x0ECHARFACE.CSF;1', 349),
        ('CHARFACE.ESF', b'\x0ECHARFACE.ESF;1', 342),
        ('CHARSEL1.CSF', b'\x0ECHARSEL1.CSF;1', 359),
        ('CHARSEL2.CSF', b'\x0ECHARSEL2.CSF;1', 348),
        ('CHARSEL3.CSF', b'\x0ECHARSEL3.CSF;1', 345),
        ('CHARSEL4.CSF', b'\x0ECHARSEL4.CSF;1', 352),
    ]
    
    injection_list = []
    
    for filename, search_str, fe_sector in csf_mapping:
        src_path = os.path.join(assets_data2, filename)
        if os.path.exists(src_path):
            # Copy to workspace DATA2 path for tools compatibility
            dst_path = os.path.join(extracted_data2, filename)
            shutil.copy2(src_path, dst_path)
            
            # Special standalone copies for CHARSEL CSF databases
            if filename.startswith('CHARSEL') and filename.endswith('.CSF'):
                shutil.copy2(src_path, os.path.join('workspace', filename))
                
            injection_list.append((src_path, search_str, fe_sector, filename))
            
    iso_clean = 'iso/unpatched/EQOA_Frontiers.iso'
    iso_patched = 'iso/patched/EQOA_Frontiers_Patched.iso'
    
    if not os.path.exists(iso_patched):
        print(f"  [*] Initializing clean base ISO...")
        os.makedirs(os.path.dirname(iso_patched), exist_ok=True)
        shutil.copyfile(iso_clean, iso_patched)
        
    tmp_path = iso_patched + '.tmp'
    shutil.copyfile(iso_patched, tmp_path)
    
    PARTITION_OFFSET = 278
    
    print(f"[*] Phase 3: Commencing UDF multi-asset sector injection of {len(injection_list)} selection CSF files...")
    
    with open(tmp_path, 'r+b') as f:
        for filepath, search_str, fe_sector, label in injection_list:
            if not os.path.exists(filepath):
                continue
                
            new_size = os.path.getsize(filepath)
            
            # Align end of ISO to 2048 bytes
            f.seek(0, 2)
            curr_size = f.tell()
            remainder = curr_size % 2048
            if remainder != 0:
                f.write(b'\x00' * (2048 - remainder))
                curr_size = f.tell()
                
            new_phys_lba = curr_size // 2048
            new_relative_lba = new_phys_lba - PARTITION_OFFSET
            
            print(f"  Appending {label}:")
            print(f"    LBA: {new_phys_lba} | Rel LBA: {new_relative_lba} | Size: {new_size:,} bytes")
            
            # Write file payload contiguously
            with open(filepath, 'rb') as src_f:
                shutil.copyfileobj(src_f, f)
                
            # Align after writing
            f.seek(0, 2)
            end_size = f.tell()
            remainder = end_size % 2048
            if remainder != 0:
                f.write(b'\x00' * (2048 - remainder))
                
            # 1. Patch ALL occurrences of ISO 9660 Directory Records in the first 100MB
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
                
            print(f"    [+] Patched {records_patched} ISO9660 directory records.")
            
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
                
                # Recompute checksum
                fe_raw[4] = 0
                new_cksum = sum(fe_raw[:16]) & 0xFF
                fe_raw[4] = new_cksum
                
                mm[fe_off : fe_off + 2048] = bytes(fe_raw)
                print("    [+] Patched UDF FE allocation descriptor.")
                
            mm.close()
            
        # 3. Patch final UDF AVDP sector and Primary Volume Descriptor
        f.seek(256 * 2048)
        avdp = f.read(2048)
        f.seek(0, 2)
        if len(avdp) == 2048 and struct.unpack('<H', avdp[:2])[0] == 2:
            f.write(avdp)
            
        total_sectors = f.tell() // 2048
        pvd_offset = 16 * 2048
        mm = mmap.mmap(f.fileno(), 0)
        if mm[pvd_offset:pvd_offset+6] == b'\x01CD001':
            mm[pvd_offset+80:pvd_offset+84] = struct.pack('<I', total_sectors)
            mm[pvd_offset+84:pvd_offset+88] = struct.pack('>I', total_sectors)
            
        mm.close()
        
    try:
        if os.path.exists(iso_patched):
            os.remove(iso_patched)
        os.replace(tmp_path, iso_patched)
        print(f"\n[+] Character Selection injection complete -> {iso_patched}")
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise IOError(f"LOCK ERROR: Could not overwrite ISO. Close PCSX2! Details: {e}")

def main(skip_merge_assets: bool = False, skip_inject_databases: bool = False):
    print("=" * 80)
    print("  EQOA DECOUPLED PHASE 2: SURGICAL CHARACTER SELECTION DATABASE OVERLAY")
    print("=" * 80)
    
    # 1. Merge baseline files and overlay selective Vanilla CHARSEL databases
    if not skip_merge_assets:
        merge_select_assets()
    else:
        print("\n[*] Skipping asset merge (skip_merge_assets=True)")
    
    # 2. Append CSF files and patch sector addresses contiguously
    if not skip_inject_databases:
        inject_select_databases()
    else:
        print("\n[*] Skipping ISO injection (skip_inject_databases=True)")
    
    print("\n[+] Character Selection databases patched and verified ready to run.")
    print("=" * 80)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='EQOA Phase 3 — character creation/selection overlay')
    parser.add_argument('--skip-merge-assets', action='store_true', help='Skip merging Vanilla/Frontiers character selection assets into assets/merged-assets')
    parser.add_argument('--skip-inject-databases', action='store_true', help='Skip ISO injection/patching of selection CSF/ESF databases')
    args = parser.parse_args()
    main(skip_merge_assets=args.skip_merge_assets, skip_inject_databases=args.skip_inject_databases)

