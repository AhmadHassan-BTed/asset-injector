import os
import sys
import struct
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def inspect():
    original_file = "workspace/expansion/CHAR.ESF"
    with open(original_file, 'rb') as f:
        data = f.read()
    parser = ESFParser(data)
    parser.parse()
    
    with open("workspace/target_assets.json") as f:
        targets = json.load(f)
        
    model_container = next(c for c in parser.root['children'] if c['type_id'] == 0x0A010)
    print(f"Model Container has {len(model_container['children'])} children.")
    
    for idx, t in enumerate(targets[:5]):
        exp_idx = t['expansion_index']
        if exp_idx < len(model_container['children']):
            child = model_container['children'][exp_idx]
            c_hash = parser._find_hash_in_subtree(child)
            hash_val = c_hash if c_hash is not None else 0
            print(f"Target index {exp_idx} in expansion CHAR.ESF:")
            print(f"  Type ID:   0x{child['type_id']:08X}")
            print(f"  Data Size: {child['data_size']}")
            print(f"  Hash ID:   0x{hash_val:08x} (expected 0x{int(t['expansion_hash'], 16):08x})")
        else:
            print(f"Target index {exp_idx} is out of bounds!")

inspect()
