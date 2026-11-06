"""Design pass 2 (2026-11-06): regenerate the material presets as vivid ramps.

Every preset except the anchor's own is computed here from a spec, so the palette can be read and
tuned in one place: (hue, chroma, first lightness, lightness step, hue step per lighter shade)
and an optional chroma profile per shade (lower at the extremes, so a near-white glint stays a
glint and the darkest shade stays clean). Colors are made in OKLCH and brought into sRGB by
lowering chroma only (`color.oklch_to_rgb`), so the value steps survive.

The anchor's presets ("... (anchor)") are kept exactly: she is the reference for shapes, outline
and shading, and the muted end of the palette. Also kept: presets listed in KEEP.

Run: .venv/bin/python tools/art/palette_presets.py   (rewrites style/style.json, then run
`pf palette --check`)
"""

from __future__ import annotations

import json
from pathlib import Path

from pixelforge.color import hex_to_oklch, oklch_to_rgb, to_hex

ROOT = Path(__file__).resolve().parents[2]
STYLE = ROOT / "style" / "style.json"

KEEP: set[tuple[str, str]] = set()  # (material, preset) kept as they are, besides the anchor's

# Chroma multipliers per shade count: the ends of a ramp carry a little less chroma.
PROFILE = {1: [1.0], 2: [0.95, 1.0], 3: [0.92, 1.0, 0.9], 4: [0.9, 1.0, 0.98, 0.78]}

