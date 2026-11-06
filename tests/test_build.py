"""Phase 1 acceptance: anchor_girl rebuilds the anchor exactly and recolors like the reference."""

from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.color import parse_hex
from pixelforge.effects import composite_on
from pixelforge.export import aseprite_json, check_export, export, spritesheet
from pixelforge.recipe import find_recipe, load_recipe
from pixelforge.recolor import ramp_map, recolor

from .conftest import read_rgba


@pytest.fixture(scope="module")
def girl(root, style):
    return build(root, "anchor_girl", style=style)


@pytest.fixture(scope="module")
def recipe(root, style):
    return load_recipe(find_recipe(root, "anchor_girl"), style)


def test_anchor_girl_rebuilds_the_anchor_exactly(girl, root):
    frame = girl.frames[("idle", "s")][0]
    ref = read_rgba(root / "style" / "anchor_with_shadow.png")
    diff = np.argwhere(np.any(frame.image != ref, axis=-1))
    assert diff.size == 0, f"{len(diff)} pixels differ, first (y, x): {diff[:10].tolist()}"


def test_anchor_girl_validates(girl):
    assert [str(f) for f in girl.errors] == []
    assert [str(f) for f in girl.warnings] == []


def test_recolors_match_the_reference(root, style, recipe):
    """The reference recolor images (Phase 0) record the original muted presets. The anchor's own
    combination still matches them pixel for pixel; design pass 2 (2026-11-06) regenerated every
    other preset as a vivid ramp, so for those the recolor must keep the reference's shade
    structure: each reference color becomes exactly one new color, taken from that combination's
    presets (index to index), and nothing outside the character changes."""
    spec = json.loads((root / "style" / "recolor_test.json").read_text())
    ref = read_rgba(root / spec["reference_1x"])[..., :3]
    beige = parse_hex(style.raw["preview_backgrounds"]["beige"])
    cell, (ox, oy) = spec["cell"], spec["offset"]
    for i, colors in enumerate(spec["combos"]):
        frame = build(root, replace(recipe, colors=colors), style=style, validate=False
                      ).frames[("idle", "s")][0]
        ours = composite_on(frame.image, beige)
        theirs = ref[oy:oy + 32, i * cell + ox:i * cell + ox + 32]
        character = frame.sprite[..., 3] == 255
        if all("(anchor)" in preset for preset in colors.values()):
            assert np.array_equal(ours[character], theirs[character]), f"combo {i} character pixels"
        else:
            mapping: dict[tuple, set] = {}
            for a, b in zip(map(tuple, theirs[character]), map(tuple, ours[character])):
                mapping.setdefault(a, set()).add(b)
            assert all(len(v) == 1 for v in mapping.values()), f"combo {i}: shade structure changed"
            allowed = {parse_hex(style.outline.color)}
            for material, preset in colors.items():
                allowed |= {parse_hex(c) for c in style.materials[material].presets[preset]}
            assert {tuple(int(v) for v in c) for c in ours[character]} <= allowed, f"combo {i} colors"
        outside = np.argwhere(np.any(ours != theirs, axis=-1) & ~character)
        # The reference images have no shadow on row 26 (see style/recolor_test.json).
        assert {(int(x), int(y)) for y, x in outside} <= {(16, 26), (19, 26)}, f"combo {i}"


def test_eyes_and_legs_recolor_independently(root, style, recipe, girl):
    base = girl.frames[("idle", "s")][0]
    eyes = base.slot_mask("eyes")
    legs = base.slot_mask("legs_wear")
    other = build(root, replace(recipe, colors={**recipe.colors, "cloth": "crimson",
                                                "hair": "blonde"}),
                  style=style, validate=False).frames[("idle", "s")][0]
    assert np.array_equal(base.image[eyes], other.image[eyes])
    assert np.array_equal(base.image[legs], other.image[legs])
    dress = base.slot_mask("torso_wear")
    assert not np.array_equal(base.image[dress], other.image[dress])
    for material, preset in (("eyes", "green"), ("leather", "tan")):
        changed = build(root, replace(recipe, colors={**recipe.colors, material: preset}),
                        style=style, validate=False).frames[("idle", "s")][0]
        mask = eyes if material == "eyes" else legs
        assert not np.array_equal(base.image[mask], changed.image[mask])
        assert np.array_equal(base.image[dress], changed.image[dress])


def test_recolor_to_the_base_presets_is_a_no_op(style, girl):
    for layer in girl.frames[("idle", "s")][0].layers:
        m = style.materials[layer.part.material]
        assert np.array_equal(recolor(layer.image, ramp_map(m, m.base)), layer.image)


def test_build_is_deterministic(root, style, tmp_path):
    a = export(build(root, "anchor_girl", style=style), tmp_path / "a", gifs=False)[0]
    b = export(build(root, "anchor_girl", style=style), tmp_path / "b", gifs=False)[0]
    for name in ("anchor_girl.png", "anchor_girl.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_export_json_matches_the_sheet(girl):
    image = spritesheet(girl)
    data = aseprite_json(girl, "anchor_girl.png")
    assert check_export(data, image, "anchor_girl") == []
    assert data["meta"]["size"] == {"w": image.shape[1], "h": image.shape[0]}
    assert data["meta"]["pixelforge"]["pivot"] == [15, 27]
    tags = {t["name"]: t for t in data["meta"]["frameTags"]}
    for (anim, d), frames in girl.frames.items():
        tag = tags[f"{anim}_{d}"]
        assert tag["to"] - tag["from"] + 1 == len(frames)
        for i, f in enumerate(frames):
            r = data["frames"][tag["from"] + i]["frame"]
            cell = image[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]]
            assert np.array_equal(cell, f.image)
            assert data["frames"][tag["from"] + i]["duration"] == f.duration


def test_turnaround_keeps_head_and_height(girl):
    """Phase 2: same head height (10 rows) and total height (18 rows) facing s, e, n and w."""
    from pixelforge.validate import Validator
    v = Validator(girl.composer)
    for d in ("s", "e", "n", "w"):
        f = girl.frames[("idle", d)][0]
        assert v.head_height(f) == 10, d
        rows = np.flatnonzero((f.sprite[..., 3] == 255).any(axis=1))
        assert (rows.min(), rows.max()) == (10, 27), d  # outline row 10 to the baseline


def test_west_is_east_mirrored_around_the_pivot(girl):
    from pixelforge.sheet import mirror
    for e, w in zip(girl.frames[("idle", "e")], girl.frames[("idle", "w")]):
        assert np.array_equal(mirror(e.image, 15)[0], w.image)
