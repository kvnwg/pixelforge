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
    "eyes_closed_frames": "eyes_closed",
    "grounded_frames": "grounded",  # a hovering rig (flyer) touching down: shadow at full size
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
    source: tuple[str, int | None] | None  # derived: (anim, frame) of another; frame None = the
                                           # same frame index (an alias, e.g. combat_idle = idle)
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
        if not self.source:
            return (self.name, index)
        anim, frame = self.source
        return (anim, index if frame is None else frame)

    def event_frame(self, *types: str) -> int | None:
        frames = [int(e["frame"]) for e in self.events if e.get("type") in types]
        return min(frames) if frames else None


def retime(anim: AnimDef, durations: list[int], profile: dict) -> list[int]:
    """Timing profiles (COMBAT.md section 2): hold frames are scaled by hold_scale; then, if the
    tell (first windup frame to the hit or spawn) is still shorter than telegraph_min_ms, the
    last hold frame before the hit is extended until it meets it."""
    holds = anim.flags.get("hold", frozenset())
    out = [round(ms * float(profile.get("hold_scale", 1.0))) if i in holds else ms
           for i, ms in enumerate(durations)]
    hit = anim.event_frame("hit", "spawn")
    start = anim.event_frame("windup") or 0
    minimum = int(profile.get("telegraph_min_ms", 0))
    if hit is not None and minimum:
        tell = sum(out[start:hit])
        if tell < minimum:
            before = [i for i in holds if start <= i < hit]
            out[max(before) if before else hit - 1] += minimum - tell
    return out


def tell_ms(anim: AnimDef, durations: list[int]) -> int | None:
    hit = anim.event_frame("hit", "spawn")
    if hit is None:
        return None
    return sum(durations[(anim.event_frame("windup") or 0):hit])


def anim_specs(style: Style, rig: str | None = None) -> dict[str, dict[str, Any]]:
    """The raw animation definitions a rig uses: the global set, then the rig's own
    (`rigs.<rig>.animations` in style.json) over it. An alias copies another's timing."""
    specs = {k: v for k, v in style.raw["animations"].items() if isinstance(v, dict)}
    if rig:
        specs.update((style.raw.get("rigs", {}).get(rig, {}) or {}).get("animations", {}))
    out = {}
    for name, a in specs.items():
        if "alias" in a and "frames_ms" not in a:
            a = {**specs[a["alias"]], **a}
        out[name] = a
    return out


def load_anims(style: Style, rig: str | None = None) -> dict[str, AnimDef]:
    out = {}
    for name, a in anim_specs(style, rig).items():
        frames_ms = tuple(a["frames_ms"])
        phases = None
        if "active_frames" in a or a.get("phases"):
            phases = tuple(a.get("phases") or _phases(len(frames_ms), set(a.get("active_frames", []))))
        src = a.get("source") or ({"anim": a["alias"], "frame": None} if "alias" in a else None)
        out[name] = AnimDef(
            name=name, loop=bool(a["loop"]), frames_ms=frames_ms,
            flags={flag: frozenset(a.get(key, [])) for key, flag in FLAG_KEYS.items()},
            events=tuple(a.get("events", [])), phases=phases,
            root_motion=tuple(a["root_motion_px"]) if "root_motion_px" in a else None,
            source=(src["anim"], None if src.get("frame") is None else int(src["frame"])) if src else None,
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
