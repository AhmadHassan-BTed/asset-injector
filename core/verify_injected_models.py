import os
import sys
import struct
import json
from core.esf_parser import ESFParser

def parse_node(data, pos):
    if pos + 12 > len(data):
        return None, pos
    type_id = struct.unpack_from('<I', data, pos)[0]
    data_size = struct.unpack_from('<I', data, pos + 4)[0]
    child_count = struct.unpack_from('<I', data, pos + 8)[0]
    
    node = {
        'type_id': type_id,
        'data_size': data_size,
        'child_count': child_count,
        'offset': pos,
        'children': [],
        'inline_data': None
    }
    
    next_pos = pos + 12
    if child_count == 0:
        if next_pos + data_size > len(data):
            raise EOFError(f"Unexpected EOF while reading leaf node data at offset 0x{next_pos:X} (expected {data_size} bytes)")
        node['inline_data'] = data[next_pos:next_pos+data_size]
        next_pos += data_size
    else:
        for i in range(child_count):
            try:
                child, next_pos = parse_node(data, next_pos)
                if child is not None:
                    node['children'].append(child)
            except EOFError as e:
                raise EOFError(f"Unexpected EOF while reading child {i} of parent 0x{type_id:05X} (offset 0x{pos:X}): {e}")
            
    return node, next_pos

def main():
    merged_esf = "workspace/FINAL_CHAR_MERGED.ESF"
    json_path = "workspace/target_assets.json"
    
    if not os.path.exists(merged_esf):
        print(f"[-] Error: {merged_esf} not found!")
        return
        
    with open(json_path, 'r') as f:
        targets = json.load(f)
        
    print(f"[*] Reading and parsing merged ESF: {merged_esf}")
    with open(merged_esf, 'rb') as f:
        esf_data = f.read()
        
    parser = ESFParser(esf_data).parse()
    pt_map = {e.asset_id: e for e in parser.pointer_table}
    
    print("\n=== Verifying Injected Models in FINAL_CHAR_MERGED.ESF ===")
    for idx, t in enumerate(targets):
        h = int(t['expansion_hash'], 16)
        print(f"\n[{idx+1}/{len(targets)}] Model 0x{h:08X} (Expansion Index {t['expansion_index']}):")
        if h not in pt_map:
            print("  [-] NOT FOUND in pointer table!")
            continue
            
        entry = pt_map[h]
        print(f"  Pointer Table Entry: offset=0x{entry.offset:X}, len={entry.length:,}, type=0x{entry.type_id:05X}")
        
        # Slice node bytes
        node_bytes = esf_data[entry.offset : entry.offset + entry.length]
        
        try:
            root_node, end_pos = parse_node(node_bytes, 0)
            print(f"  [PASS] Parse tree successful! Total children parsed: {len(root_node['children'])}")
            print(f"  Root: type=0x{root_node['type_id']:05X}, data_size={root_node['data_size']:,}, child_count={root_node['child_count']}")
            for c_idx, child in enumerate(root_node['children']):
                print(f"    Child {c_idx}: type=0x{child['type_id']:05X}, child_count={child['child_count']}, size={child['data_size']}")
                
            # Verify file trailing padding
            trailing = len(node_bytes) - end_pos
            print(f"  Trailing padding in slice: {trailing} bytes")
            
        except Exception as e:
            print(f"  [FAIL] Parsing failed: {e}")

if __name__ == '__main__':
    main()
