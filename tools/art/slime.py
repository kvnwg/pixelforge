"""The slime: the blob rig's base body, gloss, eyes, anchors and recipe (MONSTERS.md section 5.1).

The body is a dome drawn from style/examples/slime_draft.png: 11 px wide, 9 rows with a top nub,
lit from the upper right (light shade high and right, dark rim low and left). Squash and stretch
are redrawn shapes, never scaled. The body looks the same from every side; the eyes (their own
part, eyes material) sit in the lower half facing s, shift forward facing e, and are hidden
facing n. The 2 px gloss is its own part (slime_highlight material). Both follow anchors.

Slime shades: 0 #3c6553 rim, 1 #4f7c6d, 2 #659488, 3 #7bada5 light. 'O' marks an outline-colored
pixel drawn on purpose (the open mouth when spitting).

Run: .venv/bin/python tools/art/slime.py
"""

from __future__ import annotations

import numpy as np

from artlib import ROOT, STYLE, empty, g, write_anchors, write_part, write_recipe
from pixelforge.anim import load_anims

RIG = "blob"
DIRS = ("s", "e", "n")
ANIMS = load_anims(STYLE, RIG)

# (rows, x0, y0, eyes anchor, gloss anchor): every shape rests on the baseline (y 27)
SHAPES = {
    "base": ([
        "....333....",
        "..2333332..",
        ".223333332.",
        "12223333322",
        "12222223322",
        "11222222222",
        "11222222211",
        "01112222111",
        ".001111110.",
    ], 10, 19, (15, 24), (16, 21)),
    "squash": ([  # 2 px wider, 1 row shorter
        ".....333.....",
        "...2333332...",
        ".22333333332.",
        "1222333333322",
        "1122222233322",
        "1112222222211",
        "0111122221111",
        ".00111111110.",
    ], 9, 20, (15, 25), (17, 22)),
    "stretch": ([  # 2 px narrower, 2 rows taller
        "...333...",
        "..23332..",
        ".2233332.",
        "122333332",
        "122223332",
        "122222332",
        "112222222",
        "112222221",
        "111222211",
        "011122111",
        ".0011110.",
    ], 11, 17, (15, 23), (16, 19)),
    "deep": ([  # deep squash: 4 px wider, 3 rows shorter
        "......333......",
        "...223333322...",
        ".2223333333322.",
        "112222223333221",
        "011112222221111",
        ".0011111111110.",
    ], 8, 22, (15, 25), (17, 23)),
    "swell": ([  # inflating to spit
        ".....333.....",
        "...2333332...",
        "..223333332..",
        ".22233333332.",
        "1222233333322",
        "1222222233322",
        "1122222222222",
        "1112222222211",
        "0111122221111",
        ".00111111110.",
    ], 9, 18, (15, 24), (17, 21)),
    "swell2": ([
        "......333......",
        "....2333332....",
        "..22333333332..",
        ".2223333333332.",
        "122223333333322",
        "122222223333322",
        "112222222222222",
        "112222222222221",
        "111222222222211",
        "011112222221111",
        ".0011111111110.",
    ], 8, 17, (15, 24), (18, 20)),
    "melt": ([
        "......333......",
        "...222333322...",
        ".1122223333211.",
        "011112222211110",
        ".0011111111100.",
    ], 8, 23, (15, 25), (17, 24)),
    "puddle": ([  # 15 x 4
        "....2233322....",
        ".1122233332211.",
        "011112222211110",
        ".0011111111100.",
    ], 8, 24, (15, 26), (17, 25)),
}

EYES = {"s": [(-2, 0), (2, 0)], "e": [(0, 0), (3, 0)], "n": []}  # relative to the eyes anchor
GLOSS = [(0, 0), (1, 1)]  # relative to the gloss anchor
MOUTH = {"s": [(-1, 1), (0, 1), (1, 1)], "e": [(4, 1), (5, 1)], "n": []}  # spit: the open mouth

