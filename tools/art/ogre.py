"""The ogre: the humanoid_large rig on the medium canvas (MONSTERS.md sections 3 and 5.4).

48 x 48, pivot (23, 43), mirror axis x = 23. About 28 rows from the top of the head to the soles
(a 12-row head, 43%) plus a topknot: a hunched brute with the head sunk between round shoulders,
a pot belly, long arms with big fists, short legs and a club that rests on its shoulder.

How it is drawn (the same pixel scale as the 32 px cast, never an upscale):
- heads, torsos and legs are hand-drawn character grids (the s view as a left half mirrored
  around x = 23; the n view the same silhouette shaded as a back);
- arms and the club are shaded tubes through a few joint points per pose (`tube`), lit like the
  grids, then despeckled; an arm in front of the body gets a 1 px contour (an outline-colored
  detail) where it crosses the torso, and a club behind the body stops 1 px short of it, so the
  generated outline separates them.

Skin shades: 0 #755e4d, 1 #8f7863, 2 #a8957e (the ogre preset); 'O' = an outline-colored detail.

Run after the FX library: .venv/bin/python tools/art/ogre.py
"""

from __future__ import annotations

import numpy as np

from artlib import empty, g, grid, write_anchors, write_part, write_recipe
from pixelforge.anim import load_anims
from artlib import STYLE

RIG = "humanoid_large"
DIRS = ("s", "e", "n")
SIZE = 48
AXIS = 23
CLEAR, INK = grid.CLEAR, grid.INK


def E() -> np.ndarray:
    return empty(SIZE)


def G(rows: list[str], x0: int, y0: int) -> np.ndarray:
    return g(rows, x0, y0, SIZE)


def mirror_x(codes: np.ndarray) -> np.ndarray:
    """Mirror a cell around the axis (x' = 2 * axis - x): the n view's arms from the s view's."""
    out = E()
    for x in range(SIZE):
        x2 = 2 * AXIS - x
        if 0 <= x2 < SIZE:
            out[:, x2] = codes[:, x]
    return out


def sym(left: list[str]) -> list[str]:
    """A left half (x 5..23, the center column last) mirrored into full rows (x 5..41)."""
    for r in left:
        assert len(r) == 19, (r, len(r))
    return [r + r[::-1][1:] for r in left]


# ============================================================================== front (s)
LEFT_S = [  # x 5..23, y 17..40
    "................222",    # y17  the dome
    "..............11222",
    ".............112222",
    "............0112222",
    "............0122222",    # y21  the brow
    "..........111100022",    # y22  ears, sockets (eyes at x 20 and 26), the nose bridge
    "..........011100022",
    "..........201111100",    # y24  the shadow under the nose; the trapezius rises
    "........122011OOOOO",    # y25  the mouth
    "......12222011 22222".replace(" ", ""),  # y26  the lower lip (an underbite)
    "..12221122210000000",    # y27  the shadow under the jaw
    ".1222110122222222 21".replace(" ", ""),  # y28  deltoid, chest
    ".12211101122222221 1".replace(" ", ""),
    ".011110011111111111",    # y30
    "..01110.0100000001 2".replace(" ", ""),  # y31  under the pecs; the arm parts from the body
    "..0121.0112222222 22".replace(" ", ""),  # y32  the belly
    "..0121.0111222222 22".replace(" ", ""),
    ".01221.01111222222 0".replace(" ", ""),  # y34  the navel
    ".01221.01111122222 0".replace(" ", ""),
    ".01211..011111111 11".replace(" ", ""),
    "012221...0000000000",    # y37  the fists
    "012221.............",
    "011110.............",
    ".0000..............",    # y40
]
FIG_S = G(sym(LEFT_S), 5, 17)

LEFT_N = [  # the same silhouette from behind: the back of the skull, shoulder blades, a spine
    "................222",    # y17
    "..............11222",
    ".............112222",
    "............0112222",
    "............0122222",
    "..........111111222",    # y22  ears
    "..........011111111",
    "..........201111111",    # y24
    "........12210000000",    # y25  the nape in shadow
    "......1222221111111",    # y26
    "..12221122212222222",    # y27  the upper back
    ".1222110122222222 21".replace(" ", ""),
    ".12211101122222211 0".replace(" ", ""),  # y29  shoulder blades, the spine
    ".011110011111111110",
    "..01110.01111111110",    # y31
    "..0121.0111111111 10".replace(" ", ""),
    "..0121.0111111111 10".replace(" ", ""),
    ".01221.01111111111 0".replace(" ", ""),
    ".01221.01111111111 0".replace(" ", ""),
    ".01211..01111111111",
    "012221...0000000000",    # y37
    "012221.............",
    "011110.............",
    ".0000..............",
]
FIG_N = G(sym(LEFT_N), 5, 17)

