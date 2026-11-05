"""The goblin and the goblin chief: the humanoid_small rig (MONSTERS.md sections 5.4 and 6).

14 rows tall: an 8-row head, a 4-row body, 2-row legs. Big pointed ears (their own rigid part)
are the signature; a long nose facing e; a loincloth (cloth) and a crude club (wood, drawn per
frame in the hand). Every frame is assembled from a head, a torso, leg and arm poses and the
club, moved per pose. The chief is the same goblin with a crown, the darker bog hide, red glow
eyes and the elite timing profile: an added trait (the crown changes the silhouette) plus a darker
body, so it reads as different in grayscale too.

Hide shades: 0 #525b2b, 1 #637345, 2 #758c5f.

Run: .venv/bin/python tools/art/goblin.py
"""

from __future__ import annotations

import numpy as np

from artlib import STYLE, empty, g, grid, write_anchors, write_part, write_recipe
from pixelforge.anim import load_anims

RIG = "humanoid_small"
DIRS = ("s", "e", "n")

HEAD = {  # idle frame 0, y 14..21
    "s": ([
        "...1221...",
        "..122221..",
        ".11222221.",
        ".11222221.",
        ".11222211.",
        ".01122110.",
        "..011110..",
        "...0000...",
    ], 11, 14),
    "e": ([  # profile: a long pointed nose at the front, lit in front, the back of the head darker
        "...1122...",
        "..111222..",
        ".1112222..",
        ".01122222.",
        ".011222222",
        ".00112221.",
        "..011111..",
        "...0000...",
    ], 11, 14),
    "n": ([  # the back of the head: lit on top, darker toward the neck
        "...1221...",
        "..122221..",
        ".02222220.",
        ".01222210.",
        ".01122110.",
        ".00111100.",
        "..011110..",
        "...0110...",
    ], 11, 14),
}
EYES = {"s": [(13, 18), (17, 18)], "e": [(18, 17)], "n": []}
TORSO = {  # y 22..25: shoulders, a pot belly
    "s": ([".122221.", "1222222", ".122221.", "..1111."], 12, 22),
    "e": (["..1221.", ".122221", ".122221", "..1111."], 12, 22),
    "n": ([".122221.", "0122210", ".011110.", "..0000."], 12, 22),
}
LOINCLOTH = {  # cloth, y 24..25
    "s": (["..1111.", "...00.."], 12, 24),
    "e": (["..1111.", "...00.."], 12, 24),
    "n": (["..1111.", "...00.."], 12, 24),
}
LEFT_EAR = [(10, 16, 2), (9, 16, 2), (8, 16, 1), (7, 16, 1), (10, 17, 1), (9, 17, 1)]
EARS = {  # hide, rigid on the head: wide wedges pointing out at eye level, the signature
    "s": LEFT_EAR + [(30 - x, y, sh) for x, y, sh in LEFT_EAR],
    "e": [(12, 16, 2), (11, 16, 2), (10, 16, 1), (9, 16, 1), (12, 17, 1), (11, 17, 1)],
    "n": LEFT_EAR + [(30 - x, y, sh) for x, y, sh in LEFT_EAR],
}
CROWN = {  # accent, rigid on the head: three points of gold on top
    "s": [(12, 12, 1), (12, 13, 1), (15, 12, 1), (15, 13, 1), (18, 12, 1), (18, 13, 1),
          (13, 13, 0), (14, 13, 0), (16, 13, 0), (17, 13, 0)],
    "e": [(13, 12, 1), (13, 13, 1), (16, 12, 1), (16, 13, 1), (14, 13, 0), (15, 13, 0)],
    "n": [(12, 12, 1), (12, 13, 1), (15, 12, 1), (15, 13, 1), (18, 12, 1), (18, 13, 1),
          (13, 13, 0), (14, 13, 0), (16, 13, 0), (17, 13, 0)],
}

