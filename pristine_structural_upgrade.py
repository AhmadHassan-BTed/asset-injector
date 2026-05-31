#!/usr/bin/env python3
"""
pristine_structural_upgrade.py
===============================
Surgical texture-only transplant from a Vanilla (0x62700) character model
onto a Frontiers (0x72700) character model.

Contract
--------
- ONLY nodes inside the Texture Container (0x11110 / 0x11100) are modified.
- Every geometry, skeleton, bone-matrix, and root-header node in the Frontiers
  model is left **100% byte-identical** to the original.
- Vanilla texture payloads (0x01001 children) overwrite Frontiers counterparts.
- The corresponding Frontiers GS material registers (0x01101 children) are
  patched so that TEX0.TW / TEX0.TH reflect the Vanilla texture's dimensions,
  preventing UV-coordinate mis-mapping on the PS2 Graphics Synthesizer.

Dependency surface (copy these from vanilla_to_frontiers_transplant.py)
-----------------------------------------------------------------------
    parse_node, update_node_sizes, serialize_node
    _extract_bits, _insert_bits, parse_tex0, encode_tex0, _TEX0_FIELDS
    get_vanilla_texture_dimensions
    GS_REG_TEX0_1, GS_REG_TEX0_2, PSM_PALETTED
"""

import copy
import math
import struct


# ─────────────────────────────────────────────────────────────────────────────
# PS2 GS Constants
# ─────────────────────────────────────────────────────────────────────────────

GS_REG_TEX0_1 = 0x06
GS_REG_TEX0_2 = 0x16
PSM_PALETTED   = {0x13, 0x14, 0x1B, 0x24, 0x2C}

# TEX0 64-bit register bitfield layout (offset, width)
_TEX0_FIELDS = [
    ('TBP0', 0,  14), ('TBW',  14,  6), ('PSM',  20,  6), ('TW',   26,  4),
    ('TH',   30,  4), ('TCC',  34,  1), ('TFX',  35,  2), ('CBP',  37, 14),
    ('CPSM', 51,  4), ('CSM',  55,  1), ('CSA',  56,  5), ('CLD',  61,  3),
]


# ─────────────────────────────────────────────────────────────────────────────
# Bitfield Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_bits(val: int, offset: int, count: int) -> int:
    return (val >> offset) & ((1 << count) - 1)


def _insert_bits(target: int, val: int, offset: int, count: int) -> int:
    mask = ((1 << count) - 1) << offset
    return (target & ~mask) | ((val & ((1 << count) - 1)) << offset)


def parse_tex0(reg64: int) -> dict:
    return {name: _extract_bits(reg64, off, cnt) for name, off, cnt in _TEX0_FIELDS}


def encode_tex0(fields: dict) -> int:
    val = 0
    for name, off, cnt in _TEX0_FIELDS:
        val = _insert_bits(val, fields.get(name, 0), off, cnt)
    return val


# ─────────────────────────────────────────────────────────────────────────────
# FJBO Node Tree Helpers
# ─────────────────────────────────────────────────────────────────────────────

def parse_node(data: bytes, pos: int) -> tuple:
    """Recursively parse a binary FJBO node tree starting at *pos*.

    Returns (node_dict, next_pos).  Each node dict has keys:
        type_id, data_size, child_count, children, inline_data
    """
    if pos + 12 > len(data):
        return None, pos
    type_id     = struct.unpack_from('<I', data, pos    )[0]
    data_size   = struct.unpack_from('<I', data, pos + 4)[0]
    child_count = struct.unpack_from('<I', data, pos + 8)[0]
    node = {
        'type_id':     type_id,
        'data_size':   data_size,
        'child_count': child_count,
        'children':    [],
        'inline_data': None,
    }
    pos += 12
    if child_count == 0:
        if pos + data_size > len(data):
            raise EOFError(
                f"EOF reading leaf at 0x{pos:X} (need {data_size} B, "
                f"have {len(data) - pos} B)"
            )
        node['inline_data'] = data[pos: pos + data_size]
        pos += data_size
    else:
        for _ in range(child_count):
            child, pos = parse_node(data, pos)
            if child is not None:
                node['children'].append(child)
    return node, pos