# the head's rows in s and n (x ranges): everything else in rows 17..27 is shoulder or chest
HEAD_ROWS_S = {17: (21, 25), 18: (19, 27), 19: (18, 28), 20: (17, 29), 21: (17, 29), 22: (15, 31),
               23: (15, 31), 24: (16, 30), 25: (16, 30), 26: (16, 30), 27: (17, 29)}


def split_head(fig: np.ndarray, rows: dict, neck: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    """(head, torso): the head's pixels, and the rest with the neck filled in under the head so a
    raised head never leaves a hole."""
    head, torso = E(), fig.copy()
    for y, (x0, x1) in rows.items():
        head[y, x0:x1 + 1] = fig[y, x0:x1 + 1]
        torso[y, x0:x1 + 1] = CLEAR
    y0, y1, shade = neck
    for y in range(y0, y1 + 1):
        x0, x1 = rows.get(y, (0, -1))
        for x in range(x0, x1 + 1):
            if torso[y, x] == CLEAR:
                torso[y, x] = shade
    return head, torso


HEAD_S, TORSO_S = split_head(FIG_S, HEAD_ROWS_S, (23, 27, 1))
HEAD_N, TORSO_N = split_head(FIG_N, HEAD_ROWS_S, (23, 27, 1))
# the hanging arms (hand-drawn) come off the torso; poses draw their own
NEAR_HANG_S = TORSO_S.copy()
NEAR_HANG_S[:32] = CLEAR
NEAR_HANG_S[:, 11:] = CLEAR
FAR_HANG_S = TORSO_S.copy()
FAR_HANG_S[:32] = CLEAR
FAR_HANG_S[:, :36] = CLEAR
for t in (TORSO_S, TORSO_N):
    t[32:, :11] = CLEAR
    t[32:, 36:] = CLEAR
NEAR_HANG_N, FAR_HANG_N = mirror_x(NEAR_HANG_S), mirror_x(FAR_HANG_S)  # same shapes, sides swap

HEAD_ROAR_S = HEAD_S.copy()  # the jaw drops: an open mouth, tusks out
for x in range(19, 28):
    HEAD_ROAR_S[25, x] = INK
    HEAD_ROAR_S[26, x] = INK
for x in range(20, 27):
    HEAD_ROAR_S[24, x] = INK if 21 <= x <= 25 else HEAD_ROAR_S[24, x]
HEAD_ROAR_S[27, 17:30] = HEAD_S[26, 17:30]
HEAD_ROAR_S[28, 18:29] = 0

# ============================================================================== side (e)
HEAD_E = G([  # x 17..34, y 17..27: the brow juts, a deep socket, a big nose, an underbite
    "....222222........",
    "..1122222221......",
    ".112222222221.....",
    ".1222222222221....",
    "0122222222222221..",    # y21  the brow
    "011121222222001...",    # y22  the ear, the socket (eye at x 30)
    "01111022222200122.",    # y23  the nose
    ".0111111111111122 1".replace(" ", ""),
    ".0111111111OOOOO22",    # y25  the mouth; the jaw juts past it
    "..011111111111 2222".replace(" ", ""),
    "...00000000000000.",    # y27  the shadow under the jaw
], 17, 17)
HEAD_ROAR_E = HEAD_E.copy()
for x in range(28, 33):
    HEAD_ROAR_E[25, x] = INK
    HEAD_ROAR_E[26, x] = INK
HEAD_ROAR_E[27, 20:34] = HEAD_E[26, 20:34]
HEAD_ROAR_E[27, 31:35] = 2
HEAD_ROAR_E[28, 21:33] = 0

TORSO_E_EDGES = {  # y: (back x, front x): a hunched back, a deep chest, the belly in front
    23: (15, 18), 24: (14, 18), 25: (13, 18), 26: (12, 19), 27: (11, 20), 28: (11, 30), 29: (11, 31),
    30: (11, 32), 31: (11, 33), 32: (11, 34), 33: (11, 34), 34: (11, 34), 35: (12, 33), 36: (13, 32),
    37: (14, 30),
}


def torso_e() -> np.ndarray:
    """The side torso, shaded by rule: lit from above and in front, dark along the back and
    under the belly, a highlight on the belly."""
    c = E()
    for y, (x0, x1) in TORSO_E_EDGES.items():
        for x in range(x0, x1 + 1):
            if y <= 27:
                s = 2 if x > x0 else 1
            elif x <= x0 + 1:
                s = 0 if x == x0 else 1
            elif y >= 36:
                s = 0
            elif y == 30 and 24 <= x <= 31:
                s = 1  # under the chest
            elif y <= 29:
                s = 2 if x >= 16 else 1
            else:
                bx, by = (x - 28.5) / 5.2, (y - 32.5) / 2.6  # the belly's highlight
                s = 2 if bx * bx + by * by <= 1 else 1
            c[y, x] = s
    for y in range(31, 36):
        c[y, TORSO_E_EDGES[y][1]] = 1 if y < 35 else 0  # the belly's front rim
    c[35, 23:33] = 0
    return c


TORSO_E = torso_e()

# ============================================================================== legs
LEGS_S = {
    "stand": G([
        ".0112210...0122110.",   # y38, x 14..32
        ".0112210...0122110.",
        ".0111210...0121110.",
        ".0111110...0111110.",
        "001222100.001222100",
        "011111110.011111110",
    ], 14, 38),
    "step_l": G([  # the left foot lifted
        ".0112210...0122110.",
        ".0112210...0122110.",
        ".0111210...0121110.",
        "001222100..0111110.",
        "011111110.001222100",
        "..........011111110",
    ], 14, 38),
    "wide": G([
        "0112210.....0122110",
        "0112210.....0122110",
        "0111210.....0121110",
        "0111110.....0111110",
        "1222100.....0012221",
        "1111110.....0111111",
    ], 13, 38),
    "kneel": G([  # knees on the ground, shins hidden behind
        "..01222100.00122210..",
        ".0111111100011111110.",
        ".0000000000000000000.",
    ], 13, 41),
}
LEGS_S["step_r"] = mirror_x(LEGS_S["step_l"])
LEGS_N = {k: v.copy() for k, v in LEGS_S.items()}
LEGS_N["step_l"], LEGS_N["step_r"] = LEGS_S["step_r"], LEGS_S["step_l"]

LEGS_E = {
    "stand": G([  # x 14..32: the far leg darker
        "...01110..122221...",   # y37
        "...01110..122221...",
        "...01110..122211...",
        "...01110..112211...",
        "...00110..111111...",
        "..0111110012222210.",
        "..00000000111111110",
    ], 14, 37),
    "step_a": G([  # near leg forward, far leg back
        ".01110......12221..",
        ".01110......12221..",
        "011100......12211..",
        "011100.....112211..",
        "00110......111111..",
        "0111110....122222210",
        "0000000....011111111",
    ], 13, 37),
    "step_b": G([  # near leg back, far leg forward
        "........01110.12221.",
        ".......011100.12221.",
        "......0111000.12211.",
        "...12221.0110..1100.",
        "...111111.0110......",
        "..122222210111110...",
        "..011111111000000...",
    ], 13, 37),
    "wide": G([
        "..01110.......12221...",
        ".011100.......12221...",
        ".01110........122211..",
        "011100.........112211.",
        "00110..........111111.",
        "0111110........12222221",
        "0000000........01111111",
    ], 11, 37),
    "kneel": G([  # the near knee down in front, the far leg folded under
        "....0111..1222221.....",
        "...01111..12222221....",
        "..011111100111111110..",
    ], 12, 41),
}
LEGS_N["stand"] = LEGS_S["stand"]

# ============================================================================== arms and club
L_S = (0.0, -0.55, 0.83)    # light for s and n: from above, toward the viewer
L_E = (0.35, -0.55, 0.76)   # e: from above and in front


def _closest(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    n2 = dx * dx + dy * dy
    t = 0.0 if n2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / n2))
    return ax + t * dx, ay + t * dy, t


