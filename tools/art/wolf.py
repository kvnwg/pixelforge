"""The wolf: the quadruped rig's body, tail, eyes, anchors and recipe (MONSTERS.md section 5.2).

Side view (e) first: a chibi wolf about 21 px long and 14 tall, a big head (8 x 7) with two
pointed ears and a short snout, a 12 x 6 body, 3 px legs with paws, and a bushy tail that trails
by a frame (its own part, lags). Near legs are lighter than far legs so the four legs never merge.
Every frame is assembled from components moved per pose: torso and head offsets, a pose per leg,
the tail riding the rump. Facing s the head sits over the chest with the front legs below;
facing n the rump, tail and hind legs show with the ears peeking over.

Fur shades: 0 darkest .. 3 lightest, lit from the upper right; 'O' = an outline-colored detail
(nose, mouth line).

Run: .venv/bin/python tools/art/wolf.py
"""

from __future__ import annotations

import numpy as np

from artlib import STYLE, empty, g, grid, write_anchors, write_part, write_recipe
from pixelforge.anim import load_anims

RIG = "quadruped"
DIRS = ("s", "e", "n")

# ============================================================================== side view (e)
TORSO_E = ([  # x 8..18, y 17..23: shoulders high, a deep chest, a tucked belly
    ".222222222.",
    "12333333322",
    "12233333322",
    "11222222221",
    "01111122211",
    ".011...1111",
    "..0.....00.",
], 8, 17)
HEADS_E = {  # x 16..24, y 12..20: a big round skull, pointed ears, a short snout
    "rest": ([
        "..2..2...",
        ".122122..",
        "122333...",
        "1223333..",
        "12333333.",
        "122333330",
        ".12222221",
        "..11111..",
        "...11....",
    ], 16, 12),
    "ears_back": ([  # crouching: ears laid back
        ".........",
        ".........",
        "1222333..",
        "1223333..",
        "12333333.",
        "122333330",
        ".12222221",
        "..11111..",
        "...11....",
    ], 16, 12),
    "snarl": ([  # the jaw drops 1 px away from the snout
        ".........",
        ".........",
        "1222333..",
        "1223333..",
        "12333333.",
        "12233333O",
        ".122OOOO.",
        "..112221.",
        "...11....",
    ], 16, 12),
    "bite": ([  # jaws wide open
        ".........",
        ".........",
        "1222333..",
        "12233333.",
        "123333333",
        "1223OOOO0",
        ".12......",
        "..12221..",
        "...11....",
    ], 16, 12),
    # the howl's heads are the rest head tipped back over a stretched neck (x 12..22, y 4..14)
    "howl_up": ([  # swinging up: the snout at about 45 degrees, ears laid back
        ".......O.",
        "......232",
        "..11.2332",
        ".1112333.",
        ".12233332",
        "1223333321",
        ".12233321.",
    ], 13, 6),
    "howl": ([  # the snout pointed at the sky, the mouth open under the nose, ears flat back
        "....O....",
        "....3O...",
        "....32...",
        "...2332..",
        "11.23332.",
        ".12333332",
        ".12333332",
        "..1233321",
    ], 12, 4),
}
EYE_E = {"rest": (21, 16), "ears_back": (21, 16), "snarl": (21, 16), "bite": (21, 16),
         "howl_up": (17, 10), "howl": (16, 9)}
MOUTH_E = {"rest": (24, 17), "ears_back": (24, 17), "snarl": (24, 18), "bite": (24, 18),
           "howl_up": (20, 6), "howl": (16, 4)}  # the howl's mouth is the raised muzzle's tip

# legs: 2 px wide from y 23 to the paw row at y 27 (3 px, toes forward); near legs light,
# far legs one shade darker and 2 px behind their near leg so a pair reads as two legs
LEGS = {  # paws are one shade so their toe pixel never stands alone
    "stand": ["21", "21", "21", "21", "222"],
    "fwd": [".21", ".21", "21.", "21.", "222"],    # reaching forward: the paw lands 1 px ahead
    "back": ["21.", "21.", ".21", ".21", ".222"],  # pushing back
    "lift": ["21", "21", "21", "222", "..."],      # paw raised 1 row
    "tuck": ["21", "21", "222", "...", "..."],     # folded up (airborne, crouch)
    "kneel": ["21", "222", "...", "...", "..."],   # folded under a lowered body
    "brace": ["21", "21", "21", "21", "21", "21", "222"],  # straight under a lifted chest
}
LEG_TOP = {"brace": 21}  # the row a leg's first pixel starts on (23 unless listed)
LEG_X = {"far_back": 8, "near_back": 10, "far_front": 15, "near_front": 17}
FAR = {"far_back", "far_front"}

