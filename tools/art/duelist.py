"""The Ashen Duelist: a tall, quick humanoid elite on the medium 48 px canvas (MONSTERS.md
section 5.9).

The human asked for "monsters that are humanoid and tall ... that's quick". An original design:
a lean warrior twice a hero's height in dark plate, a crested helm with a pale plume and glowing
eyes behind the visor, a long tattered cape, and a glaive as tall as itself. It is fast: short
strike frames, a dash lunge that covers ground (root motion), a wide sweeping slash with a white
arc and a backstep, with tells that still meet the elite profile's minimum.

Construction: a joint skeleton per frame (hips, knees, feet, neck, shoulders, elbows, hands, the
glaive's angle), limbs as shaded tubes, the torso and cape as filled polygons, the helm as a
shaded oval; painted back to front with outline-colored contours where pieces overlap (the
Painter from dragon.py at this canvas size), each layer flattened to what it shows. Layers: cape
and plume (cloth), body (metal: armor, helm, limbs), shaft (leather), blade (metal; a slot color
can make it silver), eyes (glow, rigid), held_near (no art: the swing trails).

Run: .venv/bin/python tools/art/duelist.py
"""

from __future__ import annotations

import math

import numpy as np

import dragon
from artlib import STYLE, arc_path, crescent, empty, grid, write_anchors, write_part, write_recipe
from pixelforge.anim import load_anims

RIG = "humanoid_tall"
DIRS = ("s", "e", "n")
SIZE = 48
AXIS = 23
GROUND = 43
CLEAR, INK = grid.CLEAR, grid.INK
LAYERS = ("cape", "body", "plume", "shaft", "blade")


class Painter(dragon.Painter):
    """dragon.Painter on the 48 px canvas."""

    def __init__(self):
        self.canvas = empty(SIZE)
        self.on_top = np.full((SIZE, SIZE), "", object)
        self.layers = {k: empty(SIZE) for k in LAYERS}

    def put(self, layer, codes, x0, y0, ring=True):
        mask = np.zeros((SIZE, SIZE), bool)
        vals = np.full((SIZE, SIZE), CLEAR, np.int8)
        for (y, x), v in np.ndenumerate(codes):
            X, Y = x0 + x, y0 + y
            if v != CLEAR and 3 <= X <= SIZE - 5 and 3 <= Y <= GROUND:
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

    def finish(self):
        for k in self.layers:
            self.layers[k][self.on_top != k] = CLEAR
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


def tube(a, b, width, lit, dim, far=False):
    """A limb from a to b, `width` px across: the lit edge (left or top) a shade lighter."""
    pts = []
    line = dragon.line(a, b)
    dx, dy = b[0] - a[0], b[1] - a[1]
    horizontal = abs(dx) > abs(dy)
    for x, y in line:
        for k in range(width):
            if horizontal:
                X, Y = x, y + k - width // 2
                shade = lit if k == 0 else dim
            else:
                X, Y = x + k - width // 2, y
                shade = lit if k == 0 else dim
            pts.append((X, Y, max(0, shade - (1 if far else 0))))
    return pts


def poly(points, shade_at):
    return [(x, y, shade_at(x, y)) for x, y in dragon.fill_poly([tuple(map(float, p)) for p in points])]


# ============================================================================== poses
def P(dx=0, dy=0, crouch=0, lean=0, legs="stand", near=(5, 9), far=(-3, 10), glaive=-90, grip=0.35,
      cape=0, behind=False, fall=0.0, flags=(), sv=None, nv=None):
    """dx, dy: the body's offset (dx along the facing); crouch: hips lower by px; lean: the chest
    forward by px; legs: a stance; near / far: hands relative to the neck (e: x along the facing;
    s and n: x toward the weapon side's outside); glaive: the blade's direction from the grip in
    degrees (screen: -90 up, 0 along the facing, 90 down); grip: where the near hand holds the
    shaft (0 the butt, 1 the blade); cape: sway (px back); behind: the glaive passes behind."""
    return {"dx": dx, "dy": dy, "crouch": crouch, "lean": lean, "legs": legs, "near": near,
            "far": far, "glaive": glaive, "grip": grip, "cape": cape, "behind": behind, "fall": fall,
            "flags": flags, "sv": sv, "nv": nv}