def tube(codes: np.ndarray, pts, radii, light, t=(0.35, 0.78), shades=(0, 1, 2)) -> np.ndarray:
    """A capsule chain through pts with a radius per point, shaded like a lit cylinder: the
    arm's and club's form. Paints codes in place and returns the painted mask."""
    lv = np.asarray(light, float)
    lv = lv / np.linalg.norm(lv)
    best = np.full((SIZE, SIZE), np.inf)
    shade = np.full((SIZE, SIZE), -1, np.int8)
    for (ax, ay), (bx, by), ra, rb in zip(pts, pts[1:], radii, radii[1:]):
        for y in range(SIZE):
            for x in range(SIZE):
                cx, cy, tt = _closest(x, y, ax, ay, bx, by)
                r = ra + (rb - ra) * tt
                d = np.hypot(x - cx, y - cy) / r
                if d <= 1.0 and d < best[y, x]:
                    best[y, x] = d
                    nx, ny = (x - cx) / r, (y - cy) / r
                    nz = np.sqrt(max(0.0, 1 - nx * nx - ny * ny))
                    i = nx * lv[0] + ny * lv[1] + nz * lv[2]
                    shade[y, x] = shades[2] if i >= t[1] else shades[1] if i >= t[0] else shades[0]
    m = shade >= 0
    codes[m] = shade[m]
    return m


