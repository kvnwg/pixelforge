"""Cinderwyrm: a big, slow fire dragon on the huge 96 px canvas (MONSTERS.md section 5.8).

The human asked for "monsters that are BIG and slow like dragons". An original design: a heavy
four-legged wyrm with ember scales and pale belly plates, a long neck and tail in overlapping
segments, a horned head whose jaw drops open, membrane wings folded over its back that spread
when it roars, and back spikes along the spine. It moves slowly and hits hard, with long tells:
a lunging bite, a tail sweep (with a white swing trail), fire breath (a fan of fireballs from
the mouth) and a roar.

Construction (like the Stone Warden): every piece is a shaded rounded box (stone_codes, one
light from the upper left) or a polyline, painted back to front per frame from the pose's joint
positions; a piece drawn over another gets a 1 px outline-colored contour, so segments read
separately. Layers (one material each): wings (membrane), body (scales: body, neck, head, tail,
legs, wing bones), horns (horn: horns, spikes, claws, teeth, belly plates), eyes (glow, rigid),
held_near (no art: the tail sweep's trail). Each layer keeps only what it shows.

Run: .venv/bin/python tools/art/dragon.py
"""

from __future__ import annotations

import math

import numpy as np

from artlib import STYLE, arc_path, crescent, empty, grid, write_anchors, write_part, write_recipe
from pixelforge.anim import load_anims
from stone_warden import stone_codes

RIG = "dragon"
DIRS = ("s", "e", "n")
SIZE = 96
AXIS = 47
GROUND = 91
CLEAR, INK = grid.CLEAR, grid.INK
LAYERS = ("wings", "body", "horns")


def E() -> np.ndarray:
    return empty(SIZE)


def oval(w: int, h: int, far: bool = False) -> np.ndarray:
    return stone_codes(max(w, 2), max(h, 2), 2.1, far, 0, crack=False)


def bezier(p0, p1, p2, n):
    out = []
    for k in range(n):
        t = k / max(n - 1, 1)
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    return out


def line(a, b):
    """4-connected integer points from a to b."""
    (x0, y0), (x1, y1) = (int(round(a[0])), int(round(a[1]))), (int(round(b[0])), int(round(b[1])))
    pts = [(x0, y0)]
    n = max(abs(x1 - x0), abs(y1 - y0))
    for k in range(1, n + 1):
        x = int(round(x0 + (x1 - x0) * k / n))
        y = int(round(y0 + (y1 - y0) * k / n))
        if x != pts[-1][0] and y != pts[-1][1]:
            pts.append((x, pts[-1][1]))
        pts.append((x, y))
    return pts


def ink(p, x, y):
    """An outline-colored detail drawn straight into the body layer (eyes, nostrils)."""
    x, y = int(x), int(y)
    if 3 <= x <= SIZE - 5 and 3 <= y <= GROUND:
        p.layers["body"][y, x] = INK
        p.canvas[y, x] = INK
        p.on_top[y, x] = "body"


class Painter:
    """One frame: layers painted back to front on a shared canvas; `finish` keeps per layer only
    what shows and cleans single pixels."""

    def __init__(self):
        self.canvas = E()
        self.on_top = np.full((SIZE, SIZE), "", object)
        self.layers = {k: E() for k in LAYERS}

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

    def oval(self, layer, c, w, h, far=False, ring=True):
        codes = oval(w, h, far)
        x0, y0 = int(round(c[0] - (w - 1) / 2)), int(round(c[1] - (h - 1) / 2))
        self.put(layer, codes, x0, y0, ring)
        return (x0, y0, w, h)

    def pts(self, layer, points, ring=False):
        """(x, y, shade) in canvas coordinates."""
        if not points:
            return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x0, y0 = min(xs), min(ys)
        codes = np.full((max(ys) - y0 + 1, max(xs) - x0 + 1), CLEAR, np.int8)
        for x, y, v in points:
            codes[y - y0, x - x0] = max(codes[y - y0, x - x0], v)
        self.put(layer, codes, x0, y0, ring)

    def finish(self):
        for k in self.layers:
            self.layers[k][self.on_top != k] = CLEAR
        for k, layer in self.layers.items():
            for _ in range(2):  # a lone shade takes its neighbors' most common shade, in place,
                # so two lone neighbors agree instead of swapping shades (a checkerboard)
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


