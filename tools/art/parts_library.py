"""The Phase 4 parts library: hairstyles, clothing, armor, headwear and held items.

Rigid parts are drawn once per direction in their idle frame 0 place and follow an anchor;
greaves, boots and gauntlets are derived from every leg and arm frame of the base body, so they
fit every pose. Grids start at x = 8 (column 7 is the pivot, x = 15); each grid names its first row.
Shades are indices into the part's material ramp, 0 = darkest; 'O' is a hand-placed outline pixel.

Run: .venv/bin/python tools/art/parts_library.py
"""

from __future__ import annotations

import numpy as np

from artlib import FRAMES, empty, g, grid, write_part
from humanoid import arm_frames, legs_frames


def G(y0: int, rows: list[str]) -> np.ndarray:
    return g(rows, 8, y0)


def rigid(material: str, attach: str, notes: str, **extra) -> dict:
    return {"material": material, "kind": "rigid", "attach": attach, "origin": "auto",
            "lags": False, "rigs": ["humanoid"], "notes": notes, **extra}


def cells(s, e, n) -> dict:
    return {"rigid": {("s", 0): s, ("e", 0): e, ("n", 0): n}}


# ============================================================================== hair
#                       x: 890123456789012
SHORT_FRONT = {
    "s": G(11, ["....1222221....", "...122222221...", "...112222211...", "...011122110...",
                "...0.......0...", "...0.......0..."]),
    "e": G(11, [".....12222.....", "....1222222....", "...01222222....", "...01122211....",
                "...0011........", "...0011........", "...001.........", "...00.........."]),
    "n": G(11, ["....1222221....", "...022222221...", "...012212211...", "...011202110...",
                "...011101110...", "...001101100...", "...000101000..."]),
}
PULLED_BACK_FRONT = {  # hair drawn back from the face (ponytail and bun): the forehead shows
    "s": G(11, ["....1222221....", "...122222221...", "...112222211...", "...00.....00...",
                "...0.......0...", "...0.......0..."]),
    "e": G(11, [".....12222.....", "....1222221....", "...01222221....", "...011221.....",
                "...0011........", "...0011........", "...001.........", "...00.........."]),
    "n": G(11, ["....1222221....", "...022222221...", "...012222211...", "...011222110...",
                "...011010110...", "...001010100...", "....0000000...."]),
}
PONYTAIL_BACK = {  # the tail trails the head (lags); hidden behind the head facing s
    "s": empty(),
    "e": G(13, ["..1............", ".01............", ".01............", ".01............",
                ".00............", "..0............"]),
    "n": G(14, ["......121......", "......121......", "......111......", "......101......",
                "......010......", "......010......", ".......0.......", ".......0......."]),
}
BUN_BACK = {  # tied up on top: no lag; adds two rows of height like headwear may
    "s": G(8, ["......111......", "......221......", "......111......"]),
    "e": G(9, ["...111.........", "..1222.........", "..011.........."]),
    "n": G(8, ["......111......", "......221......", "......111......"]),
}

# ============================================================================== clothing
TUNIC = {
    "s": G(20, ["...011...110...", "...0011111.....", "....011111.....", "....011111.....",
                "....0000000...."]),
    "e": G(20, ["....001..1.....", "....001111.....", "....001111.....", "....001111.....",
                "....000000....."]),
    "n": G(20, ["...001111111...", "...0011111.....", "....011111.....", "....001111.....",
                "....0000000...."]),
}
ROBE = {  # long robe: a waist seam where a belt would sit and a fold down the skirt
    "s": G(20, ["...01.....11...", "...0011111.....", "....011111.....", "....011111.....",
                "....0000000....", "...001101100...", "...011101110..."]),
    "e": G(20, ["....00...1.....", "....001111.....", "....001111.....", "....001111.....",
                "....000000.....", "...0011011.....", "...0111011....."]),
    "n": G(20, ["...001111111...", "...0011111.....", "....011111.....", "....001111.....",
                "....0000000....", "...001101100...", "...011101110..."]),
}
PLATE = {  # metal: pauldrons on the shoulders, a dark gorget under the chin, lit breastplate
    "s": G(20, ["...330000033...", "...1112332.....", "....112332.....", "....011221.....",
                "....0111110...."]),
    "e": G(20, ["....110003.....", "....012332.....", "....012332.....", "....011221.....",
                "....011111....."]),
    "n": G(20, ["...223333322...", "...1032230.....", "....032230.....", "....002200.....",
                "....0111110...."]),
}
TABARD = {  # cloth panel from collar to hip, flap below the belt
    "s": G(21, [".....11111.....", ".....01110.....", ".....01110.....", ".....01110.....",
                "......010......", "......010......"]),
    "e": G(21, ["........11.....", "........01.....", "........01.....", "........01.....",
                "........0......"]),
    "n": G(21, [".....11111.....", ".....01110.....", ".....01110.....", ".....01110.....",
                "......010......", "......010......"]),
}
LEATHER_BELT = {
    "s": G(24, ["....1111111...."]),
    "e": G(24, ["....111111....."]),
    "n": G(24, ["....1111111...."]),
}
BUCKLE = {"s": G(24, [".......1......."]), "e": G(24, [".........1....."]), "n": empty()}

