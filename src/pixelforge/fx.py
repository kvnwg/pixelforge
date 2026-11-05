"""FX assets: smears, impacts, projectiles, status overlays (COMBAT.md section 6).

An FX lives in fx/<name>/ with fx.yaml and one sheet per animation (one row of frames, authored
facing east, painted in the FX's base ramp from style.json `fx_ramps`):

    name: fireball
    ramp: fire                 # the fx_ramps entry the sheets are painted in
    tints: []                  # optional: also export the art recolored into these ramps,
                               # one FX per tint, named <name>_<tint>
    cell: 16                   # cell size: 16, 24, 32 or 48
    pivot: [8, 7]              # the pixel placed on the event point (or the anchor it follows)
    layer: above               # above | below the characters
    space: world               # world (stays where it spawned) | follow (moves with a character)
    attach: head               # follow FX: the anchor it rides
    rotate: true               # may be rotated in 90-degree steps for s and n (FX only)
    anims:
      travel: {frames_ms: [60, 60, 60], loop: true}
      impact: {frames_ms: [40, 50, 50, 60, 70], loop: false}

Directions: e as drawn, w mirrored, s and n rotated 90 degrees (clockwise and counter-clockwise)
when `rotate` is true, otherwise drawn upright in every direction. Rotation and mirroring are
lossless on the pixel grid; characters are never rotated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .color import parse_hex, to_hex
from .recolor import recolor
from .sheet import load_rgba, save_rgba
from .style import Style

CELLS = (16, 24, 32, 48)
LAYERS = ("above", "below")
SPACES = ("world", "follow")
DIRS = ("s", "e", "n", "w")


class FXError(ValueError):
    pass


@dataclass(frozen=True)
class FXAnim:
    name: str
    frames_ms: tuple[int, ...]
    loop: bool


@dataclass
class FX:
    name: str
    folder: Path
    ramp: str
    tints: tuple[str, ...]
    cell: int
    pivot: tuple[int, int]
    layer: str
    space: str
    attach: str | None
    rotate: bool
    anims: dict[str, FXAnim]
    notes: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def sheet_path(self, anim: str) -> Path:
        return self.folder / f"{anim}.png"

    def variants(self) -> list[tuple[str, str]]:
        """(exported name, ramp) for every FX this folder builds."""
        if self.tints:
            return [(f"{self.name}_{t}", t) for t in self.tints]
        return [(self.name, self.ramp)]


def load_fx(folder: Path, style: Style) -> FX:
    path = Path(folder) / "fx.yaml"
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except FileNotFoundError:
        raise FXError(f"{path}: missing") from None
    problems = []
    ramps = style.raw["fx_ramps"]
    name = data.get("name")
    if name != Path(folder).name:
        problems.append(f"name: {name!r} does not match the folder {Path(folder).name!r}")
    ramp = data.get("ramp")
    if ramp not in ramps:
        problems.append(f"ramp: {ramp!r} is not in fx_ramps {sorted(ramps)}")
    tints = tuple(data.get("tints") or ())
    for t in tints:
        if t not in ramps:
            problems.append(f"tints: {t!r} is not in fx_ramps")
    cell = data.get("cell")
    if cell not in CELLS:
        problems.append(f"cell: {cell!r} must be one of {CELLS}")
    pivot = tuple(data.get("pivot") or ())
    if len(pivot) != 2 or not all(isinstance(v, int) for v in pivot):
        problems.append("pivot: expected [x, y]")
    elif cell in CELLS and not all(0 <= v < cell for v in pivot):
        problems.append(f"pivot: {list(pivot)} is outside the {cell} px cell")
    layer = data.get("layer", "above")
    if layer not in LAYERS:
        problems.append(f"layer: {layer!r} must be one of {LAYERS}")
    space = data.get("space", "world")
    if space not in SPACES:
        problems.append(f"space: {space!r} must be one of {SPACES}")
    anims = {}
    for aname, spec in (data.get("anims") or {}).items():
        ms = spec.get("frames_ms") or []
        if not ms or not all(isinstance(v, int) and v > 0 for v in ms):
            problems.append(f"anims.{aname}.frames_ms: positive integers expected")
        anims[aname] = FXAnim(aname, tuple(ms), bool(spec.get("loop", False)))
    if not anims:
        problems.append("anims: at least one animation")
    if problems:
        raise FXError(f"{path}:\n" + "\n".join(f"  - {p}" for p in problems))
    return FX(name=name, folder=Path(folder), ramp=ramp, tints=tints, cell=int(cell),
              pivot=(int(pivot[0]), int(pivot[1])), layer=layer, space=space,
              attach=data.get("attach"), rotate=bool(data.get("rotate", False)), anims=anims,
              notes=str(data.get("notes", "")), raw=data)


def fx_folders(root: Path) -> list[Path]:
    base = Path(root) / "fx"
    return sorted(p for p in base.iterdir() if (p / "fx.yaml").is_file()) if base.is_dir() else []


def find_fx(root: Path, name: str) -> Path:
    for folder in fx_folders(root):
        if folder.name == name:
            return folder
    raise FXError(f"no FX named {name!r} in {Path(root) / 'fx'}")


# ------------------------------------------------------------------ frames and directions
def frames(fx: FX, anim: str) -> list[np.ndarray]:
    """The east-facing cells of one animation, as drawn."""
    img = load_rgba(fx.sheet_path(anim))
    c = fx.cell
    n = fx.anims[anim].frames_ms
    if img.shape[0] != c or img.shape[1] != c * len(n):
        raise FXError(f"{fx.sheet_path(anim)}: {img.shape[1]} x {img.shape[0]}, expected "
                      f"{c * len(n)} x {c} ({len(n)} frames of {c} px)")
    return [img[:, i * c:(i + 1) * c].copy() for i in range(len(n))]


def orient(cell: np.ndarray, pivot: tuple[int, int], d: str, rotate: bool
           ) -> tuple[np.ndarray, tuple[int, int]]:
    """An east-facing cell turned to face d: w mirrors; s and n rotate 90 degrees when the FX
    may rotate (clockwise for s: east becomes south), else they stay upright like e."""
    size = cell.shape[0]
    x, y = pivot
    if d == "w":
        return cell[:, ::-1].copy(), (size - 1 - x, y)
    if d in ("s", "n") and rotate:
        if d == "s":  # (x, y) -> (size - 1 - y, x)
            return np.rot90(cell, k=-1).copy(), (size - 1 - y, x)
        return np.rot90(cell, k=1).copy(), (y, size - 1 - x)  # (x, y) -> (y, size - 1 - x)
    return cell.copy(), (x, y)


def tint(cell: np.ndarray, style: Style, src: str, dst: str) -> np.ndarray:
    if src == dst:
        return cell
    a = [parse_hex(c) for c in style.raw["fx_ramps"][src]]
    b = [parse_hex(c) for c in style.raw["fx_ramps"][dst]]
    return recolor(cell, dict(zip(a, b)))


# ------------------------------------------------------------------ validation
@dataclass(frozen=True)
class FXFinding:
    level: str
    rule: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.rule:4} {self.where}: {self.message}"


def validate_fx(fx: FX, style: Style) -> list[FXFinding]:
    """E19 (colors from the FX's own ramp only; fx_constraints are checked on the ramps by
    pf palette), binary alpha (E3), cell sizes and frame counts (E1, E12), the pivot inside the
    art's reach, and the short-and-snappy guideline (W11)."""
    out: list[FXFinding] = []
    ramp = {parse_hex(c) for c in style.raw["fx_ramps"][fx.ramp]}
    for name, anim in fx.anims.items():
        where = f"fx {fx.name} {name}"
        try:
            cells = frames(fx, name)
        except (FXError, FileNotFoundError) as e:
            out.append(FXFinding("error", "E1", where, str(e)))
            continue
        for i, cell in enumerate(cells):
            a = cell[..., 3]
            if ((a != 0) & (a != 255)).any():
                out.append(FXFinding("error", "E3", f"{where} {i}", "semi-transparent pixels: FX "
                                                                   "alpha is 0 or 255"))
            opaque = a == 255
            colors = {tuple(int(v) for v in px) for px in cell[opaque][:, :3]}
            bad = sorted(to_hex(c) for c in colors - ramp)
            if bad:
                out.append(FXFinding("error", "E19", f"{where} {i}",
                                     f"colors outside the {fx.ramp} FX ramp: {bad}"))
            if not opaque.any() and not (anim.loop is False and i == len(cells) - 1):
                out.append(FXFinding("warning", "W11", f"{where} {i}", "empty frame"))
            edge = opaque.copy()
            edge[1:-1, 1:-1] = False
            if edge.any():
                out.append(FXFinding("error", "E8", f"{where} {i}", "art touches the cell edge "
                                                                    "(rotation and mirroring "
                                                                    "need a 1 px margin)"))
        if len(anim.frames_ms) > 8 and not anim.loop:
            out.append(FXFinding("warning", "W11", where, f"{len(anim.frames_ms)} frames: one-shot "
                                                          "FX are 3 to 8 frames"))
        if not anim.loop and any(not 40 <= ms <= 120 for ms in anim.frames_ms):
            out.append(FXFinding("warning", "W11", where, f"frame times {list(anim.frames_ms)}: "
                                                          "one-shot FX run 40 to 120 ms a frame"))
    return out