LEGS = {  # y 26..27, 2 rows; s and n show two legs, e a near and a far leg
    ("s", "stand"): ["..21.12..", "..21.12.."],
    ("s", "step_l"): ["..21.12..", "..21..12."],
    ("s", "step_r"): ["..21.12..", ".21..12.."],
    ("s", "wide"): [".21...12.", ".21...12."],
    ("s", "kneel"): [".2111112.", "........."],
    ("e", "stand"): ["..0021...", "..0021..."],
    ("e", "step_a"): [".00..21..", "00....21."],
    ("e", "step_b"): ["..21.00..", ".21...00."],
    ("e", "wide"): [".00..21..", "00....21."],
    ("e", "kneel"): ["....2211.", "........."],
}
LEGS[("n", "stand")], LEGS[("n", "step_l")] = LEGS[("s", "stand")], LEGS[("s", "step_r")]
LEGS[("n", "step_r")], LEGS[("n", "wide")] = LEGS[("s", "step_l")], LEGS[("s", "wide")]
LEGS[("n", "kneel")] = LEGS[("s", "kneel")]
LEGS[("e", "step_l")], LEGS[("e", "step_r")] = LEGS[("e", "step_a")], LEGS[("e", "step_b")]

ARMS = {  # (points as (x, y, shade) in idle frame 0 coordinates, hand)
    ("s", "rest"): ([(11, 23, 1), (11, 24, 1)], (11, 24)),
    ("s", "up"): ([(11, 22, 1), (11, 21, 1), (10, 21, 1), (10, 20, 1)], (10, 20)),  # 4-connected
    ("s", "fwd"): ([(11, 23, 1), (11, 24, 1), (12, 24, 1), (12, 25, 1)], (12, 25)),
    ("e", "rest"): ([(14, 23, 2), (14, 24, 2)], (14, 24)),
    ("e", "up"): ([(13, 22, 2), (13, 21, 2), (12, 21, 2), (12, 20, 2)], (12, 20)),
    ("e", "fwd"): ([(15, 23, 2), (16, 23, 2), (17, 23, 2)], (17, 23)),
    ("n", "rest"): ([(19, 23, 1), (19, 24, 1)], (19, 24)),
    ("n", "up"): ([(19, 22, 1), (19, 21, 1), (20, 21, 1), (20, 20, 1)], (20, 20)),
    ("n", "fwd"): ([(19, 23, 1), (19, 24, 1), (18, 24, 1), (18, 25, 1)], (18, 25)),
}
ARMS[("s", "bow")] = ([(11, 23, 1), (10, 23, 1), (9, 23, 1)], (9, 23))   # the bow arm held out
ARMS[("e", "bow")] = ([(15, 22, 2), (16, 22, 2), (17, 22, 2)], (17, 22))
ARMS[("n", "bow")] = ([(19, 23, 1), (20, 23, 1), (21, 23, 1)], (21, 23))
FAR_ARM = {"s": [(19, 23, 1), (19, 24, 1)], "e": [], "n": [(11, 23, 0), (11, 24, 0)]}

CLUB = {  # wood (leather), relative to the hand: a stubby club with a knob
    "rest": [(0, 1, 1), (0, 2, 1), (0, 3, 2)],
    "up": [(0, -1, 1), (0, -2, 1), (0, -3, 2), (1, -3, 2)],
    "fwd": [(1, 0, 1), (2, 0, 1), (3, 0, 2), (3, -1, 2)],
    "down": [(1, 1, 1), (1, 2, 1), (2, 3, 2), (2, 2, 2)],
}

