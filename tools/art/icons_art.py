"""Item icons for the gear sets (ROADMAP.md, "Gear sets and item icons"): one 16 x 16 inventory
icon per piece a set wears (headwear, torso, legs, hands, feet, cape, belt) plus two pieces of
jewelry no sprite shows (an amulet, a ring). Original art in pixelforge's style: lit from the upper
right, shades in clusters, the outline generated around the silhouette by `pixelforge.icons`.

Each icon is one character grid with a legend: digits are the piece's own shades (its base layer,
one material), letters are overlay layers (a plume, a cross, a buckle, a gem), each its own
material and slot so it takes the set's colors exactly like the sprite's part does. An overlay
named after a part variant only shows when the set wears that variant (a plume only on a plumed
helm). 'O' is a hand-placed outline pixel (an eye slit, the inside of a hood).

Writes icons/<slot>/<variant>/<layer>.png (16 x 16, in the material's base ramp) and icon.yaml.
Run after parts_vivid.py: .venv/bin/python tools/art/icons_art.py
"""

from __future__ import annotations

import numpy as np
import yaml

from artlib import ROOT, STYLE
from pixelforge import grid
from pixelforge.sheet import save_rgba as write_rgba

SIZE = 16

# Each icon: (layers, rows). layers: name -> (slot, material, legend chars mapped to shades,
# requires) where requires is None (always shown), or (slot, variant) the set must wear.
# The base layer is named "base" and uses the digits.
ICONS: dict[tuple[str, str], tuple[dict, list[str]]] = {}


def icon(slot: str, variant: str, material: str, rows: list[str], **overlays) -> None:
    """overlays: name=(slot, material, "chars dark to light", requires-or-None[, under]) where
    `under` is the base shade drawn beneath the overlay, so a set without it shows no hole."""
    assert len(rows) == SIZE and all(len(r) == SIZE for r in rows), (slot, variant, [len(r) for r in rows])
    layers = {"base": (slot, material, "0123", None, None),
              **{k: (*v, None) if len(v) == 4 else v for k, v in overlays.items()}}
    ICONS[(slot, variant)] = (layers, rows)


# ------------------------------------------------------------------------------------- headwear
icon("headwear", "sallet", "metal", [
    "................",
    "................",
    "................",
    "......2333......",
    "....122333332...",
    "...11222333332..",
    "...112222333332.",
    "..0112222223332.",
    "..0112OOOOOOO32.",
    "..0112222223332.",
    ".0011122222222..",
    ".000011111111...",
    "..00000.........",
    "................",
    "................",
    "................",
])
icon("headwear", "leather_cap", "leather", [
    "................",
    "................",
    "................",
    "................",
    "......2222......",
    "....12222222....",
    "...1122222222...",
    "...11122222221..",
    "..0111122222211.",
    "..0111111222211.",
    "..0001111111111.",
    "..000000000000..",
    "................",
    "................",
    "................",
    "................",
])
icon("headwear", "great_helm", "metal", [
    "................",
    "........PP......",
    ".......pPPP.....",
    ".......pP..PP...",
    ".......pP...P...",
    ".....12233332...",
    "....1122333332..",
    "...011223X3332..",
    "...01122XXX332..",
    "...011223X3332..",
    "...0OOOOOOOOO2..",
    "...011223X2222..",
    "...011222x2221..",
    "...00111222211..",
    "....001111110...",
    "................",
], plume_tall=("headwear_trim", "cloth", "pP", ("headwear_trim", "plume_tall")),
   cross_helm=("headwear_emblem", "accent", "xX", ("headwear_emblem", "cross_helm"), 2))
icon("headwear", "hood", "cloth", [
    "................",
    "................",
    "......1111......",
    "....11111111....",
    "...1111111111...",
    "...1110000111...",
    "..1110OOOO0111..",
    "..110OOOOOO011..",
    "..110OOOOOO011..",
    "..1110OOOO0111..",
    "..01110000111O..",
    "..0011111111100.",
    "...0011111110...",
    "....00000000....",
    "................",
    "................",
])
icon("headwear", "pointed_hood", "cloth", [
    "................",
    "..........111...",
    ".........1100...",
    "........1110....",
    ".......11110....",
    ".....1111111....",
    "....111111111...",
    "...1110000111...",
    "..110OOOOO0111..",
    "..110OOOOOO011..",
    "..1110OOOO0111..",
    "..0111000011110.",
    "..0011111111100.",
    "...0000000000...",
    "................",
    "................",
])
icon("headwear", "ranger_hat", "leather", [
    "................",
    "..........ff....",
    ".........fF.....",
    "........fF......",
    "......2222......",
    ".....122222.....",
    "....11222222....",
    "....00000000....",
    ".11222222222221.",
    ".01111111111110.",
    ".00000000000000.",
    "................",
    "................",
    "................",
    "................",
    "................",
], feather=("headwear_trim", "accent", "fF", ("headwear_trim", "feather")))
icon("headwear", "witch_hat", "cloth", [
    "................",
    "..........11....",
    ".........11.....",
    "........111.....",
    "........111.....",
    ".......1111.....",
    "......01111.....",
    "......011111....",
    ".....0011111....",
    ".....0111111....",
    "....00bbBBBB0...",
    "....0011111110..",
    ".11111111111111.",
    ".01111111111110.",
    ".00000000000000.",
    "................",
], hatband=("headwear_emblem", "accent", "bB", ("headwear_emblem", "hatband"), 1))

