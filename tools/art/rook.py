"""Rook: a fast knight boss on the huge 96 px canvas (MONSTERS.md section 5.10).

The human's reference: a knight in black, battle-worn plate under a tattered red cape, a horned
great helm and a greatsword planted point-down at his side. An original design after that look:
broad layered pauldrons with spikes, a barrel breastplate, tassets and armored legs; a great helm
with a crest swept back like a horn and a visor slit with a red glint; a ragged scarlet cape; a
greatsword nearly his height with a spiked crossguard. He is the fastest thing in the game: 40 to
60 ms strike frames, long dashes, two-hit combos, and every swing leaves a red trail (the
recipe's trail ramp, fx_ramps.blood). About 55 px tall; the huge canvas is room for the raised
greatsword (on the 64 px canvas a blade raised overhead ran off the top).

Construction (like duelist.py): a joint skeleton per frame (hips, knees, feet, neck, shoulders,
elbows, hands, the sword's angle), plate limbs as shaded tubes with knee cops and sabatons, the
torso and cape as polygons, the helm and pauldrons as shaded ovals; painted back to front with
outline-colored contours where pieces overlap (dragon.py's Painter), each layer flattened to what
it shows. Layers: cape (cloth), body (metal: armor, helm, limbs, the crossguard and pommel), grip
(leather: the sword's grip and the belt), blade (metal; the recipe dyes it iron), embers (glow:
cracks in the plate, only the enraged recipe wears them; an overlay that never cuts the body),
eyes (glow, rigid), held_near (no art: the red trails, ranked by shade).

Run after duelist.py: .venv/bin/python tools/art/rook.py
"""

from __future__ import annotations

import math

import numpy as np

import dragon
from artlib import STYLE, crescent, empty, grid, write_anchors, write_part, write_recipe
from pixelforge.anim import load_anims

RIG = "greatknight"
DIRS = ("s", "e", "n")
SIZE = 96  # the huge class: he is about 55 px tall, the rest is room for a raised greatsword
AXIS = 47
GROUND = 91
HIP_Y, NECK_Y = GROUND - 21, GROUND - 39
CLEAR, INK = grid.CLEAR, grid.INK
LAYERS = ("cape", "body", "grip", "blade", "embers")
BLADE = 28  # the blade's length from the crossguard; the grip adds 7, the pommel 2
LO, HI = 3, SIZE - 5  # the mirror-safe columns (x' = 94 - x stays inside)


class Painter(dragon.Painter):
    """dragon.Painter on the 96 px canvas, clipped to the mirror-safe area."""

    def __init__(self):
        self.canvas = empty(SIZE)
        self.on_top = np.full((SIZE, SIZE), "", object)
        self.layers = {k: empty(SIZE) for k in LAYERS}

    def put(self, layer, codes, x0, y0, ring=True):
        mask = np.zeros((SIZE, SIZE), bool)
        vals = np.full((SIZE, SIZE), CLEAR, np.int8)
        for (y, x), v in np.ndenumerate(codes):
            X, Y = x0 + x, y0 + y
            if v != CLEAR and LO <= X <= HI and 3 <= Y <= GROUND:
                mask[Y, X] = True
                vals[Y, X] = v
        rg = np.zeros_like(mask)
        if ring:
            p = np.pad(mask, 1)
            rg = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]) & ~mask & (self.canvas != CLEAR)
            self.layers[layer][rg] = INK
            self.canvas[rg] = INK
        self.layers[layer][mask] = vals[mask]
        self.canvas[mask] = vals[mask]
        self.on_top[mask | rg] = layer
        return mask

    def ink(self, x, y, layer="body"):
        x, y = int(round(x)), int(round(y))
        if LO <= x <= HI and 3 <= y <= GROUND:
            self.layers[layer][y, x] = INK
            self.canvas[y, x] = INK
            self.on_top[y, x] = layer

    def finish(self, before_cleanup=None):
        for k in self.layers:
            self.layers[k][self.on_top != k] = CLEAR
        if before_cleanup:
            before_cleanup(self.layers)
        for k, layer in self.layers.items():
            for _ in range(2):
                for y, x in zip(*np.nonzero(layer >= 0)):
                    v = layer[y, x]
                    near = [layer[y + dy, x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                            if 0 <= y + dy < SIZE and 0 <= x + dx < SIZE]
                    if v in near:
                        continue
                    same = [n for n in near if n >= 0]
                    if same:
                        counts = {n: same.count(n) for n in same}
                        layer[y, x] = sorted(counts, key=lambda n: (-counts[n], n))[0]
            solid = layer >= 0
            p = np.pad(solid, 1)
            alone = solid & ~(p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:])
            layer[alone] = INK


def torn(x, y, top):
    """A few ragged tears across the cape's folds: short dark dashes every 7 rows."""
    return (y - top) % 7 == 6 and (x * 7 + y * 3) % 5 < 3


def R(q):
    return int(round(q[0])), int(round(q[1]))


def tube(a, b, width, shades, far=False):
    """A plate limb from a to b, `width` px across; shades from the lit edge to the dark one."""
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    n = max(abs(dx), abs(dy), 1)
    length = math.hypot(dx, dy) or 1
    nx, ny = -dy / length, dx / length
    if nx > 0 or (nx == 0 and ny < 0):  # the lit edge is the one toward the upper left
        nx, ny = -nx, -ny
    pts = []
    for k in range(int(n) + 1):
        cx, cy = ax + dx * k / n, ay + dy * k / n
        for w in range(width):
            off = w - (width - 1) / 2
            x, y = int(round(cx + nx * off)), int(round(cy + ny * off))
            shade = shades[min(int(w * len(shades) / width), len(shades) - 1)]
            pts.append((x, y, max(0, shade - (1 if far else 0))))
    return pts


