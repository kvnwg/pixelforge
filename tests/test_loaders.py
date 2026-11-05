"""Phase 10: the TypeScript loader (loaders/pixelforge.ts) plays exports the way the exporter
times them: retimed durations match anim.retime, events fire at their frames' start times."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from pixelforge.anim import retime
from pixelforge.build import build
from pixelforge.export import export

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

CASES = [
    ("knight", "attack_slash", "e", "enemy"),
    ("rk_ranger", "shoot_bow", "n", "boss"),
    ("knight", "attack_heavy", "s", "elite"),
    ("goblin_archer", "shoot_bow", "s", "enemy"),
    ("stone_warden", "charge", "e", "boss"),
    ("stone_warden", "cast_ring", "w", "player"),
]


@pytest.fixture(scope="module")
def exported(root, style, tmp_path_factory):
    out = tmp_path_factory.mktemp("exports")
    paths = {}
    for name in {c[0] for c in CASES}:
        b = build(root, name, style=style)
        export(b, out / name, gifs=False)
        paths[name] = (b, next((out / name).rglob(f"{name}.json")))
    return paths


@pytest.mark.parametrize("name,anim,d,profile", CASES)
def test_loader_times_events_like_the_exporter(root, style, exported, name, anim, d, profile):
    b, path = exported[name]
    run = subprocess.run([NODE, "--experimental-strip-types", "--no-warnings",
                          str(root / "loaders" / "selftest.ts"), str(path), anim, d, profile],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    got = json.loads(run.stdout)
    adef = b.composer.anims[anim]
    want = retime(adef, list(adef.frames_ms), style.raw["combat"]["timing_profiles"][profile])
    assert got["durations"] == want
    starts = [sum(want[:i]) for i in range(len(want))]
    for t, kind, frame in got["fired"]:
        assert abs(t - starts[frame]) < 5, (kind, frame, t, starts[frame])  # 5 ms ticks
    kinds = [k for _, k, _ in got["fired"]]
    assert kinds == [e["type"] for e in sorted(adef.events, key=lambda e: e["frame"])]
    assert got["pivot"] == list(b.composer.rig.size.pivot)
    assert got["facings"] == ["e", "w", "s", "n"]
