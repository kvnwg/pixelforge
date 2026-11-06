"""Design pass 2 (2026-11-06): a vibrant cast (STYLE_GUIDE.md section 14, ROADMAP.md)."""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.color import hex_to_oklch, oklch_to_rgb, rgb_to_oklch, to_hex
from pixelforge.compose import HELD_SLOTS

CAST = ["knight", "paladin", "corsair", "dwarf", "catfolk_scout", "frost_elf", "ember_warlock",
        "rk_guardian", "rk_blade", "rk_ranger", "rk_cleric", "rk_arcanist", "rk_lancer"]


def generator(root):
    spec = importlib.util.spec_from_file_location("palette_presets", root / "tools" / "art" / "palette_presets.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def cast(root, style):
    return {name: build(root, name, style=style) for name in CAST}


def test_oklch_round_trips_and_keeps_lightness_out_of_gamut():
    for hx in ("#3a263a", "#c0453f", "#1f438a", "#f4f3ef", "#5a556b"):
        o = hex_to_oklch(hx)
        assert to_hex(oklch_to_rgb(o.L, o.C, o.h)) == hx
    o = rgb_to_oklch(oklch_to_rgb(0.62, 0.40, 25))  # far past what sRGB can show
    assert abs(o.L - 0.62) < 0.01 and abs((o.h - 25 + 180) % 360 - 180) < 2 and 0.2 < o.C < 0.4


def test_presets_come_from_the_generator_and_the_anchor_stays_exact(root, style):
    """style.json's presets are written by tools/art/palette_presets.py: edit the spec there."""
    gen = generator(root)
    raw = style.raw["materials"]
    for material, presets in gen.SPECS.items():
        for name, spec in presets.items():
            assert raw[material]["presets"][name] == gen.ramp(raw[material]["shades"], spec), (material, name)
    anchor = style.raw["palette_anchor"]
    assert raw["cloth"]["presets"]["navy (anchor)"] == [anchor["cloth_dark"], anchor["cloth_mid"]]
    assert raw["skin"]["presets"]["light (anchor)"] == [anchor["skin_shadow"], anchor["skin_mid"], anchor["skin_light"]]


def test_vivid_ramps_are_saturated_and_read_light_to_dark(style):
    raw = style.raw["materials"]
    for name in ("scarlet", "royal", "emerald", "violet", "azure", "tangerine", "magenta", "flame"):
        assert max(hex_to_oklch(c).C for c in raw["cloth"]["presets"][name]) >= 0.14, name
    for name, ramp in raw["cloth"]["presets"].items():
        if "(anchor)" not in name:
            dark, light = (hex_to_oklch(c).L for c in ramp)
            assert light - dark >= 0.09, name  # two tones, not one flat color
    assert hex_to_oklch(raw["metal"]["presets"]["steel"][-1]).L >= 0.85  # a glint
    assert hex_to_oklch(raw["metal"]["presets"]["royal gold"][-1]).L >= 0.9


def test_every_cast_member_is_vivid_and_breaks_the_plain_silhouette(cast):
    """A signature color at full chroma and a shape past the plain 9 x 17 body (a plume, horns,
    a tall hat, a brim, wings, a cape's flare or a scarf's tail)."""
    for name, b in cast.items():
        assert [str(f) for f in b.findings] == [], name
        f = b.frames[("idle", "s")][0]
        colors = {tuple(int(v) for v in p) for p in f.sprite[f.sprite[..., 3] == 255][:, :3]}
        assert max(rgb_to_oklch(c).C for c in colors) >= 0.14, name
        fill = (f.owner >= 0) & ~f.slot_mask(*HELD_SLOTS)
        ys, xs = np.flatnonzero(fill.any(axis=1)), np.flatnonzero(fill.any(axis=0))
        assert xs.max() - xs.min() + 1 > 9 or ys.max() - ys.min() + 1 > 17, name


def test_tall_headgear_stays_on_the_canvas_through_a_backflip(cast):
    """The knight keeps the whole combat set: his plume clears the top edge even at the top of a
    backflip, where the head is 4 px higher, and a head trim never lags (the head keeps its height)."""
    knight = cast["knight"]
    for d in ("s", "e", "n", "w"):
        for f in knight.frames[("backflip", d)]:
            rows = np.flatnonzero((f.sprite[..., 3] == 255).any(axis=1))
            assert rows.min() >= 2, d
    plume = next(l for l in knight.frames[("idle", "s")][0].layers if l.slot == "headwear_trim")
    assert not plume.part.lags


def test_random_characters_never_get_the_anchors_muted_presets(style):
    from pixelforge.randomize import random_recipes
    for r in random_recipes(style, 3, 6, anims=("idle",)):
        assert not any("(anchor)" in p for p in r.colors.values()), r.name
        assert not any("(anchor)" in p for p in (r.slot_colors or {}).values()), r.name