# the howl lifts the chest: the torso's front rises 2 px over braced front legs and the neck
# stretches up out of it (the head covers the neck's top rows until it rises past them)
TORSO_TILT = ([  # x 8..21, y 15..23
    "...........22.",
    "........22233.",
    ".2222222333332",
    "1233333333332.",
    "1223333333322.",
    "112222222221..",
    "0111112221....",
    ".011...111....",
    "..0...........",
], 8, 15)
NECK_E = (14, "1223332")  # the neck's first column and its shade per column (nape to throat)

TAIL_E = ([  # x 3..9, y 12..18: bushy, raised; rides the rump and trails by a frame
    ".222...",
    "12332..",
    "1223321",
    ".122221",
    "..1122.",
    "....11.",
], 3, 12)

HEADS_E["flick"] = ([  # idle frame 2: the front ear flicks back
    "..2......",
    ".122.22..",
    "122333...",
    "1223333..",
    "12333333.",
    "122333330",
    ".12222221",
    "..11111..",
    "...11....",
], 16, 12)
EYE_E["flick"], MOUTH_E["flick"] = EYE_E["rest"], MOUTH_E["rest"]

LYING = ([  # death: fallen on its side, legs out, the tail flat (x 4..25, y 22..27)
    "........22.......2....",
    "....11222333322.1223..",
    "1112223333333331233330",
    "11122222222222222222.1",
    ".0111111111111111111..",
    "..1.1.......1.1.......",
], 4, 22)

# ============================================================================== front view (s)
HEADS_S = {  # x 11..19, y 12..19: ears up, eyes either side, the muzzle below
    "rest": ([
        ".2.....2.",
        "122...221",
        "123333332",
        "123333332",
        "112333211",
        ".1123211.",
        "..12O21..",
        "...111...",
    ], 11, 12),
    "snarl": ([
        ".........",
        "122...221",
        "123333332",
        "123333332",
        "112333211",
        ".1123211.",
        "..1OOO1..",
        "...121...",
    ], 11, 12),
    "howl": ([  # muzzle raised: the head tips back, the open mouth shows
        ".2.....2.",
        "122.O.221",
        "123323332",
        "123333332",
        "112333211",
        ".1122211.",
        "..11111..",
    ], 11, 12),
}
HEADS_S["howl_up"] = (HEADS_S["rest"][0], 11, 9)  # lifted on the throat, the face still to us
HEADS_S["howl"] = ([  # tipped back: the nose points up out of the head, the ears lie back,
    "....O....",      # the eyes ride high and the open mouth shows from below
    "...232...",
    ".1.232.1.",
    "122333221",
    "123333321",
    "112333211",
    ".112O211.",
    "..12O21..",
    "...121...",
], 11, 6)
THROAT_S = ([  # x 13..17, y 14..17: the stretched neck between the lifted head and the chest
    "..12321..",
    "..12321..",
    "..12321..",
    ".1123211.",
], 11, 14)
HEADS_S["ears_back"] = HEADS_S["rest"]
HEADS_S["flick"] = HEADS_S["rest"]
HEADS_S["bite"] = HEADS_S["snarl"]
EYES_S = [(-2, 0), (2, 0)]  # relative to the eyes anchor (15, 15)
CHEST_S = ([  # x 11..19, y 19..23
    ".1222221.",
    "122333221",
    "112222211",
    "011111110",
    ".0.....0.",
], 11, 19)
LEG_X_S = {"near_front": 12, "far_front": 17}  # the character's right front leg on the viewer's left

# ============================================================================== back view (n)
RUMP_N = ([  # x 10..20, y 15..23: the ears peek over the back; the rump fills the view
    ".11.....11.",
    ".12.....21.",
    "12222222221",
    "12233333221",
    "12333333321",
    "12233333221",
    "11222222211",
    ".0111111110",
    "..0.....0..",
], 10, 15)
LEG_X_N = {"near_back": 18, "far_back": 11}  # seen from behind: the right hind leg on the right
HEADS_N = {  # the howl from behind: the back of the head rises over the shoulders, the ears
    "howl": ([   # up as in the rest pose and the snout tip poking up between them; drawn behind
        "....2....",  # the rump
        ".1.232.1.",
        "12.232.21",
        "122333221",
        "112333211",
        ".1122211.",
        "..12221..",
        "..12221..",
        "..12221..",
    ], 11, 8),
}
HEADS_N["howl_up"] = (HEADS_N["howl"][0], 11, 11)  # halfway up, partly behind the back
NECK_N = (["..12221..", "..12221..", "..12221.."], 11, 14)

