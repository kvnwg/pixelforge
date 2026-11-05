from __future__ import annotations

from typer.testing import CliRunner

from pixelforge import __version__
from pixelforge.cli import app

runner = CliRunner()


def test_palette_check_passes_and_writes_swatches(root, tmp_path):
    out = tmp_path / "swatches.png"
    result = runner.invoke(app, ["palette", "--check", "--out", str(out)],
                           env={"PIXELFORGE_ROOT": str(root)})
    assert result.exit_code == 0, result.output
    assert "0 errors" in result.output
    assert out.is_file()


def test_palette_check_fails_on_a_bad_color(raw_style, style_root, tmp_path):
    raw_style["materials"]["hair"]["presets"]["neon"] = ["#7d1d2c", "#c8323a", "#ee6150"]
    bad_root = style_root(raw_style)
    result = runner.invoke(app, ["palette", "--check", "--out", str(tmp_path / "s.png")],
                           env={"PIXELFORGE_ROOT": str(bad_root)})
    assert result.exit_code == 1
    assert "ERROR" in result.output and "hair/neon" in result.output


def test_broken_style_exits_2(raw_style, style_root):
    del raw_style["outline"]
    result = runner.invoke(app, ["palette"], env={"PIXELFORGE_ROOT": str(style_root(raw_style))})
    assert result.exit_code == 2
    assert "outline: missing" in result.output


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0 and __version__ in result.output
