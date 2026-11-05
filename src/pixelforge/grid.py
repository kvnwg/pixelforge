"""Character grids: art written as rows of characters, one character per pixel.

    '.'        transparent
    'O'        the outline color (a hand-placed detail; parts never draw their outer outline)
    '0' - '9'  a shade index into the part's material ramp, 0 = darkest

Grids are how art is drawn in code (CLAUDE.md drawing tip): they are easy to reason about, diff
and fix one pixel at a time. `dump` turns a cell back into a grid for reviewing it.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .color import parse_hex, to_hex

CLEAR, INK = -1, -2


def parse(rows: Sequence[str], x0: int = 0, y0: int = 0, size: int = 32) -> np.ndarray:
    """Codes for a size x size cell; the grid's first character lands on (x0, y0)."""
    codes = np.full((size, size), CLEAR, np.int8)
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch in ". ":
                continue
            x, y = x0 + dx, y0 + dy
            if not (0 <= x < size and 0 <= y < size):
                raise ValueError(f"grid pixel ({x}, {y}) is outside the {size} px cell")
            if ch == "O":
                codes[y, x] = INK
            elif ch.isdigit():
                codes[y, x] = int(ch)
            else:
                raise ValueError(f"unknown grid character {ch!r} at ({x}, {y})")
    return codes


def paint(codes: np.ndarray, ramp: Sequence[str], outline: str) -> np.ndarray:
    """RGBA cell from codes and a ramp (dark to light)."""
    out = np.zeros((*codes.shape, 4), np.uint8)
    out[codes == INK] = (*parse_hex(outline), 255)
    for i, color in enumerate(ramp):
        out[codes == i] = (*parse_hex(color), 255)
    if (codes >= len(ramp)).any():
        raise ValueError(f"shade index {int(codes.max())} but the ramp has {len(ramp)} shades")
    return out


def codes_of(cell: np.ndarray, ramp: Sequence[str], outline: str) -> np.ndarray:
    """Inverse of `paint`. Raises ValueError for colors outside the ramp."""
    codes = np.full(cell.shape[:2], CLEAR, np.int8)
    lookup = {parse_hex(c): i for i, c in enumerate(ramp)}
    lookup[parse_hex(outline)] = INK
    for y, x in np.argwhere(cell[..., 3] > 0):
        rgb = tuple(int(v) for v in cell[y, x, :3])
        if rgb not in lookup:
            raise ValueError(f"({x}, {y}) has {to_hex(rgb)}, not in the ramp")
        codes[y, x] = lookup[rgb]
    return codes


def dump(codes: np.ndarray, *, crop: bool = True, ruler: bool = True) -> str:
    """Codes as a grid of characters, cropped to the art, with x and y rulers."""
    ys, xs = np.nonzero(codes != CLEAR)
    if crop and ys.size:
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    else:
        y0, y1, x0, x1 = 0, codes.shape[0] - 1, 0, codes.shape[1] - 1
    lines = []
    if ruler:
        lines.append("     " + "".join(str(x % 10) for x in range(x0, x1 + 1)) + f"   (x {x0}..{x1})")
    for y in range(y0, y1 + 1):
        row = "".join("." if c == CLEAR else "O" if c == INK else str(int(c))
                      for c in codes[y, x0:x1 + 1])
        lines.append(f"y{y:<3} {row}" if ruler else row)
    return "\n".join(lines)


def overlay(*layers: np.ndarray) -> np.ndarray:
    """Stack code layers; later layers win where they are not clear."""
    out = np.full(layers[0].shape, CLEAR, np.int8)
    for layer in layers:
        out = np.where(layer != CLEAR, layer, out)
    return out


def translate(codes: np.ndarray, dx: int, dy: int) -> np.ndarray:
    out = np.full(codes.shape, CLEAR, np.int8)
    h, w = codes.shape
    ys0, ys1 = max(0, -dy), min(h, h - dy)
    xs0, xs1 = max(0, -dx), min(w, w - dx)
    out[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] = codes[ys0:ys1, xs0:xs1]
    if (codes != CLEAR).sum() != (out != CLEAR).sum():
        raise ValueError(f"translating by ({dx}, {dy}) pushes pixels off the cell")
    return out


def mirror_codes(codes: np.ndarray, axis: int) -> np.ndarray:
    out = np.full(codes.shape, CLEAR, np.int8)
    w = codes.shape[1]
    for x in range(w):
        x2 = 2 * axis - x
        if 0 <= x2 < w:
            out[:, x2] = codes[:, x]
    return out
