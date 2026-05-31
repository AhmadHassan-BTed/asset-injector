import os
import sys
import struct
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def parse_table():
    original_file = "workspace/expansion/CHAR.ESF"
    with open(original_file, 'rb') as f:
        data = f.read()
        
    parser = ESFParser(data)
    parser.parse()
    
    table_node = None
    for child in parser.root['children']:
        if child['type_id'] == 0x00009000:
            table_node = child
            break
            
    if not table_node:
        print("[-] Table node 0x9000 not found!")
        return
        
    raw = table_node['inline_data']
    print(f"[*] Resource Table size: {len(raw)} bytes")
    
    # Let's inspect the first 64 bytes
    print("\n[*] First 64 bytes of 0x9000 inline data:")
    for i in range(0, min(len(raw), 128), 16):
        chunk = raw[i:i+16]
        hex_str = " ".join([f"{b:02X}" for b in chunk])
        print(f"  0x{i:04X}: {hex_str}")
        
    # Let's try parsing as 16-byte entries or similar
    # In Frontiers, there are 582 children in model_container 0xA010
    # Let's see if we can find entries matching model indexes or hashes
    print("\n[*] Parsing entries:")
    # Check if first 4 bytes is count
    count = struct.unpack_from('<I', raw, 0)[0]
    print(f"  First 4 bytes as LE uint32: {count} (expected 582 or similar)")
    
    # Let's read entries of 16 bytes
    # Each entry might have: ID/Hash, offset, size, type etc.
    entry_size = 16
    for i in range(4, min(len(raw), 4 + 5 * entry_size), entry_size):
        entry_raw = raw[i:i+entry_size]
        # Let's try unpacking as four uint32
        words = struct.unpack('<IIII', entry_raw)
        print(f"  Entry at byte {i}: {words} | hex: {[f'0x{w:08X}' for w in words]}")

parse_table()