# ============================================================================== pieces
def thick(points, shade_top=2, shade_under=1, width=2):
    """A beam 2 px thick along a polyline: lit top row, shaded underside."""
    out = []
    for a, b in zip(points, points[1:]):
        for x, y in line(a, b):
            out.append((x, y, shade_top))
            if width > 1:
                out.append((x, y + 1, shade_under))
    return out


def horn_line(points, shade=2):
    """A horn or spike in one shade: 2 px thick over its root half, 1 px to the tip, so it is one
    connected run (a shade change along a 1 px line would leave single pixels)."""
    out = []
    pts = []
    for a, b in zip(points, points[1:]):
        pts += line(a, b)
    for i, (x, y) in enumerate(pts):
        out.append((x, y, shade))
        if i < len(pts) // 2:
            out.append((x, y + 1, shade))
    return out


def fill_poly(poly):
    """Integer pixels inside a polygon (even-odd scanlines)."""
    ys = [p[1] for p in poly]
    out = []
    for y in range(int(math.floor(min(ys))), int(math.ceil(max(ys))) + 1):
        xs = []
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            for x in range(int(math.ceil(a)), int(math.floor(b)) + 1):
                out.append((x, y))
    return out


def wing(p: Painter, shoulder, wrist, tips, far=False):
    """Membrane panels between finger bones (wings layer), then the bones (body layer). Panels
    alternate shades so the fingers read; a far wing is a shade darker."""
    fingers = [wrist] + list(tips)
    panels = [[shoulder, wrist, tips[0]]] + [[wrist, a, b] for a, b in zip(tips, tips[1:])] + \
             [[shoulder, wrist, tips[-1]]]
    seen = set()
    membrane = []
    for i, poly in enumerate(panels):
        shade = (i + (1 if far else 0)) % 2 if not far else 0
        for x, y in fill_poly([tuple(map(float, q)) for q in poly]):
            if (x, y) not in seen:
                seen.add((x, y))
                membrane.append((x, y, shade))
    p.pts("wings", membrane, ring=True)
    bones = thick([shoulder, wrist], 1 if far else 2, 0 if far else 1)
    for t in tips:
        bones += thick([wrist, t], 1 if far else 2, 0 if far else 1, width=1)
    p.pts("body", bones, ring=False)
    del fingers


# ============================================================================== poses
def F(b=(0, 0), h=(0, 0), jaw=False, wings="fold", tail=(0, 0), tail_tip=(0, 0), legs="stand",
      fall=0.0, flags=()):
    """b: the body's offset; h: the head's on top of it; jaw: open; wings: fold | half | spread;
    tail: the tail curve's control offset, tail_tip: its tip's; legs: a leg pose; fall: 0..1
    collapsing (death)."""
    return {"b": b, "h": h, "jaw": jaw, "wings": wings, "tail": tail, "tail_tip": tail_tip,
            "legs": legs, "fall": fall, "flags": flags}


LEG_STEPS = {  # (front near, hind near, front far, hind far) foot offsets (dx, dy), along the facing for e
    "stand": ((0, 0), (0, 0), (0, 0), (0, 0)),
    "step_a": ((3, -2), (0, 0), (0, 0), (3, -2)),
    "step_b": ((2, 0), (-2, 0), (-2, 0), (2, 0)),
    "step_c": ((0, 0), (3, -2), (3, -2), (0, 0)),
    "step_d": ((-2, 0), (2, 0), (2, 0), (-2, 0)),
    "brace": ((3, 0), (-2, 0), (2, 0), (-2, 0)),
    "rear": ((1, -3), (0, 0), (1, -3), (0, 0)),
}

