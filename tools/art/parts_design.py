"""The design pass parts (2026-11-05): pieces that change a character's silhouette, so a cast reads
as different people at a glance instead of one body in different colors.

- back of the character: `cape/cloak` (follows through), `scarf/wrap` (tails follow through)
- shoulders: `shoulders/pauldrons` (big plates that widen the figure by 3 px a side)
- head: `beard/full`, `ears/elf`, `ears/cat`, `hair_front/spiky` (+ `hair_back/spiky`),
  `hair_back/twintails` (follow through), `headwear/ranger_hat` with `headwear_trim/feather`,
  `headwear/bandana`, `headwear/witch_hat`

Grids follow parts_library.py: 15 columns from x = 8 (column 7 is the pivot, x = 15) unless an
x0 is given, the first row named; shades index the part's material ramp, 0 = darkest; 'O' is a
hand-placed outline pixel. Drawn in their idle frame 0 place; rigid parts follow their anchor.

Run after parts_library.py: .venv/bin/python tools/art/parts_design.py
"""

from __future__ import annotations

import numpy as np

from artlib import empty, g, write_part


def G(y0: int, rows: list[str], x0: int = 8) -> np.ndarray:
    return g(rows, x0, y0)


def rigid(material: str, attach: str, notes: str, lags: bool = False, **extra) -> dict:
    return {"material": material, "kind": "rigid", "attach": attach, "origin": "auto",
            "lags": lags, "rigs": ["humanoid"], "notes": notes, **extra}


def cells(s, e, n) -> dict:
    return {"rigid": {("s", 0): s, ("e", 0): e, ("n", 0): n}}


#                       x: 890123456789012
CLOAK = {  # cloth; facing s it shows past the shoulders, facing e it trails behind,
    # facing n it covers the back (under the hair)
    "s": G(20, ["...000000000...", "..10000000001..", "..10000000001..", "..11000000011.."]),
    "e": G(20, ["....110", "...1100", "..11000", "..11000", ".110000", ".11000.", ".111..."], x0=7),
    "n": G(20, ["...000000000...", "..111O111O111..", "..111O111O111..", "..111O111O111..",
                "..111O111O111..", "..110O111O011..", "...000000000..."]),
}
WRAP = {  # cloth scarf: a wrap over the collar and the chin's edge, tails that follow through
    "s": G(19, ["....1111111....", "...001111100...", "....11.........", "....10.........",
                "....10.........", ".....0........."]),
    "e": G(19, [".....11111.....", "...1111111.....", ".1100..........", ".00............"]),
    "n": G(19, ["....1111111....", "...001111100...", "......11.......", "......11.......",
                "......11.......", "......00......."]),
}
PAULDRONS = {  # metal: banded plates (lames), light on top down to a dark rim; 5 px a side
    "s": G(19, [".333.....333.", "22222...22222", "11111...11111", ".000.....000."], x0=8),
    "e": G(20, ["....33..", "...2222.", "...1111."], x0=8),
    "n": G(19, [".333.....333.", "22222...22222", "11111...11111", ".000.....000."], x0=8),
}
BEARD = {  # hair: sideburns beside the eyes, a full beard over the chin and the chest
    "s": G(17, ["...1.......1...", "...1.......1...", "...112222211...", "....1122211....",
                ".....11211.....", "......000......"]),
    "e": G(17, ["......1........", "......1........", "......11222....", ".......11222...",
                "........1122...", ".........000..."]),
    "n": empty(),
}
ELF_EARS = {  # skin: long ears pointing up and out
    "s": G(14, ["1.............1", "12...........21", ".21.........12.", "..1.........1.."]),
    "e": G(14, ["..1............", "..11...........", "...122.........", "....22........."]),
    "n": G(14, ["1.............1", "12...........21", ".21.........12.", "..1.........1.."]),
}
CAT_EARS = {  # hair: two solid triangles on top of the head
    "s": G(8, ["...1.......1...", "...11.....11...", "...111...111..."]),
    "e": G(8, [".....1..1......", ".....11.11.....", ".....11.11....."]),
    "n": G(8, ["...1.......1...", "...11.....11...", "...111...111..."]),
}
SPIKY_FRONT = {  # hair: three locks of spikes split by outline-colored strands, spiky bangs
    "s": G(8, ["...2...2...2...", "...22.222.22...", "...22O222O22...", "...12O222O21...",
               "..112O222O211..", "..111O121O111..", "...011121110...", "...0.......0...",
               "...0.......0..."]),
    "e": G(8, ["....2...2......", "....22.222.....", "....22O2222....", "....12O2222....",
               "...112O2222....", "...0111O122....", "...0011O12.....", "...0011........",
               "...0011........", "...001.........", "...00.........."]),
    "n": G(8, ["...2...2...2...", "...22.222.22...", "...22O222O22...", "...12O222O21...",
               "..112O222O211..", "..111O222O111..", "...011202110...", "...011101110...",
               "...001101100...", "...000101000..."]),
}
SPIKY_BACK = {  # spikes sticking out behind the head facing e
    "s": empty(),
    "e": G(11, ["..11...........", ".111...........", "..11...........", ".00............"]),
    "n": empty(),
}
TWINTAILS = {  # hair: two tails tied at the sides of the head, hanging to the waist
    "s": G(12, [".11.........11.", ".12.........21.", ".12.........21.", ".12.........21.",
                ".12.........21.", ".11.........11.", ".01.........10.", ".0...........0."]),
    "e": G(12, ["..11...........", ".12............", ".12............", ".12............",
                ".12............", ".11............", ".01............", ".0............."]),
    "n": G(12, [".11.........11.", ".12.........21.", ".12.........21.", ".12.........21.",
                ".12.........21.", ".11.........11.", ".01.........10.", ".0...........0."]),
}
RANGER_HAT = {  # leather: a crown with a dark band and a wide brim, 3 to 4 px past the head
    "s": G(8, ["....2222222....", "...122222221...", "...111111111...", "...000000000...",
               ".1122222222211.", "000000000000000"], x0=8),
    "e": G(8, [".....22222.....", "....1222222....", "....1111111....", "....0000000....",
               "..112222222211.", ".0000000000000."], x0=7),
    "n": G(8, ["....2222222....", "...122222221...", "...111111111...", "...000000000...",
               ".1122222222211.", "000000000000000"], x0=8),
}
FEATHER = {  # accent: a feather in the hat band, rising and curling back
    "s": G(7, ["..........11...", "..........1....", ".........11....", ".........1....."]),
    "e": G(7, ["..11...........", "...1...........", "...11..........", "....1.........."]),
    "n": G(7, ["...11..........", "....1..........", "....11.........", ".....1........."]),
}
WITCH_HAT = {  # cloth: a tall cone bent at the tip over a wide brim; the arcanist's signature
    "s": G(6, ["..........11.....", ".........11......", "........111......",
               ".......1111......", "......01111......", ".....0011111.....", "....000000000....",
               ".111111111111111.", ".000000000000000."], x0=7),
    "e": G(6, ["....11...........", ".....11..........", ".....111.........",
               ".....1111........", ".....01111.......", ".....001111......", "....00000000.....",
               "..1111111111111..", "..0000000000000.."], x0=7),
    "n": G(6, ["......11.........", ".......11........", ".......111.......",
               ".......1111......", ".......11110.....", ".....1111100.....", "....000000000....",
               ".111111111111111.", ".000000000000000."], x0=7),
}
BANDANA = {  # cloth: a band over the top of the head, a knot and tails at one side
    "s": G(11, ["....1111111....", "...111111111...", "...000000000...", "...............",
                "..............."]),
    "e": G(11, [".....11111.....", "....1111111....", "..110000000....", ".11............",
                ".00............"]),
    "n": G(11, ["....1111111....", "...111111111...", "...000000000...", "......111......",
                "......1.1......", "......1.1......"]),
}