# ------------------------------------------------------------------------------------- torso
icon("torso_wear", "plate", "metal", [
    "................",
    "................",
    "...122....332...",
    "..01122..33332..",
    ".01122223333332.",
    ".00122tTTT33322.",
    "..0122tTTT3322..",
    "...012tTTT322...",
    "...011tTTT322...",
    "....01tTTT21....",
    "...000tTTT000...",
    "...011tTTT221...",
    "...001tTTT100...",
    "....00000000....",
    "................",
    "................",
], tabard=("over_torso", "cloth", "tT", ("over_torso", "tabard"), 2))

icon("torso_wear", "jerkin", "leather", [
    "................",
    "................",
    "...111....222...",
    "..11222..22222..",
    ".1112220.022222.",
    ".0112220.022221.",
    "..01222O.O2221..",
    "..01222.0.2221..",
    "..01222O.O2221..",
    "..01222.0.2221..",
    "..01122O.O2211..",
    "..00111.0.1110..",
    "..000000000000..",
    "................",
    "................",
    "................",
])
icon("torso_wear", "tunic", "cloth", [
    "................",
    "................",
    "...111....111...",
    "..111110011111..",
    ".11111111111111.",
    ".01111111111111.",
    "..0011111111110.",
    "...01111111111..",
    "...01111111111..",
    "...00000000000..",
    "...01111111111..",
    "...01111111111..",
    "...00111111100..",
    "....00000000....",
    "................",
    "................",
])
icon("torso_wear", "robe", "cloth", [
    "................",
    "...111....111...",
    "..111110011111..",
    ".11111111111111.",
    ".01111111111111.",
    "..0011111111110.",
    "...01111111111..",
    "...00000000000..",
    "...01111011111..",
    "..011111011111..",
    "..011111011111..",
    ".0111110111111..",
    ".01111101111111.",
    ".00111101111100.",
    "..000000000000..",
    "................",
])

# ------------------------------------------------------------------------------------- legs
icon("legs_wear", "greaves", "metal", [
    "................",
    "................",
    "...0111122333...",
    "...0111122333...",
    "...00000000000..",
    "...0112..12332..",
    "...0112..12332..",
    "...1223..23333..",
    "...0112..12332..",
    "...0112..12332..",
    "...0112..12332..",
    "...0011..11221..",
    "..00011..112221.",
    "..00000..000000.",
    "................",
    "................",
])
icon("legs_wear", "leggings", "leather", [
    "................",
    "................",
    "...01111122222..",
    "...00000000000..",
    "...011112222222.",
    "...0111..12222..",
    "...0111..12222..",
    "...0111..12222..",
    "...0111..12222..",
    "...0111..12222..",
    "...0111..12222..",
    "...0011..11221..",
    "...0000..00000..",
    "................",
    "................",
    "................",
])

# ------------------------------------------------------------------------------------- hands
icon("hands", "gauntlets", "metal", [
    "................",
    "................",
    "......2333......",
    ".....122333.....",
    ".....122333.....",
    ".....000000.....",
    "....01122332....",
    "....01122333.22.",
    "....01122333233.",
    "....01112233333.",
    "....0111222332..",
    ".....01112222...",
    ".....0001111....",
    "......00000.....",
    "................",
    "................",
])
icon("hands", "gloves", "leather", [
    "................",
    "................",
    "................",
    ".....122222.....",
    ".....000000.....",
    ".....011222.....",
    "....0111222.....",
    "....01112222.22.",
    "....01112222222.",
    "....01111222222.",
    "....0111122222..",
    ".....01111222...",
    ".....0001111....",
    "......00000.....",
    "................",
    "................",
])

# ------------------------------------------------------------------------------------- feet
icon("feet", "boots", "leather", [
    "................",
    "................",
    "....01122222....",
    "....00000000....",
    "....01112222....",
    "....01112222....",
    "....01112222....",
    "....01112222....",
    "....011122222...",
    "....0111222222..",
    "....01111222222.",
    "....00111112222.",
    "....00000000000.",
    "................",
    "................",
    "................",
])

