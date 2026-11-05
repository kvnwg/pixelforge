"""Phase 5: combat data, timing profiles and the combat validator rules (COMBAT.md, QUALITY.md)."""

from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest
from typer.testing import CliRunner

from pixelforge.anim import load_anims, retime, tell_ms
from pixelforge.build import build
from pixelforge.cli import app
from pixelforge.compose import HELD_SLOTS, SMEAR
from pixelforge.export import aseprite_json
from pixelforge.validate import Validator

COMBAT_ANIMS = ["combat_idle", "attack_slash", "attack_heavy", "cast", "block_enter", "block_hold",
                "block_impact", "dodge", "hurt", "stun", "death", "victory", "roll", "backflip",
                "vault"]


@pytest.fixture(scope="module")
def knight(root, style):
    return build(root, "knight", style=style)


@pytest.fixture(scope="module")
def enemy(root, style):
    return build(root, "knight_enemy", style=style)


def rules(findings) -> set[str]:
    return {f.rule for f in findings}


# ------------------------------------------------------------------ timing profiles
def test_player_profile_keeps_the_authored_timing(style):
    slash = load_anims(style)["attack_slash"]
    player = style.raw["combat"]["timing_profiles"]["player"]
    assert retime(slash, list(slash.frames_ms), player) == list(slash.frames_ms)


def test_enemy_profile_scales_holds_and_meets_the_telegraph(style):
    anims = load_anims(style)
    profiles = style.raw["combat"]["timing_profiles"]
    for name in ("attack_slash", "attack_heavy", "shoot_bow", "cast"):
        adef = anims[name]
        for pname in ("enemy", "elite", "boss"):
            out = retime(adef, list(adef.frames_ms), profiles[pname])
            assert tell_ms(adef, out) >= profiles[pname]["telegraph_min_ms"], (name, pname)
            for i in adef.flags["hold"]:  # holds only ever grow
                assert out[i] >= adef.frames_ms[i]
            for i, ms in enumerate(adef.frames_ms):  # nothing else changes
                if i not in adef.flags["hold"]:
                    assert out[i] == ms


def test_short_tell_is_extended_on_the_last_hold(style):
    slash = load_anims(style)["attack_slash"]
    out = retime(slash, list(slash.frames_ms), {"hold_scale": 1.0, "telegraph_min_ms": 500})
    assert out[0] == slash.frames_ms[0] and out[1] == 500 - slash.frames_ms[0]
    assert tell_ms(slash, out) == 500


def test_enemy_build_passes_the_telegraph_check(enemy):
    assert [str(f) for f in enemy.errors] == []
    durations = [f.duration for f in enemy.frames[("attack_slash", "e")]]
    assert sum(durations[:2]) >= 300


def test_E17_flags_a_tell_that_is_too_short(enemy):
    frames = {k: [replace(f, duration=ms) for f, ms in
                  zip(v, enemy.composer.anims[k[0]].frames_ms)] for k, v in enemy.frames.items()}
    found = Validator(enemy.composer).combat(frames, "enemy")
    assert "E17" in rules(found)


# ------------------------------------------------------------------ hitboxes, hurtboxes, smears
def test_hitboxes_cover_the_weapon_on_active_frames_only(knight):
    for d in ("s", "e", "n", "w"):
        frames = knight.frames[("attack_slash", d)]
        for f in frames:
            if "active" in f.flags:
                assert f.hitboxes, f.label
                weapon = f.slot_mask("held_near") | (f.owner == SMEAR)
                ys, xs = np.nonzero(weapon)
                x, y, w, h = f.hitboxes[0]
                inside = (xs >= x) & (xs < x + w) & (ys >= y) & (ys < y + h)
                assert inside.mean() > 0.9, f.label
            else:
                assert not f.hitboxes, f.label


def test_strike_frames_have_a_smear_behind_the_body(knight, girl):
    for b in (knight, girl):
        for d in ("s", "e", "n"):
            for f in b.frames[("attack_slash", d)]:
                smear = f.owner == SMEAR
                assert smear.any() == ("active" in f.flags), f.label
            heavy = b.frames[("attack_heavy", d)][3]
            assert (heavy.owner == SMEAR).any(), heavy.label