# ============================================================================== headwear
HOOD = {  # cloth hood framing the face; the seam breaks up the flat top
    "s": G(11, ["....1110111....", "...111101111...", "...111101111...", "...011101110...",
                "...00.....00...", "...00.....00...", "...00.....00...", "...00.....00...",
                "....0.....0....", "...00.....00..."]),
    "e": G(11, [".....11011.....", "....1110111....", "...01110111....", "...01101111....",
                "...0011........", "...0011........", "...0011........", "...0011........",
                "....01.........", "....00........."]),
    "n": G(11, ["....1110111....", "...111101111...", "...111101111...", "...111101111...",
                "...011101110...", "...011101110...", "...001101100...", "...001101100...",
                "....0010100....", "...000000000..."]),
}
GREAT_HELM = {  # metal; one extra row on top; lit dome, a ridge down the middle, dark rim
    "s": G(10, [".....33333.....", "....2333332....", "...023333322...", "...022232221...",
                "...012232221...", "...011232211...", "...011232111...", "...011131110...",
                "...01OOOOO10...", "....0000000...."]),
    "e": G(10, [".....3333......", "....233333.....", "...12333332....", "...01223322....",
                "...01222322....", "...01122321....", "...01122321....", "...01111311....",
                "...0111OOOO....", "....000000....."]),
    "n": G(10, [".....33333.....", "....2333332....", "...023333322...", "...022232221...",
                "...012232211...", "...011232111...", "...011131110...", "...011121110...",
                "...011121100...", "....0000000...."]),
}
PLUME = {  # headwear_trim: a short plume, cloth
    "s": G(8, [".......1.......", ".......0......."]),
    "e": G(8, ["......1........", "......0........"]),
    "n": G(8, [".......1.......", ".......0......."]),
}

# ============================================================================== held items
SWORD = {  # metal blade 4 px: the hand bobs 1 px down in idle and walk, and the tip's outline
    # must stay inside the safe area (y <= 30), so the brief's 6 to 7 px blade can't fit
    "s": G(25, ["..3............", "..3............", "..3............", "..2............"]),
    "e": G(25, ["........3......", "........3......", "........3......", "........2......"]),
    "n": G(25, ["............3..", "............3..", "............3..", "............2.."]),
}
HILT = {  # held_near_trim: grip beside the fist and a 3 px crossguard, accent
    "s": G(23, ["..0............", ".111..........."]),
    "e": G(23, ["........0......", ".......111....."]),
    "n": G(23, ["............0..", "...........111."]),
}
STAFF = {  # wood (leather material): a 10 px staff with a knob, held beside the near hand
    "s": G(18, [".2.............", ".1.............", ".1.............", ".1.............",
                ".1.............", ".1.............", ".1.............", ".0.............",
                ".1.............", ".0............."]),
    "e": G(18, ["............2..", "............1..", "............1..", "............1..",
                "............1..", "............1..", "............1..", "............0..",
                "............1..", "............0.."]),
    "n": G(18, [".............2.", ".............1.", ".............1.", ".............1.",
                ".............1.", ".............1.", ".............1.", ".............0.",
                ".............1.", ".............0."]),
}
BOW = {  # wood: a slim arc held at the grip, string implied; each straight run is one shade
    "s": G(18, ["..0............", ".1.............", ".1.............", ".1.............",
                "..1............", "..1............", "..1............", ".1.............",
                ".1.............", ".1.............", "..0............"]),
    "e": G(18, ["...........0...", "............1..", "............1..", "............1..",
                "...........1...", "...........1...", "...........1...", "............1..",
                "............1..", "............1..", "...........0..."]),
    "n": G(18, ["............0..", ".............1.", ".............1.", ".............1.",
                "............1..", "............1..", "............1..", ".............1.",
                ".............1.", ".............1.", "............0.."]),
}
SHIELD = {  # metal heater shield on the far arm: in front facing s, behind the body otherwise
    "s": G(20, ["..........1332.", "..........1322.", "..........1221.", "..........0221.",
                "...........01..", "...........0..."]),
    "e": G(20, [".........1332..", ".........1322..", ".........1221..", ".........0221..",
                "..........01...", "..........0...."]),
    "n": G(20, [".12............", ".12............", ".12............", ".12............",
                "..1............"]),
}


