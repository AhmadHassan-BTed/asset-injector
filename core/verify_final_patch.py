#!/usr/bin/env python3
import struct
import os
import hashlib

def get_file_hash(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=" * 80)
    print("  EQOA PATCED ISO INTEGRITY & SECTOR ALIGNMENT VERIFIER")
    print("=" * 80)
    
    iso_path = 'iso/patched/EQOA_Frontiers_Patched.iso'
    if not os.path.exists(iso_path):
        print(f"[-] Error: Patched ISO not found at {iso_path}")
        return

    with open(iso_path, 'rb') as f:
        # Phase 1: Verify In-game models database (CHAR.ESF)
        print("\n[STEP 1] Verifying Active In-game Models Database (CHAR.ESF)...")
        assets_esf = 'assets/merged-assets/data/CHAR.ESF'
        fallback_esf = 'workspace/FINAL_CHAR_MERGED.ESF'
        vanilla_char_esf = 'assets/Vanilla/data/CHAR.ESF'
        
        is_custom_placed = False
        if os.path.exists(assets_esf) and os.path.exists(vanilla_char_esf):
            if get_file_hash(assets_esf) != get_file_hash(vanilla_char_esf):
                is_custom_placed = True
                
        if is_custom_placed:
            expected_size = os.path.getsize(assets_esf)
            label = "Custom Placed Asset CHAR.ESF"
        elif os.path.exists(fallback_esf):
            expected_size = os.path.getsize(fallback_esf)
            label = "Compiled FINAL_CHAR_MERGED.ESF"
        else:
            expected_size = None
            label = "Vanilla Reference (Not patched)"

        if expected_size is not None:
            # Read allocation descriptor for CHAR.ESF
            f.seek(0xA8934)
            ad = f.read(8)
            sz = struct.unpack('<I', ad[0:4])[0]
            lb = struct.unpack('<I', ad[4:8])[0]
            phys = lb + 278  # partition offset = 278
            
            print("  == UDF Allocation Descriptor ==")
            print(f"    Raw bytes    : {ad.hex()}")
            print(f"    Size (LE32)  : {sz:,}  (expected {expected_size:,} for {label}) -> {'PASS' if sz==expected_size else 'FAIL'}")
            print(f"    LogLBA(LE32) : {lb}  (expected >1490000) -> {'PASS' if lb > 1490000 else 'FAIL'}")
            print(f"    PhysLBA      : {phys}  (expected >1490000) -> {'PASS' if phys > 1490000 else 'FAIL'}")
            
            # Read UDF Information Length
            f.seek(0xA8838)
            il = struct.unpack('<Q', f.read(8))[0]
            print("  == UDF Information Length ==")
            print(f"    {il:,}  (expected {expected_size:,}) -> {'PASS' if il==expected_size else 'FAIL'}")
            
            # Read ISO9660 directory record
            f.seek(0)
            data = f.read(1024*1024)  # first 1MB should contain directory
            idx = data.find(b'CHAR.ESF;1')
            print("  == ISO9660 Directory Record ==")
            if idx != -1:
                dr = idx - 33
                iso_lba  = struct.unpack_from('<I', data, dr+2)[0]
                iso_size = struct.unpack_from('<I', data, dr+10)[0]
                print(f"    LBA  : {iso_lba}  (expected {phys}) -> {'PASS' if iso_lba==phys else 'FAIL'}")
                print(f"    Size : {iso_size:,}  (expected {expected_size:,}) -> {'PASS' if iso_size==expected_size else 'FAIL'}")
            else:
                print("    [-] Fail: CHAR.ESF directory record not found in directory structure!")
            
            # Verify CHAR.ESF data at patched LBA
            f.seek(phys * 2048)
            magic = f.read(4)
            print(f"  == CHAR.ESF data at LBA {phys} ==")
            print(f"    Magic: {magic.hex()}  (expected 464a424f = FJBO) -> {'PASS' if magic==b'FJBO' else 'FAIL'}")
        else:
            print("  [*] Skip: In-game models database CHAR.ESF has not been patched/compiled yet.")

        # Phase 2: Verify Character Selection overlay databases
        print("\n[STEP 2] Verifying Character Selection Screen Databases...")
        csf_mapping = [
            ('CHARCUST.CSF', b'\x0ECHARCUST.CSF;1', 358, b'CESF'),
            ('CHARFACE.CSF', b'\x0ECHARFACE.CSF;1', 349, b'CESF'),
            ('CHARFACE.ESF', b'\x0ECHARFACE.ESF;1', 342, b'FJBO'),
            ('CHARSEL1.CSF', b'\x0ECHARSEL1.CSF;1', 359, b'CESF'),
            ('CHARSEL2.CSF', b'\x0ECHARSEL2.CSF;1', 348, b'CESF'),
            ('CHARSEL3.CSF', b'\x0ECHARSEL3.CSF;1', 345, b'CESF'),
            ('CHARSEL4.CSF', b'\x0ECHARSEL4.CSF;1', 352, b'CESF'),
        ]
        
        f.seek(0)
        first_100m = f.read(100 * 1024 * 1024)
        
        patched_csf_count = 0
        for filename, search_str, fe_sector, expected_magic in csf_mapping:
            idx = first_100m.find(search_str)
            if idx == -1:
                print(f"  [-] {filename:15} : NOT found in ISO9660 directory records.")
                continue
                
            dr = idx - 32
            iso_lba = struct.unpack_from('<I', first_100m, dr+2)[0]
            iso_size = struct.unpack_from('<I', first_100m, dr+10)[0]
            
            # Check if it was moved/patched (original LBAs are usually < 1,000,000, patched are > 1,500,000)
            if iso_lba < 1000000:
                print(f"  [*] {filename:15} : Present but UNPATCHED (Original LBA: {iso_lba})")
                continue
                
            # Verify UDF File Entry Sector
            fe_off = fe_sector * 2048
            f.seek(fe_off)
            fe_raw = f.read(2048)
            tag_id = struct.unpack('<H', fe_raw[:2])[0]
            
            udf_pass = False
            udf_size = 0
            udf_phys = 0
            if tag_id == 0x0105:
                udf_size = struct.unpack('<Q', fe_raw[0x38:0x40])[0]
                l_ea = struct.unpack('<I', fe_raw[0xA8:0xAC])[0]
                ad_start = 0xB0 + l_ea
                udf_rel_lba = struct.unpack('<I', fe_raw[ad_start+4:ad_start+8])[0]
                udf_phys = udf_rel_lba + 278
                if udf_size == iso_size and udf_phys == iso_lba:
                    udf_pass = True
            
            # Read magic bytes from patched LBA
            f.seek(iso_lba * 2048)
            magic = f.read(4)
            magic_pass = (magic == expected_magic)
            
            status = "PASS" if (udf_pass and magic_pass) else "FAIL"
            print(f"  [+] {filename:15} : {status} (LBA: {iso_lba} | Size: {iso_size:,} | Magic: {magic.decode('ascii', errors='replace')} -> {'OK' if magic_pass else 'BAD'})")
            patched_csf_count += 1
            
        if patched_csf_count == 0:
            print("  [*] Note: No character selection CSF databases have been patched in this ISO yet.")

    print("\n" + "=" * 80)
    print("  ALL VERIFICATION CHECKS COMPLETED.")
    print("=" * 80)

if __name__ == '__main__':
    main()
