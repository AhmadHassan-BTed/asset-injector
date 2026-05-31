import struct

iso_path = 'iso/patched/EQOA_Frontiers_Patched.iso'
with open(iso_path, 'rb') as f:
    data = f.read(100 * 1024 * 1024) # read first 100MB containing directories

targets = [
    (b'\x0ACHAR.ESF;1', 'CHAR.ESF'),
    (b'\x0ECHARCUST.CSF;1', 'CHARCUST.CSF'),
    (b'\x0ECHARSEL1.CSF;1', 'CHARSEL1.CSF')
]

print("Scanning for ISO9660 Directory Records in the first 100MB:")
for search_str, label in targets:
    print(f"\nTarget: {label} (pattern: {search_str.hex()})")
    pos = 0
    count = 0
    while True:
        pos = data.find(search_str, pos)
        if pos == -1:
            break
        count += 1
        dr_start = pos - 32
        # extract LBA and size LE
        lba_le = struct.unpack_from('<I', data, dr_start + 2)[0]
        size_le = struct.unpack_from('<I', data, dr_start + 10)[0]
        print(f"  [{count}] Found at offset 0x{pos:X} (dr_start=0x{dr_start:X}): LBA={lba_le}, Size={size_le:,}")
        pos += len(search_str)