def update_node_sizes(node: dict) -> None:
    """Recursively recompute data_size and child_count after any mutation."""
    if node['child_count'] == 0:
        node['data_size'] = len(node['inline_data']) if node['inline_data'] else 0
    else:
        node['child_count'] = len(node['children'])
        total = 0
        for child in node['children']:
            update_node_sizes(child)
            total += 12 + child['data_size']
        node['data_size'] = total


def serialize_node(node: dict) -> bytes:
    """Recursively serialize a node tree to its binary representation."""
    buf = bytearray()
    buf += struct.pack('<III',
                       node['type_id'],
                       node['data_size'],
                       node['child_count'])
    if node['child_count'] == 0:
        if node['inline_data']:
            buf += node['inline_data']
    else:
        for child in node['children']:
            buf += serialize_node(child)
    return bytes(buf)


# ─────────────────────────────────────────────────────────────────────────────
# Vanilla Texture Dimension Extraction
# ─────────────────────────────────────────────────────────────────────────────

_VALID_POT_DIMS = {16, 32, 64, 128, 256, 512}


def get_vanilla_texture_dimensions(inline_data: bytes) -> tuple:
    """Extract (width, height) from a Vanilla TIM2/GIF texture leaf payload.

    Primary path  : little-endian uint32 at offset 4 (width) and 8 (height).
    Fallback path : little-endian uint16 at offsets 14 and 16.
    Default       : (64, 64) when neither path yields a power-of-two dimension.
    """
    if len(inline_data) < 12:
        return 64, 64

    width  = struct.unpack_from('<I', inline_data, 4)[0]
    height = struct.unpack_from('<I', inline_data, 8)[0]

    if width in _VALID_POT_DIMS and height in _VALID_POT_DIMS:
        return width, height

    # Fallback: 16-bit fields at offsets 14 / 16
    if len(inline_data) >= 18:
        w_16 = struct.unpack_from('<H', inline_data, 14)[0]
        h_16 = struct.unpack_from('<H', inline_data, 16)[0]
        if w_16 in _VALID_POT_DIMS and h_16 in _VALID_POT_DIMS:
            return w_16, h_16

    return 64, 64


# ─────────────────────────────────────────────────────────────────────────────
# Per-Material GS TEX0 Patch
# ─────────────────────────────────────────────────────────────────────────────

def _patch_material_tex0(fro_mat_node: dict,
                         vanilla_width: int,
                         vanilla_height: int) -> dict:
    """Return a deep-copy of *fro_mat_node* with TEX0.TW/TH patched.

    Scans the GIF PACKED-mode register stream inside the material leaf for a
    TEX0_1 (0x06) or TEX0_2 (0x16) register slot and overwrites TW/TH with the
    exponents derived from *vanilla_width* / *vanilla_height*.

    If the node has no inline data, is not a PACKED GIF tag, or no TEX0 register
    is present, the node is returned unchanged (safe no-op).
    """
    result   = copy.deepcopy(fro_mat_node)
    raw      = fro_mat_node.get('inline_data', b'')
    if not raw or len(raw) < 16:
        return result

    # ── Decode GIFtag (first 128-bit / 16-byte word) ──────────────────────
    try:
        lo = struct.unpack_from('<Q', raw, 0)[0]
    except struct.error:
        return result

    nloop = lo & 0x7FFF
    flg   = (lo >> 58) & 0x3
    nreg  = (lo >> 52) & 0xF
    if nreg == 0:
        nreg = 16  # 0 → 16 per GIF spec

    # Only handle PACKED mode (FLG == 0); REGLIST / IMAGE modes differ
    if flg != 0:
        return result

    # ── Scan register slots for TEX0 ──────────────────────────────────────
    # GIFtag occupies 16 bytes; each data slot is 16 bytes (8-byte data + 8-byte addr)
    scan_pos    = 16
    tex0_offset = None
    tex0_val    = None

    for _ in range(nloop * nreg):
        if scan_pos + 16 > len(raw):
            break
        addr = struct.unpack_from('<Q', raw, scan_pos + 8)[0] & 0xFF
        if addr in (GS_REG_TEX0_1, GS_REG_TEX0_2):
            tex0_val    = struct.unpack_from('<Q', raw, scan_pos)[0]
            tex0_offset = scan_pos
            break
        scan_pos += 16

    if tex0_offset is None:
        return result  # no TEX0 in this material — nothing to patch

    # ── Patch TW / TH ─────────────────────────────────────────────────────
    fields = parse_tex0(tex0_val)

    fields['TW'] = max(0, int(math.log2(vanilla_width)))
    fields['TH'] = max(0, int(math.log2(vanilla_height)))

    # For paletted pixel formats the hardware also needs CBP / CSA reset so
    # it re-uploads the CLUT from VRAM base; match the behaviour of the
    # original translate_material_node.
    if fields['PSM'] in PSM_PALETTED:
        fields['CBP'] = 0
        fields['CSA'] = 0
        fields['CLD'] = 1

    new_tex0_val = encode_tex0(fields)

    buf = bytearray(raw)
    struct.pack_into('<Q', buf, tex0_offset, new_tex0_val)

    result['inline_data'] = bytes(buf)
    result['data_size']   = len(buf)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Texture Container Surgical Graft
