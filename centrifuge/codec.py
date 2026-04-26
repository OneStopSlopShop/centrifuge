"""
SerumPreset binary codec — pack/unpack .SerumPreset files.

File layout:
  b"XferJson\x00"
  uint32_le(json_len) uint32_le(0)
  <json_bytes>           ← metadata
  uint32_le(cbor_len) uint32_le(2)
  <zstd_frame>           ← zstd-compressed CBOR payload
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import cbor2
import zstandard as zstd

MAGIC = b"XferJson\x00"
_ZSTD_LEVEL = 3


def unpack(path: Path) -> dict:
    """Read a .SerumPreset and return {"metadata": {...}, "data": {...}}."""
    buf = Path(path).read_bytes()
    off = len(MAGIC)

    json_len, _ = struct.unpack_from("<II", buf, off)
    off += 8
    metadata = json.loads(buf[off : off + json_len])
    off += json_len

    cbor_len, _ = struct.unpack_from("<II", buf, off)
    off += 8
    cbor_bytes = zstd.ZstdDecompressor().decompress(buf[off:])
    if len(cbor_bytes) != cbor_len:
        raise ValueError(f"CBOR length mismatch: expected {cbor_len}, got {len(cbor_bytes)}")

    return {"metadata": metadata, "data": cbor2.loads(cbor_bytes)}


def pack(preset: dict, path: Path) -> None:
    """Write a {"metadata": {...}, "data": {...}} dict to a .SerumPreset file."""
    path = Path(path)
    metadata = dict(preset["metadata"])

    cbor_bytes = cbor2.dumps(preset["data"])
    metadata["hash"] = hashlib.md5(cbor_bytes).hexdigest()

    meta_bytes = json.dumps(metadata, separators=(",", ":")).encode()
    zstd_bytes = zstd.ZstdCompressor(level=_ZSTD_LEVEL).compress(cbor_bytes)

    out = bytearray()
    out += MAGIC
    out += struct.pack("<II", len(meta_bytes), 0)
    out += meta_bytes
    out += struct.pack("<II", len(cbor_bytes), 2)
    out += zstd_bytes
    path.write_bytes(bytes(out))
