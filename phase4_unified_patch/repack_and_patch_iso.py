#!/usr/bin/env python3
import os
import sys
# Add repository root to python path for modular core imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import struct
import mmap
import json

def repack_and_patch_all():
    config_path = 'workspace/patch_config.json'
    
    # 1. Default configuration
    default_config = {
        "patch_character_selection": True,
        "patch_in_game_models": True
    }
    
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"[+] Created default configuration file at: {config_path}")
        config = default_config
    else:
        with open(config_path, 'r') as f:
            try:
                config = json.load(f)
            except Exception:
                config = default_config
                
    patch_charsel = config.get("patch_character_selection", True)
    patch_gameplay = config.get("patch_in_game_models", True)
    
    print("=" * 80)
    print("  EQOA CUSTOM MULTI-COMPACT ISO UNIFIED PATCHER")
    print("=" * 80)
    print(f"  [Config] Patch Character Selection Screen : {'ENABLED' if patch_charsel else 'DISABLED'}")
    print(f"  [Config] Patch In-Game Player Models      : {'ENABLED' if patch_gameplay else 'DISABLED'}")
    print("=" * 80)
    
    # 2. Terminate running PCSX2 emulator if open to prevent file locks
    try:
        import subprocess
        res = subprocess.run(["tasklist"], capture_output=True, text=True)
        if "pcsx2-qt.exe" in res.stdout.lower() or "pcsx2.exe" in res.stdout.lower():
            print("[*] Detected running PCSX2 emulator. Terminating to avoid file locks...")
            subprocess.run(["taskkill", "/F", "/IM", "pcsx2-qt.exe"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/IM", "pcsx2.exe"], capture_output=True)
    except Exception as e:
        print(f"[!] Warning: Could not check or terminate PCSX2 process: {e}")
        
    iso_clean = 'iso/unpatched/EQOA_Frontiers.iso'
    iso_patched = 'iso/patched/EQOA_Frontiers_Patched.iso'
    tmp_path = iso_patched + '.tmp'
    
    if not os.path.exists(iso_clean):
        print(f"[-] Error: Original clean ISO not found at {iso_clean}!")
        sys.exit(1)
        
    print(f"\n[*] Copying sterile base ISO: {iso_clean} -> {tmp_path} ...")
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    shutil.copyfile(iso_clean, tmp_path)
    
    # Define files to inject based on the toggled configuration
    injection_list = []
    
    # Target 1: In-game player character models
    if patch_gameplay:
        esf_path = 'workspace/FINAL_CHAR_MERGED.ESF'
        if os.path.exists(esf_path):
            injection_list.append((esf_path, b'\x0ACHAR.ESF;1', 337, "CHAR.ESF (In-Game Models)"))
        else:
            print("[!] Warning: FINAL_CHAR_MERGED.ESF not compiled yet. Please run Step 1 first to graft models.")
            
    # Target 2: Character select screen database overlays
    if patch_charsel:
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
        
        for filename, search_str, fe_sector in csf_mapping:
            src_path = os.path.join(assets_data2, filename)
            if os.path.exists(src_path):
                # Copy to workspace paths for diagnostic tools compatibility
                dst_path = os.path.join(extracted_data2, filename)
                shutil.copy2(src_path, dst_path)
                if filename.startswith('CHARSEL') and filename.endswith('.CSF'):
                    shutil.copy2(src_path, os.path.join('workspace', filename))
                
                injection_list.append((src_path, search_str, fe_sector, filename))
                
    if not injection_list:
        print("\n[*] Info: No patch options are enabled. Patched ISO matches clean base.")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        shutil.copyfile(iso_clean, iso_patched)
        return
        
    PARTITION_OFFSET = 278
    
    print(f"\n[*] Commencing unified binary injection of {len(injection_list)} components...")
    
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
            
            print(f"\n  Appending {label}:")
            print(f"    LBA Sector (Phys): {new_phys_lba} | Rel LBA: {new_relative_lba} | Size: {new_size:,} bytes")
            
            # Write file payload contiguously
            with open(filepath, 'rb') as src_f:
                shutil.copyfileobj(src_f, f)
                
            # Align after writing
            f.seek(0, 2)
            end_size = f.tell()
            remainder = end_size % 2048
            if remainder != 0:
                f.write(b'\x00' * (2048 - remainder))
            
            f.flush()
            os.fsync(f.fileno())
                
            # 1. Patch ALL occurrences of ISO 9660 Directory Records in the first 100MB
            f.seek(0)
            mm = mmap.mmap(f.fileno(), 0)
            
            # Search limit to first 100MB where directory structures reside
            search_limit = min(100 * 1024 * 1024, len(mm))
            idx = 0
            records_patched = 0
            
            while True:
                idx = mm.find(search_str, idx, search_limit)
                if idx == -1:
                    break
                    
                dr_start = idx - 32
                lba_le = struct.unpack('<I', mm[dr_start+2:dr_start+6])[0]
                lba_be = struct.unpack('>I', mm[dr_start+6:dr_start+10])[0]
                
                # Check for LE/BE symmetric validation
                if lba_le == lba_be:
                    mm[dr_start+2:dr_start+6] = struct.pack('<I', new_phys_lba)
                    mm[dr_start+6:dr_start+10] = struct.pack('>I', new_phys_lba)
                    mm[dr_start+10:dr_start+14] = struct.pack('<I', new_size)
                    mm[dr_start+14:dr_start+18] = struct.pack('>I', new_size)
                    records_patched += 1
                    
                idx += len(search_str)
                
            print(f"    [+] Patched {records_patched} ISO9660 Directory Records in directory sector structure.")
            
            # 2. Patch UDF File Entry Sector
            fe_off = fe_sector * 2048
            fe_raw = bytearray(mm[fe_off : fe_off + 2048])
            
            tag_id = struct.unpack('<H', fe_raw[:2])[0]
            if tag_id == 0x0105:
                # UDF FE Size at 0x38 (8-byte LE)
                struct.pack_into('<Q', fe_raw, 0x38, new_size)
                
                # UDF FE Allocation Descriptor starting at 0xB0 + L_EA
                l_ea = struct.unpack('<I', fe_raw[0xA8:0xAC])[0]
                ad_start = 0xB0 + l_ea
                
                # Update allocation descriptor length and LBA offset
                flags = struct.unpack('<I', fe_raw[ad_start : ad_start + 4])[0] & 0xC0000000
                struct.pack_into('<I', fe_raw, ad_start, new_size | flags)
                struct.pack_into('<I', fe_raw, ad_start + 4, new_relative_lba)
                
                # Recompute tag checksum
                fe_raw[4] = 0
                new_cksum = sum(fe_raw[:16]) & 0xFF
                fe_raw[4] = new_cksum
                
                # Commit UDF FE
                mm[fe_off : fe_off + 2048] = bytes(fe_raw)
                print(f"    [+] Patched UDF FE at Sector {fe_sector} (New Rel LBA: {new_relative_lba}).")
            else:
                print(f"    [WARN] Sector {fe_sector} has no valid UDF File Entry tag (Tag: 0x{tag_id:04X})!")
                
            mm.close()
            
        # 3. Finalize Partition End: Splicing UDF AVDP sector at the end of the partition
        # Read AVDP from LBA 256
        f.seek(256 * 2048)
        avdp_sector = f.read(2048)
        
        f.seek(0, 2)
        if len(avdp_sector) == 2048 and struct.unpack('<H', avdp_sector[:2])[0] == 2:
            f.write(avdp_sector)
            f.flush()
            os.fsync(f.fileno())
            final_iso_size = f.tell()
            print(f"[+] Appended UDF AVDP sector at the end of the partition (New Size: {final_iso_size:,} bytes).")
        else:
            final_iso_size = f.tell()
            
        total_sectors = final_iso_size // 2048
        
        # 4. Patch total sectors in Primary Volume Descriptor (PVD)
        mm = mmap.mmap(f.fileno(), 0)
        pvd_offset = 16 * 2048
        if mm[pvd_offset:pvd_offset+6] == b'\x01CD001':
            mm[pvd_offset+80:pvd_offset+84] = struct.pack('<I', total_sectors)
            mm[pvd_offset+84:pvd_offset+88] = struct.pack('>I', total_sectors)
            print(f"[+] Patched PVD total sector count to {total_sectors}")
            
        mm.close()
        
    # ATOMIC COMMIT
    try:
        if os.path.exists(iso_patched):
            os.remove(iso_patched)
        os.replace(tmp_path, iso_patched)
        print(f"\n[+] Successfully patched ISO compiled: {iso_patched} ({final_iso_size:,} bytes)")
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise IOError(f"ATOMIC COMMIT FAILED: Unable to overwrite '{iso_patched}'. Process locked by emulator. Exception: {e}")

if __name__ == '__main__':
    repack_and_patch_all()
