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
from .effects import close_eyes, flash, footprint_shadow, over_shadow, shadow_layer
from .outline import outline
from .parts import RIGID_SHEET, Library, Part, PartError
from .recipe import Recipe, RecipeError
from .recolor import preset_ramp, ramp_map, recolor
from .rig import Rig, RigError, load_rig
from .sheet import mirror, shift
from .style import Style

EMPTY, OUTLINE, SMEAR = -1, -2, -3
NECK_SLOTS = ("torso_wear", "over_torso")  # parts that wear the collar stretch with the neck
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


def _follow(track: list[int], held: bool = False) -> int:
    """A trailing part's coordinate from its anchor's now, a frame ago, two and three ago.
    `held`: the frame stays on screen (a once-through animation's last), so no overshoot."""
    a, p, q, r = track
    clamp = lambda v: max(-1, min(1, v))  # noqa: E731
    if a != p:
        return a - clamp(a - p)    # moving: 1 px behind
    if p != q or held:
        return a                   # just stopped: caught up
    if q != r:
        return a + clamp(q - r)    # then 1 px past (follow-through)
    return a                       # settled


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
        self.slot_maps = {}  # recipe slot_colors: one part dyed apart from its material's preset
        for slot, preset in recipe.slot_colors.items():
            part = self.parts.get(slot)
            if part is None:
                continue
            if preset not in style.materials[part.material].presets:
                raise RecipeError(f"{recipe.name}: slot_colors.{slot}: {preset!r} is not a "
                                  f"{part.material} preset")
            self.slot_maps[slot] = ramp_map(style.materials[part.material],
                                            preset_ramp(style, part.material, preset))
        # closed eyes take a shade of the body around them: skin for humanoids, the rig's own
        # material for monsters (rigs.<rig>.close_eyes)
        lid = dict(self.rig_spec.get("close_eyes") or style.raw["effects"].get(
            "close_eyes", {"material": "skin", "shade": 0}))
        body = self.parts.get("body")
        if body is not None and body.material != lid["material"]:
            lid = {"material": body.material, "shade": 0}  # a skull's socket, not a skin lid
        self.lid = parse_hex(preset_ramp(style, lid["material"], recipe.colors.get(lid["material"]))
                             [lid["shade"]])
        self.flash_rgb = parse_hex(style.flash)
        self.swing_rgb = [parse_hex(c) for c in style.fx_ramps["swing"]]  # rim, mid, core

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
        """Where a rigid part sits in this frame. A lagging part (hair locks, a ponytail, a tail)
        follows its anchor like loose material (MOTION.md rule 5): 1 px behind while the anchor
        moves, caught up on the frame after it stops, 1 px past it on the next (follow-through),
        then settled. It is never more than 1 px from its anchor, so it never detaches."""
        ax, ay = self.rig.anchor(anim.name, direction, index, part.attach)
        if part.lags:
            frames = [index]
            for _ in range(3):
                frames.append(self.lag_frame(part, anim, direction, frames[-1]))
            pts = [self.rig.anchor(anim.name, direction, i, part.attach) for i in frames]
            # a once-through animation's last frame is held by the game: it never overshoots
            held = not anim.loop and index == self.rig.frame_count(anim.name, direction) - 1
            ax = _follow([p[0] for p in pts], held)
            ay = _follow([p[1] for p in pts], held)
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
            if part.slot in NECK_SLOTS:
                cell = self.stretch_neck(cell, part, anim, direction, index)
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
        mapping = self.slot_maps.get(part.slot, self.maps[part.material])
        return Layer(part.slot, part, recolor(cell, mapping), offset, dropped,
                     name)

    def stretch_neck(self, cell: np.ndarray, part: Part, anim: AnimDef, direction: str,
                     index: int) -> np.ndarray:
        """The idle's wave drops the chest under a still head and the body's neck stretches a
        row (tools/art/humanoid.py). A part that wears the collar follows: the row it shows at
        the torso's top is repeated up into the gap, so a gorget or a neckline stretches instead
        of opening a line of skin under a helmet. Facing n the repeated row takes the material's
        dark shade, the head's shadow on the back, as the body's does (a doubled row of flat
        cloth reads as a slab, W5). The gap is measured against idle frame 0."""
        try:
            chin, torso = (self.rig.anchor(anim.name, direction, index, n) for n in ("chin", "torso"))
            chin0, torso0 = (self.rig.anchor("idle", direction, 0, n) for n in ("chin", "torso"))
        except RigError:
            return cell
        gap, top = (torso[1] - chin[1]) - (torso0[1] - chin0[1]), torso[1]
        if gap <= 0 or top - gap < 0 or top >= cell.shape[0]:
            return cell
        out = cell.copy()
        source = cell[top].copy()
        if direction == "n":
            dark = np.array(parse_hex(self.style.materials[part.material].base[0]), np.uint8)
            ink = np.array(self.style.outline.rgb, np.uint8)
            shade = (source[:, 3] == 255) & ~np.all(source[:, :3] == ink, axis=-1)
            source[shade, :3] = dark
        for y in range(top - gap, top):
            fill = (source[:, 3] == 255) & (out[y, :, 3] == 0)
            out[y][fill] = source[fill]
        return out

    def smear_cell(self, held: Part | None, src: AnimDef, direction: str, index: int,
                   front: bool = False):
        """The held item's smear for a frame, placed (or None): a weapon drawn per frame (a
        monster's club) has smear_<anim>.png with a cell per frame; a posed one has
        smear_<pose>.png, moved with the item, and smear_<pose>_front.png for a blade that
        passes in front of the body (drawn over it)."""
        if held is None:
            return None
        cell = None
        if held.drawn(src.name):
            sheet = self.lib.sheet(held, f"smear_{src.name}" + ("_front" if front else ""))
            if sheet is not None and index < sheet.frames:
                cell = sheet.get(direction, index)
        else:
            pose = self.pose(held, src, direction, index)
            sheet = self.lib.sheet(held, f"smear_{pose}" + ("_front" if front else "")) if pose else None
            cell = sheet.get(direction, 0) if sheet else None
            if cell is not None:
                cell, _ = shift(cell, *self.offset(held, src, direction, index))
        return cell if cell is not None and cell[..., 3].any() else None

    def swing(self, cell: np.ndarray, fade: bool = False) -> np.ndarray:
        """Paint a smear in fx_ramps.swing by rank: the smear's lightest color becomes the white
        core, the next the mid shade, the rest the grey-blue rim. A fading trail (the frame after
        the strike) drops its darkest rank and steps the rest one shade down."""
        out = np.zeros_like(cell)
        solid = cell[..., 3] == 255
        colors = sorted({tuple(int(v) for v in px[:3]) for px in cell[solid]},
                        key=lambda c: -(0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]))
        for rank, color in enumerate(colors):
            if fade and len(colors) > 1 and rank == len(colors) - 1:
                continue
            shade = max(2 - min(rank, 2) - (1 if fade else 0), 0)
            mask = solid & np.all(cell[..., :3] == np.asarray(color, np.uint8), axis=-1)
            out[mask, :3] = self.swing_rgb[shade]
            out[mask, 3] = 255
        return out

    # ------------------------------------------------------------------ frames
    def shadow_rows(self, sprite: np.ndarray, flags: frozenset[str],
                    direction: str = "s") -> dict[int, tuple[int, int]]:
        """The ground shadow: the style's ellipse (scaled to the rig's `footprint` on a bigger
        size class), or the rig's own (`rigs.<rig>.shadow_rows`, a hovering flyer's small shadow
        that never bobs); airborne jumps shrink it."""
        rows = self.ground_shadow()
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

    def ground_shadow(self) -> dict[int, tuple[int, int]]:
        """The style's shadow on the small class; bigger classes scale it with the rig's
        footprint (MONSTERS.md section 3), never by resampling the small one."""
        if self.size == self.style.canvas:
            return dict(self.style.shadow.rows)
        default = self.size * 9 // 32 | 1  # the anchor's 9 px footprint, in proportion
        return footprint_shadow(int(self.rig_spec.get("footprint", default)), self.rig.size.pivot,
                                bottom=self.rig.size.safe_bounds[3])

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
        # Swing trails: a strike's smear (the arc the weapon traced) is drawn after the outline in
        # the white swing ramp, only on empty pixels (behind the character), never outlined; on
        # the next frame it lingers a shade dimmer, then is gone.
        held = self.parts.get("held_near")
        for front in (False, True):  # behind the body, then (a blade passing in front) over it
            cell, fade = self.smear_cell(held, src, direction, src_index, front), False
            if cell is None and src_index > 0:
                cell, fade = self.smear_cell(held, src, direction, src_index - 1, front), True
            if cell is not None:
                cell = self.swing(cell, fade)
                mask = (cell[..., 3] == 255) & (sprite[..., 3] == 0 if not front else True)
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
