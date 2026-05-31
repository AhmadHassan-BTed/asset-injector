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
    
    # Let's collect all children of model_container
    # and print their properties alongside the table entries to see if we can sort and match them.
    children = model_container['children']
    print(f"Model children count: {len(children)}")
    print(f"Table entries count: {count}")
    
    # We will build a list of table entries
    table_entries = []
    entry_size = 16
    for i in range(4, len(raw), entry_size):
        h, w1, w2, w3 = struct.unpack('<IIII', raw[i:i+entry_size])
        table_entries.append((h, w1, w2, w3, i))
        
    # Let's see if we can match any children's offset or data_size to w2 and w3
    # Maybe the table entries are sorted by something?
    # Let's sort the children by offset (which is already true, as they are sequential in the file)
    # Let's sort table entries by w3 (which seems to be increasing: 1267144, 1403392, 1941215, 2176316...)
    table_entries_sorted_by_w3 = sorted(table_entries, key=lambda x: x[3])
    
    print("\nFirst 10 table entries sorted by w3:")
    for idx, (h, w1, w2, w3, pos) in enumerate(table_entries_sorted_by_w3[:10]):
        print(f"Table idx {idx}: h=0x{h:08x}, w1={w1}, w2={w2}, w3={w3} (pos={pos})")
        
    print("\nLet's check if the difference between w3 values matches the children sizes!")
    # Let's compare w3 and children offsets or sizes
    # w3 values are:
    # 1267144, 1403392, 1941215, 2176316, 2907974...
    # Let's look at the sizes:
    # 1403392 - 1267144 = 136248
    # 1941215 - 1403392 = 537823
    # 2176316 - 1941215 = 235101
    
    # Wait, are there 582 entries in both? Yes.
    # Is it possible that the table entries correspond to the children, but they are in a different order?
    # Let's check if every child's offset (or offset - header_offset) has a match in the table entries!
    offsets_in_table = set(x[3] for x in table_entries)
    child_offsets = [c['offset'] for c in children]
    
    # Let's check how many child offsets (minus something?) exist in table's w3
    matched_exact = 0
    matched_offset_minus_44 = 0
    matched_offset_minus_56 = 0
    
    for c in children:
        off = c['offset']
        if off in offsets_in_table:
            matched_exact += 1
        if (off - 44) in offsets_in_table:
            matched_offset_minus_44 += 1
        if (off - 56) in offsets_in_table:
            matched_offset_minus_56 += 1
            
    print(f"\nMatching child offsets to w3:")
    print(f"  Exact matches: {matched_exact}")
    print(f"  Matches with offset - 44: {matched_offset_minus_44}")
    print(f"  Matches with offset - 56: {matched_offset_minus_56}")
    
    # Let's see if we can find any child offset in offsets_in_table with a constant shift!
    # Let's calculate the difference between the first child offset and the smallest w3
    # Child 0 offset is 56. Smallest w3?
    min_w3 = min(x[3] for x in table_entries)
    print(f"  Min w3: {min_w3}")
    
    # Let's see if we can find a constant difference
    diffs = {}
    for c in children:
        c_off = c['offset']
        for h, w1, w2, w3, pos in table_entries:
            d = c_off - w3
            diffs[d] = diffs.get(d, 0) + 1
            
    # Sort diffs by frequency
    sorted_diffs = sorted(diffs.items(), key=lambda x: x[1], reverse=True)
    print("\nMost common differences (child_offset - w3):")
    for d, freq in sorted_diffs[:10]:
        print(f"  Difference {d}: freq {freq}")

inspect()
