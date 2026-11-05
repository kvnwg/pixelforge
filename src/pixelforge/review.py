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
               dirs: list[str] | None = None) -> list[Path]:
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
