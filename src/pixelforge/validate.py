"""Validator rules (QUALITY.md section 1). Errors block a build; warnings must be read.

Every finding says which character, animation, direction, frame and pixels failed, and why.
Thresholds come from style.json `validator` (calibrated so the anchor itself passes).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from .color import parse_hex, to_hex
from .compose import EMPTY, OUTLINE, SMEAR, Composer, Frame
from .parts import RIGID_SHEET, Library, Part
from .sheet import Sheet, SheetError, mirror
from .style import Style

LOWER_SLOTS = ("body", "legs_wear", "feet")
HELD_SLOTS = ("held_near", "held_near_trim", "held_far")
HEAD_SLOTS = ("body", "hair_front", "hair_back", "hair_locks", "headwear", "headwear_trim", "eyes")


@dataclass(frozen=True)
class Finding:
    level: str  # "error" | "warning"
    rule: str  # "E4", "W3", ...
    where: str  # "anchor_girl idle s 0", a part id or a file
    message: str
    pixels: tuple[tuple[int, int], ...] = ()
    hint: str = ""

    def __str__(self) -> str:
        px = ""
        if self.pixels:
            shown = ", ".join(f"({x},{y})" for x, y in self.pixels[:8])
            px = f" at {shown}" + (f" and {len(self.pixels) - 8} more" if len(self.pixels) > 8 else "")
        hint = f"\n      likely cause: {self.hint}" if self.hint else ""
        return f"{self.level.upper():7} {self.rule:4} {self.where}: {self.message}{px}{hint}"


def _px(mask: np.ndarray) -> tuple[tuple[int, int], ...]:
    return tuple((int(x), int(y)) for y, x in np.argwhere(mask))


def _count_components(key: np.ndarray) -> int:
    """4-connected regions of equal key (keys below 0 are empty)."""
    h, w = key.shape
    seen = key < 0
    count = 0
    for y0, x0 in np.argwhere(~seen):
        if seen[y0, x0]:
            continue
        count += 1
        value, stack = key[y0, x0], [(y0, x0)]
        seen[y0, x0] = True
        while stack:
            y, x = stack.pop()
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and key[ny, nx] == value:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
    return count


def _neighbors4(mask: np.ndarray, fill: bool = False) -> tuple[np.ndarray, ...]:
    """(up, down, left, right): the value at (x, y-1), (x, y+1), (x-1, y), (x+1, y)."""
    p = np.pad(mask, 1, constant_values=fill)
    return p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]


class Validator:
    def __init__(self, composer: Composer):
        self.c = composer
        self.style: Style = composer.style
        v = self.style.raw.get("validator", {})
        self.singletons_max = int(v.get("singletons_max", 3))
        self.flat_area_max = int(v.get("flat_area_max", 12))
        self.flat_share_max = float(v.get("flat_share_max", 1.0))
        self.change_budget = float(v.get("change_budget", 0.35))
        self.area_change_max = float(v.get("area_change_max", 0.15))
        self.busy_singletons = float(v.get("busy_singletons_share", 0.005))
        self.busy_cluster_min = float(v.get("busy_cluster_min_px", 3))
        self.drift = v.get("pivot_drift_px", {"s": 1, "n": 1, "e": 2, "w": 2})
        rig_v = composer.rig_spec.get("validator", {})
        self.motion_anims = set(rig_v.get("motion_checked_anims",
                                          v.get("motion_checked_anims", ["idle", "walk"])))
        # E10 measures the head from these layers; a rig whose body layer also holds raised arms
        # names the layers that move with the head alone (the ogre's topknot)
        self.head_slots = tuple(rig_v.get("head_slots", HEAD_SLOTS))
        size = composer.rig.size
        self.pivot = size.pivot
        self.bounds = size.safe_bounds
        self.outline_rgb = self.style.outline.rgb
        self.shadow_alpha = self.style.shadow.alpha

    # ------------------------------------------------------------------ per frame
    def allowed_colors(self, frame: Frame) -> set[tuple[int, int, int]]:
        allowed = {self.outline_rgb}
        for mapping in [*self.c.maps.values(), *self.c.slot_maps.values()]:
            allowed.update(mapping.values())
        anim = self.c.anims[frame.anim]
        if anim.effect == "close_eyes":
            allowed.add(self.c.lid)
        if "flash" in frame.flags:
            allowed.add(self.c.flash_rgb)
        return allowed

    def frame(self, f: Frame) -> list[Finding]:
        out: list[Finding] = []
        where = f.label
        img = f.image
        size = self.c.size
        if img.shape != (size, size, 4):
            return [Finding("error", "E1", where, f"frame is {img.shape[1]} x {img.shape[0]}, "
                                                  f"not {size} x {size}")]
        alpha = img[..., 3]
        smear = f.owner == SMEAR
        opaque = (alpha == 255) & ~smear
        is_outline = opaque & np.all(img[..., :3] == np.asarray(self.outline_rgb, np.uint8), axis=-1)
        sil = opaque & ~is_outline

        # E2 palette
        allowed = self.allowed_colors(f)
        rgb = img[..., :3]
        ok = np.zeros_like(opaque)
        for color in allowed:
            ok |= np.all(rgb == np.asarray(color, np.uint8), axis=-1)
        bad = opaque & ~ok
        if bad.any():
            colors = sorted({to_hex(img[y, x]) for x, y in _px(bad)})
            out.append(Finding("error", "E2", where, f"off-palette colors {colors}", _px(bad),
                               "a part uses a color outside its material's base ramp (see E13), "
                               "or the recipe's preset is wrong"))
        # E3 alpha
        partial = (alpha != 0) & (alpha != 255)
        shadow_ok = partial & (alpha == self.shadow_alpha) & np.all(
            rgb == np.asarray(self.outline_rgb, np.uint8), axis=-1)
        if (partial & ~shadow_ok).any():
            out.append(Finding("error", "E3", where, "semi-transparent pixels that are not ground "
                                                     "shadow", _px(partial & ~shadow_ok),
                               "antialiasing or a soft brush; alpha must be 0 or 255"))
        # E4 closed outline (a swing trail drawn over the body covers it: not a gap)
        up, down, left, right = _neighbors4(sil)
        touching = ~opaque & ~smear & (up | down | left | right)
        rows = np.flatnonzero((sil | is_outline).any(axis=1))
        if rows.size:
            base = self.pivot[1]  # grounded frames measure open soles from the baseline
            yy = np.arange(size)[:, None]
            band = (yy >= base - (self.style.outline.sole_rows - 1)) & (yy <= base + 1)
            soles = touching & up & ~down & ~left & ~right & band
            if "airborne" in f.flags:
                soles = np.zeros_like(soles)
            gaps = touching & ~soles
            edge = sil.copy()
            edge[1:-1, 1:-1] = False
            if gaps.any() or edge.any():
                out.append(Finding("error", "E4", where, "outline has gaps (silhouette touches "
                                                         "transparent or shadow pixels)",
                                   _px(gaps | edge),
                                   "an effect or a layer was applied after outlining, or art "
                                   "touches the canvas edge"))
        # E5 floating pixels
        p = np.pad(opaque | smear, 1)
        neigh = sum(np.roll(np.roll(p, dy, 0), dx, 1)[1:-1, 1:-1].astype(int)
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
        floating = opaque & (neigh == 0)
        if floating.any():
            out.append(Finding("error", "E5", where, "floating pixels with no opaque neighbor",
                               _px(floating), "a stray pixel in a part, or a part shifted away "
                                              "from the body"))
        if sil.any():
            ys = np.flatnonzero(sil.any(axis=1))
            xs = np.flatnonzero(sil.any(axis=0))
            # E6 baseline: the feet (body, legs wear, boots) rest on it; held items may hang lower
            # the feet stand on the baseline even where a robe covers them: read the leg layers
            feet = np.zeros_like(sil)
            for layer in f.layers:
                if layer.slot in LOWER_SLOTS:
                    feet |= layer.image[..., 3] == 255
            fys = np.flatnonzero(feet.any(axis=1)) if feet.any() else ys
            if not ({"airborne", "lying"} & f.flags) and int(fys.max()) != self.pivot[1]:
                out.append(Finding("error", "E6", where, f"lowest foot row is {int(fys.max())}, "
                                                         f"not the baseline {self.pivot[1]}",
                                   hint="legs drawn too short or too long, or the frame should be "
                                        "flagged airborne or lying"))
            # E7 pivot drift
            if f.anim in self.c.anims and self._base_anim(f) in self.motion_anims \
                    and "displaced" not in f.flags:
                body = sil & ~f.slot_mask(*HELD_SLOTS)  # a staff held out front is not drift
                bxs = np.flatnonzero(body.any(axis=0)) if body.any() else xs
                center = (int(bxs.min()) + int(bxs.max())) / 2
                limit = self.drift.get(f.direction, 2)
                if abs(center - self.pivot[0]) > limit:
                    out.append(Finding("error", "E7", where,
                                       f"silhouette center x {center:g} drifts more than {limit} px "
                                       f"from the pivot x {self.pivot[0]}",
                                       hint="the whole sprite shifted sideways; only the planned "
                                            "regions should move"))
        # E8 bounds
        x0, y0, x1, y1 = self.bounds
        inside = np.zeros_like(opaque)
        inside[y0:y1 + 1, x0:x1 + 1] = True
        outside = (alpha > 0) & ~inside
        if outside.any():
            out.append(Finding("error", "E8", where, f"pixels outside the safe area x {x0}..{x1}, "
                                                     f"y {y0}..{y1}", _px(outside),
                               "art too close to the canvas edge (west mirroring moves x to "
                               f"{2 * self.c.rig.size.mirror_axis_x} - x)"))
        # E11 color count
        n_colors = len({tuple(c) for c in img[opaque][:, :3]})
        limit = self.style.constraints.max_colors_per_frame
        if n_colors > limit:
            out.append(Finding("error", "E11", where, f"{n_colors} colors, more than {limit}"))
        if f.mirrored_from is None:
            if "flash" not in f.flags:  # the hurt flash speckles light colors on purpose, 1 frame
                out += self._singletons(f, sil, where)
            if self.c.size > self.style.canvas:  # medium, large and huge
                out += self._busy(f, sil, opaque, where)
            if "flash" not in f.flags:  # a flash frame is one flat color on purpose
                out += self._flat_areas(f, where)
        for layer in f.layers:
            if layer.dropped:
                out.append(Finding("error", "E8", where, f"{layer.part.id}: {layer.dropped} pixels "
                                                         "moved off the canvas", hint="an anchor or "
                                                                                      "origin is wrong"))
        return out

    def _base_anim(self, f: Frame) -> str:
        return f.source[0]

    def _lonely(self, f: Frame, sil: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Isolated pixels (no 4-neighbor of the same material and color), not counting eyes and
        allowed singletons; with the (material, color) key of every pixel and the material names."""
        img = f.sprite
        allowed = np.zeros_like(sil)
        for i, layer in enumerate(f.layers):
            if layer.slot == "eyes":
                allowed |= f.owner == i
            per_dir = layer.part.allow_singletons
            if layer.sheet.startswith("pose_"):  # a held item's pose lists its own tips
                per_dir = layer.part.pose_singletons.get(layer.sheet, {})
            for x, y in per_dir.get(f.direction, ()):
                x2, y2 = x + layer.offset[0], y + layer.offset[1]
                if 0 <= x2 < img.shape[1] and 0 <= y2 < img.shape[0]:
                    allowed[y2, x2] = True
        # A shade belongs to a material: leather light and hair mid share a hex in the anchor, so
        # pixels are keyed by (material, color) through the layer that drew them.
        material = np.full(f.owner.shape, -1, np.int64)
        names = sorted({l.part.material for l in f.layers})
        for i, layer in enumerate(f.layers):
            material[f.owner == i] = names.index(layer.part.material)
        rgb = img[..., 0].astype(np.int64) << 16 | img[..., 1].astype(np.int64) << 8 | img[..., 2]
        key = np.where(sil & (material >= 0), material << 24 | rgb, -1)
        up, down, left, right = (np.pad(key, 1, constant_values=-2)[s] for s in (
            (slice(None, -2), slice(1, -1)), (slice(2, None), slice(1, -1)),
            (slice(1, -1), slice(None, -2)), (slice(1, -1), slice(2, None))))
        lonely = sil & ~allowed & (up != key) & (down != key) & (left != key) & (right != key)
        # a swing trail drawn over the body cuts it for a frame or two: what it isolates is
        # occlusion by an effect, not noisy art
        trail = np.pad(f.owner == SMEAR, 1)
        lonely &= ~(trail[:-2, 1:-1] | trail[2:, 1:-1] | trail[1:-1, :-2] | trail[1:-1, 2:])
        return lonely, key, names

    def _singletons(self, f: Frame, sil: np.ndarray, where: str) -> list[Finding]:
        lonely, key, names = self._lonely(f, sil)
        out = []
        for value in np.unique(key[lonely]):
            # counted per part: a few edge pixels each of several parts that cover one another
            # (a sword hanging across a pauldron's rim) are occlusion, not a noisy part
            for owner in np.unique(f.owner[lonely & (key == value)]):
                pts = lonely & (key == value) & (f.owner == owner)
                if pts.sum() > self.singletons_max:
                    name = names[int(value) >> 24]
                    slot = f.layers[int(owner)].slot if owner >= 0 else "outline"
                    out.append(Finding("warning", "W3", where,
                                       f"{int(pts.sum())} isolated {name} pixels of "
                                       f"#{int(value) & 0xFFFFFF:06x} in {slot} (more than "
                                       f"{self.singletons_max})", _px(pts),
                                       "noisy one-pixel clusters; merge them into neighbors"))
        return out

    def _busy(self, f: Frame, sil: np.ndarray, opaque: np.ndarray, where: str) -> list[Finding]:
        """W10: a medium, large or huge sprite whose singletons exceed 0.5% of its silhouette, or
        whose shade clusters average under 3 px, is noisy at its size (QUALITY.md)."""
        lonely, key, _ = self._lonely(f, sil)
        area = int(opaque.sum())
        out = []
        if area and lonely.sum() > self.busy_singletons * area:
            out.append(Finding("warning", "W10", where,
                               f"{int(lonely.sum())} isolated pixels, {lonely.sum() / area:.1%} of "
                               f"the silhouette (over {self.busy_singletons:.1%})", _px(lonely),
                               "a big sprite needs bigger shapes: merge single pixels into their "
                               "neighbors"))
        inside = key >= 0
        clusters = _count_components(key)
        if clusters and inside.sum() / clusters < self.busy_cluster_min:
            out.append(Finding("warning", "W10", where,
                               f"shade clusters average {inside.sum() / clusters:.1f} px (under "
                               f"{self.busy_cluster_min:g})",
                               hint="dithered or speckled shading; use bigger, simpler shade areas"))
        return out

    def _flat_areas(self, f: Frame, where: str) -> list[Finding]:
        img, owner = f.sprite, f.owner
        h, w = owner.shape
        seen = np.zeros((h, w), bool)
        out = []
        totals: dict[str, int] = {}
        for i, layer in enumerate(f.layers):
            totals[layer.part.material] = totals.get(layer.part.material, 0) + int((owner == i).sum())
        for y in range(h):
            for x in range(w):
                i = owner[y, x]
                if i < 0 or seen[y, x]:
                    continue
                material = f.layers[i].part.material
                color = tuple(img[y, x, :3])
                stack, comp = [(x, y)], []
                seen[y, x] = True
                while stack:
                    cx, cy = stack.pop()
                    comp.append((cx, cy))
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx]:
                            j = owner[ny, nx]
                            if j >= 0 and f.layers[j].part.material == material \
                                    and tuple(img[ny, nx, :3]) == color:
                                seen[ny, nx] = True
                                stack.append((nx, ny))
                share = len(comp) / max(totals.get(material, 1), 1)
                if len(comp) > self.flat_area_max and share > self.flat_share_max:
                    out.append(Finding("warning", "W5", where,
                                       f"{material} uses {to_hex(color)} over {len(comp)} connected "
                                       f"pixels ({share:.0%} of the {material}; more than "
                                       f"{self.flat_area_max})", tuple(comp[:1]),
                                       "a flat, unshaded area; add the light or dark shade"))
        return out

    # ------------------------------------------------------------------ per animation
    def head_height(self, f: Frame) -> int | None:
        src_anim, src_index = f.source
        direction = f.mirrored_from or f.direction
        try:
            _, chin = self.c.rig.anchor(src_anim, direction, src_index, "chin")
        except Exception:
            return None
        tops = [int(np.flatnonzero(l.image[..., 3].any(axis=1)).min())
                for l in f.layers if l.slot in self.head_slots and l.image[..., 3].any()]
        if not tops:
            return None
        return chin - min(tops) + 2  # rows from the outline above the head to the chin

    def animation(self, frames: list[Frame], loop: bool) -> list[Finding]:
        out: list[Finding] = []
        if not frames:
            return out
        f0 = frames[0]
        where = f"{f0.character} {f0.anim} {f0.direction}"
        pairs = list(zip(frames, frames[1:]))
        if loop and len(frames) > 1:
            pairs.append((frames[-1], frames[0]))
        motion = self._base_anim(f0) in self.motion_anims
        for a, b in pairs:
            tag = f"{where} {a.index}->{b.index}"
            out += self._jitter(a, b, tag)
            if motion:
                residual, base = self._residual(a, b)
                if residual / base > self.change_budget:
                    out.append(Finding("warning", "W2", tag,
                                       f"{residual} of {base} pixels changed beyond the planned "
                                       f"motion ({residual / base:.0%})",
                                       hint="boiling, or a misaligned layer"))
                sa = self._sil(a).sum()
                sb = self._sil(b).sum()
                if sa and abs(int(sb) - int(sa)) / sa > self.area_change_max:
                    out.append(Finding("warning", "W4", tag, f"silhouette area {sa} -> {sb}"))
        heights = {f.index: self.head_height(f) for f in frames if "squash" not in f.flags}
        values = {h for h in heights.values() if h is not None}
        if len(values) > 1:
            out.append(Finding("error", "E10", where, f"head height changes between frames: "
                                                      f"{heights}", hint="head redrawn smaller or "
                                                                         "taller in some frames"))
        return out

    def _sil(self, f: Frame) -> np.ndarray:
        return (f.sprite[..., 3] == 255) & (f.owner >= 0)

    def _points(self, f: Frame) -> dict:
        try:
            return self.c.rig.points(f.source[0], f.mirrored_from or f.direction, f.source[1])
        except Exception:
            return {}

    def _x(self, f: Frame, x: int) -> int:
        return 2 * self.c.rig.size.mirror_axis_x - x if f.mirrored_from else x

    def _residual(self, a: Frame, b: Frame) -> tuple[int, int]:
        """Pixels that changed beyond the planned motion: the upper body (above the `hip`
        anchor) is moved by the head anchor's delta before comparing; legs compare in place."""
        pa, pb = self._points(a), self._points(b)
        base = max(int((a.sprite[..., 3] == 255).sum()), 1)
        expected = a.sprite.copy()
        if "head" in pa and "head" in pb and "hip" in pa:
            dx = self._x(b, pb["head"][0]) - self._x(a, pa["head"][0])
            dy = pb["head"][1] - pa["head"][1]
            hip = pa["hip"][1]
            upper = a.sprite.copy()
            upper[hip:] = 0
            legs = a.sprite.copy()
            legs[:hip] = 0
            from .sheet import shift
            moved, _ = shift(upper, dx, dy)
            expected = np.where(moved[..., 3:] == 255, moved, legs)
        both = (expected[..., 3] == 255) | (b.sprite[..., 3] == 255)
        changed = both & np.any(expected != b.sprite, axis=-1)
        # Rigid parts only ever translate (by their anchor, a frame late if they lag), so they
        # cannot boil; W2 judges the drawn layers.
        lagging = np.zeros_like(changed)
        for f in (a, b):
            for i, layer in enumerate(f.layers):
                if not layer.part.drawn(f.source[0]):
                    lagging |= f.owner == i
        changed &= ~lagging
        return int(changed.sum()), base

    def _stride(self, a: Frame) -> int:
        """Screen-space x shift of a planted foot from frame a to the next (0 = stays put)."""
        anim = self.c.anims.get(a.source[0])
        strides = (anim.raw.get("stride_px", {}) if anim else {}).get(a.mirrored_from or a.direction)
        if not strides:
            return 0
        step = int(strides[a.source[1] % len(strides)])
        return step if a.mirrored_from else -step

    def _jitter(self, a: Frame, b: Frame, tag: str) -> list[Finding]:
        """A planted foot must not move or change: compare its bottom row (x - 1 to x + 1) in the
        lower-body layers, so a belt or skirt swinging in front of it is not jitter."""
        out = []
        pa, pb = self._points(a), self._points(b)
        if pa.get("view") != pb.get("view"):
            return out  # the body turns between these frames (a spin): its feet pivot on purpose
        stride = self._stride(a)
        for foot in sorted(set(pa.get("planted", [])) & set(pb.get("planted", []))):
            xa, ya = self._x(a, pa[foot][0]), pa[foot][1]
            xb, yb = self._x(b, pb[foot][0]), pb[foot][1]
            if (xb - xa, yb - ya) != (stride, 0):
                out.append(Finding("warning", "W1", tag, f"planted {foot} moved from ({xa},{ya}) "
                                                         f"to ({xb},{yb}); the ground moves "
                                                         f"{stride:+d} px here",
                                   hint="planted feet must stay on the ground: move them only by "
                                        "the walk's stride_px"))
                continue
            lower = LOWER_SLOTS
            la = {l.slot: l.image for l in a.layers if l.slot in lower}
            lb = {l.slot: l.image for l in b.layers if l.slot in lower}
            changed = set()
            for slot in set(la) | set(lb):
                ia = la.get(slot, np.zeros_like(a.image))[ya, xa - 1:xa + 2]
                ib = lb.get(slot, np.zeros_like(b.image))[yb, xb - 1:xb + 2]
                for i in np.flatnonzero(np.any(ia != ib, axis=-1)):
                    changed.add((int(xa - 1 + i), int(ya)))
            if changed:
                out.append(Finding("warning", "W1", tag, f"planted {foot} changed",
                                   tuple(sorted(changed)),
                                   "lock planted foot pixels; move the other leg only"))
        return out

    def mirror(self, east: list[Frame], west: list[Frame]) -> list[Finding]:
        out = []
        axis = self.c.rig.size.mirror_axis_x
        for e, w in zip(east, west):
            m, _ = mirror(e.image, axis)
            if not np.array_equal(m, w.image):
                out.append(Finding("error", "E9", w.label, "west frame is not the mirrored east frame",
                                   hint=f"mirror around x = {axis}, never flip the canvas"))
        return out

    # ------------------------------------------------------------------ recipe and parts
    def size_class(self) -> list[Finding]:
        """E18: every part is drawn on its rig's size class canvas, and the anchors keep inside
        that class's safe bounds (a bigger class is redrawn, never upscaled)."""
        out = []
        rig = self.c.rig
        canvas = rig.size.canvas
        for part in self.c.parts.values():
            if self.c.lib.cell_size(part) != canvas:
                out.append(Finding("error", "E18", f"{self.c.recipe.name} {part.id}",
                                   f"cells are {self.c.lib.cell_size(part)} px; rig {rig.name} is "
                                   f"{rig.size.name} ({canvas} px)",
                                   hint="draw the part for this size class; never upscale"))
        x0, y0, x1, y1 = rig.size.safe_bounds
        for anim, per_dir in rig.anchors.items():
            for d, frames in per_dir.items():
                for i, pts in enumerate(frames):
                    for name, p in pts.items():
                        if isinstance(p, list) and len(p) == 2 and all(isinstance(c, int) for c in p) \
                                and not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1):
                            out.append(Finding("error", "E18", f"{rig.name} {anim} {d} {i}",
                                               f"anchor {name} {tuple(p)} is outside the "
                                               f"{rig.size.name} safe bounds"))
        return out

    def completeness(self, anims: Iterable[str]) -> list[Finding]:
        out = []
        for part in self.c.parts.values():
            for anim in anims:
                adef = self.c.anims[anim]
                if adef.source:
                    continue
                need = RIGID_SHEET if not part.drawn(anim) else anim
                if not part.sheet_path(need).is_file():
                    out.append(Finding("error", "E14", f"{self.c.recipe.name} {part.id}",
                                       f"no {need}.png for animation {anim}",
                                       hint="draw the sheet (pf template) or remove the animation"))
        return out


