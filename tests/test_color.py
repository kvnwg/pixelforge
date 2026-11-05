from __future__ import annotations

import re

import pytest

from pixelforge.color import (Limits, StepGuide, check_ramp, hex_to_oklch, hue_delta, parse_hex,
                              to_hex)

CHAR = Limits(0.30, 0.80, 0.09, tolerance=0.002)
GUIDE = StepGuide(0.05, 0.10, 0.005, 3, 10, 0.02)


def rules(issues) -> set[str]:
    return {i.rule for i in issues}


def test_hex_round_trip():
    assert parse_hex("#3a263a") == (58, 38, 58)
    assert parse_hex("#3A263A") == (58, 38, 58)
    assert to_hex((58, 38, 58, 255)) == "#3a263a"
    for bad in ("3a263a", "#3a263", "#3a263g", "", None, 123):
        with pytest.raises(ValueError):
            parse_hex(bad)


def test_oklch_extremes():
    white, black = hex_to_oklch("#ffffff"), hex_to_oklch("#000000")
    assert white.L == pytest.approx(1.0, abs=1e-4) and white.C < 1e-4
    assert black.L == pytest.approx(0.0, abs=1e-6)


def test_anchor_colors_match_the_style_guide_table(root):
    """Every row of the STYLE_GUIDE.md section 4 palette table converts to its listed OKLCH."""
    text = (root / "docs" / "STYLE_GUIDE.md").read_text()
    rows = re.findall(r"^\| (\w+) \| (#[0-9a-f]{6}) \| ([\d.]+), ([\d.]+), (\d+) \|", text, re.M)
    assert len(rows) == 12
    for name, hexv, L, C, h in rows:
        got = hex_to_oklch(hexv)
        assert got.L == pytest.approx(float(L), abs=0.0015), name
        assert got.C == pytest.approx(float(C), abs=0.0015), name
        assert abs(hue_delta(got.h, float(h))) <= 1.0, name


def test_hue_delta_wraps_around():
    assert hue_delta(355, 5) == pytest.approx(10)
    assert hue_delta(5, 355) == pytest.approx(-10)
    assert hue_delta(44, 51) == pytest.approx(7)


def test_a_good_ramp_passes():
    assert check_ramp(["#735b51", "#826b5e", "#957e6d"], CHAR, GUIDE) == []  # anchor hair


def test_hard_limits_are_errors():
    assert "lightness" in rules(check_ramp(["#202020"], CHAR))
    assert "chroma" in rules(check_ramp(["#ff0000"], CHAR))
    assert "black_white" in rules(check_ramp(["#000000"], CHAR))
    assert "order" in rules(check_ramp(["#957e6d", "#735b51"], CHAR))
    dark = Limits(0.30, 0.80, 0.09, outline_L=0.45)
    assert "darker_than_outline" in rules(check_ramp(["#3f3a49"], dark))
    assert all(i.severity == "error" for i in check_ramp(["#ff0000", "#000000"], CHAR))


def test_tolerance_absorbs_rounding_on_a_limit():
    gloss = "#a3c7bf"  # slime highlight, L 0.8011 for a 0.80 limit
    assert check_ramp([gloss], CHAR) == []
    assert "lightness" in rules(check_ramp([gloss], Limits(0.30, 0.80, 0.09)))


def test_step_guide_issues_are_warnings():
    big_step = check_ramp(["#5e494c", "#957e6d"], CHAR, GUIDE)
    assert {"L_step", "hue_shift"} <= rules(big_step)
    assert all(i.severity == "warning" for i in big_step)


def test_hue_rule_is_skipped_for_near_gray_ramps():
    steel = ["#50555e", "#6d727b", "#8b8f99", "#a7aab5"]  # C about 0.016, hue barely moves
    assert check_ramp(steel, CHAR, GUIDE) == []
    strict = StepGuide(0.05, 0.10, 0.005, 3, 10, 0.0)
    assert "hue_shift" in rules(check_ramp(steel, CHAR, strict))