# tails, one cell per direction in idle frame 0's place; they ride the `tail` anchor and lag
TAILS = {"e": ([".222...", "12332..", "1223321", ".122221", "..1122.", "....11."], 3, 12),
         "s": ([".1", "12", "2."], 19, 18),
         "n": ([".2.", "232", "232", "222", "11."], 14, 10)}

def paste(base: np.ndarray, rows: list[str], x0: int, y0: int) -> np.ndarray:
    return grid.overlay(base, g(rows, x0, y0))


def darker(rows: list[str]) -> list[str]:
    """The far legs: one shade darker so the legs never twin."""
    return ["".join(str(max(int(c) - 1, 0)) if c.isdigit() else c for c in r) for r in rows]


def side_body(head: str, tdx: int, tdy: int, hdx: int, hdy: int, legs: dict, ldy: int = 0,
              tilt: bool = False, neck: bool = False) -> np.ndarray:
    """Far legs, the torso (tilted: the chest lifted), near legs, the neck, then the head."""
    codes = empty()
    for name in ("far_back", "far_front"):
        kind = legs[name]
        codes = paste(codes, darker(LEGS[kind]), LEG_X[name], LEG_TOP.get(kind, 23) + ldy)
    rows, x0, y0 = TORSO_TILT if tilt else TORSO_E
    torso = g(rows, x0 + tdx, y0 + tdy)
    codes = grid.overlay(codes, torso)
    for name in ("near_back", "near_front"):
        kind = legs[name]
        codes = paste(codes, LEGS[kind], LEG_X[name], LEG_TOP.get(kind, 23) + ldy)
    rows, x0, y0 = HEADS_E[head]
    top = g(rows, x0 + hdx, y0 + hdy)
    if neck:  # stretched between the raised head and the chest, whatever their offsets
        nx, shades = NECK_E
        for i, shade in enumerate(shades):
            x = nx + i + hdx
            above, below = np.flatnonzero(top[:, x] >= 0), np.flatnonzero(torso[:, x] >= 0)
            if above.size and below.size:
                codes[above.max() + 1:below.min(), x] = int(shade)
    return grid.overlay(codes, top)


# ============================================================================== frames
# (torso dx, dy, head, head dx, dy, legs, legs dy, tail dy)
STAND = {"far_back": "stand", "near_back": "stand", "far_front": "stand", "near_front": "stand"}


def L(nb="stand", fb="stand", nf="stand", ff="stand"):
    return {"near_back": nb, "far_back": fb, "near_front": nf, "far_front": ff}


def F(t=(0, 0), head="rest", h=(0, 0), legs=None, ldy=0, tail=0, lying=False, tilt=False,
      neck=False):
    """tail: the tail anchor's drop, one number or one per view; tilt: the chest lifted over
    braced front legs; neck: the stretched neck drawn under a raised head."""
    return {"t": t, "head": head, "h": h, "legs": legs or STAND, "ldy": ldy, "tail": tail,
            "lying": lying, "tilt": tilt, "neck": neck}


def tail_drop(spec, d: str) -> int:
    return spec["tail"][d] if isinstance(spec["tail"], dict) else spec["tail"]


BRACE = {"far_back": "stand", "near_back": "stand", "far_front": "brace", "near_front": "brace"}


