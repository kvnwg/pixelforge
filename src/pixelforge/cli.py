"""The `pf` command. Commands are added here as each phase builds them (see CLAUDE.md)."""

from __future__ import annotations

from dataclasses import replace
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
    combat: bool = typer.Option(False, "--combat", help="Also render combat timelines."),
) -> None:
    """Render review images into review/<name>/ (then open them)."""
    import json

    from .build import build
    from .review import recolor_grid, render_all
    style = _style()
    b = build(style.root, recipe, style=style)
    out = style.root / "review" / b.recipe.name
    written = render_all(b, out, anim, direction, combat=combat)
    if recolors:
        spec = json.loads((style.root / "style" / "recolor_test.json").read_text())
        path = out / "recolor_grid.png"
        recolor_grid(b, spec["combos"], style.root / spec["reference_1x"]).save(path)
        written.append(path)
    _report(b.findings)
    typer.echo(f"{len(written)} review images in {out}")


fx_app = typer.Typer(help="FX assets: build, validate and review (COMBAT.md section 6).")
app.add_typer(fx_app, name="fx")


@fx_app.command("build")
def fx_build(
    names: Optional[list[str]] = typer.Argument(None, help="FX folder names (fx/<name>)."),
    all_: bool = typer.Option(False, "--all", help="Build every FX."),
) -> None:
    """Validate FX against fx_ramps and export sheets + JSON to out/fx/ (exit 1 on errors)."""
    from .fx import character_fx_colors, export, find_fx, fx_folders, load_fx, update_fx_index, validate_fx
    style = _style()
    folders = fx_folders(style.root) if all_ or not names else [find_fx(style.root, n) for n in names]
    out_root = style.root / "out" / "fx"
    findings, entries = list(character_fx_colors(style)), []
    for folder in folders:
        fx = load_fx(folder, style)
        found = validate_fx(fx, style)
        findings += found
        if not any(f.level == "error" for f in found):
            entries += export(fx, style, out_root)
    update_fx_index(out_root, entries)
    for f in findings:
        typer.echo(f"  {f}")
    errors = sum(f.level == "error" for f in findings)
    typer.echo(f"fx: {len(entries)} exported from {len(folders)} folders to {out_root}  "
               f"({errors} errors, {len(findings) - errors} warnings)")
    if errors:
        raise typer.Exit(1)


@fx_app.command("review")
def fx_review_cmd(
    names: Optional[list[str]] = typer.Argument(None, help="FX names (variants like impact_fire)."),
) -> None:
    """Render review/fx/<name>.png for each FX (all if none named) and fx_overview.png."""
    from .fx import FXLibrary
    from .review import fx_overview, fx_review
    style = _style()
    lib = FXLibrary(style.root, style)
    out = style.root / "review" / "fx"
    out.mkdir(parents=True, exist_ok=True)
    for name in names or lib.names():
        fx_review(lib, name, style).save(out / f"{name}.png")
    fx_overview(lib, style).save(out / "fx_overview.png")
    typer.echo(f"fx review: {len(names or lib.names())} images and fx_overview.png in {out}")