def poly(points, shade_at):
    return [(x, y, shade_at(x, y)) for x, y in dragon.fill_poly([tuple(map(float, p)) for p in points])]


def oval_pts(c, w, h, shade_at):
    cx, cy = c
    out = []
    for y in range(int(math.floor(cy - h / 2)), int(math.ceil(cy + h / 2)) + 1):
        for x in range(int(math.floor(cx - w / 2)), int(math.ceil(cx + w / 2)) + 1):
            if ((x - cx) / (w / 2)) ** 2 + ((y - cy) / (h / 2)) ** 2 <= 1.0:
                out.append((x, y, shade_at(x, y)))
    return out


def dim(pts, far):
    return [(x, y, max(0, v - 1)) for x, y, v in pts] if far else pts


# ============================================================================== poses
def P(dx=0, dy=0, crouch=0, lean=0, legs="stand", near=(10, 8), far=(-2, 14), sword=90, hold=0.15,
      cape=0, behind=False, planted=True, sv=None, nv=None, lift=0, view=None, head=(0, 0)):
    """dx, dy: the body's offset (dx along the facing); crouch: hips lower by px; lean: the chest
    forward by px; legs: a stance; near / far: hands relative to the neck (e: x along the facing);
    sword: the blade's direction from the hand in screen degrees (90 straight down, -90 up, 0
    along the facing); hold: where along the grip the hand is (0 at the crossguard); planted: the
    point rests on the ground when the blade points down; cape: sway back in px; behind: the
    sword passes behind the body; sv / nv: the s and n views' own hand and sword (n mirrors s
    unless given); lift: the whole body airborne by px; view: per direction, the view a frame is
    drawn from (a spin); head: the head's offset from the neck (a bowed or thrown-back head)."""
    return {"dx": dx, "dy": dy, "crouch": crouch, "lean": lean, "legs": legs, "near": near,
            "far": far, "sword": sword, "hold": hold, "cape": cape, "behind": behind,
            "planted": planted, "sv": sv, "nv": nv, "lift": lift, "view": view or {}, "head": head}


def SV(near, sword, far=None, reach=1.0, behind=None):
    """An s view pose: the near hand relative to the neck (x toward the viewer's right), the
    sword's screen angle, the far hand, how much of the blade shows (a blade pointing at the
    camera is foreshortened) and whether it passes behind the body."""
    return {"near": near, "sword": sword, "far": far, "reach": reach, "behind": behind}


STANCES = {  # e: (near foot, far foot) x along the facing from the pivot, y lift
    "stand": ((3, 0), (-3, 0)), "wide": ((7, 0), (-6, 0)), "lunge": ((11, 0), (-9, 0)),
    "crouch": ((5, 0), (-6, 0)), "step_a": ((8, 0), (-7, -1)), "step_b": ((2, -3), (0, 0)),
    "step_c": ((-6, -1), (7, 0)), "step_d": ((0, 0), (2, -3)), "dash": ((13, -1), (-12, -2)),
    "dash_b": ((-10, -2), (12, -1)), "tuck": ((4, -4), (-4, -3)), "kneel": ((8, 0), (-6, 0)),
}


def mirrored_view(v):
    if not v:
        return None
    far = v["far"] and (-v["far"][0], v["far"][1])
    return {"near": (-v["near"][0], v["near"][1]), "sword": 180 - v["sword"], "far": far,
            "reach": v["reach"], "behind": v["behind"]}


