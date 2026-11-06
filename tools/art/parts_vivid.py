"""Design pass 2 parts (2026-11-06): bold pieces that change a character's silhouette at 1x.

The human asked for "vibrant and interesting and unique" characters "with certain characteristics
on their body like scarves or weird hats or capes". The first design pass's pieces were too timid
to change a silhouette (a 1 px plume, a scarf with a 2 px tail, a cape that only showed as a
sliver facing s), so these are big on purpose:

- `headwear_trim/plume_tall`: a crest rising 6 rows over a great helm and curling over; it sways.
- `headwear_trim/horns_curled`: viking horns sweeping out past the head and up.
- `scarf/long`: a wrap with a tail that streams 6 px out to one side; it follows through.
- `cape/mantle`: a cape that flares past both shoulders down to the ankles; it follows through.
- `headwear/pointed_hood`: a hood whose point rises and flops over.
- `headwear/tricorn`: a three-cornered hat, the brim turned up at the sides.
- `headwear/mitre_tall`: a tall two-peaked mitre with bands.
- `headwear_emblem/*` (a slot drawn over the headwear, its own material): a gold cross for a
  great helm, a cross for a mitre, a gold band for a wizard hat.

Grids: rows of characters from (x0, y0); shades index the part's material ramp, 0 = darkest;
'O' is a hand-placed outline pixel. Drawn in the idle frame 0 place; rigid parts follow their
anchor (`head` or `torso`), parts with `lags` trail the body by a frame.

Run after parts_design.py: .venv/bin/python tools/art/parts_vivid.py
"""

from __future__ import annotations

import numpy as np

from artlib import empty, g, write_part


def G(x0: int, y0: int, rows: list[str]) -> np.ndarray:
    width = {len(r) for r in rows}
    assert len(width) == 1, f"ragged grid at ({x0}, {y0}): widths {sorted(width)}"
    return g(rows, x0, y0)


def rigid(material: str, attach: str, notes: str, lags: bool = False, **extra) -> dict:
    return {"material": material, "kind": "rigid", "attach": attach, "origin": "auto",
            "lags": lags, "rigs": ["humanoid"], "notes": notes, **extra}


def cells(s, e, n) -> dict:
    return {"rigid": {("s", 0): s, ("e", 0): e, ("n", 0): n}}


# ============================================================================== head trims
# Headgear tops sit at row 7 or lower: the head rises up to 4 px in a backflip or vault, and the
# outline must stay inside the safe area (y >= 2). Trims on the head do not lag, so the head keeps
# its height (E10) and nothing overshoots past the top.
#            x: 2345678
PLUME_TALL = {  # cloth: a crest on the helm's crown curling over; facing e it sweeps back and down
    "s": G(12, 7, ["...1111.",
                   "..011.11",
                   "..011..1"]),
    #            x: 789012345
    "e": G(7, 7, ["...11111.",
                  "..11..101",
                  ".11....01",
                  "11.......",
                  "1........"]),
    #             x: 12345678
    "n": G(11, 7, [".1111...",
                   "11.011..",
                   "1..011.."]),
}
#                   x: 6789012345678901234
HORNS_CURLED = {  # horn: from the helm's upper sides out past the head and up, light tips
    "s": G(6, 6, [".2...............2.",
                  ".22.............22.",
                  ".12.............21.",
                  ".111...........111.",
                  "..111.........111..",
                  "...001.......100..."]),
    #            x: 678901234567890123
    "e": G(6, 6, [".2..............2.",
                  ".22............22.",
                  ".12............21.",
                  ".111..........111.",
                  "..111........111..",
                  "...001......100..."]),
    "n": G(6, 6, [".2...............2.",
                  ".22.............22.",
                  ".12.............21.",
                  ".111...........111.",
                  "..111.........111..",
                  "...001.......100..."]),
}

#                x: 890123456789012
MESSY_FRONT = {  # hair: the short cut with uneven tufts sticking up off the crown (Kevin's mop); each
    # tuft is a 3 px cluster of the mid shade (light would make the crown one flat area, W5)
    "s": G(8, 9, [".....1..11.....",
                  ".....11..11....",
                  "....1222221....",
                  "...122222221...",
                  "...112222211...",
                  "...011122110...",
                  "...0.......0...",
                  "...0.......0..."]),
    "e": G(8, 9, ["....1..1.......",
                  "....11.11......",
                  ".....12222.....",
                  "....1222222....",
                  "...01222222....",
                  "...01122211....",
                  "...0011........",
                  "...0011........",
                  "...001.........",
                  "...00.........."]),
    "n": G(8, 9, [".....11..1.....",
                  "....11..11.....",
                  "....1222221....",
                  "...022222221...",
                  "...012212211...",
                  "...011202110...",
                  "...011101110...",
                  "...001101100...",
                  "...000101000..."]),
}

