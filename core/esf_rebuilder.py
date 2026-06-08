import os
import sys
import json
import hashlib
import struct
from construct import Struct, Const, Int32ul, Bytes
from core.esf_parser import ESFParser, EsfHeader, EsfNodeHeader

def get_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def serialize_node(node):
    if 'raw_data' in node and node['raw_data'] is not None:
        return node['raw_data']
    data = bytearray()
    header = EsfNodeHeader.build(dict(
        type_id=node['type_id'],
        data_size=node['data_size'],
        child_count=node['child_count']
    ))
    data.extend(header)
    
    if node['child_count'] == 0:
        if node['inline_data'] is not None:
            data.extend(node['inline_data'])
    else:
        for child in node['children']:
            data.extend(serialize_node(child))
    return data

def add_padding_to_tree(node, p):
    """Recursively add padding to the last leaf node of a tree."""
    if p == 0:
        return 0
    if node['child_count'] == 0:
        if node['inline_data'] is None:
            node['inline_data'] = bytearray()
        elif isinstance(node['inline_data'], bytes):
            node['inline_data'] = bytearray(node['inline_data'])
        node['inline_data'].extend(b'\x00' * p)
        node['data_size'] += p
        return p
    else:
        last_child = node['children'][-1]
        p_added = add_padding_to_tree(last_child, p)
        node['data_size'] += p_added
        return p_added

