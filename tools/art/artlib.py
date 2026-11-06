"""Helpers for the art scripts in tools/art/.

The scripts draw parts as character grids (pixelforge.grid) and write the PNG sheets, part.yaml
files and anchors. The PNGs they write are the canonical art: once someone edits a PNG by hand in
Aseprite, the PNG wins, so don't rerun the script for that part without porting the edit back.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pixelforge import grid  # noqa: E402
from pixelforge.sheet import write_sheet  # noqa: E402
from pixelforge.style import load_style  # noqa: E402

STYLE = load_style(ROOT / "style" / "style.json")
DIRS = STYLE.drawn_directions  # ("s", "e", "n")
SIZE = 32
OUTLINE = STYLE.outline.color
FRAMES = {name: len(a["frames_ms"]) for name, a in STYLE.raw["animations"].items()
          if isinstance(a, dict)}

Cells = dict[tuple[str, int], np.ndarray]  # (direction, frame) -> codes


def g(rows: list[str], x0: int = 8, y0: int = 10, size: int = SIZE) -> np.ndarray:
    """Codes from a grid whose first character is at (x0, y0)."""
    return grid.parse(rows, x0, y0, size)


def empty(size: int = SIZE) -> np.ndarray:
    return np.full((size, size), grid.CLEAR, np.int8)


def write_part(slot: str, variant: str, meta: dict[str, Any], sheets: dict[str, Cells],
               frames: dict[str, int] | None = None, size: int = SIZE, prune: bool = False) -> Path:
    """Write a part folder. With prune, sheets this call did not write are deleted first, so a
    sheet an older version of the script made (a trail it no longer draws) cannot linger and
    still be composited."""
    folder = ROOT / "parts" / slot / variant
    folder.mkdir(parents=True, exist_ok=True)
    if prune:
        for old in folder.glob("*.png"):
            if old.stem not in sheets:
                old.unlink()
    data = {"slot": slot, "variant": variant, **meta}
    (folder / "part.yaml").write_text(yaml.safe_dump(data, sort_keys=False, width=100))
    ramp = STYLE.materials[meta["material"]].base
    for anim, cells in sheets.items():
        n = 1 if anim == "rigid" else (frames or {}).get(anim, FRAMES.get(anim, 1))
        painted = {key: grid.paint(codes, ramp, OUTLINE) for key, codes in cells.items()}
        write_sheet(folder / f"{anim}.png", painted, DIRS, n, size)
    return folder


def write_anchors(rig: str, anchors: dict[str, Any]) -> Path:
    path = ROOT / "parts" / "body" / rig / "anchors.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(anchors, indent=1)
    path.write_text(text)
    return path


def write_recipe(path: str, data: dict[str, Any]) -> Path:
    out = ROOT / "characters" / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return out


# ---------------------------------------------------------------------------------------------
# Pose helpers. Animated parts follow the base body's pose offsets exactly (ANIMATION_SPEC.md).

IDLE_UPPER_DY = [0, 1, 1, 0]  # ANIMATION_SPEC.md section 3: upper body offsets per idle frame


def split_shift(codes: np.ndarray, hip: int, dx: int, dy: int) -> np.ndarray:
    """Move the rows above `hip` (the upper body) by (dx, dy); rows from `hip` down (the legs)
    stay. Where they overlap, the upper body is in front (the belt covers the top leg row)."""
    upper = codes.copy()
    upper[hip:] = grid.CLEAR
    legs = codes.copy()
    legs[:hip] = grid.CLEAR
    return grid.overlay(legs, grid.translate(upper, dx, dy))


def shift_anchors(points: dict, dx: int, dy: int, *, keep=("foot_near", "foot_far", "planted", "hip")
                  ) -> dict:
    out = {}
    for name, value in points.items():
        out[name] = value if name in keep else [value[0] + dx, value[1] + dy]
    return out


# ============================================================================== swing trails
def crescent(arc: list[tuple[int, int]], widest: int = 3) -> list[tuple[int, int, int]]:
    """A swing trail from the path a weapon's tip traced (tail first, the weapon last): the
    path itself is the bright leading edge; behind it the trail thickens toward the weapon, up
    to `widest` px, on the inside of the curve. Shades: 2 = the white core, 1 = mid, 0 = the
    rim; the tail fades through mid to rim (the compositor paints them in fx_ramps.swing)."""
    n = len(arc)
    (x0, y0), (x1, y1) = arc[0], arc[-1]
    mid = ((x0 + x1) / 2, (y0 + y1) / 2)  # the chord's middle: the inside of the curve
    out: dict[tuple[int, int], int] = {}
    for i, (x, y) in enumerate(arc):
        t = i / max(n - 1, 1)
        ax, ay = arc[max(i - 1, 0)]
        bx, by = arc[min(i + 1, n - 1)]
        tx, ty = bx - ax, by - ay
        nx, ny = -ty, tx
        if nx * (mid[0] - x) + ny * (mid[1] - y) < 0:
            nx, ny = -nx, -ny
        step = (int(np.sign(nx)), 0) if abs(nx) >= abs(ny) else (0, int(np.sign(ny)))
        width = 1 if t < 0.3 else 2 if t < 0.65 else widest
        edge = 2 if t >= 0.3 else 1 if t >= 0.12 else 0
        out[(x, y)] = max(out.get((x, y), -1), edge)
        for k in range(1, width):
            q = (x + step[0] * k, y + step[1] * k)
            if q not in out:
                out[q] = 1 if k == 1 else 0
    return [(x, y, v) for (x, y), v in out.items()]


def arc_path(p0: tuple[int, int], p1: tuple[int, int], pivot: tuple[float, float]) -> list[tuple[int, int]]:
    """Integer points along the arc a swung tip travels from p0 to p1 around a pivot (the
    shoulder or the hand), the short way round, radius blended between the ends; 4-connected
    (a diagonal step gets a corner pixel), tail first."""
    import math
    a0 = math.atan2(p0[1] - pivot[1], p0[0] - pivot[0])
    a1 = math.atan2(p1[1] - pivot[1], p1[0] - pivot[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    r0 = math.hypot(p0[0] - pivot[0], p0[1] - pivot[1])
    r1 = math.hypot(p1[0] - pivot[0], p1[1] - pivot[1])
    pts: list[tuple[int, int]] = []
    for k in range(240):
        f = k / 239
        r, ang = r0 + (r1 - r0) * f, a0 + da * f
        q = (int(round(pivot[0] + r * math.cos(ang))), int(round(pivot[1] + r * math.sin(ang))))
        if pts and q == pts[-1]:
            continue
        if pts and abs(q[0] - pts[-1][0]) == 1 and abs(q[1] - pts[-1][1]) == 1:
            pts.append((q[0], pts[-1][1]))
        pts.append(q)
    return pts