# ============================================================================== flowing cloth
# Shades come in clusters of 2 px or more (STYLE_GUIDE.md section 7): the scarf's tail is banded in
# 2 x 2 blocks, the cape's edges are a dark strip on the shadow side and a light one on the lit side.
#                x: 8901234567890123456
SCARF_LONG = {  # cloth: a wrap over the collar, the tail streams out to the side in bands
    "s": G(8, 19, ["....1111111........",
                   "...00111110011.....",
                   "............11001..",
                   "..............0011.",
                   "................110",
                   ".................00"]),
    #            x: 678901234567  (6 px of tail: a block's 3 px knockback keeps it on the canvas)
    "e": G(6, 19, [".......1111.",
                   "....0011111.",
                   "..1100......",
                   "0011........",
                   "00.........."]),
    #            x: 4567890123456789
    "n": G(4, 19, ["........1111111.",
                   ".....11001111100",
                   "..10011.........",
                   ".1100...........",
                   "011.............",
                   "00.............."]),
}
#               x: 6789012345678901234
CAPE_MANTLE = {  # cloth: from the shoulders to the ankles, flaring past both sides of the body;
    # facing s a dark strip shows on the shadow side and a light one on the lit side, facing n it
    # covers the back in panels split by folds
    "s": G(6, 20, ["....01111111111....",
                   "....011111111111...",
                   "...0011111111111...",
                   "...00111111111111..",
                   "..000111111111111..",
                   "..0001111111111111.",
                   ".00000000000000000."]),
    #            x: 456789012
    "e": G(4, 20, [".......11",
                   "......011",
                   ".....0011",
                   "....00111",
                   "...001111",
                   "..001111.",
                   ".0000000."]),
    "n": G(6, 20, ["....11101110111....",
                   "....111011101111...",
                   "...1110111011101...",
                   "...11101110111011..",
                   "..111101110111011..",
                   "..1111011101110111.",
                   ".00000000000000000."]),
}

# ============================================================================== headwear
#                 x: 7890123456789012
POINTED_HOOD = {  # cloth: a hood framing the face, its point rises and flops over to one side
    #            x: 7890123456789012
    "s": G(7, 7, [".........110....",
                  "........1100....",
                  ".......1110.....",
                  ".....111011.....",
                  ".....1110111....",
                  "....111101111...",
                  "....111101111...",
                  "....011101110...",
                  "....00.....00...",
                  "....00.....00...",
                  "....00.....00...",
                  "....00.....00...",
                  ".....0.....0....",
                  "....00.....00..."]),
    "e": G(7, 7, ["..11............",
                  "..111...........",
                  "...1111.........",
                  "....11111.......",
                  "......11011.....",
                  ".....1110111....",
                  "....01110111....",
                  "....01101111....",
                  "....0011........",
                  "....0011........",
                  "....0011........",
                  "....0011........",
                  ".....01.........",
                  ".....00........."]),
    "n": G(7, 7, ["....011.........",
                  "....0011........",
                  ".....0111.......",
                  ".....110111.....",
                  "....1110111.....",
                  "....111101111...",
                  "....111101111...",
                  "....111101111...",
                  "....011101110...",
                  "....011101110...",
                  "....001101100...",
                  "....001101100...",
                  ".....0010100....",
                  "....000000000..."]),
}
TRICORN = {  # cloth: a crown over a dark band, a wide brim turned up at both sides and creased
    # down the middle, the front point dips over the brow
    #            x: 78901234567890123
    "s": G(7, 8, ["......11111......",
                  ".1...1111111...1.",
                  ".11.000000000.11.",
                  ".011111101111110.",
                  "..0011110111100..",
                  "....000101000....",
                  ".......000......."]),
    #            x: 67890123456789012
    "e": G(6, 8, [".......1111......",
                  "......111111.....",
                  "..1..10000001.1..",
                  "..11111110111111.",
                  "..0111111011110..",
                  "...000000000000.."]),
    "n": G(7, 8, ["......11111......",
                  ".1...1111111...1.",
                  ".11.000000000.11.",
                  ".011111101111110.",
                  "..0011110111100..",
                  "....000000000....",
                  "................."]),
}
#                  x: 01234567890
MITRE_TALL = {  # cloth: two peaks with a cleft, dark bands at the sides, a dark band at the brow
    "s": G(10, 6, ["....1.1....",
                   "...11011...",
                   "..0111110..",
                   "..0111110..",
                   ".001111100.",
                   ".011111110.",
                   ".000000000."]),
    "e": G(10, 6, ["....1......",
                   "....11.....",
                   "...011.....",
                   "..00111....",
                   ".0011111...",
                   ".0111111...",
                   ".00000000.."]),
    "n": G(10, 6, ["....1.1....",
                   "...11011...",
                   "..0111110..",
                   "..0111110..",
                   ".001111100.",
                   ".011111110.",
                   ".000000000."]),
}
#                x: 1234567890
CIRCLET = {  # accent: a gold crown band over the hair with three points
    "s": G(11, 8, [".1..1..1.",
                   ".1.111.1.",
                   ".1111111.",
                   ".0000000."]),
    "e": G(11, 8, ["..1..1..",
                   "..1.111.",
                   ".111111.",
                   ".000000."]),
    "n": G(11, 8, [".1..1..1.",
                   ".1.111.1.",
                   ".1111111.",
                   ".0000000."]),
}

