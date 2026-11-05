"""Review renders (ARCHITECTURE.md section 17, QUALITY.md section 2).

Images that make problems visible: open them and describe what you see before judging.
Display scaling is nearest-neighbor only; ghosting and grids exist only in these review images.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .build import Build
from .color import parse_hex, to_hex
from .compose import EMPTY, OUTLINE, Frame
from .effects import composite_on
from .rig import Rig
from .sheet import load_rgba

INK = (43, 43, 51)
PAPER = (243, 239, 226)
RED, GREEN, YELLOW, BLUE = (214, 69, 65), (70, 170, 80), (230, 190, 40), (60, 120, 220)


def font(size: int = 12):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def big(img: np.ndarray, k: int) -> np.ndarray:
    return np.repeat(np.repeat(img, k, axis=0), k, axis=1)


def flat(img: np.ndarray, bg: tuple[int, int, int]) -> np.ndarray:
    return composite_on(img, bg)


def bgs(b: Build) -> dict[str, tuple[int, int, int]]:
    return {k: parse_hex(v) for k, v in b.style.raw["preview_backgrounds"].items()}


def canvas(w: int, h: int, color=PAPER) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGB", (w, h), color)
    return im, ImageDraw.Draw(im)


def paste(im: Image.Image, arr: np.ndarray, x: int, y: int) -> None:
    im.paste(Image.fromarray(arr[..., :3].astype(np.uint8), "RGB"), (x, y))


def pixel_grid(arr: np.ndarray, k: int, color=(0, 0, 0), strength: float = 0.12) -> np.ndarray:
    out = arr.astype(np.float32).copy()
    out[::k, :] = out[::k, :] * (1 - strength) + np.asarray(color) * strength
    out[:, ::k] = out[:, ::k] * (1 - strength) + np.asarray(color) * strength
    return out.astype(np.uint8)


def mark_guides(arr: np.ndarray, k: int, pivot: tuple[int, int]) -> np.ndarray:
    """Baseline (red line under the baseline row) and pivot column (blue ticks) at scale k."""
    out = arr.copy()
    px, py = pivot
    out[(py + 1) * k - 1:(py + 1) * k + 1, :] = RED
    out[: 2 * k, px * k:(px + 1) * k] = BLUE
    out[-2 * k:, px * k:(px + 1) * k] = BLUE
    return out


# ------------------------------------------------------------------ per animation and direction


def sheet_image(b: Build, anim: str, d: str, k: int = 8) -> Image.Image:
    frames = b.frames[(anim, d)]
    bg = bgs(b)["beige"]
    size = b.composer.size
    pad, top = 10, 34
    im, dr = canvas(pad + len(frames) * (size * k + pad), top + size * k + pad + 18)
    for i, f in enumerate(frames):
        arr = mark_guides(pixel_grid(big(flat(f.image, bg), k), k), k, b.composer.rig.size.pivot)
        x = pad + i * (size * k + pad)
        paste(im, arr, x, top)
        flags = ", ".join(sorted(f.flags)) if f.flags else ""
        dr.text((x, 6), f"frame {i}   {f.duration} ms", fill=INK, font=font(14))
        if flags:
            dr.text((x, 20), flags, fill=RED, font=font(11))
    dr.text((pad, top + size * k + 4), f"{b.recipe.name} {anim} {d}: red = baseline, "
                                      "blue = pivot column", fill=INK, font=font(12))
    return im


def onion_image(b: Build, anim: str, d: str, k: int = 8) -> Image.Image:
    frames = b.frames[(anim, d)]
    bg = np.asarray(bgs(b)["beige"], np.float32)
    size = b.composer.size
    pad, top = 10, 24
    im, dr = canvas(pad + len(frames) * (size * k + pad), top + size * k + pad)
    loop = b.composer.anims[anim].loop
    for i, f in enumerate(frames):
        prev = frames[i - 1] if (i > 0 or loop) and len(frames) > 1 else None
        base = np.tile(bg, (size, size, 1))
        if prev is not None:
            ghost = flat(prev.image, tuple(int(c) for c in bg)).astype(np.float32)
            base = base * 0.6 + ghost * 0.4
            tint = prev.sprite[..., 3] == 255
            base[tint] = base[tint] * 0.7 + np.asarray(BLUE) * 0.3
        cur = f.image[..., 3:] / 255.0
        out = base * (1 - cur) + f.image[..., :3] * cur
        x = pad + i * (size * k + pad)
        paste(im, pixel_grid(big(out.astype(np.uint8), k), k), x, top)
        label = f"{i} over {prev.index}" if prev is not None else f"{i}"
        dr.text((x, 4), label, fill=INK, font=font(13))
    return im


def diff_image(b: Build, anim: str, d: str, k: int = 8) -> Image.Image:
    frames = b.frames[(anim, d)]
    pairs = list(zip(frames, frames[1:]))
    if b.composer.anims[anim].loop and len(frames) > 1:
        pairs.append((frames[-1], frames[0]))
    size = b.composer.size
    pad, top = 10, 40
    im, dr = canvas(pad + max(len(pairs), 1) * (size * k + pad), top + size * k + pad)
    if not pairs:
        dr.text((pad, 8), "one frame: nothing to diff", fill=INK, font=font(13))
    for i, (a, c) in enumerate(pairs):
        oa, oc = a.image[..., 3] > 0, c.image[..., 3] > 0
        gray = flat(c.image, bgs(b)["light"]).mean(axis=-1, keepdims=True)
        out = np.repeat(gray * 0.55 + 255 * 0.45, 3, axis=-1).astype(np.uint8)
        added = oc & ~oa
        removed = oa & ~oc
        recolored = oa & oc & np.any(a.image != c.image, axis=-1)
        out[added], out[removed], out[recolored] = GREEN, RED, YELLOW
        x = pad + i * (size * k + pad)
        paste(im, pixel_grid(big(out, k), k), x, top)
        dr.text((x, 4), f"{a.index} -> {c.index}", fill=INK, font=font(14))
        dr.text((x, 20), f"+{int(added.sum())}  -{int(removed.sum())}  ~{int(recolored.sum())}",
                fill=INK, font=font(12))
    return im


def silhouette_image(b: Build, anim: str, d: str, k: int = 6) -> Image.Image:
    frames = b.frames[(anim, d)]
    size = b.composer.size
    pad = 10
    im, dr = canvas(pad + len(frames) * (size * k + pad), size * k + 2 * pad, (232, 226, 208))
    for i, f in enumerate(frames):
        out = np.full((size, size, 3), (232, 226, 208), np.uint8)
        out[f.sprite[..., 3] == 255] = INK
        paste(im, big(out, k), pad + i * (size * k + pad), pad)
    return im


# ------------------------------------------------------------------ whole character


def strip_1x(b: Build, anim: str) -> Image.Image:
    dirs = b.anim_directions(anim)
    size = b.composer.size
    n = max(len(b.frames[(anim, d)]) for d in dirs)
    backgrounds = bgs(b)
    block_w = max(n * (size + 4), 96)
    im, dr = canvas(12 + 3 * (block_w + 16) + n * (2 * size + 4) + 12,
                    28 + len(dirs) * (2 * size + 6) + 10)
    for j, (name, color) in enumerate(backgrounds.items()):
        x0 = 12 + j * (block_w + 16)
        dr.text((x0, 6), f"1x on {name}", fill=INK, font=font(12))
        dr.rectangle((x0 - 4, 24, x0 + block_w, 24 + len(dirs) * (size + 6) + 4), fill=color)
        for r, d in enumerate(dirs):
            for i, f in enumerate(b.frames[(anim, d)]):
                paste(im, flat(f.image, color), x0 + i * (size + 4), 28 + r * (size + 6))
    x0 = 12 + 3 * (block_w + 16)
    dr.text((x0, 6), "2x on beige", fill=INK, font=font(12))
    for r, d in enumerate(dirs):
        for i, f in enumerate(b.frames[(anim, d)]):
            paste(im, big(flat(f.image, backgrounds["beige"]), 2), x0 + i * (2 * size + 4),
                  28 + r * (2 * size + 6))
    return im


def turnaround(b: Build, k: int = 8) -> Image.Image:
    size = b.composer.size
    dirs = [d for d in b.style.directions if ("idle", d) in b.frames]
    pad = 12
    im, dr = canvas(pad + len(dirs) * (size * k + pad), size * k + 2 * pad + 18)
    for i, d in enumerate(dirs):
        f = b.frames[("idle", d)][0]
        x = pad + i * (size * k + pad)
        paste(im, mark_guides(pixel_grid(big(flat(f.image, bgs(b)["beige"]), k), k), k,
                              b.composer.rig.size.pivot), x, pad + 18)
        dr.text((x, 4), d.upper(), fill=INK, font=font(14))
    return im


def vs_anchor(b: Build, k: int = 8) -> Image.Image:
    size = b.composer.size
    anchor = load_rgba(b.style.root / "style" / "anchor_with_shadow.png")
    f = b.frames.get(("idle", "s"), [None])[0]
    pad = 12
    report_w = 330
    rows = len({tuple(c) for c in f.sprite[f.sprite[..., 3] == 255][:, :3]}) + 4 if f is not None else 0
    im, dr = canvas(pad * 3 + 2 * size * k + report_w, max(size * k + 2 * pad + 18, 40 + rows * 18))
    bg = bgs(b)["beige"]
    paste(im, big(flat(anchor, bg), k), pad, pad + 18)
    dr.text((pad, 4), "anchor", fill=INK, font=font(14))
    if f is not None:
        paste(im, big(flat(f.image, bg), k), 2 * pad + size * k, pad + 18)
        dr.text((2 * pad + size * k, 4), f"{b.recipe.name} idle s 0", fill=INK, font=font(14))
        x = 3 * pad + 2 * size * k
        dr.text((x, 4), "palette usage", fill=INK, font=font(14))
        counts: dict[tuple[str, str], int] = {}
        for y, xx in np.argwhere(f.sprite[..., 3] == 255):
            i = f.owner[y, xx]
            color = to_hex(f.sprite[y, xx])
            if i == OUTLINE:
                material = "outline"
            elif color == b.style.outline.color:
                material = "outline (hand-placed)"
            else:
                material = f.layers[i].part.material
            key = (material, color)
            counts[key] = counts.get(key, 0) + 1
        for j, ((material, color), n) in enumerate(sorted(counts.items())):
            yy = pad + 24 + j * 18
            dr.rectangle((x, yy, x + 14, yy + 14), fill=parse_hex(color), outline=(120, 110, 100))
            dr.text((x + 20, yy), f"{material}  {color}  {n} px", fill=INK, font=font(12))
    return im


def exploded(b: Build, d: str, k: int = 6) -> Image.Image:
    f = b.frames[("idle", d)][0] if ("idle", d) in b.frames else next(
        fr[0] for (a, dd), fr in b.frames.items() if dd == d)
    size = b.composer.size
    pad = 10
    n = len(f.layers) + 1
    im, dr = canvas(pad + n * (size * k + pad), size * k + 2 * pad + 32)
    light = bgs(b)["light"]
    for i, layer in enumerate(f.layers):
        x = pad + i * (size * k + pad)
        paste(im, pixel_grid(big(flat(layer.image, light), k), k), x, pad + 30)
        dr.text((x, 4), f"{i} {layer.slot}", fill=INK, font=font(12))
        dr.text((x, 18), layer.part.variant, fill=(110, 100, 90), font=font(11))
    x = pad + len(f.layers) * (size * k + pad)
    paste(im, pixel_grid(big(flat(f.image, bgs(b)["beige"]), k), k), x, pad + 30)
    dr.text((x, 4), "composite", fill=INK, font=font(12))
    return im


def anchors_check(rig: Rig, b: Build | None, k: int = 8) -> Image.Image:
    """Base body frames with anchor points marked (pf anchors --check)."""
    colors = {"head": RED, "chin": (230, 120, 40), "torso": GREEN, "back": (40, 160, 160),
              "hand_near": BLUE, "hand_far": (150, 80, 200), "foot_near": YELLOW,
              "foot_far": (240, 150, 200)}
    entries = []
    for anim, dirs in rig.anchors.items():
        for d, frames in dirs.items():
            for i, pts in enumerate(frames):
                entries.append((anim, d, i, pts))
    size = rig.size.canvas
    cols = 8
    rows = max(1, (len(entries) + cols - 1) // cols)
    pad = 10
    im, dr = canvas(pad + cols * (size * k + pad), pad + rows * (size * k + pad + 20) + 40)
    for j, (anim, d, i, pts) in enumerate(entries):
        x = pad + (j % cols) * (size * k + pad)
        y = pad + (j // cols) * (size * k + pad + 20) + 20
        base = None
        if b is not None and (anim, d) in b.frames and i < len(b.frames[(anim, d)]):
            base = b.frames[(anim, d)][i].image
        arr = flat(base, (232, 226, 208)) if base is not None else np.full((size, size, 3), 232, np.uint8)
        arr = pixel_grid(big(arr, k), k)
        for name, p in pts.items():
            if not (isinstance(p, list) and len(p) == 2 and all(isinstance(c, int) for c in p)):
                continue  # "planted" names feet, "pose" maps slots to poses
            px, py = p
            c = colors.get(name, (0, 0, 0))
            arr[py * k + 2:(py + 1) * k - 2, px * k + 2:(px + 1) * k - 2] = c
        paste(im, arr, x, y)
        planted = ",".join(f.replace("foot_", "") for f in pts.get("planted", []))
        dr.text((x, y - 18), f"{anim} {d} {i}  planted: {planted}", fill=INK, font=font(11))
    legend_y = im.height - 30
    for j, (name, c) in enumerate(colors.items()):
        dr.rectangle((pad + j * 120, legend_y, pad + j * 120 + 12, legend_y + 12), fill=c)
        dr.text((pad + j * 120 + 16, legend_y), name, fill=INK, font=font(11))
    return im


def render_all(b: Build, out_dir: Path, anims: list[str] | None = None,
               dirs: list[str] | None = None, combat: bool = False) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    def save(im: Image.Image, name: str) -> None:
        path = out_dir / name
        im.save(path)
        written.append(path)

    if ("idle", "s") in b.frames:
        save(turnaround(b), "turnaround.png")
        save(vs_anchor(b), "vs_anchor.png")
    for d in b.style.drawn_directions:
        if any(dd == d for (_, dd) in b.frames):
            save(exploded(b, d), f"exploded_{d}.png")
    for anim in anims or list(b.recipe.anims):
        if not any(a == anim for (a, _) in b.frames):
            continue
        save(strip_1x(b, anim), f"{anim}_strip_1x.png")
        for d in dirs or b.anim_directions(anim):
            if (anim, d) not in b.frames:
                continue
            save(sheet_image(b, anim, d), f"{anim}_{d}_sheet.png")
            save(onion_image(b, anim, d), f"{anim}_{d}_onion.png")
            save(diff_image(b, anim, d), f"{anim}_{d}_diff.png")
            save(silhouette_image(b, anim, d), f"{anim}_{d}_silhouette.png")
            if combat and b.composer.anims[anim].combat:
                save(timeline_image(b, anim, d), f"{anim}_{d}_timeline.png")
    return written


def recolor_grid(b: Build, combos: list[dict[str, str]], reference: Path | None = None,
                 k: int = 6) -> Image.Image:
    """The character recolored with each combination: 6x and 1x on beige, plus the reference."""
    from dataclasses import replace

    from .build import build
    size = b.composer.size
    bg = bgs(b)["beige"]
    frames = []
    for colors in combos:
        r = replace(b.recipe, colors={**b.recipe.colors, **colors})
        frames.append(build(b.style.root, r, style=b.style, validate=False).frames[("idle", "s")][0])
    pad = 8
    ref = load_rgba(reference) if reference and Path(reference).is_file() else None
    ref_h = ref.shape[0] + 24 if ref is not None else 0
    w = pad + len(frames) * (size * k + pad)
    im, dr = canvas(max(w, ref.shape[1] + 2 * pad if ref is not None else 0),
                    24 + size * k + pad + size + 30 + ref_h)
    dr.text((pad, 4), f"{b.recipe.name}: {len(frames)} recolors at {k}x, then 1x", fill=INK,
            font=font(13))
    for i, f in enumerate(frames):
        x = pad + i * (size * k + pad)
        paste(im, big(flat(f.image, bg), k), x, 24)
        paste(im, flat(f.image, bg), x + (size * k - size) // 2, 24 + size * k + pad)
    if ref is not None:
        y = 24 + size * k + pad + size + 10
        dr.text((pad, y), f"reference: {Path(reference).name}", fill=INK, font=font(13))
        paste(im, ref, pad, y + 18)
    return im


def parts_showcase(b: Build, swaps: list[dict[str, str]], k: int = 4) -> Image.Image:
    """Each swap (slot -> variant, 'none' to empty) applied to the build's recipe, idle frame 0
    facing s, e and n, one row per swap."""
    from dataclasses import replace

    from .build import build
    size = b.composer.size
    pad, label_w = 8, 230
    rows = []
    for swap in swaps:
        r = replace(b.recipe, parts={**b.recipe.parts, **swap}, anims=("idle",))
        rows.append((swap, build(b.style.root, r, style=b.style, validate=False)))
    im, dr = canvas(label_w + 3 * (size * k + pad) + pad, pad + len(rows) * (size * k + pad))
    bg = bgs(b)["beige"]
    for j, (swap, built) in enumerate(rows):
        y = pad + j * (size * k + pad)
        dr.text((pad, y + size * k // 2 - 8), ", ".join(f"{s}/{v}" for s, v in swap.items()),
                fill=INK, font=font(12))
        for i, d in enumerate(("s", "e", "n")):
            if ("idle", d) in built.frames:
                paste(im, big(flat(built.frames[("idle", d)][0].image, bg), k),
                      label_w + i * (size * k + pad), y)
    return im


def random_gallery(builds: list[Build], k: int = 3) -> Image.Image:
    """Idle frame 0 facing s of every build at k x, then the four directions at 1x, with names."""
    if not builds:
        return canvas(10, 10)[0]
    size = builds[0].composer.size
    cols = 6
    cell_w, cell_h = size * k + 24, size * k + size + 40
    rows = (len(builds) + cols - 1) // cols
    im, dr = canvas(cols * cell_w + 16, rows * cell_h + 16)
    bg = bgs(builds[0])["beige"]
    for i, b in enumerate(builds):
        x = 12 + (i % cols) * cell_w
        y = 12 + (i // cols) * cell_h
        if ("idle", "s") in b.frames:
            paste(im, big(flat(b.frames[("idle", "s")][0].image, bg), k), x, y)
        for j, d in enumerate(("s", "e", "n", "w")):
            if ("idle", d) in b.frames:
                paste(im, flat(b.frames[("idle", d)][0].image, bg), x + j * (size + 2), y + size * k + 6)
        dr.text((x, y + size * k + size + 10), b.recipe.name, fill=INK, font=font(11))
    return im


# ------------------------------------------------------------------ combat (COMBAT.md section 9)
PHASE_COLORS = {"windup": (200, 140, 40), "active": (214, 69, 65), "recovery": (150, 145, 160)}
HIT_RGB, HURT_RGB = (255, 59, 59), (59, 139, 255)


def placeholder_spark(style) -> np.ndarray:
    """A 7 x 7 impact spark in the impact FX ramp: the Phase 5 stand-in for Phase 6's FX."""
    ramp = [parse_hex(c) for c in style.raw["fx_ramps"]["impact"]]
    rows = ["...3...", ".3.2.3.", "..212..", "3210123", "..212..", ".3.2.3.", "...3..."]
    out = np.zeros((7, 7, 4), np.uint8)
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c != ".":
                out[y, x] = (*ramp[3 - int(c)], 255)
    return out


