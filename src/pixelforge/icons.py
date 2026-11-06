"""Item icons (ROADMAP.md, "Gear sets and item icons"): a 16 x 16 inventory icon for each piece
of a gear set (parts/sets.yaml), in the set's own presets so a piece's icon always matches its
sprite.

Icon art lives in icons/<slot>/<variant>/: one PNG per layer, each in one material's base ramp
(drawn by tools/art/icons_art.py), and icon.yaml naming each layer's slot and material. A layer
takes its color the way a sprite's part does: the set's slot color for that slot first, then the
set's preset for the layer's material. An overlay that `requires` a part variant (a plume, a
buckle) only shows when the set wears it; a gem takes the set's `jewel` preset. The outline is
generated: a closed 1 px ring in the outline color around the whole silhouette.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .color import parse_hex
from .outline import outline
from .recipe import load_sets
from .recolor import preset_ramp, ramp_map, recolor
from .sheet import load_rgba, save_rgba
from .style import Style

SIZE = 16
PIECES = ("headwear", "torso_wear", "legs_wear", "hands", "feet", "cape", "belt", "amulet", "ring")
JEWELRY = ("amulet", "ring")
LABELS = {"headwear": "helmet", "torso_wear": "chest", "legs_wear": "legs", "hands": "gloves",
          "feet": "boots", "cape": "cape", "belt": "belt", "amulet": "amulet", "ring": "ring"}


@dataclass(frozen=True)
class Layer:
    name: str
    slot: str
    material: str
    requires: dict[str, str]
    preset_from: str | None


@dataclass(frozen=True)
class IconDef:
    slot: str
    variant: str
    folder: Path
    layers: tuple[Layer, ...]


def load_icons(root: Path) -> dict[tuple[str, str], IconDef]:
    out = {}
    for meta in sorted((Path(root) / "icons").glob("*/*/icon.yaml")):
        data = yaml.safe_load(meta.read_text())
        layers = tuple(Layer(l["name"], l["slot"], l["material"], dict(l.get("requires") or {}),
                             l.get("preset_from")) for l in data["layers"])
        out[(data["slot"], data["variant"])] = IconDef(data["slot"], data["variant"], meta.parent, layers)
    return out


def set_pieces(gear: dict[str, Any]) -> dict[str, str]:
    """slot -> variant for every piece a set wears that has an icon slot, plus its jewelry."""
    parts = gear.get("parts") or {}
    out = {slot: parts[slot] for slot in PIECES if parts.get(slot) not in (None, "none")}
    out.update({j: j for j in JEWELRY})
    return out


def _preset(gear: dict[str, Any], layer: Layer) -> str | None:
    if layer.preset_from:
        return gear.get(layer.preset_from)
    slot_colors = gear.get("slot_colors") or {}
    return slot_colors.get(layer.slot) or (gear.get("colors") or {}).get(layer.material)


def compose(style: Style, icon: IconDef, gear: dict[str, Any]) -> tuple[np.ndarray, list[str]]:
    """The icon as the set wears it (RGBA, SIZE x SIZE) and any problems found."""
    problems = []
    img = np.zeros((SIZE, SIZE, 4), np.uint8)
    parts = gear.get("parts") or {}
    for layer in icon.layers:
        if any(parts.get(slot) != variant for slot, variant in layer.requires.items()):
            continue
        cell = load_rgba(icon.folder / f"{layer.name}.png")
        if cell.shape[:2] != (SIZE, SIZE):
            problems.append(f"{icon.slot}/{icon.variant}/{layer.name}.png is {cell.shape[1]} x {cell.shape[0]}, "
                            f"not {SIZE} x {SIZE}")
            continue
        material = style.materials[layer.material]
        preset = _preset(gear, layer)
        if preset is None:
            problems.append(f"{icon.slot}/{icon.variant}: no {layer.material} preset for layer {layer.name!r}")
        elif preset not in material.presets:
            problems.append(f"{icon.slot}/{icon.variant}: {preset!r} is not a {layer.material} preset")
            preset = None
        allowed = {parse_hex(c) for c in material.base} | {parse_hex(style.outline.color)}
        used = {tuple(int(v) for v in px[:3]) for px in cell[cell[..., 3] == 255]}
        if used - allowed:
            problems.append(f"{icon.slot}/{icon.variant}/{layer.name}.png has colors outside the "
                            f"{layer.material} base ramp")
        cell = recolor(cell, ramp_map(material, preset_ramp(style, layer.material, preset)))
        solid = cell[..., 3] == 255
        img[solid] = cell[solid]
    if not (img[..., 3] == 255).any():
        problems.append(f"{icon.slot}/{icon.variant}: the icon is empty")
        return img, problems
    edge = np.zeros((SIZE, SIZE), bool)
    edge[[0, -1], :] = edge[:, [0, -1]] = True
    if ((img[..., 3] == 255) & edge).any():
        problems.append(f"{icon.slot}/{icon.variant}: art on the canvas edge leaves no room for the outline")
    return outline(img, parse_hex(style.outline.color), open_soles=False).image, problems


def build_icons(style: Style, root: Path, names: list[str] | None = None,
                out: Path | None = None) -> tuple[dict[str, dict[str, np.ndarray]], list[str]]:
    """Every set's icons (set -> slot -> RGBA), written to out/icons/ with a sheet and index."""
    root = Path(root)
    sets = load_sets(root)
    icons = load_icons(root)
    chosen = names or list(sets)
    problems = [f"set {n!r} is not in parts/sets.yaml" for n in chosen if n not in sets]
    result: dict[str, dict[str, np.ndarray]] = {}
    for name in [n for n in chosen if n in sets]:
        gear = sets[name]
        result[name] = {}
        for slot, variant in set_pieces(gear).items():
            icon = icons.get((slot, variant))
            if icon is None:
                problems.append(f"set {name}: no icon for {slot}/{variant} (icons/{slot}/{variant}/)")
                continue
            img, found = compose(style, icon, gear)
            problems += [f"set {name}: {p}" for p in found]
            result[name][slot] = img
    if out is not None:
        write_icons(result, sets, Path(out))
    return result, problems


