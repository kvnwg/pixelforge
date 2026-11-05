"""Load and validate style/style.json.

Every color and every piece of geometry comes from this file (CLAUDE.md: never hardcode them).
`load_style` checks the whole file and raises one `StyleError` listing every problem it found,
each with its JSON path, so a broken style fails loudly and all at once.

The parts the code uses today are returned as typed objects on `Style`; everything else (rigs,
animations, combat data) is validated here and available as `Style.raw` until a phase needs it.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from .color import RGB, WARNING_RULES, is_hex, parse_hex

ROOT_ENV = "PIXELFORGE_ROOT"
NOTE_KEYS = frozenset({"note", "notes", "rule"})  # prose allowed inside maps of named entries


class StyleError(ValueError):
    """style.json is missing, unreadable or invalid. `problems` lists every issue found."""

    def __init__(self, path: Path, problems: list[str]):
        self.path = path
        self.problems = problems
        lines = "\n".join(f"  - {p}" for p in problems)
        super().__init__(f"{path}: {len(problems)} problem(s)\n{lines}")


# --------------------------------------------------------------------------- typed model


@dataclass(frozen=True)
class SizeClass:
    name: str
    canvas: int
    pivot: tuple[int, int]
    mirror_axis_x: int
    safe_bounds: tuple[int, int, int, int]  # x0, y0, x1, y1 inclusive


@dataclass(frozen=True)
class Material:
    name: str
    shades: int
    base: tuple[str, ...]
    presets: dict[str, tuple[str, ...]]
    glow_presets: frozenset[str]


@dataclass(frozen=True)
class OutlineSpec:
    color: str
    rgb: RGB
    open_soles: bool
    sole_rows: int  # open soles apply to ring pixels at or below (lowest row - (sole_rows - 1))


@dataclass(frozen=True)
class ShadowSpec:
    color: str
    alpha: int
    rows: dict[int, tuple[int, int]]  # row -> (x0, x1) inclusive


@dataclass(frozen=True)
class ColorLimits:
    L_range: tuple[float, float]
    C_max: float


@dataclass(frozen=True)
class AcceptedWarning:
    rules: frozenset[str]
    reason: str


@dataclass(frozen=True)
class Constraints:
    character: ColorLimits
    glow: ColorLimits
    fx: ColorLimits
    L_step: tuple[float, float]
    L_step_slack: float
    hue_shift: tuple[float, float]
    hue_min_chroma: float
    tolerance: float
    max_colors_per_frame: int
    accepted: dict[str, AcceptedWarning]


@dataclass(frozen=True)
class Ramp:
    """One checkable color ramp: a material preset, a glow preset, an FX ramp or a single color."""

    id: str  # "skin/fair", "eyes/glow red", "fx/fire", "effects/flash", "outline"
    group: str  # "outline" | "character" | "glow" | "fx" | "effect"
    colors: tuple[str, ...]


@dataclass(frozen=True)
class Style:
    path: Path
    root: Path
    raw: dict[str, Any]
    name: str
    canvas: int
    pivot: tuple[int, int]
    baseline_y: int
    directions: tuple[str, ...]
    drawn_directions: tuple[str, ...]  # directions with their own art (w is mirrored from e)
    mirrors: dict[str, str]  # generated direction -> the direction it is mirrored from
    outline: OutlineSpec
    shadow: ShadowSpec
    flash: str
    constraints: Constraints
    materials: dict[str, Material]
    fx_ramps: dict[str, tuple[str, ...]]
    size_classes: dict[str, SizeClass]
    combat_view: str
    combat_directions: tuple[str, ...]
    palette_anchor: dict[str, str]
    anchor_file: Path
    hand_placed_outline: tuple[tuple[int, int], ...]

    def ramps(self) -> list[Ramp]:
        return _ramps(self.outline.color, self.materials, self.fx_ramps, self.flash)


def _ramps(outline: str, materials: dict[str, Material], fx_ramps: dict[str, tuple[str, ...]],
           flash: str) -> list[Ramp]:
    out = [Ramp("outline", "outline", (outline,))]
    for m in materials.values():
        for preset, colors in m.presets.items():
            group = "glow" if preset in m.glow_presets else "character"
            out.append(Ramp(f"{m.name}/{preset}", group, colors))
        if m.base not in m.presets.values():
            out.append(Ramp(f"{m.name}/base", "character", m.base))
    out += [Ramp(f"fx/{name}", "fx", colors) for name, colors in fx_ramps.items()]
    out.append(Ramp("effects/flash", "effect", (flash,)))
    return out


# --------------------------------------------------------------------------- finding the repo


def find_root(start: Path | None = None) -> Path:
    """The pixelforge repo: $PIXELFORGE_ROOT, else the nearest parent of `start` (default: the
    current directory) holding style/style.json and src/pixelforge, else this package's checkout."""
    env = os.environ.get(ROOT_ENV)
    if env:
        root = Path(env).expanduser().resolve()
        if not (root / "style" / "style.json").is_file():
            raise FileNotFoundError(f"{ROOT_ENV}={env} has no style/style.json")
        return root
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "style" / "style.json").is_file() and (candidate / "src" / "pixelforge").is_dir():
            return candidate
    package_root = Path(__file__).resolve().parents[2]
    if (package_root / "style" / "style.json").is_file():
        return package_root
    raise FileNotFoundError(
        "can't find the pixelforge repo: run from inside it or set PIXELFORGE_ROOT")


