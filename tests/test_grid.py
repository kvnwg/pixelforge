from __future__ import annotations

import numpy as np
import pytest

from pixelforge import grid


def test_parse_paint_and_back():
    codes = grid.parse([".0O", "21."], x0=4, y0=5, size=8)
    assert codes[5, 5] == 0 and codes[5, 6] == grid.INK and codes[6, 4] == 2 and codes[5, 4] == grid.CLEAR
    ramp = ["#735b51", "#826b5e", "#957e6d"]
    cell = grid.paint(codes, ramp, "#3a263a")
    assert np.array_equal(grid.codes_of(cell, ramp, "#3a263a"), codes)
    assert "y5" in grid.dump(codes)


def test_bad_grids_fail():
    with pytest.raises(ValueError):
        grid.parse(["x"], size=4)
    with pytest.raises(ValueError):
        grid.parse(["0"], x0=9, size=8)
    with pytest.raises(ValueError):
        grid.paint(grid.parse(["3"], size=4), ["#735b51"], "#3a263a")


def test_translate_and_overlay():
    a = grid.parse(["0"], 1, 1, 4)
    b = grid.translate(a, 1, 2)
    assert b[3, 2] == 0
    with pytest.raises(ValueError):
        grid.translate(a, 5, 0)
    top = grid.parse([".1"], 1, 1, 4)
    assert grid.overlay(a, top)[1, 2] == 1 and grid.overlay(a, top)[1, 1] == 0
    assert grid.mirror_codes(grid.parse(["0"], 3, 0, 8), 2)[0, 1] == 0
