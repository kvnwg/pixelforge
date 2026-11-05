"""Phase 8: humanoid monsters (MONSTERS.md sections 5.4 and 6): orc, skeleton, goblins, and
family variants."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pixelforge.build import build
from pixelforge.color import parse_hex
from pixelforge.validate import roster_findings


def bbox(sprite):
    ys, xs = np.nonzero(sprite[..., 3] == 255)
    return xs.min(), ys.min(), xs.max(), ys.max()


def gray(sprite):
    rgb = sprite[..., :3].astype(float)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def grayscale_change(a, b, d="s"):
    """The share of the pixels two builds both cover whose gray differs by more than 8 levels."""
    fa, fb = a.frames[("idle", d)][0].sprite, b.frames[("idle", d)][0].sprite
    both = (fa[..., 3] == 255) & (fb[..., 3] == 255)
    return float((np.abs(gray(fa) - gray(fb))[both] > 8).mean())


@pytest.fixture(scope="module")
def builds(root, style):
    names = ["anchor_girl", "orc", "skeleton", "goblin", "goblin_chief", "wolf", "frost_wolf"]
    return {n: build(root, n, style=style) for n in names}


@pytest.mark.parametrize("name", ["orc", "skeleton", "goblin", "goblin_chief", "frost_wolf"])
def test_humanoid_monsters_validate(builds, name):
    assert [str(f) for f in builds[name].findings] == []


def test_orc_horns_rise_above_a_human_head(builds):
    orc = builds["orc"].frames[("idle", "s")][0].sprite
    girl = builds["anchor_girl"].frames[("idle", "s")][0].sprite
    assert bbox(orc)[1] <= bbox(girl)[1] - 3


def test_skeleton_has_every_humanoid_animation_in_bone(root, builds, style):
    humanoid = {p.name for p in (root / "parts" / "body" / "humanoid").glob("*.png")}
    skeleton = {p.name for p in (root / "parts" / "body" / "skeleton").glob("*.png")}
    assert humanoid == skeleton
    skin = {parse_hex(c) for c in style.materials["skin"].base}
    for frames in builds["skeleton"].frames.values():
        for f in frames:
            opaque = f.sprite[f.sprite[..., 3] == 255][:, :3]
            assert not skin & {tuple(int(v) for v in px) for px in opaque}


def test_goblins_are_small(builds):
    girl = bbox(builds["anchor_girl"].frames[("idle", "s")][0].sprite)
    for name in ("goblin", "goblin_chief"):
        x0, y0, x1, y1 = bbox(builds[name].frames[("idle", "s")][0].sprite)
        assert y1 == 27 and y1 - y0 < girl[3] - girl[1]  # on the baseline, shorter than a human


def test_variants_differ_in_grayscale(builds):
    chief, goblin = builds["goblin_chief"], builds["goblin"]
    assert grayscale_change(goblin, chief) > 0.5
    a = goblin.frames[("idle", "s")][0].sprite[..., 3] == 255
    b = chief.frames[("idle", "s")][0].sprite[..., 3] == 255
    assert (a ^ b).sum() >= 10  # the crown: an added trait, not only a recolor
    assert grayscale_change(builds["wolf"], builds["frost_wolf"]) > 0.5


def test_w7_spares_a_family_but_not_strangers(builds):
    goblin, chief = builds["goblin"], builds["goblin_chief"]
    assert roster_findings([goblin, chief]) == []
    raw = {k: v for k, v in chief.recipe.raw.items() if k != "family"}
    stranger = replace(chief, recipe=replace(chief.recipe, name="hobgoblin", raw=raw,
                                             path=Path(chief.recipe.path).with_name("hobgoblin.yaml")))
    assert any(f.rule == "W7" for f in roster_findings([goblin, stranger]))


def test_the_humanoid_roster_has_no_lookalikes(builds):
    assert roster_findings(list(builds.values())) == []
