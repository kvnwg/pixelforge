"""Phase 6: the FX pipeline and library (COMBAT.md section 6, QUALITY.md E19, W9, W11)."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace

import numpy as np
import pytest
import yaml
from typer.testing import CliRunner

from pixelforge.build import build
from pixelforge.cli import app
from pixelforge.color import parse_hex
from pixelforge.fx import FXLibrary, character_fx_colors, export, fx_folders, load_fx, orient, validate_fx
from pixelforge.sheet import load_rgba, save_rgba
from pixelforge.validate import Validator

V1 = ["smear_arc", "smear_vertical", "smear_thrust", "spark_small", "impact_big", "arrow",
      "fireball", "ice_shard", "poison_glob", "arcane_orb", "status_burn", "status_poison",
      "status_freeze", "status_stun", "status_sleep", "status_shield", "poof_smoke", "soul_wisp",
      "bone_crumble", "heal_sparkle", "buff_up", "debuff_down", "dust_puff"]


@pytest.fixture(scope="module")
def lib(root, style):
    return FXLibrary(root, style)


def test_the_v1_set_is_complete(lib):
    names = set(lib.names())
    assert set(V1) <= names
    for element in ("fire", "ice", "poison", "arcane", "holy", "shadow"):
        assert f"impact_{element}" in names
    for element in ("fire", "ice", "poison", "arcane", "holy"):
        assert f"gather_glow_{element}" in names
    for proj in ("fireball", "ice_shard", "poison_glob", "arcane_orb"):
        assert f"{proj}_impact" in names


def test_every_fx_validates(root, style):
    for folder in fx_folders(root):
        assert [str(f) for f in validate_fx(load_fx(folder, style), style)] == [], folder.name


def test_fx_use_only_their_ramp_and_binary_alpha(root, style, lib):
    for name in lib.names():
        fx, ramp = lib.get(name)
        colors = {parse_hex(c) for c in style.raw["fx_ramps"][ramp]}
        for anim in fx.anims:
            cells, _, _ = lib.cells(name, anim)
            for c in cells:
                assert set(np.unique(c[..., 3])) <= {0, 255}, name
                used = {tuple(int(v) for v in px) for px in c[c[..., 3] == 255][:, :3]}
                assert used <= colors, name


def test_every_fx_reads_on_every_ground(lib, style):
    """All FX read at 1x on beige, light and dark (ROADMAP Phase 6): in every frame with art, some
    pixel differs from each ground by at least 0.07 in OKLab lightness or 0.06 in color. Shadow FX
    are dark magic: they only need to read on beige and light ground."""
    from pixelforge.color import rgb_to_oklab
    grounds = {n: rgb_to_oklab(parse_hex(c)) for n, c in style.raw["preview_backgrounds"].items()}
    for name in lib.names():
        fx, ramp = lib.get(name)
        for anim in fx.anims:
            for i, c in enumerate(lib.cells(name, anim)[0]):
                used = {tuple(int(v) for v in px) for px in c[c[..., 3] == 255][:, :3]}
                if not used:
                    continue
                labs = [rgb_to_oklab(u) for u in used]
                for gname, g in grounds.items():
                    if ramp == "shadow" and gname == "dark":
                        continue
                    best = max(max(abs(l[0] - g[0]) / 0.07,
                                   ((l[1] - g[1]) ** 2 + (l[2] - g[2]) ** 2) ** 0.5 / 0.06)
                               for l in labs)
                    assert best >= 1, (name, anim, i, gname)


def test_E19_off_ramp_color(root, style, tmp_path):
    src = root / "fx" / "spark_small"
    folder = tmp_path / "fx" / "spark_small"
    shutil.copytree(src, folder)
    img = load_rgba(folder / "play.png")
    img[7, 7] = (255, 0, 0, 255)
    save_rgba(folder / "play.png", img)
    found = validate_fx(load_fx(folder, style), style)
    assert any(f.rule == "E19" for f in found)


def test_E19_character_presets_never_use_fx_colors(style):
    assert character_fx_colors(style) == []
    raw = json.loads(json.dumps(style.raw))
    raw["materials"]["cloth"]["presets"]["crimson"][0] = raw["fx_ramps"]["fire"][0]
    found = character_fx_colors(replace(style, raw=raw))
    assert any(f.rule == "E19" and "cloth/crimson" in f.where for f in found)


def test_rotation_and_mirroring_are_lossless():
    cell = np.zeros((16, 16, 4), np.uint8)
    cell[7, 3:12] = (200, 100, 50, 255)  # an east-pointing streak
    cell[6, 11] = cell[8, 11] = (250, 250, 250, 255)
    pivot = (11, 7)
    for d in ("s", "n", "w"):
        turned, (px, py) = orient(cell, pivot, d, True)
        assert (turned[..., 3] == 255).sum() == (cell[..., 3] == 255).sum()
        assert tuple(turned[py, px]) == tuple(cell[pivot[1], pivot[0]])  # the pivot pixel follows
    s, _ = orient(cell, pivot, "s", True)
    assert (s[3:12, 8, 3] == 255).all()  # east became south: the streak is vertical
    assert np.array_equal(np.rot90(s, k=1), cell)
    upright, p = orient(cell, pivot, "s", False)
    assert np.array_equal(upright, cell) and p == pivot


def test_export_has_every_direction(root, style, tmp_path):
    fx = load_fx(root / "fx" / "fireball", style)
    entries = export(fx, style, tmp_path)
    data = json.loads((tmp_path / "fireball" / "fireball.json").read_text())
    tags = {t["name"] for t in data["meta"]["frameTags"]}
    assert tags == {"travel_s", "travel_e", "travel_n", "travel_w"}
    assert data["meta"]["pixelforge"]["pivot"]["travel_w"] == [16 - 1 - fx.pivot[0], fx.pivot[1]]
    assert entries[0]["name"] == "fireball"
    tinted = export(load_fx(root / "fx" / "impact", style), style, tmp_path)
    assert {e["name"] for e in tinted} == {f"impact_{t}" for t in ("fire", "ice", "poison", "arcane",
                                                                   "holy", "shadow")}


def test_fx_cli_build_and_review(root):
    runner = CliRunner()
    env = {"PIXELFORGE_ROOT": str(root)}
    result = runner.invoke(app, ["fx", "build", "--all"], env=env)
    assert result.exit_code == 0, result.output
    assert "0 errors" in result.output
    index = json.loads((root / "out" / "fx" / "index.json").read_text())
    assert len(index["fx"]) >= 38
    result = runner.invoke(app, ["fx", "review", "fireball", "spark_small"], env=env)
    assert result.exit_code == 0, result.output
    assert (root / "review" / "fx" / "fireball.png").is_file()


def test_events_name_fx_that_exist(root, style):
    knight = build(root, "knight", style=style)
    composer = knight.composer
    slash = composer.anims["attack_slash"]
    broken = tuple({**e, "fx": "no_such_fx"} if e["type"] == "hit" else e for e in slash.events)
    composer.anims["attack_slash"] = replace(slash, events=broken)
    try:
        found = Validator(composer).combat(knight.frames, "player")
    finally:
        composer.anims["attack_slash"] = slash
    assert any(f.rule == "E16" and "no_such_fx" in f.message for f in found)


def test_W9_fx_covering_the_tell(root, style, tmp_path):
    shutil.copytree(root / "parts", tmp_path / "parts")
    shutil.copytree(root / "fx", tmp_path / "fx")
    folder = tmp_path / "fx" / "big_blob"
    folder.mkdir()
    (folder / "fx.yaml").write_text(yaml.safe_dump({
        "name": "big_blob", "ramp": "impact", "cell": 32, "pivot": [15, 15], "layer": "above",
        "anims": {"play": {"frames_ms": [60], "loop": False}}}))
    blob = np.zeros((32, 32, 4), np.uint8)
    blob[4:28, 4:28] = (*parse_hex(style.raw["fx_ramps"]["impact"][3]), 255)
    save_rgba(folder / "play.png", blob)
    from pixelforge.recipe import find_recipe, load_recipe
    knight = build(tmp_path, load_recipe(find_recipe(root, "knight"), style), style=style)
    composer = knight.composer
    cast = composer.anims["cast"]
    events = tuple(cast.events) + ({"frame": 1, "type": "vfx", "fx": "big_blob", "point": "torso"},)
    composer.anims["cast"] = replace(cast, events=events)
    try:
        found = Validator(composer).combat(knight.frames, "player")
    finally:
        composer.anims["cast"] = cast
    assert any(f.rule == "W9" and "big_blob" in f.message for f in found)


def test_battle_strip_plays_fx(root):
    runner = CliRunner()
    env = {"PIXELFORGE_ROOT": str(root)}
    result = runner.invoke(app, ["battle", "rk_arcanist", "knight", "--anim", "cast",
                                 "--element", "fire"], env=env)
    assert result.exit_code == 0, result.output
    path = root / "review" / "battle" / "battle_rk_arcanist_vs_knight_cast_fire.png"
    img = load_rgba(path)
    fire = {parse_hex(c) for c in json.loads((root / "style" / "style.json").read_text())["fx_ramps"]["fire"]}
    colors = {tuple(int(v) for v in px) for px in img[..., :3].reshape(-1, 3)}
    assert colors & fire  # the fireball and its burst are in the strip