# frame tables: (shape, lift in px, mouth open)
FRAMES = {
    "idle": [("base", 0, False), ("squash", 0, False), ("base", 0, False), ("stretch", 0, False)],
    "move": [("squash", 0, False), ("stretch", 0, False), ("base", 3, False), ("base", 4, False),
             ("stretch", 1, False), ("squash", 0, False)],
    "attack_slam": [("deep", 0, False), ("squash", 0, False), ("stretch", 3, False),
                    ("deep", 0, False), ("stretch", 0, False), ("base", 0, False)],
    "attack_spit": [("swell", 0, False), ("swell2", 0, False), ("squash", 0, True),
                    ("stretch", 0, False), ("base", 0, False)],
    "hurt": [("base", 0, False), ("deep", 0, False), ("base", 0, False)],
    "death": [("base", 0, False), ("squash", 0, False), ("melt", 0, False), ("puddle", 0, False)],
}


def body_cell(shape: str, lift: int, mouth: bool, d: str) -> np.ndarray:
    rows, x0, y0, eyes, _ = SHAPES[shape]
    codes = g(rows, x0, y0 - lift)
    if mouth:
        ex, ey = eyes
        for dx, dy in MOUTH[d]:
            codes[ey - lift + dy, ex + dx] = -2  # grid.INK: an outline-colored mouth
    return codes


def anchors_for(anim: str, d: str, shape: str, lift: int, i: int) -> dict:
    rows, x0, y0, eyes, gloss = SHAPES[shape]
    width, height = len(rows[0]), len(rows)
    top, bottom = y0 - lift, y0 - lift + height - 1
    ex, ey = eyes[0], eyes[1] - lift
    mouth = {"s": [ex, ey + 1], "e": [x0 + width - 1, ey + 1], "n": [15, top + 1]}[d]
    pts = {
        "head": [15, top], "torso": [15, (top + bottom) // 2], "eyes": [ex, ey],
        "gloss": [gloss[0], gloss[1] - lift], "mouth": mouth,
        "ground": [17 if d == "e" else 15, 27], "foot_near": [15, bottom],
        "planted": [] if lift else ["foot_near"],
    }
    adef = ANIMS[anim]
    if i in adef.flags.get("active", ()) and anim == "attack_slam":
        pts["hitboxes"] = [[x0 - 2, top - 2, width + 4, height + 3]]
    return pts


def main() -> None:
    body: dict = {}
    anchors: dict = {}
    for anim, frames in FRAMES.items():
        assert len(frames) == ANIMS[anim].frames, anim
        body[anim] = {}
        anchors[anim] = {d: [] for d in DIRS}
        for i, (shape, lift, mouth) in enumerate(frames):
            for d in DIRS:
                body[anim][(d, i)] = body_cell(shape, lift, mouth, d)
                anchors[anim][d].append(anchors_for(anim, d, shape, lift, i))
    counts = {anim: len(f) for anim, f in FRAMES.items()}
    write_part("body", RIG, {"material": "slime", "kind": "animated", "lags": False, "rigs": [RIG],
                             "notes": "The slime's dome, redrawn for every squash and stretch."},
               body, counts)

    def rigid_cells(points_by_dir, origin_name):
        cells = {}
        for d in DIRS:
            codes = empty()
            ox, oy = anchors["idle"][d][0][origin_name]
            for dx, dy in points_by_dir[d]:
                codes[oy + dy, ox + dx] = 0
            cells[(d, 0)] = codes
        return {"rigid": cells}

    write_part("gloss", "slime", {"material": "slime_highlight", "kind": "rigid", "attach": "gloss",
                                  "origin": "auto", "lags": False, "rigs": [RIG],
                                  "notes": "The 2 px gloss high on the light side."},
               rigid_cells({d: GLOSS for d in DIRS}, "gloss"))
    write_part("eyes", "slime", {"material": "eyes", "kind": "rigid", "attach": "eyes",
                                 "origin": "auto", "lags": False, "rigs": [RIG],
                                 "allow_singletons": {}, "notes": "Two 1 px eyes in the lower "
                                 "half, 3 px apart; forward facing e; none facing n."},
               rigid_cells(EYES, "eyes"))
    write_anchors(RIG, anchors)
    write_recipe("monsters/slime.yaml", {
        "name": "slime", "rig": RIG, "timing_profile": "enemy", "seed": 1,
        "parts": {"gloss": "slime", "eyes": "slime"},
        "colors": {"slime": "mint", "slime_highlight": "mint", "eyes": "dark"},
        "anims": ["idle", "combat_idle", "move", "attack_slam", "attack_spit", "hurt", "death"],
    })
    print("wrote the slime")


if __name__ == "__main__":
    main()
