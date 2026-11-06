"""Rook (MONSTERS.md section 5.10): a fast knight boss on the huge canvas with red sword trails."""

from __future__ import annotations

import json

import numpy as np
import pytest

from pixelforge.anim import tell_ms
from pixelforge.build import build
from pixelforge.color import parse_hex
from pixelforge.compose import SMEAR

ATTACKS = ["attack_slash", "charge", "attack_slam", "attack_ring", "attack_fan"]
DIRS = ("s", "e", "n", "w")


@pytest.fixture(scope="module")
def rook(root, style):
    return build(root, "rook", style=style)


@pytest.fixture(scope="module")
def enraged(root, style):
    return build(root, "rook_enraged", style=style)


@pytest.fixture(scope="module")
def exported(rook, tmp_path_factory):
    from pixelforge.export import export
    out = tmp_path_factory.mktemp("rook")
    export(rook, out, gifs=False)
    return json.loads(next(out.rglob("rook.json")).read_text())["meta"]["pixelforge"]


def test_rook_and_his_enraged_form_validate(rook, enraged):
    assert [str(f) for f in rook.findings] == []
    assert [str(f) for f in enraged.findings] == []


def test_a_knight_on_the_huge_canvas(rook):
    size = rook.composer.rig.size
    assert (size.name, size.canvas, size.pivot) == ("huge", 96, (47, 91))
    for d in ("s", "e", "n"):
        solid = rook.frames[("idle", d)][0].sprite[..., 3] == 255
        ys = np.flatnonzero(solid.any(axis=1))
        assert ys.max() == 91 and 50 <= ys.max() - ys.min() + 1 <= 62, d  # about 55 px: a tall knight


@pytest.mark.parametrize("anim", ATTACKS)
def test_super_fast_but_every_attack_is_telegraphed(rook, style, anim):
    """Every strike is a 50 to 60 ms blink, and the boss tell still comes first."""
    adef = rook.composer.anims[anim]
    profile = style.raw["combat"]["timing_profiles"]["boss"]
    durations = [f.duration for f in rook.frames[(anim, "e")]]
    assert tell_ms(adef, durations) >= profile["telegraph_min_ms"], anim
    for i in adef.flags["active"]:
        assert durations[i] <= 60, (anim, i)
    assert max(rook.composer.anims["walk"].frames_ms) <= 80  # he prowls fast


@pytest.mark.parametrize("anim", ATTACKS)
def test_every_swing_leaves_a_red_trail(rook, style, anim):
    blood = {parse_hex(c) for c in style.fx_ramps["blood"]}
    white = {parse_hex(c) for c in style.fx_ramps["swing"]}
    active = rook.composer.anims[anim].flags["active"]
    for d in DIRS:
        for i, f in enumerate(rook.frames[(anim, d)]):
            trail = f.owner == SMEAR
            colors = {tuple(int(v) for v in px) for px in f.sprite[trail][..., :3]}
            assert colors <= blood and not colors & white, (anim, d, i)
            if i in active:
                assert trail.sum() >= 12, (anim, d, i)  # a strike frame always shows its trail


def test_the_charge_dashes_and_cuts_through(rook, exported):
    assert sum(exported["root_motion"]["charge_e"]) >= 40
    assert exported["timing_profile"] == "boss" and exported["size_class"] == "huge"
    dash = rook.frames[("charge", "e")][2]
    solid = dash.sprite[..., 3] == 255
    ys, xs = np.nonzero(solid & (dash.owner != SMEAR))
    (x, y, w, h), = dash.hitboxes
    assert x <= xs.min() and xs.max() < x + w and y <= ys.min()  # the dash hits with his whole body
    assert exported["loop_frames"]["charge_e"] == [2, 3]  # the game repeats the dash while it lasts
    assert sorted(rook.composer.anims["charge"].flags["airborne"]) == [2, 3]


def test_the_ring_and_the_fan_throw_blood_crescents(exported):
    ring = [e for e in exported["events"]["attack_ring_e"] if e["type"] == "spawn"]
    fan = [e for e in exported["events"]["attack_fan_e"] if e["type"] == "spawn"]
    assert [(e["fx"], e["pattern"], e["count"]) for e in ring] == [("blood_crescent", "ring", 14)]
    assert [(e["fx"], e["pattern"], e["count"]) for e in fan] == [("blood_crescent", "fan", 5)]
    assert fan[0]["point_name"] == "weapon_tip" and ring[0]["point_name"] == "torso"


def test_the_spin_hits_all_round_him(rook):
    for i in (1, 2, 3, 4):
        (x, y, w, h), = rook.frames[("attack_ring", "e")][i].hitboxes
        assert w >= 60, i  # the ring reaches about 30 px out on both sides


def test_the_enraged_rook_glows_through_the_cracks(rook, enraged, style):
    assert enraged.recipe.raw["family"] == rook.recipe.raw["family"] == "rook"
    assert rook.recipe.trail == enraged.recipe.trail == "blood"
    a = rook.frames[("idle", "e")][0].sprite
    b = enraged.frames[("idle", "e")][0].sprite
    assert np.array_equal(a[..., 3] == 255, b[..., 3] == 255)  # the same silhouette
    changed = (a[..., :3] != b[..., :3]).any(axis=2)
    assert changed.sum() >= 10  # the ember cracks show on the plate


def test_an_unknown_trail_ramp_is_a_recipe_problem(style):
    from pixelforge.recipe import RecipeError, parse_recipe
    data = {"name": "x", "rig": "greatknight", "parts": {"body": "rook"}, "trail": "nope"}
    with pytest.raises(RecipeError, match="trail"):
        parse_recipe(data, style)
