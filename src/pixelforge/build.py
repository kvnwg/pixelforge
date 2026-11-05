"""Building a recipe: compose every frame, mirror west, validate (ARCHITECTURE.md section 9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .anim import retime
from .compose import Composer, Frame, mirror_frame
from .parts import Library
from .recipe import Recipe, find_recipe, load_recipe
from .style import Style, load_style
from .validate import Finding, Validator


@dataclass
class Build:
    recipe: Recipe
    composer: Composer
    frames: dict[tuple[str, str], list[Frame]]  # (anim, direction) -> frames, west included
    findings: list[Finding] = field(default_factory=list)
    not_drawn: list[str] = field(default_factory=list)  # poses the rig has not been drawn in yet

    @property
    def style(self) -> Style:
        return self.composer.style

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warning"]

    def anim_directions(self, anim: str) -> list[str]:
        return [d for d in self.style.directions if (anim, d) in self.frames]


def build(root: Path, recipe: Recipe | str, *, style: Style | None = None,
          library: Library | None = None, validate: bool = True) -> Build:
    style = style or load_style(Path(root) / "style" / "style.json")
    if isinstance(recipe, str):
        recipe = load_recipe(find_recipe(root, recipe), style)
    composer = Composer(root, style, recipe, library)
    rig = composer.rig
    result = Build(recipe, composer, {})
    for anim in recipe.anims:
        adef = composer.anims[anim]
        drawn = adef.drawn_directions(style)
        for d in drawn:
            frames = []
            for i in range(adef.frames):
                src_anim, src_index = adef.source_frame(i)
                if rig.has(src_anim, d, src_index):
                    frames.append(composer.frame(anim, d, i))
            missing = adef.frames - len(frames)
            if missing:
                result.not_drawn.append(f"{anim} {d}: {missing} of {adef.frames} frames")
            if frames:
                result.frames[(anim, d)] = frames
        for west, east in style.mirrors.items():
            if (anim, east) in result.frames:
                result.frames[(anim, west)] = [mirror_frame(f, rig.size.mirror_axis_x, west)
                                               for f in result.frames[(anim, east)]]
    profile = style.raw["combat"]["timing_profiles"][recipe.timing_profile]
    for (anim, d), frames in result.frames.items():
        adef = composer.anims[anim]
        if len(frames) == adef.frames:
            for f, ms in zip(frames, retime(adef, [f.duration for f in frames], profile)):
                f.duration = ms
    if validate:
        result.findings = run_validation(result)
    return result


def run_validation(b: Build) -> list[Finding]:
    v = Validator(b.composer)
    findings = v.completeness(b.recipe.anims)
    for (anim, d), frames in b.frames.items():
        for f in frames:
            findings += v.frame(f)
        findings += v.animation(frames, b.composer.anims[anim].loop)
    for west, east in b.style.mirrors.items():
        for anim in b.recipe.anims:
            if (anim, east) in b.frames and (anim, west) in b.frames:
                findings += v.mirror(b.frames[(anim, east)], b.frames[(anim, west)])
    findings += v.combat(b.frames, b.recipe.timing_profile)
    return findings
