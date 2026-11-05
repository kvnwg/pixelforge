"""Hand-broken sprites must each trigger the right validator rule (ARCHITECTURE.md section 18)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
import yaml

from pixelforge.build import build
from pixelforge.parts import Library, load_part
from pixelforge.sheet import mirror, shift
from pixelforge.validate import Validator, validate_part


@pytest.fixture(scope="module")
def girl(root, style):
    return build(root, "anchor_girl", style=style)


@pytest.fixture(scope="module")
def v(girl):
    return Validator(girl.composer)


def rules(findings) -> set[str]:
    return {f.rule for f in findings}


def broken(frame, image):
    sprite = np.where(image[..., 3:] == 255, image, 0).astype(np.uint8)
    return replace(frame, image=image, sprite=sprite)


def test_clean_frame_has_no_findings(girl, v):
    assert v.frame(girl.frames[("idle", "s")][0]) == []


def test_gap_in_the_outline_is_E4(girl, v):
    f = girl.frames[("idle", "s")][0]
    img = f.image.copy()
    img[15, 10] = 0  # remove an outline pixel beside the hair
    assert "E4" in rules(v.frame(broken(f, img)))


def test_stray_pixel_is_E5(girl, v):
    f = girl.frames[("idle", "s")][0]
    img = f.image.copy()
    img[4, 4] = (*girl.style.outline.rgb, 255)
    assert "E5" in rules(v.frame(broken(f, img)))


def test_off_palette_color_is_E2(girl, v):
    f = girl.frames[("idle", "s")][0]
    img = f.image.copy()
    img[16, 14] = (255, 0, 0, 255)
    found = v.frame(broken(f, img))
    assert "E2" in rules(found)
    assert any((14, 16) in fd.pixels for fd in found if fd.rule == "E2")


def test_baseline_drift_is_E6(girl, v):
    f = girl.frames[("idle", "s")][0]
    img, _ = shift(f.image, 0, -1)
    assert "E6" in rules(v.frame(broken(f, img)))


def test_soft_alpha_is_E3_and_sideways_drift_is_E7(girl, v):
    f = girl.frames[("idle", "s")][0]
    img = f.image.copy()
    img[16, 14, 3] = 128
    assert "E3" in rules(v.frame(broken(f, img)))
    moved, _ = shift(f.image, 3, 0)
    assert "E7" in rules(v.frame(broken(f, moved)))


def test_mirror_is_around_the_pivot_column():
    img = np.zeros((32, 32, 4), np.uint8)
    img[10, 20] = (1, 2, 3, 255)
    out, dropped = mirror(img, 15)
    assert out[10, 10].tolist() == [1, 2, 3, 255] and dropped == 0
    assert np.array_equal(mirror(out, 15)[0], img)
    img[10, 31] = (1, 2, 3, 255)  # x = 31 would land on x = -1
    assert mirror(img, 15)[1] == 1


def test_wrong_color_in_a_part_file_is_E13(root, style, tmp_path):
    src = root / "parts" / "belt" / "sash"
    folder = tmp_path / "parts" / "belt" / "sash"
    folder.mkdir(parents=True)
    (folder / "part.yaml").write_text((src / "part.yaml").read_text())
    from pixelforge.sheet import load_rgba, save_rgba
    img = load_rgba(src / "rigid.png")
    img[24, 12] = (0x5a, 0x55, 0x6b, 255)  # cloth in an accent part
    save_rgba(folder / "rigid.png", img)
    part = load_part(folder, style)
    found = validate_part(part, Library(tmp_path, style), style)
    assert "E13" in rules(found)


def test_missing_sheet_is_E14(root, style, girl):
    recipe = replace(girl.recipe, anims=("idle", "attack_slash"))
    b = build(root, recipe, style=style)
    assert any(f.rule == "E14" and "attack_slash" in f.message for f in b.findings)


def test_part_yaml_problems_are_reported(style, tmp_path):
    folder = tmp_path / "belt" / "sash"
    folder.mkdir(parents=True)
    (folder / "part.yaml").write_text(yaml.safe_dump(
        {"slot": "belt", "variant": "sash", "material": "velvet", "kind": "rigid"}))
    with pytest.raises(ValueError, match="material") as err:
        load_part(folder, style)
    assert "attach" in str(err.value)