FRAMES = {
    "idle": [F(), F((0, 1), h=(0, 1)), F((0, 1), "flick", (0, 1)), F()],
    "walk": [F(legs=L("back", "fwd", "fwd", "back")), F((0, -1), legs=L("stand", "lift", "lift", "stand")),
             F(h=(0, -1), legs=L("fwd", "back", "back", "fwd")),
             F((0, -1), legs=L("lift", "stand", "stand", "lift"))],
    "run": [F((0, -1), legs=L("fwd", "fwd", "back", "back")),
            F((0, -2), h=(1, -2), legs=L("back", "back", "fwd", "fwd"), ldy=-1),
            F((0, -3), h=(1, -3), legs=L("tuck", "tuck", "tuck", "tuck"), ldy=-2),
            F((0, -1), h=(1, -1), legs=L("back", "back", "stand", "stand")),
            F((0, 1), h=(0, 1), legs=L("stand", "stand", "back", "back")),
            F((0, 0), legs=L("back", "back", "back", "back"))],
    "attack_bite": [F((0, 1), "ears_back", (0, 2), tail=-1),
                    F((0, 1), "snarl", (0, 2), tail=-1),
                    F((1, 0), "bite", (2, 0), L("back", "back", "fwd", "fwd")),
                    F((1, 0), "rest", (2, 0), L("back", "back", "fwd", "fwd")),
                    F()],
    # the howl (MONSTERS.md section 5.2): draw breath (dip, chin tucked), throw the head back
    # (chest up, snout at 45 degrees), howl at the sky, keep stretching a pixel through the
    # hold, then lower: the body levels first and the head follows a frame later
    "howl": [F((0, 1), "ears_back", (-1, 2), tail=1),
             F(head="howl_up", legs=BRACE, tilt=True, neck=True, tail={"e": 1, "s": 0, "n": 4}),
             F(head="howl", legs=BRACE, tilt=True, neck=True, tail={"e": 2, "s": 1, "n": 8}),
             F(head="howl", h=(0, -1), legs=BRACE, tilt=True, neck=True, tail={"e": 2, "s": 1, "n": 8}),
             F(head="howl_up", h=(2, 3), neck=True, tail=1)],
    "hurt": [F(), F((0, 1), "ears_back", (-1, 1), tail=1), F()],
    "death": [F(), F((0, 2), "ears_back", (0, 2), L("tuck", "tuck", "tuck", "tuck"), ldy=2),
              F(lying=True), F(lying=True)],
}


