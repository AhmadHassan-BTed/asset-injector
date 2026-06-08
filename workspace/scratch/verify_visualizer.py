import struct
import math
import sys
import os

sys.path.append(os.path.abspath('.'))
from core.esf_parser import ESFParser

def find_bounding_box(data: bytes, search_limit: int = 256) -> int:
    for i in range(0, min(search_limit, len(data) - 24), 4):
        try:
            floats = struct.unpack_from('<ffffff', data, i)
            valid = True
            for f in floats:
                if math.isnan(f) or math.isinf(f) or abs(f) > 50000.0 or abs(f) < 0.0001 and f != 0.0:
                    valid = False
                    break
            if valid and any(f != 0.0 for f in floats):
                return i
        except Exception:
            continue
    return None

def inspect_model_bounds(esf_path, target_hash, label):
    with open(esf_path, 'rb') as f:
        data = f.read()
    esf = ESFParser(data).parse()
    
    target_node = None
    for entry in esf.pointer_table:
        if entry.asset_id == target_hash:
            def search_tree(node, target_offset):
                if node['offset'] == target_offset: return node
                for c in node.get('children', []):
                    res = search_tree(c, target_offset)
                    if res: return res
                return None
            target_node = search_tree(esf.root, entry.offset)
            break
            
    if not target_node:
        print(f"[-] {label}: target hash not found.")
        return
        
    inline = target_node.get('inline_data', b'')
    if inline is None or len(inline) < 40:
        if target_node.get('children') and len(target_node['children']) > 0:
            first_child = target_node['children'][0]
            if first_child.get('child_count', 0) == 0:
                inline = first_child.get('inline_data', b'')
                
    off = find_bounding_box(inline)
    if off is not None:
        minX, minY, minZ, maxX, maxY, maxZ = struct.unpack_from('<ffffff', inline, off)
        sX, sY, sZ, sR = struct.unpack_from('<ffff', inline, off + 24)
        print(f"[+] {label}: off=0x{off:02X}, inline_len={len(inline)}")
        print(f"    Box: Min({minX:.3f}, {minY:.3f}, {minZ:.3f}) -> Max({maxX:.3f}, {maxY:.3f}, {maxZ:.3f})")
        print(f"    Sphere: Center({sX:.3f}, {sY:.3f}, {sZ:.3f}), Radius: {sR:.3f}")
    else:
        print(f"[-] {label}: Bounding box offset not found. inline_len={len(inline)}")

def main():
    inspect_model_bounds('workspace/original/CHAR.ESF', 0x05AEBA67, "Original Vanilla")
    inspect_model_bounds('workspace/expansion/CHAR.ESF', 0x05AEBA67, "Original Frontiers")
    inspect_model_bounds('workspace/FINAL_CHAR_MERGED.ESF', 0x05AEBA67, "Recompiled Merged")

if __name__ == '__main__':
    main()
