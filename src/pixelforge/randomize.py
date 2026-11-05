"""pf random: random characters from the parts library, respecting parts/compat.yaml."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import yaml

from .parts import Library
from .recipe import Recipe, parse_recipe
from .style import Style


class CompatError(ValueError):
    pass


def load_compat(root: Path) -> dict[str, Any]:
    path = Path(root) / "parts" / "compat.yaml"
    data = yaml.safe_load(path.read_text())
    for key in ("hairstyles", "slots", "trims", "requires", "incompatible"):
        if key not in data:
            raise CompatError(f"{path}: {key} missing")
    return data


def _pick(rng: random.Random, weights: dict[str, float]) -> str:
    names = sorted(weights)
    return rng.choices(names, weights=[float(weights[n]) for n in names])[0]


def _ok(parts: dict[str, str], compat: dict[str, Any]) -> bool:
    chosen = {f"{s}/{v}" for s, v in parts.items()}
    for need, options in compat["requires"].items():
        if need in chosen and not chosen & set(options):
            return False
    return not any(a in chosen and b in chosen for a, b in compat["incompatible"])


def random_recipe(style: Style, lib: Library, compat: dict[str, Any], rng: random.Random,
                  name: str, anims: tuple[str, ...]) -> Recipe:
    for _ in range(200):
        style_name = _pick(rng, {k: v["weight"] for k, v in compat["hairstyles"].items()})
        parts = dict(compat["hairstyles"][style_name]["parts"])
        for slot, weights in sorted(compat["slots"].items()):
            variant = _pick(rng, weights)
            if variant != "none":
                parts[slot] = variant
        for trim in compat["trims"]:
            p_slot, p_variant = trim["parent"].split("/")
            if trim["slot"] in parts or parts.get(p_slot) != p_variant:
                continue
            if rng.random() < float(trim.get("chance", 1.0)):
                parts[trim["slot"]] = trim["variant"]
        if _ok(parts, compat):
            break
    else:
        raise CompatError("no valid combination after 200 tries; check compat.yaml")
    materials = {lib.part(s, v).material for s, v in parts.items()} | {"skin"}
    excluded = compat.get("exclude_presets", {})
    colors = {}
    for m in sorted(materials):
        presets = [p for p in style.materials[m].presets if p not in excluded.get(m, [])]
        colors[m] = rng.choice(presets)
    data = {"name": name, "rig": "humanoid", "timing_profile": "player",
            "seed": rng.randrange(1 << 30), "parts": parts, "colors": colors, "anims": list(anims)}
    return parse_recipe(data, style)


def color_count(style: Style, lib: Library, recipe: Recipe) -> int:
    """Most distinct opaque colors in any idle or walk frame (the E11 budget): lag frames and
    walk legs can show shades that idle frame 0 hides."""
    from .compose import Composer
    c = Composer(style.root, style, recipe, lib)
    most = 0
    for anim in ("idle", "walk"):
        for d in style.drawn_directions:
            for i in range(c.rig.frame_count(anim, d)):
                sprite = c.frame(anim, d, i).sprite
                most = max(most, len({tuple(p) for p in sprite[sprite[..., 3] == 255][:, :3]}))
    return most


def random_recipes(style: Style, seed: int, count: int, anims: tuple[str, ...] = ("idle", "blink", "walk")
                   ) -> list[Recipe]:
    lib = Library(style.root, style)
    compat = load_compat(style.root)
    rng = random.Random(seed)
    budget = style.constraints.max_colors_per_frame
    out = []
    for i in range(count):
        for _ in range(100):  # redraw until the character fits the color budget
            r = random_recipe(style, lib, compat, rng, f"random_{seed}_{i + 1:02d}", anims)
            if color_count(style, lib, r) <= budget:
                break
        else:
            raise CompatError(f"could not fit a character in {budget} colors")
        out.append(r)
    return out
