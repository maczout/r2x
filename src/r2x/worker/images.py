"""24-bit BMP files (as the helper writes them) to PNG, with the standard library only."""

from __future__ import annotations

import struct
import zlib


def bmp_to_png(bmp: bytes) -> bytes:
    """A bottom-up or top-down 24-bit uncompressed BMP as an RGB PNG."""
    if bmp[:2] != b"BM":
        raise ValueError("not a BMP file")
    offset = struct.unpack_from("<I", bmp, 10)[0]
    width, height, _, bits, compression = struct.unpack_from("<iiHHI", bmp, 18)
    if bits != 24 or compression != 0:
        raise ValueError(f"only uncompressed 24-bit BMP is supported, not {bits}-bit/{compression}")
    stride = (width * 3 + 3) & ~3
    rows = range(height - 1, -1, -1) if height > 0 else range(-height)
    raw = bytearray()
    for r in rows:
        line = bmp[offset + r * stride:offset + r * stride + width * 3]
        raw.append(0)                        # PNG filter: none
        rgb = bytearray(line)
        rgb[0::3], rgb[2::3] = line[2::3], line[0::3]       # BGR -> RGB
        raw += rgb
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    header = struct.pack(">IIBBBBB", width, abs(height), 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
