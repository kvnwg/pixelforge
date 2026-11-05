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


# ------------------------------------------------------------------ the ogre and the medium class
@pytest.fixture(scope="module")
def ogre(root, style):
    return build(root, "ogre", style=style)


def test_ogre_validates(ogre):
    assert [str(f) for f in ogre.findings] == []


def test_medium_size_class_canvas_pivot_and_mirror(ogre, tmp_path):
    from pixelforge.export import export
    from pixelforge.sheet import mirror
    size = ogre.composer.rig.size
    assert (size.name, size.canvas, size.pivot, size.mirror_axis_x) == ("medium", 48, (23, 43), 23)
    for (anim, d), frames in ogre.frames.items():
        for f in frames:
            assert f.image.shape == (48, 48, 4)
    for anim in ("idle", "attack_heavy", "death"):
        for e, w in zip(ogre.frames[(anim, "e")], ogre.frames[(anim, "w")]):
            assert np.array_equal(mirror(e.image, 23)[0], w.image)  # x' = 46 - x, never a flip
    for d in ("s", "e", "n"):  # the feet stand on the baseline, row 43
        assert bbox(ogre.frames[("idle", d)][0].sprite)[3] == 43
    import json
    export(ogre, tmp_path, gifs=False)
    meta = json.loads(next(tmp_path.rglob("ogre.json")).read_text())["meta"]["pixelforge"]
    assert meta["pivot"] == [23, 43] and meta["size_class"] == "medium"


def test_shadow_scales_with_the_footprint(style, ogre):
    from pixelforge.effects import footprint_shadow
    assert footprint_shadow(9, (15, 27)) == dict(style.shadow.rows)  # the rule gives the anchor's
    img = ogre.frames[("idle", "s")][0].image
    shadow = (img[..., 3] == 70)
    rows = np.flatnonzero(shadow.any(axis=1))
    widths = [int(np.ptp(np.flatnonzero(shadow[y]))) + 1 for y in rows]
    full = footprint_shadow(19, (23, 43), 46)  # 19 px of feet: 21 wide, 7 rows
    assert len(full) == 7 and max(x1 - x0 + 1 for x0, x1 in full.values()) == 21
    assert rows.min() >= min(full) and rows.max() == max(full) <= 46  # inside the safe area
    assert max(widths) == 21
    assert footprint_shadow(41, (31, 59), 62)[62]  # a boss's tall shadow is lifted, not cut


def test_w10_flags_a_busy_big_sprite(ogre, style):
    from dataclasses import replace as dc_replace
    from pixelforge.validate import Validator
    v = Validator(ogre.composer)
    f = ogre.frames[("idle", "s")][0]
    assert not [x for x in v.frame(f) if x.rule == "W10"]
    skin = [tuple(int(c) for c in parse_hex(h)) for h in style.materials["skin"].presets["ogre"]]
    noisy = f.sprite.copy()
    body = f.owner == next(i for i, l in enumerate(f.layers) if l.slot == "body")
    for y, x in np.argwhere(body):
        if 30 <= y <= 36 and (x + y) % 2:  # dither the belly
            noisy[y, x, :3] = skin[0] if tuple(noisy[y, x, :3]) != skin[0] else skin[2]
    busy = dc_replace(f, sprite=noisy, image=noisy)
    assert any(x.rule == "W10" for x in v.frame(busy))


def test_drawn_weapons_carry_their_own_smear(ogre):
    from pixelforge.compose import SMEAR
    frames = ogre.frames[("attack_heavy", "e")]
    assert (frames[3].owner == SMEAR).sum() > 20  # the slam traces its arc
    assert not (frames[2].owner == SMEAR).any()


def test_roster_compares_sizes_on_their_pivots(builds, ogre):
    from pixelforge.validate import _on_pivot
    small = np.zeros((32, 32), bool)
    small[20:28, 12:19] = True  # a block standing on the small pivot (15, 27)
    big = np.zeros((48, 48), bool)
    big[36:44, 20:27] = True    # the same block on the medium pivot (23, 43)
    a, b = _on_pivot(small, (15, 27), big, (23, 43))
    assert np.array_equal(a, b)
    assert roster_findings([builds["goblin"], builds["orc"], ogre]) == []


def test_ogre_tell_meets_the_elite_profile(ogre, style):
    adef = ogre.composer.anims["attack_heavy"]
    profile = style.raw["combat"]["timing_profiles"]["elite"]
    durations = [f.duration for f in ogre.frames[("attack_heavy", "e")]]
    assert ogre.recipe.timing_profile == "elite"
    assert sum(durations[:3]) >= profile["telegraph_min_ms"]
    assert set(adef.flags["active"]) == {3, 4}
