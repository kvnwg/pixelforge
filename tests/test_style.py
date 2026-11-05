"""style.json loads, and a broken style fails loudly with the path of every problem."""

from __future__ import annotations

import pytest

from pixelforge.style import StyleError, find_root, load_style


def problems(raw_style, style_root) -> list[str]:
    with pytest.raises(StyleError) as err:
        load_style(style_root(raw_style) / "style" / "style.json")
    return err.value.problems


def test_real_style_loads(style):
    assert style.canvas == 32 and style.pivot == (15, 27) and style.baseline_y == 27
    assert style.outline.color == "#3a263a" and style.outline.sole_rows == 3
    assert style.shadow.alpha == 70 and style.shadow.rows[27] == (10, 20)
    assert style.drawn_directions == ("s", "e", "n")
    assert {"skin", "hair", "cloth", "leather", "accent", "eyes", "metal", "fur", "slime"} <= set(
        style.materials)
    assert style.materials["eyes"].glow_presets == {"glow red", "glow yellow", "glow ghost"}
    assert set(style.size_classes) == {"small", "medium", "large", "huge"}
    assert style.size_classes["medium"].pivot == (23, 43)


def test_combat_view_is_set(style):
    assert style.combat_view in style.raw["combat"]["view_options"]
    assert style.combat_directions == tuple(
        style.raw["combat"]["view_options"][style.combat_view]["combat_directions"])


def test_unset_combat_view_fails(raw_style, style_root):
    raw_style["combat"]["view"] = "UNSET: choose 'side' or 'topdown' in Phase 0"
    assert any(p.startswith("combat.view:") for p in problems(raw_style, style_root))


def test_missing_keys_fail_loudly_and_all_at_once(raw_style, style_root):
    del raw_style["outline"]["color"]
    del raw_style["materials"]["skin"]["presets"]
    found = problems(raw_style, style_root)
    assert "outline.color: missing" in found
    assert "materials.skin.presets: missing" in found


def test_wrong_shade_count_names_the_preset(raw_style, style_root):
    raw_style["materials"]["skin"]["presets"]["fair"] = ["#aa8173", "#c69d8c"]
    assert any(p.startswith("materials.skin.presets.fair:") for p in problems(raw_style, style_root))


def test_bad_hex_is_rejected(raw_style, style_root):
    raw_style["fx_ramps"]["fire"][0] = "red"
    assert any(p.startswith("fx_ramps.fire:") for p in problems(raw_style, style_root))


def test_size_class_pivot_rule(raw_style, style_root):
    raw_style["size_classes"]["medium"]["pivot"] = [24, 43]
    found = problems(raw_style, style_root)
    assert any(p.startswith("size_classes.medium.pivot:") for p in found)


def test_top_level_geometry_must_match_the_small_class(raw_style, style_root):
    raw_style["pivot"]["x"] = 16
    assert any(p.startswith("pivot:") for p in problems(raw_style, style_root))


def test_animation_events_are_checked(raw_style, style_root):
    raw_style["animations"]["attack_slash"]["events"][1]["frame"] = 9
    raw_style["animations"]["cast"]["events"][0]["type"] = "explode"
    found = problems(raw_style, style_root)
    assert any(p.startswith("animations.attack_slash.events[1].frame:") for p in found)
    assert any(p.startswith("animations.cast.events[0].type:") for p in found)


def test_rigs_need_known_size_classes(raw_style, style_root):
    raw_style["rigs"]["blob"]["size_class"] = "tiny"
    assert any(p.startswith("rigs.blob.size_class:") for p in problems(raw_style, style_root))


def test_accepted_warnings_must_name_real_ramps_and_rules(raw_style, style_root):
    raw_style["constraints"]["accepted_ramp_warnings"]["skin/purple"] = {
        "rules": ["chroma"], "reason": "no"}
    found = problems(raw_style, style_root)
    assert any(p.startswith("constraints.accepted_ramp_warnings.skin/purple:") for p in found)
    assert any(p.startswith("constraints.accepted_ramp_warnings.skin/purple.rules:") for p in found)


def test_invalid_json_is_a_style_error(tmp_path):
    bad = tmp_path / "style.json"
    bad.write_text("{not json")
    with pytest.raises(StyleError, match="not valid JSON"):
        load_style(bad)


def test_find_root_from_a_subfolder_and_from_the_env(root, monkeypatch, tmp_path):
    monkeypatch.delenv("PIXELFORGE_ROOT", raising=False)
    assert find_root(root / "docs") == root
    monkeypatch.setenv("PIXELFORGE_ROOT", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        find_root()
