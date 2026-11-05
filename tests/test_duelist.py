"""The Ashen Duelist (MONSTERS.md section 5.9): a tall, quick humanoid elite on the medium canvas."""

from __future__ import annotations

import json

import numpy as np
import pytest

from pixelforge.anim import tell_ms
from pixelforge.build import build
from pixelforge.compose import SMEAR


@pytest.fixture(scope="module")
def duelist(root, style):
    return build(root, "ashen_duelist", style=style)


def test_the_duelist_validates(duelist):
    assert [str(f) for f in duelist.findings] == []


def test_tall_on_the_medium_canvas(duelist):
    size = duelist.composer.rig.size
    assert (size.name, size.canvas, size.pivot) == ("medium", 48, (23, 43))
    for d in ("s", "e", "n"):
        solid = duelist.frames[("idle", d)][0].sprite[..., 3] == 255
        ys = np.flatnonzero(solid.any(axis=1))
        assert ys.max() == 43 and ys.max() - ys.min() + 1 >= 36, d  # twice a hero's 18 rows


@pytest.mark.parametrize("anim", ["attack_slash", "attack_lunge"])
def test_quick_but_fair(duelist, style, anim):
    """Short strikes and a fast walk, while the tell still meets the elite minimum."""
    adef = duelist.composer.anims[anim]
    profile = style.raw["combat"]["timing_profiles"]["elite"]
    durations = [f.duration for f in duelist.frames[(anim, "e")]]
    assert tell_ms(adef, durations) >= profile["telegraph_min_ms"]
    active = sorted(adef.flags["active"])
    assert durations[active[0]] <= 60  # the strike itself is a blink
    assert max(duelist.composer.anims["walk"].frames_ms) <= 100


def test_the_lunge_dashes_and_the_dodge_steps_back(duelist, tmp_path):
    from pixelforge.export import export
    export(duelist, tmp_path, gifs=False)
    pf = json.loads(next(tmp_path.rglob("ashen_duelist.json")).read_text())["meta"]["pixelforge"]
    assert sum(pf["root_motion"]["attack_lunge_e"]) >= 12
    assert sum(pf["root_motion"]["dodge_e"]) < 0
    assert pf["timing_profile"] == "elite" and pf["size_class"] == "medium"


def test_the_glaive_sweeps_across_the_body(duelist):
    strike = duelist.frames[("attack_slash", "s")][2]
    trail = strike.owner == SMEAR
    xs = np.flatnonzero(trail.any(axis=0))
    axis = duelist.composer.rig.size.pivot[0]
    assert xs.min() < axis - 6 and xs.max() > axis + 6  # from one side to the other, in front
    for d in ("e", "n"):
        assert (duelist.frames[("attack_slash", d)][2].owner == SMEAR).sum() > 15, d
    lunge = duelist.frames[("attack_lunge", "e")]
    tip = lunge[2].points["weapon_tip"]
    (x, y, w, h), = lunge[2].hitboxes
    assert x <= tip[0] < x + w and y <= tip[1] < y + h  # the thrust hits at the point
