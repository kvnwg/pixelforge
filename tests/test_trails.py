"""Swing trails (COMBAT.md section 3): every swing leaves a white trail in fx_ramps.swing on its
strike frame, and it lingers one shade dimmer on the next frame, then is gone."""

from __future__ import annotations

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.color import parse_hex
from pixelforge.compose import SMEAR

CASES = [  # recipe, animation, strike frame: a sword, a mace, a fist, a drawn club, a big club
    # (the humanoid's attack_heavy is the whirlwind, whose ring runs through every spin frame:
    # tests/test_whirlwind.py)
    ("knight", "attack_slash", 2), ("orc", "attack_slash", 2),
    ("anchor_girl", "attack_slash", 2), ("goblin", "attack_slash", 2), ("ogre", "attack_heavy", 3),
]


def trail_colors(f):
    return {tuple(int(v) for v in px[:3]) for px in f.sprite[f.owner == SMEAR]}


@pytest.mark.parametrize("name, anim, strike", CASES)
def test_every_swing_leaves_a_white_trail_that_lingers(root, style, name, anim, strike):
    rim, mid, core = (parse_hex(c) for c in style.raw["fx_ramps"]["swing"])
    b = build(root, name, style=style)
    for d in ("s", "e", "n", "w"):
        frames = b.frames[(anim, d)]
        hit, after = frames[strike], frames[strike + 1]
        assert core in trail_colors(hit) and trail_colors(hit) <= {rim, mid, core}, d
        assert trail_colors(after) and trail_colors(after) <= {rim, mid}, d  # a shade dimmer
        for i, f in enumerate(frames):
            if i not in (strike, strike + 1):
                assert not (f.owner == SMEAR).any(), (d, i)  # only on the swing, never on a tell
        assert not (hit.sprite[..., 3][hit.owner == SMEAR] != 255).any()


def test_the_trail_is_brighter_than_any_character_color(style):
    from pixelforge.color import hex_to_oklch
    core = hex_to_oklch(style.raw["fx_ramps"]["swing"][-1])
    assert core.L > style.raw["constraints"]["oklch_L_range"][1]  # an FX color: it pops


def test_a_sword_slash_sweeps_across_the_body(root, style):
    """The human's request (2026-11-05): slashes go across the body and leave an arc. Facing s the
    blade starts high on the weapon side, sweeps in front of the body to the far side, and its
    trail crosses the body from one side to the other (drawn over it); the follow-through ends low
    on the far side."""
    knight = build(root, "knight", style=style)
    axis = knight.composer.rig.size.pivot[0]
    windup, strike, after = (knight.frames[("attack_slash", "s")][i] for i in (1, 2, 3))
    assert windup.points["weapon_tip"][0] < axis  # raised on the weapon side
    assert strike.points["weapon_tip"][0] > axis + 3 and after.points["weapon_tip"][0] > axis  # far side
    trail = strike.owner == SMEAR
    ys, xs = np.nonzero(trail)
    assert xs.min() < axis - 5 and xs.max() > axis + 5  # from one side to the other
    body = strike.slot_mask("body", "torso_wear", "legs_wear")
    under = knight.frames[("attack_slash", "s")][0].slot_mask("body", "torso_wear", "legs_wear")
    assert (trail & under).sum() > 5  # it passes over the body
    for d in ("e", "n"):  # the other views keep their own arcs, over the head or in front
        f = knight.frames[("attack_slash", d)][2]
        assert (f.owner == SMEAR).sum() > 20, d
    del body, ys
