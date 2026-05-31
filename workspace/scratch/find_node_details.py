import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def find_details():
    original_file = "workspace/expansion/CHAR.ESF"
    with open(original_file, 'rb') as f:
        data = f.read()
    parser = ESFParser(data)
    parser.parse()
    
    # Let's find the container 0xA010
    model_container = next(c for c in parser.root['children'] if c['type_id'] == 0x0A010)
    
    # Print details for first child
    first_child = model_container['children'][0]
    first_hash = parser._find_hash_in_subtree(first_child)
    
    print("First Child Node Details:")
    print(f"  Type ID:   0x{first_child['type_id']:08X}")
    print(f"  Data Size: {first_child['data_size']}")
    print(f"  Child Cnt: {first_child['child_count']}")
    print(f"  Absolute Offset: 0x{first_child['offset']:08X} ({first_child['offset']} bytes)")
    print(f"  Asset Hash: 0x{first_hash:08X} (dec: {first_hash})")
    
    # Word 2 from table: 170979
    # Word 3 from table: 1267144
    # Wait, let's look at relations!
    # Does 1267144 / 2048 or something?
    # Or is 1267144 the offset relative to some container start?
    # Container offset is first_child['offset']?
    # Root node start is 32.
    # Model container start is: model_container['offset'] = 32 + 12 + 6564 = 6608?
    # Let's check model_container offset
    print(f"Model Container Offset: {model_container['offset']}")
    print(f"Model Container Data Offset: {model_container['offset'] + 12}")
    
    # Let's see if Word 3 (1267144) matches the offset of first_child relative to model container data offset!
    # first_child['offset'] = 1267156?
    # 1267156 - 12 = 1267144!
    # Oh my god!
    # first_child['offset'] = 1267144 + (model_container['offset'] + 12)?
    # Let's calculate!
    # model_container['offset'] + 12 + 1267144 = 6608 + 1267144 = 1273752?
    # Let's print the actual offsets to check this relationship!

find_details()
