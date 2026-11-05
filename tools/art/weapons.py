"""Held item poses for the combat animations: weapon cells, smears, hitboxes and named points.

Every pose is drawn per direction as clean pixel lines in the item's own shades (characters are
never rotated: each angle is drawn, here by code). Geometry is written relative to the hand: the
cell puts the hand at the idle frame 0 hand anchor, and the compositor moves it with the hand.

Line kinds (from the grip outward; sx, sy are -1, 0 or +1):
  v        straight up or down          h        straight forward or back
  steep    2 rows per column (about 63 degrees)
  shallow  2 columns per row (about 27 degrees)
Steep and shallow lines come in pairs of pixels, so a 1 px blade never breaks into singletons.
Facing n the poses mirror s (x -> 30 - x): the weapon arm is on the outside in both views.

Files per item (parts/<slot>/<variant>/):
  pose_<name>.png         the item in front (its usual z-order place)
  pose_<name>_behind.png  the item behind the character (a weapon cocked behind the head)
  smear_<name>.png        held_near only: the strike's smear, drawn after the outline
  hitboxes.json           {"hitboxes": {pose: {dir: [[x, y, w, h]]}},
                           "points": {pose: {name: {dir: [x, y]}}}}  (idle-hand coordinates)

Run after parts_library.py: .venv/bin/python tools/art/weapons.py
"""

from __future__ import annotations

import json

import numpy as np

from artlib import crescent, OUTLINE, ROOT, SIZE, STYLE, grid
from pixelforge.sheet import write_sheet

DIRS = ("s", "e", "n")
ORIGIN = {"s": (11, 23), "e": (15, 23), "n": (19, 23)}  # idle frame 0 hand_near
ORIGIN_FAR = {"s": (19, 23), "e": (13, 23), "n": (11, 23)}  # idle frame 0 hand_far
ACTIVE_POSES = ("strike", "slam", "ground")  # poses held on active frames: need hitboxes


