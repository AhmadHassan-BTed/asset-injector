import os
import shutil
import struct
import mmap
import sys

def patch_iso_in_place():
    # Terminate running PCSX2 emulator if it is open to avoid file locks on the patched ISO
    try:
        import subprocess
        res = subprocess.run(["tasklist"], capture_output=True, text=True)
        if "pcsx2-qt.exe" in res.stdout.lower() or "pcsx2.exe" in res.stdout.lower():
            print("[*] Detected running PCSX2 emulator. Terminating to avoid file locks...")
            subprocess.run(["taskkill", "/F", "/IM", "pcsx2-qt.exe"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/IM", "pcsx2.exe"], capture_output=True)
    except Exception as e:
        print(f"[!] Warning: Could not check or terminate PCSX2 process: {e}")

    print("=" * 80)
    print("  EQOA NATIVE MULTI-ASSET ISO IN-PLACE PATCHER")
    print("=" * 80)

    
    # Define source directories
    assets_data = 'assets/merged-assets/data'
    assets_data2 = 'assets/merged-assets/data2'
    
    # Define target directories in workspace
    extracted_data = 'workspace/ISO_EXTRACTED/DATA'
    extracted_data2 = 'workspace/ISO_EXTRACTED/DATA2'
    
    os.makedirs(extracted_data, exist_ok=True)
    os.makedirs(extracted_data2, exist_ok=True)
    
    print("\n[*] Step 1: Copying assets to their corresponding workspace folders...")
    
    # Copy assets/data files if they exist
    if os.path.exists(assets_data):
        for f in os.listdir(assets_data):
            src = os.path.join(assets_data, f)
            if os.path.isfile(src):
                # To DATA folder
                dst1 = os.path.join(extracted_data, f)
                shutil.copy2(src, dst1)
                print(f"  [+] Copied {src} -> {dst1}")
                
                # Special destinations
                if f == 'CHAR.ESF':
                    dst2 = 'workspace/ISO_EXTRACTED/CHAR.ESF'
                    shutil.copy2(src, dst2)
                    print(f"  [+] Copied {src} -> {dst2}")

    # Copy assets/data2 files if they exist
    if os.path.exists(assets_data2):
        for f in os.listdir(assets_data2):
            src = os.path.join(assets_data2, f)
            if os.path.isfile(src):
                # To DATA2 folder
                dst1 = os.path.join(extracted_data2, f)
                shutil.copy2(src, dst1)
                print(f"  [+] Copied {src} -> {dst1}")
                
                # Special destinations for CHARSEL files
                if f.startswith('CHARSEL') and f.endswith('.CSF'):
                    dst2 = os.path.join('workspace', f)
                    shutil.copy2(src, dst2)
                    print(f"  [+] Copied {src} -> {dst2}")

    print("\n[+] Step 1 Complete: All workspace files overwritten successfully.")

    # Step 2: Patch the target ISO
    iso_patched = 'iso/patched/EQOA_Frontiers_Patched.iso'
    
    if not os.path.exists(iso_patched):
        print(f"[-] Error: Could not find patched ISO to modify at {iso_patched}")
        sys.exit(1)
        
    # We will append the modified files to the end of the ISO
    files_to_patch = []
    
    # Only patch CHAR.ESF if a custom Frontiers overlay version is present (i.e. different from baseline Vanilla)
    custom_char_esf_present = False
    char_esf_path = os.path.join(assets_data, 'CHAR.ESF')
    vanilla_char_esf = 'assets/Vanilla/data/CHAR.ESF'
    
    if os.path.exists(char_esf_path):
        import hashlib
        def get_file_hash(p):
            h = hashlib.sha256()
            with open(p, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    h.update(chunk)
            return h.hexdigest()
            
        if os.path.exists(vanilla_char_esf):
            if get_file_hash(char_esf_path) != get_file_hash(vanilla_char_esf):
                custom_char_esf_present = True
                
    if custom_char_esf_present:
        files_to_patch.append(('workspace/ISO_EXTRACTED/DATA/CHAR.ESF', b'\x0ACHAR.ESF;1', 337))
    else:
        print("\n[*] Info: Preserving high-fidelity recompiled CHAR.ESF database (FINAL_CHAR_MERGED.ESF) inside the ISO.")
        
    # Add other CSF/ESF files from assets/data2 if they exist
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
            files_to_patch.append((f"workspace/ISO_EXTRACTED/DATA2/{filename}", search_str, fe_sector))
            
    if not files_to_patch:
        print("\n[*] Info: No asset files found to patch. ISO is already complete.")
        return

    PARTITION_OFFSET = 278
    
    print("\n[*] Step 2: Commencing multi-asset sector binary injection in-place...")
    
    with open(iso_patched, 'r+b') as f:
        for filepath, search_str, fe_sector in files_to_patch:
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
            
            print(f"\n  Injecting {os.path.basename(filepath)}:")
            print(f"    New LBA (Phys): {new_phys_lba} | Rel LBA: {new_relative_lba} | Size: {new_size:,} bytes")
            
            # Append file content
            with open(filepath, 'rb') as src_f:
                shutil.copyfileobj(src_f, f)
                
            # Align after appending
            f.seek(0, 2)
            end_size = f.tell()
            remainder = end_size % 2048
            if remainder != 0:
                f.write(b'\x00' * (2048 - remainder))
                
            # 1. Patch ISO 9660 Directory Record
            f.seek(0)
            mm = mmap.mmap(f.fileno(), 0)
            idx = mm.find(search_str)
            if idx == -1:
                print(f"    [-] Error: Directory record for {search_str.decode()} not found!")
                mm.close()
                sys.exit(1)
                
            dr_start = idx - 32
            old_lba_le = struct.unpack('<I', mm[dr_start+2:dr_start+6])[0]
            old_size_le = struct.unpack('<I', mm[dr_start+10:dr_start+14])[0]
            print(f"    [+] Found ISO9660 Record at 0x{dr_start:X} (Old LBA: {old_lba_le}, Old Size: {old_size_le:,})")
            
            # Patch ISO9660 LBA and Size (LE and BE)
            mm[dr_start+2:dr_start+6] = struct.pack('<I', new_phys_lba)
            mm[dr_start+6:dr_start+10] = struct.pack('>I', new_phys_lba)
            mm[dr_start+10:dr_start+14] = struct.pack('<I', new_size)
            mm[dr_start+14:dr_start+18] = struct.pack('>I', new_size)
            print("    [+] Patched ISO9660 Directory Record.")
            
            # 2. Patch UDF File Entry Sector
            fe_off = fe_sector * 2048
            fe_raw = bytearray(mm[fe_off : fe_off + 2048])
            
            tag_id = struct.unpack('<H', fe_raw[:2])[0]
            if tag_id != 0x0105:
                print(f"    [-] Error: Sector {fe_sector} is not a valid UDF File Entry (Tag: 0x{tag_id:04X})!")
                mm.close()
                sys.exit(1)
                
            # Overwrite allocation descriptor
            l_ea = struct.unpack('<I', fe_raw[0xA8:0xAC])[0]
            l_ad = struct.unpack('<I', fe_raw[0xAC:0xB0])[0]
            ad_start = 0xB0 + l_ea
            
            old_ext_len = struct.unpack('<I', fe_raw[ad_start : ad_start + 4])[0] & 0x3FFFFFFF
            old_ext_lba = struct.unpack('<I', fe_raw[ad_start + 4 : ad_start + 8])[0]
            print(f"    [+] Found UDF FE at sector {fe_sector} (Old Rel LBA: {old_ext_lba}, Old Extent Size: {old_ext_len:,})")
            
            # Patch UDF FE Size (8-byte LE at 0x38)
            struct.pack_into('<Q', fe_raw, 0x38, new_size)
            
            # Patch UDF FE Allocation Descriptor (Length and relative LBA)
            flags = struct.unpack('<I', fe_raw[ad_start : ad_start + 4])[0] & 0xC0000000
            struct.pack_into('<I', fe_raw, ad_start, new_size | flags)
            struct.pack_into('<I', fe_raw, ad_start + 4, new_relative_lba)
            
            # Recompute UDF Tag Checksum
            fe_raw[4] = 0
            new_cksum = sum(fe_raw[:16]) & 0xFF
            fe_raw[4] = new_cksum
            
            # Write back patched FE
            mm[fe_off : fe_off + 2048] = bytes(fe_raw)
            print(f"    [+] Patched UDF FE at Sector {fe_sector} (New Rel LBA: {new_relative_lba}, Checksum: 0x{new_cksum:02X})")
            
            mm.close()
            
        # Patch total sectors in Primary Volume Descriptor (PVD)
        f.seek(0, 2)
        curr_size = f.tell()
        remainder = curr_size % 2048
        if remainder != 0:
            f.write(b'\x00' * (2048 - remainder))
            curr_size = f.tell()
            
        # Read AVDP from LBA 256
        f.seek(256 * 2048)
        avdp_sector = f.read(2048)
        if len(avdp_sector) == 2048 and struct.unpack('<H', avdp_sector[:2])[0] == 2:
            f.seek(0, 2)
            f.write(avdp_sector)
            print("[+] Appended UDF AVDP sector at the end of the partition.")
            
        f.seek(0, 2)
        final_iso_size = f.tell()
        total_sectors = final_iso_size // 2048
        
        # Patch PVD
        mm = mmap.mmap(f.fileno(), 0)
        pvd_offset = 16 * 2048
        if mm[pvd_offset:pvd_offset+6] == b'\x01CD001':
            mm[pvd_offset+80:pvd_offset+84] = struct.pack('<I', total_sectors)
            mm[pvd_offset+84:pvd_offset+88] = struct.pack('>I', total_sectors)
            print(f"[+] Patched PVD total sector count to {total_sectors}")
            
        mm.close()
        
    print("\n" + "=" * 80)
    print("  ALL PLACED ASSETS APPLIED AND SURGICALLY PATCHED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == '__main__':
    patch_iso_in_place()
