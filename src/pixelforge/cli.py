"""The `pf` command. Commands are added here as each phase builds them (see CLAUDE.md)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .palette import check_palette, format_report, render_swatches
from .style import StyleError, load_style

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


@app.command()
def palette(
    check: bool = typer.Option(False, "--check",
                               help="Exit with status 1 if any ramp breaks a hard limit."),
    out: Optional[Path] = typer.Option(None, "--out",
                                       help="Swatch sheet path [default: review/palette_swatches.png]."),
) -> None:
    """Check every color ramp in style.json against its limits and render a swatch sheet."""
    try:
        style = load_style()
    except (StyleError, FileNotFoundError) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from None
    reports = check_palette(style)
    for line in format_report(reports, style):
        typer.echo(line)
    path = render_swatches(reports, style, out or style.root / "review" / "palette_swatches.png")
    typer.echo(f"swatches: {path}")
    if check and any(r.errors for r in reports):
        raise typer.Exit(1)