FRAMES = {
    "idle": [F(), F(b=(0, 1)), F(b=(0, 1), h=(0, 1)), F(h=(0, 1))],
    "walk": [F(legs="step_a", b=(0, -1)), F(legs="step_b"), F(legs="step_b", b=(0, 1)),
             F(legs="step_c", b=(0, -1)), F(legs="step_d"), F(legs="step_d", b=(0, 1))],
    "attack_bite": [F(h=(-6, -5), b=(-1, 0), legs="brace"), F(h=(-9, -4), b=(-2, 1), legs="brace"),
                    F(h=(6, 7), b=(2, 1), jaw=True, legs="brace"), F(h=(6, 8), b=(2, 1), legs="brace"),
                    F(h=(3, 2), b=(1, 0)), F()],
    "attack_tail": [F(b=(1, 0), tail=(6, -10), tail_tip=(10, -12), legs="brace"),
                    F(b=(2, -1), h=(2, 0), tail=(8, -16), tail_tip=(14, -22), legs="brace"),
                    F(b=(-1, 1), h=(-1, 1), tail=(-4, 4), tail_tip=(-1, 6), legs="brace"),
                    F(b=(-1, 1), tail=(-6, 6), tail_tip=(-2, 8), legs="brace"), F(b=(0, 1)), F()],
    "breath": [F(b=(0, -1), h=(-2, -4), legs="rear"), F(b=(-1, -2), h=(-5, -7), wings="half", legs="rear"),
               F(b=(1, 0), h=(5, 3), jaw=True, wings="half", legs="brace"),
               F(b=(1, 0), h=(6, 4), jaw=True, wings="half", legs="brace"), F(h=(2, 1)), F()],
    "roar": [F(b=(0, -1), h=(-2, -4), wings="half", legs="rear"),
             F(b=(0, -2), h=(-1, -7), jaw=True, wings="spread", legs="rear"),
             F(b=(0, -2), h=(-1, -7), jaw=True, wings="spread", legs="rear"), F(wings="half")],
    "hurt": [F(), F(b=(-2, 0), h=(-4, -1), jaw=True), F(b=(-1, 0), h=(-1, 0))],
    "death": [F(), F(b=(-1, 1), h=(-3, 2), jaw=True), F(b=(0, 3), h=(0, 8), fall=0.35, jaw=True),
              F(b=(0, 5), h=(4, 16), fall=0.7, wings="half"), F(b=(0, 6), h=(6, 20), fall=1.0, wings="half")],
}
FRAMES["combat_idle"] = None  # an alias of idle (style.json)


