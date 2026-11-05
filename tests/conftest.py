from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from pixelforge.style import Style, load_style

ROOT = Path(__file__).resolve().parents[1]


def read_rgba(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGBA"))


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def style() -> Style:
    return load_style(ROOT / "style" / "style.json")


@pytest.fixture
def raw_style() -> dict:
    """A fresh, mutable copy of style.json."""
    return json.loads((ROOT / "style" / "style.json").read_text())


@pytest.fixture
def style_root(tmp_path: Path):
    """Write a (modified) style.json into a throwaway repo root and return that root."""

    def write(data: dict) -> Path:
        (tmp_path / "style").mkdir(exist_ok=True)
        (tmp_path / "src" / "pixelforge").mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "style" / "anchor.png", tmp_path / "style" / "anchor.png")
        (tmp_path / "style" / "style.json").write_text(json.dumps(data, indent=2))
        return tmp_path

    return write
