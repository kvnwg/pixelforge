"""The design pass (STYLE_GUIDE.md section 13): a cast of different people, not one body in
different colors: per-slot colors, silhouette parts, bold presets, clean random characters."""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.color import hex_to_oklch, parse_hex
from pixelforge.recipe import RecipeError, parse_recipe

CAST = ["knight", "knight_enemy", "rk_guardian", "rk_blade", "rk_ranger", "rk_cleric", "rk_arcanist",
        "rk_lancer", "paladin", "corsair", "dwarf", "catfolk_scout", "frost_elf", "ember_warlock"]


@pytest.fixture(scope="module")
def cast(root, style):
    return {n: build(root, n, style=style) for n in CAST}


def colors_of(layer):
    img = layer.image
    return {tuple(int(v) for v in px[:3]) for px in img[img[..., 3] == 255]}


def ramp(style, material, preset):
    return {parse_hex(c) for c in style.materials[material].presets[preset]}


def test_slot_colors_dye_one_part_apart_from_its_material(cast, style):
    guardian = cast["rk_guardian"]
    assert guardian.recipe.slot_colors == {} and guardian.recipe.colors["cloth"] == "scarlet"
    knight = cast["knight"]
    f = knight.frames[("idle", "n")][0]
    cape = next(l for l in f.layers if l.slot == "cape")
    tabard = next(l for l in f.layers if l.slot == "over_torso")
    assert colors_of(cape) - {parse_hex(style.outline.color)} <= ramp(style, "cloth", "royal")
    assert colors_of(tabard) <= ramp(style, "cloth", "scarlet")
    assert [str(x) for x in knight.findings] == []


def test_a_slot_color_must_be_a_preset_of_that_parts_material(root, style):
    data = {"name": "x", "rig": "humanoid", "parts": {"eyes": "dots", "cape": "cloak", "torso_wear": "tunic"},
            "colors": {"cloth": "scarlet"}, "slot_colors": {"cape": "royal gold"}, "anims": ["idle"]}
    with pytest.raises(RecipeError):
        build(root, parse_recipe(data, style), style=style)
    data["slot_colors"] = {"cape": "no such preset"}
    with pytest.raises(RecipeError):
        parse_recipe(data, style)


def test_the_cast_validates_and_no_two_share_a_silhouette(cast):
    masks = {}
    for name, b in cast.items():
        assert [str(f) for f in b.findings] == [], name
        masks[name] = b.frames[("idle", "s")][0].sprite[..., 3] == 255
    for a, b in combinations(CAST, 2):
        assert (masks[a] ^ masks[b]).sum() >= 8, (a, b)  # a different outline, not a recolor


def test_each_hero_has_a_bold_signature_color(cast, style):
    """At least one part of every redesigned character uses a color past the old muted limit."""
    old_limit = 0.09
    for name, b in cast.items():
        f = b.frames[("idle", "s")][0]
        chroma = max(hex_to_oklch("#%02x%02x%02x" % c).C for l in f.layers for c in colors_of(l))
        assert chroma > old_limit, name


def test_the_limits_keep_fx_brighter_than_characters(style):
    c, fx, glow = style.raw["constraints"], style.raw["fx_constraints"], style.raw["glow_constraints"]
    assert c["oklch_C_max"] == 0.13 and c["oklch_L_range"][1] == 0.84
    assert fx["oklch_L_range"][1] > c["oklch_L_range"][1] and fx["oklch_C_max"] > c["oklch_C_max"]
    assert glow["oklch_C_max"] > c["oklch_C_max"]
    assert c["max_colors_per_frame"] == 24


def test_random_characters_use_the_new_parts_and_validate(style):
    from pixelforge.randomize import random_recipes
    recipes = random_recipes(style, seed=7, count=4)
    for r in recipes:
        assert not build(style.root, r, style=style).findings, r.name
    names = [r.name for r in recipes]
    assert names == [f"random_7_{i:02d}" for i in range(1, 5)]
    again = random_recipes(style, seed=7, count=4)
    assert [r.parts for r in again] == [r.parts for r in recipes]  # same seed, same characters


def test_followthrough_parts_trail_the_body(cast):
    """The cloak and the scarf lag like hair: walking, they trail the torso by a frame."""
    knight = cast["knight"]
    offsets = [next(l for l in f.layers if l.slot == "cape").offset[1]
               for f in knight.frames[("walk", "e")]]
    torso = [knight.composer.rig.anchor("walk", "e", i, "torso")[1] - 20 for i in range(8)]
    assert offsets != torso and all(abs(o - t) <= 1 for o, t in zip(offsets, torso))
