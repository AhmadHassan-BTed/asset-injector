import os
import sys
import struct
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def inspect():
    rebuilt_file = "workspace/FINAL_CHAR_MERGED.ESF"
    if not os.path.exists(rebuilt_file):
        print("[-] Error: Rebuilt file not found!")
        return
        
    with open(rebuilt_file, 'rb') as f:
        data = f.read()
    parser = ESFParser(data)
    parser.parse()
    
    model_container = next(c for c in parser.root['children'] if c['type_id'] == 0x0A010)
    table_node = next(c for c in parser.root['children'] if c['type_id'] == 0x00009000)
    
    raw = table_node['inline_data']
    count = struct.unpack_from('<I', raw, 0)[0]
    
    table_entries = []
    entry_size = 16
    for i in range(4, len(raw), entry_size):
        offset = struct.unpack_from('<Q', raw, i)[0]
        hash_id = struct.unpack_from('<I', raw, i+8)[0]
        dict_id = struct.unpack_from('<I', raw, i+12)[0]
        table_entries.append((offset, hash_id, dict_id))
        
    # Map offset -> entry
    offset_to_entry = { e[0]: e for e in table_entries }
    
    # Check model container children offsets
    child_offsets = [child['offset'] for child in model_container['children']]
    
    matched = 0
    mismatched_children = []
    for idx, child in enumerate(model_container['children']):
        c_off = child['offset']
        if c_off in offset_to_entry:
            matched += 1
        else:
            mismatched_children.append((idx, c_off))
            
    print(f"Total model children: {len(model_container['children'])}")
    print(f"Matched entries in rebuilt ResourceTable: {matched}")
    print(f"Mismatched children: {len(mismatched_children)}")
    
    if mismatched_children:
        print("\nSome mismatched children details:")
        for idx, c_off in mismatched_children[:10]:
            print(f"  Child {idx}: Offset={c_off}")
            
    # Let's inspect the first 5 table entries
    print("\nFirst 5 table entries in rebuilt:")
    for idx, e in enumerate(table_entries[:5]):
        print(f"  Entry {idx}: offset={e[0]} (0x{e[0]:x}), hash_id=0x{e[1]:08x}, dict_id=0x{e[2]:08x}")

inspect()