def line(kind: str, n: int, sx: int = 0, sy: int = 0) -> list[tuple[int, int]]:
    out = []
    for k in range(n):
        if kind == "v":
            out.append((0, sy * k))
        elif kind == "h":
            out.append((sx * k, 0))
        elif kind == "steep":
            out.append((sx * (k // 2), sy * k))
        elif kind == "shallow":
            out.append((sx * k, sy * (k // 2)))
        else:
            raise ValueError(kind)
    return out


def perp(kind: str) -> tuple[int, int]:
    return (1, 0) if kind in ("v", "steep") else (0, 1)


# ============================================================================== pose tables
# Blade weapons: pose -> (grip offset from the hand, kind, sx, sy, blade length, behind)
# The grip pixel sits beside the fist, the 3 px guard across the line, then the blade.
SWORD_E = {
    "ready": ((1, 0), "steep", 1, -1, 4, False),     # up and forward in front of the face
    "raised": ((0, -1), "shallow", -1, -1, 6, True),  # cocked back behind the head
    "strike": ((1, 0), "shallow", 1, 1, 4, False),   # extended forward and down
    "low": ((1, 0), "shallow", 1, 1, 4, False),      # follow-through, low in front
    "overhead": ((2, 0), "v", 0, -1, 6, False),      # lifted straight up, clear of the face
    "back": ((0, 0), "shallow", -1, -1, 6, True),    # behind the head: the heavy's tell
    "slam": ((1, 0), "v", 0, 1, 5, False),           # slammed down in front
    "ground": ((1, 0), "h", 1, 0, 5, False),         # lying forward on the ground
    "aim": ((1, 0), "h", 1, 0, 4, False),            # pointed forward (cast with a sword)
    "guard": ((3, 0), "v", 0, -1, 5, False),         # held upright in front: a parry
    "tuck": ((-1, 0), "h", -1, 0, 4, False),         # along the body, pointing back
    "high": ((1, 0), "steep", 1, -1, 6, False),      # raised high: victory
    "dropped": ((5, 1), "h", 1, 0, 5, False),        # let go: on the ground in front
}
SWORD_S = {
    "ready": ((-1, 0), "steep", -1, -1, 4, False),
    "raised": ((-1, -1), "steep", -1, -1, 6, False),  # up and out, clear of the head
    "strike": ((-1, 0), "steep", -1, 1, 4, False),
    "low": ((-1, 0), "shallow", -1, 1, 4, False),
    "overhead": ((-1, -1), "steep", -1, -1, 6, False),
    "back": ((-1, -1), "v", 0, -1, 7, False),       # tall beside the head: the heavy's tell
    "slam": ((-1, 0), "v", 0, 1, 3, False),
    "ground": ((-1, 0), "shallow", -1, 1, 6, False),
    "aim": ((-1, 0), "steep", -1, 1, 4, False),
    "guard": ((-2, 0), "v", 0, -1, 5, False),
    "tuck": ((-1, 0), "shallow", -1, -1, 4, False),  # held close, pointing up and out
    "high": ((-1, -1), "v", 0, -1, 6, False),
    "dropped": ((-2, 1), "h", -1, 0, 4, False),
}

# Smears (relative to the hand in the pose's reference arm position): the arc the weapon's tip
# traced into the strike, 1 to 2 px wide, in the item's lightest shade. Drawn only where the
# character is not, so they never cover the body.
SMEAR_E = {
    "strike": [(1, -10), (2, -10), (2, -9), (3, -9), (4, -8), (5, -7), (5, -6), (6, -6), (6, -5),
               (6, -4), (7, -4), (7, -3), (7, -2), (7, -1), (7, 0)],
    "slam": [(-1, -12), (0, -12), (1, -11), (2, -11), (2, -10), (3, -9), (3, -8), (3, -7),
             (4, -7), (4, -6), (4, -5), (4, -4), (4, -3), (4, -2), (3, -1)],
}
SMEAR_S = {  # down the weapon side, from above the shoulder to the blade
    "strike": [(0, -11), (-1, -11), (-1, -10), (-2, -10), (-3, -9), (-3, -8), (-4, -8), (-4, -7),
               (-4, -6), (-4, -5), (-4, -4), (-4, -3), (-4, -2), (-4, -1), (-3, 0)],
    "slam": [(1, -14), (0, -14), (0, -13), (-1, -13), (-1, -12), (-2, -11), (-2, -10), (-3, -10),
             (-3, -9), (-3, -8), (-3, -7), (-3, -6), (-3, -5), (-3, -4), (-2, -3)],
}
# Unarmed (the fist): shorter arcs ending at the fist
FIST_SMEAR_E = {  # a crescent bursting in front of the fist
    "strike": [(0, -3), (1, -3), (1, -2), (2, -2), (2, -1), (2, 0), (2, 1), (2, 2), (1, 2),
               (1, 3), (0, 3), (3, -1), (3, 0), (3, 1)],  # thick in the middle, thin at the tips
    "slam": [(0, -9), (1, -9), (1, -8), (2, -7), (2, -6), (2, -5), (2, -4), (2, -3), (2, -2)],
}
FIST_SMEAR_S = {
    "strike": [(-1, -8), (-2, -8), (-2, -7), (-3, -6), (-3, -5), (-3, -4), (-3, -3), (-3, -2)],
    "slam": [(-2, -10), (-3, -10), (-3, -9), (-3, -8), (-3, -7), (-3, -6), (-3, -5), (-3, -4)],
}


def mirror_rel(points):
    return [(-x, y, *rest) for x, y, *rest in points]


def mirror_table(table: dict) -> dict:
    out = {}
    for pose, (grip, kind, sx, sy, n, behind) in table.items():
        out[pose] = ((-grip[0], grip[1]), kind, -sx, sy, n, behind)
    return out


SWORD = {"e": SWORD_E, "s": SWORD_S, "n": mirror_table(SWORD_S)}
SMEARS = {"e": SMEAR_E, "s": SMEAR_S, "n": {k: mirror_rel(v) for k, v in SMEAR_S.items()}}
FIST_SMEARS = {"e": FIST_SMEAR_E, "s": FIST_SMEAR_S,
               "n": {k: mirror_rel(v) for k, v in FIST_SMEAR_S.items()}}


TRAILS = {d: {pose: crescent(arc) for pose, arc in SMEARS[d].items()} for d in SMEARS}
FIST_TRAILS = {d: {pose: crescent(arc, 2) for pose, arc in FIST_SMEARS[d].items()}
               for d in FIST_SMEARS}
# A thrust leaves straight streaks beside the shaft instead of an arc (the lance's strike):
# relative to the hand, from the butt's end past the hand, brightest nearest the head.
THRUST_E = {"strike": [(x, y, 2 if x >= -2 else 1 if x >= -6 else 0)
                       for y in (-2, 2) for x in range(-9, 3)] + [(x, 0, 0) for x in range(-12, -9)]}
THRUST_S = {"strike": [(x, y, 2 if y >= 2 else 1 if y >= -1 else 0)
                       for x in (-3, 1) for y in range(-4, 5)]}
THRUSTS = {"e": THRUST_E, "s": THRUST_S, "n": {k: mirror_rel(v) for k, v in THRUST_S.items()}}


# ============================================================================== item drawings
# Each returns {"main": [(dx, dy, shade)], "trim": [...], "tip": (dx, dy)} relative to the hand.
def sword(pose: str, d: str):
    spec = SWORD[d].get(pose)
    if spec is None:
        return None
    (gx, gy), kind, sx, sy, n, behind = spec
    pts = [(gx + x, gy + y) for x, y in line(kind, n + 2, sx, sy)]
    px, py = perp(kind)
    cx, cy = pts[1]
    trim = [(*pts[0], 0), (cx - px, cy - py, 1), (cx, cy, 1), (cx + px, cy + py, 1)]
    main = [(x, y, 3) for x, y in pts[2:]]
    return {"main": main, "trim": trim, "tip": pts[-1], "behind": behind}


def mace(pose: str, d: str):
    """A short shaft and a 3 x 3 flanged head at the end of the sword's line."""
    spec = SWORD[d].get(pose)
    if spec is None:
        return None
    (gx, gy), kind, sx, sy, n, behind = spec
    reach = 5 if n >= 5 and sy < 0 else 4  # raised or cocked, it reaches past the helm
    pts = [(gx + x, gy + y) for x, y in line(kind, reach, sx, sy)]  # grip and the shaft
    ex, ey = line(kind, reach + 1, sx, sy)[reach]
    hx, hy = gx + ex, gy + ey  # head centre just past the shaft
    main = [(x, y, 1) for x, y in pts]
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            shade = 3 if (ox, oy) == (0, 0) else 1 if oy == 1 else 2
            main.append((hx + ox, hy + oy, shade))
    return {"main": main, "trim": [], "tip": (hx, hy), "behind": behind}


STAFF_E = {  # pose -> (bottom end relative to the hand, kind, sx, sy, length, behind)
    "low": ((1, 4), "steep", 1, -1, 10, False),      # leaning forward, relaxed
    "tuck": ((1, 4), "steep", 1, -1, 10, False),
    "ground": ((1, 1), "h", 1, 0, 9, False),         # lying on the ground in front
    "dropped": ((1, 1), "h", 1, 0, 9, False),
    "ready": ((1, 3), "v", 0, -1, 10, False),
    "raised": ((1, 4), "v", 0, -1, 10, False),
    "overhead": ((1, 4), "v", 0, -1, 10, False),
    "high": ((1, 4), "v", 0, -1, 10, False),
    "aim": ((-1, 4), "steep", 1, -1, 10, False),
    "guard": ((2, 3), "v", 0, -1, 10, False),
}
STAFF_S = {
    "low": ((-2, 4), "steep", -1, -1, 10, False),    # leaning out, clear of the body
    "tuck": ((-2, 4), "steep", -1, -1, 10, False),
    "ground": ((1, 1), "h", 1, 0, 9, False),          # lying in front of the knees
    "dropped": ((1, 1), "h", 1, 0, 9, False),
    "ready": ((-1, 3), "v", 0, -1, 10, False),
    "raised": ((-1, 4), "v", 0, -1, 10, False),
    "overhead": ((-1, 4), "v", 0, -1, 10, False),
    "high": ((-1, 4), "v", 0, -1, 10, False),
    "aim": ((-2, 1), "v", 0, -1, 10, False),        # thrust toward the camera, beside the robe
    "guard": ((-1, 3), "v", 0, -1, 10, False),
}
STAFF = {"e": STAFF_E, "s": STAFF_S, "n": mirror_table(STAFF_S)}


def staff(pose: str, d: str):
    """A pole held through the hand, the knob (and the orb trim) at its top end."""
    spec = STAFF[d].get(pose)
    if spec is None:
        return None
    (bx, by), kind, sx, sy, n, behind = spec
    pts = [(bx + x, by + y) for x, y in line(kind, n, sx, sy)]
    main = []
    for i, (x, y) in enumerate(pts):
        shade = 2 if i == n - 1 else 0 if i in (0, 1) else 1  # dark butt, plain shaft, light knob
        main.append((x, y, shade))
    tx, ty = pts[-1]
    # the orb sits on the knob, 2 x 2, toward the outer side with its dark pixel outside (as in
    # the rest pose): left facing s, right facing e and n; lying down it caps the end
    if kind == "h":
        ex = tx + sx
        orb = [(ex, ty - 1, 1), (ex + sx, ty - 1, 1), (ex, ty, 1), (ex + sx, ty, 0)]
    elif d == "s":
        orb = [(tx - 1, ty - 2, 1), (tx, ty - 2, 1), (tx - 1, ty - 1, 0), (tx, ty - 1, 1)]
    else:
        orb = [(tx, ty - 2, 1), (tx + 1, ty - 2, 1), (tx, ty - 1, 1), (tx + 1, ty - 1, 0)]
    return {"main": main, "trim": orb, "tip": (tx, ty - 1), "behind": behind}


LANCE_E = {  # pose -> (butt end relative to the hand, kind, sx, sy, shaft length)
    "raised": ((0, 4), "v", 0, -1, 11),     # upright behind the head, pulled back
    "high": ((0, 4), "v", 0, -1, 11),
    "tuck": ((-6, 0), "h", 1, 0, 10),
    "dropped": ((2, 1), "h", 1, 0, 8),       # lying on the ground in front
    "ready": ((-6, 0), "h", 1, 0, 11),
    "strike": ((-5, 0), "h", 1, 0, 10),
    "slam": ((-5, 0), "h", 1, 0, 10),
    "ground": ((-3, 0), "h", 1, 0, 10),
    "aim": ((-5, 0), "h", 1, 0, 10),
    "low": ((-5, -1), "shallow", 1, 1, 8),
    "guard": ((-6, 0), "h", 1, 0, 12),
}
LANCE_S = {
    "raised": ((-1, 4), "v", 0, -1, 11),
    "high": ((-1, 4), "v", 0, -1, 11),
    "tuck": ((2, -5), "steep", -1, 1, 8),
    "dropped": ((2, 1), "h", -1, 0, 7),
    "ready": ((2, -5), "steep", -1, 1, 8),
    "strike": ((0, -6), "steep", -1, 1, 9),   # beside the fist, not across the arm
    "slam": ((0, -6), "steep", -1, 1, 9),
    "ground": ((4, 0), "h", -1, 0, 10),
    "aim": ((0, -6), "steep", -1, 1, 9),
    "low": ((4, -2), "shallow", -1, 1, 8),
    "guard": ((2, -5), "steep", -1, 1, 8),
}
LANCE = {"e": LANCE_E, "s": LANCE_S,
         "n": {k: ((-g[0], g[1]), kind, -sx, sy, n) for k, (g, kind, sx, sy, n) in LANCE_S.items()}}


def lance(pose: str, d: str):
    """A wooden shaft held at its middle and the steel head (trim) beyond its front end."""
    spec = LANCE[d].get(pose)
    if spec is None:
        return None
    (bx, by), kind, sx, sy, n = spec
    pts = [(bx + x, by + y) for x, y in line(kind, n + 3, sx, sy)]
    main = [(x, y, 0 if i == 0 else 1) for i, (x, y) in enumerate(pts[:n])]
    trim = [(x, y, 2 if i == 0 else 3) for i, (x, y) in enumerate(pts[n:])]
    return {"main": main, "trim": trim, "tip": pts[-1], "behind": pose == "raised" and d == "e"}


BOW_UPRIGHT = [(-1, -5, 0), (-2, -4, 1), (-2, -3, 1), (-2, -2, 1), (-1, -1, 1), (-1, 0, 1),
               (-1, 1, 1), (-2, 2, 1), (-2, 3, 1), (-2, 4, 1), (-1, 5, 0)]  # rest shape, s
BOW_LYING = [(x, y, s) for y, x, s in BOW_UPRIGHT if s != 0]  # on its side, tips tucked in


def bow(pose: str, d: str):
    """Facing e the bow is drawn bent with its string (outline-colored pixels) and arrow; facing
    s and n the bow is seen edge-on beside the hand, so only its height changes. Low, tucked and
    dropped it lies on its side; raised it is the rest drawing lifted with the hand."""
    if pose in ("low", "ground", "dropped", "tuck"):
        dx, dy = {"e": (6, 2), "s": (-2, 2), "n": (2, 2)}[d]
        if pose == "tuck":
            dy = 0
        pts = BOW_LYING if d != "n" else mirror_rel(BOW_LYING)
        main = [(dx + x, dy + y, s) for x, y, s in pts]
        return {"main": main, "trim": [], "tip": (dx, dy), "nock": (dx, dy), "behind": False}
    if pose == "high":
        pts = BOW_UPRIGHT if d == "s" else mirror_rel(BOW_UPRIGHT)
        dx = {"e": 4, "s": 0, "n": 0}[d]
        main = [(dx + x, y, s) for x, y, s in pts]
        return {"main": main, "trim": [], "tip": (dx, -5), "nock": (dx, 0), "behind": False}
    if pose not in ("aim", "draw", "release"):
        return None
    if d == "e":
        g = (1, 0)
        limbs = [(-2, -5, 0), (-1, -4, 1), (-1, -3, 1), (0, -2, 1), (0, -1, 1), (0, 0, 1),
                 (0, 1, 1), (0, 2, 1), (-1, 3, 1), (-1, 4, 1), (-2, 5, 0)]
        main = [(g[0] + x, g[1] + y, s) for x, y, s in limbs]
        if pose == "draw":  # the string pulled back to the cheek, the arrow on it
            string = [(-3, -4), (-3, -3), (-4, -2), (-4, -1), (-5, 0), (-4, 1), (-4, 2), (-3, 3),
                      (-3, 4)]
            arrow = [(-4, 0), (-3, 0), (-2, 0), (-1, 0), (1, 0), (2, 0)]
            nock = (g[0] - 5, 0)
        else:
            string = [(-2, y) for y in range(-4, 5)]
            arrow = [(-1, 0), (1, 0), (2, 0)] if pose == "aim" else []
            nock = (g[0] - 2, 0)
        main += [(g[0] + x, g[1] + y, "O") for x, y in string if (x, y) not in arrow]
        main += [(g[0] + x, g[1] + y, 2) for x, y in arrow]
        return {"main": main, "trim": [], "tip": (g[0] + 2, 0), "nock": nock, "behind": False}
    # s and n: the rest drawing (seen edge-on beside the hand) raised 2 px, the arm being up
    rows = [(-1, -7, 0), (-2, -6, 1), (-2, -5, 1), (-2, -4, 1), (-1, -3, 1), (-1, -2, 1),
            (-1, -1, 1), (-2, 0, 1), (-2, 1, 1), (-2, 2, 1), (-1, 3, 0)]
    if d == "n":
        rows = mirror_rel(rows)
    grip = (-1, -2) if d == "s" else (1, -2)
    return {"main": rows, "trim": [], "tip": grip, "nock": grip, "behind": False}


SHIELD_GUARD = {  # held_far guard: the heater shield raised in front, relative to the far hand
    "e": [(x, y, int(c)) for y, row in enumerate(["1332", "1322", "1221", "1221", ".11."], -1)
          for x, c in enumerate(row) if c != "."],
}
SHIELD_GUARD["s"] = [(x - 4, y, s) for x, y, s in SHIELD_GUARD["e"]]
SHIELD_GUARD["n"] = [(-x + 4, y, s) for x, y, s in SHIELD_GUARD["e"]]


# ============================================================================== writing
def cell(points, origin) -> np.ndarray:
    codes = np.full((SIZE, SIZE), grid.CLEAR, np.int8)
    ox, oy = origin
    for x, y, s in points:
        X, Y = ox + x, oy + y
        assert 0 <= X < SIZE and 0 <= Y < SIZE, (x, y, origin)
        codes[Y, X] = grid.INK if s == "O" else s
    return codes


POSE_SINGLETONS: dict = {}  # folder -> {sheet name: {dir: [[x, y]]}}


def lonely(codes: np.ndarray) -> list[list[int]]:
    """Pixels with no 4-neighbor of the same shade: the tips a pose draws on purpose."""
    out = []
    for y, x in zip(*np.nonzero(codes >= 0)):
        v = codes[y, x]
        if not any(0 <= y + dy < SIZE and 0 <= x + dx < SIZE and codes[y + dy, x + dx] == v
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            out.append([int(x), int(y)])
    return out


def write(folder, name: str, material: str, cells: dict) -> None:
    if name.startswith("pose_"):
        tips = {d: lonely(c) for d, c in cells.items() if lonely(c)}
        if tips:
            POSE_SINGLETONS.setdefault(folder, {})[name] = tips
    ramp = STYLE.materials[material].base
    painted = {(d, 0): grid.paint(cells.get(d, np.full((SIZE, SIZE), grid.CLEAR, np.int8)), ramp,
                                  OUTLINE) for d in DIRS}
    write_sheet(folder / f"{name}.png", painted, DIRS, 1, SIZE)


def bbox(points, origin, pad=1):
    xs = [origin[0] + p[0] for p in points]
    ys = [origin[1] + p[1] for p in points]
    x0, y0 = max(min(xs) - pad, 0), max(min(ys) - pad, 0)
    x1, y1 = min(max(xs) + pad, SIZE - 1), min(max(ys) + pad, SIZE - 1)
    return [x0, y0, x1 - x0 + 1, y1 - y0 + 1]


FRONT = {  # where "in front" is on the canvas, so S and N strikes reach toward their target
    "s": lambda b: _union(b, [9, 24, 13, 8]),
    "n": lambda b: _union(b, [9, 3, 13, 9]),
    "e": lambda b: b,
}


def _union(a, b):
    x0, y0 = min(a[0], b[0]), min(a[1], b[1])
    x1, y1 = max(a[0] + a[2], b[0] + b[2]), max(a[1] + a[3], b[1] + b[3])
    return [x0, y0, min(x1, SIZE) - x0, min(y1, SIZE) - y0]


def build_item(slot: str, variant: str, material: str, draw, poses, *, trim=None, smears=None,
               fist_points=False, smear_hits=True) -> None:
    """smear_hits: a swing's trail is the area it swept, so it is part of the hitbox; a thrust's
    streaks trail behind the point and are not."""
    folder = ROOT / "parts" / slot / variant
    data = {"hitboxes": {}, "points": {}}
    for pose in poses:
        front, back, tfront, tback = {}, {}, {}, {}
        for d in DIRS:
            res = draw(pose, d)
            if res is None:
                continue
            o = ORIGIN[d]
            target = back if res["behind"] else front
            target[d] = cell(res["main"], o)
            if trim and res["trim"]:
                (tback if res["behind"] else tfront)[d] = cell(res["trim"], o)
            tip = res["tip"]
            data["points"].setdefault(pose, {}).setdefault("weapon_tip", {})[d] = \
                [o[0] + tip[0], o[1] + tip[1]]
            if "nock" in res:
                n = res["nock"]
                data["points"][pose].setdefault("bow_nock", {})[d] = [o[0] + n[0], o[1] + n[1]]
            if pose in ACTIVE_POSES:
                pts = [p[:2] for p in res["main"] + res["trim"]]
                if smears and smear_hits and pose in smears[d]:
                    pts += [p[:2] for p in smears[d][pose]]
                data["hitboxes"].setdefault(pose, {})[d] = [FRONT[d](bbox(pts, o))]
        if front:
            write(folder, f"pose_{pose}", material, front)
        if back:
            write(folder, f"pose_{pose}_behind", material, back)
        if trim:
            tfolder = ROOT / "parts" / trim[0] / trim[1]
            if tfront:
                write(tfolder, f"pose_{pose}", trim[2], tfront)
            if tback:
                write(tfolder, f"pose_{pose}_behind", trim[2], tback)
    if smears:  # swing trails, written in the item's material (shade = rank in the trail)
        for pose in ACTIVE_POSES:
            cells = {d: cell([(x, y, trail_shade(material, v)) for x, y, v in smears[d][pose]],
                             ORIGIN[d]) for d in DIRS if pose in smears[d]}
            if cells:
                write(folder, f"smear_{pose}", material, cells)
    # hitboxes for active poses the item has no drawing for: the fist's reach
    for pose in ACTIVE_POSES:
        if pose not in data["hitboxes"]:
            for d in DIRS:
                pts = [(0, 0)] + FIST_SMEARS[d].get(pose, [(1, 0)])
                data["hitboxes"].setdefault(pose, {})[d] = [FRONT[d](bbox(pts, ORIGIN[d]))]
                data["points"].setdefault(pose, {}).setdefault("weapon_tip", {})[d] = \
                    [ORIGIN[d][0], ORIGIN[d][1]]
    (folder / "hitboxes.json").write_text(json.dumps(data, indent=1))


def check_bounds() -> list[str]:
    """Every held item, in every frame of every recipe that holds it, stays in the safe area with
    its outline (x 2..29, y 2..30): a pose drawn for one hand position must not run off the
    canvas in another frame that reuses it."""
    from pixelforge.parts import Library
    from pixelforge.recipe import all_recipes, load_recipe
    from pixelforge.rig import load_rig
    lib = Library(ROOT, STYLE)
    rig = load_rig(ROOT, STYLE, "humanoid")
    defaults = STYLE.raw["rigs"]["humanoid"].get("defaults", {})
    x0, y0, x1, y1 = 2, 2, 29, 30
    problems = set()
    from pixelforge.anim import anim_specs
    specs = anim_specs(STYLE, "humanoid")
    for path in all_recipes(ROOT, include_random=True):
        recipe = load_recipe(path, STYLE)
        if recipe.rig != "humanoid":  # monsters draw their own weapons per frame
            continue
        parts = {**defaults, **recipe.parts}
        for slot in ("held_near", "held_near_trim", "held_far"):
            if parts.get(slot, "none") == "none":
                continue
            part = lib.part(slot, parts[slot])
            hand = part.attach  # the anchor the item follows (the shield rides the torso)
            for anim in recipe.anims:
                src = specs[anim].get("source", {}).get("anim", specs[anim].get("alias", anim))
                for d in DIRS:
                    origin = rig.anchor("idle", d, 0, hand)
                    for i in range(rig.frame_count(src, d)):
                        pts = rig.points(src, d, i)
                        pose = pts.get("pose", {}).get(slot.replace("_trim", ""))
                        sheets = []
                        if pose:
                            sheets = [lib.sheet(part, f"pose_{pose}"),
                                      lib.sheet(part, f"pose_{pose}_behind")]
                            sheets = [sh for sh in sheets if sh is not None]
                        sheets = sheets or [lib.sheet(part, "rigid")]
                        dx, dy = pts[hand][0] - origin[0], pts[hand][1] - origin[1]
                        right = x1 - 1 if d == "e" else x1  # west mirrors x to 30 - x
                        for sh in sheets:
                            img = sh.get(d, 0)
                            ys, xs = (img[..., 3] > 0).nonzero()
                            if len(xs) and (xs.min() + dx - 1 < x0 or xs.max() + dx + 1 > right or
                                            ys.min() + dy - 1 < y0 or ys.max() + dy + 1 > y1):
                                problems.add(f"{part.id} {pose or 'rest'} {d}: {recipe.name} "
                                             f"{src} {i}")
    return sorted(problems)


def top_shade(material: str) -> int:
    return len(STYLE.materials[material].base) - 1


def trail_shade(material: str, rank: int) -> int:
    """A trail's rank (2 core, 1 mid, 0 rim) as distinct shades of the item's material, lightest
    for the core: the compositor repaints them by rank in fx_ramps.swing."""
    top = top_shade(material)
    return max(0, top - (2 - rank))


def fist() -> None:
    """The unarmed default for held_near: no art, only strike smears (accent light), the reach of
    a punch as hitboxes and the fist as weapon_tip."""
    from artlib import write_part
    empty = {(d, 0): np.full((SIZE, SIZE), grid.CLEAR, np.int8) for d in DIRS}
    write_part("held_near", "fist", {
        "material": "accent", "kind": "rigid", "attach": "hand_near", "origin": "auto",
        "lags": False, "rigs": ["humanoid"],
        "notes": "Unarmed: the rig default for held_near. No art; strike smears and hitboxes.",
    }, {"rigid": empty})
    folder = ROOT / "parts" / "held_near" / "fist"
    data = {"hitboxes": {}, "points": {}}
    for pose in ACTIVE_POSES + ("ready", "raised", "low", "aim", "guard", "high", "tuck"):
        for d in DIRS:
            o = ORIGIN[d]
            data["points"].setdefault(pose, {}).setdefault("weapon_tip", {})[d] = list(o)
            if pose in ACTIVE_POSES:
                pts = [(0, 0)] + FIST_SMEARS[d].get(pose, [])
                data["hitboxes"].setdefault(pose, {})[d] = [FRONT[d](bbox(pts, o))]
    for pose in ("strike", "slam"):
        cells = {d: cell([(x, y, trail_shade("accent", v)) for x, y, v in FIST_TRAILS[d][pose]],
                         ORIGIN[d]) for d in DIRS}
        write(folder, f"smear_{pose}", "accent", cells)
    (folder / "hitboxes.json").write_text(json.dumps(data, indent=1))


def shield() -> None:
    """The shield is attached to the torso; its guard pose is drawn where the far hand holds it
    up in front (combat.py's far "guard" arm), in idle-torso coordinates."""
    from combat import ARMS
    folder = ROOT / "parts" / "held_far" / "shield"
    guard_hand = {d: tuple(ARMS[(d, "far")]["guard"]["hand"]) for d in DIRS}
    cells = {d: cell(SHIELD_GUARD[d], guard_hand[d]) for d in DIRS}
    write(folder, "pose_guard", "metal", cells)
    data = {"hitboxes": {}, "points": {"guard": {"shield_front": {}}, "rest": {"shield_front": {}}}}
    for d in DIRS:
        ox, oy = guard_hand[d]
        front = {"e": (ox + 4, oy + 1), "s": (ox - 2, oy + 1), "n": (ox + 2, oy + 1)}[d]
        data["points"]["guard"]["shield_front"][d] = list(front)
        data["points"]["rest"]["shield_front"][d] = list({"e": (19, 22), "s": (20, 22),
                                                          "n": (10, 22)}[d])
    (folder / "hitboxes.json").write_text(json.dumps(data, indent=1))


BLADE_POSES = tuple(SWORD_E)


def main() -> None:
    build_item("held_near", "sword", "metal", sword, BLADE_POSES,
               trim=("held_near_trim", "hilt", "accent"), smears=TRAILS)
    build_item("held_near", "mace", "metal", mace, BLADE_POSES, smears=TRAILS)
    build_item("held_near", "staff", "leather", staff, tuple(STAFF_E),
               trim=("held_near_trim", "orb", "accent"))
    build_item("held_near", "lance", "leather", lance, tuple(LANCE_E),
               trim=("held_near_trim", "spearhead", "metal"), smears=THRUSTS, smear_hits=False)
    build_item("held_near", "bow", "leather", bow, ("aim", "draw", "release", "low", "ground",
                                                     "dropped", "tuck", "high"))
    fist()
    shield()
    import yaml
    for folder in sorted({f for f in (ROOT / "parts").glob("held*/*") if f.is_dir()}):
        meta = yaml.safe_load((folder / "part.yaml").read_text())
        meta.pop("pose_singletons", None)
        if POSE_SINGLETONS.get(folder):
            meta["pose_singletons"] = POSE_SINGLETONS[folder]
        (folder / "part.yaml").write_text(yaml.safe_dump(meta, sort_keys=False, width=100))
    problems = check_bounds()
    for p in problems:
        print("out of bounds:", p)
    print("wrote the held item poses" + (f" ({len(problems)} out of bounds)" if problems else ""))


if __name__ == "__main__":
    main()