def placeholder_projectile(style, kind: str) -> np.ndarray:
    """An arrow (5 x 1 shaft and a head) or a 3 x 3 orb: stand-ins for the Phase 6 projectiles."""
    if kind == "arrow":
        ramp = [parse_hex(c) for c in style.raw["fx_ramps"]["impact"]]
        out = np.zeros((3, 7, 4), np.uint8)
        out[1, 0:6] = (*ramp[1], 255)
        out[0, 5] = out[2, 5] = (*ramp[0], 255)
        out[1, 6] = (*ramp[3], 255)
        return out
    ramp = [parse_hex(c) for c in style.raw["fx_ramps"]["arcane"]]
    out = np.zeros((3, 3, 4), np.uint8)
    out[:, :] = (*ramp[1], 255)
    out[1, 1] = (*ramp[3], 255)
    out[0, 0] = out[0, 2] = out[2, 0] = out[2, 2] = 0
    return out


def blit(dst: np.ndarray, src: np.ndarray, x: int, y: int) -> None:
    """Alpha-over a small RGBA image into an RGBA canvas at (x, y), clipped."""
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    m = s[..., 3] > 0
    region = dst[y0:y1, x0:x1]
    region[m] = s[m]


def _boxes(dr: ImageDraw.ImageDraw, boxes, x: int, y: int, k: int, color, width: int = 2) -> None:
    for bx, by, bw, bh in boxes:
        dr.rectangle((x + bx * k, y + by * k, x + (bx + bw) * k - 1, y + (by + bh) * k - 1),
                     outline=color, width=width)


