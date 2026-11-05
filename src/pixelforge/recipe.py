"""Recipes: characters/<name>.yaml (ARCHITECTURE.md section 8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .style import Style


class RecipeError(ValueError):
    pass


@dataclass(frozen=True)
class Recipe:
    name: str
    rig: str
    timing_profile: str
    seed: int
    parts: dict[str, str]  # slot -> variant; "none" leaves the slot empty
    colors: dict[str, str]  # material -> preset name
    anims: tuple[str, ...]
    path: Path | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_yaml(self) -> str:
        data = {"name": self.name, "rig": self.rig, "timing_profile": self.timing_profile,
                "seed": self.seed, "parts": dict(self.parts), "colors": dict(self.colors),
                "anims": list(self.anims)}
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def parse_recipe(data: dict[str, Any], style: Style, path: Path | None = None) -> Recipe:
    problems = []
    for key in ("name", "rig", "parts", "anims"):
        if key not in data:
            problems.append(f"{key}: missing")
    rig = data.get("rig", "humanoid")
    if rig not in style.raw.get("rigs", {}):
        problems.append(f"rig: {rig!r} is not in style.json")
    profile = data.get("timing_profile", "player")
    if profile not in style.raw["combat"]["timing_profiles"]:
        problems.append(f"timing_profile: {profile!r} is not in style.json")
    colors = {str(k): str(v) for k, v in (data.get("colors") or {}).items()}
    for material, preset in colors.items():
        if material not in style.materials:
            problems.append(f"colors.{material}: no such material")
        elif preset not in style.materials[material].presets:
            problems.append(f"colors.{material}: {preset!r} is not a preset of {material} "
                            f"({', '.join(style.materials[material].presets)})")
    anims = tuple(data.get("anims") or [])
    from .anim import anim_specs
    rig_name = rig if isinstance(rig, str) else None
    unknown = [a for a in anims if a not in anim_specs(style, rig_name)]
    if unknown:
        problems.append(f"anims: {unknown} are not animations in style.json")
    if problems:
        raise RecipeError(f"{path or data.get('name')}:\n" + "\n".join(f"  - {p}" for p in problems))
    return Recipe(
        name=str(data["name"]), rig=rig, timing_profile=profile, seed=int(data.get("seed", 1)),
        parts={str(k): str(v) for k, v in data["parts"].items()}, colors=colors, anims=anims,
        path=path, raw=data,
    )


def load_recipe(path: Path, style: Style) -> Recipe:
    try:
        data = yaml.safe_load(Path(path).read_text())
    except FileNotFoundError:
        raise RecipeError(f"{path}: not found") from None
    return parse_recipe(data or {}, style, Path(path))


def find_recipe(root: Path, name: str) -> Path:
    """characters/<name>.yaml, or anywhere below characters/, or a path."""
    p = Path(name)
    if p.suffix in (".yaml", ".yml") and p.is_file():
        return p
    chars = Path(root) / "characters"
    direct = chars / f"{name}.yaml"
    if direct.is_file():
        return direct
    matches = sorted(chars.rglob(f"{name}.yaml"))
    if not matches:
        raise RecipeError(f"no recipe {name!r} under {chars}")
    return matches[0]


def all_recipes(root: Path, *, include_random: bool = False) -> list[Path]:
    chars = Path(root) / "characters"
    paths = sorted(chars.rglob("*.yaml")) if chars.is_dir() else []
    return [p for p in paths if include_random or "random" not in p.relative_to(chars).parts]