# --------------------------------------------------------------------------- validation helpers


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


_KINDS: dict[str, Callable[[Any], bool]] = {
    "object": lambda v: isinstance(v, dict),
    "list": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str) and v != "",
    "int": _is_int,
    "number": _is_num,
    "bool": lambda v: isinstance(v, bool),
    "hex color": is_hex,
    "point [x, y]": lambda v: isinstance(v, list) and len(v) == 2 and all(map(_is_int, v)),
    "int span [x0, x1]": lambda v: (isinstance(v, list) and len(v) == 2 and all(map(_is_int, v))
                                    and v[0] <= v[1]),
    "span [lo, hi]": lambda v: (isinstance(v, list) and len(v) == 2 and all(map(_is_num, v))
                                and v[0] <= v[1]),
    "list of ints": lambda v: isinstance(v, list) and all(map(_is_int, v)),
    "list of numbers": lambda v: isinstance(v, list) and all(map(_is_num, v)),
    "list of strings": lambda v: isinstance(v, list) and all(isinstance(s, str) and s for s in v),
}


def _show(v: Any) -> str:
    text = json.dumps(v)
    return text if len(text) <= 60 else text[:57] + "..."


class _Checker:
    def __init__(self) -> None:
        self.problems: list[str] = []

    def fail(self, path: str, message: str) -> None:
        self.problems.append(f"{path}: {message}")

    def get(self, obj: Any, path: str, key: str, kind: str, *, optional: bool = False) -> Any:
        """obj[key] if present and of the right kind; otherwise record why and return None."""
        full = f"{path}.{key}" if path else key
        if not isinstance(obj, dict):
            return None  # the parent was already reported
        if key not in obj:
            if not optional:
                self.fail(full, "missing")
            return None
        value = obj[key]
        if not _KINDS[kind](value):
            self.fail(full, f"expected {kind}, got {_show(value)}")
            return None
        return value

    def entries(self, obj: Any, path: str, kind: str = "object") -> Iterator[tuple[str, Any]]:
        """(name, value) for each named entry of a map, skipping prose notes."""
        if not isinstance(obj, dict):
            return
        for name, value in obj.items():
            if name in NOTE_KEYS and isinstance(value, str):
                continue
            if not _KINDS[kind](value):
                self.fail(f"{path}.{name}", f"expected {kind}, got {_show(value)}")
                continue
            yield name, value

    def ramp(self, value: Any, path: str, length: int | None = None) -> tuple[str, ...] | None:
        if not isinstance(value, list) or not value:
            self.fail(path, f"expected a non-empty list of hex colors, got {_show(value)}")
            return None
        bad = [v for v in value if not is_hex(v)]
        if bad:
            self.fail(path, f"not #rrggbb colors: {_show(bad)}")
            return None
        if length is not None and len(value) != length:
            self.fail(path, f"has {len(value)} shades; the material has {length}")
            return None
        return tuple(v.lower() for v in value)

    def in_canvas(self, point: Any, path: str, canvas: int | None) -> bool:
        if not _KINDS["point [x, y]"](point):
            self.fail(path, f"expected point [x, y], got {_show(point)}")
            return False
        if canvas is not None and not all(0 <= c < canvas for c in point):
            self.fail(path, f"{point} is outside the {canvas} x {canvas} canvas")
            return False
        return True