def main():
    original_file = "workspace/expansion/CHAR.ESF"
    output_file = "workspace/FINAL_CHAR_MERGED.ESF"
    json_path = "workspace/target_assets.json"

    if not os.path.exists(original_file):
        print(f"[-] Error: Could not find {original_file}")
        sys.exit(1)

    with open(json_path, 'r') as f:
        targets = json.load(f)
    target_map = { int(t['expansion_hash'], 16): t for t in targets }

    print(f"[*] Reading Expansion ESF: {original_file}")
    with open(original_file, 'rb') as f:
        original_data = f.read()

    parser = ESFParser(original_data)
    parser.parse()
    
    # Store the original padding at the end of the file
    integrity = parser.verify_integrity()
    original_padding_bytes = integrity['padding_bytes']

    # Locate Model Container
    model_container = None
    for child in parser.root['children']:
        if child['type_id'] == 0x0A010:
            model_container = child
            break
            
    if not model_container:
        print("[-] Error: Model Container not found!")
        sys.exit(1)

    # Map original offsets of the children in the model container
    original_offsets = [child['offset'] for child in model_container['children']]
    offset_to_index = {offset: idx for idx, offset in enumerate(original_offsets)}

    print("[*] Scanning payloads directory for injection...")
    import glob
    bin_files = glob.glob("workspace/payloads/*.bin")
    
    # Pre-map all hashes existing in the Model Container
    existing_hashes = {}
    for i, child in enumerate(model_container['children']):
        ah = parser._find_hash_in_subtree(child)
        if ah is not None:
            existing_hashes[ah] = i

    total_delta = 0
    injected_count = 0
    appended_count = 0

    for bin_path in bin_files:
        # Extract hash from filename (e.g., asset_0x05AEBA67.bin)
        filename = os.path.basename(bin_path)
        try:
            hash_str = filename.split('_')[1].split('.')[0]
            asset_hash = int(hash_str, 16)
        except Exception:
            print(f"[-] Warning: Unrecognized payload format: {filename}")
            continue
            
        with open(bin_path, 'rb') as bf:
            bin_data = bf.read()
            
        # Parse only the 12-byte header of the .bin payload
        type_id = struct.unpack_from('<I', bin_data, 0)[0]
        data_size = struct.unpack_from('<I', bin_data, 4)[0]
        child_count = struct.unpack_from('<I', bin_data, 8)[0]
        
        payload_node = {
            'type_id': type_id,
            'data_size': data_size,
            'child_count': child_count,
            'children': [],
            'inline_data': None,
            'raw_data': bin_data
        }
        
        new_payload_size = len(bin_data)
        p = 0
        new_total_size = new_payload_size
        
        # Inject or Append logic
        if asset_hash in existing_hashes:
            # Replace existing node
            idx = existing_hashes[asset_hash]
            old_child = model_container['children'][idx]
            old_total_size = 12 + old_child['data_size']
            
            model_container['children'][idx] = payload_node
            
            delta = new_total_size - old_total_size
            total_delta += delta
            injected_count += 1
            print(f"  [+] Injected 0x{asset_hash:08X} | Size: {new_payload_size} | Delta: {delta}")
        else:
            # Append as a brand new node (Dependency not natively in Frontiers)
            model_container['children'].append(payload_node)
            model_container['child_count'] += 1
            
            total_delta += new_total_size
            appended_count += 1
            print(f"  [+] Appended New Dependency: 0x{asset_hash:08X} | Size: {new_payload_size} | Padding: {p}")

    # Update data_size of parent nodes
    model_container['data_size'] += total_delta
    parser.root['data_size'] += total_delta

    print(f"[*] Injected {injected_count} and Appended {appended_count} recursive payloads. Total shift applied: {total_delta} bytes.")

    # Helper to calculate precise serialized size of any node tree
    def get_serialized_size(node):
        if 'raw_data' in node and node['raw_data'] is not None:
            return len(node['raw_data'])
        size = 12
        if node['child_count'] == 0:
            if node['inline_data'] is not None:
                size += len(node['inline_data'])
        else:
            for child in node['children']:
                size += get_serialized_size(child)
        return size

    # Recompute the new offsets for all children in model_container
    new_offsets = []
    current_offset = 56  # child 0 starts at 56 (32 ESF header + 12 root header + 12 container header)
    for child in model_container['children']:
        new_offsets.append(current_offset)
        current_offset += get_serialized_size(child)

    # Locate and patch Resource Table 0x09000
    table_node = None
    for child in parser.root['children']:
        if child['type_id'] == 0x00009000:
            table_node = child
            break

    if table_node:
        print("[*] Found Resource Table (0x09000). Patching offsets...")
        table_inline_data = bytearray(table_node['inline_data'])
        count = struct.unpack_from('<I', table_inline_data, 0)[0]
        
        patched_count = 0
        for i in range(count):
            elem_offset = 4 + i * 16
            original_offset = struct.unpack_from('<Q', table_inline_data, elem_offset)[0]
            
            idx = offset_to_index.get(original_offset)
            if idx is not None:
                # Update with the new offset
                new_offset = new_offsets[idx]
                struct.pack_into('<Q', table_inline_data, elem_offset, new_offset)
                patched_count += 1
            else:
                print(f"  [-] Warning: Original offset {original_offset} not found in model children mapping")
                
        table_node['inline_data'] = table_inline_data
        print(f"[+] Resource Table successfully patched: {patched_count}/{count} offsets updated.")
    else:
        print("[-] Warning: Resource Table (0x09000) not found!")

    print("[*] Rebuilding ESF...")
    output_data = bytearray()
    
    # Serialize file header
    header_dict = dict(
        version=parser.header.version,
        constant=parser.header.constant,
        reserved1=parser.header.reserved1,
        header_size=parser.header.header_size,
        reserved2=parser.header.reserved2,
        padding=parser.header.padding
    )
    output_data.extend(EsfHeader.build(header_dict))
    
    # Serialize root node and all descendants
    output_data.extend(serialize_node(parser.root))
    
    # Append the original end-of-file padding
    if original_padding_bytes > 0:
        output_data.extend(original_data[-original_padding_bytes:])
        
    print(f"[*] Saving rebuilt ESF: {output_file}")
    with open(output_file, 'wb') as f:
        f.write(output_data)
        
    print("[+] FINAL_CHAR_MERGED.ESF creation complete!")

if __name__ == '__main__':
    main()
