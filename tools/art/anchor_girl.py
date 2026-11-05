"""anchor_girl's parts, decomposed from style/anchor.png, and her recipe.

One material per part; outline-colored pixels are hand-placed details. Grids start at x = 8,
y = 10. Shades per material (0 = darkest):
  hair:    0 #735b51  1 #826b5e  2 #957e6d
  cloth:   0 #4c445a  1 #5a556b
  accent:  0 #bc8f5f  1 #d2ab70
  leather: 0 #5e494c  1 #735b51  2 #826b5e
  eyes:    0 #5a556b

Run: .venv/bin/python tools/art/anchor_girl.py
"""

from __future__ import annotations

from artlib import FRAMES, empty, g, write_part, write_recipe

BLANK = ["..............."]
#                x: 890123456789012
EYES_S = g(BLANK * 8 + [".....0...0....."])  # y18: (13, 18) and (17, 18)

# Hair splits in three: hair_front moves with the head; hair_locks (the outer locks framing the
# face, x 11-12 and 18-19 on rows 15 to 17) trail the head by one frame; hair_back is the hair
# behind the head (nothing shows of it facing s).
HAIR_FRONT_S = g(BLANK + [
    "....1222221....",  # y11
    "...122221221...",  # y12 center part: mid tone at x = 16
    "...122221221...",  # y13
    "...112221121...",  # y14
    ".....12..1.....",  # y15 bangs over the forehead
    "...............",  # y16
    ".....2...2.....",  # y17 inner locks
])
HAIR_LOCKS_S = g(BLANK * 5 + [
    "...01.....10...",  # y15
    "...00.....00...",  # y16
    "...02.....20...",  # y17
])

DRESS_S = g(BLANK * 10 + [
    "...01.....11...",  # y20 shoulders
    "...0011111.....",  # y21 sleeve and bodice
    "....011111.....",  # y22
    "....011111.....",  # y23
    "....0111100....",  # y24 hem (mostly under the sash)
])
SASH_S = g(BLANK * 14 + [
    "....110...0....",  # y24 knot on the viewer-left hip
    "......0110.....",  # y25 the tail hanging in front
])
LEGGINGS_S = g(BLANK * 15 + [
    "....211..11....",  # y25
    "....220........",  # y26
    "....220........",  # y27
])

RECIPE = {
    "name": "anchor_girl",
    "rig": "humanoid",
    "timing_profile": "player",
    "seed": 1,
    "parts": {
        "eyes": "dots",
        "hair_front": "long_straight",
        "hair_locks": "long_straight",
        "hair_back": "long_straight",
        "torso_wear": "dress",
        "belt": "sash",
        "legs_wear": "leggings",
    },
    "colors": {
        "skin": "light (anchor)",
        "hair": "brown (anchor)",
        "cloth": "navy (anchor)",
        "leather": "brown (anchor)",
        "accent": "gold (anchor)",
        "eyes": "navy (anchor)",
    },
    "anims": ["idle"],
}


def rigid(material: str, attach: str, notes: str, lags: bool = False, **extra) -> dict:
    return {"material": material, "kind": "rigid", "attach": attach, "origin": "auto",
            "lags": lags, "rigs": ["humanoid"], "notes": notes, **extra}


def main() -> None:
    write_part("eyes", "dots", rigid("eyes", "head", "Two 1 px eyes, 3 px apart.",
                                     allow_singletons=[]), {"rigid": {("s", 0): EYES_S}})
    write_part("hair_front", "long_straight",
               rigid("hair", "head", "Long straight hair: top, center part, bangs, inner locks."),
               {"rigid": {("s", 0): HAIR_FRONT_S}})
    write_part("hair_locks", "long_straight",
               rigid("hair", "head", "The outer locks framing the face; they trail the head.",
                     lags=True), {"rigid": {("s", 0): HAIR_LOCKS_S}})
    write_part("hair_back", "long_straight",
               rigid("hair", "head", "Hair behind the head: hidden facing s.", lags=True),
               {"rigid": {("s", 0): empty()}})
    write_part("torso_wear", "dress", rigid("cloth", "torso", "Dress with sleeves to the elbow."),
               {"rigid": {("s", 0): DRESS_S}})
    write_part("belt", "sash", rigid("accent", "torso", "Sash knotted on the hip, tail in front."),
               {"rigid": {("s", 0): SASH_S}})
    write_part("legs_wear", "leggings", {
        "material": "leather", "kind": "animated", "lags": False, "rigs": ["humanoid"],
        "notes": "Leather leggings and shoes, redrawn per frame with the legs.",
    }, {"idle": {("s", 0): LEGGINGS_S}}, {"idle": FRAMES["idle"]})
    write_recipe("anchor_girl.yaml", RECIPE)
    print("wrote anchor_girl's parts and recipe")


if __name__ == "__main__":
    main()