def timeline_image(b: Build, anim: str, d: str, k: int = 5) -> Image.Image:
    """Frames under a time bar whose segments are proportional to duration, colored by phase,
    with event markers; hitboxes (red) and hurtboxes (blue) drawn on the frames."""
    frames = b.frames[(anim, d)]
    adef = b.composer.anims[anim]
    size = b.composer.size
    bg = bgs(b)["beige"]
    phases = adef.phases or ("",) * len(frames)
    total = sum(f.duration for f in frames)
    cell = size * k
    pad, bar_y, bar_h = 12, 54, 20
    width = pad * 2 + len(frames) * (cell + 8)
    scale = (width - 2 * pad) / max(total, 1)
    im, dr = canvas(width, bar_y + bar_h + 34 + cell + 40)
    from .anim import tell_ms
    tell = tell_ms(adef, [f.duration for f in frames])
    title = f"{b.recipe.name}  {anim}  {d}   total {total} ms   profile {b.recipe.timing_profile}"
    if tell is not None:
        title += f"   tell (windup to hit) {tell} ms"
    dr.text((pad, 10), title, fill=INK, font=font(14))
    dr.text((pad, 30), "windup", fill=PHASE_COLORS["windup"], font=font(12))
    dr.text((pad + 60, 30), "active", fill=PHASE_COLORS["active"], font=font(12))
    dr.text((pad + 112, 30), "recovery", fill=PHASE_COLORS["recovery"], font=font(12))
    dr.text((pad + 186, 30), "hitbox", fill=HIT_RGB, font=font(12))
    dr.text((pad + 240, 30), "hurtbox", fill=HURT_RGB, font=font(12))
    t = 0
    starts = []
    for i, f in enumerate(frames):
        x0 = pad + round(t * scale)
        x1 = pad + round((t + f.duration) * scale) - 1
        starts.append(x0)
        color = PHASE_COLORS.get(phases[i], (205, 200, 190))
        dr.rectangle((x0, bar_y, x1, bar_y + bar_h), fill=color, outline=PAPER)
        dr.text((x0 + 3, bar_y + 4), f"{i}·{f.duration}", fill=PAPER if phases[i] else INK,
                font=font(11))
        t += f.duration
    for e in adef.events:
        i = int(e["frame"])
        if i >= len(frames):
            continue
        x = starts[i]
        dr.polygon([(x, bar_y + bar_h + 2), (x - 5, bar_y + bar_h + 11), (x + 5, bar_y + bar_h + 11)],
                   fill=INK)
        label = e["type"] + (f" {e['fx']}" if "fx" in e else "")
        dr.text((x + 7, bar_y + bar_h + 2), label, fill=INK, font=font(11))
    fy = bar_y + bar_h + 30
    for i, f in enumerate(frames):
        x = pad + i * (cell + 8)
        arr = pixel_grid(big(flat(f.image, bg), k), k, strength=0.06)
        paste(im, arr, x, fy)
        color = PHASE_COLORS.get(phases[i], (205, 200, 190))
        dr.rectangle((x - 2, fy - 2, x + cell + 1, fy + cell + 1), outline=color, width=2)
        if f.hurtbox:
            _boxes(dr, [f.hurtbox], x, fy, k, HURT_RGB)
        _boxes(dr, f.hitboxes, x, fy, k, HIT_RGB)
        for e in adef.events:
            if int(e["frame"]) == i and isinstance(e.get("point"), str) and e["point"] in f.points:
                px, py = f.points[e["point"]]
                dr.ellipse((x + px * k - 3, fy + py * k - 3, x + px * k + k + 2, fy + py * k + k + 2),
                           outline=INK, width=2)
        dr.text((x, fy + cell + 6), f"{i} {phases[i]}", fill=INK, font=font(11))
    return im


