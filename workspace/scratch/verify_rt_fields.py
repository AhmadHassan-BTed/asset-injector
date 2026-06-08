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
    
    # Each entry in ResourceTable (16 bytes):
    #   Offset: uint64 (8 bytes) -> bytes 0 to 7
    #   HashID: uint32 (4 bytes) -> bytes 8 to 11
    #   DictID: uint32 (4 bytes) -> bytes 12 to 15
    table_entries = []
    entry_size = 16
    for i in range(4, len(raw), entry_size):
        offset = struct.unpack_from('<Q', raw, i)[0]
        hash_id = struct.unpack_from('<I', raw, i+8)[0]
        dict_id = struct.unpack_from('<I', raw, i+12)[0]
        table_entries.append((offset, hash_id, dict_id, i))
        
    print(f"Loaded {len(table_entries)} ResourceTable entries.")
    
    # Collect all children of model_container with their offset and subtree hash
    child_info = []
    for idx, child in enumerate(model_container['children']):
        h = parser._find_hash_in_subtree(child)
        child_info.append({
            'idx': idx,
            'offset': child['offset'],
            'size': child['data_size'],
            'hash': h
        })
        
    print(f"Loaded {len(child_info)} Model Container children.")
    
    # Let's see if we can match child_info to table_entries!
    # Let's match by child_info['hash'] == table_entry's hash_id (or dict_id?)
    # or child_info['offset'] == table_entry's offset (or offset - something?)
    matches = 0
    hash_matches = 0
    dict_matches = 0
    offset_matches = 0
    
    # Let's see if there is any overlap
    table_offsets = set(e[0] for e in table_entries)
    table_hashes = set(e[1] for e in table_entries)
    table_dicts = set(e[2] for e in table_entries)
    
    child_offsets = set(c['offset'] for c in child_info)
    child_hashes = set(c['hash'] for c in child_info)
    
    print(f"Overlap between child offsets and table offsets: {len(child_offsets.intersection(table_offsets))}")
    print(f"Overlap between child hashes and table HashIDs: {len(child_hashes.intersection(table_hashes))}")
    print(f"Overlap between child hashes and table DictIDs: {len(child_hashes.intersection(table_dicts))}")
    
    # Let's print the first 5 child_info items
    print("\nFirst 5 child info items:")
    for c in child_info[:5]:
        hash_val = c['hash'] if c['hash'] is not None else 0
        print(f"  Child {c['idx']}: offset={c['offset']}, size={c['size']}, hash=0x{hash_val:08x}")
        
    # Let's print the first 5 table_entries
    print("\nFirst 5 table entries:")
    for idx, e in enumerate(table_entries[:5]):
        print(f"  Entry {idx}: offset={e[0]} (0x{e[0]:x}), hash_id=0x{e[1]:08x}, dict_id=0x{e[2]:08x}")
        
inspect()
