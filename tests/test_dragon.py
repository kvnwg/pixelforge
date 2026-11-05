"""The Cinderwyrm (MONSTERS.md section 5.8): a big, slow dragon on the huge 96 px size class."""

from __future__ import annotations

import json

import numpy as np
import pytest

from pixelforge.anim import tell_ms
from pixelforge.build import build
from pixelforge.compose import SMEAR

ATTACKS = ("attack_bite", "attack_tail", "breath")


@pytest.fixture(scope="module")
def wyrm(root, style):
    return build(root, "cinderwyrm", style=style)


@pytest.fixture(scope="module")
def obsidian(root, style):
    return build(root, "cinderwyrm_obsidian", style=style)


def test_the_wyrm_and_its_variant_validate(wyrm, obsidian):
    assert [str(f) for f in wyrm.findings] == []
    assert [str(f) for f in obsidian.findings] == []


def test_huge_size_class_and_big(wyrm):
    from pixelforge.sheet import mirror
    size = wyrm.composer.rig.size
    assert (size.name, size.canvas, size.pivot, size.mirror_axis_x) == ("huge", 96, (47, 91), 47)
    for e, w in zip(wyrm.frames[("attack_bite", "e")], wyrm.frames[("attack_bite", "w")]):
        assert np.array_equal(mirror(e.image, 47)[0], w.image)
    for d in ("s", "e", "n"):
        solid = wyrm.frames[("idle", d)][0].sprite[..., 3] == 255
        ys, xs = np.flatnonzero(solid.any(axis=1)), np.flatnonzero(solid.any(axis=0))
        assert ys.max() == 91 and ys.max() - ys.min() + 1 >= 60, d  # over 3 times a hero's height
        assert xs.max() - xs.min() + 1 >= 60, d


@pytest.mark.parametrize("anim", ATTACKS)
def test_slow_heavy_attacks_telegraph_long(wyrm, style, anim):
    adef = wyrm.composer.anims[anim]
    profile = style.raw["combat"]["timing_profiles"]["boss"]
    holds = adef.flags.get("hold", frozenset())
    durations = [round(ms * profile["hold_scale"]) if i in holds else ms for i, ms in enumerate(adef.frames_ms)]
    assert tell_ms(adef, durations) >= 900, anim  # big and slow: almost a second of warning
    assert min(wyrm.composer.anims["walk"].frames_ms) >= 250


def test_the_wyrm_breathes_fire_and_sweeps_its_tail(wyrm, tmp_path):
    from pixelforge.export import export
    export(wyrm, tmp_path, gifs=False)
    pf = json.loads(next(tmp_path.rglob("cinderwyrm.json")).read_text())["meta"]["pixelforge"]
    fan = [e for e in pf["events"]["breath_e"] if e["type"] == "spawn"][0]
    assert fan["fx"] == "fireball" and fan["pattern"] == "fan" and fan["count"] == 5
    assert fan["point_name"] == "mouth"
    assert pf["size_class"] == "huge" and pf["timing_profile"] == "boss"
    for d in ("s", "n"):  # the sweep leaves a white trail where the tail went
        frames = wyrm.frames[("attack_tail", d)]
        assert (frames[2].owner == SMEAR).sum() > 30 and (frames[3].owner == SMEAR).any(), d
    bite = wyrm.frames[("attack_bite", "e")]
    mx, my = bite[2].points["mouth"]
    (x, y, w, h), = bite[2].hitboxes
    assert x <= mx < x + w and y <= my < y + h  # the bite hits where the jaws are


def test_the_obsidian_wyrm_is_a_family_recolor(wyrm, obsidian):
    a = wyrm.frames[("idle", "e")][0].sprite
    b = obsidian.frames[("idle", "e")][0].sprite
    assert np.array_equal(a[..., 3], b[..., 3])
    assert not np.array_equal(a[..., :3], b[..., :3])
    assert obsidian.recipe.raw["family"] == wyrm.recipe.raw["family"] == "cinderwyrm"