@app.command()
def battle(
    attacker: str = typer.Argument(..., help="Attacking recipe."),
    defender: str = typer.Argument(..., help="Defending recipe (reacts with hurt)."),
    anim: str = typer.Option("attack_slash", "--anim", help="The attack to play."),
    direction: Optional[list[str]] = typer.Option(None, "--dir", help="Facing (default: e)."),
    profile: Optional[str] = typer.Option(None, "--profile",
                                          help="Timing profile for the attacker (player, enemy...)."),
    element: str = typer.Option("arcane", "--element",
                                help="Spell element for cast: fire, ice, poison, arcane, holy."),
) -> None:
    """Render battle_<a>_vs_<b>.png: the attack against a reacting defender, with its FX."""
    from dataclasses import replace as _replace

    from .build import build
    from .fx import FXLibrary, fx_folders
    from .recipe import find_recipe, load_recipe
    from .review import battle_image
    style = _style()
    fxlib = FXLibrary(style.root, style) if fx_folders(style.root) else None
    a_recipe = load_recipe(find_recipe(style.root, attacker), style)
    if profile:
        a_recipe = _replace(a_recipe, timing_profile=profile)
    if anim not in a_recipe.anims:
        a_recipe = _replace(a_recipe, anims=tuple(a_recipe.anims) + (anim,))
    a = build(style.root, a_recipe, style=style, validate=False)
    dfn = build(style.root, defender, style=style, validate=False)
    out_dir = style.root / "review" / "battle"
    out_dir.mkdir(parents=True, exist_ok=True)
    for d in direction or ["e"]:
        suffix = "" if d == "e" else f"_{d}"
        tag = f"_{profile}" if profile else ""
        tag += f"_{element}" if anim == "cast" else ""
        path = out_dir / f"battle_{a.recipe.name}_vs_{dfn.recipe.name}_{anim}{suffix}{tag}.png"
        battle_image(a, dfn, anim, d, fxlib=fxlib, element=element).save(path)
        typer.echo(f"battle: {path}")


@app.command()
def anchors(
    check: bool = typer.Option(True, "--check/--no-check", help="Render the anchor check image."),
    rig: str = typer.Option("humanoid", "--rig", help="Rig to check."),
    anim: Optional[list[str]] = typer.Option(None, "--anim", help="Only these animations."),
) -> None:
    """Render every base body frame with its anchor points marked."""
    from .build import build
    from .recipe import parse_recipe
    from .review import anchors_check
    from .rig import load_rig
    style = _style()
    r = load_rig(style.root, style, rig)
    anims = [a for a in r.anchors if a in style.raw["animations"] and (not anim or a in anim)]
    if anim:
        r = replace(r, anchors={a: v for a, v in r.anchors.items() if a in anims})
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


@app.command()
def template(
    slot: str = typer.Argument(..., help="Slot, e.g. headwear."),
    variant: str = typer.Argument(..., help="Variant name, e.g. wizard_hat."),
    anim: str = typer.Argument(..., help="Animation (or 'rigid' for a rigid part's 3 cells)."),
    rig: str = typer.Option("humanoid", "--rig"),
) -> None:
    """Write an empty sheet and a *_guide.png with the base body ghosted in every cell."""
    from .template import write_template
    style = _style()
    sheet, guide = write_template(style, slot, variant, anim, rig)
    typer.echo(f"sheet: {sheet}\nguide: {guide}  (put it on a reference layer in Aseprite)")


@app.command("random")
def random_cmd(
    seed: int = typer.Option(1, "--seed"),
    count: int = typer.Option(12, "--count"),
    out: Optional[Path] = typer.Option(None, "--out", help="Output folder [default: out/]."),
) -> None:
    """Generate random characters (characters/random/), build them, and render a gallery."""
    from .build import build
    from .export import export
    from .randomize import random_recipes
    from .review import random_gallery
    style = _style()
    recipes = random_recipes(style, seed, count)
    folder = style.root / "characters" / "random"
    folder.mkdir(parents=True, exist_ok=True)
    builds, errors = [], 0
    for r in recipes:
        (folder / f"{r.name}.yaml").write_text(r.to_yaml())
        b = build(style.root, r, style=style)
        _, ef = export(b, out or style.root / "out", gifs=False)
        e, w = _report(b.findings + ef)
        errors += e
        builds.append(b)
        parts = ", ".join(f"{s}/{v}" for s, v in sorted(r.parts.items()))
        typer.echo(f"{r.name}: {e} errors, {w} warnings  [{parts}]")
    path = style.root / "review" / f"random_{seed}_gallery.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    random_gallery(builds).save(path)
    typer.echo(f"gallery: {path}")
    if errors:
        raise typer.Exit(1)