# poses: shoulder, elbow, fist (idle frame 0 coordinates; they move with the upper body),
# the club's tip and whether the club is in front of the body or behind it
ARM_S = {
    "shoulder": ((9, 30), (8, 34), (10, 29), (5, 15), "front"),  # rest: the club on the shoulder
    "up": ((9, 29), (6, 25), (7, 21), (8, 8), "front"),
    "cocked": ((9, 29), (8, 22), (11, 16), (19, 6), "behind"),
    "slam": ((9, 30), (8, 33), (10, 34), (5, 41), "front"),
    "ground": ((9, 30), (8, 34), (10, 37), (5, 41), "front"),
    "flex": ((9, 29), (5, 26), (6, 21), (6, 10), "front"),
    "hang": None,
}
FAR_S = {"hang": None, "flex": ((37, 29), (41, 26), (40, 20))}
ARM_E = {  # the club stays 13 to 16 px long; the s and n views foreshorten it toward the viewer
    "shoulder": ((20, 28), (20, 35), (27, 31), (17, 18), "front"),
    "up": ((21, 28), (25, 23), (27, 19), (14, 9), "front"),
    "cocked": ((20, 28), (22, 21), (20, 14), (7, 20), "behind"),
    "slam": ((22, 29), (27, 31), (30, 32), (40, 40), "front"),
    "ground": ((22, 30), (26, 34), (29, 36), (40, 41), "front"),
    "flex": ((21, 28), (25, 22), (26, 17), (22, 7), "front"),
    "hang": ((21, 29), (21, 34), (22, 38), None, "front"),
}
FAR_E = {"hang": None, "flex": ((17, 28), (12, 24), (13, 17))}
DROPPED = {  # where the club lies once dropped; facing e it fell on the far side of the body
    "s": ((15, 41), (6, 41), "front"), "e": ((29, 41), (40, 41), "behind"), "n": ((31, 41), (40, 41), "front")}


def mirror_pt(p):
    return None if p is None else (2 * AXIS - p[0], p[1])


ARM_N = {k: None if v is None else (*[mirror_pt(p) for p in v[:4]], v[4]) for k, v in ARM_S.items()}
ARM_N["cocked"] = (*ARM_N["cocked"][:4], "front")  # behind its head is toward the viewer
ARM_N["slam"] = (*ARM_N["slam"][:4], "behind")
ARM_N["ground"] = (*ARM_N["ground"][:4], "behind")
FAR_N = {"hang": None, "flex": tuple(mirror_pt(p) for p in FAR_S["flex"])}


def shifted(p, dx, dy):
    return None if p is None else (p[0] + dx, p[1] + dy)


def arm_codes(d: str, spec, dx: int, dy: int, light) -> tuple[np.ndarray, np.ndarray]:
    """(arm, fist mask) for a tube pose."""
    sh, el, fi = (shifted(p, dx, dy) for p in spec[:3])
    c = E()
    tube(c, [sh, el, fi], [2.3, 2.3, 2.6], light)
    fist = E()
    m = tube(fist, [fi, fi], [3.0, 3.0], light)
    return grid.overlay(c, fist), m


