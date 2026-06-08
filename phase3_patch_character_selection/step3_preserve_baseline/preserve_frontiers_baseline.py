#!/usr/bin/env python3
"""
preserve_frontiers_baseline.py
==============================
Handles extraction of sterile template databases and setup of the clean base ISO.
Ensures that everything else (non-player assets, textures, menus) remains 100% native Frontiers.
"""
import os
import sys
# Add repository root to python path for modular core imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import pycdlib

def setup_baseline_iso(force_reset=False):
    iso_clean = 'iso/unpatched/EQOA_Frontiers.iso'
    iso_patched = 'iso/patched/EQOA_Frontiers_Patched.iso'
    
    if not os.path.exists(iso_clean):
        print(f"[-] Error: Sterile original Frontiers ISO not found at {iso_clean}!")
        print("[-] Please run setup_environment.bat or place the file manually.")
        sys.exit(1)
        
    if force_reset or not os.path.exists(iso_patched):
        print(f"[*] Copying sterile base Frontiers ISO: {iso_clean} -> {iso_patched} ...")
        os.makedirs(os.path.dirname(iso_patched), exist_ok=True)
        shutil.copyfile(iso_clean, iso_patched)
        print("[+] Sterile Frontiers base ISO is ready.")
    else:
        print("[*] Patched ISO already exists. Preserving existing modifications.")

def extract_baseline_assets():
    iso_path = 'iso/unpatched/EQOA_Frontiers.iso'
    output_dir = 'assets/Frontiers'
    
    if not os.path.exists(iso_path):
        print(f"[-] Error: Could not find clean baseline ISO at {iso_path}")
        sys.exit(1)
        
    os.makedirs(os.path.join(output_dir, 'data'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'data2'), exist_ok=True)
    
    files_to_extract = {
        '/DATA/CHAR.ESF;1': 'data/CHAR.ESF',
        '/DATA2/CHARCUST.CSF;1': 'data2/CHARCUST.CSF',
        '/DATA2/CHARFACE.CSF;1': 'data2/CHARFACE.CSF',
        '/DATA2/CHARFACE.ESF;1': 'data2/CHARFACE.ESF',
        '/DATA2/CHARSEL1.CSF;1': 'data2/CHARSEL1.CSF',
        '/DATA2/CHARSEL2.CSF;1': 'data2/CHARSEL2.CSF',
        '/DATA2/CHARSEL3.CSF;1': 'data2/CHARSEL3.CSF',
        '/DATA2/CHARSEL4.CSF;1': 'data2/CHARSEL4.CSF',
    }
    
    iso = pycdlib.PyCdlib()
    try:
        print(f"[*] Opening clean base ISO: {iso_path}...")
        iso.open(iso_path)
        
        for iso_path_in, rel_out_path in files_to_extract.items():
            dest = os.path.join(output_dir, rel_out_path)
            print(f"  [*] Extracting {iso_path_in} -> {dest} ...")
            with open(dest, 'wb') as out_f:
                iso.get_file_from_iso_fp(out_f, iso_path=iso_path_in)
            print(f"    [+] Extracted successfully ({os.path.getsize(dest):,} bytes)")
            
        iso.close()
        print("\n[+] Extraction Complete! Baseline Frontiers assets successfully saved.")
    except Exception as e:
        if iso:
            try:
                iso.close()
            except Exception:
                pass
        print(f"[-] Error during baseline extraction: {e}")
        sys.exit(1)

def main():
    print("=" * 80)
    print("  EQOA DECOUPLED PHASE 3: FRONTIERS BASELINE PRESERVATION & EXTRACTION")
    print("=" * 80)
    
    # Enforce baseline ISO availability
    setup_baseline_iso(force_reset=False)
    
    # Extract sterile templates
    extract_baseline_assets()
    
    print("\n[+] Baseline preservation complete. Frontiers assets are 100% preserved.")
    print("=" * 80)

if __name__ == '__main__':
    main()