#               x: 890123456789012
WING_CAP = {  # metal: the winged helm's cap without its small metal wings (wings are a trim)
    "s": G(8, 10, ["...223333322...", "...223333322...", "...022333220...", "...012232210...",
                   "...011121110...", "...000000000..."]),
    "e": G(8, 10, ["...223333......", "....2333332....", "...02333332....", "...02233322....",
                   "...00223222....", "...00000000...."]),
    "n": G(8, 10, ["...223333322...", "...223333322...", "...022333220...", "...012232210...",
                   "...011121110...", "...011111110...", "...000000000..."]),
}
#                 x: 6789012345678901234
WINGS = {  # cloth (white): feathered wings sweeping out and up from the cap's sides
    "s": G(6, 7, [".11.............11.",
                  ".111...........111.",
                  "..0111.......1110..",
                  "...0011.....1100...",
                  "....001.....100...."]),
    #            x: 890123
    "e": G(8, 7, ["11....",
                  "111...",
                  "0111..",
                  ".0011.",
                  "..001."]),
    "n": G(6, 7, [".11.............11.",
                  ".111...........111.",
                  "..0111.......1110..",
                  "...0011.....1100...",
                  "....001.....100...."]),
}

# ============================================================================== emblems (accent)
#                 x: 2345678
CROSS_HELM = {  # a gold cross on the great helm's face, above the eye slit
    "s": G(12, 12, ["...1...",
                    "...1...",
                    ".11111.",
                    "...1...",
                    "...0..."]),
    "e": G(17, 12, ["1.",
                    "1.",
                    "11",
                    "1.",
                    "0."]),
    "n": empty(),
}
CROSS_MITRE = {  # a gold cross on the mitre's front (and back)
    "s": G(14, 7, [".1.",
                   "111",
                   ".1.",
                   ".0."]),
    "e": G(15, 8, ["1",
                   "1",
                   "0"]),
    "n": G(14, 7, [".1.",
                   "111",
                   ".1.",
                   ".0."]),
}
#                 x: 890123456789012
HATBAND = {  # a gold band around a wizard hat's crown, a buckle in front
    "s": G(11, 12, ["011111110"]),
    "e": G(11, 12, ["01111111"]),
    "n": G(11, 12, ["011111110"]),
}


def main() -> None:
    write_part("headwear_trim", "plume_tall", rigid(
        "cloth", "head", "A plume on a great helm's crown curling over; facing e it sweeps back."),
        cells(**PLUME_TALL))
    write_part("headwear_trim", "horns_curled", rigid(
        "horn", "head", "Viking horns sweeping out past the head and up, light at the tips."),
        cells(**HORNS_CURLED))
    write_part("hair_front", "messy", rigid(
        "hair", "head", "A mop with a few tufts sticking up and a ragged fringe."), cells(**MESSY_FRONT))
    write_part("scarf", "long", rigid(
        "cloth", "torso", "A scarf wrapped over the collar, its long tail streaming out to one side "
        "in bands; it follows through.", lags=True), cells(**SCARF_LONG))
    write_part("cape", "mantle", rigid(
        "cloth", "torso", "A cape from the shoulders to the ankles that flares past both sides of "
        "the body; it follows through.", lags=True,
        # facing s a body sinking to its knees (death) shows the hem through the gaps by the legs
        allow_singletons={"s": [[10, 24], [10, 26], [13, 26], [17, 26]]}), cells(**CAPE_MANTLE))
    hides_hair = ["hair_front", "hair_locks", "hair_back"]
    write_part("headwear", "pointed_hood", rigid(
        "cloth", "head", "A hood framing the face; its point rises and flops over.", hides=hides_hair),
        cells(**POINTED_HOOD))
    write_part("headwear", "tricorn", rigid(
        "cloth", "head", "A three-cornered hat: a wide brim turned up at both sides."),
        cells(**TRICORN))
    write_part("headwear", "mitre_tall", rigid(
        "cloth", "head", "A tall two-peaked mitre with side bands."), cells(**MITRE_TALL))
    write_part("headwear", "wing_cap", rigid(
        "metal", "head", "A rounded cap for a pair of wings (headwear_trim/wings).", hides=["hair_front"]),
        cells(**WING_CAP))
    write_part("headwear_trim", "wings", rigid(
        "cloth", "head", "White feathered wings sweeping out and up from a cap's sides."), cells(**WINGS))
    write_part("headwear", "circlet", rigid(
        "accent", "head", "A gold crown band over the hair with three points."), cells(**CIRCLET))
    write_part("headwear_emblem", "cross_helm", rigid(
        "accent", "head", "A gold cross on a great helm's face."), cells(**CROSS_HELM))
    write_part("headwear_emblem", "cross_mitre", rigid(
        "accent", "head", "A gold cross on a mitre."), cells(**CROSS_MITRE))
    write_part("headwear_emblem", "hatband", rigid(
        "accent", "head", "A gold band around a wizard hat's crown."), cells(**HATBAND))
    print("wrote the design pass 2 parts")


if __name__ == "__main__":
    main()