def club_codes(grip, tip, light) -> np.ndarray:
    """The club from the grip toward the tip: a short handle end behind the fist, a shaft and a
    swelling head."""
    c = E()
    (gx, gy), (tx, ty) = grip, tip
    n = np.hypot(tx - gx, ty - gy)
    ux, uy = (tx - gx) / n, (ty - gy) / n
    start = (gx - 2.5 * ux, gy - 2.5 * uy)
    neck = (gx + (n - 6) * ux, gy + (n - 6) * uy)
    tube(c, [start, neck], [0.95, 1.15], light, shades=(0, 0, 1))  # the handle: dark wood
    tube(c, [neck, (tx, ty)], [1.15, 2.7], light, t=(0.3, 0.75))    # the head: lit
    return despeckle(c)


def dilate(mask: np.ndarray) -> np.ndarray:
    p = np.pad(mask, 1)
    return mask | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]


def contour(body: np.ndarray, arm: np.ndarray, keep_clear: np.ndarray) -> np.ndarray:
    """Body pixels bordering an arm drawn over it become outline-colored details, except near
    the shoulder joint (where the arm grows out of the body)."""
    out = body.copy()
    ring = dilate(arm != CLEAR) & ~(arm != CLEAR) & (body != CLEAR) & ~keep_clear
    out[ring] = INK
    return out


def near_disk(p, r) -> np.ndarray:
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    return (xx - p[0]) ** 2 + (yy - p[1]) ** 2 <= r * r


# ============================================================================== frames
def dirx(d: str, dx: int) -> int:
    return dx if d == "e" else 0  # leans happen along the facing; s and n bob in place


def F(b=(0, 0), h=(0, 0), legs="stand", near="shoulder", far="hang", head="rest", club=None):
    return {"b": b, "h": h, "legs": legs, "near": near, "far": far, "head": head, "club": club}


FRAMES = {
    "idle": [F(), F(b=(0, 1)), F(b=(0, 1), h=(0, 0)), F()],
    "walk": [F(legs="step_a"), F(b=(0, -1)), F(legs="step_b"), F(b=(0, -1))],
    "attack_heavy": [
        F(b=(0, -1), near="up"),                                    # lift
        F(b=(-1, -1), h=(-1, 0), near="cocked", legs="wide"),       # lean back: the big tell
        F(b=(-1, 1), h=(-1, 0), near="cocked", legs="wide"),        # peak squash
        F(b=(1, 1), h=(1, 1), near="slam", legs="wide"),            # slam, smear; hit
        F(b=(1, 2), h=(1, 1), near="ground", legs="wide"),          # on the ground; impact_big
        F(b=(1, 2), h=(1, 2), near="ground", legs="wide"),          # stuck low, bent
        F(b=(0, 1), near="shoulder"),                               # heave back
    ],
    "roar": [
        F(b=(0, -1), h=(0, -1), near="up"),
        F(b=(0, -1), h=(0, -1), near="flex", far="flex", head="roar"),
        F(b=(0, 0), h=(0, 0), near="shoulder"),
    ],
    "hurt": [F(), F(b=(-1, 0), h=(-1, 0)), F()],
    "death": [
        F(),
        F(b=(-1, 0), h=(-1, -1), near="hang", club="dropped"),
        F(b=(0, 3), h=(0, 1), near="hang", legs="kneel", club="dropped"),
        F(b=(0, 4), h=(0, 3), near="hang", legs="kneel", club="dropped"),
        F(b=(0, 4), h=(0, 3), near="hang", legs="kneel", club="dropped"),
    ],
}
FRAMES["combat_idle"] = None  # an alias of idle (style.json)

LEG_NAMES = {"s": {"step_a": "step_l", "step_b": "step_r"}, "n": {"step_a": "step_r", "step_b": "step_l"}}


