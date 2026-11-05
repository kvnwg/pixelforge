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

from dataclasses import dataclass, field, replace
from pathlib import Path

import json

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

EMPTY, OUTLINE, SMEAR = -1, -2, -3
HELD_SLOTS = ("held_near", "held_near_trim", "held_far")


@dataclass
class Layer:
    slot: str
    part: Part
    image: np.ndarray  # recolored cell in canvas coordinates
    offset: tuple[int, int]  # translation applied to a rigid part; (0, 0) for drawn cells
    dropped: int  # opaque pixels pushed off the canvas by that translation
    sheet: str = ""  # the sheet the cell came from: "rigid", "pose_raised", "walk"...


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
    hitboxes: list[tuple[int, int, int, int]] = field(default_factory=list)  # x, y, w, h
    hurtbox: tuple[int, int, int, int] | None = None
    points: dict[str, tuple[int, int]] = field(default_factory=dict)  # named points for events

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
        self.anims: dict[str, AnimDef] = load_anims(style, recipe.rig)
        self.rig_spec = style.raw["rigs"][recipe.rig]
        self.size = self.rig.size.canvas
        self.parts = self._resolve()
        materials = {p.material for p in self.parts.values()}
        self.maps = {m: ramp_map(style.materials[m], preset_ramp(style, m, recipe.colors.get(m)))
                     for m in materials}
        # closed eyes take a shade of the body around them: skin for humanoids, the rig's own
        # material for monsters (rigs.<rig>.close_eyes)
        lid = self.rig_spec.get("close_eyes") or style.raw["effects"].get(
            "close_eyes", {"material": "skin", "shade": 0})
        self.lid = parse_hex(preset_ramp(style, lid["material"], recipe.colors.get(lid["material"]))
                             [lid["shade"]])
        self.flash_rgb = parse_hex(style.flash)

    # ------------------------------------------------------------------ parts
    def _resolve(self) -> dict[str, Part]:
        chosen: dict[str, str] = {}
        for slot in ("body", "arm_near", "arm_far"):
            if (self.lib.root / slot / self.rig.name / "part.yaml").is_file():
                chosen[slot] = self.rig.name
        # rig defaults (an unarmed humanoid holds the 'fist': no art, just its smear and hitboxes)
        chosen.update(self.style.raw["rigs"][self.rig.name].get("defaults", {}))
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
        """Where a rigid part sits in this frame. A lagging part trails its anchor by one frame
        but never by more than 1 px, so a lock drifts behind a big move instead of detaching."""
        ax, ay = self.rig.anchor(anim.name, direction, index, part.attach)
        if part.lags:
            px, py = self.rig.anchor(anim.name, direction,
                                     self.lag_frame(part, anim, direction, index), part.attach)
            ax -= max(-1, min(1, ax - px))
            ay -= max(-1, min(1, ay - py))
        ox, oy = self.origin(part, direction)
        return ax - ox, ay - oy

    def lag_frame(self, part: Part, anim: AnimDef, direction: str, index: int) -> int:
        if not part.lags:
            return index
        n = self.rig.frame_count(anim.name, direction)
        return (index - 1) % n if anim.loop else max(index - 1, 0)

    def pose(self, part: Part, anim: AnimDef, direction: str, index: int) -> str | None:
        """The pose a frame asks of a part (a weapon raised, striking...); trims follow their
        parent slot's pose."""
        poses = self.rig.points(anim.name, direction, index).get("pose", {})
        slot = part.slot[:-5] if part.slot.endswith("_trim") else part.slot
        return poses.get(slot)

    def pose_sheet(self, part: Part, pose: str | None, behind: bool = False):
        """A held item's cell for a pose: pose_<name>.png, drawn in idle-hand coordinates like
        rigid.png. A pose may put the item behind the character (pose_<name>_behind.png, a
        weapon cocked behind the head); one with only a behind cell has nothing in front."""
        if not pose:
            return None if behind else self.lib.sheet(part, RIGID_SHEET)
        if behind:
            return self.lib.sheet(part, f"pose_{pose}_behind")
        front = self.lib.sheet(part, f"pose_{pose}")
        if front is not None or self.lib.sheet(part, f"pose_{pose}_behind") is not None:
            return front
        return self.lib.sheet(part, RIGID_SHEET)

    def layer(self, part: Part, anim: AnimDef, direction: str, index: int,
              behind: bool = False) -> Layer | None:
        if not part.drawn(anim.name):
            sheet = self.pose_sheet(part, self.pose(part, anim, direction, index), behind)
            cell = sheet.get(direction, 0) if sheet else None
            if cell is None or not cell[..., 3].any():
                return None
            dx, dy = self.offset(part, anim, direction, index)
            cell, dropped = shift(cell, dx, dy)
            offset = (dx, dy)
            name = sheet.path.stem if getattr(sheet, "path", None) else RIGID_SHEET
        elif behind:
            return None
        else:
            sheet = self.lib.sheet(part, anim.name)
            cell = sheet.get(direction, self.lag_frame(part, anim, direction, index)) if sheet else None
            if cell is None or not cell[..., 3].any():
                return None
            offset, dropped = (0, 0), 0
            name = anim.name
        return Layer(part.slot, part, recolor(cell, self.maps[part.material]), offset, dropped,
                     name)

    # ------------------------------------------------------------------ frames
    def shadow_rows(self, sprite: np.ndarray, flags: frozenset[str],
                    direction: str = "s") -> dict[int, tuple[int, int]]:
        """The ground shadow: the style's ellipse, or the rig's own (`rigs.<rig>.shadow_rows`,
        a hovering flyer's small shadow that never bobs); airborne jumps shrink it."""
        rows = dict(self.style.shadow.rows)
        own = self.rig_spec.get("shadow_rows")
        if own and direction in own:  # per direction: a long side view casts a long shadow
            own = own[direction]
        elif own and any(k in own for k in ("s", "e", "n")):
            own = None
        if own and "grounded" not in flags:
            rows = {int(y): (int(x0), int(x1)) for y, (x0, x1) in own.items()}
            if not self.rig_spec.get("hover"):
                return self._shrink(rows, sprite, flags)
            return rows
        return self._shrink(rows, sprite, flags)

    def _shrink(self, rows, sprite, flags):
        """An airborne jump shrinks the shadow 1 px a side per 2 px of lift."""
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
        for slot in HELD_SLOTS:  # held items posed behind the character go under everything
            part = self.parts.get(slot)
            if part is not None:
                layer = self.layer(part, src, direction, src_index, behind=True)
                if layer is not None:
                    layers.append(layer)
        hidden_here = set(self.rig.points(src.name, direction, src_index).get("hide", []))
        for slot in self.rig.z_order[direction]:
            part = self.parts.get(slot)
            if part is not None and slot not in hidden_here:  # a pose may hide a part
                layer = self.layer(part, src, direction, src_index)
                if layer is not None:
                    layers.append(layer)
        flags = src.frame_flags(src_index) | anim.frame_flags(index)
        if self.rig_spec.get("hover") and "grounded" not in flags:
            flags = flags | {"airborne"}  # a flyer's body floats above its grounded pivot
        if not flags & {"airborne", "lying"}:
            # nothing but held items goes below the ground: a skirt or tabard pushed under the
            # baseline by a deep crouch folds onto it
            base = self.rig.size.pivot[1]
            for layer in layers:
                if layer.slot not in HELD_SLOTS:
                    layer.image[base + 1:] = 0
        sprite = np.zeros((self.size, self.size, 4), np.uint8)
        owner = np.full((self.size, self.size), EMPTY, np.int16)
        for i, layer in enumerate(layers):
            mask = layer.image[..., 3] == 255
            sprite[mask] = layer.image[mask]
            owner[mask] = i
        o = self.style.outline
        airborne = "airborne" in flags
        result = outline(sprite, o.rgb, open_soles=o.open_soles and not airborne,
                         sole_rows=o.sole_rows, lowest=None if airborne else self.rig.size.pivot[1])
        sprite = result.image
        owner[result.ring] = OUTLINE
        if anim.effect == "close_eyes" or "eyes_closed" in flags:
            eyes = np.isin(owner, [i for i, l in enumerate(layers) if l.slot == "eyes"])
            sprite = close_eyes(sprite, eyes, self.lid)
        # Smears trace a strike: drawn after the outline, in the weapon's own material, only on
        # empty pixels (behind the character), never outlined.
        held = self.parts.get("held_near")
        if held is not None and not held.drawn(src.name):
            pose = self.pose(held, src, direction, src_index)
            sheet = self.lib.sheet(held, f"smear_{pose}") if pose else None
            cell = sheet.get(direction, 0) if sheet else None
            if cell is not None and cell[..., 3].any():
                cell, _ = shift(cell, *self.offset(held, src, direction, src_index))
                cell = recolor(cell, self.maps[held.material])
                mask = (cell[..., 3] == 255) & (sprite[..., 3] == 0)
                sprite[mask] = cell[mask]
                owner[mask] = SMEAR
        if "flash" in flags:
            sprite = flash(sprite, o.rgb, self.flash_rgb)
        shadow = shadow_layer(self.style.shadow, o.rgb, self.size,
                              rows=self.shadow_rows(sprite, flags, direction))
        frame = Frame(
            character=self.recipe.name, anim=anim_name, direction=direction, index=index,
            duration=anim.frames_ms[index], sprite=sprite, image=over_shadow(sprite, shadow),
            layers=layers, owner=owner, open_soles=result.open, flags=flags,
            source=(src_name, src_index),
        )
        self.combat_data(frame, src, direction, src_index)
        return frame

    # ------------------------------------------------------------------ combat data
    def part_data(self, part: Part) -> dict:
        path = part.folder / "hitboxes.json"
        return json.loads(path.read_text()) if path.is_file() else {}

    def combat_data(self, frame: Frame, anim: AnimDef, direction: str, index: int) -> None:
        pts = self.rig.points(anim.name, direction, index)
        if "active" in frame.flags:  # monsters (and any rig) author their own hitboxes
            right = 2 * self.rig.size.mirror_axis_x  # clipped so the mirrored box stays on canvas
            for x, y, w, h in pts.get("hitboxes", []):
                x0, y0 = max(int(x), 0), max(int(y), 0)
                x1, y1 = min(int(x) + int(w), right + 1), min(int(y) + int(h), self.size)
                if x1 > x0 and y1 > y0:
                    frame.hitboxes.append((x0, y0, x1 - x0, y1 - y0))
        frame.points = {k: (int(v[0]), int(v[1])) for k, v in pts.items()
                        if isinstance(v, list) and len(v) == 2 and all(isinstance(c, int) for c in v)}
        # the hurtbox: the body's bounding box inside its outline (the outlined silhouette inset
        # by 1 px), without held items or smears
        body = (frame.owner >= 0) & ~frame.slot_mask(*HELD_SLOTS)
        if body.any():
            ys, xs = np.nonzero(body)
            x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            frame.hurtbox = (x0, y0, x1 - x0 + 1, y1 - y0 + 1)
        for slot in ("held_near", "held_far"):
            part = self.parts.get(slot)
            if part is None:
                continue
            data = self.part_data(part)
            pose = self.pose(part, anim, direction, index) or "rest"
            dx, dy = (0, 0) if part.drawn(anim.name) else self.offset(part, anim, direction, index)
            for name, per_dir in data.get("points", {}).get(pose, {}).items():
                if direction in per_dir:
                    x, y = per_dir[direction]
                    frame.points[name] = (x + dx, y + dy)
            if slot == "held_near" and "active" in frame.flags:
                for x, y, w, h in data.get("hitboxes", {}).get(pose, {}).get(direction, []):
                    # a reach box moves with the hand; the canvas clips it
                    x0, y0 = max(x + dx, 0), max(y + dy, 0)
                    x1, y1 = min(x + dx + w, self.size), min(y + dy + h, self.size)
                    if x1 > x0 and y1 > y0:
                        frame.hitboxes.append((x0, y0, x1 - x0, y1 - y0))


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

    def box(b):
        x, y, w, h = b
        return (2 * axis - (x + w - 1), y, w, h)

    return replace(
        frame, direction=direction, sprite=m(frame.sprite), image=m(frame.image),
        layers=[replace(layer, image=m(layer.image)) for layer in frame.layers],
        owner=m2(frame.owner), open_soles=m2(frame.open_soles), mirrored_from=frame.direction,
        hitboxes=[box(b) for b in frame.hitboxes],
        hurtbox=box(frame.hurtbox) if frame.hurtbox else None,
        points={k: (2 * axis - x, y) for k, (x, y) in frame.points.items()},
    )
