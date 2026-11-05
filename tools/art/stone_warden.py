"""The Stone Warden: the first boss, on the golem rig and the large 64 px canvas
(MONSTERS.md section 5.5). Redesigned on 2026-11-05 after the human's reference as a forest
guardian: a pale bone skull with branching antlers instead of a stone head and crown, a body of
dark charcoal boulders, a jagged leafy mane over the shoulders, leaf sleeves on the forearms and
shins with orange berries, brass bands on the upper arms and legs, bone claws on the fists and
feet, and green glowing eyes and core. Enraged, the leaves turn autumn red and the glow red.

A guardian of separate boulders around a glowing core. Every stone is a rounded box shaded by
one light from the upper left (`stone_codes`), drawn per frame at its pose position. Stones
parted by a 1 px gap are outlined by the compositor; a stone drawn over another gets a 1 px
outline-colored contour where they overlap (an outline-colored detail in the part that is in
front), so the pieces never merge however they move.

Layers: arm_far, body (pelvis, legs, torso), arm_near (stone); skull (bone: the skull, antlers
and claws), leaves (leaf), berries (fruit) and bands (metal); core and eyes (eyes material, glow
presets; rigid, riding the `core` and `eyes` anchors). Every frame is painted back to front
(far arm, body, mane, skull, near arm, each with its leaves, bands and claws) and each layer
keeps only what it shows. Seen from behind (n) both arms are past the body.

Stone shades: 0 darkest .. 3 lightest (the `stone` material); 'O' = an outline-colored detail.

Run after the FX library: .venv/bin/python tools/art/stone_warden.py
"""

from __future__ import annotations

import math

import numpy as np

from artlib import ROOT as ROOT_DIR, STYLE, arc_path, crescent, empty, grid, write_anchors, write_part, write_recipe
from pixelforge.anim import load_anims

RIG = "golem"
DIRS = ("s", "e", "n")
SIZE = 64
AXIS = 31
CLEAR, INK = grid.CLEAR, grid.INK
LIGHT = np.array([-0.42, -0.62, 0.66])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def E() -> np.ndarray:
    return empty(SIZE)


