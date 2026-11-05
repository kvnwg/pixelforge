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
    for f in frames:
        bottom = bbox(f)[3]
        if "airborne" in f.flags:
            assert 27 - bottom >= 3
            # the shadow under a jump is narrower (row 28 shows below every shape)
            assert (f.image[28, :, 3] == 70).sum() < (frames[0].image[28, :, 3] == 70).sum()
        else:
            assert bottom == 27


def test_slime_spits_from_its_mouth(slime):
    f = slime.frames[("attack_spit", "e")][2]
    assert f.points["mouth"][0] >= bbox(f)[2] - 1  # at the front edge facing e
    pf_events = [e for e in slime.composer.anims["attack_spit"].events if e["type"] == "spawn"]
    assert pf_events[0]["fx"] == "poison_glob"
