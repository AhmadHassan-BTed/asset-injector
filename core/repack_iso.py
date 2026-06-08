#!/usr/bin/env python3
import os
import sys
import shutil
import struct
import mmap

def repack_iso():
    # Terminate running PCSX2 emulator if it is open to avoid file locks on the patched ISO
    try:
        import subprocess
        res = subprocess.run(["tasklist"], capture_output=True, text=True)
        if "pcsx2-qt.exe" in res.stdout.lower():
            print("[*] Detected running PCSX2 emulator. Terminating to avoid file locks...")
            subprocess.run(["taskkill", "/F", "/IM", "pcsx2-qt.exe"], capture_output=True)
    except Exception as e:
        print(f"[!] Warning: Could not check or terminate PCSX2 process: {e}")

    iso_path = 'iso/unpatched/EQOA_Frontiers.iso'
    patched_path = 'iso/patched/EQOA_Frontiers_Patched.iso'
    tmp_path = patched_path + '.tmp'
    esf_path = 'workspace/FINAL_CHAR_MERGED.ESF'

    if not os.path.exists(iso_path):
        print(f"[-] Error: Could not find original ISO {iso_path}")
        sys.exit(1)
        
    if not os.path.exists(esf_path):
        print(f"[-] Error: Could not find merged ESF {esf_path}")
        sys.exit(1)

    print(f"[*] Copying {iso_path} -> {tmp_path} ...")
    shutil.copyfile(iso_path, tmp_path)
    
    iso_size = os.path.getsize(tmp_path)
    esf_size = os.path.getsize(esf_path)
    
    padding_bytes = 0
    if iso_size % 2048 != 0:
        padding_bytes = 2048 - (iso_size % 2048)
        
    new_lba = (iso_size + padding_bytes) // 2048
    
    with open(tmp_path, 'r+b') as f:
        f.seek(0, 2)
        if padding_bytes > 0:
            f.write(b'\x00' * padding_bytes)
            
        with open(esf_path, 'rb') as esf_f:
            for chunk in iter(lambda: esf_f.read(4 * 1024 * 1024), b""):
                f.write(chunk)
                
        # 1. Enforce 2048-Byte EOF Padding
        filesize = f.tell()
        remainder = filesize % 2048
        if remainder != 0:
            padding_needed = 2048 - remainder
            f.write(b'\x00' * padding_needed)
            final_aligned_filesize = filesize + padding_needed
        else:
            final_aligned_filesize = filesize

        # 2. UDF AVDP Splicing for UDF compliance
        f.seek((new_lba - 1) * 2048)
        avdp_sector = f.read(2048)
        if len(avdp_sector) == 2048 and struct.unpack('<H', avdp_sector[:2])[0] == 2:
            f.seek(0, 2)
            f.write(avdp_sector)
            final_aligned_filesize += 2048
                
    # Surgical LBA patch
    records_patched = 0
    with open(tmp_path, 'r+b') as f:
        mm = mmap.mmap(f.fileno(), 0)
        search_str = b'\x0ACHAR.ESF;1'
        idx = 0
        while True:
            idx = mm.find(search_str, idx)
            if idx == -1: break
            dr_start = idx - 32
            lba_le = struct.unpack('<I', mm[dr_start+2:dr_start+6])[0]
            lba_be = struct.unpack('>I', mm[dr_start+6:dr_start+10])[0]
            if lba_le == lba_be:
                mm[dr_start+2:dr_start+6] = struct.pack('<I', new_lba)
                mm[dr_start+6:dr_start+10] = struct.pack('>I', new_lba)
                mm[dr_start+10:dr_start+14] = struct.pack('<I', esf_size)
                mm[dr_start+14:dr_start+18] = struct.pack('>I', esf_size)
                records_patched += 1
            idx += len(search_str)

        pvd_offset = 16 * 2048
        if mm[pvd_offset:pvd_offset+6] == b'\x01CD001':
            total_sectors = final_aligned_filesize // 2048
            mm[pvd_offset+80:pvd_offset+84] = struct.pack('<I', total_sectors)
            mm[pvd_offset+84:pvd_offset+88] = struct.pack('>I', total_sectors)
            
        mm.close()

    # ATOMIC COMMIT
    try:
        os.replace(tmp_path, patched_path)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise IOError(f"ATOMIC COMMIT FAILED: Unable to overwrite '{patched_path}'. File lock detected. Exception: {e}")

if __name__ == '__main__':
    repack_iso()