# ============================================================================== stones
def stone_codes(w: int, h: int, p: float = 2.6, far: bool = False, seed: int = 0,
                crack: bool = True) -> np.ndarray:
    """A w x h rounded box (a superellipse of power p) shaded 0..3 by the light; `far` stones
    (the far arm, the far leg) are a shade darker. A big stone gets a short crack."""
    c = np.full((h, w), CLEAR, np.int8)
    cx, cy = (w - 1) / 2, (h - 1) / 2
    a, b = w / 2, h / 2
    for y in range(h):
        for x in range(w):
            nx, ny = (x - cx) / a, (y - cy) / b
            if abs(nx) ** p + abs(ny) ** p > 1.0:
                continue
            # a soft normal: the face is flat-ish, the rim turns away
            r = min(1.0, (abs(nx) ** p + abs(ny) ** p) ** (1 / p))
            k = r ** 2.2
            n = np.array([nx * k, ny * k, max(0.05, 1 - k)])
            n = n / np.linalg.norm(n)
            i = float(n @ LIGHT)
            s = 3 if i >= 0.86 else 2 if i >= 0.62 else 1 if i >= 0.32 else 0
            if far:
                s = max(0, s - 1)
            c[y, x] = s
    if crack and w >= 10 and h >= 8:
        rng = np.random.default_rng(seed)
        x = int(rng.integers(w // 3, w - w // 3))
        y = int(rng.integers(h // 3, h - h // 3))
        step = int(rng.choice([-1, 1]))
        for k in range(int(rng.integers(4, 6))):  # a staircase: every pixel touches the next
            if 0 <= x < w and 0 <= y < h and c[y, x] != CLEAR:
                c[y, x] = INK
            if k % 2:
                x += step
            else:
                y += 1
    return c


class Stone:
    """A stone at an integer box; its codes are cached per size and darkness."""
    _cache: dict = {}

    def __init__(self, name: str, w: int, h: int, *, far=False, moss=False, p=2.6, seed=0, crack=True):
        self.name, self.w, self.h, self.far, self.moss = name, w, h, far, moss
        key = (w, h, far, p, seed, crack)
        if key not in Stone._cache:
            Stone._cache[key] = stone_codes(w, h, p, far, seed, crack)
        self.codes = Stone._cache[key]

    def at(self, cx: float, cy: float) -> tuple[np.ndarray, int, int]:
        """The stone's codes and its top-left for a center (cx, cy)."""
        x0 = int(round(cx - (self.w - 1) / 2))
        y0 = int(round(cy - (self.h - 1) / 2))
        return self.codes, x0, y0


def paste(layer: np.ndarray, canvas: np.ndarray, codes: np.ndarray, x0: int, y0: int,
          bottom: int | None = None) -> np.ndarray:
    """Draw a stone into its layer and the running canvas: a contour on whatever it covers,
    then the stone. Returns the stone's mask on the canvas."""
    h, w = codes.shape
    mask = np.zeros((SIZE, SIZE), bool)
    vals = np.full((SIZE, SIZE), CLEAR, np.int8)
    for y in range(h):
        for x in range(w):
            if codes[y, x] == CLEAR:
                continue
            X, Y = x0 + x, y0 + y
            if 0 <= X < SIZE and 0 <= Y < SIZE and (bottom is None or Y <= bottom):
                mask[Y, X] = True
                vals[Y, X] = codes[y, x]
    p = np.pad(mask, 1)
    ring = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]) & ~mask & (canvas != CLEAR)
    layer[ring] = INK
    canvas[ring] = INK
    layer[mask] = vals[mask]
    canvas[mask] = vals[mask]
    return mask | ring


# ============================================================================== the forest guardian's pieces
# Skull grids: bone shades 0..3, 'O' an outline-colored detail, 'E' a socket (outline-colored;
# the eyes part glows in its lower row), '.' clear. s and n are centered on the head; e faces right.
SKULL = {
    "s": ["....33333....", "..233333332..", ".12333333321.", ".1EE23332EE1.", ".1EE23332EE1.",
          "..112333211..", "...1223221...", "...1123211...", "....12321....", "....12221....",
          "....1O2O1....", ".....111.....", ".....000....."],
    "e": ["...23332.........", "..2333333........", ".233333333332....", "1233EE33333333...",
          "1223EE333333332..", "11222233333333332", ".1112222223333O32", "..11111112222221.",
          "....0000.1111110.", "..........0000..."],
    "n": ["...33333...", ".233333332.", "12333333321", "12233333221", "11222322211", ".112222211.",
          "..1122211..", "...11111...", "....000...."],
}
SKULL_ORIGIN = {"s": (-6, -6), "e": (-7, -6), "n": (-5, -5)}  # top-left from the head's center
# Antlers from the skull's top (dx, dy from its top-left): a 2 px beam through the points, 1 px
# tines from a beam point up to a tip. s and n carry both antlers (mirrored); e the near one and
# a darker far one behind it.
BEAM_S = [(3, 1), (0, -1), (-4, -2), (-8, -3), (-11, -5)]
TINES_S = [((0, -1), (0, -5)), ((-4, -2), (-5, -6)), ((-8, -3), (-9, -7)), ((-11, -5), (-13, -7))]
BEAM_E = [(3, 0), (0, -2), (-4, -3), (-8, -4), (-11, -6)]
TINES_E = [((0, -2), (1, -6)), ((-4, -3), (-4, -7)), ((-8, -4), (-9, -7))]


def _line(a, b):
    """4-connected integer points from a to b."""
    (x0, y0), (x1, y1) = a, b
    pts = [(x0, y0)]
    n = max(abs(x1 - x0), abs(y1 - y0))
    for k in range(1, n + 1):
        x = int(round(x0 + (x1 - x0) * k / n))
        y = int(round(y0 + (y1 - y0) * k / n))
        px, py = pts[-1]
        if x != px and y != py:
            pts.append((x, py))
        pts.append((x, y))
    return pts


def antler_points(d: str) -> list[tuple[int, int, int]]:
    """(dx, dy, shade) from the skull's top-left: beams 2 px thick (lit top, shaded underside),
    tines 1 px with light tips."""
    w = len(SKULL[d][0])
    out: dict[tuple[int, int], int] = {}

    def put(x, y, v):
        out[(x, y)] = max(out.get((x, y), -1), v)

    sides = [(1, 0)] if d == "e" else [(1, 0), (-1, w - 1)]
    beam, tines = (BEAM_E, TINES_E) if d == "e" else (BEAM_S, TINES_S)
    for sign, base in sides:
        X = (lambda x: base + x) if sign == 1 else (lambda x: base - x)
        for a, b in zip(beam, beam[1:]):
            for x, y in _line(a, b):
                put(X(x), y, 2)
                put(X(x), y + 1, 1)
        for root_pt, tip in tines:  # one light shade, so a tine is one connected run
            for x, y in _line(root_pt, tip)[1:]:
                put(X(x), y, 3)
    pts = [(x, y, v) for (x, y), v in out.items()]
    if d == "e":  # the far antler: the same shape 3 px back and up, a shade darker, behind
        far = [(x + 3, y - 1, max(0, v - 1)) for x, y, v in pts]
        return far, pts
    return [], pts


def leaf_codes(w: int, h: int, teeth: int = 0, seed: int = 0) -> np.ndarray:
    """A clump of leaves: an ellipse w x h whose edge is cut into pointed leaves (a sawtooth of
    the radius around the angle), shaded 0..3 by the same light as the stones."""
    pad = 3
    c = np.full((h + 2 * pad, w + 2 * pad), CLEAR, np.int8)
    cy, cx = (h + 2 * pad - 1) / 2, (w + 2 * pad - 1) / 2
    k = teeth or max(6, (w + h) // 3)
    for y in range(c.shape[0]):
        for x in range(c.shape[1]):
            nx, ny = (x - cx) / (w / 2), (y - cy) / (h / 2)
            ang = math.atan2(ny, nx)
            saw = abs(((ang / (2 * math.pi)) * k + seed * 0.37) % 1.0 - 0.5) * 2  # 1 at a tip
            reach = 0.86 + 0.34 * saw
            r = math.hypot(nx, ny)
            if r > reach:
                continue
            kk = min(1.0, r) ** 2
            n = np.array([nx * kk, ny * kk, max(0.05, 1 - kk)])
            n = n / np.linalg.norm(n)
            i = float(n @ LIGHT)
            c[y, x] = 3 if i >= 0.84 else 2 if i >= 0.6 else 1 if i >= 0.3 else 0
    for _ in range(3):  # a leaf tip touching the clump only at a corner would float alone
        solid = c != CLEAR
        p = np.pad(solid, 1)
        linked = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
        c[solid & ~linked] = CLEAR
    return c


CLAW_S = [(0, 0, 2), (1, 0, 1), (0, 1, 2), (1, 1, 1), (1, 2, 1)]  # down, 2 px at the root
CLAW_E = [(0, 0, 2), (0, 1, 1), (1, 0, 2), (1, 1, 1), (2, 1, 1)]  # forward


# ============================================================================== layout (idle frame 0)
def mx(p):
    """Mirror a center around the axis: x' = 2 * axis - x."""
    return (2 * AXIS - p[0], p[1])


ARM_STONES = (("shoulder", 11, 10), ("upper", 8, 7), ("fore", 10, 6), ("fist", 13, 9))

BODY_S = {  # piece: (w, h, center); the skull and antlers ride the head
    "pelvis": (15, 5, (31, 45)), "torso": (23, 16, (31, 33.5)), "head": (13, 13, (31, 20)),
}
LEGS_S = {"leg_near": (9, 11, (25, 54)), "leg_far": (9, 11, (37, 54))}
BODY_E = {  # profile: the far arm behind, a deep torso, the near arm hanging in front
    "pelvis": (12, 5, (27.5, 45)), "torso": (16, 16, (27.5, 33.5)), "head": (14, 8, (31, 21)),
}
LEGS_E = {"leg_near": (9, 11, (32, 54)), "leg_far": (9, 11, (23, 54))}

# arm poses: centers of shoulder, upper arm, forearm, fist (the near arm; s and n mirror it)
ARM_S = {
    "rest": [(13, 29.5), (12.5, 39), (12.5, 46.5), (12, 55)],
    "raise": [(14, 27.5), (11.5, 20), (15.5, 14), (21, 10)],
    "slam": [(14, 31.5), (16.5, 39), (19.5, 46), (23, 54)],
    "ground": [(14, 33.5), (16.5, 41), (19.5, 47), (23, 55)],
    "spread": [(13, 28.5), (8.5, 22), (8.5, 16), (11, 10)],
    "spread_back": [(13, 29.5), (8.5, 24), (8.5, 18), (10, 12)],
    "cock": [(13, 29.5), (11.5, 37), (15.5, 31), (17, 24)],
    "punch": [(14, 30.5), (17.5, 37), (20.5, 43), (23, 50)],
    "up": [(13, 28.5), (11.5, 21), (11.5, 15), (12, 10)],
    "sweep": [(13, 29.5), (10.5, 38), (9.5, 45), (10, 53)],
    "balance": [(13, 29.5), (9.5, 36), (8.5, 43), (9, 51)],
    "guard": [(13, 29.5), (13.5, 38), (17.5, 44), (20, 51)],
}
ARM_E_NEAR = {  # in front of the body, hanging forward of the chest
    "rest": [(36, 30.5), (40.5, 38), (43.5, 46), (46, 55)],
    "raise": [(35, 28.5), (37.5, 21), (34.5, 15), (29, 11)],
    "slam": [(36, 31.5), (41.5, 36), (45.5, 43), (48, 53)],
    "ground": [(36, 33.5), (42.5, 39), (46.5, 46), (49, 55)],
    "spread": [(35, 28.5), (40.5, 22), (43.5, 17), (45, 11)],
    "spread_back": [(35, 29.5), (40.5, 24), (44.5, 18), (46, 12)],
    "cock": [(34, 30.5), (29.5, 35), (24.5, 31), (20, 26)],
    "punch": [(36, 29.5), (41.5, 30), (46, 31), (50, 31)],
    "up": [(36, 28.5), (40.5, 21), (42.5, 16), (43, 10)],
    "sweep": [(36, 30.5), (41.5, 36), (45.5, 43), (48, 51)],
    "balance": [(36, 30.5), (41.5, 33), (46.5, 37), (50, 41)],
    "guard": [(36, 30.5), (40.5, 37), (44.5, 43), (47, 50)],
}
ARM_E_FAR = {  # behind the body, a shade darker
    "rest": [(20, 29.5), (16.5, 37), (14.5, 45), (13, 54)],
    "raise": [(21, 28.5), (20.5, 21), (23.5, 15), (27, 10)],
    "slam": [(23, 31.5), (29.5, 36), (34.5, 43), (39, 53)],
    "ground": [(23, 33.5), (30.5, 39), (35.5, 46), (40, 55)],
    "spread": [(20, 28.5), (15.5, 22), (12.5, 17), (11, 11)],
    "spread_back": [(20, 29.5), (15.5, 24), (11.5, 18), (10, 12)],
    "cock": [(20, 29.5), (19.5, 37), (22.5, 44), (26, 50)],
    "punch": [(20, 29.5), (15.5, 36), (13.5, 43), (13, 50)],
    "up": [(21, 28.5), (19.5, 21), (18.5, 15), (18, 10)],
    "sweep": [(22, 30.5), (27.5, 37), (31.5, 44), (34, 52)],
    "balance": [(20, 29.5), (15.5, 33), (12.5, 37), (11, 41)],
    "guard": [(20, 29.5), (16.5, 37), (14.5, 45), (13, 54)],
}
LEG_POSES = {  # (near dx, dy), (far dx, dy)
    "s": {"stand": ((0, 0), (0, 0)), "step_a": ((0, -2), (0, 0)), "step_b": ((0, 0), (0, -2)),
          "lift": ((-1, -9), (1, 0)), "wide": ((-1, 0), (1, 0)), "charge": ((0, -1), (0, 0))},
    "e": {"stand": ((0, 0), (0, 0)), "step_a": ((2, -1), (-1, 0)), "step_b": ((-1, 0), (2, -1)),
          "lift": ((3, -9), (-1, 0)), "wide": ((2, 0), (-2, 0)), "charge": ((3, 0), (-3, -1))},
}
LEG_POSES["n"] = {k: (b, a) for k, (a, b) in LEG_POSES["s"].items()}  # from behind the sides swap


def arm_pose(d: str, side: str, name: str):
    if d == "e":
        return (ARM_E_NEAR if side == "near" else ARM_E_FAR)[name]
    pts = ARM_S[name]
    # s: the near arm is on the viewer's left; n: on the right
    mirrored = (d == "s" and side == "far") or (d == "n" and side == "near")
    return [mx(p) for p in pts] if mirrored else pts


# ============================================================================== frames
def F(t=(0, 0), h=(0, 0), pelvis=0, legs="stand", near="rest", far=None, lag=(0, 0), core=True,
      fall=0.0, behind=False):
    """t: the torso's offset (along the facing for e), h: the head's on top of it, pelvis: its
    dy, legs: a leg pose, near/far: arm poses (far defaults to near), lag: extra arm offset
    (floating stones trailing the body), fall: 0..1, how far the stones have tumbled (death),
    behind: facing e, both arms pass behind the head (raised overhead) so the face stays seen."""
    return {"t": t, "h": h, "pelvis": pelvis, "legs": legs, "near": near, "far": far or near,
            "lag": lag, "core": core, "fall": fall, "behind": behind}


FRAMES = {
    "idle": [F(), F(t=(0, 1), h=(0, 0)), F(t=(0, 1), lag=(0, 1)), F(lag=(0, 1))],
    "walk": [F(legs="step_a"), F(t=(0, -1)), F(legs="step_b"), F(t=(0, -1))],
    "attack_slam": [
        F(t=(0, -1), near="guard"),
        F(t=(0, -2), h=(0, -1), near="raise", behind=True),
        F(t=(-1, -2), h=(-1, -1), near="raise", lag=(0, -1), behind=True),
        F(t=(1, 3), h=(1, 1), pelvis=1, legs="wide", near="slam"),
        F(t=(1, 3), h=(1, 1), pelvis=1, legs="wide", near="ground"),
        F(t=(1, 2), h=(1, 1), pelvis=1, legs="wide", near="ground"),
        F(t=(0, 1), near="guard"),
    ],
    "cast_ring": [
        F(t=(0, -1), near="spread"),
        F(t=(0, -1), h=(0, -1), near="spread", lag=(0, -1)),
        F(t=(-1, -1), h=(-1, -1), near="spread_back"),
        F(t=(1, 0), near="spread", lag=(0, 1)),
        F(t=(0, 1), near="sweep"),
        F(),
    ],
    "attack_fan": [
        F(t=(-1, 0), near="cock", far="guard"),
        F(t=(-1, 2), h=(0, 1), pelvis=1, legs="wide", near="cock", far="guard"),
        F(t=(-2, 2), h=(-1, 1), pelvis=1, legs="wide", near="cock", far="guard", lag=(-1, 0)),
        F(t=(2, 1), legs="wide", near="punch", far="guard"),
        F(t=(1, 1), legs="wide", near="punch", far="guard", lag=(1, 0)),
        F(),
    ],
    "charge": [
        F(t=(1, 2), h=(2, 3), pelvis=1, near="guard", far="guard"),
        F(t=(2, 4), h=(4, 5), pelvis=2, legs="charge", near="guard", far="guard", lag=(-1, 0)),
        F(t=(4, 3), h=(5, 4), pelvis=1, legs="step_a", near="guard", far="guard", lag=(-2, 0)),
        F(t=(4, 3), h=(5, 4), pelvis=1, legs="step_b", near="guard", far="guard", lag=(-2, 0)),
        F(t=(-1, 1), h=(-1, 0), legs="wide", near="rest"),
        F(),
    ],
    "summon": [
        F(t=(0, -1), near="up"),
        F(t=(0, -2), h=(0, -1), near="up", lag=(0, -1)),
        F(t=(0, 2), h=(0, 1), pelvis=1, near="sweep"),
        F(),
    ],
    "stomp": [
        F(t=(0, -1), legs="lift", near="balance"),
        F(t=(-1, -2), h=(0, -1), legs="lift", near="balance", lag=(0, -1)),
        F(t=(1, 2), h=(1, 1), pelvis=1, legs="wide", near="guard"),
        F(t=(0, 1), legs="wide", near="rest"),
        F(),
    ],
    "enrage": [
        F(t=(-1, 0), h=(-1, 0), near="spread_back"),
        F(t=(0, -2), h=(0, -2), near="spread", lag=(0, -1)),
        F(t=(0, 1), near="rest"),
    ],
    "hurt": [F(), F(t=(-1, 0), h=(-2, 0), lag=(1, 0)), F(lag=(-1, 0))],
    "death": [
        F(),
        F(t=(-1, 1), h=(-1, 1), fall=0.12),
        F(t=(0, 2), h=(0, 3), fall=0.45),
        F(t=(0, 3), fall=0.8, core=False),
        F(fall=1.0, core=False),
    ],
}
FRAMES["combat_idle"] = None  # an alias of idle (style.json)


# ============================================================================== composing a frame
def stones_for(d: str) -> dict[str, Stone]:
    body = BODY_E if d == "e" else BODY_S
    legs = LEGS_E if d == "e" else LEGS_S
    out = {}
    seeds = {"torso": 3, "head": 5, "pelvis": 7, "leg_near": 11, "leg_far": 13}
    for name, (w, h, _) in {**body, **legs}.items():
        far = d == "e" and name == "leg_far"
        out[name] = Stone(name, w, h, far=far, moss=name in ("head", "torso"),
                          seed=seeds.get(name, 1), crack=name in seeds and name != "pelvis",
                          p=3.2 if name.startswith("crown") else 2.6)
    for side in ("near", "far"):
        for i, (name, w, h) in enumerate(ARM_STONES):
            far = d == "e" and side == "far"
            out[f"{side}_{name}"] = Stone(f"{side}_{name}", w, h, far=far,
                                          moss=name == "shoulder" and not far,
                                          seed=17 + i + (10 if side == "far" else 0),
                                          crack=name in ("shoulder", "fist"))
    return out


def rubble(d: str, name: str, st: Stone, c: tuple[float, float]) -> tuple[float, float]:
    """Where a stone ends up when the warden falls apart: on the ground, spread outward, the
    head and shoulders on top of the pile."""
    lift = {"head": 7, "crown_l": 3, "crown_m": 12, "crown_r": 3, "torso": 1,
            "near_shoulder": 3, "far_shoulder": 3}.get(name, 0)
    x = AXIS + (c[0] - AXIS) * 1.18
    return x, 59 - (st.h - 1) / 2 - lift


def frame(d: str, spec) -> dict:
    """The layers' codes, the points and the stones' boxes for one frame."""
    ex = (lambda v: v) if d == "e" else (lambda v: 0)
    tdx, tdy = ex(spec["t"][0]), spec["t"][1]
    hdx, hdy = tdx + ex(spec["h"][0]), tdy + spec["h"][1]
    lx, ly = ex(spec["lag"][0]), spec["lag"][1]
    body = BODY_E if d == "e" else BODY_S
    legs = LEGS_E if d == "e" else LEGS_S
    stones = stones_for(d)
    centers: dict[str, tuple[float, float]] = {}
    for name, (_, _, (cx, cy)) in body.items():
        if name == "pelvis":
            centers[name] = (cx + tdx // 2, cy + spec["pelvis"])
        elif name == "torso":
            centers[name] = (cx + tdx, cy + tdy)
        else:
            centers[name] = (cx + hdx, cy + hdy)
    near_off, far_off = LEG_POSES[d][spec["legs"]]
    for name, off in (("leg_near", near_off), ("leg_far", far_off)):
        _, _, (cx, cy) = legs[name]
        centers[name] = (cx + off[0], cy + off[1])
    for side in ("near", "far"):
        pts = arm_pose(d, side, spec[side])
        for (name, _, _), (cx, cy) in zip(ARM_STONES, pts):
            centers[f"{side}_{name}"] = (cx + tdx + lx, cy + tdy + ly)
    if spec["fall"]:
        f = spec["fall"]
        for name, c in list(centers.items()):
            rx, ry = rubble(d, name, stones[name], c)
            centers[name] = (c[0] + (rx - c[0]) * f, c[1] + (ry - c[1]) * f * f ** 0.3)

    canvas = E()
    owner = np.full((SIZE, SIZE), "", object)
    on_top = np.full((SIZE, SIZE), "", object)  # the layer that drew each final pixel
    layers = {k: E() for k in ("arm_far", "body", "arm_near", "skull", "leaves", "berries", "bands")}
    boxes: dict[str, tuple[int, int, int, int]] = {}
    face: dict[str, list[int]] = {}
    seed = {"near": 1, "far": 2}

    def put(layer, name, codes, x0, y0, clip=False, ring=True):
        if clip:  # extras stay where their outline still mirrors inside the safe area (x 2..60)
            ys, xs = np.mgrid[0:codes.shape[0], 0:codes.shape[1]]
            codes = codes.copy()
            codes[(xs + x0 < 3) | (xs + x0 > SIZE - 5) | (ys + y0 < 3)] = CLEAR
        if not ring:  # drawn straight on (claws on a fist): no contour cutting them up
            m = np.zeros((SIZE, SIZE), bool)
            for (cy, cx), v in np.ndenumerate(codes):
                X, Y = x0 + cx, y0 + cy
                if v != CLEAR and 0 <= X < SIZE and 0 <= Y <= 59:
                    layers[layer][Y, X] = v
                    canvas[Y, X] = v
                    m[Y, X] = True
            owner[m] = name
            on_top[m] = layer
            return m
        m = paste(layers[layer], canvas, codes, x0, y0, bottom=59)
        owner[m] = name
        on_top[m] = layer
        return m

    def stone(layer, name):
        st = stones[name]
        codes, x0, y0 = st.at(*centers[name])
        put(layer, name, codes, x0, y0)
        boxes[name] = (x0, y0, st.w, st.h)
        if name == "torso" and d != "n" and spec["core"]:
            face["core"] = draw_socket(layers[layer], canvas, d, x0, y0, st)

    def leaves(at, w, h, dx=0, dy=0, k=0, berries=()):
        cx, cy = centers[at]
        codes = leaf_codes(w, h, seed=k)
        x0 = int(round(cx + dx - (codes.shape[1] - 1) / 2))
        y0 = int(round(cy + dy - (codes.shape[0] - 1) / 2))
        put("leaves", f"{at}_leaves", codes, x0, y0, clip=True)
        for bx, by in berries:  # 2 x 2: a lit row over a dark one
            put("berries", f"{at}_berry", np.array([[1, 1], [0, 0]], np.int8),
                int(round(cx + dx + bx)), int(round(cy + dy + by)), clip=True)

    def band(name, row):
        x0, y0, w, h = boxes[name]
        codes = np.full((2, w - 2), 3, np.int8)
        codes[1, :] = 1
        put("bands", f"{name}_band", codes, x0 + 1, y0 + row)

    def claws(name, foot=False):
        x0, y0, w, h = boxes[name]
        if d == "e":
            spots = [(x0 + w - 1, y0 + h - 3)] if foot else \
                [(x0 + w - 1, y0 + 1), (x0 + w - 1, y0 + h // 2), (x0 + w - 2, y0 + h - 2)]
            pattern = CLAW_E
        else:
            spots = [(x0 + 1, y0 + h - 4), (x0 + w - 3, y0 + h - 4)] if foot else \
                [(x0 + 2, min(y0 + h - 3, 56)), (x0 + w - 4, min(y0 + h - 3, 56))]  # a fist on
            # the ground keeps its claws whole, above the ground row
            pattern = CLAW_S
        for X, Y in spots:
            codes = np.full((3, 3), CLEAR, np.int8)
            for cx, cy, v in pattern:
                codes[cy, cx] = v + 1  # bone: a shade lighter than the pattern's index
            put("skull", f"{name}_claw", codes, X, Y, clip=True, ring=False)

    def arm(side):
        names = [f"{side}_{n}" for n, _, _ in ARM_STONES]
        for n in names:
            stone(f"arm_{side}", n)
        band(f"{side}_upper", 2)
        leaves(f"{side}_fore", 12, 7, k=seed[side] + 3, berries=[(1, -1)])
        leaves(f"{side}_shoulder", 13, 8, dy=-2, k=seed[side] + 5, berries=[(-3, -1)])
        claws(f"{side}_fist")

    def skull():
        cx, cy = centers["head"]
        ox, oy = SKULL_ORIGIN[d]
        X0, Y0 = int(round(cx)) + ox, int(round(cy)) + oy
        far, near = antler_points(d)

        def stamp(pts, name):
            if not pts:
                return
            mx0 = min(p[0] for p in pts)
            my0 = min(p[1] for p in pts)
            codes = np.full((max(p[1] for p in pts) - my0 + 1, max(p[0] for p in pts) - mx0 + 1),
                            CLEAR, np.int8)
            for x, y, v in pts:
                codes[y - my0, x - mx0] = v
            put("skull", name, codes, X0 + mx0, Y0 + my0)

        rows = SKULL[d]
        codes = np.full((len(rows), len(rows[0])), CLEAR, np.int8)
        sockets = []
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch.isdigit():
                    codes[y, x] = int(ch)
                elif ch in "OE":
                    codes[y, x] = INK
                    if ch == "E":
                        sockets.append((x, y))
        stamp(far, "antler_far")
        if d != "e":
            stamp(near, "antlers")
        put("skull", "head", codes, X0, Y0)
        boxes["head"] = (X0, Y0, codes.shape[1], codes.shape[0])
        if d == "e":
            stamp(near, "antlers")
        if sockets:
            low = max(y for _, y in sockets)
            xs = sorted(x for x, y in sockets if y == low)
            face["eyes"] = [X0 + (xs[0] + xs[-1] + 1) // 2 if d == "s" else X0 + xs[0], Y0 + low]

    def body_part():
        for n in ("leg_far", "leg_near"):
            stone("body", n)
            band(n, 3)
            leaves(n, 11, 6, dy=-1, k=7 if n == "leg_far" else 9, berries=[(1, -1)])
            claws(n, foot=True)
        stone("body", "pelvis")
        stone("body", "torso")
        tx, ty = centers["torso"]
        mane = {"s": (31, 12, 0, -6), "e": (22, 12, -6, -4), "n": (33, 16, 0, -4)}[d]
        leaves("torso", mane[0], mane[1], dx=mane[2], dy=mane[3], k=11,
               berries=[(-10, -1), (-4, 2), (5, -2), (11, 1)] if d != "e" else [(-6, 0), (2, -2)])
        skull()

    if d == "n":
        order = [lambda: arm("far"), lambda: arm("near"), body_part]
    else:
        order = [lambda: arm("far"), body_part, lambda: arm("near")]
    if spec["behind"] and d == "e":  # arms raised behind the head: the body over them
        order = [lambda: arm("far"), lambda: arm("near"), body_part]
    if spec["fall"] >= 0.8:  # in the pile the body lies under the arms
        order = [body_part, lambda: arm("far"), lambda: arm("near")]
    for step in order:
        step()
    # flatten: each layer keeps only what shows, so the engine's fixed z-order gives this frame
    # whatever the per-frame order was (arms behind the head, a pile of stones)
    for k in layers:
        layers[k][on_top != k] = CLEAR
    for k in layers:
        layers[k] = despeckle_stone(layers[k], canvas)
    tidy_visible({k: layers[k] for k in ("arm_far", "body", "arm_near")}, E())
    for k, layer in layers.items():  # a pixel cut off from its own layer becomes a dark detail
        solid = layer >= 0
        p = np.pad(solid, 1)
        alone = solid & ~(p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:])
        layer[alone] = INK

    def center(name):
        x0, y0, w, h = boxes[name]
        return [int(round(x0 + (w - 1) / 2)), int(round(y0 + (h - 1) / 2))]

    def bottom(name):
        x0, y0, w, h = boxes[name]
        return [int(round(x0 + (w - 1) / 2)), min(y0 + h - 1, 59)]

    hx, hy = center("head")
    nf, ff = center("near_fist"), center("far_fist")
    summon = {"s": [31, 61], "e": [54, 58], "n": [31, 44]}[d]
    pts = {
        "head": [hx, boxes["head"][1]], "torso": center("torso"),
        "core": face.get("core") or center("torso"), "eyes": face.get("eyes") or [hx, hy],
        "hand_near": nf, "fist_far": ff, "hand_far": ff,
        "slam": [int(round((nf[0] + ff[0]) / 2)), min(59, max(bottom("near_fist")[1], bottom("far_fist")[1]))],
        "foot_near": bottom("leg_near"), "foot_far": bottom("leg_far"),
        "summon_point": summon, "planted": [],
    }
    stones_only = {k: v for k, v in boxes.items() if k in stones}
    return {"layers": layers, "points": pts, "boxes": stones_only, "canvas": canvas}


def draw_socket(layer, canvas, d, x0, y0, st) -> list[int]:
    """The core's socket in the torso: an outline-colored ring around a 3 x 3 gem (s), or a
    sliver at the chest's front edge (e). Returns the core point."""
    if d == "s":
        cx, cy = x0 + (st.w - 1) // 2, y0 + 7
    else:  # a sliver at the chest's front, below the near shoulder
        cx, cy = x0 + st.w - 2, y0 + 11
    for y in range(cy - 2, cy + 3):
        for x in range(cx - 2, cx + 3):
            if 0 <= x < SIZE and canvas[y, x] != CLEAR and (abs(x - cx) == 2 or abs(y - cy) == 2):
                layer[y, x] = INK
                canvas[y, x] = INK
    return [cx, cy]


def draw_visor(layer, canvas, d, x0, y0, st, spec) -> list[int]:
    """A dark slit across the face (s) or at its front (e), where the eyes glow."""
    y = y0 + 5
    if d == "s":
        xs = range(x0 + 3, x0 + st.w - 3)
        cx = x0 + (st.w - 1) // 2
    else:
        xs = range(x0 + st.w - 6, x0 + st.w)
        cx = x0 + st.w - 3
    for x in xs:
        if canvas[y, x] != CLEAR:
            layer[y, x] = INK
            canvas[y, x] = INK
    return [cx, y]


def draw_moss(canvas, owner, stones, boxes, d) -> np.ndarray:
    """Moss (hide shades 0..2) on the visible top rows of mossy stones: a light row, a darker
    one, and a few drips."""
    moss = E()
    for name, st in stones.items():
        if not st.moss or name not in boxes:
            continue
        x0, y0, w, h = boxes[name]
        x_from, x_to = x0 + w // 5, x0 + w - w // 4
        for x in range(x_from, x_to + 1):
            col = [y for y in range(y0, y0 + h) if 0 <= x < SIZE and 0 <= y < SIZE and owner[y, x] == name
                   and canvas[y, x] >= 0]
            if not col:
                continue
            top = col[0]
            for y in (top, top + 1):
                if y in col:  # light in the box's top rows, a band that stays connected
                    moss[y, x] = 2 if y <= y0 + 1 else 1
            if (x * 7 + y0) % 5 == 0 and top + 3 in col:  # a 2 px drip
                moss[top + 2, x] = 0
                moss[top + 3, x] = 0
    for _ in range(3):
        moss = despeckle_stone(moss, canvas, inplace=True)
        lone = (moss >= 0) & ~_has_neighbor(moss >= 0)
        moss[lone] = CLEAR
    return moss


def tidy_visible(layers: dict, moss: np.ndarray) -> None:
    """What the validator sees: a stone pixel with no visible 4-neighbor of its shade (its
    neighbors under moss, or contours around it) takes its visible stone neighbors' most common
    shade, or becomes an outline-colored corner when it has none. In place."""
    stone = E()
    who = np.full((SIZE, SIZE), "", object)
    for k, layer in layers.items():
        m = layer != CLEAR
        stone[m] = layer[m]
        who[m] = k
    visible = (stone >= 0) & (moss == CLEAR)
    for y in range(SIZE):
        for x in range(SIZE):
            if not visible[y, x]:
                continue
            v = stone[y, x]
            near = [stone[y + dy, x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= y + dy < SIZE and 0 <= x + dx < SIZE and visible[y + dy, x + dx]]
            if v in near:
                continue
            new = INK
            if near:
                counts = {n: near.count(n) for n in near}
                new = sorted(counts, key=lambda n: (-counts[n], n))[0]
            layers[who[y, x]][y, x] = new
            stone[y, x] = new


def _has_neighbor(mask: np.ndarray) -> np.ndarray:
    p = np.pad(mask, 1)
    return p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]


def despeckle_stone(layer: np.ndarray, canvas: np.ndarray, inplace: bool = False) -> np.ndarray:
    """Merge lone shade pixels (no 4-neighbor of the same shade) into their neighbors' most common
    shade; outline-colored details and empty pixels are untouched. `inplace` reads the pixels
    already changed in this pass, so two lone neighbors agree instead of swapping shades."""
    out = layer.copy()
    if inplace:
        layer = out
    for y in range(SIZE):
        for x in range(SIZE):
            v = layer[y, x]
            if v < 0:
                continue
            near = [layer[y + dy, x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= y + dy < SIZE and 0 <= x + dx < SIZE]
            if v in near:
                continue
            same = [n for n in near if n >= 0]
            if same:
                counts = {n: same.count(n) for n in same}
                out[y, x] = sorted(counts, key=lambda n: (-counts[n], n))[0]
    return out


# ============================================================================== combat data
def fist_box(boxes) -> list[int]:
    xs = [b[0] for k, b in boxes.items() if k.endswith("fist")]
    ys = [b[1] for k, b in boxes.items() if k.endswith("fist")]
    x1 = max(b[0] + b[2] for k, b in boxes.items() if k.endswith("fist"))
    y1 = max(b[1] + b[3] for k, b in boxes.items() if k.endswith("fist"))
    return [min(xs) - 2, min(ys) - 2, x1 - min(xs) + 4, min(y1, 60) - min(ys) + 4]


def body_front(d: str, boxes) -> list[int]:
    """The charging body's leading half: in front facing e, low facing s, high facing n."""
    x0 = min(b[0] for b in boxes.values())
    x1 = max(b[0] + b[2] for b in boxes.values())
    top = boxes["head"][1]
    tx, ty, tw, th = boxes["torso"]
    mid = ty + th // 2
    if d == "e":
        cx = tx + tw // 2
        return [cx, top, x1 - cx + 2, 60 - top]
    if d == "s":
        return [x0, mid, x1 - x0, 60 - mid]
    return [x0, top, x1 - x0, mid - top]


HITBOXES = {"attack_slam": (3, 4), "charge": (2, 3)}


# ============================================================================== writing
def main() -> None:
    import shutil
    anims = load_anims(STYLE, RIG)
    slots = ("body", "arm_near", "arm_far", "skull", "leaves", "berries", "bands")
    layers = {k: {} for k in slots}
    anchors = {}
    for anim, frames in FRAMES.items():
        if frames is None:
            continue
        assert len(frames) == anims[anim].frames, (anim, len(frames), anims[anim].frames)
        for k in layers:
            layers[k][anim] = {}
        anchors[anim] = {d: [] for d in DIRS}
        for i, spec in enumerate(frames):
            for d in DIRS:
                f = frame(d, spec)
                for k in slots:
                    layers[k][anim][(d, i)] = f["layers"][k]
                pts = f["points"]
                if i in HITBOXES.get(anim, ()):
                    pts["hitboxes"] = [fist_box(f["boxes"]) if anim == "attack_slam" else
                                       body_front(d, f["boxes"])]
                if not spec["core"]:
                    pts["hide"] = ["core"]
                anchors[anim][d].append(pts)
    counts = {a: len(f) for a, f in FRAMES.items() if f is not None}
    # swing trails: the fists carry no art, only the white arc each strike traces (the
    # compositor's smear_<anim> for a drawn held item): the slam brings both fists down from
    # overhead, the fan's punch drives the near fist forward
    fists = {a: {(d, i): E() for d in DIRS for i in range(n)} for a, n in counts.items()}
    trails = {}
    for anim, sides in (("attack_slam", ("near", "far")), ("attack_fan", ("near",))):
        cells = {(d, i): E() for d in DIRS for i in range(counts[anim])}
        for i in sorted(anims[anim].flags.get("active", ()))[:1]:
            for d in DIRS:
                before, now = frame(d, FRAMES[anim][i - 1]), frame(d, FRAMES[anim][i])
                for side in sides:
                    fist = "hand_near" if side == "near" else "fist_far"
                    x0, y0, w, h = now["boxes"][f"{side}_shoulder"]
                    pivot = (x0 + w / 2, y0 + h / 2)
                    path = arc_path(tuple(before["points"][fist]), tuple(now["points"][fist]), pivot)
                    for x, y, rank in crescent(path, 4):
                        if 3 <= x <= SIZE - 5 and 3 <= y <= 59 and cells[(d, i)][y, x] == CLEAR:
                            cells[(d, i)][y, x] = rank + 1  # metal shades 1..3: rim, mid, core
        trails[f"smear_{anim}"] = cells
    write_part("held_near", "warden_fists", {
        "material": "metal", "kind": "animated", "lags": False, "rigs": [RIG],
        "notes": "No art: the white swing trails of the slam and the punch (smear_<anim>)."},
        {**fists, **trails}, {**counts, **{k: counts[k[6:]] for k in trails}}, size=SIZE)
    parts = {
        "body": ("stone", "Pelvis, legs and torso (with the core's socket): charcoal boulders."),
        "arm_near": ("stone", "Shoulder, upper arm, forearm and fist: separate boulders, in front."),
        "arm_far": ("stone", "The same four boulders on the far side (darker facing e, where it is behind)."),
        "skull": ("bone", "The skull with its branching antlers, and the claws on the fists and feet."),
        "leaves": ("leaf", "A jagged mane over the shoulders and back, leaf sleeves on the forearms "
                           "and shins."),
        "berries": ("fruit", "Berries in the leaves."),
        "bands": ("metal", "Brass bands round the upper arms and legs."),
    }
    for slot, (material, notes) in parts.items():
        variant = RIG if slot in ("body", "arm_near", "arm_far") else "warden"
        write_part(slot, variant, {"material": material, "kind": "animated", "lags": False,
                                   "rigs": [RIG], "notes": notes}, layers[slot], counts, size=SIZE)
    old_moss = ROOT_DIR / "parts" / "moss" / "warden"
    if old_moss.is_dir():
        shutil.rmtree(old_moss)
        if not any(old_moss.parent.iterdir()):
            old_moss.parent.rmdir()
    # rigid glow: the core gem and the eyes, at idle frame 0
    f0 = {d: frame(d, F()) for d in DIRS}
    core, eyes = {}, {}
    for d in DIRS:
        c, e = E(), E()
        if d != "n":
            cx, cy = f0[d]["points"]["core"]
            for y in range(cy - 1, cy + 2):
                for x in (range(cx - 1, cx + 2) if d == "s" else range(cx, cx + 2)):
                    c[y, x] = 0
            ex, ey = f0[d]["points"]["eyes"]
            for ox in ((-4, -3, 3, 4) if d == "s" else (0, 1)):
                e[ey, ex + ox] = 0
        core[(d, 0)], eyes[(d, 0)] = c, e
    write_part("core", "warden", {"material": "eyes", "kind": "rigid", "attach": "core", "origin": "auto",
                                  "lags": False, "rigs": [RIG],
                                  "notes": "The glowing heart in the chest (a glow eye preset)."},
               {"rigid": core}, size=SIZE)
    write_part("eyes", "warden", {"material": "eyes", "kind": "rigid", "attach": "eyes", "origin": "auto",
                                  "lags": False, "rigs": [RIG],
                                  "allow_singletons": {},
                                  "notes": "Two eyes glowing in the skull's sockets."},
               {"rigid": eyes}, size=SIZE)
    write_anchors(RIG, anchors)
    base = {
        "rig": RIG, "timing_profile": "boss", "seed": 1,
        "parts": {"skull": "warden", "leaves": "warden", "berries": "warden", "bands": "warden",
                  "core": "warden", "eyes": "warden", "held_near": "warden_fists"},
        "anims": ["idle", "walk", "combat_idle", "attack_slam", "cast_ring", "attack_fan", "charge",
                  "summon", "stomp", "enrage", "hurt", "death"],
    }
    write_recipe("monsters/stone_warden.yaml", {
        "name": "stone_warden", "family": "stone_warden", **base,
        "colors": {"stone": "charcoal", "bone": "antler", "leaf": "spring", "fruit": "berry",
                   "metal": "gold", "eyes": "glow leaf"}})
    write_recipe("monsters/stone_warden_enraged.yaml", {
        "name": "stone_warden_enraged", "family": "stone_warden", **base,
        "colors": {"stone": "charcoal", "bone": "antler", "leaf": "autumn", "fruit": "blood",
                   "metal": "gold", "eyes": "glow red"}})
    print("wrote the stone warden")


if __name__ == "__main__":
    main()