# ============================================================================== Rolling Knight classes
# Headwear for the six classes (docs/GAMES.md). Wings and brims grow upward, never sideways:
# facing s and n nothing but held items may be wider than the head.
SALLET = {  # metal; visor edge across the brow, the face shows below; a tail at the back facing e
    "s": G(10, [".....33333.....", "....2333332....", "...123333322...", "...022232221...",
                "...012232211...", "...011121110...", "...000000000..."]),
    "e": G(10, [".....3333......", "....233333.....", "...12333332....", "...02233322....",
                "...01223222....", "..001111111....", "..000000000...."]),
    "n": G(10, [".....33333.....", "....2333332....", "...123333322...", "...022232221...",
                "...012232211...", "...011121110...", "...011111110...", "...000000000..."]),
}
MITRE = {  # cloth; a tall pointed hat over the crown, the fringe shows below
    "s": G(8, [".......1.......", "......101......", ".....11011.....", "....1110111....",
               "...111101111...", "...000000000..."]),
    "e": G(8, [".......1.......", "......111......", ".....11111.....", "....1111111....",
               "...11111111....", "...00000000...."]),
    "n": G(8, [".......1.......", "......101......", ".....11011.....", "....1110111....",
               "...111101111...", "...000000000..."]),
}
WIZARD_HAT = {  # cloth; a cone with a bent tip and a dark band where a brim would be
    "s": G(8, [".......11......", "......111......", ".....11111.....", "....1111111....",
               "...000000000..."]),
    "e": G(8, ["......11.......", "......111......", ".....11111.....", "....111111.....",
               "...00000000...."]),
    "n": G(8, ["......11.......", "......111......", ".....11111.....", "....1111111....",
               "...000000000..."]),
}
WINGED_HELM = {  # metal cap with two small wings rising from its sides
    "s": G(8, ["...2.......2...", "...22.....22...", "...223333322...", "...223333322...",
               "...022333220...", "...012232210...", "...011121110...", "...000000000..."]),
    "e": G(8, ["..2............", "..22...........", "...223333......", "....2333332....",
               "...02333332....", "...02233322....", "...00223222....", "...00000000...."]),
    "n": G(8, ["...2.......2...", "...22.....22...", "...223333322...", "...223333322...",
               "...022333220...", "...012232210...", "...011121110...", "...011111110...",
               "...000000000..."]),
}
MACE = {  # metal; held upright, the flanged head above the fist
    "s": G(19, ["222............", "232............", "111............", ".1.............",
                ".1.............", ".1.............", ".1............."]),
    "e": G(19, [".........222...", ".........232...", ".........111...", "..........1....",
                "..........1....", "..........1....", "..........1...."]),
    "n": G(19, ["............222", "............232", "............111", ".............1.",
                ".............1.", ".............1.", ".............1."]),
}
LANCE = {  # wood shaft held upright beside the near hand; the steel head is a trim part
    "s": G(11, [".1............."] * 17 + [".0............."]),
    "e": G(11, ["............1.."] * 17 + ["............0.."]),
    "n": G(11, [".............1."] * 17 + [".............0."]),
}
SPEARHEAD = {  # held_near_trim, metal
    "s": G(8, [".3.............", ".3.............", ".2............."]),
    "e": G(8, ["............3..", "............3..", "............2.."]),
    "n": G(8, [".............3.", ".............3.", ".............2."]),
}
ORB = {  # held_near_trim for a staff, accent: gold for a cleric, silver or red for an arcanist
    "s": G(16, ["11.............", "01............."]),
    "e": G(16, ["............11.", "............10."]),
    "n": G(16, [".............11", ".............10"]),
}


