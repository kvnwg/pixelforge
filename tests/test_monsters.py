"""Phase 7: monster rigs (MONSTERS.md section 5): per-rig animations, the slime, bat and wolf."""

from __future__ import annotations

import numpy as np
import pytest

from pixelforge.anim import load_anims
from pixelforge.build import build


@pytest.fixture(scope="module")
def slime(root, style):
    return build(root, "slime", style=style)


def bbox(frame):
    body = frame.owner >= 0
    ys, xs = np.nonzero(body)
    return xs.min(), ys.min(), xs.max(), ys.max()


def test_rigs_have_their_own_animations(style):
    humanoid, blob = load_anims(style, "humanoid"), load_anims(style, "blob")
    assert humanoid["idle"].frames_ms == (450, 150, 450, 150)
    assert blob["idle"].frames_ms == (200, 150, 200, 150)
    assert "attack_spit" in blob and "attack_spit" not in humanoid
    assert blob["combat_idle"].frames_ms == blob["idle"].frames_ms  # an alias of idle
    assert blob["combat_idle"].source_frame(2) == ("idle", 2)


def test_slime_validates_on_the_enemy_profile(slime):
    assert slime.recipe.timing_profile == "enemy"
    assert [str(f) for f in slime.findings] == []


def test_slime_squash_and_stretch_are_redrawn(slime):
    base, squash, _, stretch = slime.frames[("idle", "s")]
    bx0, by0, bx1, by1 = bbox(base)
    sx0, sy0, sx1, sy1 = bbox(squash)
    tx0, ty0, tx1, ty1 = bbox(stretch)
    assert sx1 - sx0 == bx1 - bx0 + 2 and sy1 - sy0 < by1 - by0  # 2 px wider, shorter
    assert tx1 - tx0 == bx1 - bx0 - 2 and ty1 - ty0 > by1 - by0  # 2 px narrower, taller
    for f in (base, squash, stretch):
        assert bbox(f)[3] == 27  # every grounded shape sits on the baseline


def test_slime_eyes_face_the_view(slime):
    def eyes(f):
        return [(int(x), int(y)) for y, x in zip(*np.nonzero(f.slot_mask("eyes")))]
    s, e, n = (slime.frames[("idle", d)][0] for d in ("s", "e", "n"))
    assert len(eyes(s)) == 2 and abs(eyes(s)[0][0] - eyes(s)[1][0]) == 4  # 3 px apart
    assert min(x for x, _ in eyes(e)) > min(x for x, _ in eyes(s))  # shifted forward
    assert eyes(n) == []
    assert s.slot_mask("gloss").sum() == 2


def test_slime_hop_leaves_the_ground(slime):
    frames = slime.frames[("move", "e")]
    assert max(27 - bbox(f)[3] for f in frames) >= 3  # the peak rises 3 to 4 px
    for f in frames:
        bottom = bbox(f)[3]
        if "airborne" in f.flags:
            assert bottom < 27
            if 27 - bottom >= 2:  # the shadow narrows 1 px a side for every 2 px of lift
                assert (f.image[28, :, 3] == 70).sum() < (frames[0].image[28, :, 3] == 70).sum()
        else:
            assert bottom == 27


def test_slime_spits_from_its_mouth(slime):
    f = slime.frames[("attack_spit", "e")][2]
    assert f.points["mouth"][0] >= bbox(f)[2] - 1  # at the front edge facing e
    pf_events = [e for e in slime.composer.anims["attack_spit"].events if e["type"] == "spawn"]
    assert pf_events[0]["fx"] == "poison_glob"


@pytest.fixture(scope="module")
def bat(root, style):
    return build(root, "bat", style=style)


def test_bat_validates_and_hovers(bat):
    assert [str(f) for f in bat.findings] == []
    for f in bat.frames[("idle", "s")]:
        assert "airborne" in f.flags
        assert 27 - bbox(f)[3] >= 6  # the body floats about 7 px up
        shadow = np.nonzero(f.image[..., 3] == 70)
        assert set(shadow[0]) == {27, 28} and shadow[1].min() >= 12  # small, on the ground


def test_bat_wings_beat(bat):
    def wing_span(f):
        ys = np.nonzero(f.slot_mask("wings"))[0]
        return ys.min(), ys.max()
    up, mid, down, _ = (wing_span(f) for f in bat.frames[("idle", "s")])
    assert up[0] < mid[0] and down[1] > mid[1]  # tips raised, then swept below


def test_bat_falls_to_the_ground_when_it_dies(bat):
    last = bat.frames[("death", "s")][-1]
    assert "airborne" not in last.flags and bbox(last)[3] == 27
    full = np.nonzero(last.image[..., 3] == 70)
    assert full[1].min() < 12  # the default (full size) shadow once grounded


@pytest.fixture(scope="module")
def wolf(root, style):
    return build(root, "wolf", style=style)


def test_wolf_validates(wolf):
    assert [str(f) for f in wolf.findings] == []


def test_wolf_near_legs_are_lighter_than_far_legs(wolf, style):
    from pixelforge.color import parse_hex
    fur = [parse_hex(c) for c in style.materials["fur"].presets["gray"]]
    f = wolf.frames[("idle", "e")][0]
    leg_row = 25  # below the body, above the paws
    shades = {x: fur.index(tuple(int(v) for v in f.sprite[leg_row, x, :3]))
              for x in range(32) if f.owner[leg_row, x] >= 0}
    far = [shades[x] for x in (8, 9, 15, 16) if x in shades]
    near = [shades[x] for x in (10, 11, 17, 18) if x in shades]
    assert far and near and max(far) < max(near)


def test_wolf_tail_trails_the_body(wolf):
    c = wolf.composer
    tail = c.parts["tail"]
    idle = c.anims["idle"]
    # frame 1 lowers the body; the lagging tail is still where frame 0 put it
    assert c.offset(tail, idle, "e", 1)[1] == c.offset(tail, idle, "e", 0)[1]
    assert c.offset(tail, idle, "e", 2)[1] == c.offset(tail, idle, "e", 1)[1] + 1


def test_wolf_bite_reaches_ahead(wolf):
    f = wolf.frames[("attack_bite", "e")][2]
    x, y, w, h = f.hitboxes[0]
    assert x + w > bbox(f)[2] - 2  # in front of the snout
    w_frame = wolf.frames[("attack_bite", "w")][2]
    assert all(bx >= 0 for bx, *_ in w_frame.hitboxes)


def test_wolf_dies_on_its_side(wolf):
    last = wolf.frames[("death", "e")][-1]
    x0, y0, x1, y1 = bbox(last)
    assert x1 - x0 >= 18 and y1 - y0 <= 7 and y1 == 27  # long and low, on the ground


def test_roster_has_no_lookalikes_and_W7_fires_on_one(root, style, slime, bat, wolf):
    from dataclasses import replace
    from pathlib import Path
    from pixelforge.validate import roster_findings
    assert roster_findings([slime, bat, wolf]) == []
    twin = replace(slime, recipe=replace(slime.recipe, name="slime_twin", parts={"eyes": "slime"},
                                         path=Path(slime.recipe.path).with_name("slime_twin.yaml")))
    found = roster_findings([slime, twin])
    assert any(f.rule == "W7" for f in found)