def despeckle(codes: np.ndarray) -> np.ndarray:
    """Merge lone shade pixels into their neighbors' shade (ties darker); outline details and
    empty pixels are untouched."""
    out = codes.copy()
    for y in range(SIZE):
        for x in range(SIZE):
            v = codes[y, x]
            if v < 0:
                continue
            near = [codes[y + dy, x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= y + dy < SIZE and 0 <= x + dx < SIZE]
            if v in near:
                continue
            same = [n for n in near if n >= 0]
            if same:
                counts = {n: same.count(n) for n in same}
                out[y, x] = sorted(counts, key=lambda n: (-counts[n], n))[0]
    return out


def despeckle_visible(codes: np.ndarray, cover: np.ndarray) -> np.ndarray:
    """Despeckle what shows: a body pixel whose same-shade neighbors are all hidden (under the
    club or the loincloth) takes the shade of its visible neighbors."""
    out = codes.copy()
    for y in range(SIZE):
        for x in range(SIZE):
            v = codes[y, x]
            if v < 0 or cover[y, x]:
                continue
            near = [codes[y + dy, x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= y + dy < SIZE and 0 <= x + dx < SIZE and not cover[y + dy, x + dx]]
            if v in near:
                continue
            same = [n for n in near if n >= 0]
            if same:
                counts = {n: same.count(n) for n in same}
                out[y, x] = sorted(counts, key=lambda n: (-counts[n], n))[0]
    return out


def parts_cover(d: str, bdx: int, bdy: int, hdx: int, hdy: int) -> np.ndarray:
    """Where the rigid parts (loincloth, topknot, eyes, tusks) sit over the body this frame."""
    rows, x0, y0 = LOIN[d]
    cover = G(rows, x0 + bdx, y0 + bdy) != CLEAR
    rows, x0, y0 = TOPKNOT
    cover |= G(rows, x0 + hdx, y0 + hdy) != CLEAR
    for x, y in EYES[d]:
        cover[y + hdy, x + hdx] = True
    for x, y, _ in TUSKS[d]:
        cover[y + hdy, x + hdx] = True
    return cover


def frame(d: str, spec) -> tuple[np.ndarray, np.ndarray, dict]:
    """(body codes, club codes, anchors) for one frame."""
    bdx, bdy = dirx(d, spec["b"][0]), spec["b"][1]
    hdx, hdy = bdx + dirx(d, spec["h"][0]), bdy + spec["h"][1]
    light = L_E if d == "e" else L_S
    legs_name = LEG_NAMES.get(d, {}).get(spec["legs"], spec["legs"])
    legs = {"s": LEGS_S, "e": LEGS_E, "n": LEGS_N}[d].get(legs_name)
    if legs is None:
        legs = {"s": LEGS_S, "e": LEGS_E, "n": LEGS_N}[d]["stand"]
    torso = {"s": TORSO_S, "e": TORSO_E, "n": TORSO_N}[d]
    roar = spec["head"] == "roar"
    head = {"s": HEAD_ROAR_S if roar else HEAD_S, "e": HEAD_ROAR_E if roar else HEAD_E,
            "n": HEAD_N}[d]
    arms = {"s": ARM_S, "e": ARM_E, "n": ARM_N}[d]
    fars = {"s": FAR_S, "e": FAR_E, "n": FAR_N}[d]
    near_spec, far_spec = arms[spec["near"]], fars[spec["far"]]

    up = grid.translate(torso, bdx, bdy)
    hd = grid.translate(head, hdx, hdy)
    hand, tip, club_layer = None, None, "front"
    behind, front = [], []
    # the far arm
    if far_spec is None:
        if d != "e":
            hang = FAR_HANG_S if d == "s" else FAR_HANG_N
            front.append(grid.translate(hang, 0, bdy))
    else:
        fa, _ = arm_codes(d, far_spec, bdx, bdy, light)
        (behind if d in ("e", "n") else front).append(fa)
    # the near arm
    fist_mask = np.zeros((SIZE, SIZE), bool)
    if near_spec is None:
        hang = NEAR_HANG_S if d == "s" else NEAR_HANG_N
        near_codes = grid.translate(hang, 0, bdy)
        hand = (8 + bdx, 38 + bdy) if d == "s" else (38, 38 + bdy)
    else:
        near_codes, fist_mask = arm_codes(d, near_spec, bdx, bdy, light)
        hand = shifted(near_spec[2], bdx, bdy)
        tip = shifted(near_spec[3], bdx, bdy)
        club_layer = near_spec[4]
    codes = E()
    for layer in behind:
        codes = grid.overlay(codes, layer)
    if d == "n" and near_spec is not None:  # seen from behind, the arms are past the body
        codes = grid.overlay(codes, near_codes)
    codes = grid.overlay(codes, legs, up, hd)
    for layer in front:
        codes = grid.overlay(codes, layer)
    if d != "n" or near_spec is None:
        if near_spec is not None:
            shoulder = shifted(near_spec[0], bdx, bdy)
            codes = contour(codes, near_codes, near_disk(shoulder, 3.6))
        codes = grid.overlay(codes, near_codes)
    codes = despeckle(codes)

    club = E()
    cover = parts_cover(d, bdx, bdy, hdx, hdy)
    if spec["club"] == "dropped":
        a, b, club_layer = DROPPED[d]
        club = club_codes(a, b, light)
        tip = b
        if club_layer == "behind":
            club[dilate((codes != CLEAR) | cover)] = CLEAR
            club = despeckle(club)
    elif tip is not None:
        club = club_codes(hand, tip, light)
        club[fist_mask] = CLEAR  # the fingers wrap the handle
        if club_layer == "behind":
            club[dilate(codes != CLEAR)] = CLEAR
        club = despeckle(club)
    codes = despeckle_visible(codes, (club != CLEAR) | cover)
    cx = {"s": 23, "e": 26, "n": 23}[d]
    anchors = {
        "head": [cx + hdx, 17 + hdy], "chin": [cx + hdx, 27 + hdy], "jaw": [cx + hdx, 26 + hdy],
        "eyes": [{"s": 23, "e": 30, "n": 23}[d] + hdx, 22 + hdy],
        "mouth": [{"s": 23, "e": 32, "n": 23}[d] + hdx, 25 + hdy],
        "torso": [{"s": 23, "e": 22, "n": 23}[d] + bdx, 32 + bdy],
        "hand_near": [int(round(hand[0])), int(round(hand[1]))],
        "foot_near": {"s": [18, 43], "e": [27, 43], "n": [28, 43]}[d],
        "foot_far": {"s": [28, 43], "e": [19, 43], "n": [18, 43]}[d],
        "planted": [],
    }
    if tip is not None:
        anchors["weapon_tip"] = [int(round(tip[0])), int(round(tip[1]))]
    else:
        anchors["weapon_tip"] = list(anchors["hand_near"])
    return codes, club, anchors


# ============================================================================== rigid parts
LOIN = {  # cloth, attached to the torso: two side wraps and a front flap, parted by folds
    "s": (["0111110111110111110", "0011100111110011100", ".000000111110000 00.".replace(" ", ""),
           "......0111110......", ".......00000......."], 14, 36),
    "e": (["0111110111111011110", "0011100111110001110", "0000000000000001110",
           "..............01110", "...............000."], 13, 35),
    "n": (["0111110111110111110", "0011100111110011100", ".000000111110000 00.".replace(" ", ""),
           "......0011100......"], 14, 36),
}
TOPKNOT = ([".....", "..2..", ".121.", ".121.", "..O..", ".111."], 21, 11)
EYES = {"s": [(20, 22), (26, 22)], "e": [(30, 22)], "n": []}
TUSKS = {"s": [(19, 24, 3), (19, 25, 3), (27, 24, 3), (27, 25, 3)], "e": [(32, 24, 3), (32, 25, 3)],
         "n": []}


# ============================================================================== combat
def reach_box(pts: dict) -> list[int]:
    """The slam's hitbox: from the fist to past the club's head, with a margin for the head."""
    (hx, hy), (tx, ty) = pts["hand_near"], pts["weapon_tip"]
    x0, y0 = min(hx, tx) - 3, min(hy, ty) - 3
    return [x0, y0, abs(tx - hx) + 7, abs(ty - hy) + 7]


HITBOX = {d: {"slam": reach_box, "ground": reach_box} for d in DIRS}


def smear_arc(cx: float, cy: float, rx: float, ry: float, a0: float, a1: float) -> np.ndarray:
    """A 2 px band along an elliptical arc (degrees, 0 = facing right, 90 = down): the path of
    the club's head, light outside, mid inside. Drawn only on empty pixels by the compositor."""
    c = E()
    x0, y0, x1, y1 = STYLE.size_classes["medium"].safe_bounds
    for k in range(400):
        a = np.radians(a0 + (a1 - a0) * k / 399)
        for dr, shade in ((0.0, 2), (-1.0, 1)):
            x = int(round(cx + (rx + dr) * np.cos(a)))
            y = int(round(cy + (ry + dr) * np.sin(a)))
            if x0 <= x <= x1 and y0 <= y <= y1 and c[y, x] in (CLEAR, 1):
                c[y, x] = shade
    return c


SMEAR = {
    "e": smear_arc(22, 30, 21, 25, -100, 18),   # over the head, down in front
    "s": smear_arc(16, 26, 13, 20, -95, -205),  # over the near shoulder, down the near side
}
SMEAR["n"] = mirror_x(SMEAR["s"])


# ============================================================================== writing
def rigid_cells(points: dict, shade=None) -> dict:
    cells = {}
    for d in DIRS:
        codes = E()
        for p in points[d]:
            x, y = p[0], p[1]
            codes[y, x] = shade if shade is not None else p[2]
        cells[(d, 0)] = codes
    return {"rigid": cells}


def main() -> None:
    anims = load_anims(STYLE, RIG)
    body, club, smear, anchors = {}, {}, {}, {}
    for anim, frames in FRAMES.items():
        if frames is None:
            continue
        assert len(frames) == anims[anim].frames, (anim, len(frames), anims[anim].frames)
        body[anim], club[anim] = {}, {}
        anchors[anim] = {d: [] for d in DIRS}
        active = anims[anim].flags.get("active", ())
        for i, spec in enumerate(frames):
            for d in DIRS:
                codes, clubc, pts = frame(d, spec)
                if spec["head"] == "roar":  # the jaw drops: tusks and mouth go with it
                    pts["jaw"][1] += 1
                    pts["mouth"][1] += 1
                body[anim][(d, i)], club[anim][(d, i)] = codes, clubc
                if i in active:
                    pts["hitboxes"] = [HITBOX[d][spec["near"]](pts)]
                anchors[anim][d].append(pts)
    smear = {(d, i): E() for d in DIRS for i in range(len(FRAMES["attack_heavy"]))}
    for d in DIRS:
        smear[(d, 3)] = SMEAR[d]
    counts = {a: len(f) for a, f in FRAMES.items() if f is not None}
    write_part("body", RIG, {
        "material": "skin", "kind": "animated", "lags": False, "rigs": [RIG],
        "notes": "The ogre (tools/art/ogre.py): hand-drawn head, torso and legs; arms per pose."},
        body, counts, size=SIZE)
    write_part("held_near", "ogre_club", {
        "material": "leather", "kind": "animated", "lags": False, "rigs": [RIG],
        "notes": "A big club, drawn per frame; smear_attack_heavy.png is the slam's smear."},
        {**club, "smear_attack_heavy": smear}, {**counts, "smear_attack_heavy": counts["attack_heavy"]},
        size=SIZE)
    cloth = {}
    for d in DIRS:
        rows, x0, y0 = LOIN[d]
        cloth[(d, 0)] = G(rows, x0, y0)
    write_part("over_torso", "ogre_loincloth", {
        "material": "cloth", "kind": "rigid", "attach": "torso", "origin": "auto", "lags": False,
        "rigs": [RIG], "notes": "A wrap with a front flap."}, {"rigid": cloth}, size=SIZE)
    rows, x0, y0 = TOPKNOT
    knot = {(d, 0): G(rows, x0, y0) for d in DIRS}
    write_part("hair_front", "topknot", {
        "material": "hair", "kind": "rigid", "attach": "head", "origin": "auto", "lags": False,
        "rigs": [RIG], "allow_singletons": {d: [[23, 15]] for d in DIRS},
        "notes": "A tied tuft on a bald head: the ogre's silhouette mark."}, {"rigid": knot}, size=SIZE)
    write_part("eyes", "ogre", {
        "material": "eyes", "kind": "rigid", "attach": "eyes", "origin": "auto", "lags": False,
        "rigs": [RIG], "notes": "Small eyes deep under the brow."}, rigid_cells(EYES, 0), size=SIZE)
    write_part("tusks", "ogre", {
        "material": "bone", "kind": "rigid", "attach": "jaw", "origin": "auto", "lags": False,
        "rigs": [RIG], "notes": "Two tusks from the underbite."}, rigid_cells(TUSKS), size=SIZE)
    write_anchors(RIG, anchors)
    write_recipe("monsters/ogre.yaml", {
        "name": "ogre", "rig": RIG, "timing_profile": "elite", "seed": 1,
        "parts": {"eyes": "ogre", "tusks": "ogre", "hair_front": "topknot",
                  "over_torso": "ogre_loincloth", "held_near": "ogre_club"},
        "colors": {"skin": "ogre", "cloth": "teal", "hair": "black", "bone": "ivory",
                   "leather": "dark", "eyes": "glow yellow"},
        "anims": ["idle", "walk", "combat_idle", "attack_heavy", "roar", "hurt", "death"],
    })
    print("wrote the ogre")


if __name__ == "__main__":
    main()
