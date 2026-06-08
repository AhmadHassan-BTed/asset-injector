import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def inspect():
    original_file = "workspace/expansion/CHAR.ESF"
    with open(original_file, 'rb') as f:
        data = f.read()
    parser = ESFParser(data)
    parser.parse()
    
    print("Root children:")
    for idx, child in enumerate(parser.root['children']):
        print(f"Child {idx}: type={hex(child['type_id'])}, offset={child['offset']}, size={child['data_size']}, child_count={child['child_count']}")

inspect()
