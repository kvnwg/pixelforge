"""Phase 4: the parts library, the knight, Rolling Knight's classes and pf random."""

from __future__ import annotations

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.parts import Library
from pixelforge.randomize import color_count, load_compat, random_recipes
from pixelforge.recipe import all_recipes, load_recipe
from pixelforge.validate import validate_part


def test_every_part_file_is_one_material(root, style):
    lib = Library(root, style)
    problems = [str(f) for p in lib.all_parts() for f in validate_part(p, lib, style)]
    assert problems == []


@pytest.mark.parametrize("name", ["knight", "rk_guardian", "rk_blade", "rk_ranger", "rk_cleric",
                                  "rk_arcanist", "rk_lancer"])
def test_armored_and_class_characters_validate_clean(root, style, name):
    b = build(root, name, style=style)
    assert [str(f) for f in b.findings] == []
    assert b.not_drawn == []


def test_knight_matches_the_brief(root, style):
    b = build(root, "knight", style=style, validate=False)
    f = b.frames[("idle", "s")][0]
    slots = {l.slot: l.part.variant for l in f.layers}
    assert slots["headwear"] == "great_helm" and "hair_front" not in slots and "eyes" not in slots
    assert slots["torso_wear"] == "plate" and slots["over_torso"] == "tabard"
    assert slots["held_near"] == "sword" and slots["held_near_trim"] == "hilt"
    fill = (f.sprite[..., 3] == 255) & (f.owner >= 0)
    rows = np.flatnonzero(fill.any(axis=1))
    assert rows.min() >= 8  # helm and plume fill at most two rows above row 10


def test_random_is_deterministic_and_valid(root, style):
    a = random_recipes(style, 1, 12)
    b = random_recipes(style, 1, 12)
    assert [r.to_yaml() for r in a] == [r.to_yaml() for r in b]
    lib = Library(root, style)
    for r in a:
        assert color_count(style, lib, r) <= style.constraints.max_colors_per_frame
        built = build(root, r, style=style, library=lib)
        assert built.errors == [], r.name


def test_random_respects_compat(root, style):
    compat = load_compat(root)
    for r in random_recipes(style, 7, 30, anims=("idle",)):
        chosen = {f"{s}/{v}" for s, v in r.parts.items()}
        for need, options in compat["requires"].items():
            assert need not in chosen or chosen & set(options), (r.name, need)
        for a, b in compat["incompatible"]:
            assert not (a in chosen and b in chosen), (r.name, a, b)
        assert "glow red" not in r.colors.values()


def test_derived_parts_follow_the_base_body(root, style):
    b = build(root, "knight", style=style, validate=False)
    for (anim, d), frames in b.frames.items():
        if d == "w":
            continue
        for f in frames:
            layers = {l.slot: l.image for l in f.layers}
            for slot, base in (("hands", ("arm_near", "arm_far")),):
                if slot in layers:
                    arms = np.zeros(f.owner.shape, bool)
                    for a in base:
                        arms |= (layers[a][..., 3] == 255) if a in layers else False
                    assert ((layers[slot][..., 3] == 255) & ~arms).sum() == 0, (anim, d, f.index)


def test_template_writes_a_sheet_and_a_guide(root, style, tmp_path, monkeypatch):
    from pixelforge.template import write_template
    sheet, guide = write_template(style, "headwear", "test_template_hat", "walk")
    try:
        from pixelforge.sheet import load_rgba
        assert load_rgba(sheet).shape == (96, 128, 4) and load_rgba(guide)[..., 3].any()
    finally:
        import shutil
        shutil.rmtree(sheet.parent)
