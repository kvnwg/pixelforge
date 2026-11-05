"""Effects that need no art (ARCHITECTURE.md section 13): flash, closed eyes, dissolve, shadow."""

from __future__ import annotations

import numpy as np

from .color import RGB
from .style import ShadowSpec

# 4x4 Bayer matrix: dissolve step k (1..4) removes pixels whose threshold is below k * 4.
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def flash(sprite: np.ndarray, outline: RGB, color: RGB) -> np.ndarray:
    """Every non-outline opaque pixel becomes the flash color; the outline is unchanged."""
    out = sprite.copy()
    opaque = out[..., 3] == 255
    is_outline = np.all(out[..., :3] == np.asarray(outline, np.uint8), axis=-1)
    out[opaque & ~is_outline, :3] = color
    return out


def close_eyes(sprite: np.ndarray, eye_mask: np.ndarray, lid: RGB) -> np.ndarray:
    out = sprite.copy()
    out[eye_mask & (out[..., 3] == 255), :3] = lid
    return out


def dissolve(sprite: np.ndarray, step: int) -> np.ndarray:
    """Remove 25% of pixels per step (1 to 4) in a Bayer pattern, outline included."""
    h, w = sprite.shape[:2]
    thresholds = np.tile(BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w]
    out = sprite.copy()
    out[thresholds < step * 4] = 0
    return out


def shadow_layer(spec: ShadowSpec, rgb: RGB, size: int, *, rows: dict[int, tuple[int, int]] | None = None
                 ) -> np.ndarray:
    """The translucent ground shadow: outline color at the shadow alpha, never outlined."""
    layer = np.zeros((size, size, 4), np.uint8)
    for y, (x0, x1) in (rows or spec.rows).items():
        if 0 <= y < size:
            layer[y, max(0, x0):min(size, x1 + 1)] = (*rgb, spec.alpha)
    return layer


def over_shadow(sprite: np.ndarray, shadow: np.ndarray) -> np.ndarray:
    """The sprite (binary alpha) over the shadow: sprite pixels replace, elsewhere the shadow."""
    return np.where(sprite[..., 3:] == 255, sprite, shadow)


def composite_on(image: np.ndarray, background: RGB) -> np.ndarray:
    """Flatten RGBA onto a solid background, with the rounding the reference images use."""
    rgb = image[..., :3].astype(np.int32)
    a = image[..., 3:].astype(np.int32)
    bg = np.asarray(background, np.int32)
    out = (rgb * a + bg * (255 - a) + 127) // 255
    return out.astype(np.uint8)