def write_icons(result: dict[str, dict[str, np.ndarray]], sets: dict, out: Path) -> Path:
    """out/<set>/<slot>.png, a sheet (a row per set, a column per piece) and index.json."""
    out.mkdir(parents=True, exist_ok=True)
    sheet = np.zeros((SIZE * len(result), SIZE * len(PIECES), 4), np.uint8)
    index: dict[str, Any] = {"cell": SIZE, "pieces": list(PIECES), "labels": LABELS, "sets": {}}
    for row, (name, pieces) in enumerate(result.items()):
        (out / name).mkdir(exist_ok=True)
        entry = {"row": row, "note": sets[name].get("note", ""), "pieces": {}}
        for col, slot in enumerate(PIECES):
            if slot not in pieces:
                continue
            save_rgba(out / name / f"{LABELS[slot]}.png", pieces[slot])
            sheet[row * SIZE:(row + 1) * SIZE, col * SIZE:(col + 1) * SIZE] = pieces[slot]
            entry["pieces"][slot] = {"col": col, "label": LABELS[slot],
                                     "variant": set_pieces(sets[name])[slot]}
        index["sets"][name] = entry
    save_rgba(out / "icons.png", sheet)
    (out / "index.json").write_text(json.dumps(index, indent=1))
    return out


def render_overview(style: Style, result: dict[str, dict[str, np.ndarray]], path: Path,
                    zoom: int = 5) -> Path:
    """Every set's icons on beige, light and dark ground, zoomed (nearest neighbor), labelled."""
    from PIL import Image, ImageDraw
    grounds = [parse_hex(style.raw["preview_backgrounds"][k]) for k in ("beige", "light", "dark")]
    cell = SIZE * zoom + 6
    label_w, head = 90, 18
    block_w = label_w + cell * len(PIECES) + 12
    img = Image.new("RGB", (block_w * len(grounds), head + cell * len(result) + 8), (240, 236, 224))
    draw = ImageDraw.Draw(img)
    for g, ground in enumerate(grounds):
        x0 = g * block_w
        for col, slot in enumerate(PIECES):
            draw.text((x0 + label_w + col * cell + 2, 4), LABELS[slot], fill=(40, 40, 40))
        for row, (name, pieces) in enumerate(result.items()):
            y = head + row * cell
            draw.rectangle([x0 + label_w, y, x0 + label_w + cell * len(PIECES) - 1, y + cell - 1], fill=ground)
            draw.text((x0 + 4, y + cell // 2 - 6), name, fill=(40, 40, 40))
            for col, slot in enumerate(PIECES):
                if slot in pieces:
                    big = Image.fromarray(pieces[slot]).resize((SIZE * zoom, SIZE * zoom), Image.NEAREST)
                    img.paste(big, (x0 + label_w + col * cell + 3, y + 3), big)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path
