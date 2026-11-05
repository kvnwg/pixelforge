"""Validator rules (QUALITY.md section 1). Errors block a build; warnings must be read.

Every finding says which character, animation, direction, frame and pixels failed, and why.
Thresholds come from style.json `validator` (calibrated so the anchor itself passes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .color import parse_hex, to_hex
from .compose import EMPTY, OUTLINE, Composer, Frame
from .parts import RIGID_SHEET, Library, Part
from .sheet import Sheet, SheetError, mirror
from .style import Style

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
        self.change_budget = float(v.get("change_budget", 0.35))
        self.area_change_max = float(v.get("area_change_max", 0.15))
        self.drift = v.get("pivot_drift_px", {"s": 1, "n": 1, "e": 2, "w": 2})
        self.motion_anims = set(v.get("motion_checked_anims", ["idle", "walk"]))
        size = composer.rig.size
        self.pivot = size.pivot
        self.bounds = size.safe_bounds
        self.outline_rgb = self.style.outline.rgb
        self.shadow_alpha = self.style.shadow.alpha

    # ------------------------------------------------------------------ per frame
    def allowed_colors(self, frame: Frame) -> set[tuple[int, int, int]]:
        allowed = {self.outline_rgb}
        for mapping in self.c.maps.values():
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
        opaque = alpha == 255
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
        # E4 closed outline
        up, down, left, right = _neighbors4(sil)
        touching = ~opaque & (up | down | left | right)
        rows = np.flatnonzero((sil | is_outline).any(axis=1))
        if rows.size:
            cut = int(rows[-1]) - (self.style.outline.sole_rows - 1)
            yy = np.arange(size)[:, None]
            soles = touching & up & ~down & ~left & ~right & (yy >= cut)
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
        p = np.pad(opaque, 1)
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
            # E6 baseline
            if not ({"airborne", "lying"} & f.flags) and int(ys.max()) != self.pivot[1]:
                out.append(Finding("error", "E6", where, f"lowest silhouette row is {int(ys.max())}, "
                                                         f"not the baseline {self.pivot[1]}",
                                   hint="legs drawn too short or too long, or the frame should be "
                                        "flagged airborne or lying"))
            # E7 pivot drift
            if f.anim in self.c.anims and self._base_anim(f) in self.motion_anims \
                    and "displaced" not in f.flags:
                center = (int(xs.min()) + int(xs.max())) / 2
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
                               "art too close to the canvas edge (west mirroring moves x to 30 - x)"))
        # E11 color count
        n_colors = len({tuple(c) for c in img[opaque][:, :3]})
        limit = self.style.constraints.max_colors_per_frame
        if n_colors > limit:
            out.append(Finding("error", "E11", where, f"{n_colors} colors, more than {limit}"))
        if f.mirrored_from is None:
            out += self._singletons(f, sil, where)
            out += self._flat_areas(f, where)
        for layer in f.layers:
            if layer.dropped:
                out.append(Finding("error", "E8", where, f"{layer.part.id}: {layer.dropped} pixels "
                                                         "moved off the canvas", hint="an anchor or "
                                                                                      "origin is wrong"))
        return out

    def _base_anim(self, f: Frame) -> str:
        return f.source[0]

    def _singletons(self, f: Frame, sil: np.ndarray, where: str) -> list[Finding]:
        img = f.sprite
        allowed = np.zeros_like(sil)
        for i, layer in enumerate(f.layers):
            if layer.slot == "eyes":
                allowed |= f.owner == i
            for x, y in layer.part.allow_singletons.get(f.direction, ()):
                x2, y2 = x + layer.offset[0], y + layer.offset[1]
                if 0 <= x2 < img.shape[1] and 0 <= y2 < img.shape[0]:
                    allowed[y2, x2] = True
        key = img[..., 0].astype(np.int32) << 16 | img[..., 1].astype(np.int32) << 8 | img[..., 2]
        key = np.where(sil, key, -1)
        up, down, left, right = (np.pad(key, 1, constant_values=-2)[s] for s in (
            (slice(None, -2), slice(1, -1)), (slice(2, None), slice(1, -1)),
            (slice(1, -1), slice(None, -2)), (slice(1, -1), slice(2, None))))
        lonely = sil & ~allowed & (up != key) & (down != key) & (left != key) & (right != key)
        out = []
        for value in np.unique(key[lonely]):
            pts = lonely & (key == value)
            if pts.sum() > self.singletons_max:
                out.append(Finding("warning", "W3", where,
                                   f"{int(pts.sum())} isolated pixels of #{int(value):06x} "
                                   f"(more than {self.singletons_max})", _px(pts),
                                   "noisy one-pixel clusters; merge them into neighbors"))
        return out

    def _flat_areas(self, f: Frame, where: str) -> list[Finding]:
        img, owner = f.sprite, f.owner
        h, w = owner.shape
        seen = np.zeros((h, w), bool)
        out = []
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
                if len(comp) > self.flat_area_max:
                    out.append(Finding("warning", "W5", where,
                                       f"{material} uses {to_hex(color)} over {len(comp)} connected "
                                       f"pixels (more than {self.flat_area_max})", tuple(comp[:1]),
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
                for l in f.layers if l.slot in HEAD_SLOTS and l.image[..., 3].any()]
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
                both = (a.sprite[..., 3] == 255) | (b.sprite[..., 3] == 255)
                changed = both & np.any(a.sprite != b.sprite, axis=-1)
                base = max(int((a.sprite[..., 3] == 255).sum()), 1)
                if changed.sum() / base > self.change_budget:
                    out.append(Finding("warning", "W2", tag, f"{int(changed.sum())} of {base} pixels "
                                                             f"changed ({changed.sum() / base:.0%})",
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

    def _jitter(self, a: Frame, b: Frame, tag: str) -> list[Finding]:
        out = []
        rig = self.c.rig
        da, db = a.mirrored_from or a.direction, b.mirrored_from or b.direction
        try:
            pa = set(rig.planted(*a.source[:1], da, a.source[1]))
            pb = set(rig.planted(*b.source[:1], db, b.source[1]))
        except Exception:
            return out
        for foot in sorted(pa & pb):
            (xa, ya) = rig.anchor(a.source[0], da, a.source[1], foot)
            (xb, yb) = rig.anchor(b.source[0], db, b.source[1], foot)
            if a.mirrored_from:
                xa, xb = 2 * self.pivot[0] - xa, 2 * self.pivot[0] - xb
            if (xa, ya) != (xb, yb):
                out.append(Finding("warning", "W1", tag, f"planted {foot} moved from ({xa},{ya}) to "
                                                         f"({xb},{yb})", hint="planted feet must "
                                                                              "not slide"))
                continue
            win = (slice(ya - 1, ya + 1), slice(xa - 1, xa + 2))
            diff = np.any(a.image[win] != b.image[win], axis=-1)
            if diff.any():
                pts = tuple((int(x) + xa - 1, int(y) + ya - 1) for y, x in np.argwhere(diff))
                out.append(Finding("warning", "W1", tag, f"planted {foot} changed", pts,
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
