import pycdlib

def list_sorted_lba(iso_path):
    iso = pycdlib.PyCdlib()
    iso.open(iso_path)
    files = []
    for root, dirs, filenames in iso.walk(iso_path='/'):
        for f in filenames:
            fpath = f"{root}/{f}"
            try:
                record = iso.get_record(iso_path=fpath)
                extent = None
                for attr in ['extent_loc', 'extent_location', 'location', 'extent']:
                    if hasattr(record, attr):
                        val = getattr(record, attr)
                        if callable(val):
                            extent = val()
                        else:
                            extent = val
                        break
                if extent is not None:
                    files.append((extent, record.data_length, fpath))
            except:
                pass
    files.sort(key=lambda x: x[0])
    for extent, length, path in files:
        if '.ESF' in path.upper() or '.CSF' in path.upper():
            print(f"LBA: {extent:7d} | Size: {length:11,} B | {path}")
    iso.close()

list_sorted_lba('iso/patched/EQOA_Frontiers_Patched.iso')