def test_hurtbox_is_the_body_without_held_items(knight):
    f = knight.frames[("attack_slash", "e")][0]  # sword cocked behind the head
    body = (f.owner >= 0) & ~f.slot_mask(*HELD_SLOTS)
    ys, xs = np.nonzero(body)
    assert f.hurtbox == (xs.min(), ys.min(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)


def test_west_combat_data_mirrors_east(knight):
    axis = knight.composer.rig.size.mirror_axis_x
    for e, w in zip(knight.frames[("attack_slash", "e")], knight.frames[("attack_slash", "w")]):
        assert [(2 * axis - (x + bw - 1), y, bw, bh) for x, y, bw, bh in e.hitboxes] == w.hitboxes
        assert {k: (2 * axis - x, y) for k, (x, y) in e.points.items()} == w.points


def test_E15_active_frame_without_hitbox(knight):
    frames = dict(knight.frames)
    frames[("attack_slash", "e")] = [replace(f, hitboxes=[]) for f in frames[("attack_slash", "e")]]
    found = Validator(knight.composer).combat(frames, "player")
    assert any(f.rule == "E15" and "attack_slash e 2" in f.where for f in found)


def test_E15_hitbox_outside_the_active_phase(knight):
    frames = dict(knight.frames)
    fs = list(frames[("attack_slash", "e")])
    fs[0] = replace(fs[0], hitboxes=[(16, 12, 8, 8)])
    frames[("attack_slash", "e")] = fs
    found = Validator(knight.composer).combat(frames, "player")
    assert any(f.rule == "E15" and "outside the active phase" in f.message for f in found)


def test_E16_attack_without_recover(knight):
    composer = knight.composer
    slash = composer.anims["attack_slash"]
    broken = replace(slash, events=tuple(e for e in slash.events if e["type"] != "recover"))
    original = composer.anims["attack_slash"]
    composer.anims["attack_slash"] = broken
    try:
        found = Validator(composer).combat(knight.frames, "player")
    finally:
        composer.anims["attack_slash"] = original
    assert any(f.rule == "E16" and "recover" in f.message for f in found)


def test_W8_windup_identical_to_combat_idle(knight):
    frames = dict(knight.frames)
    idle = frames[("combat_idle", "e")][0]
    frames[("attack_slash", "e")] = [replace(f, sprite=idle.sprite) if f.index < 2 else f
                                     for f in frames[("attack_slash", "e")]]
    found = Validator(knight.composer).combat(frames, "player")
    assert any(f.rule == "W8" and "attack_slash e" in f.where for f in found)


# ------------------------------------------------------------------ poses
def test_lagging_hair_trails_by_at_most_one_pixel(girl):
    c = girl.composer
    hair = c.parts["hair_back"]
    for anim in COMBAT_ANIMS:
        adef = c.anims[anim]
        for d in ("e", "n"):
            for i in range(adef.frames):
                head = c.rig.anchor(anim, d, i, "head")
                ox, oy = c.origin(hair, d)
                dx, dy = c.offset(hair, adef, d, i)
                assert abs(ox + dx - head[0]) <= 1 and abs(oy + dy - head[1]) <= 1, (anim, d, i)


def test_nothing_but_held_items_below_the_ground(root, style):
    cleric = build(root, "rk_cleric", style=style)  # robe: the deepest crouch pushes it down
    base = style.size_classes["small"].pivot[1]
    for (anim, d), frames in cleric.frames.items():
        for f in frames:
            if f.flags & {"airborne", "lying"}:
                continue
            for layer in f.layers:
                if layer.slot not in HELD_SLOTS:
                    assert not layer.image[base + 1:, :, 3].any(), (f.label, layer.slot)


def test_rolling_knight_classes_validate(root, style):
    for name in ("rk_guardian", "rk_blade", "rk_ranger", "rk_cleric", "rk_arcanist", "rk_lancer"):
        b = build(root, name, style=style)
        assert [str(f) for f in b.findings] == [], name


def test_every_combat_animation_is_drawn_in_s_e_n(knight):
    for anim in COMBAT_ANIMS:
        for d in ("s", "e", "n", "w"):
            assert len(knight.frames[(anim, d)]) == knight.composer.anims[anim].frames, (anim, d)


# ------------------------------------------------------------------ export and tools
def test_export_carries_combat_data(knight):
    data = aseprite_json(knight, "knight.png")
    pf = data["meta"]["pixelforge"]
    assert pf["hitboxes"]["attack_slash_e"]["2"]
    assert set(pf["hurtboxes"]["attack_slash_e"]) == {"0", "1", "2", "3", "4"}
    heavy = {e["type"]: e for e in pf["events"]["attack_heavy_e"]}
    assert heavy["vfx"]["point_name"] == "weapon_tip" and len(heavy["vfx"]["point"]) == 2
    assert pf["holds"]["attack_slash_e"] == [0, 1]
    assert pf["base_durations"]["attack_slash_e"] == [120, 80, 60, 140, 160]
    assert pf["timing_profiles"]["enemy"]["telegraph_min_ms"] == 300
    assert pf["root_motion"]["roll_e"] == [4, 14, 16, 14, 6]


def test_review_combat_and_battle(root):
    runner = CliRunner()
    env = {"PIXELFORGE_ROOT": str(root)}
    result = runner.invoke(app, ["review", "knight", "--anim", "attack_slash", "--dir", "e",
                                 "--combat"], env=env)
    assert result.exit_code == 0, result.output
    assert (root / "review" / "knight" / "attack_slash_e_timeline.png").is_file()
    result = runner.invoke(app, ["battle", "knight", "anchor_girl", "--anim", "attack_slash"], env=env)
    assert result.exit_code == 0, result.output
    assert (root / "review" / "battle" / "battle_knight_vs_anchor_girl_attack_slash.png").is_file()


@pytest.fixture(scope="module")
def girl(root, style):
    return build(root, "anchor_girl", style=style)


def test_E18_anchor_outside_the_size_class(knight):
    rig = knight.composer.rig
    pts = rig.anchors["attack_slash"]["e"][0]
    saved = pts["hand_near"]
    pts["hand_near"] = [31, 23]  # past the small class's safe bounds (x 2..29)
    try:
        found = Validator(knight.composer).size_class()
    finally:
        pts["hand_near"] = saved
    assert any(f.rule == "E18" and "hand_near" in f.message for f in found)
    assert Validator(knight.composer).size_class() == []
