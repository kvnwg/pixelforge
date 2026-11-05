"""The `pf` command. Commands are added here as each phase builds them (see CLAUDE.md)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import typer

from . import __version__
from .palette import check_palette, format_report, render_swatches
from .style import Style, StyleError, find_root, load_style

app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help="pixelforge: build, validate and review pixel art characters.")


def _version(value: bool) -> None:
    if value:
        typer.echo(f"pixelforge {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(None, "--version", callback=_version, is_eager=True,
                                           help="Show the version and exit."),
) -> None:
    """pixelforge: build, validate and review pixel art characters.

    Runs against the repo it is called from, or $PIXELFORGE_ROOT.
    """


def _style() -> Style:
    try:
        return load_style()
    except (StyleError, FileNotFoundError) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from None


def _report(findings, quiet_warnings: bool = False) -> tuple[int, int]:
    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]
    for f in errors + ([] if quiet_warnings else warnings):
        typer.echo(f"  {f}")
    return len(errors), len(warnings)


@app.command()
def palette(
    check: bool = typer.Option(False, "--check",
                               help="Exit with status 1 if any ramp breaks a hard limit."),
    out: Optional[Path] = typer.Option(None, "--out",
                                       help="Swatch sheet path [default: review/palette_swatches.png]."),
) -> None:
    """Check every color ramp in style.json against its limits and render a swatch sheet."""
    style = _style()
    reports = check_palette(style)
    for line in format_report(reports, style):
        typer.echo(line)
    path = render_swatches(reports, style, out or style.root / "review" / "palette_swatches.png")
    typer.echo(f"swatches: {path}")
    if check and any(r.errors for r in reports):
        raise typer.Exit(1)


def _recipes(style: Style, names: list[str], all_: bool) -> list[Path]:
    from .recipe import all_recipes, find_recipe
    if all_:
        return all_recipes(style.root)
    if not names:
        typer.echo("error: name a recipe or pass --all", err=True)
        raise typer.Exit(2)
    return [find_recipe(style.root, n) for n in names]


@app.command("build")
def build_cmd(
    recipes: list[str] = typer.Argument(None, help="Recipe names (characters/<name>.yaml)."),
    all_: bool = typer.Option(False, "--all", help="Build every recipe in characters/."),
    out: Optional[Path] = typer.Option(None, "--out", help="Output folder [default: out/]."),
    no_gifs: bool = typer.Option(False, "--no-gifs", help="Skip the preview GIFs."),
) -> None:
    """Composite, validate and export recipes."""
    from .build import build
    from .export import export
    from .recipe import load_recipe
    style = _style()
    total_errors = 0
    for path in _recipes(style, recipes or [], all_):
        recipe = load_recipe(path, style)
        b = build(style.root, recipe, style=style)
        folder, export_findings = export(b, out or style.root / "out", gifs=not no_gifs)
        n = sum(len(v) for v in b.frames.values())
        e, w = _report(b.findings + export_findings)
        total_errors += e
        typer.echo(f"{recipe.name}: {n} frames -> {folder}  ({e} errors, {w} warnings)")
        for line in b.not_drawn:
            typer.echo(f"  not drawn yet: {line}")
    if total_errors:
        raise typer.Exit(1)


@app.command()
def validate(
    paths: list[str] = typer.Argument(None, help="Part folders or recipe names; default: all."),
) -> None:
    """Run every validator rule on parts and recipes. Exits 1 on errors."""
    from .build import build
    from .parts import Library, load_part
    from .recipe import all_recipes, find_recipe, load_recipe
    from .validate import validate_part
    style = _style()
    lib = Library(style.root, style)
    parts, recipes = [], []
    for p in paths or []:
        folder = Path(p)
        if (folder / "part.yaml").is_file():
            parts.append(load_part(folder.resolve(), style))
        else:
            recipes.append(find_recipe(style.root, p))
    if not paths:
        parts = lib.all_parts()
        recipes = all_recipes(style.root, include_random=True)
    findings = []
    for part in parts:
        findings += validate_part(part, lib, style)
    for path in recipes:
        findings += build(style.root, load_recipe(path, style), style=style, library=lib).findings
    e, w = _report(findings)
    typer.echo(f"validated {len(parts)} parts and {len(recipes)} recipes: {e} errors, {w} warnings")
    if e:
        raise typer.Exit(1)


@app.command()
def review(
    recipe: str = typer.Argument(..., help="Recipe name."),
    anim: Optional[list[str]] = typer.Option(None, "--anim", help="Only these animations."),
    direction: Optional[list[str]] = typer.Option(None, "--dir", help="Only these directions."),
    recolors: bool = typer.Option(False, "--recolors",
                                  help="Also render the recolor grid from style/recolor_test.json."),
) -> None:
    """Render review images into review/<name>/ (then open them)."""
    import json

    from .build import build
    from .review import recolor_grid, render_all
    style = _style()
    b = build(style.root, recipe, style=style)
    out = style.root / "review" / b.recipe.name
    written = render_all(b, out, anim, direction)
    if recolors:
        spec = json.loads((style.root / "style" / "recolor_test.json").read_text())
        path = out / "recolor_grid.png"
        recolor_grid(b, spec["combos"], style.root / spec["reference_1x"]).save(path)
        written.append(path)
    _report(b.findings)
    typer.echo(f"{len(written)} review images in {out}")


@app.command()
def anchors(
    check: bool = typer.Option(True, "--check/--no-check", help="Render the anchor check image."),
    rig: str = typer.Option("humanoid", "--rig", help="Rig to check."),
) -> None:
    """Render every base body frame with its anchor points marked."""
    from .build import build
    from .recipe import parse_recipe
    from .review import anchors_check
    from .rig import load_rig
    style = _style()
    r = load_rig(style.root, style, rig)
    anims = [a for a in r.anchors if a in style.raw["animations"]]
    bare = parse_recipe({"name": f"{rig}_bare", "rig": rig, "parts": {}, "anims": anims}, style)
    b = build(style.root, bare, style=style, validate=False)
    out = style.root / "review" / f"anchors_{rig}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    anchors_check(r, b).save(out)
    typer.echo(f"anchors: {out}")


@app.command()
def diff(a: Path, b: Path, out: Optional[Path] = typer.Option(None, "--out")) -> None:
    """Pixel diff of two PNGs: count, and an image with differences in red."""
    from PIL import Image

    from .sheet import load_rgba
    x, y = load_rgba(a), load_rgba(b)
    if x.shape != y.shape:
        typer.echo(f"different sizes: {x.shape[1]}x{x.shape[0]} vs {y.shape[1]}x{y.shape[0]}")
        raise typer.Exit(1)
    mask = np.any(x != y, axis=-1)
    typer.echo(f"{int(mask.sum())} pixels differ")
    if out:
        img = (x[..., :3] * 0.35 + 160).astype(np.uint8)
        img[mask] = (214, 69, 65)
        Image.fromarray(img).resize((img.shape[1] * 8, img.shape[0] * 8), Image.NEAREST).save(out)
        typer.echo(f"diff image: {out}")
    if mask.any():
        raise typer.Exit(1)


@app.command()
def preview(
    port: int = typer.Option(8000, "--port", help="Port for the local server."),
    bundle: Optional[Path] = typer.Option(None, "--bundle",
                                          help="Write a single self-contained HTML file instead."),
) -> None:
    """Serve tools/preview (reads out/index.json), or bundle it into one HTML file."""
    from .bundle import write_bundle
    style = _style()
    if bundle:
        path = write_bundle(style.root, bundle)
        typer.echo(f"bundle: {path} ({path.stat().st_size // 1024} KB)")
        return
    import functools
    import http.server
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(style.root))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        typer.echo(f"preview: http://127.0.0.1:{port}/tools/preview/  (Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
