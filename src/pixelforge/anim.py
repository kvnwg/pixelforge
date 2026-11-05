"""Animation definitions from style.json: timing, loops, per-frame flags, events, combat data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .style import Style

FLAG_KEYS = {
    "hold_frames": "hold",
    "active_frames": "active",
    "airborne_frames": "airborne",
    "flash_frames": "flash",
    "squash_frames": "squash",
    "displaced_frames": "displaced",
    "lying_frames": "lying",
}


@dataclass(frozen=True)
class AnimDef:
    name: str
    loop: bool
    frames_ms: tuple[int, ...]
    flags: dict[str, frozenset[int]]
    events: tuple[dict[str, Any], ...]
    phases: tuple[str, ...] | None
    root_motion: tuple[float, ...] | None
    source: tuple[str, int] | None  # derived animations: built from (anim, frame) of another
    effect: str | None  # effect applied to every frame ("close_eyes" for blink)
    only_directions: tuple[str, ...] | None  # drawn directions when limited (blink: s, e)
    combat: bool
    raw: dict[str, Any] = field(repr=False)

    @property
    def frames(self) -> int:
        return len(self.frames_ms)

    def frame_flags(self, index: int) -> frozenset[str]:
        return frozenset(name for name, frames in self.flags.items() if index in frames)

    def drawn_directions(self, style: Style) -> tuple[str, ...]:
        if self.only_directions is not None:
            return self.only_directions
        return style.combat_directions if self.combat else style.drawn_directions

    def directions(self, style: Style) -> tuple[str, ...]:
        """Drawn directions plus the ones mirrored from them, in style order."""
        drawn = self.drawn_directions(style)
        mirrored = [d for d, src in style.mirrors.items() if src in drawn]
        return tuple(d for d in style.directions if d in drawn or d in mirrored)

    def source_frame(self, index: int) -> tuple[str, int]:
        return self.source if self.source else (self.name, index)


def load_anims(style: Style) -> dict[str, AnimDef]:
    out = {}
    for name, a in style.raw["animations"].items():
        if not isinstance(a, dict):
            continue
        frames_ms = tuple(a["frames_ms"])
        phases = None
        if "active_frames" in a or a.get("phases"):
            phases = tuple(a.get("phases") or _phases(len(frames_ms), set(a.get("active_frames", []))))
        src = a.get("source")
        out[name] = AnimDef(
            name=name, loop=bool(a["loop"]), frames_ms=frames_ms,
            flags={flag: frozenset(a.get(key, [])) for key, flag in FLAG_KEYS.items()},
            events=tuple(a.get("events", [])), phases=phases,
            root_motion=tuple(a["root_motion_px"]) if "root_motion_px" in a else None,
            source=(src["anim"], int(src["frame"])) if src else None,
            effect=a.get("effect"),
            only_directions=tuple(a["directions"]) if "directions" in a else None,
            combat=bool(a.get("combat", False)), raw=a,
        )
    return out


def _phases(n: int, active: set[int]) -> list[str]:
    """windup before the first active frame, active, recovery after."""
    first = min(active) if active else n
    last = max(active) if active else n - 1
    return ["windup" if i < first else "active" if i <= last else "recovery" for i in range(n)]