# ============================================================================== derived parts
LEATHER_TO_METAL = {0: 1, 1: 2, 2: 2}  # far leg darker; the visible top of a leg reads as one plate
SKIN_TO_METAL = {0: 2, 1: 2, 2: 3}  # shaded arm -> one mid shade, lit arm -> light


def remap(codes: np.ndarray, table: dict[int, int]) -> np.ndarray:
    out = codes.copy()
    for src, dst in table.items():
        out[codes == src] = dst
    return out


def components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    seen = np.zeros_like(mask)
    out = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        stack, comp = [(y, x)], []
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            comp.append((cy, cx))
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] \
                        and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        out.append(comp)
    return out


def boots_from(legs: np.ndarray) -> np.ndarray:
    """The bottom two rows of every leg (feet in shadow, drawn as 'O', stay as they are)."""
    out = np.full(legs.shape, grid.CLEAR, np.int8)
    for comp in components(legs >= 0):
        bottom = max(y for y, _ in comp)
        for y, x in comp:
            if y >= bottom - 1:
                out[y, x] = legs[y, x]
    return out


def hands_from(arm: np.ndarray, *, only_outside: tuple[int, int] | None = None) -> np.ndarray:
    """Armored forearm and hand: every visible arm pixel in metal (a knight in plate with bare
    forearms reads wrong). With only_outside, keep only pixels that peek out past the torso (the
    far arm facing e is otherwise hidden behind the body)."""
    out = np.full(arm.shape, grid.CLEAR, np.int8)
    for y, x in zip(*np.nonzero(arm >= 0)):
        if only_outside and only_outside[0] <= x <= only_outside[1]:
            continue
        out[y, x] = SKIN_TO_METAL[int(arm[y, x])]
    return out


def derived() -> tuple[dict, dict, dict]:
    greaves, boots, gauntlets = {}, {}, {}
    for (anim, d, i), legs in legs_frames().items():
        digits = np.where(legs >= 0, legs, grid.CLEAR).astype(np.int8)
        greaves.setdefault(anim, {})[(d, i)] = remap(digits, LEATHER_TO_METAL)
        boots.setdefault(anim, {})[(d, i)] = remap(boots_from(digits), {0: 0, 1: 1, 2: 1})
    for (anim, d, i), (near, far, tdx) in arm_frames().items():
        hand = hands_from(near)
        hidden = (12 + tdx, 17 + tdx) if d == "e" else None  # behind the torso facing e
        hand = grid.overlay(hand, hands_from(far, only_outside=hidden))
        gauntlets.setdefault(anim, {})[(d, i)] = hand
    return greaves, boots, gauntlets


