"""Compositing a recipe into finished frames (ARCHITECTURE.md section 9).

For each (animation, direction, frame):
 1. resolve the recipe's parts in z-order, skipping slots hidden by other parts;
 2. take each part's cell: drawn sheets give the frame directly; rigid parts are translated so
    their origin lands on the rig's anchor; parts with `lags` use the previous frame;
 3. recolor each cell from its material's base ramp to the recipe's preset;
 4. stack with binary alpha (outline-colored pixels in parts are hand-placed details);
 5. generate the outline around the combined silhouette (outline.py);
 6. apply effects (closed eyes, flash) and put the ground shadow behind.
West frames are mirrored from finished east frames by the build (build.py).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from .anim import AnimDef, load_anims
from .color import parse_hex
from .effects import close_eyes, flash, over_shadow, shadow_layer
from .outline import outline
from .parts import RIGID_SHEET, Library, Part, PartError
from .recipe import Recipe, RecipeError
from .recolor import preset_ramp, ramp_map, recolor
from .rig import Rig, load_rig
from .sheet import mirror, shift
from .style import Style

EMPTY, OUTLINE = -1, -2


@dataclass
class Layer:
    slot: str
    part: Part
    image: np.ndarray  # recolored cell in canvas coordinates
    offset: tuple[int, int]  # translation applied to a rigid part; (0, 0) for drawn cells
    dropped: int  # opaque pixels pushed off the canvas by that translation


@dataclass
class Frame:
    character: str
    anim: str
    direction: str
    index: int
    duration: int
    sprite: np.ndarray  # binary alpha: art, generated outline and effects, no shadow
    image: np.ndarray  # the sprite over the ground shadow: what gets exported
    layers: list[Layer]
    owner: np.ndarray  # per pixel: index of the visible layer, EMPTY or OUTLINE
    open_soles: np.ndarray  # ring pixels left open by the open-soles rule
    flags: frozenset[str]
    source: tuple[str, int]  # the drawn (anim, frame) this frame comes from
    mirrored_from: str | None = None

    @property
    def label(self) -> str:
        return f"{self.character} {self.anim} {self.direction} {self.index}"

    def slot_mask(self, *slots: str) -> np.ndarray:
        idx = [i for i, layer in enumerate(self.layers) if layer.slot in slots]
        return np.isin(self.owner, idx)

    def material_at(self, x: int, y: int) -> str | None:
        i = self.owner[y, x]
        return self.layers[i].part.material if i >= 0 else None


class Composer:
    def __init__(self, root: Path, style: Style, recipe: Recipe, library: Library | None = None):
        self.root, self.style, self.recipe = Path(root), style, recipe
        self.lib = library or Library(root, style)
        self.rig: Rig = load_rig(root, style, recipe.rig)
        self.anims: dict[str, AnimDef] = load_anims(style)
        self.size = self.rig.size.canvas
        self.parts = self._resolve()
        materials = {p.material for p in self.parts.values()}
        self.maps = {m: ramp_map(style.materials[m], preset_ramp(style, m, recipe.colors.get(m)))
                     for m in materials}
        lid = style.raw["effects"].get("close_eyes", {"material": "skin", "shade": 0})
        self.lid = parse_hex(preset_ramp(style, lid["material"], recipe.colors.get(lid["material"]))
                             [lid["shade"]])
        self.flash_rgb = parse_hex(style.flash)

    # ------------------------------------------------------------------ parts
    def _resolve(self) -> dict[str, Part]:
        chosen: dict[str, str] = {}
        for slot in ("body", "arm_near", "arm_far"):
            if (self.lib.root / slot / self.rig.name / "part.yaml").is_file():
                chosen[slot] = self.rig.name
        chosen.update(self.recipe.parts)
        present: dict[str, Part] = {}
        for slot, variant in chosen.items():
            if variant == "none":
                continue
            try:
                part = self.lib.part(slot, variant)
            except PartError as e:
                raise RecipeError(f"{self.recipe.name}: {e}") from None
            if self.rig.name not in part.rigs:
                raise RecipeError(f"{self.recipe.name}: {part.id} does not fit rig {self.rig.name}")
            present[slot] = part
        hidden = set().union(*(p.hides for p in present.values())) if present else set()
        return {s: p for s, p in present.items() if s not in hidden}

    def origin(self, part: Part, direction: str) -> tuple[int, int]:
        if part.origin and direction in part.origin:
            return part.origin[direction]
        return self.rig.anchor("idle", direction, 0, part.attach)

    def offset(self, part: Part, anim: AnimDef, direction: str, index: int) -> tuple[int, int]:
        """Where a rigid part sits in this frame (lagging parts use the previous frame)."""
        f = self.lag_frame(part, anim, direction, index)
        ax, ay = self.rig.anchor(anim.name, direction, f, part.attach)
        ox, oy = self.origin(part, direction)
        return ax - ox, ay - oy

    def lag_frame(self, part: Part, anim: AnimDef, direction: str, index: int) -> int:
        if not part.lags:
            return index
        n = self.rig.frame_count(anim.name, direction)
        return (index - 1) % n if anim.loop else max(index - 1, 0)

    def layer(self, part: Part, anim: AnimDef, direction: str, index: int) -> Layer | None:
        if not part.drawn(anim.name):
            sheet = self.lib.sheet(part, RIGID_SHEET)
            cell = sheet.get(direction, 0) if sheet else None
            if cell is None or not cell[..., 3].any():
                return None
            dx, dy = self.offset(part, anim, direction, index)
            cell, dropped = shift(cell, dx, dy)
            offset = (dx, dy)
        else:
            sheet = self.lib.sheet(part, anim.name)
            cell = sheet.get(direction, self.lag_frame(part, anim, direction, index)) if sheet else None
            if cell is None or not cell[..., 3].any():
                return None
            offset, dropped = (0, 0), 0
        return Layer(part.slot, part, recolor(cell, self.maps[part.material]), offset, dropped)

    # ------------------------------------------------------------------ frames
    def shadow_rows(self, sprite: np.ndarray, flags: frozenset[str]) -> dict[int, tuple[int, int]]:
        rows = dict(self.style.shadow.rows)
        if "airborne" in flags:
            sil = sprite[..., 3] == 255
            ys = np.flatnonzero(sil.any(axis=1))
            lift = self.rig.size.pivot[1] - int(ys.max()) if ys.size else 0
            cut = max(0, lift) // 2
            out = {}
            for y, (x0, x1) in rows.items():
                width = max(x1 - x0 + 1 - 2 * cut, 5)
                mid = (x0 + x1) // 2
                out[y] = (mid - width // 2, mid - width // 2 + width - 1)
            rows = out
        return rows

    def frame(self, anim_name: str, direction: str, index: int) -> Frame:
        anim = self.anims[anim_name]
        src_name, src_index = anim.source_frame(index)
        src = self.anims[src_name]
        layers = []
        for slot in self.rig.z_order[direction]:
            part = self.parts.get(slot)
            if part is not None:
                layer = self.layer(part, src, direction, src_index)
                if layer is not None:
                    layers.append(layer)
        sprite = np.zeros((self.size, self.size, 4), np.uint8)
        owner = np.full((self.size, self.size), EMPTY, np.int16)
        for i, layer in enumerate(layers):
            mask = layer.image[..., 3] == 255
            sprite[mask] = layer.image[mask]
            owner[mask] = i
        o = self.style.outline
        flags = src.frame_flags(src_index) | anim.frame_flags(index)
        airborne = "airborne" in flags
        result = outline(sprite, o.rgb, open_soles=o.open_soles and not airborne,
                         sole_rows=o.sole_rows, lowest=None if airborne else self.rig.size.pivot[1])
        sprite = result.image
        owner[result.ring] = OUTLINE
        if anim.effect == "close_eyes":
            eyes = np.isin(owner, [i for i, l in enumerate(layers) if l.slot == "eyes"])
            sprite = close_eyes(sprite, eyes, self.lid)
        if "flash" in flags:
            sprite = flash(sprite, o.rgb, self.flash_rgb)
        shadow = shadow_layer(self.style.shadow, o.rgb, self.size,
                              rows=self.shadow_rows(sprite, flags))
        return Frame(
            character=self.recipe.name, anim=anim_name, direction=direction, index=index,
            duration=anim.frames_ms[index], sprite=sprite, image=over_shadow(sprite, shadow),
            layers=layers, owner=owner, open_soles=result.open, flags=flags,
            source=(src_name, src_index),
        )


def mirror_frame(frame: Frame, axis: int, direction: str) -> Frame:
    def m(a: np.ndarray) -> np.ndarray:
        return mirror(a, axis)[0]

    def m2(a: np.ndarray) -> np.ndarray:  # 2-D masks and owner maps
        out = np.zeros_like(a) if a.dtype == bool else np.full_like(a, EMPTY)
        w = a.shape[1]
        for x in range(w):
            x2 = 2 * axis - x
            if 0 <= x2 < w:
                out[:, x2] = a[:, x]
        return out

    return replace(
        frame, direction=direction, sprite=m(frame.sprite), image=m(frame.image),
        layers=[replace(layer, image=m(layer.image)) for layer in frame.layers],
        owner=m2(frame.owner), open_soles=m2(frame.open_soles), mirrored_from=frame.direction,
    )