# ============================================================================== composing a frame
def frame(d: str, spec) -> dict:
    p = Painter()
    ex = (lambda v: v) if d == "e" else (lambda v: 0)
    bx, by = ex(spec["b"][0]), spec["b"][1]
    hx, hy = bx + (spec["h"][0] if d == "e" else 0), by + spec["h"][1] + (0 if d == "e" else spec["h"][0] // 3)
    if d == "s":  # a lunge toward the camera reads as the head coming down and nearer
        hy = by + spec["h"][1] + max(0, spec["h"][0]) // 2
    if d == "n":
        hy = by + spec["h"][1] - max(0, spec["h"][0]) // 2
    fall = spec["fall"]
    steps = LEG_STEPS[spec["legs"]]
    boxes: dict[str, tuple[int, int, int, int]] = {}
    pts: dict[str, list[int]] = {}

    def leg(hip, foot, size, far=False, name=""):
        tw, th = size
        hip = (hip[0], hip[1] + fall * 6)
        boxes[name + "_thigh"] = p.oval("body", hip, tw, th, far)
        shin_c = ((hip[0] + foot[0]) / 2, (hip[1] + th / 3 + foot[1]) / 2)
        p.oval("body", shin_c, max(5, tw - 4), max(6, int(foot[1] - hip[1] - th / 3)), far, ring=False)
        fw = tw + 1
        boxes[name] = p.oval("body", (foot[0], foot[1] - 2), fw, 5, far, ring=False)
        claws = []
        front = 1 if d == "e" else 0
        if d == "e":  # three claws curling forward off the toes, 2 px each
            cx = int(round(foot[0] + fw / 2))
            for k in range(2):
                y = int(foot[1]) - 3 + k * 2
                claws += [(cx, y, 2), (cx + 1, y, 2)]
        else:
            x0 = int(round(foot[0] - fw / 2)) + 1
            for k in range(3):
                X = x0 + k * max(3, fw // 3)
                claws += [(X, int(foot[1]) - 1, 2), (X + 1, int(foot[1]) - 1, 2)]
        del front
        p.pts("horns", claws, ring=False)

    if d == "e":
        B = (40 + bx, 66 + by + fall * 10)
        H = (63 + hx, 37 + hy)
        # far side first: far wing, far legs
        wing_pose(p, d, spec["wings"], B, far=True)
        leg((B[0] + 10, B[1] + 2), (B[0] + 13 + steps[2][0], GROUND + steps[2][1]), (11, 13), True, "front_far")
        leg((B[0] - 10, B[1] + 2), (B[0] - 8 + steps[3][0], GROUND + steps[3][1]), (12, 14), True, "hind_far")
        # the tail behind the body, tip first
        root = (B[0] - 17, B[1] + 2)
        tip = (6 + spec["tail_tip"][0], 82 + by + spec["tail_tip"][1] + fall * 4)
        ctrl = (14 + spec["tail"][0], 64 + by + spec["tail"][1])
        tail = bezier(root, ctrl, tip, 8)
        for i in range(len(tail) - 1, -1, -1):
            w = int(round(15 - i * 1.4))
            p.oval("body", tail[i], w, max(4, w - 2), ring=i == len(tail) - 1)
        pts["tail_tip"] = [int(round(tip[0])), int(round(tip[1]))]
        spikes = []
        for i in range(1, len(tail), 2):  # spikes along the tail's top
            x, y = tail[i]
            top = int(round(y - (15 - i * 1.4) / 2))
            spikes += horn_line([(x, top), (x - 2, top - 3)])
        boxes["body"] = p.oval("body", B, 38, 24)
        belly = []
        x0, y0, w, h = boxes["body"]
        for x in range(x0 + 6, x0 + w - 5):
            for k in range(3):
                y = y0 + h - 2 - k
                belly.append((x, y, 2 if k == 2 else 1 if k == 1 else 0) if (x - x0) % 5 else (x, y, 0))
        p.pts("horns", belly, ring=False)
        leg((B[0] - 12, B[1] + 4), (B[0] - 10 + steps[1][0], GROUND + steps[1][1]), (13, 15), False, "hind_near")
        # the neck, chest to head, then the head
        chest = (B[0] + 14, B[1] - 6)
        neck = bezier(chest, (H[0] - 6, H[1] + 18), (H[0] - 3, H[1] + 5), 5)
        for i, c in enumerate(neck[:-1]):
            w = int(round(14 - i * 1.3))
            p.oval("body", c, w, w, ring=i == 0)
            spikes += horn_line([(int(c[0]) - 1, int(c[1] - w / 2)), (int(c[0]) - 3, int(c[1] - w / 2) - 3)])
        for i in (0, 2, 4):  # spikes along the back
            sx = x0 + 8 + i * 4
            spikes += horn_line([(sx, y0 + 1), (sx - 2, y0 - 3)])
        p.pts("horns", spikes, ring=True)
        leg((B[0] + 12, B[1] + 4), (B[0] + 15 + steps[0][0], GROUND + steps[0][1]), (12, 14), False, "front_near")
        head_e(p, H, spec["jaw"], pts, boxes)
        wing_pose(p, d, spec["wings"], B, far=False)
        pts["torso"] = [int(round(B[0])), int(round(B[1]))]
    else:  # s and n: symmetric about the axis
        B = (AXIS + 0.0, 62 + by + fall * 10)
        H = (AXIS + 0.0, (50 if d == "s" else 34) + hy)
        front = d == "s"
        if front:
            wing_pose(p, d, spec["wings"], B, far=True)
            # the tail curls out at the right, behind the body
            tail = bezier((B[0] + 8, B[1] + 10),
                          (B[0] + 30 + spec["tail"][0] // 4, B[1] + 18 + spec["tail"][1]),
                          (B[0] + 40 + spec["tail_tip"][0] // 4, GROUND - 6 + spec["tail_tip"][1]), 7)
            for i, c in enumerate(tail):
                w = int(round(13 - i * 1.3))
                p.oval("body", c, w, max(4, w - 2), ring=i == 0)
            pts["tail_tip"] = [int(round(tail[-1][0])), int(round(tail[-1][1]))]
            for sx in (-1, 1):  # hind legs peek out behind
                st = steps[1] if sx < 0 else steps[3]
                leg((B[0] + sx * 18, B[1] + 6), (B[0] + sx * 22 + sx * st[0], GROUND + st[1]),
                    (11, 13), True, "hind_far" if sx > 0 else "hind_near")
            boxes["body"] = p.oval("body", B, 34, 26)
            x0, y0, w, h = boxes["body"]
            belly = []
            for y in range(y0 + 8, y0 + h - 2):
                half = 6 - abs(y - (y0 + h // 2 + 3)) // 3
                for x in range(int(B[0]) - half, int(B[0]) + half + 1):
                    belly.append((x, y, 2 if (y - y0) % 4 == 0 else 1))
            p.pts("horns", belly, ring=True)
            for sx in (-1, 1):
                st = steps[0] if sx < 0 else steps[2]
                leg((B[0] + sx * 13, B[1] + 8), (B[0] + sx * 15 + sx * st[0], GROUND + st[1]),
                    (12, 14), False, "front_near" if sx < 0 else "front_far")
            neck_c = ((B[0] + H[0]) / 2, (B[1] - 10 + H[1]) / 2)
            p.oval("body", neck_c, 14, 12)
            head_s(p, H, spec["jaw"], pts, boxes)
            wing_pose(p, d, spec["wings"], B, far=False)
        else:  # n: from behind, the tail comes toward the camera
            for sx in (-1, 1):
                st = steps[2] if sx > 0 else steps[0]
                leg((B[0] + sx * 12, B[1] + 4), (B[0] + sx * 14 - sx * st[0], GROUND - 3 + st[1]),
                    (10, 12), True, "front_far" if sx > 0 else "front_near")
            neck = bezier((B[0], B[1] - 10), (H[0], H[1] + 14), (H[0], H[1] + 6), 4)
            for i, c in enumerate(neck):
                w = int(round(15 - i * 1.4))
                p.oval("body", c, w, w - 1, ring=i == 0)
            head_n(p, H, pts, boxes)
            boxes["body"] = p.oval("body", B, 34, 26)
            spikes = []
            for k in range(5):  # down the spine
                y = int(B[1]) - 10 + k * 5
                spikes += horn_line([(AXIS, y), (AXIS, y - 3)])
            p.pts("horns", spikes, ring=True)
            wing_pose(p, d, spec["wings"], B, far=False)
            for sx in (-1, 1):
                st = steps[1] if sx < 0 else steps[3]
                leg((B[0] + sx * 16, B[1] + 8), (B[0] + sx * 19 + sx * st[0], GROUND + st[1]),
                    (13, 15), False, "hind_near" if sx < 0 else "hind_far")
            tail = bezier((B[0] + 2, B[1] + 10), (B[0] + 12 + spec["tail"][0], GROUND - 2 + spec["tail"][1]),
                          (B[0] + 30 + spec["tail_tip"][0], GROUND - 6 + spec["tail_tip"][1]), 7)
            for i, c in enumerate(tail):
                w = int(round(14 - i * 1.4))
                p.oval("body", c, w, max(4, w - 3), ring=i == 0)
            pts["tail_tip"] = [int(round(tail[-1][0])), int(round(tail[-1][1]))]
        pts["torso"] = [int(round(B[0])), int(round(B[1]))]
    p.finish()

    def bottom(name):
        x0, y0, w, h = boxes[name]
        return [int(round(x0 + (w - 1) / 2)), min(y0 + h - 1, GROUND)]

    pts.update({"foot_near": bottom("front_near"), "foot_far": bottom("hind_near"), "planted": []})
    tx, ty = pts["tail_tip"]
    pts["tail_tip"] = [min(max(tx, 4), SIZE - 6), min(max(ty, 4), GROUND)]
    pts.setdefault("eyes", pts["head"])
    return {"layers": p.layers, "points": pts, "boxes": boxes}


WINGS = {  # (shoulder, wrist, tips) relative to the body's center, facing e; s/n: the left wing
    ("e", "fold"): ((4, -10), (-4, -34), [(-24, -26), (-22, -14), (-14, -6)]),
    ("e", "half"): ((4, -10), (-2, -40), [(-26, -36), (-26, -22), (-16, -8)]),
    ("e", "spread"): ((4, -10), (2, -44), [(-24, -44), (-30, -28), (-20, -10)]),
    ("s", "fold"): ((-12, -8), (-20, -32), [(-34, -22), (-30, -12), (-22, -4)]),
    ("s", "half"): ((-12, -8), (-24, -36), [(-38, -28), (-38, -14), (-26, -4)]),
    ("s", "spread"): ((-12, -8), (-28, -40), [(-42, -36), (-42, -20), (-32, -6)]),
}


def wing_pose(p, d, pose, B, far):
    if d == "e":
        sh, wr, tips = WINGS[("e", pose)]
        off = (5, -3) if far else (0, 0)
        to = lambda q: (B[0] + q[0] + off[0], B[1] + q[1] + off[1])  # noqa: E731
        wing(p, to(sh), to(wr), [to(t) for t in tips], far=far)
        return
    if far and d == "s":  # facing s both wings sit behind the body: draw them first, as "far"
        for sx in (-1, 1):
            sh, wr, tips = WINGS[("s", pose)]
            to = lambda q, sx=sx: (B[0] + q[0] if sx < 0 else B[0] - q[0], B[1] + q[1])  # noqa: E731
            wing(p, to(sh), to(wr), [to(t) for t in tips], far=False)
        return
    if d == "n" and not far:  # from behind the wings lie over the back
        for sx in (-1, 1):
            sh, wr, tips = WINGS[("s", pose)]
            to = lambda q, sx=sx: (B[0] + q[0] if sx < 0 else B[0] - q[0], B[1] + q[1])  # noqa: E731
            wing(p, to(sh), to(wr), [to(t) for t in tips], far=False)


def head_e(p, H, jaw, pts, boxes):
    """Profile head facing right: cranium, snout, jaw (dropped when open), eye, nostril, teeth,
    two horns sweeping back."""
    horns = horn_line([(H[0] - 3, H[1] - 5), (H[0] - 9, H[1] - 9), (H[0] - 15, H[1] - 10)])
    p.pts("horns", [(x + 2, y - 1, max(0, v - 1)) for x, y, v in horns], ring=True)  # the far horn
    jaw_c = (H[0] + 7, H[1] + (9 if jaw else 6))
    p.oval("body", jaw_c, 13 if jaw else 14, 5)
    if jaw:  # the mouth: a dark gap between the jaws with teeth
        gap = [(x, y, 0) for x in range(int(H[0]) + 2, int(H[0]) + 14) for y in range(int(H[1]) + 5, int(H[1]) + 7)]
        p.pts("body", gap, ring=False)
    boxes["head"] = p.oval("body", H, 13, 11)
    p.oval("body", (H[0] + 9, H[1] + 2), 15, 7)
    teeth = [(x, int(H[1]) + 5 + (1 if jaw else 0), 2) for x in range(int(H[0]) + 5, int(H[0]) + 15, 3)]
    teeth += [(x + 1, y, 2) for x, y, _ in teeth]
    p.pts("horns", teeth, ring=False)
    eye = (int(H[0]) + 2, int(H[1]) - 1)
    ink(p, *eye)
    ink(p, eye[0] + 1, eye[1])
    ink(p, int(H[0]) + 15, int(H[1]) + 1)  # nostril
    p.pts("horns", horns, ring=True)
    pts["head"] = [int(H[0]), boxes["head"][1]]
    pts["eyes"] = [eye[0], eye[1]]
    pts["mouth"] = [int(H[0]) + 16, int(H[1]) + (6 if jaw else 4)]


def head_s(p, H, jaw, pts, boxes):
    """Facing the camera: cranium over a short snout, the jaw below (open: a dark mouth), eyes at
    the brow, horns rising and curling out."""
    for sx in (-1, 1):
        p.pts("horns", horn_line([(H[0] + sx * 5, H[1] - 7), (H[0] + sx * 9, H[1] - 12),
                                  (H[0] + sx * 14, H[1] - 14)]), ring=False)
    jaw_c = (H[0], H[1] + (9 if jaw else 7))
    p.oval("body", jaw_c, 10, 5)
    if jaw:
        p.pts("body", [(x, y, 0) for x in range(int(H[0]) - 3, int(H[0]) + 4)
                       for y in range(int(H[1]) + 5, int(H[1]) + 7)], ring=False)
    boxes["head"] = p.oval("body", (H[0], H[1] - 3), 15, 11)
    p.oval("body", (H[0], H[1] + 3), 11, 8)
    eyes = []
    for sx in (-1, 1):
        ex = int(H[0]) + sx * 4 - (1 if sx < 0 else 0)
        for x in (ex, ex + 1):
            ink(p, x, int(H[1]) - 3)
        eyes.append(ex)
    for sx in (-1, 1):
        ink(p, int(H[0]) + sx * 2, int(H[1]) + 4)  # nostrils
    if jaw:
        teeth = [(x, int(H[1]) + 5, 2) for x in (int(H[0]) - 3, int(H[0]) - 2, int(H[0]) + 2, int(H[0]) + 3)]
        p.pts("horns", teeth, ring=False)
    pts["head"] = [int(H[0]), boxes["head"][1]]
    pts["eyes"] = [int(H[0]), int(H[1]) - 3]
    pts["mouth"] = [int(H[0]), int(H[1]) + 8]


def head_n(p, H, pts, boxes):
    boxes["head"] = p.oval("body", H, 14, 11)
    for sx in (-1, 1):
        p.pts("horns", horn_line([(H[0] + sx * 5, H[1] - 4), (H[0] + sx * 9, H[1] - 9),
                                  (H[0] + sx * 14, H[1] - 11)]), ring=True)
    pts["head"] = [int(H[0]), boxes["head"][1]]
    pts["mouth"] = [int(H[0]), int(H[1]) - 6]


# ============================================================================== writing
HIT = {"attack_bite": (2, 3), "attack_tail": (2, 3)}


def main() -> None:
    anims = load_anims(STYLE, RIG)
    layers = {k: {} for k in LAYERS}
    anchors = {}
    fists = {}
    trail = {}
    for anim, frames in FRAMES.items():
        if frames is None:
            continue
        assert len(frames) == anims[anim].frames, (anim, len(frames), anims[anim].frames)
        for k in layers:
            layers[k][anim] = {}
        anchors[anim] = {d: [] for d in DIRS}
        fists[anim] = {(d, i): E() for d in DIRS for i in range(len(frames))}
        for i, spec in enumerate(frames):
            for d in DIRS:
                f = frame(d, spec)
                for k in LAYERS:
                    layers[k][anim][(d, i)] = f["layers"][k]
                pts = f["points"]
                if i in HIT.get(anim, ()):
                    if anim == "attack_bite":
                        mx, my = pts["mouth"]
                        pts["hitboxes"] = [[mx - 9, my - 7, 16, 14]]
                    else:
                        tx, ty = pts["tail_tip"]
                        pts["hitboxes"] = [[tx - 10, ty - 10, 22, 18]]
                anchors[anim][d].append(pts)
    # the tail sweep's trail: on the strike frame, the arc the tail's tip traced from the frame before
    cells = {(d, i): E() for d in DIRS for i in range(len(FRAMES["attack_tail"]))}
    for d in DIRS:
        a = anchors["attack_tail"][d][1]["tail_tip"]
        b = anchors["attack_tail"][d][2]["tail_tip"]
        pivot = anchors["attack_tail"][d][2]["torso"]
        for x, y, rank in crescent(arc_path(tuple(a), tuple(b), tuple(pivot)), 4):
            if 3 <= x <= SIZE - 5 and 3 <= y <= GROUND and cells[(d, 2)][y, x] == CLEAR:
                cells[(d, 2)][y, x] = rank + 1
    trail["smear_attack_tail"] = cells
    counts = {a: len(f) for a, f in FRAMES.items() if f is not None}
    notes = {"wings": ("membrane", "Wing membranes in panels between the finger bones."),
             "body": ("scales", "Body, neck, head, tail and legs in overlapping segments; wing bones."),
             "horns": ("horn", "Horns, back spikes, claws, teeth and belly plates.")}
    for slot, (material, text) in notes.items():
        write_part(slot, "cinderwyrm", {"material": material, "kind": "animated", "lags": False,
                                        "rigs": [RIG], "notes": text}, layers[slot], counts, size=SIZE)
    write_part("held_near", "cinderwyrm_tail", {
        "material": "metal", "kind": "animated", "lags": False, "rigs": [RIG],
        "notes": "No art: the tail sweep's white swing trail (smear_attack_tail)."},
        {**fists, **trail}, {**counts, "smear_attack_tail": counts["attack_tail"]}, size=SIZE)
    eyes = {}
    f0 = {d: frame(d, F()) for d in DIRS}
    for d in DIRS:
        e = E()
        if d != "n":
            ex, ey = f0[d]["points"]["eyes"]
            for ox in ((-4, -5, 4, 3) if d == "s" else (0, 1)):
                e[ey, ex + ox] = 0
        eyes[(d, 0)] = e
    write_part("eyes", "cinderwyrm", {"material": "eyes", "kind": "rigid", "attach": "eyes",
                                      "origin": "auto", "lags": False, "rigs": [RIG],
                                      "allow_singletons": {},
                                      "notes": "Glowing eyes under the brow."}, {"rigid": eyes}, size=SIZE)
    write_anchors(RIG, anchors)
    base = {"rig": RIG, "timing_profile": "boss", "seed": 1,
            "parts": {"wings": "cinderwyrm", "body": "cinderwyrm", "horns": "cinderwyrm",
                      "eyes": "cinderwyrm", "held_near": "cinderwyrm_tail"},
            "anims": ["idle", "walk", "combat_idle", "attack_bite", "attack_tail", "breath", "roar",
                      "hurt", "death"]}
    write_recipe("monsters/cinderwyrm.yaml", {
        "name": "cinderwyrm", "family": "cinderwyrm", **base,
        "colors": {"scales": "ember", "membrane": "ember", "horn": "pale", "eyes": "glow yellow"}})
    write_recipe("monsters/cinderwyrm_obsidian.yaml", {
        "name": "cinderwyrm_obsidian", "family": "cinderwyrm", **base,
        "colors": {"scales": "obsidian", "membrane": "ash", "horn": "gilded", "eyes": "glow red"}})
    print("wrote the cinderwyrm")


if __name__ == "__main__":
    main()