def main() -> None:
    hair = "hair"
    write_part("hair_front", "short", rigid(hair, "head", "Short hair with a side fringe and sideburns."),
               cells(**SHORT_FRONT))
    for variant in ("ponytail", "bun"):
        write_part("hair_front", variant, rigid(hair, "head", "Hair drawn back from the face."),
                   cells(**PULLED_BACK_FRONT))
    write_part("hair_back", "ponytail", rigid(hair, "head", "A ponytail; it trails the head.",
                                              lags=True), cells(**PONYTAIL_BACK))
    write_part("hair_back", "bun", rigid(hair, "head", "A bun tied on top; adds two rows."),
               cells(**BUN_BACK))
    write_part("torso_wear", "tunic", rigid("cloth", "torso", "Tunic to the hip, dark hem.",
                                            # the shoulder corners stand alone when a tucked head's
                                            # ears cover the collar (backflip, dodge)
                                            allow_singletons={"s": [[11, 20], [19, 20]]}),
               cells(**TUNIC))
    write_part("torso_wear", "robe", rigid("cloth", "torso", "Long robe to the ankles."), cells(**ROBE))
    write_part("torso_wear", "plate", rigid("metal", "torso", "Breastplate with pauldrons and a "
                                                              "gorget."), cells(**PLATE))
    write_part("over_torso", "tabard", rigid("cloth", "torso", "Tabard panel, front and back."),
               cells(**TABARD))
    write_part("belt", "leather_belt", rigid("leather", "torso", "A leather belt."),
               cells(**LEATHER_BELT))
    write_part("belt_trim", "buckle", rigid("accent", "torso", "Belt buckle.",
                                            allow_singletons={"s": [[15, 24]], "e": [[17, 24]]}),
               cells(**BUCKLE))
    write_part("headwear", "hood", rigid("cloth", "head", "Hood framing the face.",
                                         hides=["hair_front", "hair_locks", "hair_back"]), cells(**HOOD))
    write_part("headwear", "great_helm", rigid("metal", "head", "Rounded great helm with an eye slit.",
                                               hides=["hair_front", "hair_locks", "hair_back", "eyes"]),
               cells(**GREAT_HELM))
    write_part("headwear_trim", "plume", rigid("cloth", "head", "A short plume for a helm."),
               cells(**PLUME))
    write_part("held_near", "sword", rigid("metal", "hand_near", "Sword held low, blade down.",
                                           allow_singletons={"s": [[10, 28]], "e": [[16, 28]],
                                                             "n": [[20, 28]]}),
               cells(**SWORD))
    write_part("held_near_trim", "hilt", rigid("accent", "hand_near", "Sword crossguard and grip."),
               cells(**HILT))
    write_part("held_near", "staff", rigid("leather", "hand_near", "Wooden staff beside the hand."),
               cells(**STAFF))
    write_part("held_near", "bow", rigid("leather", "hand_near", "Wooden bow held at the grip.",
                                         allow_singletons={"s": [[10, 18], [10, 28]],
                                                           "e": [[19, 18], [19, 28]],
                                                           "n": [[20, 18], [20, 28]]}),
               cells(**BOW))
    # The shield rides the far forearm but is attached to the torso: drawn in front of the body
    # (facing e the far hand is hidden behind it), it must not swing off when that arm moves.
    write_part("held_far", "shield", rigid("metal", "torso", "Heater shield on the far arm."),
               cells(**SHIELD))
    hides_hair = ["hair_front", "hair_locks", "hair_back"]
    write_part("headwear", "sallet", rigid("metal", "head", "Sallet with the visor raised.",
                                           hides=hides_hair), cells(**SALLET))
    write_part("headwear", "mitre", rigid("cloth", "head", "A cleric's mitre."), cells(**MITRE))
    write_part("headwear", "wizard_hat", rigid("cloth", "head", "An arcanist's pointed hat."),
               cells(**WIZARD_HAT))
    write_part("headwear", "winged_helm", rigid("metal", "head", "A cap with two small wings.",
                                                hides=["hair_front"]), cells(**WINGED_HELM))
    write_part("held_near", "mace", rigid("metal", "hand_near", "A flanged mace held upright.",
                                          allow_singletons={"s": [[9, 20]], "e": [[18, 20]],
                                                            "n": [[21, 20]]}), cells(**MACE))
    write_part("held_near", "lance", rigid("leather", "hand_near", "A lance held upright.",
                                           allow_singletons={"s": [[9, 28]], "e": [[20, 28]],
                                                             "n": [[21, 28]]}), cells(**LANCE))
    write_part("held_near_trim", "spearhead", rigid("metal", "hand_near", "A lance's steel head.",
                                                    allow_singletons={"s": [[9, 10]], "e": [[20, 10]],
                                                                      "n": [[21, 10]]}),
               cells(**SPEARHEAD))
    write_part("held_near_trim", "orb", rigid("accent", "hand_near", "An orb atop a staff.",
                                              allow_singletons={"s": [[8, 17]], "e": [[21, 17]],
                                                                "n": [[22, 17]]}), cells(**ORB))
    greaves, boots, gauntlets = derived()
    animated = {"kind": "animated", "lags": False, "rigs": ["humanoid"]}
    write_part("legs_wear", "greaves", {"material": "metal", **animated,
                                        "notes": "Metal greaves, derived from the base legs."}, greaves)
    write_part("feet", "boots", {"material": "leather", **animated,
                                 "notes": "Boots: the bottom two rows of each leg."}, boots)
    write_part("hands", "gauntlets", {"material": "metal", **animated,
                                      "notes": "Armored forearms and hands over the visible arm."},
               gauntlets)
    print("wrote the parts library")


if __name__ == "__main__":
    main()
