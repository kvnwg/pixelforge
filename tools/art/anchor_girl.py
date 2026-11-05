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

from artlib import empty, g, write_part, write_recipe

# Combat animations every humanoid recipe lists (shoot_bow only with a bow in hand)
COMBAT_ANIMS = ["combat_idle", "attack_slash", "attack_heavy", "cast", "block_enter", "block_hold",
                "block_impact", "dodge", "hurt", "stun", "death", "victory", "roll", "backflip",
                "vault"]
from humanoid import leather_legs, legs_frames

BLANK = ["..............."]
#                x: 890123456789012
EYES_S = g(BLANK * 8 + [".....0...0....."])  # y18: (13, 18) and (17, 18)
EYES_E = g(BLANK * 8 + [".........0....."])  # y18: one eye near the front of the face

# Hair splits in three: hair_front moves with the head; hair_locks (the outer locks framing the
# face, x 11-12 and 18-19 on rows 15 to 17) trail the head by one frame; hair_back is the hair
# behind the head (nothing shows of it facing s).
HAIR_FRONT_S = g(BLANK + [
    "....1222221....",  # y11
    "...122221221...",  # y12 center part: mid tone at x = 16
    "...122221221...",  # y13
    "...112221121...",  # y14
    "...0112..110...",  # y15 bangs; the side pixels sit under the locks (no gap when they lag)
])
# Facing e the hair covers the top and back of the head; bangs end on row 15 with one pixel of
# forehead at the front. hair_back is the back of the head and the nape, trailing the head.
HAIR_FRONT_E = g(BLANK + [
    ".....12222.....",  # y11
    "....1222221....",  # y12
    "...01222122....",  # y13
    "...01122212....",  # y14
    "...0011211.....",  # y15 bangs
])
HAIR_BACK_E = g(BLANK * 4 + [
    "...0112........",  # y14 (under hair_front: overlap so a lag never opens a gap)
    "...0011........",  # y15
    "...0011........",  # y16
    "...0011........",  # y17
    "...0001........",  # y18
    "....00.........",  # y19 nape
])
# Facing n the hair covers the whole head: hair_front is the crown, hair_back hangs below it.
HAIR_FRONT_N = g(BLANK + [
    "....1222221....",  # y11 the crown catches the light, like the top of the hair facing s
    "...022222221...",  # y12 shadow side dark, lit side mid
    "...012222211...",  # y13
    "...011121011...",  # y14 one light strand down the middle; the right dark strand starts
])
HAIR_BACK_N = g(BLANK * 4 + [
    "...011121011...",  # y14 (under hair_front)
    "...011011011...",  # y15 short dark strands split the mass
    "...011011010...",  # y16
    "...001011000...",  # y17
    "...001011000...",  # y18
    "....0001100....",  # y19 down to the collar: the hair meets the dress
])
HAIR_LOCKS_S = g(BLANK * 5 + [
    "...011...110...",  # y15 the side hair framing the face, rows 15 to 17, trails the head
    "...00.....00...",  # y16
    "...022...220...",  # y17
])

DRESS_S = g(BLANK * 10 + [
    "...01.....11...",  # y20 shoulders
    "...0011111.....",  # y21 sleeve and bodice
    "....011111.....",  # y22
    "....011111.....",  # y23
    "....0111100....",  # y24 hem (mostly under the sash)
    "......0110.....",  # y25 skirt under the sash tail (shows facing n)
])
DRESS_E = g(BLANK * 10 + [
    "....00...1.....",  # y20 back of the collar, front of the collar
    "....001111.....",  # y21 back in shade, front lit
    "....001111.....",  # y22
    "....001111.....",  # y23
    "....001111.....",  # y24
])
DRESS_N = g(BLANK * 10 + [
    "...001111111...",  # y20 back of the shoulders: the hair ends right above
    "...0011111.....",  # y21
    "....011111.....",  # y22
    "....001111.....",  # y23
    "....0111111....",  # y24 under the sash
    "......0110.....",  # y25 skirt between the legs
])
SASH_S = g(BLANK * 14 + [
    "....110...0....",  # y24 knot on the viewer-left hip
    "......0110.....",  # y25 the tail hanging in front
])
SASH_E = g(BLANK * 14 + [
    "....111100.....",  # y24 knot in shade at the front of the hip
    "........0......",  # y25 the end of the knot hanging
])
SASH_N = g(BLANK * 14 + [
    "....0111110....",  # y24 the band around the back (the tail hangs in front)
])
LEGGINGS_S = g(BLANK * 15 + [
    "....211..11....",  # y25
    "....220........",  # y26
    "....220........",  # y27
])
LEGGINGS_E = g(BLANK * 15 + [
    ".....0121......",  # y25 far leg darker leather, near leg lighter (no twinning)
    ".......21......",  # y26
    ".......221.....",  # y27 near foot, toes forward
])
LEGGINGS_N = LEGGINGS_S  # same legs on screen as facing s

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
    "anims": ["idle", "blink", "walk", *COMBAT_ANIMS],
}


def leggings() -> dict:
    """Leather leggings for every drawn pose of the base legs (idle, walk and combat)."""
    out: dict = {}
    for (anim, d, i), legs in legs_frames().items():
        out.setdefault(anim, {})[(d, i)] = leather_legs(legs)
    return out


def rigid(material: str, attach: str, notes: str, lags: bool = False, **extra) -> dict:
    return {"material": material, "kind": "rigid", "attach": attach, "origin": "auto",
            "lags": lags, "rigs": ["humanoid"], "notes": notes, **extra}


def main() -> None:
    write_part("eyes", "dots", rigid("eyes", "head", "Two 1 px eyes, 3 px apart; one facing e; none facing n.",
                                     allow_singletons=[]),
               {"rigid": {("s", 0): EYES_S, ("e", 0): EYES_E, ("n", 0): empty()}})
    write_part("hair_front", "long_straight",
               rigid("hair", "head", "Long straight hair: top, center part, bangs, inner locks."),
               {"rigid": {("s", 0): HAIR_FRONT_S, ("e", 0): HAIR_FRONT_E, ("n", 0): HAIR_FRONT_N}})
    write_part("hair_locks", "long_straight",
               rigid("hair", "head", "The outer locks framing the face; they trail the head.",
                     lags=True),
               {"rigid": {("s", 0): HAIR_LOCKS_S, ("e", 0): empty(), ("n", 0): empty()}})
    write_part("hair_back", "long_straight",
               rigid("hair", "head", "Hair behind and below the crown; trails the head. Hidden facing s.",
                     lags=True),
               {"rigid": {("s", 0): empty(), ("e", 0): HAIR_BACK_E, ("n", 0): HAIR_BACK_N}})
    write_part("torso_wear", "dress", rigid("cloth", "torso", "Dress with sleeves to the elbow."),
               {"rigid": {("s", 0): DRESS_S, ("e", 0): DRESS_E, ("n", 0): DRESS_N}})
    write_part("belt", "sash", rigid("accent", "torso", "Sash knotted on the hip, tail in front."),
               {"rigid": {("s", 0): SASH_S, ("e", 0): SASH_E, ("n", 0): SASH_N}})
    write_part("legs_wear", "leggings", {
        "material": "leather", "kind": "animated", "lags": False, "rigs": ["humanoid"],
        "notes": "Leather leggings and shoes, redrawn per frame with the legs.",
    }, leggings())
    write_recipe("anchor_girl.yaml", RECIPE)
    print("wrote anchor_girl's parts and recipe")


if __name__ == "__main__":
    main()
