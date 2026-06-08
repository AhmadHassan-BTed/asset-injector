import pycdlib
import os

def find_all_records(iso_path):
    if not os.path.exists(iso_path):
        print(f"File not found: {iso_path}")
        return
    iso = pycdlib.PyCdlib()
    iso.open(iso_path)
    
    files_to_check = [
        '/DATA/CHAR.ESF;1',
        '/DATA2/CHARCUST.CSF;1',
        '/DATA2/CHARFACE.CSF;1',
        '/DATA2/CHARFACE.ESF;1',
        '/DATA2/CHARSEL1.CSF;1',
        '/DATA2/CHARSEL2.CSF;1',
        '/DATA2/CHARSEL3.CSF;1',
        '/DATA2/CHARSEL4.CSF;1',
    ]
    
    for fpath in files_to_check:
        try:
            record = iso.get_record(iso_path=fpath)
            print(f"File: {fpath:<25} | LBA: {record.orig_extent_loc:<8} | Size: {record.data_length:,} bytes")
        except Exception as e:
            print(f"Error checking {fpath}: {e}")
                
    iso.close()

print("=== Pristine Frontiers ISO ===")
find_all_records('iso/unpatched/EQOA_Frontiers.iso')

print("\n=== Patched Frontiers ISO ===")
find_all_records('iso/patched/EQOA_Frontiers_Patched.iso')
