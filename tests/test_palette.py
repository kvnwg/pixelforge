from __future__ import annotations

from PIL import Image

from pixelforge.palette import check_palette, render_swatches
from pixelforge.style import load_style


def by_id(reports):
    return {r.id: r for r in reports}


def test_every_ramp_passes_the_hard_limits(style):
    errors = {r.id: [str(i) for i in r.errors] for r in check_palette(style) if r.errors}
    assert errors == {}


def test_no_unaccepted_warnings(style):
    """New presets must meet the step guide or be accepted in style.json with a reason."""
    warnings = {r.id: [str(i) for i in r.warnings] for r in check_palette(style) if r.warnings}
    assert warnings == {}


def test_every_preset_and_fx_ramp_is_checked(style):
    ids = {r.id for r in check_palette(style)}
    for m in style.materials.values():
        assert {f"{m.name}/{p}" for p in m.presets} <= ids
    assert {f"fx/{name}" for name in style.fx_ramps} <= ids
    assert {"outline", "effects/flash"} <= ids


def test_glow_eyes_use_their_own_limits(style):
    reports = by_id(check_palette(style))
    glow_red = reports["eyes/glow red"]
    assert glow_red.group == "glow" and glow_red.status == "ok"
    assert glow_red.lch[0].C > style.constraints.character.C_max  # too bright for a character
    assert reports["fx/fire"].group == "fx"


def test_anchor_ramps_are_accepted_not_failed(style):
    reports = by_id(check_palette(style))
    for ramp_id in ("skin/light (anchor)", "cloth/navy (anchor)", "leather/brown (anchor)"):
        assert reports[ramp_id].status == "accepted"
        assert reports[ramp_id].reason


def test_a_too_saturated_preset_is_an_error(raw_style, style_root):
    raw_style["materials"]["cloth"]["presets"]["neon"] = ["#e8102a", "#ff3040"]  # past C 0.20
    style = load_style(style_root(raw_style) / "style" / "style.json")
    report = by_id(check_palette(style))["cloth/neon"]
    assert report.status == "error"
    assert "chroma" in {i.rule for i in report.errors}


def test_stale_acceptances_are_flagged(raw_style, style_root):
    raw_style["constraints"]["accepted_ramp_warnings"]["hair/black"] = {
        "rules": ["L_step"], "reason": "test"}
    style = load_style(style_root(raw_style) / "style" / "style.json")
    report = by_id(check_palette(style))["hair/black"]
    assert [i.rule for i in report.warnings] == ["stale_acceptance"]


def test_swatch_sheet_renders(style, tmp_path):
    path = render_swatches(check_palette(style), style, tmp_path / "sub" / "swatches.png")
    with Image.open(path) as img:
        assert img.mode == "RGB" and img.width > 300 and img.height > 1000
