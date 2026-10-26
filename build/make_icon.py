#!/usr/bin/env python3
"""Rebuild app/web/icon.ico from assets/mascot-avatar.png only (16–256). Never use fish-logo."""
from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "mascot-avatar.png"
OUT = ROOT / "app" / "web" / "icon.ico"
SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]


def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_ico(src: Image.Image) -> bytes:
    images: list[bytes] = []
    entries: list[tuple[int, int, int]] = []
    for s in SIZES:
        layer = src.resize((s, s), Image.Resampling.LANCZOS)
        data = png_bytes(layer)
        images.append(data)
        w = 0 if s >= 256 else s
        h = 0 if s >= 256 else s
        entries.append((w, h, len(data)))
        # Guard: mascot has skin-tone center + dark/transparent corner; fish is blue square.
        c = layer.getpixel((s // 2, s // 2))
        corner = layer.getpixel((0, 0))
        if not (c[0] > 200 and c[1] > 180 and c[2] > 180):
            raise SystemExit(f"icon layer {s}: center not mascot skin {c}")
        if corner[3] > 32 and not (corner[0] < 40 and corner[1] < 40 and corner[2] < 40):
            raise SystemExit(f"icon layer {s}: corner looks like fish blue square {corner}")

    header = struct.pack("<HHH", 0, 1, len(SIZES))
    offset = 6 + 16 * len(SIZES)
    directory = b""
    blob = b""
    for (w, h, size), data in zip(entries, images):
        directory += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, size, offset)
        blob += data
        offset += size
    return header + directory + blob


def main() -> int:
    if not SRC.exists():
        print(f"missing {SRC}", file=sys.stderr)
        return 1
    src = Image.open(SRC).convert("RGBA")
    data = build_ico(src)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    print(f"wrote {OUT} ({len(data)} bytes) from {SRC.name}; sizes={SIZES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
