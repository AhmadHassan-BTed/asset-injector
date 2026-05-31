import os
import sys
import struct
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def search_table_for_hashes():
    original_file = "workspace/expansion/CHAR.ESF"
    with open(original_file, 'rb') as f:
        data = f.read()
    parser = ESFParser(data)
    parser.parse()
    
    table_node = next(c for c in parser.root['children'] if c['type_id'] == 0x00009000)
    
    raw = table_node['inline_data']
    count = struct.unpack_from('<I', raw, 0)[0]
    
    targets = [0x19603EEF, 0xCC3EA73A]
    print("Searching Resource Table for target hashes:")
    entry_size = 16
    for i in range(4, len(raw), entry_size):
        h, word1, word2, word3 = struct.unpack('<IIII', raw[i:i+entry_size])
        if h in targets:
            print(f"  FOUND hash 0x{h:08X} at byte {i}! W2={word2}, W3={word3}")
            
    # Let's also print the first 20 entries of 0x9000 raw hashes in hex
    print("\nFirst 20 Resource Table hashes:")
    for i in range(4, 4 + 20 * entry_size, entry_size):
        h, w1, w2, w3 = struct.unpack('<IIII', raw[i:i+entry_size])
        print(f"  Entry {i:3}: 0x{h:08X} (W2={w2}, W3={w3})")

search_table_for_hashes()