def character_fx_colors(style: Style) -> list[FXFinding]:
    """E19's other half: character presets never use FX ramp colors (glow eyes excepted)."""
    fx_colors = {parse_hex(c): name for name, ramp in style.raw["fx_ramps"].items() for c in ramp}
    out = []
    for mname, m in style.raw["materials"].items():
        glow = set(m.get("glow_presets") or [])
        for pname, ramp in m.get("presets", {}).items():
            if pname in glow:
                continue
            for c in ramp:
                if parse_hex(c) in fx_colors:
                    out.append(FXFinding("error", "E19", f"{mname}/{pname}",
                                         f"{c} is a {fx_colors[parse_hex(c)]} FX color"))
    return out


# ------------------------------------------------------------------ export
def export(fx: FX, style: Style, out_root: Path) -> list[dict[str, Any]]:
    """One spritesheet + Aseprite JSON per variant: rows (anim, dir) in s, e, n, w order."""
    entries = []
    for vname, ramp in fx.variants():
        rows, tags, frames_json = [], [], []
        index = 0
        pivots: dict[str, list[int]] = {}
        for aname, anim in fx.anims.items():
            cells = [tint(c, style, fx.ramp, ramp) for c in frames(fx, aname)]
            for d in DIRS:
                turned = [orient(c, fx.pivot, d, fx.rotate) for c in cells]
                rows.append([t[0] for t in turned])
                pivots[f"{aname}_{d}"] = list(turned[0][1])
                tags.append({"name": f"{aname}_{d}", "from": index, "to": index + len(cells) - 1,
                             "direction": "forward"})
                for i, ms in enumerate(anim.frames_ms):
                    frames_json.append({
                        "filename": f"{vname} {aname}_{d} {i}",
                        "frame": {"x": i * fx.cell, "y": (len(rows) - 1) * fx.cell,
                                  "w": fx.cell, "h": fx.cell},
                        "rotated": False, "trimmed": False,
                        "spriteSourceSize": {"x": 0, "y": 0, "w": fx.cell, "h": fx.cell},
                        "sourceSize": {"w": fx.cell, "h": fx.cell}, "duration": ms})
                index += len(cells)
        width = max(len(r) for r in rows) * fx.cell
        sheet = np.zeros((len(rows) * fx.cell, width, 4), np.uint8)
        for r, cells in enumerate(rows):
            for i, c in enumerate(cells):
                sheet[r * fx.cell:(r + 1) * fx.cell, i * fx.cell:(i + 1) * fx.cell] = c
        folder = Path(out_root) / vname
        folder.mkdir(parents=True, exist_ok=True)
        save_rgba(folder / f"{vname}.png", sheet)
        meta = {
            "app": "pixelforge", "version": "1", "image": f"{vname}.png", "format": "RGBA8888",
            "size": {"w": width, "h": len(rows) * fx.cell}, "scale": "1", "frameTags": tags,
            "pixelforge": {"fx": vname, "ramp": ramp, "cell": fx.cell, "pivot": pivots,
                           "layer": fx.layer, "space": fx.space, "attach": fx.attach,
                           "rotate": fx.rotate,
                           "loop": {a: anim.loop for a, anim in fx.anims.items()}},
        }
        (folder / f"{vname}.json").write_text(json.dumps({"frames": frames_json, "meta": meta},
                                                         indent=1))
        entries.append({"name": vname, "image": f"fx/{vname}/{vname}.png",
                        "json": f"fx/{vname}/{vname}.json", "layer": fx.layer,
                        "anims": list(fx.anims)})
    return entries