def battle_image(att: Build, dfn: Build, anim: str, d: str = "e", k: int = 4) -> Image.Image:
    """The attacker's frames with the defender reacting from the hit (or the projectile's
    arrival) on: hurt, then back to combat_idle. Placeholder sparks and projectiles mark the
    hit; rows at k x and 1 x on the three backgrounds (COMBAT.md section 9)."""
    style = att.style
    frames = att.frames[(anim, d)]
    adef = att.composer.anims[anim]
    size = att.composer.size
    back = {"e": "w", "w": "e", "s": "n", "n": "s"}[d]
    idle = dfn.frames.get(("combat_idle", back)) or dfn.frames[("idle", back)]
    hurt = dfn.frames.get(("hurt", back)) or idle
    hit_i = adef.event_frame("hit")
    spawn_i = adef.event_frame("spawn")
    ranged = spawn_i is not None and hit_i is None
    # Distance: melee puts the defender's hurtbox just inside the strike's reach; ranged leaves
    # room for the projectile to travel.
    axis = 0 if d in ("e", "w") else 1
    sign = 1 if d in ("e", "s") else -1
    if ranged:
        gap = 30
    else:
        active = [f for f in frames if f.hitboxes] or frames
        reach = max((bx + bw if sign > 0 else size - bx) if axis == 0 else
                    (by + bh if sign > 0 else size - by)
                    for f in active for bx, by, bw, bh in (f.hitboxes or [(15, 15, 1, 1)]))
        hb = idle[0].hurtbox or (11, 11, 9, 16)
        near_edge = (hb[0] if sign > 0 else size - hb[0] - hb[2]) if axis == 0 else \
            (hb[1] if sign > 0 else size - hb[1] - hb[3])
        gap = max(reach - near_edge - 2, 6)
    W = size + abs(gap) if axis == 0 else size
    H = size if axis == 0 else size + abs(gap)
    ax, ay = (0, 0) if sign > 0 else ((gap, 0) if axis == 0 else (0, gap))
    dx, dy = ((gap, 0) if axis == 0 else (0, gap)) if sign > 0 else (0, 0)
    spark = placeholder_spark(style)
    proj = placeholder_projectile(style, "arrow" if anim == "shoot_bow" else "orb")
    if d in ("w",):
        proj = proj[:, ::-1]
    if d in ("s", "n"):
        proj = np.transpose(proj, (1, 0, 2))[::(1 if d == "s" else -1)]
    impact_i = None
    if ranged:
        impact_i = min(spawn_i + 2, len(frames) - 1)
    elif hit_i is not None:
        impact_i = hit_i
    cells = []
    for i, f in enumerate(frames):
        scene = np.zeros((H, W, 4), np.uint8)
        if impact_i is not None and i >= impact_i:
            j = i - impact_i
            react = hurt[j] if j < len(hurt) else idle[(j - len(hurt)) % len(idle)]
        else:
            react = idle[i % len(idle)]
        blit(scene, react.image, dx, dy)
        blit(scene, f.image, ax, ay)
        if impact_i is not None and i == impact_i:
            if f.hitboxes and not ranged:
                bx, by, bw, bh = f.hitboxes[0]
                hb = react.hurtbox or (11, 11, 9, 16)
                x0 = max(ax + bx, dx + hb[0]); x1 = min(ax + bx + bw, dx + hb[0] + hb[2])
                y0 = max(ay + by, dy + hb[1]); y1 = min(ay + by + bh, dy + hb[1] + hb[3])
                cx = (x0 + x1) // 2 if x1 > x0 else dx + hb[0] + hb[2] // 2
                cy = (y0 + y1) // 2 if y1 > y0 else dy + hb[1] + hb[3] // 2
            else:
                hb = react.hurtbox or (11, 11, 9, 16)
                cx, cy = dx + hb[0] + hb[2] // 2, dy + hb[1] + hb[3] // 2
            blit(scene, spark, cx - 3, cy - 3)
        if ranged and spawn_i is not None and spawn_i <= i < impact_i:
            sx, sy = f.points.get("bow_nock", f.points.get("hand_near", (size // 2, size // 2)))
            hb = idle[0].hurtbox or (11, 11, 9, 16)
            tx, ty = dx + hb[0] + hb[2] // 2, dy + hb[1] + hb[3] // 2
            u = (i - spawn_i + 0.5) / (impact_i - spawn_i)
            px = round(ax + sx + (tx - ax - sx) * u)
            py = round(ay + sy + (ty - ay - sy) * u)
            blit(scene, proj, px - proj.shape[1] // 2, py - proj.shape[0] // 2)
        for e in adef.events:
            if e["type"] == "vfx" and int(e["frame"]) == i and isinstance(e.get("point"), str):
                pt = f.points.get(e["point"])
                if pt:
                    blit(scene, spark, ax + pt[0] - 3, ay + pt[1] - 3)
        cells.append(scene)
    pad = 10
    grounds = bgs(att)
    cw, ch = W * k, H * k
    im, dr = canvas(pad + len(cells) * (cw + pad), 44 + ch + 30 + 3 * (H + 8) + 20)
    dr.text((pad, 10), f"{att.recipe.name} {anim} {d} vs {dfn.recipe.name}   placeholder spark and "
                       f"projectile until the Phase 6 FX", fill=INK, font=font(13))
    phases = adef.phases or ("",) * len(frames)
    for i, scene in enumerate(cells):
        x = pad + i * (cw + pad)
        paste(im, big(flat(scene, grounds["beige"]), k), x, 44)
        color = PHASE_COLORS.get(phases[i], (205, 200, 190))
        dr.rectangle((x - 2, 42, x + cw + 1, 44 + ch + 1), outline=color, width=2)
        dr.text((x, 44 + ch + 6), f"{i} {frames[i].duration}ms {phases[i]}", fill=INK, font=font(11))
        for r, name in enumerate(("beige", "light", "dark")):
            y = 44 + ch + 30 + r * (H + 8)
            paste(im, flat(scene, grounds[name]), x, y)
    return im
