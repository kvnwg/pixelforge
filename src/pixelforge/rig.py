"""Rigs: a body plan's size class, layer order and anchor points (ARCHITECTURE.md sections 6, 20).

Anchors live in parts/body/<rig>/anchors.json:

    {"idle": {"s": [{"head": [15, 11], "torso": [15, 20], ..., "planted": ["foot_near"]}, ...]}}

Every frame lists named points (pixels in the frame's canvas); "planted" names the feet that
carry weight in that frame. The frames listed here are the poses the rig has been drawn in.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .style import SizeClass, Style


class RigError(ValueError):
    pass


@dataclass(frozen=True)
class Rig:
    name: str
    size: SizeClass
    anchors: dict[str, dict[str, list[dict[str, Any]]]]
    z_order: dict[str, list[str]]
    head_rows: int | None

    def frame_count(self, anim: str, direction: str) -> int:
        return len(self.anchors.get(anim, {}).get(direction, []))

    def has(self, anim: str, direction: str, frame: int) -> bool:
        return 0 <= frame < self.frame_count(anim, direction)

    def points(self, anim: str, direction: str, frame: int) -> dict[str, Any]:
        try:
            return self.anchors[anim][direction][frame]
        except (KeyError, IndexError):
            raise RigError(f"rig {self.name} has no {anim} {direction} frame {frame}") from None

    def anchor(self, anim: str, direction: str, frame: int, name: str) -> tuple[int, int]:
        pts = self.points(anim, direction, frame)
        if name not in pts:
            raise RigError(f"rig {self.name}: {anim} {direction} frame {frame} has no anchor {name!r}")
        x, y = pts[name]
        return int(x), int(y)

    def planted(self, anim: str, direction: str, frame: int) -> list[str]:
        return list(self.points(anim, direction, frame).get("planted", []))


def load_rig(root: Path, style: Style, name: str) -> Rig:
    spec = style.raw.get("rigs", {}).get(name)
    if not isinstance(spec, dict):
        raise RigError(f"rig {name!r} is not in style.json")
    size_name = spec["size_class"]
    if size_name not in style.size_classes:
        raise RigError(f"rig {name!r}: size class {size_name!r} must be a single class to build it")
    path = Path(root) / "parts" / "body" / name / "anchors.json"
    anchors = json.loads(path.read_text()) if path.is_file() else {}
    z_order = {d: list(spec.get("z_order", {}).get(d, style.raw["z_order"][d]))
               for d in style.drawn_directions}
    return Rig(name, style.size_classes[size_name], anchors, z_order, spec.get("head_rows"))
