import struct

def check():
    iso_path = 'iso/unpatched/EQOA_Frontiers.iso'
    with open(iso_path, 'rb') as f:
        # Check sector 337 (0x2000 * 337 = 0xA8800)
        f.seek(337 * 2048)
        fe_raw = f.read(2048)
        tag_id = struct.unpack('<H', fe_raw[:2])[0]
        print(f"Sector 337 Tag ID: 0x{tag_id:04x}")
        
        if tag_id == 0x0105:
            # Parse size
            size = struct.unpack('<Q', fe_raw[0x38:0x40])[0]
            l_ea = struct.unpack('<I', fe_raw[0xA8:0xAC])[0]
            ad_start = 0xB0 + l_ea
            rel_lba = struct.unpack('<I', fe_raw[ad_start+4:ad_start+8])[0]
            print(f"  Size: {size:,} bytes")
            print(f"  Rel LBA: {rel_lba} (Phys LBA: {rel_lba + 278})")
            
check()