def validate_part(part: Part, lib: Library, style: Style) -> list[Finding]:
    """E13: every pixel in a part file is from its material's base ramp or the outline color."""
    out = []
    allowed = {parse_hex(c) for c in style.materials[part.material].base} | {style.outline.rgb}
    sheets = sorted(p for p in part.folder.glob("*.png") if not p.stem.endswith("_guide"))
    if not sheets:
        out.append(Finding("error", "E14", part.id, "no sheets"))
    for path in sheets:
        try:
            sheet = Sheet.load(path, lib.cell_size(part), style.drawn_directions)
        except SheetError as e:
            out.append(Finding("error", "E1", part.id, str(e)))
            continue
        img = sheet.image
        alpha = img[..., 3]
        if ((alpha != 0) & (alpha != 255)).any():
            out.append(Finding("error", "E13", f"{part.id} {path.name}", "semi-transparent pixels",
                               _px((alpha != 0) & (alpha != 255))))
        opaque = alpha == 255
        ok = np.zeros_like(opaque)
        for c in allowed:
            ok |= np.all(img[..., :3] == np.asarray(c, np.uint8), axis=-1)
        if (opaque & ~ok).any():
            colors = sorted({to_hex(img[y, x]) for x, y in _px(opaque & ~ok)})
            out.append(Finding("error", "E13", f"{part.id} {path.name}",
                               f"colors outside the {part.material} base ramp: {colors}",
                               _px(opaque & ~ok), "one material per part file"))
    return out


