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


def test_loader_places_fx_by_their_own_pivots(root, style, exported, tmp_path):
    """FX pivots are per tag: the loader plays an event's FX at the event's point."""
    from pixelforge.fx import export as export_fx, load_fx
    b, path = exported["goblin_archer"]
    export_fx(load_fx(root / "fx" / "arrow", style), style, tmp_path)
    fx_json = next(tmp_path.rglob("arrow.json"))
    run = subprocess.run([NODE, "--experimental-strip-types", "--no-warnings",
                          str(root / "loaders" / "selftest.ts"), str(path), "shoot_bow", "e",
                          "enemy", str(fx_json)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    got = json.loads(run.stdout)["fx"]
    assert got["isFx"] and got["anim"] == "travel" and got["pivot"] == [8, 7]
    assert got["origin"] == got["at"]  # the arrow's pivot lands on the bow's nock


def test_charge_loops_are_exported(exported):
    b, path = exported["goblin_archer"]
    pf = json.loads(path.read_text())["meta"]["pixelforge"]
    assert pf["loop_frames"]["shoot_bow_e"] == [2]  # the held full draw