# ------------------------------------------------------------------------------------- cape
icon("cape", "mantle", "cloth", [
    "................",
    ".....00000......",
    "....011aA10.....",
    "...01110111.....",
    "...011101111....",
    "..0110110111....",
    "..01101101111...",
    "..011011011111..",
    ".0110110111111..",
    ".01101101111111.",
    ".01101101111111.",
    ".01101101111111.",
    ".00110010011100.",
    "..00..00..000...",
    "................",
    "................",
], clasp=("clasp", "accent", "aA", None, 1))

icon("cape", "cloak", "cloth", [
    "................",
    ".....111111.....",
    "....11111111....",
    "...1110000111...",
    "...110OOOO011...",
    "...1110OO0111...",
    "..011110011111..",
    "..011111011111..",
    "..0111110111111.",
    ".01111101111111.",
    ".01111101111111.",
    ".01111101111111.",
    ".01111101111111.",
    ".00000000000000.",
    "................",
    "................",
])

# ------------------------------------------------------------------------------------- belt
icon("belt", "leather_belt", "leather", [
    "................",
    "................",
    "............011.",
    "..........01222.",
    ".........0122O2.",
    "........0122222.",
    ".......012O220..",
    "......0122220...",
    "..kkKKK2O220....",
    "..k00K12220.....",
    "..k01K1220......",
    "..kkKKK10.......",
    "................",
    "................",
    "................",
    "................",
], buckle=("belt_trim", "accent", "kK", ("belt_trim", "buckle"), 2))

icon("belt", "sash", "accent", [
    "................",
    "................",
    "................",
    "................",
    ".00111111100....",
    ".0111111101110..",
    ".00011111001110.",
    "........011.011.",
    "......0111...01.",
    ".....0111....01.",
    "....0111........",
    "....011.........",
    "................",
    "................",
    "................",
    "................",
])

# ------------------------------------------------------------------------------------- jewelry
icon("amulet", "amulet", "accent", [
    "................",
    "...0........1...",
    "...0........1...",
    "....0......1....",
    "....0......1....",
    ".....0....1.....",
    "......0001......",
    "......0111......",
    ".....0gGGG1.....",
    "....0gGGGGG1....",
    "....0gGGGGG1....",
    "....0ggGGGG1....",
    ".....0ggGG1.....",
    "......0001......",
    "................",
    "................",
], gem=("amulet", "accent", "gG", None))
icon("ring", "ring", "accent", [
    "................",
    "................",
    "................",
    "......gGG.......",
    ".....gGGGG......",
    ".....ggGGG......",
    "......000.......",
    "....0011111.....",
    "...001...111....",
    "...00.....11....",
    "...00.....11....",
    "...001...111....",
    "....0011111.....",
    "......000.......",
    "................",
    "................",
], gem=("ring", "accent", "gG", None))


def split(rows: list[str], layers: dict) -> dict[str, np.ndarray]:
    """One code grid per layer: digits are the base, legend letters are overlays, 'O' an outline
    detail kept on the base layer."""
    out = {name: np.full((SIZE, SIZE), grid.CLEAR, np.int8) for name in layers}
    lookup = {}
    for name, (_, _, chars, _, _) in layers.items():
        for shade, ch in enumerate(chars):
            if ch != ".":
                lookup[ch] = (name, shade)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            if ch == "O":
                out["base"][y, x] = grid.INK
            elif ch in lookup:
                name, shade = lookup[ch]
                out[name][y, x] = shade
                under = layers[name][4]
                if under is not None:
                    out["base"][y, x] = under
            else:
                raise ValueError(f"unknown icon character {ch!r} at ({x}, {y})")
    return out


def main() -> None:
    outline = STYLE.outline.color
    for (slot, variant), (layers, rows) in ICONS.items():
        folder = ROOT / "icons" / slot / variant
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.png"):
            old.unlink()
        codes = split(rows, layers)
        meta = []
        for name, (layer_slot, material, _, requires, _) in layers.items():
            ramp = STYLE.materials[material].base
            write_rgba(folder / f"{name}.png", grid.paint(codes[name], ramp, outline))
            entry = {"name": name, "slot": layer_slot, "material": material}
            if requires:
                entry["requires"] = {requires[0]: requires[1]}
            if name == "gem":
                entry["preset_from"] = "jewel"
            meta.append(entry)
        (folder / "icon.yaml").write_text(yaml.safe_dump(
            {"slot": slot, "variant": variant, "layers": meta}, sort_keys=False))
    print(f"wrote {len(ICONS)} icons")


if __name__ == "__main__":
    main()
