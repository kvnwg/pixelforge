"""Auto-outline: the 4-neighbor ring with open soles (ARCHITECTURE.md section 10).

    silhouette = opaque pixels that are not outline-colored (shadow excluded)
    ring       = transparent pixels with a silhouette pixel directly up, down, left or right
    lowest     = lowest row containing silhouette or hand-placed outline
    a ring pixel touching the silhouette only from above, at or below lowest - (sole_rows - 1),
    is left open (open soles: the ground shadow shows there); every other ring pixel is outlined
    hand-placed outline pixels (outline-colored pixels already in the art) are kept as they are

Diagonal-only neighbors are never outlined, which is what rounds the corners. Applied to the anchor
with its outline removed except the four hand-placed pixels, this reproduces it exactly (tested).
Input frames must have binary alpha: outline first, then composite the translucent shadow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

import numpy as np

from .color import RGB

if TYPE_CHECKING:
    from .style import OutlineSpec


@dataclass(frozen=True)
class OutlineResult:
    image: np.ndarray  # H x W x 4 uint8: the input with the outline drawn
    ring: np.ndarray  # bool H x W: pixels this pass drew in the outline color
    open: np.ndarray  # bool H x W: ring pixels left open by the open-soles rule


def _check_rgba(img: np.ndarray) -> None:
    if not isinstance(img, np.ndarray) or img.dtype != np.uint8 or img.ndim != 3 or img.shape[2] != 4:
        raise ValueError("expected an H x W x 4 uint8 RGBA array")
    if not np.isin(img[..., 3], (0, 255)).all():
        raise ValueError("alpha must be 0 or 255; outline before compositing the shadow")


def outline_colored(img: np.ndarray, color: RGB) -> np.ndarray:
    """Opaque pixels drawn in the outline color (hand-placed details)."""
    return (img[..., 3] == 255) & np.all(img[..., :3] == np.asarray(color, np.uint8), axis=-1)


def silhouette(img: np.ndarray, color: RGB) -> np.ndarray:
    """Opaque pixels that are not outline-colored."""
    return (img[..., 3] == 255) & ~outline_colored(img, color)


def outline(img: np.ndarray, color: RGB, *, open_soles: bool = True, sole_rows: int = 3
            ) -> OutlineResult:
    """Draw the generated outline around `img`'s silhouette. Returns a new array."""
    _check_rgba(img)
    opaque = img[..., 3] == 255
    hand = outline_colored(img, color)
    sil = opaque & ~hand
    p = np.pad(sil, 1)
    up, down = p[:-2, 1:-1], p[2:, 1:-1]  # silhouette at (x, y-1) / (x, y+1)
    left, right = p[1:-1, :-2], p[1:-1, 2:]  # silhouette at (x-1, y) / (x+1, y)
    ring = ~opaque & (up | down | left | right)
    open_ = np.zeros_like(ring)
    rows = np.flatnonzero((sil | hand).any(axis=1))
    if open_soles and rows.size:
        lowest = int(rows[-1])
        below_cut = (np.arange(sil.shape[0]) >= lowest - (sole_rows - 1))[:, None]
        open_ = ring & up & ~down & ~left & ~right & below_cut
    drawn = ring & ~open_
    out = img.copy()
    out[drawn] = (*color, 255)
    return OutlineResult(out, drawn, open_)


def apply_outline(img: np.ndarray, spec: OutlineSpec) -> OutlineResult:
    """`outline` with the color and open-soles settings from style.json."""
    return outline(img, spec.rgb, open_soles=spec.open_soles, sole_rows=spec.sole_rows)


def strip_outline(img: np.ndarray, color: RGB, keep: Iterable[tuple[int, int]] = ()) -> np.ndarray:
    """A copy with every outline-colored pixel made transparent, except the (x, y) in `keep`."""
    mask = outline_colored(img, color)
    for x, y in keep:
        mask[y, x] = False
    out = img.copy()
    out[mask] = 0
    return out
