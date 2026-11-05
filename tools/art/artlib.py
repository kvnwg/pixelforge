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


def g(rows: list[str], x0: int = 8, y0: int = 10) -> np.ndarray:
    """Codes from a grid whose first character is at (x0, y0)."""
    return grid.parse(rows, x0, y0, SIZE)


def empty() -> np.ndarray:
    return np.full((SIZE, SIZE), grid.CLEAR, np.int8)


def write_part(slot: str, variant: str, meta: dict[str, Any], sheets: dict[str, Cells],
               frames: dict[str, int] | None = None) -> Path:
    folder = ROOT / "parts" / slot / variant
    folder.mkdir(parents=True, exist_ok=True)
    data = {"slot": slot, "variant": variant, **meta}
    (folder / "part.yaml").write_text(yaml.safe_dump(data, sort_keys=False, width=100))
    ramp = STYLE.materials[meta["material"]].base
    for anim, cells in sheets.items():
        n = 1 if anim == "rigid" else (frames or {}).get(anim, FRAMES.get(anim, 1))
        painted = {key: grid.paint(codes, ramp, OUTLINE) for key, codes in cells.items()}
        write_sheet(folder / f"{anim}.png", painted, DIRS, n, SIZE)
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
