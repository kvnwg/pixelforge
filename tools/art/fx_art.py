"""The v1 FX library (COMBAT.md section 6), drawn in code facing east.

Every FX is a set of frames of shade indices into its base ramp (0 darkest .. 3 lightest from
style.json `fx_ramps`), with -1 for empty. No outline; hard pixels; a 1 px margin inside the cell
so the exporter can mirror and rotate without clipping. Shapes come from a few helpers (stars,
rings, crescents, blobs) and small hand-placed grids.

Run: .venv/bin/python tools/art/fx_art.py   (then pf fx build --all)
"""

from __future__ import annotations

import math

import numpy as np
import yaml

from artlib import ROOT, STYLE
from pixelforge.color import parse_hex
from pixelforge.sheet import save_rgba

FX_DIR = ROOT / "fx"
ELEMENTS = ("fire", "ice", "poison", "arcane", "holy", "shadow")


# ============================================================================== drawing helpers
class Cell:
    def __init__(self, size: int):
        self.size = size
        self.g = np.full((size, size), -1, np.int8)

    def put(self, x: float, y: float, s: int, *, over: bool = True) -> None:
        x, y = int(round(x)), int(round(y))
        if not (1 <= x < self.size - 1 and 1 <= y < self.size - 1):
            raise ValueError(f"({x}, {y}) is outside the {self.size} px cell's margin")
        if over or self.g[y, x] < 0:
            self.g[y, x] = s

    def brighten(self, x, y, s):
        x, y = int(round(x)), int(round(y))
        if self.g[y, x] < s:
            self.put(x, y, s)

    def grid(self, rows: list[str], x0: int, y0: int) -> None:
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch != ".":
                    self.put(x0 + dx, y0 + dy, int(ch))

    def plus(self, cx, cy, shades: list[int], *, start: int = 0) -> None:
        """Arms along the axes; shades[d] at distance d (from `start` outward)."""
        for d in range(start, len(shades)):
            for x, y in {(cx + d, cy), (cx - d, cy), (cx, cy + d), (cx, cy - d)}:
                self.put(x, y, shades[d])

    def diag(self, cx, cy, d: int, s: int) -> None:
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.put(cx + sx * d, cy + sy * d, s)

    def disk(self, cx, cy, r: float, s: int) -> None:
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + r * 0.6:
                    self.put(x, y, s)

    def ring(self, cx, cy, r: int, s: int, keep=lambda a: True) -> None:
        """A 1 px ring (midpoint circle); keep(angle in degrees) leaves gaps."""
        x, y, err = r, 0, 1 - r
        pts = set()
        while x >= y:
            for px, py in ((x, y), (y, x), (-y, x), (-x, y), (-x, -y), (-y, -x), (y, -x), (x, -y)):
                pts.add((px, py))
            y += 1
            if err < 0:
                err += 2 * y + 1
            else:
                x -= 1
                err += 2 * (y - x) + 1
        for px, py in pts:
            if keep(math.degrees(math.atan2(-py, px)) % 360):
                self.put(cx + px, cy + py, s)

    def blob(self, cx, cy, r: float, *, light=3, mid=2, dark=1) -> None:
        """A shaded ball lit from the upper right: dark rim low-left, light high-right."""
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if d2 <= r * r + r * 0.6:
                    lx, ly = x - cx, y - cy
                    s = mid
                    if lx - ly > r * 0.6:
                        s = light
                    elif ly - lx > r * 0.7 or d2 > r * r - r * 0.4:
                        s = dark if ly - lx > -0.5 else mid
                    self.put(x, y, s)


