"""Kevin, Rolling Knight's one Absolute knight, remade in pixelforge's format (2026-11-06).

The game's own sheet for him (drawn outside pixelforge) broke the format: a 48 px cell with its own
pivot, hand-drawn near-black outlines, 44 colors of its own, no run, and a sword whose hilt floats
away from his hand. Here he is a recipe like every other knight.
"""

from __future__ import annotations

import numpy as np
import pytest

from pixelforge.build import build


@pytest.fixture(scope="module")
def kevin(root, style):
    return build(root, "rk_kevin", style=style)


def test_kevin_follows_the_format_of_the_other_knights(kevin, root, style):
    blade = build(root, "rk_blade", style=style, validate=False)
    assert [str(f) for f in kevin.findings] == []
    size = kevin.composer.rig.size
    assert (kevin.recipe.rig, size.canvas, size.pivot) == ("humanoid", 32, (15, 27))
    assert kevin.recipe.anims == blade.recipe.anims  # the Blade's whole set, run included
    outline = style.outline.color.lstrip("#")
    f = kevin.frames[("idle", "s")][0]
    colors = {"%02x%02x%02x" % tuple(int(v) for v in p) for p in f.sprite[f.sprite[..., 3] == 255][:, :3]}
    assert outline in colors  # the generated outline, not a hand-drawn line of its own


def test_kevin_holds_the_sword_by_its_grip(kevin):
    """In every stance and gait, the hilt touches the hand that holds it."""
    for anim in ("idle", "walk", "run", "combat_idle"):
        for d in ("s", "e", "n", "w"):
            for i, f in enumerate(kevin.frames[(anim, d)]):
                hilt = next(l for l in f.layers if l.slot == "held_near_trim")
                ys, xs = np.nonzero(hilt.image[..., 3] == 255)
                hx, hy = f.points["hand_near"]
                assert min(abs(x - hx) + abs(y - hy) for x, y in zip(xs, ys)) <= 1, (anim, d, i)
