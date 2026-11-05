"""The walk and the run (ANIMATION_SPEC.md section 5, MOTION.md): 8-frame cycles with a
triangle bob, planted feet locked to the ground, and a run with a lean and flight frames."""

from __future__ import annotations

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.color import parse_hex
from pixelforge.compose import EMPTY, OUTLINE

WALK_MS = [100, 80, 90, 80, 100, 80, 90, 80]
RUN_MS = [70, 60, 70, 80, 70, 60, 70, 80]
GAITS = {"walk": (WALK_MS, 12), "run": (RUN_MS, 30)}  # durations, ground px per cycle (facing e)


@pytest.fixture(scope="module")
def girl(root, style):
    return build(root, "anchor_girl", style=style)


@pytest.mark.parametrize("anim", GAITS)
def test_gaits_have_eight_uneven_frames_everywhere(girl, style, anim):
    ms, _ = GAITS[anim]
    assert style.raw["animations"][anim]["frames_ms"] == ms
    assert len(set(ms)) > 1  # MOTION.md rule 2: an even beat reads mechanical
    for d in ("s", "e", "n", "w"):
        assert [f.duration for f in girl.frames[(anim, d)]] == ms


@pytest.mark.parametrize("anim", GAITS)
def test_the_bob_is_low_on_down_and_high_on_up(girl, anim):
    """Contact, down (lowest), pass, up (highest), twice: the head's path is a triangle wave."""
    rig = girl.composer.rig
    for d in ("s", "e", "n"):
        heads = [rig.anchor(anim, d, i, "head")[1] for i in range(8)]
        assert [h - heads[0] for h in heads] == [0, 1, 0, -1, 0, 1, 0, -1], (anim, d)


@pytest.mark.parametrize("anim", GAITS)
def test_planted_feet_follow_the_ground(girl, style, anim):
    """Facing e a planted foot moves back exactly the stride; facing s and n it stays put. The
    validator's W1 checks the pixels; this checks the plan."""
    rig = girl.composer.rig
    stride = style.raw["animations"][anim]["stride_px"]["e"]
    assert sum(stride) == GAITS[anim][1]
    for i in range(8):
        j = (i + 1) % 8
        a, b = rig.points(anim, "e", i), rig.points(anim, "e", j)
        for foot in set(a["planted"]) & set(b["planted"]):
            assert a[foot][0] - b[foot][0] == stride[i] and a[foot][1] == b[foot][1] == 27
        for d in ("s", "n"):
            a, b = rig.points(anim, d, i), rig.points(anim, d, j)
            for foot in set(a["planted"]) & set(b["planted"]):
                assert a[foot] == b[foot]
    assert not [f for f in girl.findings if f.rule == "W1"]


def test_the_run_covers_ground_three_times_faster(style):
    speed = {a: sum(style.raw["animations"][a]["stride_px"]["e"]) / sum(GAITS[a][0]) * 1000
             for a in GAITS}
    assert 15 <= speed["walk"] <= 20 and 50 <= speed["run"] <= 60  # px/s; Rolling Knight runs
    assert speed["run"] >= 3 * speed["walk"]


def test_the_run_leaves_the_ground_on_its_flight_frames(girl, style):
    assert style.raw["animations"]["run"]["airborne_frames"] == [3, 7]
    for d in ("s", "e", "n", "w"):
        for i, f in enumerate(girl.frames[("run", d)]):
            drawn = (f.owner != EMPTY) & (f.owner != OUTLINE)
            on_ground = bool(drawn[27].any())
            assert on_ground == (i not in (3, 7)), (d, i)


def test_the_run_leans_into_its_facing(girl):
    rig = girl.composer.rig
    for i in range(8):
        walk, run = rig.anchor("walk", "e", i, "head"), rig.anchor("run", "e", i, "head")
        assert run[0] == walk[0] + 1, i
    for d in ("s", "n"):  # facing the viewer or away, the lean is invisible: no sideways drift
        assert {rig.anchor("run", d, i, "head")[0] for i in range(8)} == {rig.anchor("idle", d, 0, "head")[0]}


def test_arms_swing_against_the_legs(girl):
    """Facing e the near hand swings back while the near foot leads and forward while it trails,
    at the extremes on the contact frames (Pixelblog 50), passing the rest pose as the legs cross."""
    rig = girl.composer.rig
    rest = rig.points("idle", "e", 0)
    rest = rest["hand_near"][0] - rest["hand_far"][0]
    for anim in GAITS:
        swung = 0
        for i in range(8):
            p = rig.points(anim, "e", i)
            leg = p["foot_near"][0] - p["foot_far"][0]
            arm = p["hand_near"][0] - p["hand_far"][0] - rest
            assert leg * arm <= 0, (anim, i)
            swung += leg * arm < 0
        assert swung >= 6, anim
    for contact in (0, 4):
        p = rig.points("walk", "e", contact)
        assert p["hand_near"][0] - p["hand_far"][0] - rest == (-2 if contact == 0 else 2)


def test_near_and_far_legs_use_different_leather(girl, style):
    ramp = [parse_hex(c) for c in style.materials["leather"].base]
    for anim in GAITS:
        for f in girl.frames[(anim, "e")]:
            legs = next(l for l in f.layers if l.slot == "legs_wear").image
            colors = {tuple(int(v) for v in px[:3]) for px in legs[legs[..., 3] == 255]}
            assert ramp[0] in colors and ramp[2] in colors, (anim, f.index)  # dark far, light near


def test_contact_frames_open_the_stride(girl):
    def leg_span(f):
        rows = f.sprite[24:28, :, 3] == 255
        xs = np.flatnonzero(rows.any(axis=0))
        return int(xs.max() - xs.min())
    for anim in GAITS:
        e = girl.frames[(anim, "e")]
        for contact, passing in ((0, 2), (4, 6)):
            assert leg_span(e[contact]) > leg_span(e[passing]), anim


def test_gaits_export_their_stride(root, style):
    from pixelforge.export import aseprite_json
    data = aseprite_json(build(root, "anchor_girl", style=style, validate=False), "x.png")
    walk, run = [2, 1, 2, 1, 2, 1, 2, 1], [4, 4, 4, 3, 4, 4, 4, 3]
    assert data["meta"]["pixelforge"]["stride_px"] == {"walk_e": walk, "walk_w": walk,
                                                      "run_e": run, "run_w": run}
