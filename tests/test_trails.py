"""Swing trails (COMBAT.md section 3): every swing leaves a white trail in fx_ramps.swing on its
strike frame, and it lingers one shade dimmer on the next frame, then is gone."""

from __future__ import annotations

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.color import parse_hex
from pixelforge.compose import SMEAR

CASES = [  # recipe, animation, strike frames: a sword, a mace, a fist, a drawn club, a big club.
    # The humanoid's Cleave strikes over two frames (the swing and the strike); its attack_heavy
    # is the whirlwind, whose ring runs through every spin frame (tests/test_whirlwind.py).
    ("knight", "attack_slash", (2, 3)), ("orc", "attack_slash", (2, 3)),
    ("anchor_girl", "attack_slash", (2, 3)), ("goblin", "attack_slash", (2,)),
    ("ogre", "attack_heavy", (3,)),
]


def trail_colors(f):
    return {tuple(int(v) for v in px[:3]) for px in f.sprite[f.owner == SMEAR]}


@pytest.mark.parametrize("name, anim, strikes", CASES)
def test_every_swing_leaves_a_white_trail_that_lingers(root, style, name, anim, strikes):
    rim, mid, core = (parse_hex(c) for c in style.raw["fx_ramps"]["swing"])
    b = build(root, name, style=style)
    for d in ("s", "e", "n", "w"):
        frames = b.frames[(anim, d)]
        after = frames[strikes[-1] + 1]
        for strike in strikes:
            hit = frames[strike]
            assert core in trail_colors(hit) and trail_colors(hit) <= {rim, mid, core}, (d, strike)
            assert not (hit.sprite[..., 3][hit.owner == SMEAR] != 255).any()
        assert trail_colors(after) and trail_colors(after) <= {rim, mid}, d  # a shade dimmer
        for i, f in enumerate(frames):
            if i not in (*strikes, strikes[-1] + 1):
                assert not (f.owner == SMEAR).any(), (d, i)  # only on the swing, never on a tell


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
    windup, strike, after = (knight.frames[("attack_slash", "s")][i] for i in (1, 3, 4))
    assert windup.points["weapon_tip"][0] < axis  # raised on the weapon side
    assert strike.points["weapon_tip"][0] > axis + 3 and after.points["weapon_tip"][0] > axis  # far side
    trail = strike.owner == SMEAR
    ys, xs = np.nonzero(trail)
    assert xs.min() < axis - 5 and xs.max() > axis + 5  # from one side to the other
    body = strike.slot_mask("body", "torso_wear", "legs_wear")
    under = knight.frames[("attack_slash", "s")][0].slot_mask("body", "torso_wear", "legs_wear")
    assert (trail & under).sum() > 5  # it passes over the body
    for d in ("e", "n"):  # the other views keep their own arcs, over the head or in front
        f = knight.frames[("attack_slash", d)][3]
        assert (f.owner == SMEAR).sum() > 40, d
    del body, ys


def test_the_cleave_is_wide_and_strikes_over_two_frames(root, style):
    """The human, 2026-11-05: "even the slash itself isn't dramatic enough". Target (COMBAT.md):
    a coil with the blade far back, a swing frame where the blade is a blur over the first half
    of the arc, then a strike whose crescent is wider than the body, thick toward the blade,
    across the front of the body facing e."""
    knight = build(root, "knight", style=style)
    frames = knight.frames[("attack_slash", "e")]
    coil, swing, strike = frames[1], frames[2], frames[3]
    assert coil.points["weapon_tip"][0] <= 5  # cocked level behind the shoulders
    assert not swing.slot_mask("held_near").any()  # the blade is a blur: only its trail shows
    trail = strike.owner == SMEAR
    ys, xs = np.nonzero(trail)
    assert xs.max() - xs.min() >= 20  # wider than the body (about 7 px)
    body = np.zeros_like(trail)
    for layer in strike.layers:  # what the strike frame draws under its trail
        if not layer.slot.startswith("held"):
            body |= layer.image[..., 3] == 255
    assert (trail & body).sum() > 10  # it cuts across the front of the body
    assert trail[:, xs.max() - 3].sum() >= 3  # thick toward the blade
    assert (swing.owner == SMEAR).sum() < trail.sum()  # the swing frame shows half the arc