def _near(a: tuple[int, int], b: tuple[int, int], r: int) -> bool:
    return abs(a[0] - b[0]) <= r and abs(a[1] - b[1]) <= r


def resolve_fx(lib, name, element: str = "arcane"):
    from .review import resolve_fx as _resolve
    return _resolve(lib, name, element)


def _combat_checks(self, frames: dict, profile_name: str) -> list[Finding]:
    """E15 hitboxes, E16 events, E17 telegraph, W8 weak tell (COMBAT.md, QUALITY.md)."""
    from .anim import tell_ms
    out: list[Finding] = []
    size = self.c.size
    profile = self.style.raw["combat"]["timing_profiles"][profile_name]
    for (anim, d), fs in frames.items():
        adef = self.c.anims[anim]
        if not adef.combat:
            continue
        where = f"{self.c.recipe.name} {anim} {d}"
        active = adef.flags.get("active", frozenset())
        ranged = adef.event_frame("spawn") is not None  # the projectile carries the hit
        for f in fs:
            if f.index in active and not f.hitboxes and not ranged:
                out.append(Finding("error", "E15", f.label, "active frame without a hitbox",
                                   hint="the held item has no hitbox for this pose (hitboxes.json)"))
            if f.index not in active and f.hitboxes:
                out.append(Finding("error", "E15", f.label, "hitbox outside the active phase"))
            for x, y, w, h in f.hitboxes:
                if x < 0 or y < 0 or x + w > size or y + h > size:
                    out.append(Finding("error", "E15", f.label, f"hitbox {(x, y, w, h)} leaves the canvas"))
        attack = bool(active) or adef.event_frame("hit", "spawn") is not None
        if attack:
            types = {e["type"] for e in adef.events}
            missing = [t for t in ("windup", "recover") if t not in types]
            if not types & {"hit", "spawn"}:
                missing.append("hit or spawn")
            if missing:
                out.append(Finding("error", "E16", where, f"attack lacks events: {missing}"))
        for e in adef.events:
            i = int(e["frame"])
            if not 0 <= i < len(fs):
                out.append(Finding("error", "E16", where, f"event {e['type']} on frame {i} of {len(fs)}"))
                continue
            fxlib = self.fx_library()
            if fxlib is not None and e.get("fx") and resolve_fx(fxlib, e["fx"]) is None:
                out.append(Finding("error", "E16", where, f"event {e['type']} names FX "
                                                          f"{e['fx']!r}, which is not in fx/"))
            point = e.get("point")
            if point is None:
                continue
            f = fs[i]
            xy = f.points.get(point) if isinstance(point, str) else tuple(point)
            if xy is None:
                out.append(Finding("error", "E16", f.label, f"event point {point!r} is not defined",
                                   hint="add it to the rig anchors or the held item's points"))
                continue
            if not (0 <= xy[0] < size and 0 <= xy[1] < size):
                out.append(Finding("error", "E16", f.label, f"event point {point} {xy} is off the canvas"))
            if e["type"] in ("spawn", "vfx"):
                refs = [f.points[k] for k in ("hand_near", "hand_far", "weapon_tip", "bow_nock",
                                              "shield_front", "mouth") if k in f.points]
                emitters = ("foot_near", "foot_far", "head", "torso", "ground", "back",
                            *self.c.rig_spec.get("emitters", ()))  # a boss's core
                if refs and not any(_near(xy, r, 3) for r in refs) and point not in emitters:
                    out.append(Finding("error", "E16", f.label, f"{e['type']} point {xy} is more than "
                                                                f"3 px from a hand or weapon tip"))
        if profile_name in ("enemy", "elite", "boss") and len(fs) == adef.frames:
            tell = tell_ms(adef, [f.duration for f in fs])
            if tell is not None and tell < int(profile["telegraph_min_ms"]):
                out.append(Finding("error", "E17", where, f"tell is {tell} ms, under the {profile_name} "
                                                          f"minimum {profile['telegraph_min_ms']} ms"))
        out += self._hidden_tell(adef, fs, where)
        overlay = adef.raw.get("overlay_fx")
        if overlay and self.fx_library() is not None and resolve_fx(self.fx_library(), overlay) is None:
            out.append(Finding("error", "E16", where, f"overlay FX {overlay!r} is not in fx/"))
        rm = adef.root_motion
        if rm is not None and len(rm) != adef.frames:
            out.append(Finding("error", "E20", where, f"{len(rm)} root motion values for {adef.frames} frames"))
        if attack and ("combat_idle", d) in frames and adef.event_frame("windup") is not None:
            # the tell is the strongest pose of the windup phase (a heavy lifts, then cocks back)
            ref = frames[("combat_idle", d)][0].sprite[..., 3] == 255
            hit = adef.event_frame("hit", "spawn") or len(fs)
            active = sorted(adef.flags.get("active", ()))
            if active:  # a swing frame before the hit is the strike, not the tell
                hit = min(hit, active[0])
            best, change = None, -1.0
            for f in fs[adef.event_frame("windup"):hit]:
                sil = f.sprite[..., 3] == 255
                c = (ref ^ sil).sum() / max((ref | sil).sum(), 1)
                if c > change:
                    best, change = f, c
            if best is not None and change < 0.08:
                out.append(Finding("warning", "W8", best.label, f"windup pose differs from "
                                                                f"combat_idle by {change:.1%} "
                                                                f"(under 8%)",
                                   hint="make the tell a whole-body pose: lean, crouch, raise"))
    return out


