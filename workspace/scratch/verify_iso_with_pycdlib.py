import pycdlib
import os
import sys

def verify_iso(iso_path):
    if not os.path.exists(iso_path):
        print(f"[-] Error: File not found: {iso_path}")
        return False
        
    print(f"[*] Opening ISO via pycdlib: {iso_path}...")
    iso = pycdlib.PyCdlib()
    try:
        iso.open(iso_path)
        print("[+] Success: pycdlib successfully opened the ISO! Filesystem is valid.")
        
        # Walk and verify we can get records
        print("[*] Walking filesystem to verify records...")
        files_checked = 0
        for root, dirs, files in iso.walk(iso_path='/'):
            for f in files:
                fpath = f"{root}/{f}"
                record = iso.get_record(iso_path=fpath)
                files_checked += 1
                
        print(f"[+] Walk complete: successfully verified {files_checked} files.")
        iso.close()
        return True
    except Exception as e:
        print(f"[-] UDF/ISO9660 Parsing Error: {e}")
        if iso:
            try:
                iso.close()
            except Exception:
                pass
        return False

verify_iso('iso/patched/EQOA_Frontiers_Patched.iso')
