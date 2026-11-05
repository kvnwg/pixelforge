"""Swing trails (COMBAT.md section 3): every swing leaves a white trail in fx_ramps.swing on its
strike frame, and it lingers one shade dimmer on the next frame, then is gone."""

from __future__ import annotations

import pytest

from pixelforge.build import build
from pixelforge.color import parse_hex
from pixelforge.compose import SMEAR

CASES = [  # recipe, animation, strike frame: a sword, a mace, a fist, a drawn club, a big club
    ("knight", "attack_slash", 2), ("knight", "attack_heavy", 3), ("orc", "attack_slash", 2),
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
