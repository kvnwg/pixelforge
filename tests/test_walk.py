"""Phase 3b: the walk cycle (ANIMATION_SPEC.md section 5)."""

from __future__ import annotations

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.color import parse_hex


@pytest.fixture(scope="module")
def girl(root, style):
    return build(root, "anchor_girl", style=style)


def test_walk_has_four_frames_everywhere(girl):
    for d in ("s", "e", "n", "w"):
        assert [f.duration for f in girl.frames[("walk", d)]] == [130] * 4


def test_walk_bobs_one_pixel_on_passing_frames(girl):
    rig = girl.composer.rig
    for d in ("s", "e", "n"):
        heads = [rig.anchor("walk", d, i, "head")[1] for i in range(4)]
        assert [h - heads[0] for h in heads] == [0, -1, 0, -1], d


def test_planted_feet_follow_the_ground(girl, style):
    """Facing e the planted foot moves back exactly the stride (10 px per cycle); facing s and n
    it stays put. The validator's W1 checks the pixels; this checks the plan."""
    rig = girl.composer.rig
    stride = style.raw["animations"]["walk"]["stride_px"]["e"]
    assert sum(stride) == 10
    for i in range(4):
        j = (i + 1) % 4
        a, b = rig.points("walk", "e", i), rig.points("walk", "e", j)
        for foot in set(a["planted"]) & set(b["planted"]):
            assert a[foot][0] - b[foot][0] == stride[i] and a[foot][1] == b[foot][1] == 27
        for d in ("s", "n"):
            a, b = rig.points("walk", d, i), rig.points("walk", d, j)
            for foot in set(a["planted"]) & set(b["planted"]):
                assert a[foot] == b[foot]
    assert not [f for f in girl.findings if f.rule == "W1"]


def test_near_and_far_legs_use_different_leather(girl, style):
    ramp = [parse_hex(c) for c in style.materials["leather"].base]
    for f in girl.frames[("walk", "e")]:
        legs = next(l for l in f.layers if l.slot == "legs_wear").image
        colors = {tuple(int(v) for v in px[:3]) for px in legs[legs[..., 3] == 255]}
        assert ramp[0] in colors and ramp[2] in colors, f.index  # dark far leg, light near leg


def test_contact_frames_open_the_stride(girl):
    def leg_span(f):
        rows = f.sprite[25:28, :, 3] == 255
        xs = np.flatnonzero(rows.any(axis=0))
        return int(xs.max() - xs.min())
    e = girl.frames[("walk", "e")]
    assert leg_span(e[0]) > leg_span(e[1]) and leg_span(e[2]) > leg_span(e[3])


def test_walk_exports_its_stride(root, style, tmp_path):
    from pixelforge.export import aseprite_json
    data = aseprite_json(build(root, "anchor_girl", style=style, validate=False), "x.png")
    assert data["meta"]["pixelforge"]["stride_px"] == {"walk_e": [3, 2, 3, 2], "walk_w": [3, 2, 3, 2]}
