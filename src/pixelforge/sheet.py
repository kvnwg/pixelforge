"""Sheets: one PNG per (part, animation), a grid of square cells (ARCHITECTURE.md section 4).

Rows are the drawn directions in style order (s, e, n; w is mirrored, never stored); columns are
frames. A fully transparent cell means the part draws nothing in that frame. Rigid parts keep
their one pose per direction in `rigid.png`, a sheet with a single column.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image


def load_rgba(path: str | Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.array(im.convert("RGBA"))


def save_rgba(path: str | Path, arr: np.ndarray) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.ascontiguousarray(arr, dtype=np.uint8), "RGBA").save(path)
    return path


def blank(size: int) -> np.ndarray:
    return np.zeros((size, size, 4), np.uint8)


class SheetError(ValueError):
    pass


class Sheet:
    def __init__(self, image: np.ndarray, cell: int, rows: Sequence[str], path: Path | None = None):
        h, w = image.shape[:2]
        if w % cell or h % cell or w == 0:
            raise SheetError(f"{path}: {w} x {h} is not a grid of {cell} px cells")
        if h // cell != len(rows):
            raise SheetError(f"{path}: has {h // cell} rows of cells; expected {len(rows)} "
                             f"({', '.join(rows)})")
        self.image, self.cell, self.rows, self.path = image, cell, tuple(rows), path

    @classmethod
    def load(cls, path: str | Path, cell: int, rows: Sequence[str]) -> "Sheet":
        return cls(load_rgba(path), cell, rows, Path(path))

    @property
    def frames(self) -> int:
        return self.image.shape[1] // self.cell

    def get(self, direction: str, frame: int) -> np.ndarray | None:
        """A copy of one cell, or None when the sheet has no such row or column."""
        if direction not in self.rows or not 0 <= frame < self.frames:
            return None
        r, c = self.rows.index(direction), self.cell
        return self.image[r * c:(r + 1) * c, frame * c:(frame + 1) * c].copy()

    def cells(self):
        for d in self.rows:
            for f in range(self.frames):
                yield d, f, self.get(d, f)


def write_sheet(path: str | Path, cells: dict[tuple[str, int], np.ndarray], rows: Sequence[str],
                frames: int, cell: int) -> Path:
    img = np.zeros((len(rows) * cell, frames * cell, 4), np.uint8)
    for (d, f), arr in cells.items():
        r = list(rows).index(d)
        img[r * cell:(r + 1) * cell, f * cell:(f + 1) * cell] = arr
    return save_rgba(path, img)


def shift(img: np.ndarray, dx: int, dy: int) -> tuple[np.ndarray, int]:
    """Translate by whole pixels. Returns the moved image and how many opaque pixels fell off."""
    out = np.zeros_like(img)
    h, w = img.shape[:2]
    ys0, ys1 = max(0, -dy), min(h, h - dy)
    xs0, xs1 = max(0, -dx), min(w, w - dx)
    if ys0 < ys1 and xs0 < xs1:
        out[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] = img[ys0:ys1, xs0:xs1]
    dropped = int((img[..., 3] > 0).sum() - (out[..., 3] > 0).sum())
    return out, dropped


def mirror(img: np.ndarray, axis: int) -> tuple[np.ndarray, int]:
    """Mirror around column `axis` (x_new = 2 * axis - x), never around the canvas center.
    Returns the mirrored image and how many opaque pixels would land outside the canvas."""
    out = np.zeros_like(img)
    w = img.shape[1]
    dropped = 0
    for x in range(w):
        x2 = 2 * axis - x
        if 0 <= x2 < w:
            out[:, x2] = img[:, x]
        else:
            dropped += int((img[:, x, 3] > 0).sum())
    return out, dropped
