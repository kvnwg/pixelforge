"""pf template: an empty sheet of the right size and a guide with the base body ghosted in."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .anim import load_anims
from .build import build
from .recipe import parse_recipe
from .rig import load_rig
from .sheet import save_rgba
from .style import Style

GHOST_ALPHA = 90  # the guide is a drawing aid, not art: translucency is fine here


def write_template(style: Style, slot: str, variant: str, anim: str, rig_name: str = "humanoid"
                   ) -> tuple[Path, Path]:
    rig = load_rig(style.root, style, rig_name)
    size = rig.size.canvas
    anims = load_anims(style)
    source = "idle" if anim == "rigid" else anim
    rows = anims[source].drawn_directions(style) if source in anims else style.drawn_directions
    frames = 1 if anim == "rigid" else anims[anim].frames
    folder = style.root / "parts" / slot / variant
    folder.mkdir(parents=True, exist_ok=True)
    sheet_path = folder / f"{anim}.png"
    if not sheet_path.exists():
        save_rgba(sheet_path, np.zeros((len(rows) * size, frames * size, 4), np.uint8))
    bare = parse_recipe({"name": "guide", "rig": rig_name, "parts": {}, "anims": [source]}, style)
    base = build(style.root, bare, style=style, validate=False)
    girl = None
    if rig_name == "humanoid" and (style.root / "characters" / "anchor_girl.yaml").is_file():
        girl = build(style.root, "anchor_girl", style=style, validate=False)
    guide = np.zeros((len(rows) * size, frames * size, 4), np.uint8)
    for r, d in enumerate(rows):
        for f in range(frames):
            cell = guide[r * size:(r + 1) * size, f * size:(f + 1) * size]
            for b, alpha in ((girl, GHOST_ALPHA // 2), (base, GHOST_ALPHA)):
                if b is None or (source, d) not in b.frames or f >= len(b.frames[(source, d)]):
                    continue
                art = b.frames[(source, d)][f].sprite
                mask = art[..., 3] == 255
                cell[mask, :3] = art[mask, :3]
                cell[mask, 3] = np.maximum(cell[mask, 3], alpha)
    guide_path = folder / f"{anim}_guide.png"
    save_rgba(guide_path, guide)
    return sheet_path, guide_path
