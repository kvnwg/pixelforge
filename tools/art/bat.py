"""The bat: the flyer rig's body, wings, eyes, anchors and recipe (MONSTERS.md section 5.3).

A round 7 x 6 body with 1 px ears floats with its bottom 7 px above the baseline (y 20); the
pivot and the small ground shadow stay on the ground (rigs.flyer in style.json). Wings are their
own part (membrane material), redrawn per pose: up, mid, down, swept back, crumpled, and flat
on the ground when it falls. Facing s the face shows; facing e the eyes shift forward; facing n
the furry back shows and the wings are drawn over the body.

Fur shades 0 #564a43 .. 3 #9a9085; membrane 0 dark, 1 light.

Run: .venv/bin/python tools/art/bat.py
"""

from __future__ import annotations

import numpy as np

from artlib import empty, g, grid, write_anchors, write_part, write_recipe, STYLE
from pixelforge.anim import load_anims

RIG = "flyer"
DIRS = ("s", "e", "n")
ANIMS = load_anims(STYLE, RIG)
BODY_X, BODY_Y = 12, 14  # the body grid's top-left in the hover's rest position

BODY = {
    "s": [".1...2.",   # y14 ear tips
          ".12232.",   # y15
          "1233332",   # y16 forehead, lit from the upper right
          "1233332",   # y17 eye row
          "1122222",   # y18
          ".11221.",   # y19 belly
          "..010.."],  # y20 tucked feet
    "n": [".1...2.",   # the back: darker, lit on the right shoulder
          ".12221.",
          "1122221",
          "1122221",
          "0011221",
          ".00121.",
          "..000.."],
}
BODY["e"] = BODY["s"]
EYES = {"s": [(14, 17), (16, 17)], "e": [(15, 17), (17, 17)], "n": []}

# Left wings (the right wing mirrors them around x = 15), membrane shades, at rest height:
# (rows, x0, y0)
WINGS = {  # light leading edges, dark membrane in connected staircases (no lone pixels)
    "up": ([".1....",
            ".11...",
            ".111..",
            "..011.",
            "..0011",
            "...001",
            "....00"], 6, 10),
    "mid": ([".11...",
             "111111",
             "100100",
             "1..1.."], 6, 15),
    "down": (["....11",
              "...110",
              "..1100",
              ".1100.",
              "1100.."], 6, 16),
    "back": (["1...",
              "11..",
              "0111",
              "0011"], 8, 13),
    "crumpled": (["111",
                  "001"], 9, 17),
    "flat": ([".11111",
              "110011"], 6, 26),
}

# frames: (body dx, body dy, wings pose); a grounded body rests with its bottom on the baseline
FRAMES = {
    "idle": [(0, 1, "up"), (0, 0, "mid"), (0, -1, "down"), (0, 0, "mid")],
    "attack_swoop": [(0, -2, "up"), (0, -2, "mid"), (1, 4, "back"), (1, 4, "down"), (0, 0, "up")],
    "hurt": [(0, 0, "mid"), (-1, 1, "crumpled"), (0, 0, "mid")],
    "death": [(0, 0, "mid"), (-1, 1, "crumpled"), (0, 3, "crumpled"), (0, 7, "flat"), (0, 7, "flat")],
}


def mirror_cols(codes: np.ndarray) -> np.ndarray:
    out = np.full(codes.shape, grid.CLEAR, np.int8)
    for x in range(codes.shape[1]):
        if 0 <= 30 - x < codes.shape[1]:
            out[:, 30 - x] = codes[:, x]
    return out


def wings_cell(pose: str, dx: int, dy: int) -> np.ndarray:
    rows, x0, y0 = WINGS[pose]
    left = g(rows, x0, y0 + (0 if pose == "flat" else dy))
    both = grid.overlay(left, mirror_cols(left))
    return grid.translate(both, dx, 0)


def body_cell(d: str, dx: int, dy: int) -> np.ndarray:
    return g(BODY[d], BODY_X + dx, BODY_Y + dy)


def anchors_for(anim: str, d: str, dx: int, dy: int, pose: str, i: int) -> dict:
    top, bottom = BODY_Y + dy, BODY_Y + dy + 6
    pts = {
        "head": [15 + dx, top], "torso": [15 + dx, top + 4], "eyes": [15 + dx, top + 3],
        "mouth": {"s": [15 + dx, top + 5], "e": [18 + dx, top + 5], "n": [15 + dx, top + 1]}[d],
        "ground": [15, 27], "planted": [],
    }
    adef = ANIMS[anim]
    if i in adef.flags.get("active", ()):
        # the bat itself is the weapon: its body and swept wings, a little ahead of it
        ahead = {"e": (1, 0), "s": (0, 1), "n": (0, -1)}[d]
        pts["hitboxes"] = [[9 + dx + ahead[0], top - 1 + ahead[1], 13, 10]]
    return pts


def main() -> None:
    body, wings, anchors = {}, {}, {}
    for anim, frames in FRAMES.items():
        assert len(frames) == ANIMS[anim].frames, anim
        body[anim], wings[anim] = {}, {}
        anchors[anim] = {d: [] for d in DIRS}
        for i, (dx, dy, pose) in enumerate(frames):
            for d in DIRS:
                body[anim][(d, i)] = body_cell(d, dx, dy)
                wings[anim][(d, i)] = wings_cell(pose, dx, dy)
                anchors[anim][d].append(anchors_for(anim, d, dx, dy, pose, i))
    counts = {anim: len(f) for anim, f in FRAMES.items()}
    write_part("body", RIG, {"material": "fur", "kind": "animated", "lags": False, "rigs": [RIG],
                             "notes": "The bat's round body with 1 px ears."}, body, counts)
    write_part("wings", "bat", {"material": "membrane", "kind": "animated", "lags": False,
                                "rigs": [RIG], "notes": "Membrane wings, redrawn per beat."},
               wings, counts)
    eyes = {}
    for d in DIRS:
        codes = empty()
        for x, y in EYES[d]:
            codes[y + FRAMES["idle"][0][1], x] = 0
        eyes[(d, 0)] = codes
    write_part("eyes", "bat", {"material": "eyes", "kind": "rigid", "attach": "eyes", "origin": "auto",
                               "lags": False, "rigs": [RIG],
                               "notes": "Two eyes close together; forward facing e; none facing n."},
               {"rigid": eyes})
    write_anchors(RIG, anchors)
    write_recipe("monsters/bat.yaml", {
        "name": "bat", "rig": RIG, "timing_profile": "enemy", "seed": 1,
        "parts": {"wings": "bat", "eyes": "bat"},
        "colors": {"fur": "brown", "membrane": "dusk", "eyes": "glow red"},
        "anims": ["idle", "combat_idle", "move", "attack_swoop", "hurt", "death"],
    })
    print("wrote the bat")


if __name__ == "__main__":
    main()
