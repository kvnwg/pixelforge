"""Recoloring: map a material's base ramp onto a preset ramp, shade i to shade i (section 11).

Each part declares exactly one material, so colors shared between materials (eyes and cloth,
leather and hair) never collide. Outline-colored pixels pass through untouched.
"""

from __future__ import annotations

import numpy as np

from .color import RGB, parse_hex
from .style import Material, Style


def ramp_map(material: Material, preset: tuple[str, ...]) -> dict[RGB, RGB]:
    if len(preset) != material.shades:
        raise ValueError(f"{material.name}: preset has {len(preset)} shades, needs {material.shades}")
    return {parse_hex(b): parse_hex(p) for b, p in zip(material.base, preset)}


def preset_ramp(style: Style, material: str, preset: str | None) -> tuple[str, ...]:
    m = style.materials[material]
    return m.presets[preset] if preset else m.base


def recolor(cell: np.ndarray, mapping: dict[RGB, RGB]) -> np.ndarray:
    out = cell.copy()
    if all(k == v for k, v in mapping.items()):
        return out
    opaque = cell[..., 3] == 255
    for src, dst in mapping.items():
        mask = opaque & np.all(cell[..., :3] == np.asarray(src, np.uint8), axis=-1)
        out[mask, :3] = dst
    return out
