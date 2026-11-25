#!/usr/bin/env python3
"""news-image-20261124 entrypoint (Python standard library only).

The front page (``entry.png``, 1024x1024, Tuesday 24 November 2026) was
rendered at build time and is stored beside this file in the repository.
This program does no drawing and needs no third-party package: it checks
the stored PNG is whole and within the competition limits, copies it
byte-for-byte to ``/output/entry.png`` (or ``$MAKEFUN_OUTPUT_DIR``), and
then reads the copy back and confirms it is identical.

v2 (25 Nov 2026): the "ALSO ON TUESDAY 24 NOVEMBER" strip was realigned
— text lines evened to a uniform pitch and every icon re-centred on its
own text line (see EVIDENCE/fix-also-on-alignment.md). No story, headline
or other section changed.

v3 (25 Nov 2026): round-2 owner revision of the ALSO ON strip — each of
the 7 rows now has its OWN icon (the shared rows-4/5 composite is gone;
row 4 is exam paper + ban + a correct South Korean Taegeukgi, row 5 is a
plane + a correct Bangladesh flag), the "-" bullets became numbers 1-7,
and the footer now reads "ALL REPORTS AS OF 22:00 GMT" (see
EVIDENCE/fix-also-on-round2.md). The palette gained a true green for the
Bangladesh flag; no story, headline or other section changed.

Exit codes: 0 ok, 2 the stored image is bad, 3 the copy does not match.
"""

import hashlib
import os
import struct
import sys
import zlib

MAX_BYTES = 1048576
SIDE = 1024
SIGNATURE = b"\x89PNG\r\n\x1a\n"
IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"


def fail(message, code):
    print("error: " + message, file=sys.stderr)
    return code


def png_info(blob):
    """Return (width, height, bit depth, color type) from the IHDR chunk."""
    width, height = struct.unpack(">II", blob[16:24])
    return width, height, blob[24], blob[25]


def find_palette(blob):
    """Return the PLTE chunk payload, or None when there is none."""
    offset = 8
    while offset + 8 <= len(blob):
        size, kind = struct.unpack(">I4s", blob[offset:offset + 8])
        stop = offset + 12 + size
        if stop > len(blob):
            return None
        if kind == b"PLTE":
            return blob[offset + 8:offset + 8 + size]
        if kind == b"IDAT":
            return None
        offset = stop
    return None


def check_png(blob):
    """Return None when blob is a whole 1024x1024 PNG within limits."""
    if len(blob) > MAX_BYTES:
        return "entry.png is %d bytes, over the %d limit" % (len(blob), MAX_BYTES)
    if len(blob) < 8 or blob[:8] != SIGNATURE:
        return "entry.png does not start with the PNG signature"
    if len(blob) < 33 or blob[12:16] != b"IHDR":
        return "entry.png has no IHDR chunk"
    width, height, bit_depth, color_type = png_info(blob)
    if width != SIDE or height != SIDE:
        return "entry.png is %dx%d, expected 1024x1024" % (width, height)
    allowed_depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8),
                      4: (8, 16), 6: (8, 16)}
    if bit_depth not in allowed_depths.get(color_type, ()):
        return ("entry.png has color type %d with bit depth %d"
                % (color_type, bit_depth))
    if color_type == 3:
        # A palette image needs a PLTE chunk with one RGB triple per index.
        palette = find_palette(blob)
        if palette is None:
            return "entry.png has no PLTE chunk"
        if len(palette) != 3 * (1 << bit_depth):
            return ("entry.png PLTE chunk is %d bytes, expected %d"
                    % (len(palette), 3 * (1 << bit_depth)))
    if blob[-12:] != IEND:
        return "entry.png has no IEND trailer"
    return walk_chunks(blob)


def walk_chunks(blob):
    """Verify every chunk length and CRC, and require IDAT and IEND."""
    offset = 8
    saw_data = False
    saw_end = False
    while offset + 8 <= len(blob):
        size, kind = struct.unpack(">I4s", blob[offset:offset + 8])
        stop = offset + 12 + size
        if stop > len(blob):
            return "entry.png has a truncated %s chunk" % kind.decode("latin1")
        want = struct.unpack(">I", blob[stop - 4:stop])[0]
        got = zlib.crc32(blob[offset + 4:stop - 4]) & 0xFFFFFFFF
        if want != got:
            return "entry.png has a bad CRC in the %s chunk" % kind.decode("latin1")
        if kind == b"IDAT":
            saw_data = True
        if kind == b"IEND":
            saw_end = True
            if stop != len(blob):
                return "entry.png has bytes after the IEND chunk"
            break
        offset = stop
    if not saw_data:
        return "entry.png has no IDAT chunk"
    if not saw_end:
        return "entry.png has no IEND chunk"
    return None


def run(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    origin = os.path.join(here, "entry.png")
    try:
        with open(origin, "rb") as handle:
            blob = handle.read()
    except OSError as exc:
        return fail("cannot read entry.png: %s" % exc, 2)
    problem = check_png(blob)
    if problem:
        return fail(problem, 2)
    if len(argv) > 1 and argv[1] == "--check":
        # Self-test mode: validate the stored image without writing output.
        width, height, bit_depth, color_type = png_info(blob)
        palette = find_palette(blob)
        print("entry.png ok (%d bytes, %dx%d, color type %d, bit depth %d,"
              " palette %d entries, sha256 %s)"
              % (len(blob), width, height, color_type, bit_depth,
                 len(palette) // 3 if palette is not None else 0,
                 hashlib.sha256(blob).hexdigest()))
        return 0
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    target = os.path.join(out_dir, "entry.png")
    os.makedirs(out_dir, exist_ok=True)
    with open(target, "wb") as handle:
        handle.write(blob)
    with open(target, "rb") as handle:
        written = handle.read()
    if written != blob:
        return fail("written entry.png differs from the stored bytes", 3)
    print("wrote %s (%d bytes, sha256 %s)"
          % (target, len(blob), hashlib.sha256(blob).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv))