def polar(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy - r * math.sin(a)


# ============================================================================== impacts
def spark_small():
    """A 4-point hit spark about 9 px across: flash, star, breaking up, tips fading."""
    out = []
    c = Cell(16); c.plus(7, 7, [3, 3, 3, 0]); out.append(c)
    c = Cell(16); c.plus(7, 7, [3, 3, 3, 2, 0]); c.diag(7, 7, 2, 3); c.diag(7, 7, 3, 0); out.append(c)
    c = Cell(16); c.plus(7, 7, [0, 0, 3, 2, 0], start=2); c.diag(7, 7, 3, 2); out.append(c)
    c = Cell(16); c.plus(7, 7, [0, 0, 0, 0, 0], start=4); c.diag(7, 7, 3, 3); out.append(c)
    return {"play": out}


def impact_big():
    """A heavy slam: flash, a 17 px star, a breaking ring, and a dust ring along the ground."""
    cx, cy, gy = 15, 16, 20  # burst centre and the ground row the dust runs along
    out = []
    c = Cell(32); c.disk(cx, cy, 1.6, 3); c.plus(cx, cy, [3, 3, 3, 3, 0]); out.append(c)
    c = Cell(32); c.plus(cx, cy, [3, 3, 3, 3, 2, 2, 0]); c.diag(cx, cy, 2, 3); c.diag(cx, cy, 3, 2)
    c.diag(cx, cy, 4, 0); c.disk(cx, cy, 1, 3)
    c.grid(["00"], cx - 5, gy); c.grid(["00"], cx + 4, gy); out.append(c)
    c = Cell(32); c.ring(cx, cy, 5, 3, keep=lambda a: int(a) % 45 > 12)
    c.ring(cx, cy, 6, 0, keep=lambda a: 15 < int(a) % 45 < 32)
    for a in range(0, 360, 45):
        x, y = polar(cx, cy, 7, a); c.put(x, y, 2 if a % 90 else 0)
    c.grid(["001", "110"], cx - 8, gy - 1); c.grid(["100", "011"], cx + 6, gy - 1); out.append(c)
    c = Cell(32); c.ring(cx, cy, 7, 2, keep=lambda a: int(a) % 45 > 20)
    for a in range(22, 360, 45):
        x, y = polar(cx, cy, 8, a); c.put(x, y, 3)
    for a in range(0, 360, 90):
        x, y = polar(cx, cy, 8, a); c.put(x, y, 0)
    c.grid([".00", "010"], cx - 11, gy - 1); c.grid(["00.", "010"], cx + 9, gy - 1); out.append(c)
    c = Cell(32)
    for a in range(0, 360, 60):
        x, y = polar(cx, cy, 9, a + 15); c.put(x, y, 3 if a % 120 else 0)
    c.grid(["00"], cx - 13, gy - 1); c.grid(["00"], cx + 12, gy - 1); out.append(c)
    c = Cell(32)
    for a in range(30, 360, 90):
        x, y = polar(cx, cy, 10, a); c.put(x, y, 0 if a % 180 == 30 else 2)
    c.put(cx - 14, gy - 1, 0); c.put(cx + 14, gy - 1, 0); out.append(c)
    return {"play": out}


def dust_puff():
    """Kicked-up dust at a foot: two puffs that swell, rise and thin out."""
    frames_rows = [
        ["....0....0...", "...010..010..", "...010..010.."],
        ["...0......0..", "..010....010.", "..0110..0110."],
        ["..0........0.", ".010......010", ".0.0......0.0"],
        [".0..........0", "0.0........0."],
    ]
    out = []
    for i, rows in enumerate(frames_rows):
        c = Cell(16); c.grid(rows, 1, 9 - i); out.append(c)
    return {"play": out}


def burst(size=24, flame=False):
    """The shared elemental impact: core flash, petals, ring with rays, scattered motes."""
    cx = cy = size // 2 - 1
    out = []
    c = Cell(size); c.disk(cx, cy, 1.6, 3); c.plus(cx, cy, [3, 3, 2, 0]); out.append(c)
    c = Cell(size); c.disk(cx, cy, 2.6, 2); c.disk(cx, cy, 1.2, 3); c.plus(cx, cy, [3, 3, 3, 2, 1, 0])
    out.append(c)
    c = Cell(size); c.ring(cx, cy, 4, 1); c.ring(cx, cy, 2, 3, keep=lambda a: int(a) % 90 > 20)
    for a in range(0, 360, 45):
        x, y = polar(cx, cy, 6, a); c.put(x, y, 0 if a % 90 else 3)
    out.append(c)
    c = Cell(size); c.ring(cx, cy, 6, 0, keep=lambda a: int(a) % 60 > 25)
    for a in range(30, 360, 60):
        x, y = polar(cx, cy, 7, a); c.put(x, y, 3)
    if flame:
        c.grid(["2", "3"], cx - 3, cy - 9); c.grid(["2", "1"], cx + 3, cy - 8)
    out.append(c)
    c = Cell(size)
    for a in range(0, 360, 72):
        x, y = polar(cx, cy, 8, a + 10); c.put(x, y, 3 if a % 144 else 0)
    if flame:
        c.grid(["1", "2"], cx - 2, cy - 10); c.put(cx + 3, cy - 10, 1)
    out.append(c)
    return out


def impact_elemental():
    return {"play": burst(24)}


# ============================================================================== smears
def crescent(c: Cell, outer, inner, ok, shade_out=2, shade_in=1):
    """Pixels inside the outer circle but outside the inner one, where ok(x, y)."""
    (ox, oy, orad), (ix, iy, irad) = outer, inner
    for y in range(c.size):
        for x in range(c.size):
            if not ok(x, y):
                continue
            do = (x - ox) ** 2 + (y - oy) ** 2
            di = (x - ix) ** 2 + (y - iy) ** 2
            if do <= orad * orad and di > irad * irad:
                edge = do > (orad - 1.2) ** 2
                inner = di <= (irad + 1.0) ** 2
                c.put(x, y, shade_out if edge else 0 if inner else shade_in)


def smears():
    """One-frame swing trails in character coordinates (pivot = the character pivot, facing e),
    in the white swing ramp like the trails weapons draw: core on the leading edge, rim inside."""
    arc = Cell(32)  # a slash: high in front of the head down to the ground in front
    crescent(arc, (16, 17, 11), (14, 17, 10), lambda x, y: x >= 18 and 7 <= y <= 26)
    vertical = Cell(32)  # an overhead: from above the head down to the ground
    crescent(vertical, (15, 18, 12), (13, 19, 11), lambda x, y: x >= 15 and 4 <= y <= 27)
    thrust = Cell(32)  # a thrust: three streaks ahead of the body
    thrust.grid(["...0011112", "0001111122", "....00112"], 18, 19)
    return {"smear_arc": {"play": [arc]}, "smear_vertical": {"play": [vertical]},
            "smear_thrust": {"play": [thrust]}}


# ============================================================================== projectiles
def arrow():
    travel = []
    for wiggle in (0, 1):
        c = Cell(16)
        c.grid(["0000000", ], 4, 7)
        c.put(11, 7, 3); c.put(10, 6, 2); c.put(10, 8, 2)  # head and barbs
        c.grid(["22"], 2 + wiggle, 6); c.grid(["22"], 3 - wiggle, 8); c.put(3, 7, 1)  # fletching
        travel.append(c)
    impact = []
    c = Cell(16); c.grid(["000000"], 3, 7); c.plus(10, 7, [3, 3, 2]); impact.append(c)
    c = Cell(16); c.grid(["000000"], 3, 7); c.plus(10, 7, [0, 2, 2, 1], start=1); impact.append(c)
    c = Cell(16); c.grid(["00000"], 4, 7); c.put(3, 8, 0); c.diag(10, 7, 2, 1); impact.append(c)
    c = Cell(16); c.diag(10, 7, 3, 0); impact.append(c)
    return {"travel": travel, "impact": impact}


FIREBALL = [  # the draft in style/examples/battle_mock: bright head ahead, flickering tail
    [".....0112.....", "...0012233....", ".00112233332...", "...0012233....", ".....0112....."],
    ["......011.....", "..00112233....", "0011122333332..", "..00112233....", "......011....."],
    [".....01122....", "...0012233....", "..0112233332...", ".0..012233....", ".....0112....."],
]


def fireball():
    travel = []
    for rows in FIREBALL:
        c = Cell(16); c.grid(rows, 1, 5); travel.append(c)
    return {"travel": travel, "impact": burst(24, flame=True)}


def ice_shard():
    travel = []
    for glint in (6, 8):
        c = Cell(16)
        c.grid(["....11122.....", "..0111222233...", "....11122....."], 1, 6)
        c.put(glint, 7, 3)
        travel.append(c)
    impact = []
    cx = cy = 11
    c = Cell(24); c.plus(cx, cy, [3, 3, 2]); c.diag(cx, cy, 1, 2); impact.append(c)
    for step, shade in ((3, 3), (5, 2), (7, 1), (9, 0)):
        c = Cell(24)
        for a in (20, 100, 160, 230, 300):  # shards: 2 px lines flying out
            x, y = polar(cx, cy, step, a)
            x2, y2 = polar(cx, cy, step + 1, a)
            c.put(x, y, shade); c.put(x2, y2, max(shade - 2, 0))  # light inner, dark outer
        impact.append(c)
    return {"travel": travel, "impact": impact}


def poison_glob():
    globs = [  # round, stretched along the flight, a little tall: lit from the upper right
        ([".123.", "11233", "11223", "01122", ".011."], 7, 5, [(5, 8, 1), (3, 7, 0)]),
        ([".1233.", "112233", "011222", ".0011."], 6, 5, [(4, 8, 1), (2, 8, 0)]),
        ([".23.", "1233", "1223", "0112", ".01."], 8, 5, [(6, 9, 1), (4, 7, 0)]),
    ]
    travel = []
    for rows, x0, y0, drips in globs:
        c = Cell(16); c.grid(rows, x0, y0)
        for x, y, sh in drips:  # drips trailing behind
            c.put(x, y, sh)
        travel.append(c)
    impact = []
    cx, cy = 11, 13
    c = Cell(24); c.disk(cx, cy, 2.2, 2); c.put(cx + 1, cy - 1, 3); impact.append(c)
    c = Cell(24); c.grid(["..222..", ".22322.", "2211122"], cx - 3, cy - 1)
    for a in (60, 120, 30, 150):
        x, y = polar(cx, cy, 4, a); c.put(x, y, 2)
    impact.append(c)
    c = Cell(24); c.grid(["1.1.1.1", "1111111"], cx - 3, cy)
    for a in (55, 125, 25, 155, 90):
        x, y = polar(cx, cy, 6, a); c.put(x, y, 2 if a != 90 else 3)
    impact.append(c)
    c = Cell(24); c.grid(["0.1...1.0"], cx - 4, cy + 1)
    for a in (50, 130, 20, 160):
        x, y = polar(cx, cy, 8, a); c.put(x, y, 1)
    impact.append(c)
    c = Cell(24); c.grid(["0.....0"], cx - 3, cy + 1)
    for a in (45, 135):
        x, y = polar(cx, cy, 9, a); c.put(x, y, 0)
    impact.append(c)
    return {"travel": travel, "impact": impact}


def arcane_orb():
    travel = []
    for a in (90, 210, 330):
        c = Cell(16); c.disk(8, 7, 1.8, 2); c.plus(8, 7, [3, 3]); c.put(9, 6, 3)
        x, y = polar(8, 7, 4, a); c.put(x, y, 3)
        x, y = polar(8, 7, 4, a + 180); c.put(x, y, 1)
        travel.append(c)
    return {"travel": travel, "impact": burst(24)}


# ============================================================================== casting, status
def gather_glow():
    """Motes converging on the hand while a spell charges (loops)."""
    out = []
    c = Cell(16); c.diag(7, 7, 4, 0); c.put(7, 7, 3); out.append(c)
    c = Cell(16); c.plus(7, 7, [3, 1]); c.plus(7, 7, [0, 0, 0, 0], start=3); out.append(c)
    c = Cell(16); c.disk(7, 7, 1, 3); c.diag(7, 7, 2, 1); c.plus(7, 7, [0, 0, 0, 0, 0, 0], start=5)
    out.append(c)
    return {"loop": out}


STAR = ["2", "3", "2"]  # a tiny star drawn as a plus around its centre


def status_stun():
    """Three stars orbiting above the head, 11 px wide; the ones behind are small and dim."""
    out = []
    for f in range(4):
        c = Cell(24)
        for k in range(3):
            a = f * 30 + k * 120 + 90
            x = 11 + 5 * math.cos(math.radians(a))
            y = 11 + 1.5 * math.sin(math.radians(a))
            if math.sin(math.radians(a)) < -0.2:  # behind the head
                c.put(x, y, 0)
            else:
                c.plus(round(x), round(y), [3, 0])
        out.append(c)
    return {"loop": out}


Z_SMALL = ["2222", "..2.", ".2..", "2222"]  # a 4 x 4 z, pale
Z_BIG = ["11111", "...1.", "..1..", ".1...", "11111"]  # deeper blue, so it holds on light ground


def status_sleep():
    out = []
    for f in range(3):
        c = Cell(24)
        c.grid(Z_SMALL, 12 + f, 13 - 2 * f)
        if f >= 1:
            c.grid(Z_BIG, 14 + f, 9 - 2 * f)
        out.append(c)
    return {"loop": out}


def status_burn():
    out = []
    tongues = [((6, 14), (16, 11), (11, 8)), ((7, 13), (15, 12), (10, 7)), ((6, 12), (16, 13), (12, 8))]
    for f in range(3):
        c = Cell(24)
        for i, (x, y) in enumerate(tongues[f]):
            c.grid(["2", "3", "1"] if (i + f) % 2 else ["3", "2", "1"], x, y)
            c.put(x + (1 if i % 2 else -1), y + 2, 1)
        out.append(c)
    return {"loop": out}


def status_poison():
    out = []
    spots = [(7, 15), (15, 11), (11, 7)]
    for f in range(3):
        c = Cell(24)
        for i, (x, y) in enumerate(spots):
            yy = y - ((f + i) % 3) * 2
            c.grid(["23", "12"], x, yy)
        out.append(c)
    return {"loop": out}


def status_freeze():
    out = []
    for glint in (0, 1):
        c = Cell(32)
        for x, h in ((8, 4), (11, 2), (20, 3), (23, 5)):
            for k in range(h):
                c.put(x, 26 - k, 2 if k < h - 1 else 3)
        c.grid(["1111111111111111111"], 6, 27)
        c.put(9 if glint else 22, 21 if glint else 22, 3)
        out.append(c)
    return {"loop": out}


def status_shield():
    out = []
    for f in range(4):
        c = Cell(32)
        for a in range(0, 360, 12):
            x = 15 + 11 * math.cos(math.radians(a))
            y = 16 - 13 * math.sin(math.radians(a))
            if y > 27:
                continue
            bright = abs(((a - f * 90) + 180) % 360 - 180) < 30
            c.put(x, y, 3 if bright else (0 if (a // 12) % 2 else 2))  # dark and pale dots
        out.append(c)
    return {"loop": out}


# ============================================================================== death, support
def poof_smoke():
    out = []
    plans = [
        [(15, 20, 2.0)],
        [(13, 20, 2.6), (18, 19, 2.2), (15, 16, 2.0)],
        [(11, 19, 3.0), (19, 18, 2.8), (15, 14, 2.6), (15, 22, 2.2)],
        [(10, 17, 2.8), (20, 16, 2.6), (15, 11, 2.4), (15, 21, 2.0)],
        [(9, 15, 2.0), (21, 14, 2.0), (15, 9, 1.8)],
        [(9, 13, 1.0), (21, 12, 1.0), (15, 7, 1.0)],
    ]
    for i, plan in enumerate(plans):
        c = Cell(32)
        for x, y, r in plan:
            if i < 4:
                c.blob(x, y, r, light=3, mid=2, dark=1)
            elif i == 4:  # thinning: a dark rim around a pale heart
                c.disk(x, y, r, 0)
                c.put(x, y, 2)
            else:
                c.disk(x, y, r, 0)
        out.append(c)
    return {"play": out}


def soul_wisp():
    out = []
    for i, y in enumerate((18, 15, 12, 9, 6, 4)):
        c = Cell(24)
        fade = max(0, 3 - i // 2)
        c.grid([".3.", "323", "323", ".2.", ".1."][: 5 - i // 2], 10 + (i % 2), y)
        if i >= 4:
            c.g[c.g > fade] = fade
        out.append(c)
    return {"play": out}


def bone_crumble():
    """A skull and three bones dropping from the body and scattering on the ground. Bones are
    light with dark ends, so they read on light and dark ground alike."""
    pieces = [  # (rows, start x, start y, drift x per frame)
        (["333", "303", "030"], 14, 12, 0),   # skull: dark eye holes and jaw
        (["0330"], 9, 16, -1),                # bones
        (["0", "3", "3", "0"], 20, 14, 1),
        (["0330"], 15, 19, 1),
    ]
    out = []
    for f in range(5):
        c = Cell(32)
        for i, (rows, x, y, dx) in enumerate(pieces):
            h = len(rows)
            yy = min(y + f * (3 + i % 2), 27 - h + 1)
            c.grid(rows, x + dx * f, yy)
        if f >= 3:
            c.grid(["0.0...0..0"], 10, 27)  # chips on the ground
        out.append(c)
    return {"play": out}


def heal_sparkle():
    out = []
    spots = [(7, 16), (15, 13), (11, 9), (9, 5)]
    for f in range(5):
        c = Cell(24)
        for i, (x, y) in enumerate(spots):
            k = f - i
            if 0 <= k <= 2:
                c.plus(x, y - k, [3, 2] if k < 2 else [2])
        out.append(c)
    return {"play": out}


def chevrons(up: bool):
    out = []
    for f in range(4):
        c = Cell(24)
        for x, base in ((6, 16), (16, 14)):
            y = base - 2 * f if up else base - 8 + 2 * f
            rows = [".3.", "0.0"] if up else ["2.2", ".3."]
            c.grid(rows, x, y)
            if f % 2 == 0:  # a second chevron trails the first on alternate frames
                c.grid(rows, x, y + (3 if up else -3))
        out.append(c)
    return {"play": out}


def sound_rings():
    """A howl or roar: arcs widening ahead of the mouth (facing e), light with dark ends."""
    out = []
    for radii in ((2,), (2, 4), (4, 6), (6,)):
        c = Cell(16)
        for r in radii:
            c.ring(2, 7, r, 3 if r == radii[0] else 2, keep=lambda a: a < 50 or a > 310)
            x, y = polar(2, 7, r, 55); c.put(x, y, 0)
            x, y = polar(2, 7, r, 305); c.put(x, y, 0)
        out.append(c)
    return {"play": out}


# ============================================================================== boss (Phase 9)
def ground_ellipse(c: Cell, cx, cy, rx, ry, s, keep=lambda a: True) -> None:
    """A 1 px ellipse along the ground (rx wide, ry deep), with gaps where keep(angle) is false."""
    for k in range(int(8 * rx) + 8):
        a = 360 * k / (8 * rx + 8)
        if keep(a):
            x, y = cx + rx * math.cos(math.radians(a)), cy - ry * math.sin(math.radians(a))
            c.put(x, y, s, over=False)


def shockwave():
    """A slam's ring of dust racing out along the ground, thinning as it spreads."""
    cx, cy = 23, 24
    out = []
    for i, (rx, s, gap) in enumerate(((5, 3, 0), (9, 3, 0), (13, 2, 18), (17, 1, 28), (20, 0, 40))):
        c = Cell(48)
        ground_ellipse(c, cx, cy, rx, rx / 3, s, keep=lambda a, g=gap: g == 0 or int(a) % 60 > g)
        ground_ellipse(c, cx, cy, rx - 1, (rx - 1) / 3, 0 if i < 2 else max(s - 1, 0),  # dark dust
                       keep=lambda a, g=gap: int(a) % 45 > 20 + g // 2)       # reads on light ground
        for a in range(10 + i * 7, 360, 40):  # dust thrown up off the ring
            x, y = cx + (rx + 1) * math.cos(math.radians(a)), cy - (rx + 1) / 3 * math.sin(math.radians(a)) - 2
            c.put(x, y, 0, over=False)
        out.append(c)
    return {"play": out}


def rock_shard():
    """A spinning shard of stone (facing e), a dust trail behind it; impact: rock_shard_impact."""
    a = [".23.", "2332", "1221", ".11."]
    b = [".12..", "12332", ".1221", "..1.."]
    out = []
    for rows in (a, b):
        c = Cell(16); c.grid(rows, 7, 5); c.put(4, 7, 0); c.put(3, 8, 0); c.put(5, 6, 1)
        out.append(c)
    impact = []
    for i, r in enumerate((1.5, 3, 5, 6)):
        c = Cell(24)
        for k, ang in enumerate(range(0, 360, 60)):
            x, y = polar(11, 11, r + (k % 2), ang + i * 15)
            c.put(x, y, (0 if k % 2 else 3) if i < 2 else (1 if k % 2 else 0))  # dark chips read on light ground
        if i < 2:
            c.disk(11, 11, 1.2 - 0.6 * i, 3)
        impact.append(c)
    c = Cell(24)  # the last motes settle
    for ang in range(30, 360, 120):
        x, y = polar(11, 12, 7, ang); c.put(x, y, 0)
    impact.append(c)
    return {"travel": out, "impact": impact}


def summon_circle():
    """A rune ring on the ground where minions rise: two ellipses and four marks that turn."""
    cx, cy = 23, 24
    out = []
    for i in range(3):
        c = Cell(48)
        ground_ellipse(c, cx, cy, 15, 5, 2, keep=lambda a: int(a) % 30 > 4)
        ground_ellipse(c, cx, cy, 10, 3.3, 1)
        for k in range(4):
            ang = math.radians(k * 90 + i * 30)
            x, y = cx + 12.5 * math.cos(ang), cy - 4.2 * math.sin(ang)
            c.put(x, y, 3); c.put(x, y - 1, 3); c.put(x + 1, y - 1, 2)
        c.put(cx, cy - 2 - i, 3); c.put(cx, cy - 3 - i, 2)
        out.append(c)
    return {"loop": out}


def falling_rock():
    """A rock that drops onto its landing point (the pivot) and shatters into dust."""
    rock = [".122.", "12332", "12221", ".111."]
    out = []
    for y, shadow in ((3, 2), (10, 3), (18, 4)):
        c = Cell(32); c.grid(rock, 13, y)
        ground_ellipse(c, 15, 27, shadow, 1, 0)
        out.append(c)
    for i, r in enumerate((3, 6, 8)):
        c = Cell(32)
        for k, ang in enumerate(range(15, 180, 30)):
            x, y = polar(15, 26, r + (k % 2), ang)
            c.put(x, y, 3 if i == 0 else (1 if k % 2 else 0))
        ground_ellipse(c, 15, 27, r + 2, 1.2, 2 if i < 2 else 0, keep=lambda a: int(a) % 40 > 12)
        if i == 0:
            c.grid(["232", "121"], 14, 24)
        out.append(c)
    return {"play": out}


# ============================================================================== the library
def fx(name, ramp, cell, pivot, anims, art, *, layer="above", space="world", attach=None,
       rotate=False, tints=None, notes=""):
    return {"name": name, "ramp": ramp, "cell": cell, "pivot": list(pivot), "layer": layer,
            "space": space, **({"attach": attach} if attach else {}), "rotate": rotate,
            **({"tints": list(tints)} if tints else {}), "anims": anims, "notes": notes,
            "_art": art}


def library():
    sm = smears()
    one = {"play": {"frames_ms": [60], "loop": False}}
    return [
        fx("spark_small", "impact", 16, (7, 7), {"play": {"frames_ms": [40, 40, 50, 60], "loop": False}},
           spark_small(), rotate=True, notes="A hit spark about 9 px across: slashes, blocks, arrows."),
        fx("impact_big", "impact", 32, (15, 20), {"play": {"frames_ms": [40, 50, 50, 60, 60, 70],
                                                          "loop": False}},
           impact_big(), notes="A heavy slam on the ground: 17 px star, ring, dust along the ground."),
        fx("dust_puff", "impact", 16, (7, 11), {"play": {"frames_ms": [50, 60, 60, 70], "loop": False}},
           dust_puff(), layer="below", notes="Dust kicked up at a foot: rolls, landings, skids."),
        fx("smear_arc", "swing", 32, (15, 27), one, sm["smear_arc"], space="follow", rotate=True,
           notes="A slash smear in character coordinates (pivot = the character pivot)."),
        fx("smear_vertical", "swing", 32, (15, 27), one, sm["smear_vertical"], space="follow",
           rotate=True, notes="An overhead smear in character coordinates."),
        fx("smear_thrust", "swing", 32, (15, 27), one, sm["smear_thrust"], space="follow",
           rotate=True, notes="Thrust streaks in character coordinates."),
        fx("impact", "arcane", 24, (11, 11), {"play": {"frames_ms": [40, 50, 50, 60, 70], "loop": False}},
           impact_elemental(), tints=ELEMENTS, notes="One elemental impact per element: impact_fire..."),
        fx("arrow", "impact", 16, (8, 7), {"travel": {"frames_ms": [80, 80], "loop": True},
                                           "impact": {"frames_ms": [40, 50, 60, 70], "loop": False}},
           arrow(), rotate=True, notes="Spawned at the bow's nock; travel points east."),
        fx("fireball", "fire", 16, (9, 7), {"travel": {"frames_ms": [60, 60, 60], "loop": True}}, fireball(),
           rotate=True, notes="The draft fireball from style/examples, three flickers; its impact "
                              "is a separate 24 px cell (fireball_impact)."),
        fx("ice_shard", "ice", 16, (8, 7), {"travel": {"frames_ms": [70, 70], "loop": True}}, ice_shard(),
           rotate=True, notes="A crystal with a running glint; impact in ice_shard_impact."),
        fx("poison_glob", "poison", 16, (9, 7), {"travel": {"frames_ms": [70, 70, 70], "loop": True}},
           poison_glob(), rotate=True, notes="A wobbling glob with drips; impact in poison_glob_impact."),
        fx("arcane_orb", "arcane", 16, (8, 7), {"travel": {"frames_ms": [60, 60, 60], "loop": True}},
           arcane_orb(), rotate=True, notes="An orb with an orbiting mote; impact in arcane_orb_impact."),
        fx("gather_glow", "arcane", 16, (7, 7), {"loop": {"frames_ms": [80, 80, 80], "loop": True}},
           gather_glow(), space="follow", attach="hand_near", tints=("fire", "ice", "poison", "arcane", "holy"),
           notes="Motes gathering at the hand while a spell charges; one tint per element."),
        fx("status_stun", "holy", 24, (11, 15), {"loop": {"frames_ms": [120, 120, 120, 120], "loop": True}},
           status_stun(), space="follow", attach="head", notes="Stars orbiting 11 px wide above the head."),
        fx("status_sleep", "ice", 24, (11, 17), {"loop": {"frames_ms": [220, 220, 220], "loop": True}},
           status_sleep(), space="follow", attach="head", notes="Z's rising from the head."),
        fx("status_burn", "fire", 24, (11, 18), {"loop": {"frames_ms": [100, 100, 100], "loop": True}},
           status_burn(), space="follow", attach="torso", notes="Small flames licking the body."),
        fx("status_poison", "poison", 24, (11, 18), {"loop": {"frames_ms": [140, 140, 140], "loop": True}},
           status_poison(), space="follow", attach="torso", notes="Bubbles rising off the body."),
        fx("status_freeze", "ice", 32, (15, 27), {"loop": {"frames_ms": [200, 200], "loop": True}},
           status_freeze(), space="follow", notes="Ice spikes around the feet; a glint."),
        fx("status_shield", "holy", 32, (15, 27), {"loop": {"frames_ms": [100, 100, 100, 100], "loop": True}},
           status_shield(), space="follow", notes="A dotted bubble around the body with a running glint."),
        fx("poof_smoke", "impact", 32, (15, 27), {"play": {"frames_ms": [60, 70, 80, 90, 100, 110],
                                                           "loop": False}},
           poof_smoke(), notes="Death poof: a smoke puff where the body was."),
        fx("soul_wisp", "ice", 24, (11, 21), {"play": {"frames_ms": [90, 90, 90, 90, 90, 90], "loop": False}},
           soul_wisp(), notes="A wisp rising from a fallen body."),
        fx("bone_crumble", "impact", 32, (15, 27), {"play": {"frames_ms": [70, 70, 70, 80, 90],
                                                             "loop": False}},
           bone_crumble(), notes="Bones falling apart and scattering (skeletons)."),
        fx("sound_rings", "impact", 16, (2, 7), {"play": {"frames_ms": [80, 80, 80, 80], "loop": False}},
           sound_rings(), rotate=True, notes="A howl or roar: arcs widening ahead of the mouth."),
        fx("heal_sparkle", "poison", 24, (11, 21), {"play": {"frames_ms": [80, 80, 80, 80, 80],
                                                             "loop": False}},
           heal_sparkle(), space="follow", attach="torso", notes="Green sparkles rising: healing."),
        fx("buff_up", "holy", 24, (11, 21), {"play": {"frames_ms": [90, 90, 90, 90], "loop": False}},
           chevrons(True), space="follow", attach="torso", notes="Chevrons rising: a buff."),
        fx("debuff_down", "shadow", 24, (11, 21), {"play": {"frames_ms": [90, 90, 90, 90], "loop": False}},
           chevrons(False), space="follow", attach="torso", notes="Chevrons sinking: a debuff."),
        fx("shockwave", "impact", 48, (23, 24), {"play": {"frames_ms": [50, 60, 60, 70, 80], "loop": False}},
           shockwave(), layer="below", notes="A slam's dust ring racing out along the ground (bosses)."),
        fx("rock_shard", "impact", 16, (8, 7), {"travel": {"frames_ms": [70, 70], "loop": True}},
           rock_shard(), rotate=True, notes="A spinning stone shard; the Stone Warden's ring and fan. "
                                            "Impact in rock_shard_impact."),
        fx("summon_circle", "ice", 48, (23, 24), {"loop": {"frames_ms": [120, 120, 120], "loop": True}},
           summon_circle(), layer="below", notes="A rune ring on the ground where minions rise."),
        fx("falling_rock", "impact", 32, (15, 27), {"play": {"frames_ms": [60, 60, 60, 60, 70, 80],
                                                             "loop": False}},
           falling_rock(), notes="A rock falling onto its pivot and shattering (a boss's rain)."),
    ]


def projectile_impacts(entries):
    """Projectiles' impacts are 24 px cells, so they are their own FX: <name>_impact."""
    out = []
    for e in entries:
        art = e["_art"]
        if e["name"] in ("fireball", "ice_shard", "poison_glob", "arcane_orb", "rock_shard"):
            out.append(fx(f"{e['name']}_impact", e["ramp"], 24, (11, 11),
                          {"play": {"frames_ms": [40, 50, 50, 60, 70], "loop": False}},
                          {"play": art["impact"]}, rotate=True,
                          notes=f"Where a {e['name']} lands."))
            art.pop("impact")
    return out


def paint(codes: np.ndarray, ramp: list[str]) -> np.ndarray:
    out = np.zeros((*codes.shape, 4), np.uint8)
    for i, c in enumerate(ramp):
        out[codes == i] = (*parse_hex(c), 255)
    return out


def main() -> None:
    entries = library()
    entries += projectile_impacts(entries)
    for e in entries:
        folder = FX_DIR / e["name"]
        folder.mkdir(parents=True, exist_ok=True)
        art = e.pop("_art")
        ramp = STYLE.raw["fx_ramps"][e["ramp"]]
        for anim, cells in art.items():
            assert len(cells) == len(e["anims"][anim]["frames_ms"]), (e["name"], anim)
            sheet = np.concatenate([paint(c.g, ramp) for c in cells], axis=1)
            save_rgba(folder / f"{anim}.png", sheet)
        (folder / "fx.yaml").write_text(yaml.safe_dump(e, sort_keys=False, width=100))
    print(f"wrote {len(entries)} FX")


if __name__ == "__main__":
    main()