def _fx_library(self):
    """The FX library under <root>/fx, loaded once (None when the repo has no FX yet)."""
    if not hasattr(self, "_fxlib"):
        from .fx import FXLibrary, fx_folders
        self._fxlib = FXLibrary(self.c.root, self.style) if fx_folders(self.c.root) else None
    return self._fxlib


def _hidden_tell(self, adef, fs: list, where: str) -> list[Finding]:
    """W9: an FX played during the windup covers more than 15% of the attacker's silhouette."""
    fxlib = self.fx_library()
    if fxlib is None or not adef.phases:
        return []
    out = []
    for e in adef.events:
        i = int(e["frame"])
        if e["type"] not in ("vfx", "spawn") or i >= len(fs) or adef.phases[i] != "windup":
            continue
        name = resolve_fx(fxlib, e.get("fx"))
        point = e.get("point")
        f = fs[i]
        xy = f.points.get(point) if isinstance(point, str) else (tuple(point) if point else None)
        if not name or xy is None:
            continue
        cells, pivot, _ = fxlib.cells(name, None, f.mirrored_from and "w" or f.direction)
        cell = cells[0]
        sil = (f.sprite[..., 3] == 255)
        cover = np.zeros_like(sil)
        x0, y0 = xy[0] - pivot[0], xy[1] - pivot[1]
        h, w = cell.shape[:2]
        for yy in range(h):
            for xx in range(w):
                X, Y = x0 + xx, y0 + yy
                if cell[yy, xx, 3] and 0 <= X < sil.shape[1] and 0 <= Y < sil.shape[0]:
                    cover[Y, X] = True
        share = (cover & sil).sum() / max(sil.sum(), 1)
        if share > 0.15:
            out.append(Finding("warning", "W9", f.label, f"{name} covers {share:.0%} of the "
                                                         f"attacker during the windup",
                               hint="move the FX off the body or play it after the tell"))
    return out