def despeckle(codes: np.ndarray) -> np.ndarray:
    """Merge lone shading pixels into their neighbors: a pixel whose shade no 4-neighbor shares
    takes the shade most of its fur neighbors have (ties go darker). Outline-colored details
    and empty pixels are untouched. Keeps assembled poses free of single-pixel noise (W3)."""
    out = codes.copy()
    h, w = codes.shape
    for y in range(h):
        for x in range(w):
            v = codes[y, x]
            if v < 0:
                continue
            near = [codes[y + dy, x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= y + dy < h and 0 <= x + dx < w]
            if v in near:
                continue
            fur = [n for n in near if n >= 0]
            if len(fur) >= 2:
                counts = {n: fur.count(n) for n in fur}
                out[y, x] = sorted(counts, key=lambda n: (-counts[n], n))[0]
    return out


def side_frame(spec) -> np.ndarray:
    if spec["lying"]:
        rows, x0, y0 = LYING
        return g(rows, x0, y0)
    tdx, tdy = spec["t"]
    hdx, hdy = spec["h"]
    return side_body(spec["head"], tdx, tdy, hdx, hdy, spec["legs"], spec["ldy"], spec["tilt"],
                     spec["neck"])


def front_frame(spec, d) -> np.ndarray:
    if spec["lying"]:
        rows, x0, y0 = LYING
        return g(rows, x0, y0)
    tdx, tdy = spec["t"]
    hdx, hdy = spec["h"]
    codes = empty()
    if d == "s":
        for name, x in LEG_X_S.items():
            kind = spec["legs"][name]
            rows = [r.replace(".", "")[:2].ljust(2, ".") for r in LEGS[kind]]
            codes = paste(codes, rows, x, LEG_TOP.get(kind, 23) + spec["ldy"])
        rows, x0, y0 = CHEST_S
        codes = paste(codes, rows, x0, y0 + tdy - spec["tilt"])  # the lifted chest
        if spec["neck"]:
            rows, x0, y0 = THROAT_S
            codes = paste(codes, rows, x0, y0 + tdy)
        rows, x0, y0 = HEADS_S[spec["head"]]
        codes = paste(codes, rows, x0, y0 + hdy)
    else:
        for name, x in LEG_X_N.items():
            rows = LEGS[spec["legs"][name]]
            codes = paste(codes, [r.replace(".", "")[:2].ljust(2, ".") for r in rows], x, 23 + spec["ldy"])
        rows, x0, y0 = RUMP_N
        if spec["head"] in HEADS_N:  # the raised head over the back; the rump hides its ears
            if spec["neck"]:
                nrows, nx, ny = NECK_N
                codes = paste(codes, nrows, nx, ny + hdy)
            hrows, hx, hy = HEADS_N[spec["head"]]
            codes = paste(codes, hrows, hx, hy + hdy)
            rows, y0 = rows[2:], y0 + 2
        codes = paste(codes, rows, x0, y0 + tdy)
    return codes


def anchors_for(anim: str, d: str, spec, i: int, adef) -> dict:
    tdx, tdy = spec["t"]
    hdx, hdy = spec["h"]
    lying = spec["lying"]
    drop, name = tail_drop(spec, d), spec["head"]
    if d == "e":
        ex, ey = EYE_E[name]
        mx, my = MOUTH_E[name]
        eyes, mouth = [ex + hdx, ey + hdy], [mx + hdx, my + hdy]
        hx, hy = (16, 6) if name.startswith("howl") else (20, 12)
        head, tail = [hx + hdx, hy + hdy], [8 + tdx, 18 + tdy + drop]
    elif d == "s":
        if name == "howl":  # tipped back: the eyes high, the mouth opens at the top
            eyes, mouth, head = [15, 10 + hdy], [15, 6 + hdy], [15, 7 + hdy]
        else:
            eyes, mouth, head = [15, 15 + hdy], [15, 18 + hdy], [15, 12 + hdy]
        tail = [19, 19 + tdy + drop]
    else:
        if name in HEADS_N:  # the raised head: the snout tip on top
            top = HEADS_N[name][2] + hdy
            eyes, mouth, head = [15, top + 3], [15, top], [15, top + 1]
        else:
            eyes, mouth, head = [15, 15 + tdy], [15, 13 + tdy], [15, 15 + tdy]
        tail = [15, 15 + tdy + drop]
    pts = {"head": head, "torso": [13 + tdx if d == "e" else 15, 19 + tdy], "eyes": eyes,
           "mouth": mouth, "tail": tail, "ground": [15, 27]}
    if lying:  # the lying drawing has its own flat tail
        pts.update({"head": [21, 23], "eyes": [21, 24], "mouth": [24, 25], "tail": [8, 22],
                    "torso": [13, 24], "hide": ["tail"]})
    if i in adef.flags.get("active", ()):
        ahead = {"e": [mouth[0] - 2, mouth[1] - 5, 8, 9], "s": [10, mouth[1] - 2, 11, 10],
                 "n": [10, 6, 11, 10]}[d]
        pts["hitboxes"] = [ahead]
    pts["planted"] = []
    return pts


def main() -> None:
    anims = load_anims(STYLE, RIG)
    body, anchors = {}, {}
    for anim, frames in FRAMES.items():
        assert len(frames) == anims[anim].frames, anim
        body[anim] = {}
        anchors[anim] = {d: [] for d in DIRS}
        for i, spec in enumerate(frames):
            for d in DIRS:
                body[anim][(d, i)] = despeckle(side_frame(spec) if d == "e" else front_frame(spec, d))
                anchors[anim][d].append(anchors_for(anim, d, spec, i, anims[anim]))
    counts = {anim: len(f) for anim, f in FRAMES.items()}
    write_part("body", RIG, {"material": "fur", "kind": "animated", "lags": False, "rigs": [RIG],
                             "notes": "The wolf: head, body and legs, assembled per pose."},
               body, counts)
    tails = {}
    for d in DIRS:
        rows, x0, y0 = TAILS[d]
        tails[(d, 0)] = despeckle(g(rows, x0, y0))
    write_part("tail", "wolf", {"material": "fur", "kind": "rigid", "attach": "tail", "origin": "auto",
                                "lags": True, "rigs": [RIG],
                                "notes": "A bushy tail riding the rump; it trails by a frame."},
               {"rigid": tails})
    eyes = {}
    for d in DIRS:
        codes = empty()
        ex, ey = anchors["idle"][d][0]["eyes"]
        if d == "e":
            codes[ey, ex] = 0
        elif d == "s":
            for dx, dy in EYES_S:
                codes[ey + dy, ex + dx] = 0
        eyes[(d, 0)] = codes
    write_part("eyes", "wolf", {"material": "eyes", "kind": "rigid", "attach": "eyes", "origin": "auto",
                                "lags": False, "rigs": [RIG], "notes": "One eye in profile, two facing s."},
               {"rigid": eyes})
    write_anchors(RIG, anchors)
    write_recipe("monsters/wolf.yaml", {
        "name": "wolf", "family": "wolf", "rig": RIG, "timing_profile": "enemy", "seed": 1,
        "parts": {"tail": "wolf", "eyes": "wolf"},
        "colors": {"fur": "gray", "eyes": "glow yellow"},
        "anims": ["idle", "combat_idle", "walk", "run", "attack_bite", "howl", "hurt", "death"],
    })
    print("wrote the wolf")


if __name__ == "__main__":
    main()
