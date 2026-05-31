import os
import sys
import hashlib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.esf_parser import ESFParser, EsfHeader, EsfNodeHeader
from core.esf_rebuilder import serialize_node

def test_identity():
    original_file = "workspace/expansion/CHAR.ESF"
    with open(original_file, 'rb') as f:
        original_data = f.read()
        
    parser = ESFParser(original_data)
    parser.parse()
    
    integrity = parser.verify_integrity()
    original_padding_bytes = integrity['padding_bytes']
    
    output_data = bytearray()
    header_dict = dict(
        version=parser.header.version,
        constant=parser.header.constant,
        reserved1=parser.header.reserved1,
        header_size=parser.header.header_size,
        reserved2=parser.header.reserved2,
        padding=parser.header.padding
    )
    output_data.extend(EsfHeader.build(header_dict))
    output_data.extend(serialize_node(parser.root))
    
    if original_padding_bytes > 0:
        output_data.extend(original_data[-original_padding_bytes:])
        
    orig_hash = hashlib.sha256(original_data).hexdigest()
    rebuilt_hash = hashlib.sha256(output_data).hexdigest()
    
    print(f"Original SHA256: {orig_hash}")
    print(f"Rebuilt SHA256:  {rebuilt_hash}")
    if orig_hash == rebuilt_hash:
        print("[PASS] Rebuilt ESF is byte-for-byte identical!")
    else:
        print("[FAIL] Rebuilt ESF differs!")
        print(f"Original size: {len(original_data):,} bytes")
        print(f"Rebuilt size:  {len(output_data):,} bytes")

test_identity()