# ─────────────────────────────────────────────────────────────────────────────

def _graft_texture_container(van_tex_container: dict,
                             fro_tex_container: dict,
                             asset_label: str) -> dict:
    """Return a deep-copy of *fro_tex_container* with:

    - Every Frontiers texture leaf node (0x01001 children) replaced by the
      corresponding Vanilla texture leaf's raw inline_data.
    - Every Frontiers material leaf node (0x01101 children) TEX0 register
      patched to match the Vanilla texture's width / height.

    Counts are clamped to min(van, fro) so that a mismatched texture count
    never produces an out-of-range access.
    """
    result = copy.deepcopy(fro_tex_container)

    # ── Locate 0x01001 (Texture List) in both containers ─────────────────
    van_texlist = next(
        (c for c in van_tex_container['children'] if c['type_id'] == 0x01001), None)
    fro_texlist = next(
        (c for c in result['children']            if c['type_id'] == 0x01001), None)

    if van_texlist is None or fro_texlist is None:
        print(f"      [WARN] {asset_label}: 0x01001 TextureList missing in "
              f"{'Vanilla' if van_texlist is None else 'Frontiers'} container — skipping.")
        return result

    # ── Locate 0x01101 (Material List) in both containers ────────────────
    van_matlist = next(
        (c for c in van_tex_container['children'] if c['type_id'] == 0x01101), None)
    fro_matlist = next(
        (c for c in result['children']            if c['type_id'] == 0x01101), None)

    van_textures  = van_texlist['children']
    fro_textures  = fro_texlist['children']
    van_materials = van_matlist['children'] if van_matlist else []
    fro_materials = fro_matlist['children'] if fro_matlist else []

    n_tex = min(len(van_textures), len(fro_textures))
    if n_tex == 0:
        print(f"      [WARN] {asset_label}: zero texture slots to transplant.")
        return result

    if len(van_textures) != len(fro_textures):
        print(f"      [WARN] {asset_label}: texture count mismatch "
              f"(Vanilla={len(van_textures)}, Frontiers={len(fro_textures)}); "
              f"transplanting first {n_tex}.")

    # ── Per-slot transplant ───────────────────────────────────────────────
    for i in range(n_tex):
        van_tex  = van_textures[i]
        fro_tex  = fro_textures[i]

        # Extract Vanilla dimensions BEFORE overwriting
        v_w, v_h = get_vanilla_texture_dimensions(van_tex['inline_data'])

        # Overwrite Frontiers texture payload with Vanilla's raw bytes
        fro_tex['inline_data'] = van_tex['inline_data']
        fro_tex['data_size']   = len(van_tex['inline_data'])

        # Patch TEX0 in the matching material leaf (if it exists)
        if i < len(fro_materials):
            fro_materials[i] = _patch_material_tex0(fro_materials[i], v_w, v_h)

    # ── Propagate updated sizes up through both list nodes ────────────────
    update_node_sizes(fro_texlist)
    if fro_matlist is not None:
        update_node_sizes(fro_matlist)
    update_node_sizes(result)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def pristine_structural_upgrade(vanilla_bytes: bytes,
                                frontiers_bytes: bytes,
                                asset_label: str) -> bytes:
    """Surgically graft Vanilla textures onto a Frontiers character model.

    Only the Texture Container subtree (type 0x11100 / 0x11110) is modified
    inside the Frontiers model.  All geometry, skeleton, bone-matrix, and
    animation nodes are preserved byte-for-byte so that VU1 rigging indices
    remain valid.

    Parameters
    ----------
    vanilla_bytes : bytes
        Raw binary of the complete Vanilla model entry (beginning at its root
        node header, i.e. the slice extracted from CHAR.ESF via the pointer
        table).
    frontiers_bytes : bytes
        Raw binary of the complete Frontiers model entry (same convention).
    asset_label : str
        Human-readable identifier used in diagnostic messages (e.g. "0x2EF8E480").

    Returns
    -------
    bytes
        Serialised Frontiers model with Vanilla textures transplanted.
    """
    # ── 1. Parse both model trees ─────────────────────────────────────────
    van_root, van_end = parse_node(vanilla_bytes,   0)
    fro_root, fro_end = parse_node(frontiers_bytes, 0)

    if van_root is None:
        raise ValueError(f"{asset_label}: failed to parse Vanilla model bytes.")
    if fro_root is None:
        raise ValueError(f"{asset_label}: failed to parse Frontiers model bytes.")

    if van_end != len(vanilla_bytes):
        print(f"      [WARN] {asset_label}: Vanilla parse consumed {van_end} / "
              f"{len(vanilla_bytes)} bytes.")
    if fro_end != len(frontiers_bytes):
        print(f"      [WARN] {asset_label}: Frontiers parse consumed {fro_end} / "
              f"{len(frontiers_bytes)} bytes.")

    # ── 2. Locate Texture Container in Vanilla model ──────────────────────
    # Vanilla uses 0x11100; Frontiers uses 0x11110 — accept either in both.
    van_tex_container = next(
        (c for c in van_root['children']
         if c['type_id'] in (0x11100, 0x11110)), None)

    if van_tex_container is None:
        raise ValueError(
            f"{asset_label}: Vanilla model has no texture container "
            f"(0x11100 / 0x11110) at root level.")

    # ── 3. Work on a deep-copy of the Frontiers tree ──────────────────────
    # We never mutate the parsed-from-bytes structures directly; all changes
    # happen on this independent copy so the original parse output stays clean.
    result_root = copy.deepcopy(fro_root)

    fro_tex_idx = next(
        (i for i, c in enumerate(result_root['children'])
         if c['type_id'] in (0x11100, 0x11110)), None)

    if fro_tex_idx is None:
        raise ValueError(
            f"{asset_label}: Frontiers model has no texture container "
            f"(0x11100 / 0x11110) at root level.")

    fro_tex_container = result_root['children'][fro_tex_idx]

    # ── 4. Perform surgical texture graft ─────────────────────────────────
    print(f"      -> Transplanting textures from Vanilla 0x{van_tex_container['type_id']:05X} "
          f"→ Frontiers 0x{fro_tex_container['type_id']:05X}  [{asset_label}]")

    grafted_container = _graft_texture_container(
        van_tex_container,
        fro_tex_container,
        asset_label,
    )

    # ── 5. Splice grafted container back; leave all other children intact ─
    result_root['children'][fro_tex_idx] = grafted_container

    # ── 6. Recalculate sizes from the container upward to the root ────────
    update_node_sizes(result_root)

    # ── 7. Serialise ──────────────────────────────────────────────────────
    output = serialize_node(result_root)

    # ── 8. Self-verification: re-parse and check structural completeness ──
    check_root, check_end = parse_node(output, 0)
    if check_end != len(output):
        raise RuntimeError(
            f"{asset_label}: post-serialisation parse mismatch: "
            f"consumed {check_end} / {len(output)} bytes.")

    if check_root['type_id'] != fro_root['type_id']:
        raise RuntimeError(
            f"{asset_label}: root type_id changed after transplant "
            f"(expected 0x{fro_root['type_id']:05X}, "
            f"got 0x{check_root['type_id']:05X}).")

    print(f"      -> Transplant complete: "
          f"Frontiers {len(frontiers_bytes):,} B → output {len(output):,} B")

    return output