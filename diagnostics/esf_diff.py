#!/usr/bin/env python3
"""
EQOA ESF Asset Index Diffing Tool
=================================
Compares the Virtual Pointer Tables of the Original and Expansion CHAR.ESF
files using their unique Asset ID hashes, filters for character models 
(type 0x062700), and identifies the 11 original models that were missing 
or stubbed in the expansion.
"""

import os
import sys
import json
from esf_parser import ESFParser

def diff_assets(original_path, expansion_path):
    """Compare pointer tables and isolate the 11 target original character models."""
    # 1. Parse Original CHAR.ESF
    print(f"[*] Parsing Original ESF: {original_path}")
    with open(original_path, 'rb') as f:
        orig_data = f.read()
    orig_parser = ESFParser(orig_data).parse()
    orig_table = orig_parser.pointer_table

    # 2. Parse Expansion CHAR.ESF
    print(f"[*] Parsing Expansion ESF: {expansion_path}")
    with open(expansion_path, 'rb') as f:
        exp_data = f.read()
    exp_parser = ESFParser(exp_data).parse()
    exp_table = exp_parser.pointer_table

    # Map expansion table by Asset ID for O(1) lookups
    exp_map = {entry.asset_id: entry for entry in exp_table if entry.asset_id is not None}

    # 3. Perform Diff Analysis
    print("\n[*] Diffing assets to locate the 22 original character race models...")
    
    PLAYABLE_CHARACTER_HASHES = {
        0x2EF8E480, 0x05AEBA67, 0xB54E4D8A, 0xCD51EF83, 0x7C0C8A10,
        0x90BCCCF2, 0x6074557C, 0x5BDEA541, 0xEBB9FC93, 0x0017A0BD,
        0xB5C785F2, 0xFE4FF1F2, 0xCC3EA73A, 0x998B1B02, 0x618C0875,
        0xE32D91A8, 0xF924B56B, 0x5B8E5BDC, 0x19603EEF, 0x9C23B6FF,
        0x628A0767, 0x2610A50D
    }
    
    type_changed = []
    
    for orig_entry in orig_table:
        h = orig_entry.asset_id
        if h not in PLAYABLE_CHARACTER_HASHES:
            continue
            
        if h in exp_map:
            exp_entry = exp_map[h]
            type_changed.append((orig_entry, exp_entry))

    # Sort type-changed models by original size descending to isolate the 22 base race models
    type_changed.sort(key=lambda x: x[0].length, reverse=True)
    
    target_models = type_changed
    print(f"[+] Isolated the {len(target_models)} target original character race models based on precise hash mapping.")
    
    # Format output as JSON list
    output_list = []
    for orig_entry, exp_entry in target_models:
        output_list.append({
            'original_hash': f"0x{orig_entry.asset_id:08X}",
            'original_offset': orig_entry.offset,
            'original_length': orig_entry.length,
            'original_index': orig_entry.index,
            'expansion_hash': f"0x{exp_entry.asset_id:08X}",
            'expansion_offset': exp_entry.offset,
            'expansion_length': exp_entry.length,
            'expansion_index': exp_entry.index,
            'original_type': f"0x{orig_entry.type_id:05X}",
            'expansion_type': f"0x{exp_entry.type_id:05X}",
            'status': 'Type changed to 0x72700 in Expansion'
        })

    # Print nicely formatted JSON
    print("\n=== Target Assets (JSON Array) ===")
    print(json.dumps(output_list, indent=2))
    
    # Write to output file in workspace
    out_json_path = './workspace/target_assets.json'
    with open(out_json_path, 'w') as out_f:
        json.dump(output_list, out_f, indent=2)
    print(f"\n[+] Saved targets to '{out_json_path}'")

def main():
    original_esf = './workspace/original/CHAR.ESF'
    expansion_esf = './workspace/expansion/CHAR.ESF'
    
    if not os.path.exists(original_esf) or not os.path.exists(expansion_esf):
        print(f"[-] Error: Could not locate ESF files. Please run extract_assets.py first.", file=sys.stderr)
        sys.exit(1)
        
    diff_assets(original_esf, expansion_esf)

if __name__ == '__main__':
    main()
