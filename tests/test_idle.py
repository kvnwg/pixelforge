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


def test_idle_has_four_frames_in_every_direction(girl):
    for d in ("s", "e", "n", "w"):
        assert [f.duration for f in girl.frames[("idle", d)]] == [450, 150, 450, 150]


def test_legs_never_move_in_idle(girl):
    for d in ("s", "e", "n"):
        frames = girl.frames[("idle", d)]
        legs = [layer(f, "legs_wear").image for f in frames]
        feet_rows = [layer(f, "body").image[26:] for f in frames]
        for i in range(1, 4):
            assert np.array_equal(legs[0], legs[i]), (d, i)
            assert np.array_equal(feet_rows[0], feet_rows[i]), (d, i)


def test_upper_body_breathes_one_pixel(girl):
    for d in ("s", "e", "n"):
        heads = [girl.composer.rig.anchor("idle", d, i, "head")[1] for i in range(4)]
        assert [h - heads[0] for h in heads] == [0, 1, 1, 0], d


@pytest.mark.parametrize("d, slot", [("s", "hair_locks"), ("e", "hair_back"), ("n", "hair_back")])
def test_loose_hair_lags_one_frame(girl, d, slot):
    frames = girl.frames[("idle", d)]
    head_dy = [girl.composer.rig.anchor("idle", d, i, "head")[1] - 11 for i in range(4)]
    for i, f in enumerate(frames):
        assert layer(f, slot).offset == (0, head_dy[i - 1]), (d, i)  # previous frame, wrapping
        assert layer(f, "hair_front").offset == (0, head_dy[i]), (d, i)


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
