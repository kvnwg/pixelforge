"""Gear sets and item icons (ROADMAP.md, "Gear sets and item icons")."""

from __future__ import annotations

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.color import parse_hex
from pixelforge.icons import JEWELRY, SIZE, build_icons, compose, load_icons, set_pieces
from pixelforge.recipe import RecipeError, load_sets, parse_recipe

SETS = ["iron", "leather", "gold", "crystal", "traveler", "crimson", "forest", "azure"]


@pytest.fixture(scope="module")
def icons(root, style):
    result, problems = build_icons(style, root)
    return result, problems


def test_a_set_dresses_a_recipe_and_the_recipe_wins(style):
    data = {"name": "x", "rig": "humanoid", "set": "forest", "anims": ["idle"],
            "parts": {"eyes": "dots", "headwear": "hood"}, "colors": {"cloth": "scarlet"}}
    r = parse_recipe(data, style)
    assert r.gear_set == "forest"
    assert r.parts["torso_wear"] == "tunic" and r.parts["cape"] == "mantle"  # from the set
    assert r.parts["headwear"] == "hood" and r.colors["cloth"] == "scarlet"  # the recipe's own
    assert r.slot_colors["cape"] == "emerald"
    with pytest.raises(RecipeError, match="set"):
        parse_recipe({**data, "set": "nope"}, style)


def test_every_set_has_a_recipe_that_validates(root, style):
    assert sorted(load_sets(root)) == sorted(SETS)
    for name in SETS:
        b = build(root, f"set_{name}", style=style)
        assert b.recipe.gear_set == name
        assert [str(f) for f in b.findings] == [], name


def test_every_piece_has_a_clean_icon(icons, style):
    result, problems = icons
    assert problems == []
    outline = parse_hex(style.outline.color)
    for name in SETS:
        gear = load_sets(style.root)[name]
        assert set(result[name]) == set(set_pieces(gear)), name
        for slot, img in result[name].items():
            assert img.shape == (SIZE, SIZE, 4), (name, slot)
            assert set(np.unique(img[..., 3])) <= {0, 255}, (name, slot)
            solid = img[..., 3] == 255
            # a closed ring: every pixel beside the art is outline-colored, and no art sits on the
            # canvas edge (the ring itself may: art reaches column 14, its outline column 15)
            inner = solid & ~np.all(img[..., :3] == outline, axis=-1)
            p = np.pad(inner, 1)
            near = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
            ring = ~inner & near
            assert (solid[ring]).all(), (name, slot)
            assert not inner[[0, -1], :].any() and not inner[:, [0, -1]].any(), (name, slot)
    assert all(j in result[n] for n in SETS for j in JEWELRY)


def test_a_pieces_icon_matches_its_sprite(icons, root, style):
    result, _ = icons
    knight = build(root, "set_gold", style=style, validate=False)
    f = knight.frames[("idle", "s")][0]
    helm = next(l for l in f.layers if l.slot == "headwear")
    sprite_colors = {tuple(int(v) for v in px[:3]) for px in helm.image[helm.image[..., 3] == 255]}
    icon = result["gold"]["headwear"]
    icon_colors = {tuple(int(v) for v in px[:3]) for px in icon[icon[..., 3] == 255]}
    royal_gold = {parse_hex(c) for c in style.materials["metal"].presets["royal gold"]}
    assert sprite_colors & royal_gold and icon_colors & royal_gold


def test_a_hidden_overlay_leaves_no_hole(root, style):
    """The gold set wears no cross on its helm: the helm's icon has the same shape either way."""
    gear = load_sets(root)["gold"]
    helm = load_icons(root)[("headwear", "great_helm")]
    plain, _ = compose(style, helm, gear)
    crossed, _ = compose(style, helm, {**gear, "parts": {**gear["parts"], "headwear_emblem": "cross_helm"}})
    assert np.array_equal(plain[..., 3], crossed[..., 3])
    assert not np.array_equal(plain, crossed)  # and the cross shows when worn
