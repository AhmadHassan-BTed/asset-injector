import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def list_containers(path):
    print(f"\n[*] Parsing: {path}")
    with open(path, 'rb') as f:
        data = f.read()
    parser = ESFParser(data)
    parser.parse()
    
    print(f"Root Node: type_id=0x{parser.root['type_id']:08X}, data_size={parser.root['data_size']}, child_count={parser.root['child_count']}")
    for child in parser.root['children']:
        print(f"  Container: type_id=0x{child['type_id']:08X}, data_size={child['data_size']}, child_count={child['child_count']}")

list_containers("workspace/original/CHAR.ESF")
list_containers("workspace/expansion/CHAR.ESF")
