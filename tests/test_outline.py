"""The outline pass (ARCHITECTURE.md section 10). The anchor reproduction must be exact."""

from __future__ import annotations

import numpy as np
import pytest

from pixelforge.outline import apply_outline, outline, outline_colored, strip_outline

from .conftest import read_rgba

INK = (58, 38, 58)  # tests below use a fixed color; the anchor tests read it from style.json


def blank(h: int = 12, w: int = 12) -> np.ndarray:
    return np.zeros((h, w, 4), np.uint8)


def paint(img: np.ndarray, pixels, rgb=(200, 150, 130)) -> np.ndarray:
    for x, y in pixels:
        img[y, x] = (*rgb, 255)
    return img


def coords(mask: np.ndarray) -> set[tuple[int, int]]:
    return {(int(x), int(y)) for y, x in np.argwhere(mask)}


def test_anchor_outline_reproduces_exactly(style):
    anchor = read_rgba(style.anchor_file)
    stripped = strip_outline(anchor, style.outline.rgb, keep=style.hand_placed_outline)
    assert outline_colored(stripped, style.outline.rgb).sum() == len(style.hand_placed_outline)

    result = apply_outline(stripped, style.outline)

    diff = np.argwhere(np.any(result.image != anchor, axis=-1))
    assert diff.size == 0, f"{len(diff)} pixels differ, first (y, x): {diff[:10].tolist()}"


def test_anchor_outline_uses_every_rule(style):
    anchor = read_rgba(style.anchor_file)
    stripped = strip_outline(anchor, style.outline.rgb, keep=style.hand_placed_outline)
    result = apply_outline(stripped, style.outline)
    # Generated ring plus the four hand-placed pixels make up the anchor's whole outline.
    assert result.ring.sum() + len(style.hand_placed_outline) == outline_colored(
        anchor, style.outline.rgb).sum()
    # Open soles were applied (under the feet and in the gap between the legs).
    assert result.open.sum() > 0
    assert all(y >= 26 for _, y in coords(result.open))


def test_single_pixel_gets_a_diamond_without_diagonals():
    img = paint(blank(), [(5, 5)])
    result = outline(img, INK, open_soles=False)
    assert coords(result.ring) == {(5, 4), (5, 6), (4, 5), (6, 5)}


def test_open_soles_leave_the_bottom_open():
    img = paint(blank(), [(4, 4), (5, 4), (6, 4), (4, 5), (5, 5), (6, 5), (4, 6), (5, 6), (6, 6)])
    result = outline(img, INK, open_soles=True, sole_rows=3)
    assert coords(result.open) == {(4, 7), (5, 7), (6, 7)}
    # Sides stay closed all the way down; the top is closed; corners stay empty (rounded).
    assert {(3, 6), (7, 6), (5, 3)} <= coords(result.ring)
    assert not ({(3, 3), (7, 3), (3, 7), (7, 7)} & coords(result.ring | result.open))


def test_open_soles_reach_exactly_two_rows_above_the_lowest(style):
    # A column (rows 2..9, so lowest = 9) with an arm on each side. Pixels under the arms touch
    # the silhouette only from above: under the row-6 arm they sit on row 7 = lowest - 2 (open);
    # under the row-5 arm they sit on row 6 = lowest - 3 (outlined). The anchor alone can't pin
    # this boundary, so this test does, using the style's own setting.
    column = [(6, y) for y in range(2, 10)]
    img = paint(blank(), column + [(3, 5), (4, 5), (5, 5)] + [(7, 6), (8, 6), (9, 6)])
    result = apply_outline(img, style.outline)
    assert {(8, 7), (9, 7)} <= coords(result.open)
    assert {(3, 6), (4, 6)} <= coords(result.ring)
    assert (7, 7) in coords(result.ring)  # also touches the column from the side


def test_hand_placed_pixels_are_kept_and_not_outlined_around():
    img = paint(blank(), [(5, 5), (6, 5)])
    paint(img, [(9, 9)], INK)  # a lone hand-placed outline pixel
    result = outline(img, INK, open_soles=False)
    assert tuple(result.image[9, 9]) == (*INK, 255)
    assert not ({(9, 8), (8, 9), (10, 9), (9, 10)} & coords(result.ring))


def test_input_is_not_modified_and_empty_frames_pass_through():
    img = paint(blank(), [(5, 5)])
    before = img.copy()
    outline(img, INK)
    assert np.array_equal(img, before)
    empty = blank()
    assert np.array_equal(outline(empty, INK).image, empty)


def test_partial_alpha_is_rejected():
    img = paint(blank(), [(5, 5)])
    img[0, 0] = (*INK, 70)  # a shadow pixel: composite shadows after outlining
    with pytest.raises(ValueError, match="alpha"):
        outline(img, INK)
