"""Export: spritesheet PNG, Aseprite JSON (array format) and preview GIFs (section 14).

Rows of the sheet are (animation, direction) in recipe order with directions s, e, n, w; columns
are frames, left-aligned, no padding. `meta.pixelforge` carries the pivot, loops, events,
phases, hitboxes, hurtboxes and root motion that games need.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .build import Build
from .color import parse_hex
from .effects import composite_on
from .sheet import save_rgba
from .validate import Finding

APP_VERSION = "1.0"


def sheet_layout(b: Build) -> list[tuple[str, str, int]]:
    """(anim, direction, frame count) per sheet row."""
    rows = []
    for anim in b.recipe.anims:
        for d in b.anim_directions(anim):
            rows.append((anim, d, len(b.frames[(anim, d)])))
    return rows


def spritesheet(b: Build) -> np.ndarray:
    cell = b.composer.size
    rows = sheet_layout(b)
    width = max((n for _, _, n in rows), default=1) * cell
    img = np.zeros((max(len(rows), 1) * cell, width, 4), np.uint8)
    for r, (anim, d, _) in enumerate(rows):
        for c, f in enumerate(b.frames[(anim, d)]):
            img[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell] = f.image
    return img


def aseprite_json(b: Build, image_name: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    cell = b.composer.size
    rows = sheet_layout(b)
    frames, tags = [], []
    loops, events, phases, root_motion, durations = {}, {}, {}, {}, {}
    i = 0
    for r, (anim, d, n) in enumerate(rows):
        adef = b.composer.anims[anim]
        tag = f"{anim}_{d}"
        start = i
        for c, f in enumerate(b.frames[(anim, d)]):
            frames.append({
                "filename": f"{b.recipe.name} {tag} {c}",
                "frame": {"x": c * cell, "y": r * cell, "w": cell, "h": cell},
                "rotated": False, "trimmed": False,
                "spriteSourceSize": {"x": 0, "y": 0, "w": cell, "h": cell},
                "sourceSize": {"w": cell, "h": cell},
                "duration": f.duration,
            })
            i += 1
        tags.append({"name": tag, "from": start, "to": i - 1, "direction": "forward"})
        loops[anim] = adef.loop
        if adef.events:
            events[tag] = [dict(e) for e in adef.events]
        if adef.phases:
            phases[tag] = list(adef.phases)
        if adef.root_motion:
            root_motion[tag] = list(adef.root_motion)
        durations[tag] = [f.duration for f in b.frames[(anim, d)]]
    size = b.composer.rig.size
    meta_pf: dict[str, Any] = {
        "pivot": list(size.pivot), "size_class": size.name, "rig": b.composer.rig.name,
        "timing_profile": b.recipe.timing_profile, "loop": loops, "events": events,
        "phases": phases, "hitboxes": {}, "hurtboxes": {}, "root_motion": root_motion,
    }
    if extra:
        meta_pf.update(extra)
    sheet_h = max(len(rows), 1) * cell
    sheet_w = max((n for _, _, n in rows), default=1) * cell
    return {
        "frames": frames,
        "meta": {
            "app": "pixelforge", "version": APP_VERSION, "image": image_name,
            "format": "RGBA8888", "size": {"w": sheet_w, "h": sheet_h}, "scale": "1",
            "frameTags": tags, "pixelforge": meta_pf,
        },
    }


def check_export(data: dict[str, Any], image: np.ndarray, where: str) -> list[Finding]:
    """E12: frame rects inside the sheet, positive durations, tags cover every frame once,
    events on valid frames."""
    out = []
    h, w = image.shape[:2]
    frames = data["frames"]
    for i, fr in enumerate(frames):
        r = fr["frame"]
        if r["x"] < 0 or r["y"] < 0 or r["x"] + r["w"] > w or r["y"] + r["h"] > h:
            out.append(Finding("error", "E12", where, f"frame {i} rect {r} is outside the sheet"))
        if fr["duration"] <= 0:
            out.append(Finding("error", "E12", where, f"frame {i} has duration {fr['duration']}"))
    covered = [0] * len(frames)
    for t in data["meta"]["frameTags"]:
        for i in range(t["from"], t["to"] + 1):
            if 0 <= i < len(frames):
                covered[i] += 1
    if any(c != 1 for c in covered):
        out.append(Finding("error", "E12", where, "frame tags do not cover every frame exactly once"))
    tags = {t["name"]: t for t in data["meta"]["frameTags"]}
    for tag, evs in data["meta"]["pixelforge"].get("events", {}).items():
        n = tags[tag]["to"] - tags[tag]["from"] + 1 if tag in tags else 0
        for e in evs:
            if not 0 <= e["frame"] < n:
                out.append(Finding("error", "E12", where, f"{tag} event {e['type']} on frame "
                                                          f"{e['frame']} of {n}"))
    return out


def write_gif(path: Path, frames: list, background: str, scale: int = 4) -> Path:
    bg = parse_hex(background)
    images = []
    for f in frames:
        flat = composite_on(f.image, bg)
        im = Image.fromarray(flat, "RGB").resize(
            (flat.shape[1] * scale, flat.shape[0] * scale), Image.NEAREST)
        images.append(im.convert("P", palette=Image.ADAPTIVE, colors=64))
    path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(path, save_all=True, append_images=images[1:],
                   duration=[f.duration for f in frames], loop=0, disposal=2, optimize=False)
    return path


def export(b: Build, out_dir: Path, *, gifs: bool = True, extra: dict[str, Any] | None = None
           ) -> tuple[Path, list[Finding]]:
    name = b.recipe.name
    folder = Path(out_dir) / name
    folder.mkdir(parents=True, exist_ok=True)
    image = spritesheet(b)
    save_rgba(folder / f"{name}.png", image)
    data = aseprite_json(b, f"{name}.png", extra)
    (folder / f"{name}.json").write_text(json.dumps(data, indent=1))
    if gifs:
        bg = b.style.raw["preview_backgrounds"]["beige"]
        for (anim, d), frames in b.frames.items():
            write_gif(folder / f"{name}_{anim}_{d}.gif", frames, bg)
    findings = check_export(data, image, name)
    update_index(Path(out_dir), b, data)
    return folder, findings


def update_index(out_dir: Path, b: Build, data: dict[str, Any]) -> Path:
    path = out_dir / "index.json"
    index = json.loads(path.read_text()) if path.is_file() else {"characters": []}
    entry = {
        "name": b.recipe.name, "rig": b.composer.rig.name, "cell": b.composer.size,
        "image": f"{b.recipe.name}/{b.recipe.name}.png", "json": f"{b.recipe.name}/{b.recipe.name}.json",
        "timing_profile": b.recipe.timing_profile, "anims": list(b.recipe.anims),
        "monster": b.composer.rig.name not in ("humanoid",) or "monsters" in str(b.recipe.path or ""),
    }
    index["characters"] = [c for c in index["characters"] if c["name"] != entry["name"]] + [entry]
    index["characters"].sort(key=lambda c: c["name"])
    path.write_text(json.dumps(index, indent=1))
    return path
