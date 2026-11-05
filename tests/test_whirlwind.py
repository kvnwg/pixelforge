"""The whirlwind (COMBAT.md, attack_heavy): Rolling Knight's Blade special as a spin. The body
coils a quarter turn away (the tell), spins through s, e, n and w with the blade pointing where
it faces inside a white ring, sweeps once more across the front and settles."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from pixelforge.anim import tell_ms
from pixelforge.build import build
from pixelforge.color import parse_hex
from pixelforge.compose import SMEAR

SPIN = (2, 3, 4, 5)
ORDER = {"s": "senw", "e": "enws", "n": "nwse", "w": "wsen"}  # counter-clockwise from above


@pytest.fixture(scope="module")
def knight(root, style):
    return build(root, "knight", style=style)


def test_the_body_turns_through_every_view(knight):
    c = knight.composer
    adef = c.anims["attack_heavy"]
    for d, order in ORDER.items():
        if d == "w":  # west mirrors east: e, n, w, s seen in a mirror
            continue
        assert "".join(c.view(adef, d, i) for i in SPIN) == order, d
        assert c.view(adef, d, 1) not in (d, order[1])  # the coil turns the other way first
        assert c.view(adef, d, 0) == d and c.view(adef, d, 8) == d


def test_a_white_ring_surrounds_the_body_while_it_spins(knight, style):
    rim, mid, core = (parse_hex(x) for x in style.raw["fx_ramps"]["swing"])
    for d in ("s", "e", "n", "w"):
        frames = knight.frames[("attack_heavy", d)]
        for i in SPIN:
            f = frames[i]
            ys, xs = np.nonzero(f.owner == SMEAR)
            assert xs.min() <= 6 and xs.max() >= 24, (d, i)  # out past both sides
            assert ys.min() <= 18 and ys.max() >= 26, (d, i)  # behind the back, before the feet
            colors = {tuple(int(v) for v in px[:3]) for px in f.sprite[f.owner == SMEAR]}
            assert colors == {rim, mid, core}, (d, i)  # a comet: brightest at the blade
        assert not (frames[0].owner == SMEAR).any() and not (frames[1].owner == SMEAR).any()
        fade = {tuple(int(v) for v in px[:3]) for px in frames[7].sprite[frames[7].owner == SMEAR]}
        assert fade and core not in fade, d  # the release lingers a shade dimmer
        assert not (frames[8].owner == SMEAR).any(), d


def test_the_spin_loops_seamlessly(knight, style):
    """The ring's brightest part steps a quarter turn per frame the same way round, from the last
    spin frame back to the first too, so the game can repeat loop_frames for the whole channel."""
    core = np.array(parse_hex(style.raw["fx_ramps"]["swing"][2]), np.uint8)
    for d in ("s", "e", "n"):
        angles = []
        for i in SPIN:
            f = knight.frames[("attack_heavy", d)][i]
            mask = (f.owner == SMEAR) & np.all(f.sprite[..., :3] == core, axis=-1)
            ys, xs = np.nonzero(mask)
            angles.append(math.degrees(math.atan2((ys.mean() - 22) * 2.2, xs.mean() - 15)))
        steps = [(angles[(k + 1) % 4] - angles[k] + 540) % 360 - 180 for k in range(4)]
        assert all(-135 <= s <= -45 for s in steps), (d, [round(s) for s in steps])


def test_it_hits_all_around_and_tells_like_a_heavy(knight, style, tmp_path):
    from pixelforge.export import export
    for d in ("s", "e", "n", "w"):
        for i in (*SPIN, 6):
            (x, y, w, h), *_ = knight.frames[("attack_heavy", d)][i].hitboxes
            assert x <= 4 and x + w >= 27 and y <= 16 and y + h >= 28, (d, i)
    adef = knight.composer.anims["attack_heavy"]
    for name in ("enemy", "elite"):
        profile = style.raw["combat"]["timing_profiles"][name]
        holds = adef.flags.get("hold", frozenset())
        ms = [round(t * profile["hold_scale"]) if i in holds else t for i, t in enumerate(adef.frames_ms)]
        assert tell_ms(adef, ms) >= profile["telegraph_min_ms"], name
    export(knight, tmp_path, gifs=False)
    pf = json.loads(next(tmp_path.rglob("knight.json")).read_text())["meta"]["pixelforge"]
    assert all(pf["loop_frames"][f"attack_heavy_{d}"] == list(SPIN) for d in "senw")


@pytest.mark.parametrize("name", ["anchor_girl", "dwarf", "orc", "rk_guardian"])
def test_every_holder_spins_with_its_own_weapon(root, style, name):
    """Fists draw a tighter ring than a blade or a mace; every humanoid that has the heavy
    validates with it."""
    b = build(root, name, style=style)
    assert [str(f) for f in b.findings] == []
    f = b.frames[("attack_heavy", "e")][3]
    xs = np.nonzero(f.owner == SMEAR)[1]
    width = xs.max() - xs.min()
    assert width >= (12 if name == "anchor_girl" else 20), (name, width)