Validator.combat = _combat_checks
Validator.fx_library = _fx_library
Validator._hidden_tell = _hidden_tell


# ------------------------------------------------------------------ the roster (MONSTERS.md section 7)
def is_monster(recipe) -> bool:
    return recipe.path is not None and "monsters" in Path(recipe.path).parts


def _on_pivot(a: np.ndarray, pa: tuple[int, int], b: np.ndarray, pb: tuple[int, int]
              ) -> tuple[np.ndarray, np.ndarray]:
    """Two silhouettes on one canvas, their pivots on the same pixel (a medium ogre beside a
    small goblin stand on the same ground point)."""
    left, top = max(pa[0], pb[0]), max(pa[1], pb[1])
    w = left + max(a.shape[1] - pa[0], b.shape[1] - pb[0])
    h = top + max(a.shape[0] - pa[1], b.shape[0] - pb[1])
    out = []
    for m, (px, py) in ((a, pa), (b, pb)):
        c = np.zeros((h, w), bool)
        x0, y0 = left - px, top - py
        c[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] = m
        out.append(c)
    return out[0], out[1]


def roster_findings(builds: list, threshold: float = 0.85) -> list[Finding]:
    """W7: two different monsters whose combat_idle frame 0 silhouettes overlap by more than
    85% (intersection over union), facing s and e, are too alike: change the shape."""
    out = []
    monsters = [b for b in builds if is_monster(b.recipe)]
    for i, a in enumerate(monsters):
        for b in monsters[i + 1:]:
            fam_a = a.recipe.raw.get("family", a.recipe.name)
            fam_b = b.recipe.raw.get("family", b.recipe.name)
            if fam_a == fam_b or (a.recipe.rig == b.recipe.rig and a.recipe.parts == b.recipe.parts):
                continue  # variants and elites of one family share a shape on purpose
            for d in ("s", "e"):
                fa = a.frames.get(("combat_idle", d)) or a.frames.get(("idle", d))
                fb = b.frames.get(("combat_idle", d)) or b.frames.get(("idle", d))
                if not fa or not fb:
                    continue
                sa, sb = _on_pivot(fa[0].sprite[..., 3] == 255, a.composer.rig.size.pivot,
                                   fb[0].sprite[..., 3] == 255, b.composer.rig.size.pivot)
                iou = (sa & sb).sum() / max((sa | sb).sum(), 1)
                if iou > threshold:
                    out.append(Finding("warning", "W7", f"{a.recipe.name} vs {b.recipe.name} {d}",
                                       f"combat_idle silhouettes overlap {iou:.0%} (over "
                                       f"{threshold:.0%})",
                                       hint="change the shape, not the color: a signature "
                                            "feature, posture or size"))
    return out