def joints(d: str, spec) -> dict:
    """Joint positions for a view. e faces +x; s faces the camera with the sword arm on the
    viewer's left; n from behind with the sword arm on the viewer's right."""
    side = {"e": 1, "s": -1, "n": 1}[d]  # the sword arm's x direction (s and n)
    dx = spec["dx"] if d == "e" else 0
    crouch, dy, lean, lift = spec["crouch"], spec["dy"], spec["lean"], spec["lift"]
    hip = (AXIS + dx, HIP_Y + dy + crouch - lift)
    neck = (AXIS + dx + (lean if d == "e" else 0),
            NECK_Y + dy + crouch - lift + (max(0, abs(lean) // 3) if d != "e" else 0))
    hox, hoy = spec["head"]
    head = (neck[0] + (1 if d == "e" else 0) + (hox if d == "e" else 0), neck[1] - 7 + hoy)
    legs = spec["legs"]
    nf, ff = STANCES[legs]
    reach = 1.0
    behind = spec["behind"]
    if d == "e":
        foot_n = (AXIS + dx + nf[0], GROUND + nf[1] - lift)
        foot_f = (AXIS + dx + ff[0], GROUND + ff[1] - lift)
        sh_n, sh_f = (neck[0] + 2, neck[1] + 2), (neck[0] - 2, neck[1] + 2)
        hand_n = (neck[0] + spec["near"][0], neck[1] + spec["near"][1])
        hand_f = (neck[0] + spec["far"][0], neck[1] + spec["far"][1])
        ang = math.radians(spec["sword"])
    else:
        spread = max(0, nf[0] - ff[0] - 6) // 3
        foot_n = (AXIS + side * (4 + spread), GROUND + min(nf[1], 0) - lift)
        foot_f = (AXIS - side * (4 + spread), GROUND + min(ff[1], 0) - lift)
        sh_n, sh_f = (neck[0] + side * 7, neck[1] + 2), (neck[0] - side * 7, neck[1] + 2)
        view = spec["sv"] if d == "s" else (spec["nv"] or mirrored_view(spec["sv"]))
        if view:
            hand_n = (neck[0] + view["near"][0], neck[1] + view["near"][1])
            ang = math.radians(view["sword"])
            far = view["far"] or (-side * 9, 14)
            hand_f = (neck[0] + far[0], neck[1] + far[1])
            reach = view["reach"]
            if view["behind"] is not None:
                behind = view["behind"]
        else:  # the e pose seen from the front or back: the sword arm stays on its side
            hand_n = (sh_n[0] + side * 3, neck[1] + spec["near"][1])
            hand_f = (sh_f[0] - side * 1, sh_f[1] + 13)
            ang = math.radians(90)
            if not spec["planted"] or abs(spec["sword"] - 90) > 1:
                g = spec["sword"]
                ang = math.radians(-90 + (g + 90) * 0.5) if d == "s" else math.radians(-90 - (g + 90) * 0.5)
                if side < 0:
                    ang = math.pi - ang
    tip_dir = (math.cos(ang), math.sin(ang))
    up = 7 * (1 - spec["hold"])  # the grip above the hand
    guard = (hand_n[0] + tip_dir[0] * (7 * spec["hold"] + 1), hand_n[1] + tip_dir[1] * (7 * spec["hold"] + 1))
    pommel = (hand_n[0] - tip_dir[0] * up, hand_n[1] - tip_dir[1] * up)
    tip = (guard[0] + tip_dir[0] * BLADE * reach, guard[1] + tip_dir[1] * BLADE * reach)
    if spec["planted"] and abs(math.degrees(ang) - 90) < 15 and reach == 1.0:  # the point in the ground
        over = tip[1] - GROUND
        guard, pommel, tip = (guard[0], guard[1] - over), (pommel[0], pommel[1] - over), (tip[0], GROUND)

    def knee(h, f, fwd):
        return ((h[0] + f[0]) / 2 + fwd, (h[1] + f[1]) / 2 - 1)

    def elbow(s, h, out):
        return ((s[0] + h[0]) / 2 + out[0], (s[1] + h[1]) / 2 + out[1])

    hip_n = (hip[0] + (1 if d == "e" else side * 3), hip[1])
    hip_f = (hip[0] - (1 if d == "e" else side * 3), hip[1])
    fwd = 2 if d == "e" else 0
    knee_n, knee_f = knee(hip_n, foot_n, fwd), knee(hip_f, foot_f, fwd)
    if legs == "kneel":  # down on the far knee, the near foot planted ahead
        if d == "e":
            knee_n = (hip_n[0] + 6, hip_n[1] + 2)
            knee_f = (hip_f[0] - 1, GROUND - 1)
            foot_f = (hip_f[0] - 8, GROUND)
        else:
            knee_n = (foot_n[0], hip_n[1] + 4)
            knee_f = (foot_f[0], GROUND - 1)
            foot_f = knee_f
    return {"hip": hip, "neck": neck, "head": head, "hip_n": hip_n, "hip_f": hip_f,
            "knee_n": knee_n, "knee_f": knee_f, "foot_n": foot_n, "foot_f": foot_f,
            "sh_n": sh_n, "sh_f": sh_f,
            "elbow_n": elbow(sh_n, hand_n, (0, 2) if d == "e" else (side, 1)),
            "elbow_f": elbow(sh_f, hand_f, (-1, 2) if d == "e" else (-side, 1)),
            "hand_n": hand_n, "hand_f": hand_f, "guard": guard, "pommel": pommel, "tip": tip,
            "tip_dir": tip_dir, "side": side, "behind": behind}


# ============================================================================== drawing
def frame(d: str, spec) -> dict:
    p = Painter()
    j = joints(d, spec)

    def cape():
        nx, ny = R(j["neck"])
        sway = spec["cape"]
        hem = min(ny + 30, GROUND - 4)
        if d == "e":  # hangs from the shoulders down the back and flares behind; a ragged hem
            back = nx - 5
            pts = [(nx + 1, ny + 1), (back - 1, ny + 2), (back - 4 - sway, ny + 12), (back - 8 - sway, hem - 4),
                   (back - 9 - sway, hem + 1), (back - 6 - sway, hem - 1), (back - 5 - sway, hem + 2),
                   (back - 3 - sway, hem - 2), (back - 1 - sway, hem + 3), (back + 1 - sway // 2, hem - 1),
                   (back + 3, hem + 1), (nx, ny + 18)]
            shade = lambda x, y: 0 if ((x + y // 4) % 5 in (0, 1) or torn(x, y, ny)) else 1  # noqa: E731
        else:  # facing s it shows past the shoulders and below the tassets; facing n it covers the back
            w = 10 + (1 if sway > 1 else 0)
            pts = [(nx - w + 1, ny + 1), (nx + w - 1, ny + 1), (nx + w + 1, ny + 12), (nx + w + 2, hem - 2),
                   (nx + w, hem + 2), (nx + 7, hem - 1), (nx + 5, hem + 3), (nx + 2, hem), (nx, hem + 3),
                   (nx - 3, hem - 1), (nx - 5, hem + 2), (nx - 8, hem - 1), (nx - w, hem + 3), (nx - w - 2, hem - 2),
                   (nx - w - 1, ny + 12)]
            shade = lambda x, y: 0 if ((x - nx) % 5 in (1, 2) or torn(x, y, ny)) else 1  # noqa: E731
        p.pts("cape", poly(pts, shade), ring=True)

    def leg(which, far):
        hx, hy = R(j["hip_" + which])
        kx, ky = R(j["knee_" + which])
        fx, fy = R(j["foot_" + which])
        p.pts("body", tube((hx, hy), (kx, ky), 5, (3, 2, 2, 1, 1), far), ring=True)  # the thigh
        if (fx, fy) != (kx, ky):
            p.pts("body", tube((kx, ky), (fx, fy - 2), 4, (2, 2, 1, 1), far), ring=True)  # the greave
        cop = [(kx + ox, ky + oy, 3 if (ox, oy) == (0, 0) else 2) for ox in (-1, 0, 1) for oy in (-1, 0, 1)]
        p.pts("body", dim(cop, far), ring=True)  # the knee cop
        toe = 1 if d == "e" else 0
        boot = [(fx + k, fy, 1) for k in range(-2, 3 + toe)] + [(fx + k, fy - 1, 2) for k in range(-2, 2 + toe)]
        p.pts("body", dim(boot, far), ring=True)  # the sabaton

    def arm(which, far):
        sx, sy = R(j["sh_" + which])
        ex, ey = R(j["elbow_" + which])
        hx, hy = R(j["hand_" + which])
        p.pts("body", tube((sx, sy), (ex, ey), 4, (3, 2, 1, 1), far), ring=True)
        p.pts("body", tube((ex, ey), (hx, hy), 4, (2, 2, 1, 1), far), ring=True)
        fist = [(hx + ox, hy + oy, 2 if oy < 0 else 1) for ox in (-1, 0, 1) for oy in (-1, 0, 1)]
        p.pts("body", dim(fist, far), ring=True)

    def pauldron(which, far):
        sx, sy = R(j["sh_" + which])
        w = 9 if d == "e" else 8
        cy = sy - 1
        bands = lambda x, y: (3 if y - cy < -1 else 2) if (y - cy) % 3 != 2 else 1  # noqa: E731
        p.pts("body", dim(oval_pts((sx, cy), w, 7, bands), far), ring=True)
        # two short spikes along the top edge: the reference's jagged plate
        out = 1 if d == "e" else (j["side"] if which == "n" else -j["side"])
        for k, tall in ((-1, 2), (2, 3)):
            bx = sx + k * out
            p.pts("body", dim([(bx, cy - 3 - t, 2 if t else 1) for t in range(tall)], far), ring=True)

    def torso():
        nx, ny = R(j["neck"])
        hx, hy = R(j["hip"])
        if d == "e":
            pts = [(nx - 5, ny + 1), (nx + 3, ny + 1), (nx + 6, ny + 6), (nx + 5, ny + 11), (hx + 4, hy - 4),
                   (hx + 4, hy), (hx - 4, hy), (hx - 4, hy - 4), (nx - 6, ny + 8)]
            lit = lambda x, y: 3 if (x - nx > 1 and y - ny < 7) else 2 if y - ny < 12 else 1  # noqa: E731
        else:
            pts = [(nx - 8, ny + 1), (nx + 8, ny + 1), (nx + 7, ny + 9), (hx + 5, hy - 4), (hx + 5, hy),
                   (hx - 5, hy), (hx - 5, hy - 4), (nx - 7, ny + 9)]
            if d == "s":
                lit = lambda x, y: 3 if (abs(x - nx) < 3 and 2 < y - ny < 9) else 2 if y - ny < 12 else 1  # noqa: E731
            else:
                lit = lambda x, y: 2 if y - ny < 9 else 1  # noqa: E731
        p.pts("body", poly(pts, lit), ring=True)
        w = 5 if d == "e" else 6  # tassets: a skirt of plates over the hips, split by dark seams
        tass = []
        for x in range(hx - w, hx + w + 1):
            for y in range(hy - 1, hy + 4):
                seam = (x - hx) % 3 == 0 and y > hy
                tass.append((x, y, 0 if seam else (2 if y == hy - 1 else 1)))
        p.pts("body", tass, ring=True)
        p.pts("grip", [(x, hy - 2, 0) for x in range(hx - w + 1, hx + w)], ring=False)  # the belt

    def helm():
        hx, hy = R(j["head"])
        shade = lambda x, y: 3 if (x - hx > 0 and y - hy < -1) else 2 if y - hy < 2 else 1  # noqa: E731
        if d == "n":
            shade = lambda x, y: 2 if y - hy < -1 else 1  # noqa: E731
        p.pts("body", oval_pts((hx, hy), 10, 12, shade), ring=True)
        if d == "e":  # the faceplate juts forward a little
            p.pts("body", [(hx + 5, y, 2) for y in range(hy - 1, hy + 4)] + [(hx + 4, hy + 5, 1)], ring=False)
        p.pts("body", [(x, hy + 6, 1) for x in range(hx - 3, hx + 4)], ring=False)  # the gorget
        if d == "e":  # the crest: swept back over the helm like a horn, 2 px at the root, 1 at the tip
            crest = [(hx + 1, hy - 6), (hx - 1, hy - 8), (hx - 4, hy - 10), (hx - 7, hy - 11)]
        else:
            crest = [(hx, hy - 6), (hx, hy - 9), (hx, hy - 12)]
        p.pts("body", dragon.horn_line(crest, 2), ring=True)
        if d != "n":  # the visor slit; the eyes glow in it
            for x in (range(hx + 1, hx + 6) if d == "e" else range(hx - 3, hx + 4)):
                p.ink(x, hy)
            if d == "s":
                p.ink(hx, hy + 1)
                p.ink(hx, hy + 2)

    def sword():
        g, t, pm, dirv = j["guard"], j["tip"], j["pommel"], j["tip_dir"]
        nx, ny = -dirv[1], dirv[0]  # across the blade
        length = max(int(round(math.hypot(t[0] - g[0], t[1] - g[1]))), 1)
        blade = []
        for k in range(length + 1):
            f = k / length
            cx, cy = g[0] + (t[0] - g[0]) * f, g[1] + (t[1] - g[1]) * f
            width = 3 if f < 0.85 else 2 if f < 0.97 else 1
            for w in range(width):
                off = w - (width - 1) / 2
                shade = 3 if off < 0 else 1 if off == 0 and width == 3 else 2
                blade.append((int(round(cx + nx * off)), int(round(cy + ny * off)), shade))
        p.pts("blade", blade, ring=True)
        cross = []  # the crossguard: across the blade, 11 px, its ends hooked toward the point
        for k in range(-5, 6):
            x, y = g[0] + nx * k, g[1] + ny * k
            cross.append((int(round(x)), int(round(y)), 2))
            cross.append((int(round(x - dirv[0])), int(round(y - dirv[1])), 1))
        for s in (-1, 1):
            hx, hy = g[0] + nx * 5 * s + dirv[0], g[1] + ny * 5 * s + dirv[1]
            cross.append((int(round(hx)), int(round(hy)), 1))
            cross.append((int(round(hx + dirv[0])), int(round(hy + dirv[1])), 1))
        p.pts("body", cross, ring=True)
        line = dragon.line(R(g), R(pm))
        grip = [(x, y, 0 if i % 3 == 2 else 1) for i, (x, y) in enumerate(line)]
        grip += [(x + int(round(nx)), y + int(round(ny)), 1) for x, y in line]
        p.pts("grip", grip, ring=True)
        px, py = R(pm)
        knob = [(px + ox, py + oy, 2 if oy <= 0 else 1) for ox in (-1, 0, 1) for oy in (-1, 0, 1)]
        knob.append((int(round(px - dirv[0] * 2)), int(round(py - dirv[1] * 2)), 2))  # its spike
        p.pts("body", knob, ring=True)

    behind = j["behind"]
    if d == "n":  # from behind: what is in front of him first, the cape over his back last
        if not behind:
            sword()
        arm("f", True)
        arm("n", True)
        leg("f", True)
        leg("n", True)
        torso()
        pauldron("f", True)
        pauldron("n", True)
        helm()
        cape()
        if behind:
            sword()
    else:
        cape()
        if behind:
            sword()
        arm("f", True)
        if d == "e":
            pauldron("f", True)
        leg("f", True)
        torso()
        leg("n", False)
        if d == "s":
            pauldron("f", False)
        helm()
        if not behind:
            sword()
        arm("n", False)
        pauldron("n", False)
    def contact_shade(layers):
        """When only a sliver of cape shows (no row over 6 px across, or under 120 px in all: it
        hangs right behind a crouched or lunging body), its folds would run along it as one flat
        stripe: it takes alternating 3-row bands instead, a ragged edge."""
        if d == "n":
            return
        cape_layer = layers["cape"]
        runs = []
        for y in range(SIZE):
            xs = np.flatnonzero(cape_layer[y] >= 0)
            if xs.size:
                runs += [(y, run) for run in np.split(xs, np.flatnonzero(np.diff(xs) != 1) + 1)]
        if not runs or (max(len(run) for _, run in runs) > 6 and sum(len(r) for _, r in runs) >= 120):
            return  # enough of the cape shows for its folds to read
        for y, run in runs:
            cape_layer[y, run] = np.where(cape_layer[y, run] == INK, INK, 0 if (y // 3) % 2 == 0 else 1)

    p.finish(contact_shade)
    p.layers["embers"] = cracks(p.layers["body"], j, d)
    hx, hy = R(j["head"])
    pts = {"head": [hx, hy - 8], "eyes": [hx, hy], "torso": [R(j["neck"])[0], R(j["neck"])[1] + 8],
           "hand_near": list(R(j["hand_n"])), "hand_far": list(R(j["hand_f"])),
           "weapon_tip": [min(max(R(j["tip"])[0], LO), HI), min(max(R(j["tip"])[1], 3), GROUND)],
           "foot_near": list(R(j["foot_n"])), "foot_far": list(R(j["foot_f"])), "planted": []}
    return {"layers": p.layers, "points": pts, "joints": j}


def cracks(body: np.ndarray, j: dict, d: str) -> np.ndarray:
    """The enraged plate's glowing cracks: a few jagged runs across the breastplate, the
    pauldrons and the thighs, laid only over pixels the body shows (an overlay: without the
    embers part the plate is whole)."""
    out = empty(SIZE)
    nx, ny = R(j["neck"])
    hx, hy = R(j["hip"])
    runs = [[(nx - 2, ny + 3), (nx, ny + 5), (nx - 1, ny + 8), (nx + 1, ny + 10)],
            [(hx + 1, hy - 7), (hx + 3, hy - 5)],
            [R(j["sh_n"]), (R(j["sh_n"])[0] + 2, R(j["sh_n"])[1] - 2)],
            [R(j["knee_n"]), (R(j["knee_n"])[0] - 1, R(j["knee_n"])[1] - 4)]]
    if d == "n":
        runs = runs[2:]
    for run in runs:
        for a, b in zip(run, run[1:]):
            for x, y in dragon.line(a, b):
                if 0 <= x < SIZE and 0 <= y < SIZE and body[y, x] >= 0:
                    out[y, x] = 0
    solid = out >= 0  # a crack cut to one pixel by what covers it is dropped
    pad = np.pad(solid, 1)
    out[solid & ~(pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:])] = CLEAR
    return out


# ============================================================================== frames
HAND = (10, 8)  # the idle hand on the grip of the planted sword
FRAMES = {
    # the reference stance: the sword planted beside him, a hand on the grip; a slow breath
    "idle": [P(), P(dy=1, cape=1), P(dy=1, cape=2), P(cape=1)],
    # a fast prowl: long strides, the greatsword carried low with its point trailing behind
    "walk": [P(legs=lg, dy=bob, near=(7, 15), sword=158, hold=0.25, planted=False, cape=c,
               sv=SV((-11, 12), 100), nv=SV((11, 12), 80, behind=True))
             for lg, bob, c in (("step_a", -1, 2), ("step_b", 0, 3), ("step_b", 1, 3),
                                ("step_c", -1, 2), ("step_d", 0, 3), ("step_d", 1, 3))],
    # two cuts: hoisted over the shoulder (the tell), down across the front, swung back low,
    # a backhand the other way, follow-through, recover
    "attack_slash": [
        P(dx=-1, crouch=2, lean=-2, legs="wide", near=(1, -3), sword=-150, behind=True, planted=False,
          cape=3, sv=SV((-8, -4), -125, behind=True)),
        P(dx=2, crouch=2, lean=3, legs="lunge", near=(12, 10), sword=50, planted=False, cape=0,
          sv=SV((7, 13), 40, reach=0.9)),
        P(dx=2, crouch=3, lean=1, legs="lunge", near=(4, 13), sword=165, planted=False, cape=1,
          sv=SV((-9, 12), 150)),
        P(dx=2, crouch=2, lean=3, legs="lunge", near=(8, 6), sword=-5, planted=False, cape=-1,
          sv=SV((9, 6), -20, reach=0.9)),
        P(dx=2, crouch=1, lean=2, legs="wide", near=(8, 0), sword=-45, planted=False, cape=0,
          sv=SV((8, 0), -60)),
        P(dx=1, legs="wide", near=(9, 8), cape=1),
    ],
    # the dash: sinks low and leans in with the blade drawn back behind (the tell, 0.8 s on the
    # boss profile), flat out with the blade trailing (loop_frames while the game moves him),
    # a passing cut, a skid
    "charge": [
        P(crouch=5, lean=3, legs="crouch", near=(-2, 13), sword=172, behind=True, planted=False, cape=3,
          sv=SV((-10, 10), -115, behind=True), nv=SV((10, 10), -65)),
        P(crouch=7, lean=5, legs="crouch", near=(-4, 14), sword=175, behind=True, planted=False, cape=4,
          sv=SV((-11, 9), -110, behind=True), nv=SV((11, 9), -70)),
        P(crouch=9, lean=13, legs="dash", near=(-8, 12), sword=178, planted=False, cape=7, head=(1, 1),
          sv=SV((-11, 10), -100, behind=True), nv=SV((11, 10), -80)),
        P(crouch=9, lean=13, legs="dash_b", near=(-8, 12), sword=178, planted=False, cape=8, head=(1, 1),
          sv=SV((-11, 10), -100, behind=True), nv=SV((11, 10), -80)),
        P(dx=2, crouch=4, lean=6, legs="lunge", near=(5, 8), sword=10, planted=False, cape=3,
          sv=SV((9, 10), 20, reach=0.9)),
        P(dx=2, crouch=3, lean=2, legs="wide", near=(9, 11), sword=70, planted=False, cape=2,
          sv=SV((6, 12), 70)),
    ],
    # the leap and slam: crouch with the blade raised behind the head, leap, drive it point-first
    # into the ground in front, stuck, wrench it out
    "attack_slam": [
        P(crouch=5, lean=-1, legs="crouch", near=(0, -5), sword=-105, hold=0.3, behind=True, planted=False,
          cape=2, sv=SV((-4, -6), -100, behind=True)),
        P(lift=8, legs="tuck", near=(-1, -7), sword=-135, hold=0.3, behind=True, planted=False, cape=-1,
          sv=SV((-3, -8), -95, behind=True)),
        P(crouch=6, lean=4, legs="wide", near=(11, 12), sword=88, hold=0.1, cape=1,
          sv=SV((-4, 12), 90)),
        P(crouch=7, lean=4, legs="wide", near=(11, 12), sword=88, hold=0.1, cape=2,
          sv=SV((-4, 13), 90)),
        P(crouch=4, lean=3, legs="wide", near=(11, 11), sword=88, hold=0.1, cape=1,
          sv=SV((-4, 12), 90)),
        P(legs="wide", near=HAND, cape=1),
    ],
    # the ring: the blade swung out behind (the tell), one full spin through every view with the
    # blade where the body faces (a red ring around him; a ring of red crescents flies out)
    "attack_ring": [
        P(crouch=3, lean=-2, legs="wide", near=(-6, 8), sword=180, behind=True, planted=False, cape=3,
          sv=SV((-11, 8), 180, behind=True)),
        *[P(crouch=2, legs="wide", near=(6, 9), sword=0, planted=False, cape=4,
            sv=SV((-6, 10), 92, reach=0.45), nv=SV((6, 6), -90, reach=0.45, behind=False),
            view=dict(zip(DIRS, views)))
          for views in (("s", "e", "n"), ("e", "n", "w"), ("n", "w", "s"), ("w", "s", "e"))],
        P(legs="wide", near=HAND, cape=2),
    ],
    # the fan: raised high over the shoulder (the tell), one huge cut forward (a fan of red
    # crescents flies out), follow-through low, recover
    "attack_fan": [
        P(crouch=2, lean=-3, legs="wide", near=(1, -6), sword=-140, behind=True, planted=False, cape=3,
          sv=SV((-8, -6), -120, behind=True)),
        P(dx=2, crouch=3, lean=5, legs="lunge", near=(9, 9), sword=30, planted=False, cape=0,
          sv=SV((8, 12), 35, reach=0.9)),
        P(dx=2, crouch=3, lean=4, legs="lunge", near=(9, 14), sword=75, planted=False, cape=1,
          sv=SV((6, 14), 75)),
        P(dx=1, legs="wide", near=HAND, cape=1),
    ],
    # enrage: plants the sword, throws his head back with both hands on the hilt, then stands
    "enrage": [P(near=HAND, cape=1), P(dy=-1, lean=-3, near=(9, 6), cape=4, head=(-1, -1)), P(cape=2)],
    "hurt": [P(), P(dx=-2, lean=-3, near=(8, 6), sword=100, planted=False, cape=3), P(dx=-1, lean=-1, cape=2)],
    # death: staggers, drops to one knee on the planted sword, head bowed, and stays
    "death": [P(), P(crouch=3, lean=-1, near=(10, 9), cape=2),
              P(crouch=11, lean=3, legs="kneel", near=(11, 2), cape=1, head=(1, 2)),
              P(crouch=11, lean=4, legs="kneel", near=(11, 2), cape=0, head=(1, 3))],
}
FRAMES["combat_idle"] = None  # an alias of idle: the planted sword is his guard

# Active frames and their trails. A cut's trail runs from the blade's tip on an earlier frame to
# its tip now, along a curve through a control point placed per view relative to the torso: over
# the top for a down-cut or the slam, a shallow sweep across the front of the waist for a
# backhand or the dash's passing cut, a slight bow down the weapon side facing the camera. The
# last field lists the views where that cut passes in front of him (its trail is drawn over him).
HIT = {
    "attack_slash": {1: ("arc", 0, {"e": (18, -50), "s": (-11, 1), "n": (11, 1)}, ("s",)),
                     3: ("arc", 2, {"e": (0, 18), "s": (0, 21), "n": (0, 17)}, ("s", "e"))},
    "charge": {2: ("dash",), 3: ("dash",),
               4: ("arc", 3, {"e": (-2, 20), "s": (-17, 9), "n": (17, 9)}, ("s", "e"))},
    "attack_slam": {2: ("arc", 1, {"e": (16, -52), "s": (-12, -27), "n": (12, -27)}, ()), 3: ("none",)},
    "attack_ring": {i: ("ring",) for i in (1, 2, 3, 4)},
    "attack_fan": {1: ("arc", 0, {"e": (14, -50), "s": (-11, 0), "n": (11, 0)}, ("s",))},
}


def bow(a, b, c):
    """4-connected points along the quadratic curve from a to b pulled toward c, tail first."""
    pts: list[tuple[int, int]] = []
    for k in range(241):
        t = k / 240
        x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0]
        y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]
        q = (int(round(x)), int(round(y)))
        if pts and q == pts[-1]:
            continue
        if pts and abs(q[0] - pts[-1][0]) == 1 and abs(q[1] - pts[-1][1]) == 1:
            pts.append((q[0], pts[-1][1]))
        pts.append(q)
    return pts


def mirror_codes(codes: np.ndarray) -> np.ndarray:
    out = np.full(codes.shape, CLEAR, np.int8)
    out[:, :2 * AXIS + 1] = codes[:, 2 * AXIS::-1]
    return out


def mirror_points(pts: dict) -> dict:
    out = {}
    for k, v in pts.items():
        if isinstance(v, list) and len(v) == 2 and all(isinstance(c, int) for c in v):
            out[k] = [2 * AXIS - v[0], v[1]]
        else:
            out[k] = v
    return out


def render(anim: str, d: str, i: int, spec) -> dict:
    """A frame for direction d, drawn from its view (a spin frame turns the body)."""
    view = spec["view"].get(d, d)
    if view == "w":
        f = frame("e", spec)
        f = {"layers": {k: mirror_codes(v) for k, v in f["layers"].items()},
             "points": mirror_points(f["points"]), "joints": f["joints"]}
    else:
        f = frame(view, spec)
    if view != d:
        f["points"]["view"] = view
    f["view"] = view
    return f


def comet(center, rx, ry, newest, span=270):
    """A spin's ring trail ranked by age (2 the newest quarter), as in weapons.ring_trail."""
    from weapons import ring_trail
    return ring_trail(center, rx, ry, newest, span)


TIP_ANGLE = {"s": 90, "e": 0, "n": -90, "w": -180}


def trail_points(anim: str, d: str, i: int, frames: dict) -> tuple[list, list]:
    """(behind, front) trail points (x, y, rank) for an active frame."""
    kind = HIT[anim][i][0]
    f = frames[(d, i)]
    pts = f["points"]
    if kind == "arc":
        _, src, controls, front = HIT[anim][i]
        a = tuple(frames[(d, src)]["points"]["weapon_tip"])
        b = tuple(pts["weapon_tip"])
        tx, ty = pts["torso"]
        ox, oy = controls[d]
        # a big arc over the top thickens to 4 px at the blade; a flat sweep across the front to 3
        trail = crescent(bow(a, b, (tx + ox, ty + oy)), 4 if oy < 0 else 3)
        return ([], trail) if d in front else (trail, [])
    if kind == "dash":  # speed streaks off his back, brightest at the body
        j = f["joints"]
        out = []
        if d == "e":
            back = int(min(j["hip"][0], j["neck"][0])) - 8
            for y, length in ((R(j["head"])[1], 14), (R(j["neck"])[1] + 5, 20), (R(j["hip"])[1] - 2, 16),
                              (R(j["knee_f"])[1], 10)):
                for k in range(length):
                    out.append((back - k, y, 2 if k < length // 3 else 1 if k < 2 * length // 3 else 0))
        elif d == "s":  # toward the camera the streaks rise behind his shoulders
            for x, length in ((AXIS - 13, 12), (AXIS + 13, 12), (AXIS - 5, 8), (AXIS + 5, 8)):
                for k in range(length):
                    out.append((x, NECK_Y - 2 - k, 2 if k < length // 3 else 1 if k < 2 * length // 3 else 0))
        else:  # away from the camera they trail down beside him: below his feet is only ground
            solid = np.zeros((SIZE, SIZE), bool)
            for codes in f["layers"].values():
                solid |= codes >= 0
            ys, xs = np.nonzero(solid)
            left, right, top = int(xs.min()), int(xs.max()), int(ys.min())
            for x, y0, length in ((left - 3, top + 14, 16), (right + 3, top + 12, 16),
                                  (left - 7, top + 22, 10), (right + 7, top + 20, 10)):
                for k in range(length):
                    out.append((x, y0 + k, 2 if k < length // 3 else 1 if k < 2 * length // 3 else 0))
        return out, []
    if kind == "ring":
        newest = TIP_ANGLE[f["view"]]
        # unwrap so the comet always runs the spin's way (counter-clockwise from above)
        ring = comet((AXIS, HIP_Y - 1), 30, 9, newest)
        return ([q for q in ring if q[1] <= HIP_Y - 1], [q for q in ring if q[1] > HIP_Y - 1])
    return [], []


def main() -> None:
    anims = load_anims(STYLE, RIG)
    layers = {k: {} for k in LAYERS}
    anchors, trails = {}, {}
    for anim, frames in FRAMES.items():
        if frames is None:
            continue
        assert len(frames) == anims[anim].frames, (anim, len(frames), anims[anim].frames)
        for k in LAYERS:
            layers[k][anim] = {}
        anchors[anim] = {d: [] for d in DIRS}
        built = {}
        for i, spec in enumerate(frames):
            for d in DIRS:
                built[(d, i)] = render(anim, d, i, spec)
        behind = {(d, i): empty(SIZE) for d in DIRS for i in range(len(frames))}
        front = {(d, i): empty(SIZE) for d in DIRS for i in range(len(frames))}
        for (d, i), f in built.items():
            for k in LAYERS:
                layers[k][anim][(d, i)] = f["layers"][k]
            pts = f["points"]
            if i in HIT.get(anim, {}):
                back, fr = trail_points(anim, d, i, built)
                for target, tpts in ((behind, back), (front, fr)):
                    for x, y, rank in tpts:
                        if LO <= x <= HI and 3 <= y <= GROUND and target[(d, i)][y, x] == CLEAR:
                            target[(d, i)][y, x] = rank + 1  # metal shades 1..3, ranked by shade
                xs = [pts["weapon_tip"][0], pts["hand_near"][0]]
                ys = [pts["weapon_tip"][1], pts["hand_near"][1]]
                for x, y, _ in back + fr:
                    xs.append(x), ys.append(y)
                if HIT[anim][i][0] == "dash":  # the dash hits with his whole body
                    body = f["layers"]["body"] >= 0
                    by, bx = np.nonzero(body)
                    xs += [int(bx.min()), int(bx.max())]
                    ys += [int(by.min()), int(by.max())]
                x0, y0 = max(min(xs) - 2, 0), max(min(ys) - 2, 0)
                x1, y1 = min(max(xs) + 2, SIZE - 1), min(max(ys) + 2, GROUND + 1)
                pts["hitboxes"] = [[x0, y0, x1 - x0 + 1, y1 - y0 + 1]]
            anchors[anim][d].append(pts)
        if any((c != CLEAR).any() for c in behind.values()):
            trails[f"smear_{anim}"] = behind
        if any((c != CLEAR).any() for c in front.values()):
            trails[f"smear_{anim}_front"] = front
    counts = {a: len(f) for a, f in FRAMES.items() if f is not None}
    notes = {"cape": ("cloth", "A tattered cape from the shoulders to the knees, its hem ragged."),
             "body": ("metal", "Black plate: helm with a swept crest, spiked pauldrons, breastplate, tassets, "
                               "armored limbs, the sword's crossguard and pommel; posed per frame."),
             "grip": ("leather", "The greatsword's wrapped grip and the belt."),
             "blade": ("metal", "The greatsword's blade."),
             "embers": ("eyes", "Glowing cracks in the plate: the enraged Rook only.")}
    for slot, (material, text) in notes.items():
        write_part(slot, "rook", {"material": material, "kind": "animated", "lags": False,
                                  "rigs": [RIG], "notes": text}, layers[slot], counts, size=SIZE, prune=True)
    empty_cells = {anim: {(d, i): empty(SIZE) for d in DIRS for i in range(n)} for anim, n in counts.items()}
    trail_counts = {k: counts[k[6:].removesuffix("_front")] for k in trails}
    write_part("held_near", "rook_greatsword", {
        "material": "metal", "kind": "animated", "lags": False, "rigs": [RIG],
        "notes": "No art: the greatsword's red trails (smear_<anim>), ranked by shade."},
        {**empty_cells, **trails}, {**counts, **trail_counts}, size=SIZE, prune=True)
    eyes = {}
    f0 = {d: frame(d, P()) for d in DIRS}
    singles = {}
    for d in DIRS:
        e = empty(SIZE)
        if d != "n":
            ex, ey = f0[d]["points"]["eyes"]
            spots = ((-2, 0), (2, 0)) if d == "s" else ((3, 0), (4, 0))
            for ox, oy in spots:
                e[ey + oy, ex + ox] = 0
            if d == "s":
                singles["s"] = [[ex - 2, ey], [ex + 2, ey]]
        eyes[(d, 0)] = e
    write_part("eyes", "rook", {"material": "eyes", "kind": "rigid", "attach": "eyes", "origin": "auto",
                                "lags": False, "rigs": [RIG], "allow_singletons": singles,
                                "notes": "A red glint in the visor slit."}, {"rigid": eyes}, size=SIZE, prune=True)
    write_anchors(RIG, anchors)
    base = {"rig": RIG, "timing_profile": "boss", "seed": 1, "family": "rook", "trail": "blood",
            "anims": ["idle", "combat_idle", "walk", "attack_slash", "charge", "attack_slam",
                      "attack_ring", "attack_fan", "enrage", "hurt", "death"]}
    parts = {"cape": "rook", "body": "rook", "grip": "rook", "blade": "rook", "eyes": "rook",
             "held_near": "rook_greatsword"}
    colors = {"metal": "obsidian", "cloth": "scarlet", "leather": "black", "eyes": "glow red"}
    write_recipe("monsters/rook.yaml", {"name": "rook", **base, "parts": parts, "colors": colors,
                                        "slot_colors": {"blade": "iron"}})
    write_recipe("monsters/rook_enraged.yaml", {"name": "rook_enraged", **base,
                                                "parts": {**parts, "embers": "rook"}, "colors": colors,
                                                "slot_colors": {"blade": "iron"}})
    print("wrote rook")


if __name__ == "__main__":
    main()
