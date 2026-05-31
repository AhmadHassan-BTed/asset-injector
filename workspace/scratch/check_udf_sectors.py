import struct
import os

def check_file_and_pvd(iso_path):
    if not os.path.exists(iso_path):
        print(f"File not found: {iso_path}")
        return
        
    actual_size = os.path.getsize(iso_path)
    actual_sectors = actual_size // 2048
    
    with open(iso_path, 'rb') as f:
        # PVD is at sector 16
        f.seek(16 * 2048)
        pvd_data = f.read(2048)
        
        # Total sectors is at offset 80 (4-byte LE) and 84 (4-byte BE)
        pvd_sectors_le = struct.unpack('<I', pvd_data[80:84])[0]
        pvd_sectors_be = struct.unpack('>I', pvd_data[84:88])[0]
        
        print(f"Actual ISO File Size: {actual_size:,} bytes")
        print(f"Actual ISO Sectors:   {actual_sectors}")
        print(f"PVD Total Sectors LE: {pvd_sectors_le}")
        print(f"PVD Total Sectors BE: {pvd_sectors_be}")
        
        # Check AVDP at sector 256
        f.seek(256 * 2048)
        avdp_256 = f.read(16)
        print(f"AVDP at sector 256 tag: {struct.unpack('<H', avdp_256[:2])[0]}")
        
        # Check AVDP at last sector (actual_sectors - 1)
        f.seek((actual_sectors - 1) * 2048)
        avdp_last = f.read(16)
        if len(avdp_last) >= 2:
            print(f"AVDP at last sector ({actual_sectors - 1}) tag: {struct.unpack('<H', avdp_last[:2])[0]}")
        else:
            print(f"AVDP at last sector is EMPTY!")
            
        # Check AVDP at pvd_sectors_le - 1
        f.seek((pvd_sectors_le - 1) * 2048)
        avdp_pvd = f.read(16)
        if len(avdp_pvd) >= 2:
            print(f"AVDP at PVD last sector ({pvd_sectors_le - 1}) tag: {struct.unpack('<H', avdp_pvd[:2])[0]}")
        else:
            print(f"AVDP at PVD last sector is EMPTY!")

check_file_and_pvd('iso/patched/EQOA_Frontiers_Patched.iso')