# material -> preset -> (hue, chroma, first L, L step, hue step) [, chroma profile override]
SPECS: dict[str, dict[str, tuple]] = {
    "skin": {
        "fair": (42, 0.075, 0.70, 0.10, 6),
        "tan": (46, 0.09, 0.57, 0.11, 6),
        "deep": (40, 0.08, 0.43, 0.105, 6),
        "ebony": (36, 0.07, 0.38, 0.10, 6),
        "green (orc)": (128, 0.13, 0.50, 0.115, 5),
        "ogre": (60, 0.07, 0.52, 0.11, 6),
        "frost": (226, 0.085, 0.62, 0.11, 6),
        "dusk": (296, 0.11, 0.48, 0.11, 6),
        "ash": (252, 0.02, 0.56, 0.11, 4),
        "ember": (26, 0.15, 0.50, 0.11, 6),
        "porcelain": (52, 0.035, 0.76, 0.085, 5),
    },
    "hair": {
        "black": (280, 0.045, 0.31, 0.10, 6),
        "raven": (262, 0.055, 0.31, 0.095, 5),
        "blonde": (78, 0.13, 0.70, 0.105, 6),
        "golden": (70, 0.16, 0.66, 0.11, 7),
        "auburn": (34, 0.13, 0.45, 0.11, 6),
        "fire": (30, 0.19, 0.52, 0.11, 8),
        "copper": (44, 0.16, 0.55, 0.11, 7),
        "silver": (280, 0.02, 0.62, 0.13, 4),
        "platinum": (95, 0.03, 0.74, 0.095, 5),
        "mint": (168, 0.10, 0.62, 0.11, 5),
        "bubblegum": (354, 0.15, 0.62, 0.11, 7),
        "lavender": (296, 0.13, 0.58, 0.11, 6),
        "sky": (234, 0.12, 0.60, 0.11, 5),
        "leaf": (134, 0.15, 0.55, 0.11, 5),
        "chestnut": (40, 0.09, 0.40, 0.11, 6),
        "snow": (240, 0.015, 0.78, 0.08, 5),
    },
    "cloth": {
        "crimson": (17, 0.16, 0.40, 0.11, 6),
        "forest": (148, 0.11, 0.40, 0.11, 6),
        "teal": (200, 0.11, 0.50, 0.12, 6),
        "plum": (330, 0.11, 0.38, 0.11, 6),
        "mustard": (80, 0.12, 0.60, 0.11, 6),
        "cream": (85, 0.04, 0.80, 0.10, 6),
        "royal": (262, 0.18, 0.43, 0.12, 6),
        "scarlet": (25, 0.19, 0.50, 0.12, 7),
        "emerald": (150, 0.16, 0.50, 0.12, 6),
        "violet": (300, 0.17, 0.44, 0.12, 6),
        "sunflower": (84, 0.16, 0.75, 0.11, 7),
        "azure": (235, 0.14, 0.58, 0.12, 6),
        "rose": (355, 0.15, 0.62, 0.12, 7),
        "tangerine": (45, 0.17, 0.64, 0.12, 8),
        "ink": (275, 0.04, 0.32, 0.09, 5),
        "snow": (95, 0.015, 0.84, 0.10, 5),
        "jade": (170, 0.13, 0.56, 0.12, 6),
        "wine": (8, 0.14, 0.38, 0.10, 6),
        "magenta": (335, 0.19, 0.52, 0.12, 7),
        "lime": (124, 0.18, 0.70, 0.12, 6),
        "turquoise": (190, 0.13, 0.62, 0.12, 5),
        "ice": (220, 0.08, 0.74, 0.12, 5),
        "flame": (38, 0.19, 0.60, 0.12, 9),
        "midnight": (270, 0.11, 0.34, 0.10, 5),
    },
    "leather": {
        "dark": (32, 0.045, 0.33, 0.095, 7),
        "tan": (55, 0.085, 0.52, 0.11, 7),
        "black": (292, 0.025, 0.31, 0.09, 5),
        "red": (25, 0.14, 0.42, 0.105, 6),
        "white": (80, 0.02, 0.72, 0.105, 5),
        "green": (140, 0.10, 0.40, 0.10, 5),
        "chestnut": (40, 0.085, 0.40, 0.11, 7),
        "slate": (265, 0.05, 0.31, 0.10, 5),
    },
    "accent": {
        "bright gold": (76, 0.155, 0.74, 0.13, 9),
        "silver": (262, 0.015, 0.70, 0.16, 3),
        "red": (25, 0.18, 0.54, 0.12, 7),
        "emerald": (150, 0.16, 0.58, 0.12, 6),
        "sapphire": (258, 0.17, 0.50, 0.12, 6),
        "amethyst": (303, 0.17, 0.52, 0.12, 6),
        "ruby": (18, 0.19, 0.48, 0.12, 6),
        "pearl": (95, 0.02, 0.82, 0.11, 5),
        "onyx": (289, 0.03, 0.32, 0.11, 4),
        "orange": (45, 0.18, 0.64, 0.12, 8),
    },
    "eyes": {
        "dark": (300, 0.035, 0.33, 0.0, 0),
        "brown": (40, 0.07, 0.42, 0.0, 0),
        "green": (150, 0.13, 0.52, 0.0, 0),
        "blue": (252, 0.15, 0.52, 0.0, 0),
        "violet": (304, 0.16, 0.50, 0.0, 0),
        "amber": (68, 0.15, 0.68, 0.0, 0),
        "teal": (195, 0.11, 0.56, 0.0, 0),
        "glow red": (25, 0.215, 0.67, 0.0, 0),
        "glow yellow": (95, 0.17, 0.89, 0.0, 0),
        "glow ghost": (200, 0.10, 0.87, 0.0, 0),
        "glow leaf": (128, 0.19, 0.84, 0.0, 0),
    },
    "metal": {
        "steel": (258, 0.022, 0.44, 0.14, 4, [0.9, 1.0, 1.0, 0.7]),
        "iron": (255, 0.012, 0.38, 0.135, 3),
        "bronze": (58, 0.11, 0.48, 0.13, 6),
        "gold": (70, 0.14, 0.54, 0.125, 7),
        "obsidian": (285, 0.03, 0.31, 0.11, 7),
        "royal gold": (74, 0.165, 0.58, 0.115, 7),
        "blued": (250, 0.11, 0.42, 0.135, 4),
        "rose gold": (36, 0.11, 0.52, 0.125, 6),
        "verdigris": (172, 0.09, 0.46, 0.13, 5),
        "crimson": (20, 0.16, 0.38, 0.115, 5),
    },
    "fur": {
        "gray": (60, 0.02, 0.42, 0.13, 4),
        "brown": (45, 0.085, 0.40, 0.12, 5),
        "frost": (236, 0.05, 0.56, 0.12, 5),
    },
    "scales": {
        "green": (140, 0.14, 0.42, 0.12, 5),
        "red": (22, 0.16, 0.42, 0.12, 6),
        "ember": (25, 0.17, 0.40, 0.12, 6),
        "obsidian": (285, 0.035, 0.31, 0.105, 5),
    },
    "bone": {
        "ivory": (80, 0.04, 0.60, 0.11, 5),
        "antler": (85, 0.03, 0.62, 0.105, 7),
    },
    "chitin": {"dusk": (300, 0.09, 0.34, 0.11, 7)},
    "slime": {"mint": (152, 0.15, 0.52, 0.12, 6)},
    "slime_highlight": {"mint": (165, 0.06, 0.93, 0.0, 0)},
    "hide": {
        "goblin": (120, 0.15, 0.50, 0.115, 5),
        "bog": (126, 0.11, 0.40, 0.11, 5),
    },
    "membrane": {
        "dusk": (318, 0.10, 0.40, 0.11, 6),
        "ember": (38, 0.17, 0.54, 0.12, 7),
        "ash": (288, 0.03, 0.44, 0.11, 5),
    },
    "horn": {
        "pale": (72, 0.045, 0.62, 0.125, 6),
        "gilded": (70, 0.13, 0.62, 0.125, 6),
        "ebony": (300, 0.035, 0.32, 0.11, 7),
    },
    "stone": {
        "granite": (95, 0.02, 0.44, 0.12, 4),
        "basalt": (262, 0.02, 0.35, 0.12, 3),
        "sandstone": (60, 0.07, 0.48, 0.12, 5),
        "frost": (226, 0.05, 0.46, 0.12, 5),
        "charcoal": (255, 0.02, 0.31, 0.10, 4),
    },
    "leaf": {  # greens warm toward yellow as they lighten: the hue falls (an accepted warning)
        "spring": (150, 0.16, 0.42, 0.12, -7, [0.8, 1.0, 1.0, 0.95]),
        "autumn": (30, 0.17, 0.45, 0.12, 8),
    },
    "fruit": {
        "berry": (40, 0.17, 0.62, 0.12, 8),
        "blood": (20, 0.18, 0.48, 0.12, 7),
    },
}


def ramp(n: int, spec: tuple) -> list[str]:
    hue, chroma, L0, dL, dh = spec[:5]
    profile = spec[5] if len(spec) > 5 else PROFILE[n]
    return [to_hex(oklch_to_rgb(L0 + i * dL, chroma * profile[i], hue + i * dh)) for i in range(n)]


def main() -> None:
    style = json.loads(STYLE.read_text())
    mats = style["materials"]
    changed = 0
    for material, presets in SPECS.items():
        n = mats[material]["shades"]
        for name, spec in presets.items():
            if "(anchor)" in name or (material, name) in KEEP:
                continue
            new = ramp(n, spec)
            if mats[material]["presets"].get(name) != new:
                changed += 1
            mats[material]["presets"][name] = new
    STYLE.write_text(json.dumps(style, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {changed} presets")
    for material, presets in SPECS.items():
        for name in presets:
            if name in mats[material]["presets"]:
                o = [hex_to_oklch(c) for c in mats[material]["presets"][name]]
                print(f"  {material}/{name}: " + " ".join(mats[material]["presets"][name]) +
                      "  C " + " ".join(f"{x.C:.2f}" for x in o) + "  L " + " ".join(f"{x.L:.2f}" for x in o))


if __name__ == "__main__":
    main()