def SV(near, glaive, grip=None):
    """A pose of the near hand (relative to the neck, x toward the viewer's right) and the glaive
    (degrees on screen) for the s view; n mirrors it unless it has its own."""
    return {"near": near, "glaive": glaive, "grip": grip}


STANCES = {  # e: (near foot, far foot) x along the facing from the pivot, y lift
    "stand": ((2, 0), (-3, 0)), "step_a": ((5, 0), (-5, -2)), "step_b": ((1, -2), (0, 0)),
    "step_c": ((-4, -2), (4, 0)), "step_d": ((0, 0), (1, -2)), "wide": ((5, 0), (-5, 0)),
    "lunge": ((8, 0), (-7, 0)), "crouch": ((3, 0), (-4, 0)), "back": ((-1, 0), (-7, -1)),
}
SHAFT = 30  # the glaive's length; the blade adds 7

FRAMES = {
    "idle": [P(), P(dy=1, cape=1), P(dy=1, cape=1), P(cape=0)],
    "walk": [P(legs="step_a", dy=-1, cape=1), P(legs="step_b", cape=2), P(legs="step_b", dy=1, cape=2),
             P(legs="step_c", dy=-1, cape=1), P(legs="step_d", cape=2), P(legs="step_d", dy=1, cape=2)],
    # a wide sweep: the glaive drawn back high behind (the tell), swept across in front, followed
    # through low, recovered
    "attack_slash": [P(dx=-1, crouch=1, lean=-1, legs="wide", near=(-2, 2), glaive=-150, grip=0.5,
                       behind=True, cape=2, sv=SV((-7, -3), -115, 0.55)),
                     P(dx=-2, crouch=2, lean=-2, legs="wide", near=(-3, 1), glaive=-160, grip=0.5,
                       behind=True, cape=3, sv=SV((-8, -4), -125, 0.55)),
                     P(dx=2, crouch=1, lean=2, legs="lunge", near=(9, 6), glaive=10, grip=0.4, cape=0,
                       sv=SV((4, 8), 12, 0.5)),
                     P(dx=3, crouch=2, lean=2, legs="lunge", near=(8, 9), glaive=50, grip=0.4, cape=-1,
                       sv=SV((6, 10), 55, 0.5)),
                     P(dx=1, legs="wide", cape=1)],
    # a dash: coil low with the point forward (the tell), drive the point out at full stretch while
    # the body travels (root motion), hold, draw back
    "attack_lunge": [P(dx=-3, crouch=3, lean=-1, legs="crouch", near=(1, 8), glaive=5, grip=0.75, cape=2,
                       sv=SV((-2, 8), 80, 0.75), nv=SV((2, 4), -80, 0.75)),
                     P(dx=-4, crouch=4, lean=-1, legs="crouch", near=(0, 8), glaive=5, grip=0.75, cape=3,
                       sv=SV((-2, 7), 82, 0.75), nv=SV((2, 3), -82, 0.75)),
                     P(dx=-2, crouch=2, lean=3, legs="lunge", near=(7, 6), glaive=0, grip=0.8, cape=-2,
                       sv=SV((0, 12), 90, 0.8), nv=SV((0, 0), -90, 0.8)),
                     P(dx=-2, crouch=2, lean=3, legs="lunge", near=(8, 6), glaive=0, grip=0.8, cape=-1,
                       sv=SV((0, 13), 90, 0.8), nv=SV((0, -1), -90, 0.8)),
                     P(dx=-1, crouch=1, legs="wide", cape=1)],
    "dodge": [P(crouch=2, legs="crouch", cape=1), P(dx=-2, dy=-2, legs="back", cape=-2, flags=("airborne",)),
              P(dx=-1, crouch=1, legs="wide", cape=1)],
    "hurt": [P(), P(dx=-2, lean=-2, near=(3, 8), glaive=-100, cape=2), P(dx=-1, lean=-1, cape=1)],
    "death": [P(), P(dx=-1, crouch=3, lean=-2, legs="crouch", glaive=-60, cape=2),
              P(crouch=8, lean=-1, legs="crouch", near=(4, 12), glaive=-20, cape=2, fall=0.5),
              P(crouch=12, legs="crouch", near=(6, 14), glaive=0, cape=1, fall=1.0, flags=("lying",))],
}
FRAMES["combat_idle"] = None  # an alias of idle


