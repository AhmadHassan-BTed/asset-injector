import os
import sys
import struct
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def inspect():
    original_file = "workspace/expansion/CHAR.ESF"
    with open(original_file, 'rb') as f:
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
        h, w1, w2, w3 = struct.unpack('<IIII', raw[i:i+entry_size])
        table_entries.append((h, w1, w2, w3))
        
    table_hashes = set(x[0] for x in table_entries)
    
    # Collect all hashes in the model container children subtrees
    child_hashes = []
    for idx, child in enumerate(model_container['children']):
        h = parser._find_hash_in_subtree(child)
        child_hashes.append((idx, h, child['offset'], child['data_size']))
        
    matched = []
    unmatched = []
    for idx, h, offset, size in child_hashes:
        if h in table_hashes:
            matched.append((idx, h, offset, size))
        else:
            unmatched.append((idx, h, offset, size))
            
    print(f"Total model children hashes: {len(child_hashes)}")
    print(f"Matched in Resource Table: {len(matched)}")
    print(f"Unmatched in Resource Table: {len(unmatched)}")
    
    if matched:
        print("\nSome matched entries:")
        for idx, h, offset, size in matched[:5]:
            # Find the corresponding entry in table
            entry = next(x for x in table_entries if x[0] == h)
            print(f"  Child {idx} (hash 0x{h:08x}): offset={offset}, size={size} | Table w1={entry[1]}, w2={entry[2]}, w3={entry[3]}")
            
    if unmatched:
        print("\nSome unmatched entries:")
        for idx, h, offset, size in unmatched[:5]:
            print(f"  Child {idx} (hash {f'0x{h:08x}' if h else 'None'}): offset={offset}, size={size}")

inspect()
