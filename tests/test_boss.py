"""Phase 9: the first boss, the Stone Warden (MONSTERS.md section 5.5) on the large size class."""

from __future__ import annotations

import json

import numpy as np
import pytest

from pixelforge.anim import tell_ms
from pixelforge.build import build

ATTACKS = ("attack_slam", "cast_ring", "attack_fan", "charge", "summon", "stomp")


@pytest.fixture(scope="module")
def warden(root, style):
    return build(root, "stone_warden", style=style)


@pytest.fixture(scope="module")
def enraged(root, style):
    return build(root, "stone_warden_enraged", style=style)


def test_warden_and_its_enraged_form_validate(warden, enraged):
    assert [str(f) for f in warden.findings] == []
    assert [str(f) for f in enraged.findings] == []


def test_large_size_class(warden):
    from pixelforge.sheet import mirror
    size = warden.composer.rig.size
    assert (size.name, size.canvas, size.pivot, size.mirror_axis_x) == ("large", 64, (31, 59), 31)
    for e, w in zip(warden.frames[("attack_slam", "e")], warden.frames[("attack_slam", "w")]):
        assert np.array_equal(mirror(e.image, 31)[0], w.image)
    for d in ("s", "e", "n"):
        ys = np.flatnonzero((warden.frames[("idle", d)][0].sprite[..., 3] == 255).any(axis=1))
        assert ys.max() == 59 and ys.max() - ys.min() + 1 >= 48  # a big boss on the baseline


@pytest.mark.parametrize("anim", ATTACKS)
def test_every_move_telegraphs_600_ms_on_the_boss_profile(warden, style, anim):
    adef = warden.composer.anims[anim]
    profile = style.raw["combat"]["timing_profiles"]["boss"]
    holds = adef.flags.get("hold", frozenset())
    durations = [round(ms * profile["hold_scale"]) if i in holds else ms
                 for i, ms in enumerate(adef.frames_ms)]
    tell = tell_ms(adef, durations)
    if tell is None:  # summon and stomp are not attacks: their tell runs to the first non-hold
        tell = sum(durations[:max(holds) + 1])
    assert tell >= 600, (anim, tell)


def test_moves_carry_what_the_game_needs(warden, tmp_path):
    from pixelforge.export import export
    export(warden, tmp_path, gifs=False)
    pf = json.loads(next(tmp_path.rglob("stone_warden.json")).read_text())["meta"]["pixelforge"]
    ring = [e for e in pf["events"]["cast_ring_s"] if e["type"] == "spawn"][0]
    assert ring["pattern"] == "ring" and ring["count"] == 14 and ring["point_name"] == "core"
    fan = [e for e in pf["events"]["attack_fan_e"] if e["type"] == "spawn"][0]
    assert fan["pattern"] == "fan" and fan["count"] == 5 and fan["spread"] == pytest.approx(0.22)
    assert pf["loop_frames"]["charge_e"] == [2, 3]
    assert any(e["type"] == "summon" for e in pf["events"]["summon_s"])
    assert pf["timing_profile"] == "boss" and pf["size_class"] == "large"


def test_layers_never_overlap(warden):
    """Each frame keeps only what each layer shows, so z-order cannot change the picture."""
    for (anim, d), frames in warden.frames.items():
        if d == "w":
            continue
        for f in frames:
            seen = np.zeros(f.owner.shape, int)
            for layer in f.layers:
                if layer.slot in ("body", "arm_near", "arm_far"):
                    seen += layer.image[..., 3] == 255
            assert seen.max() <= 1, (anim, d, f.index)


def test_the_core_goes_dark_in_death(warden):
    last = warden.frames[("death", "s")][-1]
    assert "core" not in {l.slot for l in last.layers}
    assert "core" in {l.slot for l in warden.frames[("idle", "s")][0].layers}


def test_enraged_form_burns_red(warden, enraged, style):
    from pixelforge.color import parse_hex
    red = parse_hex(style.materials["eyes"].presets["glow red"][0])
    calm = parse_hex(style.materials["eyes"].presets["glow ghost"][0])
    a = enraged.frames[("idle", "s")][0].sprite
    b = warden.frames[("idle", "s")][0].sprite
    px = lambda img, c: int(np.all(img[..., :3] == np.asarray(c, np.uint8), axis=-1).sum())  # noqa: E731
    assert px(a, red) >= 9 and px(a, calm) == 0 and px(b, calm) >= 9
    assert np.array_equal(a[..., 3], b[..., 3])  # the same shape: a family


def test_boss_fx_are_in_the_library(root):
    for name in ("shockwave", "rock_shard", "rock_shard_impact", "summon_circle", "falling_rock"):
        assert (root / "fx" / name / "fx.yaml").is_file()
