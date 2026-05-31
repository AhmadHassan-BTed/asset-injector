import os
import sys
import struct
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def find_at_offset():
    original_file = "workspace/expansion/CHAR.ESF"
    target_offset = 1267144
    
    with open(original_file, 'rb') as f:
        f.seek(target_offset)
        # Read the 12-byte node header
        hdr = f.read(12)
        type_id, data_size, child_count = struct.unpack('<III', hdr)
        print(f"Node at offset {target_offset}:")
        print(f"  Type ID:   0x{type_id:08X}")
        print(f"  Data Size: {data_size}")
        print(f"  Child Cnt: {child_count}")

find_at_offset()