def update_fx_index(out_root: Path, entries: list[dict[str, Any]]) -> Path:
    path = Path(out_root) / "index.json"
    index = json.loads(path.read_text()) if path.is_file() else {"fx": []}
    by_name = {e["name"]: e for e in index.get("fx", [])}
    for e in entries:
        by_name[e["name"]] = e
    index["fx"] = [by_name[k] for k in sorted(by_name)]
    path.write_text(json.dumps(index, indent=1))
    return path


class FXLibrary:
    """Every built FX variant's east-facing frames, for review renders and battle strips."""

    def __init__(self, root: Path, style: Style):
        self.root, self.style = Path(root), style
        self._fx: dict[str, tuple[FX, str]] = {}
        for folder in fx_folders(root):
            fx = load_fx(folder, style)
            for vname, ramp in fx.variants():
                self._fx[vname] = (fx, ramp)

    def names(self) -> list[str]:
        return sorted(self._fx)

    def has(self, name: str) -> bool:
        return name in self._fx

    def get(self, name: str) -> tuple[FX, str]:
        if name not in self._fx:
            raise FXError(f"no FX named {name!r}")
        return self._fx[name]

    def cells(self, name: str, anim: str | None = None, d: str = "e"
              ) -> tuple[list[np.ndarray], tuple[int, int], FXAnim]:
        fx, ramp = self.get(name)
        anim = anim or next(iter(fx.anims))
        out = []
        pivot = fx.pivot
        for c in frames(fx, anim):
            turned, pivot = orient(tint(c, self.style, fx.ramp, ramp), fx.pivot, d, fx.rotate)
            out.append(turned)
        return out, pivot, fx.anims[anim]
