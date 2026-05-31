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
    print(f"Model container type: {hex(model_container['type_id'])}")
    print(f"Number of children: {len(model_container['children'])}")
    
    print("\nFirst 5 children in model container:")
    for idx, child in enumerate(model_container['children'][:5]):
        print(f"Child {idx}: type={hex(child['type_id'])}, offset={child['offset']}, data_size={child['data_size']}, child_count={child['child_count']}")
        h = parser._find_hash_in_subtree(child)
        print(f"  subtree hash: {f'0x{h:08X}' if h else 'None'}")
        # Print children of this child
        for cidx, subchild in enumerate(child['children']):
            print(f"    Subchild {cidx}: type={hex(subchild['type_id'])}, size={subchild['data_size']}")

inspect()
