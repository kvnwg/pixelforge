"""Humanoid monsters on the humanoid rig, and monster families (MONSTERS.md sections 5.4 and 6).

- Orc: the green (orc) skin preset, a tusks part (2 px, horn), iron armor and a mace; glow eyes.
- Skeleton: body/skeleton and arm_*/skeleton, the humanoid base body converted to bone (skin
  shadow, mid, light -> bone 1, 2, 3) with eye sockets, a nose hole and ribs carved from each
  frame's own anchors, so it has every humanoid animation; glow eyes; bone_crumble death.
- Frost wolf: the wolf in the frost fur preset (lighter, so it differs in grayscale too) with
  ghost-blue eyes: a family variant.

Run after humanoid.py, parts_library.py and weapons.py: .venv/bin/python tools/art/monsters_humanoid.py
"""

from __future__ import annotations

import json

import numpy as np

from artlib import ROOT, STYLE, empty, g, write_part, write_recipe
from pixelforge.color import parse_hex
from pixelforge.sheet import Sheet, write_sheet

DIRS = ("s", "e", "n")
OUTLINE = parse_hex(STYLE.outline.color)
SKIN = [parse_hex(c) for c in STYLE.materials["skin"].base]
BONE = [parse_hex(c) for c in STYLE.materials["bone"].base]
SKIN_TO_BONE = {SKIN[0]: BONE[1], SKIN[1]: BONE[2], SKIN[2]: BONE[3]}


# ============================================================================== orc
TUSKS = {"s": [(13, 19), (17, 19)], "e": [(18, 19)], "n": []}  # idle frame 0, at the jaw corners

CAP = {  # headwear/horned_helm, metal: a rounded cap down to the brow, the face shows below
    "s": g([".....33333.....", "....2333332....", "...123333322...", "...022232221...",
            "...000000000..."], 8, 10),
    "e": g([".....3333......", "....233333.....", "...12333332....", "...02233322....",
            "...00000000...."], 8, 10),
    "n": g([".....33333.....", "....2333332....", "...123333322...", "...022232221...",
            "...011121110...", "...000000000..."], 8, 10),
}
HORNS = {  # headwear_trim/horns, horn: rising from the cap, light tips; the orc's signature
    "s": [(11, 10, 1), (11, 9, 1), (10, 8, 2), (10, 7, 2), (19, 10, 1), (19, 9, 1), (20, 8, 2), (20, 7, 2)],
    "e": [(13, 10, 1), (13, 9, 1), (12, 8, 2), (12, 7, 2), (17, 9, 0), (17, 8, 1)],
    "n": [(11, 10, 1), (11, 9, 1), (10, 8, 2), (10, 7, 2), (19, 10, 1), (19, 9, 1), (20, 8, 2), (20, 7, 2)],
}


def horned_helm() -> None:
    write_part("headwear", "horned_helm", {
        "material": "metal", "kind": "rigid", "attach": "head", "origin": "auto", "lags": False,
        "rigs": ["humanoid"], "hides": ["hair_front", "hair_locks", "hair_back"],
        "notes": "A rounded iron cap for the horns to rise from."},
        {"rigid": {(d, 0): CAP[d] for d in DIRS}})
    cells = {}
    for d in DIRS:
        codes = empty()
        for x, y, shade in HORNS[d]:
            codes[y, x] = shade
        cells[(d, 0)] = codes
    write_part("headwear_trim", "horns", {
        "material": "horn", "kind": "rigid", "attach": "head", "origin": "auto", "lags": False,
        "rigs": ["humanoid"], "allow_singletons": {"e": [[17, 9], [17, 8]]},
        "notes": "Two horns rising from a helm: a silhouette no human enemy shares."},
        {"rigid": cells})


def orc() -> None:
    cells = {}
    for d in DIRS:
        codes = empty()
        for x, y in TUSKS[d]:
            codes[y, x] = 2  # horn light
        cells[(d, 0)] = codes
    write_part("tusks", "orc", {"material": "horn", "kind": "rigid", "attach": "chin", "origin": "auto",
                                "lags": False, "rigs": ["humanoid"],
                                "allow_singletons": {"s": [[13, 19], [17, 19]], "e": [[18, 19]]},
                                "notes": "Two 1 px tusks at the corners of the jaw."},
               {"rigid": cells})
    horned_helm()
    write_recipe("monsters/orc.yaml", {
        "name": "orc", "rig": "humanoid", "timing_profile": "enemy", "seed": 1,
        "parts": {"eyes": "dots", "headwear": "horned_helm", "headwear_trim": "horns",
                  "tusks": "orc", "torso_wear": "plate",
                  "belt": "leather_belt", "belt_trim": "buckle", "legs_wear": "greaves",
                  "feet": "boots", "hands": "gauntlets", "held_near": "mace"},
        "colors": {"skin": "green (orc)", "hair": "black", "metal": "iron", "leather": "dark",
                   "accent": "silver", "eyes": "glow red", "horn": "pale"},
        "anims": ["idle", "blink", "walk", "combat_idle", "attack_slash", "attack_heavy", "hurt",
                  "stun", "death", "victory"],
    })


# ============================================================================== skeleton
def anchors() -> dict:
    return json.loads((ROOT / "parts" / "body" / "humanoid" / "anchors.json").read_text())