# frames: (head dx, dy, torso dy, legs, near arm, club pose[, bow pose]); without a bow pose the
# bow follows the club (rest, raised, dropped)
FRAMES = {
    "idle": [(0, 0, 0, "stand", "rest", "rest"), (0, 1, 1, "stand", "rest", "rest"),
             (0, 1, 1, "stand", "rest", "rest"), (0, 0, 0, "stand", "rest", "rest")],
    "walk": [(0, 0, 0, "step_l", "rest", "rest"), (0, -1, -1, "stand", "rest", "rest"),
             (0, 0, 0, "step_r", "rest", "rest"), (0, -1, -1, "stand", "rest", "rest")],
    "attack_slash": [(-1, 0, 0, "wide", "up", "up"), (-1, 1, 1, "wide", "up", "up"),
                     (1, 0, 0, "wide", "fwd", "fwd"), (1, 0, 0, "wide", "fwd", "down"),
                     (0, 0, 0, "stand", "rest", "rest")],
    "hurt": [(-1, 0, 0, "stand", "rest", "rest"), (-1, 1, 1, "stand", "rest", "rest"),
             (0, 0, 0, "stand", "rest", "rest")],
    "death": [(0, 0, 0, "stand", "rest", "rest"), (0, 1, 1, "wide", "rest", "down"),
              (0, 2, 2, "kneel", "rest", "down"), (0, 2, 2, "kneel", "rest", "down")],
    "victory": [(0, 1, 1, "wide", "rest", "rest"), (0, -2, -2, "stand", "up", "up"),
                (0, 1, 1, "wide", "up", "up"), (0, 0, 0, "stand", "up", "up")],
}
FRAMES["shoot_bow"] = [  # the goblin archer: nock, draw, full draw (held), release, recoil, lower
    (0, 0, 0, "wide", "bow", "rest", "nock"), (-1, 0, 0, "wide", "bow", "rest", "draw"),
    (-1, 0, 0, "wide", "bow", "rest", "full"), (0, 0, 0, "wide", "bow", "rest", "release"),
    (-1, 0, 0, "wide", "bow", "rest", "release"), (0, 0, 0, "stand", "rest", "rest", "rest"),
]
FRAMES["combat_idle"] = None  # an alias of idle (style.json)
BOW_FROM_CLUB = {"rest": "rest", "up": "up", "fwd": "rest", "down": "dropped"}
PULL = {"nock": 0, "draw": 1, "full": 2, "release": 0}


def bow_codes(d: str, pose: str, hand: tuple[int, int]) -> tuple[np.ndarray, list[int]]:
    """The goblin's short bow (leather) with an outline-colored string: held out and drawn
    (nock, draw, full: the string pulled back 0, 1, 2 px, an arrow on it; release: straight and
    empty), at rest beside the hand, raised, or dropped on the ground. Returns the codes and the
    nock point (where the arrow leaves)."""
    c = empty()
    hx, hy = hand
    if pose == "dropped":
        y = 27
        x0 = {"s": 6, "e": 16, "n": 20}[d]
        for x in range(x0, x0 + 6):
            c[y, x] = 1 if x in (x0, x0 + 5) else 2
        for x in range(x0 + 1, x0 + 5):
            c[y - 1, x] = grid.INK
        return c, [x0 + 3, y - 1]
    if pose in ("rest", "up"):  # held upright beside the hand, the string toward the body
        side = {"s": -1, "e": 1, "n": 1}[d]
        # raised facing s or n, the bow stands in the hand's own column so the ear beside it stays
        # one piece
        bx = hx if pose == "up" and d != "e" else hx + side
        top = hy - 3 if pose == "rest" else hy - 5
        limbs = [(bx, top, 1), (bx, top + 1, 2), (bx, top + 2, 2), (bx, top + 3, 2), (bx, top + 4, 1),
                 (bx, top + 5, 1), (bx, top + 6, 0)]
        for x, y, sh in limbs:
            if 0 <= y < 32:
                c[y, x] = sh
        for y in range(top + 1, top + 6):
            if 0 <= y < 32 and c[y, bx + side] == grid.CLEAR and (bx + side, y) != (hx, hy):
                c[y, bx + side] = grid.INK
        return c, [hx, hy]
    pull = PULL[pose]
    if d == "e":  # aimed ahead: limbs in front of the hand, the string pulled back toward the face
        gx, back = hx + 1, -1
    else:  # s and n: the bow upright on the weapon side, the string pulled toward the body
        gx, back = (hx - 1, 1) if d == "s" else (hx + 1, -1)
    for dy, sh in ((0, 1), (-1, 2), (-2, 2), (-3, 1), (1, 1), (2, 1), (3, 0)):
        c[hy + dy, gx] = sh
    c[hy - 4, gx + back] = 1  # the tips curve back toward the archer
    c[hy + 4, gx + back] = 0
    nock = (gx + back * (1 + pull), hy)
    for dy in range(-3, 4):  # the string from tip to tip through the nock
        x = gx + back * (1 + round(pull * (1 - abs(dy) / 4)))
        if c[hy + dy, x] == grid.CLEAR and (x, hy + dy) != (hx, hy):
            c[hy + dy, x] = grid.INK
    if pose != "release":
        if d == "e":  # the arrow on the string, its head past the bow
            for x in range(nock[0] + 1, gx + 3):
                c[hy, x] = 2
            c[hy, gx + 3] = 1
        else:  # facing s or n the arrow points at the viewer: a short light shaft at the nock
            c[hy, nock[0]] = 2
            c[hy + 1, nock[0]] = 2
    return c, list(nock)