def main() -> None:
    write_part("cape", "cloak", rigid("cloth", "torso", "A cloak hanging from the shoulders; it "
                                      "follows through when the body moves.", lags=True,
                                      # facing n long hair covers the middle of the collar and the
                                      # hem in a roll, leaving their corners alone
                                      allow_singletons={"n": [[11, 20], [19, 20], [11, 26], [19, 26]]}),
               cells(**CLOAK))
    write_part("scarf", "wrap", rigid("cloth", "torso", "A scarf wrapped over the collar with "
                                      "tails that follow through.", lags=True), cells(**WRAP))
    write_part("shoulders", "pauldrons", rigid("metal", "torso", "Big domed shoulder plates: the "
                                               "figure is 3 px wider a side."), cells(**PAULDRONS))
    write_part("beard", "full", rigid("hair", "head", "Sideburns and a full beard over the chin "
                                      "and chest (hair colors)."), cells(**BEARD))
    write_part("ears", "elf", rigid("skin", "head", "Long pointed ears through the hair."),
               cells(**ELF_EARS))
    write_part("ears", "cat", rigid("hair", "head", "Animal ears on top of the head, in the hair's "
                                    "color."), cells(**CAT_EARS))
    write_part("hair_front", "spiky", rigid("hair", "head", "A crown of spikes and spiky bangs."),
               cells(**SPIKY_FRONT))
    write_part("hair_back", "spiky", rigid("hair", "head", "Spikes behind the head (facing e).",
                                           lags=True), cells(**SPIKY_BACK))
    write_part("hair_back", "twintails", rigid("hair", "head", "Two tails tied at the sides of the "
                                               "head; they follow through.", lags=True),
               cells(**TWINTAILS))
    write_part("headwear", "ranger_hat", rigid("leather", "head", "A wide-brimmed hat with a dark "
                                               "band."), cells(**RANGER_HAT))
    write_part("headwear_trim", "feather", rigid("accent", "head", "A feather in the hat band."),
               cells(**FEATHER))
    write_part("headwear", "witch_hat", rigid("cloth", "head", "A tall cone bent at the tip over a "
                                              "wide brim."), cells(**WITCH_HAT))
    write_part("headwear", "bandana", rigid("cloth", "head", "A cloth band over the head, knotted "
                                            "at the back."), cells(**BANDANA))
    print("wrote the design pass parts")


if __name__ == "__main__":
    main()