def joints(d: str, spec) -> dict:
    """Joint positions for a view. e faces +x; s faces the camera, the weapon side on the viewer's
    left; n from behind, the weapon side on the viewer's right."""
    side = {"e": 1, "s": -1, "n": 1}[d]  # the weapon side's x direction (s and n)
    dx = spec["dx"] if d == "e" else 0
    crouch, dy, lean = spec["crouch"], spec["dy"], spec["lean"]
    hip = (AXIS + dx, 30 + dy + crouch)
    neck = (AXIS + dx + (lean if d == "e" else 0), 18 + dy + crouch + (max(0, -lean) if d != "e" else 0))
    head = (neck[0] + (1 if d == "e" else 0), neck[1] - 6)
    nf, ff = STANCES[spec["legs"]]
    if d == "e":
        foot_n = (AXIS + nf[0], GROUND + nf[1])
        foot_f = (AXIS + ff[0], GROUND + ff[1])
        sh_n, sh_f = (neck[0] + 1, neck[1] + 1), (neck[0] - 1, neck[1] + 1)
        hand_n = (neck[0] + spec["near"][0], neck[1] + spec["near"][1])
        hand_f = (neck[0] + spec["far"][0], neck[1] + spec["far"][1])
        ang = math.radians(spec["glaive"])
    else:
        spread = max(0, nf[0] - ff[0] - 5) // 2  # a wide or lunging stance plants the feet apart
        foot_n = (AXIS + side * (3 + spread), GROUND + min(nf[1], 0))
        foot_f = (AXIS - side * (3 + spread), GROUND + min(ff[1], 0))
        sh_n, sh_f = (neck[0] + side * 5, neck[1] + 1), (neck[0] - side * 5, neck[1] + 1)
        nx, ny = spec["near"]
        # s and n: a hand reaching along the facing comes toward the camera (down, s) or away (up, n)
        reach = nx - 5
        hand_n = (sh_n[0] + side * 2 - side * max(0, reach) // 2,
                  sh_n[1] + ny - 1 + (max(0, reach) // 2 if d == "s" else -max(0, reach) // 2))
        hand_f = (sh_f[0] - side * 2, sh_f[1] + 9)
        g = spec["glaive"]
        # the glaive's angle in s and n: up stays up; along the facing turns toward the camera
        ang = math.radians(-90 + (g + 90) * 0.55) if d == "s" else math.radians(-90 - (g + 90) * 0.55)
        if side < 0:  # mirror for the weapon on the viewer's left
            ang = math.pi - ang
        view = spec["sv"] if d == "s" else (spec["nv"] or (spec["sv"] and {
            "near": (-spec["sv"]["near"][0], spec["sv"]["near"][1]),
            "glaive": 180 - spec["sv"]["glaive"], "grip": spec["sv"]["grip"]}))
        if view:  # an explicit s pose (n mirrors it): a sweep across the front, a thrust at the camera
            hand_n = (neck[0] + view["near"][0], neck[1] + view["near"][1])
            ang = math.radians(view["glaive"])
            if view["grip"] is not None:
                spec = {**spec, "grip": view["grip"]}
    tip_dir = (math.cos(ang), math.sin(ang))
    grip = hand_n
    up = SHAFT * (1 - spec["grip"])
    down = SHAFT * spec["grip"]
    blade_root = (grip[0] + tip_dir[0] * up, grip[1] + tip_dir[1] * up)
    butt = (grip[0] - tip_dir[0] * down, grip[1] - tip_dir[1] * down)
    blade_tip = (blade_root[0] + tip_dir[0] * 7, blade_root[1] + tip_dir[1] * 7)

    def knee(h, f, fwd):
        return ((h[0] + f[0]) / 2 + fwd, (h[1] + f[1]) / 2 - 1)

    def elbow(s, h, out):
        return ((s[0] + h[0]) / 2 + out[0], (s[1] + h[1]) / 2 + out[1])

    hip_n = (hip[0] + (1 if d == "e" else side * 2), hip[1])
    hip_f = (hip[0] - (1 if d == "e" else side * 2), hip[1])
    fwd = 1 if d == "e" else 0
    return {"hip": hip, "neck": neck, "head": head, "hip_n": hip_n, "hip_f": hip_f,
            "knee_n": knee(hip_n, foot_n, fwd), "knee_f": knee(hip_f, foot_f, fwd),
            "foot_n": foot_n, "foot_f": foot_f, "sh_n": sh_n, "sh_f": sh_f,
            "elbow_n": elbow(sh_n, hand_n, (0, 1) if d == "e" else (side, 0)),
            "elbow_f": elbow(sh_f, hand_f, (-1, 1) if d == "e" else (-side, 0)),
            "hand_n": hand_n, "hand_f": hand_f, "butt": butt, "blade_root": blade_root,
            "blade_tip": blade_tip, "tip_dir": tip_dir, "side": side}


def frame(d: str, spec) -> dict:
    p = Painter()
    j = joints(d, spec)
    fall = spec["fall"]

    def r(q):
        return (int(round(q[0])), int(round(q[1] + fall * 0)))

    def cape():
        nx, ny = r(j["neck"])
        sway = spec["cape"]
        if d == "e":  # trailing behind the back
            pts = [(nx - 1, ny), (nx - 4 - sway, ny + 4), (nx - 8 - sway, ny + 16), (nx - 9 - sway, ny + 23),
                   (nx - 6 - sway, ny + 22), (nx - 4 - sway, ny + 24), (nx - 2 - sway, ny + 22),
                   (nx, ny + 23), (nx + 1, ny + 12)]
        else:  # behind the body facing s, over the back facing n: wider than the shoulders; its
            # hem stays above the boots however low the body crouches
            w = 7
            hem = min(ny + 24, GROUND - 5) - ny
            pts = [(nx - w, ny + 1), (nx + w, ny + 1), (nx + w + 2 + (sway > 1), ny + hem - 3),
                   (nx + w, ny + hem), (nx + 4, ny + hem - 2), (nx + 1, ny + hem + 1), (nx - 2, ny + hem - 2),
                   (nx - 5, ny + hem), (nx - w - 2, ny + hem - 3)]
        shade = lambda x, y: 0 if (x - nx) % 4 == 0 else 1  # noqa: E731  (vertical folds)
        p.pts("cape", poly(pts, lambda x, y: 0 if d == "s" else shade(x, y)), ring=True)

    def leg(which, far):
        p.pts("body", tube(r(j["hip_" + which]), r(j["knee_" + which]), 3, 2, 1, far), ring=True)
        p.pts("body", tube(r(j["knee_" + which]), r(j["foot_" + which]), 3, 2, 1, far), ring=False)
        fx, fy = r(j["foot_" + which])
        boot = [(fx + k, fy, 1 if not far else 0) for k in ((-1, 0, 1, 2) if d == "e" else (-1, 0, 1))]
        boot += [(fx + k, fy - 1, 2 if not far else 1) for k in ((-1, 0, 1, 2) if d == "e" else (-1, 0, 1))]
        p.pts("body", boot, ring=False)

    def arm(which, far):
        p.pts("body", tube(r(j["sh_" + which]), r(j["elbow_" + which]), 2, 3, 2, far), ring=True)
        p.pts("body", tube(r(j["elbow_" + which]), r(j["hand_" + which]), 2, 3, 2, far), ring=False)
        hx, hy = r(j["hand_" + which])
        p.pts("body", [(hx, hy, 1), (hx + 1, hy, 1), (hx, hy + 1, 1), (hx + 1, hy + 1, 1)], ring=False)

    def torso():
        nx, ny = r(j["neck"])
        hx, hy = r(j["hip"])
        if d == "e":
            pts = [(nx - 3, ny), (nx + 3, ny), (nx + 4, ny + 4), (hx + 2, hy), (hx - 3, hy), (nx - 4, ny + 5)]
        else:
            pts = [(nx - 5, ny), (nx + 5, ny), (nx + 4, ny + 6), (hx + 3, hy), (hx - 3, hy), (nx - 4, ny + 6)]
        lit = lambda x, y: 3 if x - nx < -1 and y - ny < 6 else 2 if y - ny < 8 else 1  # noqa: E731
        if d == "n":
            lit = lambda x, y: 2 if y - ny < 6 else 1  # noqa: E731
        p.pts("body", poly(pts, lit), ring=True)
        belt = [(x, hy - 1, 0) for x in range(hx - 3, hx + 3)] + [(x, hy - 2, 0) for x in range(hx - 3, hx + 3)]
        p.pts("shaft", belt, ring=False)  # a leather belt

    def helm():
        hx, hy = r(j["head"])
        p.oval("body", (hx, hy), 9, 9)
        if d != "n":  # the visor slit; the eyes glow in it
            for x in ((hx - 3, hx - 2, hx - 1, hx + 1, hx + 2, hx + 3) if d == "s" else (hx + 1, hx + 2, hx + 3, hx + 4)):
                if 3 <= x <= SIZE - 5:
                    p.layers["body"][hy, x] = INK
                    p.canvas[hy, x] = INK
                    p.on_top[hy, x] = "body"
        # the crest: a pale plume sweeping back from the top
        if d == "e":
            plume = [(hx + k, hy - 5 - (1 if k > -3 else 0), 1) for k in range(1, -7, -1)]
            plume += [(hx + k, hy - 4, 0) for k in range(-1, -7, -1)]
            plume += [(hx - 7, hy - 3, 0), (hx - 8, hy - 2, 0), (hx - 7, hy - 2, 0)]
        else:
            plume = [(hx + k, hy - 6, 1) for k in (-1, 0, 1)] + [(hx + k, hy - 5, 0) for k in (-1, 0, 1)]
            plume += [(hx + k, hy - 7, 1) for k in (-1, 0)]
        p.pts("plume", plume, ring=True)

    def glaive():
        root, tip, butt, dirv = j["blade_root"], j["blade_tip"], j["butt"], j["tip_dir"]
        shaft = dragon.line(r(butt), r(root))  # dark grip wraps every 7 px break the long run
        p.pts("shaft", [(x, y, 0 if i % 7 in (5, 6) else 1) for i, (x, y) in enumerate(shaft)], ring=False)
        # the blade: a curved edge 2 px wide, the back edge darker
        nx, ny = -dirv[1], dirv[0]  # normal
        pts = []
        for k in range(8):
            t = k / 7
            cx = root[0] + (tip[0] - root[0]) * t + nx * (1.5 * math.sin(t * math.pi))
            cy = root[1] + (tip[1] - root[1]) * t + ny * (1.5 * math.sin(t * math.pi))
            pts.append((int(round(cx)), int(round(cy)), 3))
            pts.append((int(round(cx - nx)), int(round(cy - ny)), 2))
        p.pts("blade", pts, ring=True)

    behind = spec["behind"]
    if d == "n":  # from behind: the weapon (in front of the body) first, the cape over the back last
        glaive()
        arm("f", True)
        arm("n", True)
        leg("f", True)
        leg("n", True)
        torso()
        helm()
        cape()
    else:
        cape()
        if behind:
            glaive()
        arm("f", True)
        leg("f", True)
        torso()
        leg("n", False)
        helm()
        if not behind:
            glaive()
        arm("n", False)
    p.finish()
    pts = {"head": [int(round(j["head"][0])), int(round(j["head"][1])) - 4],
           "eyes": [int(round(j["head"][0])), int(round(j["head"][1]))],
           "torso": [int(round(j["neck"][0])), int(round(j["neck"][1])) + 6],
           "hand_near": list(r(j["hand_n"])), "hand_far": list(r(j["hand_f"])),
           "weapon_tip": [min(max(int(round(j["blade_tip"][0])), 3), SIZE - 5),
                          min(max(int(round(j["blade_tip"][1])), 3), GROUND)],
           "foot_near": list(r(j["foot_n"])), "foot_far": list(r(j["foot_f"])), "planted": []}
    return {"layers": p.layers, "points": pts}


HIT = {"attack_slash": (2,), "attack_lunge": (2, 3)}


def sweep(a, b, c, through=None):
    """The arc a blade's tip draws from a to b around c; `through` (degrees) picks the way round
    that passes that direction (90: in front, below, facing s; -90: above, facing n)."""
    a0 = math.atan2(a[1] - c[1], a[0] - c[0])
    a1 = math.atan2(b[1] - c[1], b[0] - c[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    if through is not None:
        t = math.radians(through)
        on_path = lambda delta: (((t - a0) % (2 * math.pi)) <= (delta % (2 * math.pi))) if delta > 0 \
            else (((a0 - t) % (2 * math.pi)) <= ((-delta) % (2 * math.pi)))  # noqa: E731
        if not on_path(da):
            da = da - 2 * math.pi if da > 0 else da + 2 * math.pi
    r0, r1 = math.hypot(a[0] - c[0], a[1] - c[1]), math.hypot(b[0] - c[0], b[1] - c[1])
    pts: list[tuple[int, int]] = []
    for k in range(160):
        f = k / 159
        r, ang = r0 + (r1 - r0) * f, a0 + da * f
        q = (int(round(c[0] + r * math.cos(ang))), int(round(c[1] + r * 0.8 * math.sin(ang))))
        if pts and q == pts[-1]:
            continue
        if pts and abs(q[0] - pts[-1][0]) == 1 and abs(q[1] - pts[-1][1]) == 1:
            pts.append((q[0], pts[-1][1]))
        pts.append(q)
    return pts


def main() -> None:
    anims = load_anims(STYLE, RIG)
    layers = {k: {} for k in LAYERS}
    anchors = {}
    fists = {}
    for anim, frames in FRAMES.items():
        if frames is None:
            continue
        assert len(frames) == anims[anim].frames, (anim, len(frames), anims[anim].frames)
        for k in LAYERS:
            layers[k][anim] = {}
        anchors[anim] = {d: [] for d in DIRS}
        fists[anim] = {(d, i): empty(SIZE) for d in DIRS for i in range(len(frames))}
        for i, spec in enumerate(frames):
            for d in DIRS:
                f = frame(d, spec)
                for k in LAYERS:
                    layers[k][anim][(d, i)] = f["layers"][k]
                pts = f["points"]
                if i in HIT.get(anim, ()):
                    tx, ty = pts["weapon_tip"]
                    hx, hy = pts["hand_near"]
                    x0, y0 = min(tx, hx) - 3, min(ty, hy) - 3
                    pts["hitboxes"] = [[x0, y0, abs(tx - hx) + 7, abs(ty - hy) + 7]]
                anchors[anim][d].append(pts)
    # swing trails: the slash sweeps the blade's tip from the windup to the strike around the
    # shoulder; the lunge leaves streaks along the thrust
    trails = {}
    for anim, (a, b) in (("attack_slash", (1, 2)), ("attack_lunge", (1, 2))):
        cells = {(d, i): empty(SIZE) for d in DIRS for i in range(len(FRAMES[anim]))}
        front = {(d, i): empty(SIZE) for d in DIRS for i in range(len(FRAMES[anim]))}
        for d in DIRS:
            pa, pb = anchors[anim][d][a]["weapon_tip"], anchors[anim][d][b]["weapon_tip"]
            pivot = anchors[anim][d][b]["torso"]
            if anim == "attack_slash":
                through = {"e": None, "s": 90, "n": -90}[d]
                path = sweep(tuple(pa), tuple(pb), (pivot[0], pivot[1] - 2), through)
            else:
                path = dragon.line(tuple(pa), tuple(pb))
            target = front if (anim == "attack_slash" and d == "s") else cells
            for x, y, rank in crescent(path, 3):
                if 3 <= x <= SIZE - 5 and 3 <= y <= GROUND and target[(d, b)][y, x] == CLEAR:
                    target[(d, b)][y, x] = rank + 1
        trails[f"smear_{anim}"] = cells
        if any((c != CLEAR).any() for c in front.values()):
            trails[f"smear_{anim}_front"] = front
    counts = {a: len(f) for a, f in FRAMES.items() if f is not None}
    notes = {"cape": ("cloth", "A long tattered cape: behind facing s and e, over the back facing n."),
             "body": ("metal", "Plate armor, the crested helm and the limbs, posed per frame."),
             "plume": ("cloth", "The helm's plume, sweeping back."),
             "shaft": ("leather", "The glaive's shaft and the belt."),
             "blade": ("metal", "The glaive's curved blade.")}
    for slot, (material, text) in notes.items():
        write_part(slot, "duelist", {"material": material, "kind": "animated", "lags": False,
                                     "rigs": [RIG], "notes": text}, layers[slot], counts, size=SIZE)
    write_part("held_near", "duelist_glaive", {
        "material": "metal", "kind": "animated", "lags": False, "rigs": [RIG],
        "notes": "No art: the white trails of the glaive's sweep and lunge (smear_<anim>)."},
        {**fists, **trails}, {**counts, **{k: counts[k[6:].removesuffix("_front")] for k in trails}},
        size=SIZE)
    eyes = {}
    f0 = {d: frame(d, P()) for d in DIRS}
    for d in DIRS:
        e = empty(SIZE)
        if d != "n":
            ex, ey = f0[d]["points"]["eyes"]
            for ox in ((-2, 2) if d == "s" else (2, 3)):
                e[ey, ex + ox] = 0
        eyes[(d, 0)] = e
    write_part("eyes", "duelist", {"material": "eyes", "kind": "rigid", "attach": "eyes", "origin": "auto",
                                   "lags": False, "rigs": [RIG], "allow_singletons": {"s": [[21, 12], [25, 12]]},
                                   "notes": "Eyes glowing in the visor slit."}, {"rigid": eyes}, size=SIZE)
    write_anchors(RIG, anchors)
    base = {"rig": RIG, "timing_profile": "elite", "seed": 1,
            "parts": {"cape": "duelist", "body": "duelist", "plume": "duelist", "shaft": "duelist",
                      "blade": "duelist", "eyes": "duelist", "held_near": "duelist_glaive"},
            "anims": ["idle", "walk", "combat_idle", "attack_slash", "attack_lunge", "dodge", "hurt",
                      "death"]}
    write_recipe("monsters/ashen_duelist.yaml", {
        "name": "ashen_duelist", "family": "ashen_duelist", **base,
        "colors": {"metal": "obsidian", "cloth": "scarlet", "leather": "black", "eyes": "glow yellow"},
        "slot_colors": {"blade": "steel", "plume": "snow"}})
    print("wrote the ashen duelist")


if __name__ == "__main__":
    main()