# --------------------------------------------------------------------------- loading


def load_style(path: str | os.PathLike[str] | None = None) -> Style:
    """Load and validate style.json (default: <repo>/style/style.json)."""
    style_path = Path(path) if path is not None else find_root() / "style" / "style.json"
    try:
        raw = json.loads(style_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise StyleError(style_path, ["file not found"]) from None
    except json.JSONDecodeError as e:
        raise StyleError(style_path, [f"not valid JSON: {e}"]) from None
    if not isinstance(raw, dict):
        raise StyleError(style_path, ["the top level must be an object"])
    return _build(raw, style_path.resolve())


def _build(raw: dict[str, Any], path: Path) -> Style:
    c = _Checker()
    root = path.parent.parent
    name = c.get(raw, "", "name", "string")
    c.get(raw, "", "version", "int")

    # Size classes first: the top-level canvas and pivot must agree with the small class.
    classes = _size_classes(c, raw)
    small = classes.get("small")
    canvas_obj = c.get(raw, "", "canvas", "object")
    cw = c.get(canvas_obj, "canvas", "w", "int")
    ch = c.get(canvas_obj, "canvas", "h", "int")
    pivot_obj = c.get(raw, "", "pivot", "object")
    px = c.get(pivot_obj, "pivot", "x", "int")
    py = c.get(pivot_obj, "pivot", "y", "int")
    baseline = c.get(raw, "", "baseline_y", "int")
    safe_obj = c.get(raw, "", "safe_bounds", "object")
    safe = tuple(c.get(safe_obj, "safe_bounds", k, "int") for k in ("x0", "y0", "x1", "y1"))
    canvas = cw if cw is not None and cw == ch else None
    if cw is not None and ch is not None and cw != ch:
        c.fail("canvas", f"must be square, got {cw} x {ch}")
    if small is not None:
        if canvas is not None and canvas != small.canvas:
            c.fail("canvas", f"{canvas} does not match size_classes.small.canvas {small.canvas}")
        if None not in (px, py) and (px, py) != small.pivot:
            c.fail("pivot", f"({px}, {py}) does not match size_classes.small.pivot {list(small.pivot)}")
        if None not in safe and safe != small.safe_bounds:
            c.fail("safe_bounds", f"{list(safe)} does not match size_classes.small.safe_bounds")
    if None not in (baseline, py) and baseline != py:
        c.fail("baseline_y", f"{baseline} must equal pivot.y {py}")

    # Directions and mirroring.
    directions = c.get(raw, "", "directions", "list of strings") or []
    generated: dict[str, str] = {}
    mirror = c.get(raw, "", "mirror", "object")
    for d, m in c.entries(mirror, "mirror"):
        src = c.get(m, f"mirror.{d}", "from", "string")
        axis = c.get(m, f"mirror.{d}", "axis_x", "int")
        if d not in directions or (src is not None and src not in directions):
            c.fail(f"mirror.{d}", f"mirrors between directions not in {directions}")
        elif src is not None:
            generated[d] = src
        if axis is not None and small is not None and axis != small.mirror_axis_x:
            c.fail(f"mirror.{d}.axis_x", f"{axis} must equal the small class's axis {small.mirror_axis_x}")
    drawn = tuple(d for d in directions if d not in generated)

    # Outline and shadow.
    o = c.get(raw, "", "outline", "object")
    outline_color = c.get(o, "outline", "color", "hex color")
    outline_color = outline_color.lower() if outline_color else None
    mode = c.get(o, "outline", "mode", "string")
    if mode is not None and mode != "4-neighbor":
        c.fail("outline.mode", f"{mode!r} is not supported; only '4-neighbor'")
    soles = c.get(o, "outline", "open_soles", "object")
    soles_on = c.get(soles, "outline.open_soles", "enabled", "bool")
    sole_rows = c.get(soles, "outline.open_soles", "rows_from_bottom", "int")
    if sole_rows is not None and sole_rows < 1:
        c.fail("outline.open_soles.rows_from_bottom", "must be at least 1")
    shadow = _shadow(c, raw, canvas, outline_color)
    flash = c.get(c.get(raw, "", "effects", "object"), "effects", "flash", "hex color")
    list(c.entries(c.get(raw, "", "preview_backgrounds", "object"), "preview_backgrounds",
                   "hex color"))

    # Colors.
    materials = _materials(c, raw)
    fx_ramps = {}
    for fx_name, value in c.entries(c.get(raw, "", "fx_ramps", "object"), "fx_ramps", "list"):
        ramp = c.ramp(value, f"fx_ramps.{fx_name}")
        if ramp is not None and len(ramp) < 2:
            c.fail(f"fx_ramps.{fx_name}", "needs at least 2 shades")
        elif ramp is not None:
            fx_ramps[fx_name] = ramp
    ramp_ids = {r.id for r in _ramps(outline_color or "#000000", materials, fx_ramps,
                                     flash or "#000000")}
    constraints = _constraints(c, raw, ramp_ids)
    palette_anchor: dict[str, str] = {}
    base_colors = {h for m in materials.values() for h in m.base}
    for key, value in c.entries(c.get(raw, "", "palette_anchor", "object"), "palette_anchor",
                                "hex color"):
        palette_anchor[key] = value.lower()
        if materials and value.lower() not in base_colors and value.lower() != outline_color:
            c.fail(f"palette_anchor.{key}", f"{value} is not the outline or any material's base shade")

    # The anchor sprite's metadata.
    a = c.get(raw, "", "anchor", "object")
    anchor_file = c.get(a, "anchor", "file", "string")
    if anchor_file is not None and not (root / anchor_file).is_file():
        c.fail("anchor.file", f"{anchor_file} not found under {root}")
    bbox = c.get(a, "anchor", "bbox", "object")
    for k in ("x0", "y0", "x1", "y1"):
        v = c.get(bbox, "anchor.bbox", k, "int")
        if v is not None and canvas is not None and not 0 <= v < canvas:
            c.fail(f"anchor.bbox.{k}", f"{v} is outside the canvas")
    for i, point in enumerate(c.get(a, "anchor", "eyes", "list") or []):
        c.in_canvas(point, f"anchor.eyes[{i}]", canvas)
    hand_placed = []
    for i, point in enumerate(c.get(a, "anchor", "hand_placed_outline", "list") or []):
        if c.in_canvas(point, f"anchor.hand_placed_outline[{i}]", canvas):
            hand_placed.append((point[0], point[1]))

    # Layer order, rigs, combat and animations.
    z = c.get(raw, "", "z_order", "object")
    for d in drawn:
        layers = c.get(z, "z_order", d, "list of strings")
        if layers is not None and len(set(layers)) != len(layers):
            c.fail(f"z_order.{d}", "lists a slot more than once")
    for rig, spec in c.entries(c.get(raw, "", "rigs", "object"), "rigs"):
        size = c.get(spec, f"rigs.{rig}", "size_class", "string")
        if size is not None and classes:
            for part in size.split(" or "):
                if part not in classes:
                    c.fail(f"rigs.{rig}.size_class", f"{part!r} is not one of {sorted(classes)}")
    view, combat_dirs, event_types = _combat(c, raw, directions)
    _animations(c, raw, event_types)

    if c.problems:
        raise StyleError(path, c.problems)
    assert outline_color and flash and name and canvas is not None  # guaranteed by the checks
    return Style(
        path=path, root=root, raw=raw, name=name, canvas=canvas, pivot=(px, py),
        baseline_y=baseline, directions=tuple(directions), drawn_directions=drawn,
        mirrors=generated,
        outline=OutlineSpec(outline_color, parse_hex(outline_color), soles_on, sole_rows),
        shadow=shadow, flash=flash.lower(), constraints=constraints, materials=materials,
        fx_ramps=fx_ramps, size_classes=classes, combat_view=view,
        combat_directions=tuple(combat_dirs), palette_anchor=palette_anchor,
        anchor_file=root / anchor_file, hand_placed_outline=tuple(hand_placed),
    )


def _size_classes(c: _Checker, raw: dict[str, Any]) -> dict[str, SizeClass]:
    out: dict[str, SizeClass] = {}
    for name, sc in c.entries(c.get(raw, "", "size_classes", "object"), "size_classes"):
        p = f"size_classes.{name}"
        canvas = c.get(sc, p, "canvas", "int")
        pivot = c.get(sc, p, "pivot", "point [x, y]")
        axis = c.get(sc, p, "mirror_axis_x", "int")
        bounds = c.get(sc, p, "safe_bounds", "list of ints")
        if None in (canvas, pivot, axis, bounds):
            continue
        if len(bounds) != 4:
            c.fail(f"{p}.safe_bounds", "expected [x0, y0, x1, y1]")
            continue
        rule = [canvas // 2 - 1, canvas - 5]
        if pivot != rule:
            c.fail(f"{p}.pivot", f"{pivot} breaks the rule pivot = (canvas/2 - 1, canvas - 5) = {rule}")
        if axis != pivot[0]:
            c.fail(f"{p}.mirror_axis_x", f"{axis} must equal pivot x {pivot[0]}")
        x0, y0, x1, y1 = bounds
        if not (0 <= x0 <= pivot[0] <= x1 < canvas and 0 <= y0 <= pivot[1] <= y1 < canvas):
            c.fail(f"{p}.safe_bounds", f"{bounds} must lie inside the canvas and contain the pivot")
        out[name] = SizeClass(name, canvas, (pivot[0], pivot[1]), axis, (x0, y0, x1, y1))
    if "size_classes" in raw and "small" not in out:
        c.fail("size_classes.small", "missing (the anchor's size class)")
    return out


def _shadow(c: _Checker, raw: dict[str, Any], canvas: int | None,
            outline_color: str | None) -> ShadowSpec:
    s = c.get(raw, "", "shadow", "object")
    color = c.get(s, "shadow", "color", "hex color")
    alpha = c.get(s, "shadow", "alpha", "int")
    if color and outline_color and color.lower() != outline_color:
        c.fail("shadow.color", f"{color} must be the outline color {outline_color}")
    if alpha is not None and not 0 < alpha < 255:
        c.fail("shadow.alpha", f"{alpha} must be partial (1 to 254)")
    rows: dict[int, tuple[int, int]] = {}
    for key, span in c.entries(c.get(s, "shadow", "ellipse_rows", "object"), "shadow.ellipse_rows",
                               "int span [x0, x1]"):
        p = f"shadow.ellipse_rows.{key}"
        if not key.isdigit() or (canvas is not None and int(key) >= canvas):
            c.fail(p, "row must be a number inside the canvas")
        elif canvas is not None and not 0 <= span[0] <= span[1] < canvas:
            c.fail(p, f"{span} must be [x0, x1] inside the canvas")
        else:
            rows[int(key)] = (span[0], span[1])
    return ShadowSpec((color or "").lower(), alpha or 0, rows)


def _materials(c: _Checker, raw: dict[str, Any]) -> dict[str, Material]:
    out: dict[str, Material] = {}
    for name, m in c.entries(c.get(raw, "", "materials", "object"), "materials"):
        p = f"materials.{name}"
        shades = c.get(m, p, "shades", "int")
        if shades is not None and shades < 1:
            c.fail(f"{p}.shades", "must be at least 1")
            shades = None
        base = c.ramp(m.get("base"), f"{p}.base", shades) if "base" in m else None
        if "base" not in m:
            c.fail(f"{p}.base", "missing")
        presets: dict[str, tuple[str, ...]] = {}
        for preset, colors in c.entries(c.get(m, p, "presets", "object"), f"{p}.presets", "list"):
            ramp = c.ramp(colors, f"{p}.presets.{preset}", shades)
            if ramp is not None:
                presets[preset] = ramp
        if isinstance(m.get("presets"), dict) and not m["presets"]:
            c.fail(f"{p}.presets", "needs at least one preset")
        glow = c.get(m, p, "glow_presets", "list of strings", optional=True) or []
        for g in glow:
            if isinstance(m.get("presets"), dict) and g not in m["presets"]:
                c.fail(f"{p}.glow_presets", f"{g!r} is not a preset of {name}")
        if shades is not None and base is not None:
            out[name] = Material(name, shades, base, presets, frozenset(glow))
    return out


def _limits(c: _Checker, obj: Any, path: str) -> ColorLimits:
    L = c.get(obj, path, "oklch_L_range", "span [lo, hi]")
    C = c.get(obj, path, "oklch_C_max", "number")
    return ColorLimits((L[0], L[1]) if L else (0.0, 1.0), C if C is not None else 1.0)


def _constraints(c: _Checker, raw: dict[str, Any], ramp_ids: set[str]) -> Constraints:
    p = "constraints"
    k = c.get(raw, "", p, "object")
    step = c.get(k, p, "ramp_L_step_range", "span [lo, hi]") or [0.0, 1.0]
    hue = c.get(k, p, "ramp_hue_shift_deg_per_lighter_step", "span [lo, hi]") or [-180.0, 180.0]
    max_colors = c.get(k, p, "max_colors_per_frame", "int") or 0
    c.get(k, p, "alpha_values_allowed", "list of ints")
    numbers = {}
    for key in ("limit_tolerance", "ramp_L_step_slack", "hue_shift_min_chroma"):
        v = c.get(k, p, key, "number")
        if v is not None and v < 0:
            c.fail(f"{p}.{key}", "must not be negative")
        numbers[key] = v or 0.0
    accepted: dict[str, AcceptedWarning] = {}
    for ramp_id, entry in c.entries(c.get(k, p, "accepted_ramp_warnings", "object"),
                                    f"{p}.accepted_ramp_warnings"):
        q = f"{p}.accepted_ramp_warnings.{ramp_id}"
        if ramp_id not in ramp_ids:
            c.fail(q, "is not a ramp in this style (use material/preset, fx/name, ...)")
        rules = c.get(entry, q, "rules", "list of strings") or []
        unknown = sorted(set(rules) - WARNING_RULES)
        if unknown:
            c.fail(f"{q}.rules", f"{unknown} are not warning rules {sorted(WARNING_RULES)}")
        reason = c.get(entry, q, "reason", "string")
        accepted[ramp_id] = AcceptedWarning(frozenset(rules), reason or "")
    return Constraints(
        character=_limits(c, k, p),
        glow=_limits(c, c.get(raw, "", "glow_constraints", "object"), "glow_constraints"),
        fx=_limits(c, c.get(raw, "", "fx_constraints", "object"), "fx_constraints"),
        L_step=(step[0], step[1]), L_step_slack=numbers["ramp_L_step_slack"],
        hue_shift=(hue[0], hue[1]), hue_min_chroma=numbers["hue_shift_min_chroma"],
        tolerance=numbers["limit_tolerance"], max_colors_per_frame=max_colors, accepted=accepted,
    )


def _combat(c: _Checker, raw: dict[str, Any], directions: list[str]
            ) -> tuple[str, list[str], set[str]]:
    p = "combat"
    cb = c.get(raw, "", p, "object")
    options: dict[str, list[str]] = {}
    for name, opt in c.entries(c.get(cb, p, "view_options", "object"), f"{p}.view_options"):
        q = f"{p}.view_options.{name}"
        dirs = c.get(opt, q, "combat_directions", "list of strings") or []
        gen = c.get(opt, q, "generated", "list of strings") or []
        stray = [d for d in dirs + gen if d not in directions]
        if stray:
            c.fail(q, f"{stray} are not directions {directions}")
        options[name] = dirs
    view = c.get(cb, p, "view", "string")
    if view is not None and options and view not in options:
        c.fail(f"{p}.view", f"{_show(view)} is not one of {sorted(options)}; choose it in "
                            "Phase 0 (COMBAT.md section 0)")
    for name, prof in c.entries(c.get(cb, p, "timing_profiles", "object"), f"{p}.timing_profiles"):
        q = f"{p}.timing_profiles.{name}"
        tmin = c.get(prof, q, "telegraph_min_ms", "int")
        scale = c.get(prof, q, "hold_scale", "number")
        if tmin is not None and tmin < 0:
            c.fail(f"{q}.telegraph_min_ms", "must not be negative")
        if scale is not None and scale <= 0:
            c.fail(f"{q}.hold_scale", "must be positive")
    event_types = set(c.get(cb, p, "event_types", "list of strings") or [])
    return view or "", options.get(view or "", []), event_types


def _animations(c: _Checker, raw: dict[str, Any], event_types: set[str]) -> None:
    for name, a in c.entries(c.get(raw, "", "animations", "object"), "animations"):
        p = f"animations.{name}"
        c.get(a, p, "loop", "bool")
        frames = c.get(a, p, "frames_ms", "list of ints")
        if frames is None:
            continue
        if not frames or any(ms <= 0 for ms in frames):
            c.fail(f"{p}.frames_ms", "needs at least one frame, every duration positive")
            continue
        n = len(frames)
        for key in ("hold_frames", "active_frames", "airborne_frames", "flash_frames"):
            for i in c.get(a, p, key, "list of ints", optional=True) or []:
                if not 0 <= i < n:
                    c.fail(f"{p}.{key}", f"frame {i} does not exist ({n} frames)")
        charge = c.get(a, p, "charge_loop_frame", "int", optional=True)
        if charge is not None and not 0 <= charge < n:
            c.fail(f"{p}.charge_loop_frame", f"frame {charge} does not exist ({n} frames)")
        motion = c.get(a, p, "root_motion_px", "list of numbers", optional=True)
        if motion is not None and len(motion) != n:
            c.fail(f"{p}.root_motion_px", f"has {len(motion)} values for {n} frames")
        dissolve = c.get(a, p, "optional_dissolve_ms", "list of ints", optional=True)
        if dissolve is not None and any(ms <= 0 for ms in dissolve):
            c.fail(f"{p}.optional_dissolve_ms", "every duration must be positive")
        for i, ev in enumerate(c.get(a, p, "events", "list", optional=True) or []):
            q = f"{p}.events[{i}]"
            if not isinstance(ev, dict):
                c.fail(q, f"expected an object, got {_show(ev)}")
                continue
            frame = c.get(ev, q, "frame", "int")
            kind = c.get(ev, q, "type", "string")
            if frame is not None and not 0 <= frame < n:
                c.fail(f"{q}.frame", f"frame {frame} does not exist ({n} frames)")
            if kind is not None and event_types and kind not in event_types:
                c.fail(f"{q}.type", f"{kind!r} is not in combat.event_types")
            point = ev.get("point")
            if point is not None and not (isinstance(point, str) and point) \
                    and not _KINDS["point [x, y]"](point):
                c.fail(f"{q}.point", f"expected an anchor name or [x, y], got {_show(point)}")
            c.get(ev, q, "fx", "string", optional=True)
