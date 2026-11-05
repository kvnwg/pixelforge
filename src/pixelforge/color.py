"""Color helpers: hex and RGB, OKLCH, and ramp constraint checks.

OKLCH comes from sRGB through OKLab (Bjorn Ottosson's matrices): lightness L runs 0 to 1, chroma C
is 0 for grays and stays under about 0.09 for this style, hue h is in degrees, 0 to 360.

Ramp rules (STYLE_GUIDE.md section 4) come in two strengths:

- errors (hard limits, they block a build): lightness or chroma outside the limits, pure black or
  white, shades not ordered dark to light, a color darker than the outline;
- warnings (guidance for new ramps): the lightness step between shades and the hue shift per
  lighter step. The hue rule is skipped for near-gray ramps, where hue is meaningless.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal, Sequence

RGB = tuple[int, int, int]
Severity = Literal["error", "warning"]

ERROR_RULES = frozenset({"lightness", "chroma", "black_white", "order", "darker_than_outline"})
WARNING_RULES = frozenset({"L_step", "hue_shift"})

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_hex(value: object) -> bool:
    """True for a '#rrggbb' string."""
    return isinstance(value, str) and bool(_HEX.match(value))


def parse_hex(value: str) -> RGB:
    """'#3a263a' -> (58, 38, 58). Raises ValueError for anything that isn't '#rrggbb'."""
    if not is_hex(value):
        raise ValueError(f"not a #rrggbb color: {value!r}")
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def to_hex(rgb: Sequence[int]) -> str:
    """(58, 38, 58) -> '#3a263a'. Extra channels (alpha) are ignored."""
    channels = [int(c) for c in rgb[:3]]
    if len(channels) != 3 or any(not 0 <= c <= 255 for c in channels):
        raise ValueError(f"not an RGB triple in 0..255: {rgb!r}")
    return "#{:02x}{:02x}{:02x}".format(*channels)


@dataclass(frozen=True)
class OKLCH:
    L: float
    C: float
    h: float  # degrees, 0 <= h < 360

    def __str__(self) -> str:
        return f"L {self.L:.3f} C {self.C:.3f} h {self.h:.0f}"


def _linear(channel: int) -> float:
    v = channel / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def rgb_to_oklab(rgb: Sequence[int]) -> tuple[float, float, float]:
    r, g, b = (_linear(c) for c in rgb[:3])
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1.0 / 3.0), v) for v in (l, m, s))
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720453 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def rgb_to_oklch(rgb: Sequence[int]) -> OKLCH:
    L, a, b = rgb_to_oklab(rgb)
    return OKLCH(L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360.0)


def hex_to_oklch(value: str) -> OKLCH:
    return rgb_to_oklch(parse_hex(value))


def hue_delta(h0: float, h1: float) -> float:
    """Signed shortest turn from hue h0 to hue h1, in degrees, in (-180, 180]."""
    d = (h1 - h0) % 360.0
    return d - 360.0 if d > 180.0 else d


# --------------------------------------------------------------------------- ramp checks


@dataclass(frozen=True)
class Limits:
    """Hard limits for every color in a ramp. Breaking one is an error."""

    L_min: float
    L_max: float
    C_max: float
    tolerance: float = 0.0  # slack on L and C limits for 8-bit rounding of colors set on a limit
    outline_L: float | None = None  # no color may be darker than the outline


@dataclass(frozen=True)
class StepGuide:
    """Guidance between consecutive shades of a ramp. Breaking it is a warning."""

    L_step_min: float
    L_step_max: float
    L_step_slack: float
    hue_shift_min: float
    hue_shift_max: float
    hue_min_chroma: float  # ramps with a mean chroma below this skip the hue rule (near-gray)


@dataclass(frozen=True)
class Issue:
    severity: Severity
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.rule}: {self.message}"


def check_ramp(colors: Sequence[str], limits: Limits, guide: StepGuide | None = None) -> list[Issue]:
    """Check a ramp (darkest shade first) against hard limits and, optionally, the step guide."""
    issues: list[Issue] = []
    lch = [hex_to_oklch(c) for c in colors]
    tol = limits.tolerance

    for i, (value, c) in enumerate(zip(colors, lch)):
        name = f"shade {i} {value}"
        if value.lower() in ("#000000", "#ffffff"):
            issues.append(Issue("error", "black_white", f"{name} is pure black or white"))
        if c.L < limits.L_min - tol or c.L > limits.L_max + tol:
            issues.append(Issue(
                "error", "lightness",
                f"{name} has L {c.L:.3f}; allowed {limits.L_min:.2f} to {limits.L_max:.2f}"))
        if c.C > limits.C_max + tol:
            issues.append(Issue(
                "error", "chroma", f"{name} has C {c.C:.3f}; allowed up to {limits.C_max:.2f}"))
        if limits.outline_L is not None and c.L < limits.outline_L:
            issues.append(Issue(
                "error", "darker_than_outline",
                f"{name} (L {c.L:.3f}) is darker than the outline (L {limits.outline_L:.3f})"))

    for i in range(len(lch) - 1):
        if lch[i + 1].L <= lch[i].L:
            issues.append(Issue(
                "error", "order",
                f"shade {i + 1} {colors[i + 1]} is not lighter than shade {i} {colors[i]}"))

    if guide is not None and len(lch) > 1:
        lo, hi, slack = guide.L_step_min, guide.L_step_max, guide.L_step_slack
        for i in range(len(lch) - 1):
            step = lch[i + 1].L - lch[i].L
            if step < lo - slack or step > hi + slack:
                issues.append(Issue(
                    "warning", "L_step",
                    f"shade {i} to {i + 1} steps L by {step:.3f}; guide {lo:.2f} to {hi:.2f}"))
        mean_chroma = sum(c.C for c in lch) / len(lch)
        if mean_chroma >= guide.hue_min_chroma:
            for i in range(len(lch) - 1):
                shift = hue_delta(lch[i].h, lch[i + 1].h)
                if not guide.hue_shift_min <= shift <= guide.hue_shift_max:
                    issues.append(Issue(
                        "warning", "hue_shift",
                        f"shade {i} to {i + 1} shifts hue {shift:+.1f} deg; guide "
                        f"+{guide.hue_shift_min:g} to +{guide.hue_shift_max:g} per lighter step"))
    return issues
