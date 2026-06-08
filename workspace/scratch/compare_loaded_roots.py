import os
import sys
import struct
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser

def get_node_tree_list(node, depth=0):
    lst = []
    # node is a dict representing the parsed ESF node
    # type_id, data_size, child_count, children, inline_data
    dict_str = ""
    if node['child_count'] == 0 and node['inline_data'] and len(node['inline_data']) >= 4:
        # maybe it has a DictID?
        pass
    
    lst.append((depth, node['type_id'], node['data_size'], node['child_count']))
    for child in node['children']:
        lst.extend(get_node_tree_list(child, depth+1))
    return lst

def inspect():
    with open("workspace/target_assets.json") as f:
        targets = json.load(f)
    target = targets[1]  # 0x05AEBA67
    
    # 1. Load original Frontiers model
    with open("workspace/expansion/CHAR.ESF", 'rb') as f:
        fro_data = f.read()
    fro_parser = ESFParser(fro_data)
    fro_parser.parse()
    fro_container = next(c for c in fro_parser.root['children'] if c['type_id'] == 0x0A010)
    fro_child = fro_container['children'][target['expansion_index']]
    
    # 2. Load grafted payload from FINAL_CHAR_MERGED.ESF
    with open("workspace/FINAL_CHAR_MERGED.ESF", 'rb') as f:
        graft_data = f.read()
    graft_parser = ESFParser(graft_data)
    graft_parser.parse()
    graft_container = next(c for c in graft_parser.root['children'] if c['type_id'] == 0x0A010)
    graft_child = graft_container['children'][target['expansion_index']]
    
    # Dump first 40 nodes of each tree
    fro_tree = get_node_tree_list(fro_child)
    graft_tree = get_node_tree_list(graft_child)
    
    print(f"Comparison for Asset 0x{int(target['expansion_hash'], 16):08X}:")
    print(f"{'Depth':<5} | {'Original Frontiers':<40} | {'Grafted model':<40}")
    print("-" * 90)
    
    max_len = max(len(fro_tree), len(graft_tree))
    for i in range(min(max_len, 60)):
        fro_str = "---"
        if i < len(fro_tree):
            d, t, s, c = fro_tree[i]
            indent = "  " * d
            fro_str = f"{indent}0x{t:05X} (size={s}, children={c})"
            
        graft_str = "---"
        if i < len(graft_tree):
            d, t, s, c = graft_tree[i]
            indent = "  " * d
            graft_str = f"{indent}0x{t:05X} (size={s}, children={c})"
            
        print(f"{i:<5} | {fro_str:<40} | {graft_str:<40}")

inspect()
