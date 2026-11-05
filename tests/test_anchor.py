"""style.json's anchor metadata agrees with the anchor images."""

from __future__ import annotations

import numpy as np

from pixelforge.color import parse_hex, to_hex

from .conftest import read_rgba


def test_anchor_uses_exactly_the_anchor_palette(style):
    img = read_rgba(style.anchor_file)
    assert img.shape == (style.canvas, style.canvas, 4)
    assert set(np.unique(img[..., 3])) <= {0, 255}
    used = {to_hex(p) for p in img[img[..., 3] == 255]}
    assert used == set(style.palette_anchor.values())


def test_anchor_bbox_eyes_and_hand_placed_outline(style):
    img = read_rgba(style.anchor_file)
    ys, xs = np.nonzero(img[..., 3])
    bbox = style.raw["anchor"]["bbox"]
    assert (xs.min(), ys.min(), xs.max(), ys.max()) == (bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"])
    assert ys.max() == style.baseline_y
    eye = parse_hex(style.materials["eyes"].base[0])
    for x, y in style.raw["anchor"]["eyes"]:
        assert tuple(img[y, x, :3]) == eye
    for x, y in style.hand_placed_outline:
        assert tuple(img[y, x]) == (*style.outline.rgb, 255)


def test_shadow_png_matches_the_style(style, root):
    shadow = read_rgba(root / "style" / "shadow.png")
    expected = np.zeros_like(shadow)
    for y, (x0, x1) in style.shadow.rows.items():
        expected[y, x0:x1 + 1] = (*style.outline.rgb, style.shadow.alpha)
    assert np.array_equal(shadow, expected)


def test_anchor_with_shadow_is_the_anchor_over_the_shadow(style, root):
    anchor = read_rgba(style.anchor_file)
    shadow = read_rgba(root / "style" / "shadow.png")
    combined = np.where(anchor[..., 3:] == 255, anchor, shadow)
    assert np.array_equal(read_rgba(root / "style" / "anchor_with_shadow.png"), combined)