def despeckle(codes: np.ndarray) -> np.ndarray:
    """Merge lone shading pixels into their neighbors' shade (ties darker); outline details
    and empty pixels are untouched (as for the wolf)."""
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
            same = [n for n in near if n >= 0]
            if same:  # an edge pixel with one neighbor follows it too
                counts = {n: same.count(n) for n in same}
                out[y, x] = sorted(counts, key=lambda n: (-counts[n], n))[0]
    return out


def dirx(d: str, dx: int) -> int:
    return dx if d == "e" else 0  # leans happen along the facing; s and n bob in place


def body_frame(d: str, spec) -> tuple[np.ndarray, np.ndarray, dict]:
    hdx, hdy, tdy, legs, arm, club = spec[:6]
    hx = dirx(d, hdx)
    codes = empty()
    rows = LEGS.get((d, legs)) or LEGS[(d, "stand")]
    codes = grid.overlay(codes, g(rows, 11, 26))
    for x, y, s in FAR_ARM[d]:
        codes[y + tdy, x + hx] = s
    rows, x0, y0 = TORSO[d]
    codes = grid.overlay(codes, g(rows, x0 + hx, y0 + tdy))
    rows, x0, y0 = HEAD[d]
    codes = grid.overlay(codes, g(rows, x0 + hx, y0 + hdy))
    pts, hand = ARMS[(d, arm)]
    for x, y, s in pts:
        codes[y + tdy, x + hx] = s
    hand = (hand[0] + hx, hand[1] + tdy)
    clubc = empty()
    for dx, dy, s in CLUB[club]:
        sx = -dx if d == "s" else dx
        clubc[hand[1] + dy, hand[0] + sx] = s
    head = (15 + hx, 14 + hdy)
    anchors = {"head": list(head), "chin": [15 + hx, 21 + hdy], "torso": [15 + hx, 22 + tdy],
               "eyes": [15 + hx, 18 + hdy], "hand_near": list(hand), "mouth": [16 + hx, 20 + hdy],
               "foot_near": [13, 27], "foot_far": [17, 27], "planted": []}
    return codes, clubc, anchors


