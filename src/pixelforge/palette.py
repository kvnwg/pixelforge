"""`pf palette --check`: every color ramp in style.json against its limits, plus a swatch sheet.

Which limits apply:

- outline and character material presets: `constraints` (L 0.30 to 0.80, C up to 0.09), plus the
  step guide (lightness step and hue shift between shades) as warnings;
- glow eye presets (`materials.<m>.glow_presets`): `glow_constraints`;
- FX ramps and the flash color: `fx_constraints`.

Warnings listed in `constraints.accepted_ramp_warnings` are known deviations (the anchor's own
ramps, mostly) and are reported as accepted, with their reason. See STYLE_GUIDE.md section 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .color import OKLCH, Issue, Limits, StepGuide, check_ramp, hex_to_oklch, parse_hex
from .style import Style

GROUP_TITLES = {
    "outline": "Outline",
    "character": "Character and monster materials",
    "glow": "Glow eyes (allowed brighter, enemies only)",
    "fx": "FX ramps (brighter on purpose)",
    "effect": "Effects",
}


@dataclass(frozen=True)
class RampReport:
    id: str
    group: str
    colors: tuple[str, ...]
    lch: tuple[OKLCH, ...]
    errors: tuple[Issue, ...]
    warnings: tuple[Issue, ...]  # not accepted
    accepted: tuple[Issue, ...]  # accepted in style.json
    reason: str | None  # why the accepted warnings are fine

    @property
    def status(self) -> str:
        if self.errors:
            return "error"
        if self.warnings:
            return "warning"
        return "accepted" if self.accepted else "ok"


def check_palette(style: Style) -> list[RampReport]:
    k = style.constraints
    outline_L = hex_to_oklch(style.outline.color).L

    def limits(group_limits, floor: float | None) -> Limits:
        lo, hi = group_limits.L_range
        return Limits(lo, hi, group_limits.C_max, k.tolerance, floor)

    by_group = {
        "outline": limits(k.character, outline_L),
        "character": limits(k.character, outline_L),
        "glow": limits(k.glow, outline_L),
        "fx": limits(k.fx, None),
        "effect": limits(k.fx, None),
    }
    guide = StepGuide(k.L_step[0], k.L_step[1], k.L_step_slack, k.hue_shift[0], k.hue_shift[1],
                      k.hue_min_chroma)
    reports = []
    for ramp in style.ramps():
        issues = check_ramp(ramp.colors, by_group[ramp.group],
                            guide if ramp.group == "character" else None)
        acc = k.accepted.get(ramp.id)
        accepted_rules = acc.rules if acc else frozenset()
        warnings = [i for i in issues if i.severity == "warning"]
        open_warnings = [i for i in warnings if i.rule not in accepted_rules]
        for rule in sorted(accepted_rules - {i.rule for i in warnings}):
            open_warnings.append(Issue(
                "warning", "stale_acceptance",
                f"{rule} is accepted for this ramp but no longer fires; remove it from "
                "constraints.accepted_ramp_warnings"))
        reports.append(RampReport(
            id=ramp.id, group=ramp.group, colors=ramp.colors,
            lch=tuple(hex_to_oklch(c) for c in ramp.colors),
            errors=tuple(i for i in issues if i.severity == "error"),
            warnings=tuple(open_warnings),
            accepted=tuple(i for i in warnings if i.rule in accepted_rules),
            reason=acc.reason if acc else None,
        ))
    return reports


def counts(reports: list[RampReport]) -> dict[str, int]:
    out = {"error": 0, "warning": 0, "accepted": 0, "ok": 0}
    for r in reports:
        out[r.status] += 1
    return out


def format_report(reports: list[RampReport], style: Style) -> list[str]:
    width = max(len(r.id) for r in reports)
    lines = [f"palette check: style {style.name!r}, {len(reports)} ramps"]
    for r in reports:
        lines.append(f"  {r.status.upper() if r.status in ('error', 'warning') else r.status:<9}"
                     f"{r.id:<{width}}  {' '.join(r.colors)}")
        for issue in (*r.errors, *r.warnings):
            lines.append(f"{'':11}{issue}")
        if r.accepted:
            lines.append(f"{'':11}accepted ({', '.join(sorted({i.rule for i in r.accepted}))}): "
                         f"{r.reason}")
    n = counts(reports)
    lines.append(f"summary: {n['error']} errors, {n['warning']} warnings, "
                 f"{n['accepted']} accepted, {n['ok']} ok")
    return lines


# --------------------------------------------------------------------------- swatch sheet

_INK = (43, 43, 51)
_PAPER = (243, 239, 226)
_EDGE = (138, 132, 120)
_STATUS_INK = {"ok": (61, 107, 69), "accepted": (122, 116, 104), "warning": (166, 114, 31),
               "error": (176, 58, 46)}


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow without FreeType sizing
        return ImageFont.load_default()


def render_swatches(reports: list[RampReport], style: Style, out_path: Path, *, cell: int = 22
                    ) -> Path:
    """Write a swatch sheet: one row per ramp, grouped, with OKLCH range and check status."""
    font, small, title = _font(13), _font(11), _font(16)
    pad, row_h, label_w = 14, cell + 8, 210
    max_shades = max(len(r.colors) for r in reports)
    sw_w = max_shades * (cell + 3)
    info_x = pad + label_w + sw_w + 14
    status_x = info_x + 190
    width = status_x + 170
    groups = [g for g in GROUP_TITLES if any(r.group == g for r in reports)]
    height = pad + 52 + sum(30 + row_h * sum(r.group == g for r in reports) for g in groups) + pad

    img = Image.new("RGB", (width, height), _PAPER)
    d = ImageDraw.Draw(img)
    n = counts(reports)
    d.text((pad, pad), f"pixelforge palette: {style.name}", fill=_INK, font=title)
    d.text((pad, pad + 24), f"{len(reports)} ramps   {n['error']} errors   {n['warning']} warnings"
                            f"   {n['accepted']} accepted   {n['ok']} ok", fill=_INK, font=font)
    y = pad + 52
    for g in groups:
        d.text((pad, y + 8), GROUP_TITLES[g], fill=_INK, font=title)
        y += 30
        for r in (r for r in reports if r.group == g):
            d.text((pad + 8, y + (cell - 13) // 2), r.id, fill=_INK, font=font)
            for i, hexv in enumerate(r.colors):
                x = pad + label_w + i * (cell + 3)
                d.rectangle((x, y, x + cell - 1, y + cell - 1), fill=parse_hex(hexv), outline=_EDGE)
            Ls = [c.L for c in r.lch]
            info = (f"L {min(Ls):.2f}-{max(Ls):.2f}  C<={max(c.C for c in r.lch):.3f}"
                    if len(Ls) > 1 else f"L {Ls[0]:.2f}  C {r.lch[0].C:.3f}")
            d.text((info_x, y + (cell - 11) // 2), info, fill=_INK, font=small)
            if r.status in ("error", "warning"):
                first = (r.errors or r.warnings)[0]
                note = f"{r.status}: {first.rule}" + (" (+more)" if len(r.errors) + len(r.warnings) > 1 else "")
            elif r.status == "accepted":
                note = f"accepted: {', '.join(sorted({i.rule for i in r.accepted}))}"
            else:
                note = "ok"
            d.text((status_x, y + (cell - 11) // 2), note, fill=_STATUS_INK[r.status], font=small)
            y += row_h
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path
