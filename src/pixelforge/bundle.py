"""Bundle tools/preview into one self-contained HTML file (sprites and data inlined).

The preview page marks its parts with <!-- pf:head -->, <!-- pf:body --> and <!-- pf:data -->.
The bundle keeps only those parts (no doctype or html/head/body tags), so it can also be
published as a page that gets its own document skeleton.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path


def _between(text: str, start: str, end: str) -> str:
    i, j = text.index(start) + len(start), text.index(end)
    return text[i:j]


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")


def write_bundle(root: Path, out: Path) -> Path:
    root = Path(root)
    page = (root / "tools" / "preview" / "index.html").read_text(encoding="utf-8")
    head = _between(page, "<!-- pf:head -->", "<!-- /pf:head -->")
    body = _between(page, "<!-- pf:body -->", "<!-- /pf:body -->")
    index = json.loads((root / "out" / "index.json").read_text())
    characters = {}
    for entry in index["characters"]:
        characters[entry["name"]] = {
            "json": json.loads((root / "out" / entry["json"]).read_text()),
            "png": data_uri(root / "out" / entry["image"]),
        }
    fx_index_path = root / "out" / "fx" / "index.json"
    fx = {"index": {"fx": []}, "items": {}}
    if fx_index_path.is_file():
        fx["index"] = json.loads(fx_index_path.read_text())
        for entry in fx["index"]["fx"]:
            fx["items"][entry["name"]] = {
                "json": json.loads((root / "out" / entry["json"]).read_text()),
                "png": data_uri(root / "out" / entry["image"]),
            }
    data = {"index": index, "characters": characters, "fx": fx,
            "anchor": data_uri(root / "style" / "anchor_with_shadow.png")}
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    script = f"<script>window.PIXELFORGE_BUNDLE = {payload};</script>"
    body = body.replace("<!-- pf:data -->", script)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # the charset comes first so the file also reads right opened straight from disk; inside a
    # published page's own skeleton it is a harmless repeat
    text = '<meta charset="utf-8">\n' + head.strip() + "\n" + body.strip() + "\n"
    out.write_text(re.sub(r"\n{3,}", "\n\n", text), encoding="utf-8")
    return out
