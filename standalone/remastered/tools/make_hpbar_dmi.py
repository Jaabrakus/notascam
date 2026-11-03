#!/usr/bin/env python3
"""Write game/Icons/Remastered/HPBar.dmi: 32x32 health bars, states "0".."10" (tenths)."""
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
SIZE, STATES = 32, 11
LEFT, WIDTH, TOP = 4, 24, 1  # bar sits on the top edge of the unit's tile

OUTLINE = (0, 0, 0, 220)
EMPTY = (110, 0, 0, 230)
FULL_COLORS = [(220, 40, 30), (230, 120, 30), (230, 200, 40), (60, 200, 60)]  # low -> high health


def bar_color(state):
    if state <= 2: return FULL_COLORS[0]
    if state <= 4: return FULL_COLORS[1]
    if state <= 6: return FULL_COLORS[2]
    return FULL_COLORS[3]


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


def main():
    width, height = SIZE * STATES, SIZE
    pixels = [[(0, 0, 0, 0)] * width for _ in range(height)]
    for state in range(STATES):
        x0 = state * SIZE
        filled = round(WIDTH * state / 10)
        r, g, b = bar_color(state)
        for y in range(TOP, TOP + 4):
            for x in range(LEFT - 1, LEFT + WIDTH + 1):
                edge = y in (TOP, TOP + 3) or x in (LEFT - 1, LEFT + WIDTH)
                if edge: color = OUTLINE
                elif x - LEFT < filled: color = (r, g, b, 255)
                else: color = EMPTY
                pixels[y][x0 + x] = color
    raw = b''.join(b'\0' + bytes(c for px in row for c in px) for row in pixels)
    description = '# BEGIN DMI\nversion = 4.0\n\twidth = 32\n\theight = 32\n'
    for state in range(STATES):
        description += f'state = "{state}"\n\tdirs = 1\n\tframes = 1\n'
    description += '# END DMI\n'
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    png += chunk(b'zTXt', b'Description\0\0' + zlib.compress(description.encode()))
    png += chunk(b'IDAT', zlib.compress(raw, 9))
    png += chunk(b'IEND', b'')
    out = ROOT / 'game/Icons/Remastered/HPBar.dmi'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(png)
    print(f'Wrote {out} ({STATES} states)')


if __name__ == '__main__':
    main()