def carve(cell: np.ndarray, d: str, pts: dict) -> np.ndarray:
    """Sockets, nose and ribs, placed from the frame's anchors (head, chin, torso)."""
    out = cell.copy()
    hx, hy = pts["head"]
    tx, ty = pts["torso"]
    dark, gap = (*BONE[0], 255), (*OUTLINE, 255)

    def put(x, y, color):
        if 0 <= x < 32 and 0 <= y < 32 and out[y, x, 3] == 255:
            out[y, x] = color

    if d == "s":
        for ex in (hx - 3, hx - 2, hx + 2, hx + 3):  # sockets around both eyes
            put(ex, hy + 6, dark)
            put(ex, hy + 7, dark)
        put(hx, hy + 8, dark)  # the nose hole
        for dy in (2, 3):  # two ribs either side of the spine
            for dx in (-2, -1, 1, 2):
                put(tx + dx, ty + dy + (1 if dy == 3 else 0), gap)
    elif d == "e":
        for ex in (hx + 2, hx + 3):
            put(ex, hy + 6, dark)
            put(ex, hy + 7, dark)
        put(hx + 3, hy + 8, dark)
        for dy in (2, 4):
            for dx in (-1, 0, 1):
                put(tx + dx, ty + dy, gap)
    else:  # n: the spine and ribs from behind
        for dy in (2, 4):
            for dx in (-2, -1, 1, 2):
                put(tx + dx, ty + dy, gap)
    return out


def despeckle(cell: np.ndarray) -> np.ndarray:
    """A bone pixel no 4-neighbor shares a color with takes its neighbors' most common bone
    color (ties darker). The darkest bone (sockets, the nose hole) and the outline-colored rib
    gaps are left alone: they are drawn on purpose."""
    out = cell.copy()
    bones = [tuple(b) for b in BONE]
    for y in range(32):
        for x in range(32):
            c = tuple(int(v) for v in cell[y, x, :3])
            if cell[y, x, 3] != 255 or c not in bones[1:]:
                continue
            near = [tuple(int(v) for v in cell[y + dy, x + dx, :3]) for dx, dy in
                    ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= y + dy < 32 and 0 <= x + dx < 32 and cell[y + dy, x + dx, 3] == 255]
            if c in near:
                continue
            bone_near = [n for n in near if n in bones[1:]]
            if len(bone_near) >= 2:
                counts = {n: bone_near.count(n) for n in bone_near}
                out[y, x, :3] = sorted(counts, key=lambda n: (-counts[n], bones.index(n)))[0]
    return out


def to_bone(cell: np.ndarray) -> np.ndarray:
    out = cell.copy()
    opaque = out[..., 3] == 255
    for src, dst in SKIN_TO_BONE.items():
        mask = opaque & np.all(cell[..., :3] == np.asarray(src, np.uint8), axis=-1)
        out[mask, :3] = dst
    return out


def skeleton() -> None:
    pts = anchors()
    for slot in ("body", "arm_near", "arm_far"):
        src = ROOT / "parts" / slot / "humanoid"
        dst = ROOT / "parts" / slot / "skeleton"
        dst.mkdir(parents=True, exist_ok=True)
        meta = {"slot": slot, "variant": "skeleton", "material": "bone", "kind": "animated",
                "lags": False, "rigs": ["humanoid"],
                "notes": "The humanoid base body in bone, with sockets and ribs (generated)."}
        import yaml
        (dst / "part.yaml").write_text(yaml.safe_dump(meta, sort_keys=False))
        for png in sorted(src.glob("*.png")):
            anim = png.stem
            sheet = Sheet.load(png, 32, DIRS)
            cells = {}
            for d in DIRS:
                for i in range(sheet.frames):
                    cell = sheet.get(d, i)
                    cell = to_bone(cell)
                    if slot == "body" and anim in pts and i < len(pts[anim][d]):
                        cell = carve(cell, d, pts[anim][d][i])
                    cells[(d, i)] = despeckle(cell)
            write_sheet(dst / f"{anim}.png", cells, DIRS, sheet.frames, 32)
    write_recipe("monsters/skeleton.yaml", {
        "name": "skeleton", "rig": "humanoid", "timing_profile": "enemy", "seed": 1,
        "parts": {"body": "skeleton", "arm_near": "skeleton", "arm_far": "skeleton", "eyes": "dots",
                  "belt": "leather_belt", "held_near": "sword", "held_near_trim": "hilt",
                  "held_far": "shield"},
        "colors": {"bone": "ivory", "eyes": "glow ghost", "metal": "iron", "accent": "silver",
                   "leather": "dark"},
        "anims": ["idle", "walk", "combat_idle", "attack_slash", "block_enter", "block_hold",
                  "block_impact", "hurt", "stun", "death_crumble", "victory"],
    })


# ============================================================================== families
def frost_wolf() -> None:
    write_recipe("monsters/frost_wolf.yaml", {
        "name": "frost_wolf", "family": "wolf", "rig": "quadruped", "timing_profile": "enemy", "seed": 1,
        "parts": {"tail": "wolf", "eyes": "wolf"},
        "colors": {"fur": "frost", "eyes": "glow ghost"},
        "anims": ["idle", "combat_idle", "walk", "run", "attack_bite", "howl", "hurt", "death"],
    })


def main() -> None:
    orc()
    skeleton()
    frost_wolf()
    print("wrote the orc, skeleton and frost wolf")


if __name__ == "__main__":
    main()