def main() -> None:
    anims = load_anims(STYLE, RIG)
    body, club, anchors = {}, {}, {}
    bow = {}
    for anim, frames in FRAMES.items():
        if frames is None:
            continue
        assert len(frames) == anims[anim].frames, anim
        body[anim], club[anim], bow[anim] = {}, {}, {}
        anchors[anim] = {d: [] for d in DIRS}
        for i, spec in enumerate(frames):
            for d in DIRS:
                codes, clubc, pts = body_frame(d, spec)
                body[anim][(d, i)], club[anim][(d, i)] = despeckle(codes), clubc
                bow_pose = spec[6] if len(spec) > 6 else BOW_FROM_CLUB[spec[5]]
                bow[anim][(d, i)], nock = bow_codes(d, bow_pose, tuple(pts["hand_near"]))
                pts["bow_nock"] = nock
                if i in anims[anim].flags.get("active", ()) and anim != "shoot_bow":
                    hx, hy = pts["hand_near"]
                    pts["hitboxes"] = [{"e": [hx, hy - 4, 7, 7], "s": [8, hy - 1, 14, 8],
                                        "n": [8, 9, 14, 8]}[d]]
                anchors[anim][d].append(pts)
    counts = {a: len(f) for a, f in FRAMES.items() if f is not None}
    write_part("body", RIG, {"material": "hide", "kind": "animated", "lags": False, "rigs": [RIG],
                             "notes": "The goblin: head, pot-bellied body, arms and legs, per pose."},
               body, counts)
    write_part("held_near", "goblin_club", {"material": "leather", "kind": "animated", "lags": False,
                                            "rigs": [RIG], "notes": "A stubby club, drawn per frame."},
               club, counts)
    write_part("held_near", "goblin_bow", {"material": "leather", "kind": "animated", "lags": False,
                                           "rigs": [RIG], "notes": "A short bow with an outline-colored "
                                           "string, drawn per frame; the arrow leaves from bow_nock."},
               bow, counts)

    def rigid(points: dict, origin: str) -> dict:
        cells = {}
        for d in DIRS:
            codes = empty()
            for x, y, s in points[d]:
                codes[y, x] = s
            cells[(d, 0)] = codes
        return {"rigid": cells}

    write_part("ears", "goblin", {"material": "hide", "kind": "rigid", "attach": "head", "origin": "auto",
                                  "lags": False, "rigs": [RIG],
                                  "notes": "Wide pointed ears: the goblin's signature."},
               rigid(EARS, "head"))
    write_part("headwear", "crown", {"material": "accent", "kind": "rigid", "attach": "head",
                                     "origin": "auto", "lags": False, "rigs": [RIG],
                                     "notes": "A three-pointed crown: the goblin chief's trait."},
               rigid(CROWN, "head"))
    cloth = {}
    for d in DIRS:
        rows, x0, y0 = LOINCLOTH[d]
        cloth[(d, 0)] = g(rows, x0, y0)
    write_part("over_torso", "loincloth", {"material": "cloth", "kind": "rigid", "attach": "torso",
                                           "origin": "auto", "lags": False, "rigs": [RIG],
                                           "notes": "A ragged loincloth."}, {"rigid": cloth})
    eyes = {}
    for d in DIRS:
        codes = empty()
        for x, y in EYES[d]:
            codes[y, x] = 0
        eyes[(d, 0)] = codes
    write_part("eyes", "goblin", {"material": "eyes", "kind": "rigid", "attach": "eyes", "origin": "auto",
                                  "lags": False, "rigs": [RIG], "notes": "Beady eyes; one in profile."},
               {"rigid": eyes})
    write_anchors(RIG, anchors)
    common = ["idle", "walk", "combat_idle", "attack_slash", "hurt", "death", "victory"]
    write_recipe("monsters/goblin.yaml", {
        "name": "goblin", "family": "goblin", "rig": RIG, "timing_profile": "enemy", "seed": 1,
        "parts": {"ears": "goblin", "eyes": "goblin", "over_torso": "loincloth",
                  "held_near": "goblin_club"},
        "colors": {"hide": "goblin", "cloth": "mustard", "leather": "brown (anchor)", "eyes": "glow yellow"},
        "anims": common,
    })
    write_recipe("monsters/goblin_chief.yaml", {
        "name": "goblin_chief", "family": "goblin", "rig": RIG, "timing_profile": "elite", "seed": 1,
        "parts": {"ears": "goblin", "eyes": "goblin", "over_torso": "loincloth",
                  "held_near": "goblin_club", "headwear": "crown"},
        "colors": {"hide": "bog", "cloth": "crimson", "leather": "dark", "accent": "gold (anchor)",
                   "eyes": "glow red"},
        "anims": common,
    })
    write_recipe("monsters/goblin_archer.yaml", {
        "name": "goblin_archer", "family": "goblin", "rig": RIG, "timing_profile": "enemy", "seed": 1,
        "parts": {"ears": "goblin", "eyes": "goblin", "over_torso": "loincloth",
                  "held_near": "goblin_bow"},
        "colors": {"hide": "goblin", "cloth": "forest", "leather": "tan", "eyes": "glow yellow"},
        "anims": ["idle", "walk", "combat_idle", "shoot_bow", "hurt", "death", "victory"],
    })
    print("wrote the goblin, the goblin chief and the goblin archer")


if __name__ == "__main__":
    main()
