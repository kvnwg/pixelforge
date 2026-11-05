"""Parts, their part.yaml, and the parts library (ARCHITECTURE.md section 5)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .sheet import Sheet
from .style import Style

RIGID_SHEET = "rigid"
KINDS = ("animated", "rigid")


class PartError(ValueError):
    pass


@dataclass(frozen=True)
class Part:
    slot: str
    variant: str
    material: str
    kind: str
    attach: str | None
    origin: dict[str, tuple[int, int]] | None  # None: the attach anchor in idle frame 0
    animated_overrides: frozenset[str]
    hides: frozenset[str]
    lags: bool
    allow_singletons: dict[str, tuple[tuple[int, int], ...]]  # per direction, frame-0 coords
    rigs: tuple[str, ...]
    notes: str
    folder: Path

    @property
    def id(self) -> str:
        return f"{self.slot}/{self.variant}"

    def sheet_path(self, anim: str) -> Path:
        return self.folder / f"{anim}.png"

    def drawn(self, anim: str) -> bool:
        """True when this animation comes from a drawn sheet (not from translating rigid.png)."""
        return self.kind == "animated" or anim in self.animated_overrides


def all_slots(style: Style) -> set[str]:
    slots: set[str] = set()
    for order in style.raw["z_order"].values():
        slots.update(order)
    for rig in style.raw.get("rigs", {}).values():
        if isinstance(rig, dict):
            for order in rig.get("z_order", {}).values():
                slots.update(order)
    return slots


def load_part(folder: Path, style: Style) -> Part:
    path = folder / "part.yaml"
    try:
        data: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    except FileNotFoundError:
        raise PartError(f"{path}: missing") from None
    problems = []

    def need(key: str) -> Any:
        if key not in data:
            problems.append(f"{key}: missing")
        return data.get(key)

    slot, variant, material, kind = need("slot"), need("variant"), need("material"), need("kind")
    if slot is not None and slot != folder.parent.name:
        problems.append(f"slot: {slot!r} does not match folder {folder.parent.name!r}")
    if variant is not None and str(variant) != folder.name:
        problems.append(f"variant: {variant!r} does not match folder {folder.name!r}")
    if material is not None and material not in style.materials:
        problems.append(f"material: {material!r} is not in style.json")
    if kind is not None and kind not in KINDS:
        problems.append(f"kind: {kind!r} must be one of {KINDS}")
    attach = data.get("attach")
    if kind == "rigid" and not attach:
        problems.append("attach: rigid parts need an anchor name")
    origin = None
    raw_origin = data.get("origin", "auto")
    if raw_origin not in (None, "auto"):
        if isinstance(raw_origin, list) and len(raw_origin) == 2:
            origin = {d: (int(raw_origin[0]), int(raw_origin[1])) for d in style.drawn_directions}
        elif isinstance(raw_origin, dict):
            origin = {d: (int(v[0]), int(v[1])) for d, v in raw_origin.items()}
        else:
            problems.append(f"origin: expected 'auto', [x, y] or a map per direction")
    slots = all_slots(style)
    hides = frozenset(data.get("hides") or [])
    if hides - slots:
        problems.append(f"hides: {sorted(hides - slots)} are not slots")
    singles = data.get("allow_singletons") or {}
    if isinstance(singles, list):  # same list for every direction
        singles = {d: singles for d in style.drawn_directions}
    rigs = tuple(data.get("rigs") or ["humanoid"])
    unknown = [r for r in rigs if r not in style.raw.get("rigs", {})]
    if unknown:
        problems.append(f"rigs: {unknown} are not rigs in style.json")
    if problems:
        raise PartError(f"{path}:\n" + "\n".join(f"  - {p}" for p in problems))
    return Part(
        slot=slot, variant=str(variant), material=material, kind=kind, attach=attach,
        origin=origin, animated_overrides=frozenset(data.get("animated_overrides") or []),
        hides=hides, lags=bool(data.get("lags", False)),
        allow_singletons={d: tuple((int(x), int(y)) for x, y in v) for d, v in singles.items()},
        rigs=rigs, notes=str(data.get("notes", "")), folder=folder,
    )


class Library:
    """All parts under <root>/parts, loaded lazily, with their sheets cached."""

    def __init__(self, root: Path, style: Style):
        self.root = Path(root) / "parts"
        self.style = style
        self._parts: dict[str, Part] = {}
        self._sheets: dict[tuple[str, str], Sheet | None] = {}

    def part(self, slot: str, variant: str) -> Part:
        key = f"{slot}/{variant}"
        if key not in self._parts:
            folder = self.root / slot / variant
            if not folder.is_dir():
                raise PartError(f"no part {key} (expected {folder})")
            self._parts[key] = load_part(folder, self.style)
        return self._parts[key]

    def slots(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if p.is_dir()) if self.root.is_dir() else []

    def variants(self, slot: str) -> list[str]:
        folder = self.root / slot
        if not folder.is_dir():
            return []
        return sorted(p.name for p in folder.iterdir() if (p / "part.yaml").is_file())

    def all_parts(self) -> list[Part]:
        return [self.part(s, v) for s in self.slots() for v in self.variants(s)]

    def cell_size(self, part: Part) -> int:
        size = self.style.raw["rigs"][part.rigs[0]]["size_class"]
        return self.style.size_classes[size].canvas

    def sheet(self, part: Part, anim: str, rows: tuple[str, ...] | None = None) -> Sheet | None:
        key = (part.id, anim)
        if key not in self._sheets:
            path = part.sheet_path(anim)
            if not path.is_file():
                self._sheets[key] = None
            else:
                self._sheets[key] = Sheet.load(path, self.cell_size(part),
                                               rows or self.style.drawn_directions)
        return self._sheets[key]
