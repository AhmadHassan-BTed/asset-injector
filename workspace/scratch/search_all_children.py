import os
import sys
import struct
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def map_table():
    original_file = "workspace/expansion/CHAR.ESF"
    with open(original_file, 'rb') as f:
        data = f.read()
    parser = ESFParser(data)
    parser.parse()
    
    model_container = next(c for c in parser.root['children'] if c['type_id'] == 0x0A010)
    table_node = next(c for c in parser.root['children'] if c['type_id'] == 0x00009000)
    
    raw = table_node['inline_data']
    count = struct.unpack_from('<I', raw, 0)[0]
    print(f"Total entries in table: {count}")
    
    # Map model container hashes
    model_hashes = {}
    for idx, child in enumerate(model_container['children']):
        h = parser._find_hash_in_subtree(child)
        if h is not None:
            model_hashes[h] = (idx, child['offset'], child['data_size'])
            
    print(f"Total model hashes parsed from container: {len(model_hashes)}")
    
    # Now let's check first 10 table entries and see if they exist in model_hashes
    entry_size = 16
    matched_count = 0
    print("\nMapping first 10 table entries:")
    for i in range(4, 4 + 10 * entry_size, entry_size):
        entry_raw = raw[i:i+entry_size]
        h, word1, word2, word3 = struct.unpack('<IIII', entry_raw)
        
        match = model_hashes.get(h)
        if match:
            idx, offset, size = match
            print(f"  Entry h=0x{h:08x}: Index={idx:3} | Table(W2={word2:7}, W3={word3:7}) | Node(Offset={offset:7}, Size={size:7})")
            matched_count += 1
        else:
            print(f"  Entry h=0x{h:08x}: NOT FOUND IN CONTAINER (W2={word2}, W3={word3})")
            
    # Let's count how many overall entries match
    all_matched = 0
    for i in range(4, len(raw), entry_size):
        h, word1, word2, word3 = struct.unpack('<IIII', raw[i:i+entry_size])
        if h in model_hashes:
            all_matched += 1
            
    print(f"\nOverall matches between table and container: {all_matched} / {count}")

map_table()
