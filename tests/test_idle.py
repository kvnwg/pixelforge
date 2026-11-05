"""Phase 3a: idle breathing, hair lag and blink (ANIMATION_SPEC.md sections 3 and 4)."""

from __future__ import annotations

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.bundle import write_bundle


@pytest.fixture(scope="module")
def girl(root, style):
    return build(root, "anchor_girl", style=style)


def layer(frame, slot):
    return next((l for l in frame.layers if l.slot == slot), None)


IDLE_MS = [360, 100, 100, 260, 140, 140]
WAVE = {"torso": [0, 1, 1, 1, 0, 0], "head": [0, 0, 1, 1, 1, 0], "hand_near": [0, 0, 0, 1, 1, 1]}


def test_idle_is_a_six_frame_wave_with_gravity_timing(girl, style):
    """MOTION.md rules 1 and 2: six frames, the settle quicker than the rise, the top held."""
    assert style.raw["animations"]["idle"]["frames_ms"] == IDLE_MS
    for d in ("s", "e", "n", "w"):
        assert [f.duration for f in girl.frames[("idle", d)]] == IDLE_MS


def test_legs_never_move_in_idle(girl):
    for d in ("s", "e", "n"):
        frames = girl.frames[("idle", d)]
        legs = [layer(f, "legs_wear").image for f in frames]
        feet_rows = [layer(f, "body").image[26:] for f in frames]
        for i in range(1, len(frames)):
            assert np.array_equal(legs[0], legs[i]), (d, i)
            assert np.array_equal(feet_rows[0], feet_rows[i]), (d, i)


def test_the_breath_travels_chest_then_head_then_hands(girl):
    rig = girl.composer.rig
    for d in ("s", "e", "n"):
        for point, wave in WAVE.items():
            ys = [rig.anchor("idle", d, i, point)[1] for i in range(len(IDLE_MS))]
            assert [y - ys[0] for y in ys] == wave, (d, point)


def test_the_neck_stretches_instead_of_tearing(girl):
    """Frame 1 drops the chest under a still head: the body has no empty row between them."""
    for d in ("s", "e", "n"):
        body = layer(girl.frames[("idle", d)][1], "body").image[..., 3] == 255
        rows = np.flatnonzero(body.any(axis=1))
        assert list(rows) == list(range(rows.min(), rows.max() + 1)), d


def test_follow_through_trails_catches_up_and_overshoots():
    """MOTION.md rule 5: a trailing part's coordinate from its anchor now, 1, 2 and 3 frames ago."""
    from pixelforge.compose import _follow
    assert _follow([1, 0, 0, 0]) == 0   # the anchor moves: 1 px behind
    assert _follow([5, 0, 0, 0]) == 4   # never more than 1 px behind
    assert _follow([1, 1, 0, 0]) == 1   # it stops: caught up
    assert _follow([1, 1, 1, 0]) == 2   # a frame later: 1 px past
    assert _follow([1, 1, 1, 1]) == 1   # settled
    assert _follow([1, 1, 1, 0], held=True) == 1  # a held last frame never overshoots


@pytest.mark.parametrize("d, slot", [("s", "hair_locks"), ("e", "hair_back"), ("n", "hair_back")])
def test_loose_hair_follows_through(girl, d, slot):
    frames = girl.frames[("idle", d)]
    head = [girl.composer.rig.anchor("idle", d, i, "head")[1] - 11 for i in range(len(frames))]
    hair = [layer(f, slot).offset for f in frames]
    assert [dy for _, dy in hair] == [0, -1, 0, 1, 2, 1], d  # trails the head and swings past it
    for i, f in enumerate(frames):
        assert abs(hair[i][1] - head[i]) <= 1, (d, i)
        assert layer(f, "hair_front").offset == (0, head[i]), (d, i)


def test_blink_closes_the_eyes(girl, style):
    assert ("blink", "n") not in girl.frames
    lid = tuple(int(style.materials["skin"].base[0][i:i + 2], 16) for i in (1, 3, 5))
    for d in ("s", "e", "w"):
        blink = girl.frames[("blink", d)][0]
        idle = girl.frames[("idle", d)][0]
        eyes = idle.slot_mask("eyes")
        assert eyes.sum() == (2 if d == "s" else 1)
        assert all(tuple(px[:3]) == lid for px in blink.image[eyes])
        assert np.array_equal(blink.image[~eyes], idle.image[~eyes])
        assert blink.duration == 100


def test_preview_bundle_is_self_contained(root, tmp_path):
    out = write_bundle(root, tmp_path / "preview.html")
    text = out.read_text()
    assert "window.PIXELFORGE_BUNDLE" in text and "<title>" in text
    assert "<!doctype" not in text.lower() and "<html" not in text.lower() and "<body" not in text.lower()
    assert "../../out/" in text  # the local fallback stays, unused when the bundle is present
    assert text.startswith('<meta charset="utf-8">')  # reads right opened straight from disk


def test_armor_stretches_with_the_neck(root, style):
    """Idle frame 1 drops the chest under a still helmet: the plate's gorget row repeats up into
    the gap (no line of skin), in the dark shade facing n like the body's nape."""
    knight = build(root, "knight", style=style)
    for d in ("s", "e", "n"):
        f = knight.frames[("idle", d)][1]
        plate = layer(f, "torso_wear").image
        solid = plate[..., 3] == 255
        assert solid[20].any() and (solid[20] >= solid[21]).all(), d
        body = next(i for i, l in enumerate(f.layers) if l.slot == "body")
        assert not (f.owner[20] == body).any(), d  # no skin shows between helmet and plate
        if d == "n":
            assert len({tuple(px[:3]) for px in plate[20][solid[20]]}) == 1  # one shadow shade
    rest, low = (layer(knight.frames[("idle", "s")][i], "torso_wear").image for i in (0, 3))
    assert np.array_equal(low[1:], rest[:-1])  # once the head follows, the plate just moves down
