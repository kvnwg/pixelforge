"""The humanoid base body: skin-only mannequin, its arms, and anchors.

Skin shades: 0 shadow #9f6f65, 1 mid #c08d80, 2 light #dba292. 'O' is a hand-placed outline pixel.
Grids start at x = 8, y = 10 (as in STYLE_GUIDE.md section 2), so column 7 is x = 15, the pivot.

Run: .venv/bin/python tools/art/humanoid.py
"""

from __future__ import annotations

from artlib import FRAMES, IDLE_UPPER_DY, empty, g, grid, shift_anchors, split_shift, write_anchors, write_part

# ---------------------------------------------------------------------------------------------
# idle frame 0, facing s (the anchor pose). The head under the hair is a complete bald head, the
# torso under the dress is bare, the legs are the leggings' footprint, so any outfit works.
#                x: 890123456789012
BODY_S = g([
    "...............",  # y10
    "....1222221....",  # y11 top of the skull (hidden under hair; shaded like a sphere so
    "...012222221...",  # y12   bald, short and pulled-back hair look round)
    "...011222221...",  # y13
    "...011111211...",  # y14
    "...011122211...",  # y15 forehead shows under the center part
    "...112222211...",  # y16
    "...112222211...",  # y17
    "...122222221...",  # y18 eye row: skin mid cheeks at x 11 and 19
    "....0222220....",  # y19 chin, skin shadow at both ends
    "...110000011...",  # y20 collar line (skin shadow) between the shoulders
    "...1122221.....",  # y21 shoulder and torso (under the dress)
    "....122221.....",  # y22
    "....122221.....",  # y23
    "....1111111....",  # y24 waist (under belt and hem)
    "....211..11....",  # y25 tops of the legs
    "....220..OO....",  # y26 set-back foot: two hand-placed dark pixels
    "....220........",  # y27 planted foot on the baseline
])
# Arms hang beside the torso, above clothing in z-order. Facing s, the near arm (the character's
# right) is on the viewer's left, in shade; the far arm is lit. The hip tucks below each hand are
# hand-placed outline pixels.
ARM_NEAR_S = g([
    "...............",  # y10
] + ["..............."] * 11 + [
    "...0...........",  # y22 skin shadow
    "...1...........",  # y23 hand, skin mid
    "..O............",  # y24 hip tuck
])
ARM_FAR_S = g([
    "...............",
] + ["..............."] * 10 + [
    "..........22...",  # y21
    "..........12...",  # y22
    "..........12...",  # y23 hand
    "............O..",  # y24 hip tuck
])

# idle frame 0, facing e (screen-right). Head 8 px wide (10 with outline), same 10 rows; the
# face is the lit front quarter; hair (separate parts) covers the top and back. The near arm is in
# front of the torso; the far arm is hidden behind it. The near leg is planted with the foot
# pointing forward; the far leg is set back one pixel up and behind, its foot dark like the anchor's.
#                x: 890123456789012
BODY_E = g([
    "...............",  # y10
    ".....12222.....",  # y11 skull (under hair), lit on top and front, dark at the back
    "....1122222....",  # y12
    "...01122222....",  # y13
    "...01112221....",  # y14
    "...00111112....",  # y15 forehead peeks out at x 18
    "...00101222....",  # y16 face: x 15 mid, x 16-18 light; ear in shadow at x 14
    "...00101222....",  # y17
    "...01111222....",  # y18 eye at x 17 (eyes part)
    "....110221.....",  # y19 jaw; shadow at the back under the ear
    "....110001.....",  # y20 neck: the collar line
    "....122221.....",  # y21 torso (under the dress)
    "....122221.....",  # y22
    "....122221.....",  # y23
    "....111111.....",  # y24 waist
    ".....1121......",  # y25 far leg x 13-14, near leg x 15-16
    ".....OO21......",  # y26 far foot set back (dark), near leg
    ".......211.....",  # y27 near foot planted, toes forward
])
ARM_NEAR_E = g(["..............."] * 12 + [
    ".......2.......",  # y22 forearm in front of the dress, lit
    ".......1.......",  # y23 hand
])
ARM_FAR_E = g(["..............."] * 12 + [
    ".....1.........",  # y22 hidden behind the torso at rest
    ".....0.........",  # y23
])

# idle frame 0, facing n (away). The silhouette matches s so turning never pops: same head, same
# arm and leg positions on screen. Facing n the near (right) arm is on the viewer's right, so the
# lit 2 px arm is the near arm here and the 1 px shaded arm is the far arm.
BODY_N = g([
    "...............",  # y10
    "....1222221....",  # y11 back of the skull (under hair)
    "...012222221...",  # y12
    "...012222211...",  # y13
    "...011222111...",  # y14
    "...011111111...",  # y15
    "...001111110...",  # y16
    "...001121100...",  # y17
    "...111222111...",  # y18 nape (shows under short hair and when the hair lifts)
    "....1122211....",  # y19
    "...111111111...",  # y20 shoulders (under the dress)
    "...1122221.....",  # y21
    "....122221.....",  # y22
    "....122221.....",  # y23
    "....1111111....",  # y24
    "....211..11....",  # y25 legs: same place on screen as facing s
    "....220..OO....",  # y26
    "....220........",  # y27
])

ANCHORS_S0 = {
    "head": [15, 11], "chin": [15, 19], "torso": [15, 20], "back": [15, 21], "hip": [15, 25],
    "hand_near": [11, 23], "hand_far": [19, 23],
    "foot_near": [13, 27], "foot_far": [17, 26], "planted": ["foot_near", "foot_far"],
}
ANCHORS_E0 = {
    "head": [15, 11], "chin": [15, 19], "torso": [15, 20], "back": [12, 21], "hip": [15, 25],
    "hand_near": [15, 23], "hand_far": [13, 23],
    "foot_near": [16, 27], "foot_far": [13, 26], "planted": ["foot_near", "foot_far"],
}
ANCHORS_N0 = {
    "head": [15, 11], "chin": [15, 19], "torso": [15, 20], "back": [15, 21], "hip": [15, 25],
    "hand_near": [19, 23], "hand_far": [11, 23],
    "foot_near": [17, 26], "foot_far": [13, 27], "planted": ["foot_near", "foot_far"],
}


HIP = 25  # first leg row in idle frame 0, every direction

# The legs' footprint in idle, as leather shades ('O' = a set-back foot in shadow). Leggings,
# greaves and boots are all derived from these and the walk legs, so every legs part lines up.
LEGS_IDLE = {
    "s": g(["..............."] * 15 + ["....211..11....", "....220..OO....", "....220........"]),
    "e": g(["..............."] * 15 + [".....0021......", ".....OO21......", ".......222....."]),
}
LEGS_IDLE["n"] = LEGS_IDLE["s"]  # the n stance matches s on screen
BODY0 = {"s": BODY_S, "e": BODY_E, "n": BODY_N}
ARM_NEAR0 = {"s": ARM_NEAR_S, "e": ARM_NEAR_E, "n": ARM_FAR_S}
ARM_FAR0 = {"s": ARM_FAR_S, "e": ARM_FAR_E, "n": ARM_NEAR_S}
ANCHORS0 = {"s": ANCHORS_S0, "e": ANCHORS_E0, "n": ANCHORS_N0}


def idle() -> tuple[dict, dict, dict, dict]:
    """Idle: the upper body breathes down and up 1 px; legs and feet never move.
    Hands move with the upper body; hair locks lag through their part's `lags`."""
    body, near, far, anchors = {}, {}, {}, {}
    for d in ("s", "e", "n"):
        anchors[d] = []
        for i, dy in enumerate(IDLE_UPPER_DY):
            body[(d, i)] = split_shift(BODY0[d], HIP, 0, dy)
            near[(d, i)] = grid.translate(ARM_NEAR0[d], 0, dy)
            far[(d, i)] = grid.translate(ARM_FAR0[d], 0, dy)
            anchors[d].append(shift_anchors(ANCHORS0[d], 0, dy))
    return body, near, far, anchors


# ---------------------------------------------------------------------------------------------
# Walk (ANIMATION_SPEC.md section 5): contact, passing, contact, passing at 130 ms.
# Legs are drawn per frame as leather shades with 'O' for a lifted foot in shadow; the skin legs
# under the leggings use the same footprint, so bare legs and leggings line up.
WALK_UPPER_DY = [0, -1, 0, -1]  # the body rises on passing frames; legs extend a row to meet it
WALK_HIP = [25, 24, 25, 24]

LEGS_S = [
    g(["..............."] * 15 + [  # 0 contact A: the anchor stance
        "....211..11....",  # y25
        "....220..OO....",  # y26 viewer-right foot back and lifted, in shadow
        "....220........",  # y27 viewer-left foot planted
    ]),
    g(["..............."] * 14 + [  # 1 passing: legs together, the right foot passes lifted
        "....21101......",  # y24
        "....21101......",  # y25
        "....220OO......",  # y26
        "....220........",  # y27 the same planted foot
    ]),
    g(["..............."] * 15 + [  # 2 contact B: mirror of contact A
        "....11..112....",  # y25
        "....OO..022....",  # y26
        "........022....",  # y27
    ]),
    g(["..............."] * 14 + [  # 3 passing: mirror of frame 1
        "......10112....",  # y24
        "......10112....",  # y25
        "......OO022....",  # y26
        "........022....",  # y27
    ]),
]
# Facing e: near leg light leather (2, 1), far leg dark (1, 0), so they never twin. The supporting
# foot moves back 3 then 2 px (the ground's travel at the walk's natural speed), so it looks
# planted in the game; the swinging foot passes lifted on row 26.
LEGS_E = [  # each leg one shade: a 2 px diagonal stroke shaded front and back is a staircase
    g(["..............."] * 15 + [  # 0 contact A: near foot 3 px ahead, far foot 2 px behind
        ".....0022......",  # y25
        "....00..22.....",  # y26
        "....000..222...",  # y27
    ]),
    g(["..............."] * 14 + [  # 1 passing: near leg under the pivot, far leg lifted behind it
        "......220......",  # y24
        "......220......",  # y25
        "......2200.....",  # y26
        "......222......",  # y27
    ]),
    g(["..............."] * 15 + [  # 2 contact B: far foot ahead, near foot behind
        ".....2200......",  # y25
        "....22..00.....",  # y26
        "....222..000...",  # y27
    ]),
    g(["..............."] * 14 + [  # 3 passing: far leg under the pivot, near leg lifted in front
        "......022......",  # y24
        "......022......",  # y25
        "......0022.....",  # y26
        "......000......",  # y27
    ]),
]
WALK_STRIDE_E = [3, 2, 3, 2]  # px the ground moves back between frames i and i + 1

# Arms swing by reaching 1 px lower (forward) or pulling 1 px shorter (back), so the sleeve
# never detaches. Facing s and n the swing is vertical; facing e the hands swing along x.
ARM_LONG_RIGHT = g(["..............."] * 11 + [   # viewer-right arm reaching 1 px down
    "..........22...", "..........12...", "..........12...", "..........11...", "............O.."])
ARM_SHORT_RIGHT = g(["..............."] * 11 + [  # viewer-right arm 1 px shorter
    "..........22...", "..........11...", "............O.."])
ARM_LONG_LEFT = g(["..............."] * 12 + [    # viewer-left arm reaching 1 px down
    "...0...........", "...1...........", "...1...........", "..O............"])
ARM_SHORT_LEFT = g(["..............."] * 12 + [   # viewer-left arm 1 px shorter
    "...1...........", "..O............"])
ARM_NEAR_E_BACK = g(["..............."] * 12 + [".......2.......", "......1........"])
ARM_NEAR_E_FWD = g(["..............."] * 12 + [".......2.......", "........1......"])
ARM_FAR_E_FWD = g(["..............."] * 12 + ["........1......", ".........10...."])
ARM_FAR_E_BACK = g(["..............."] * 12 + [".....1.........", "...01.........."])


def skin_legs(legs: "np.ndarray") -> "np.ndarray":
    """The bare legs under the leggings: the same footprint and shades, in skin."""
    return legs.copy()


def leather_legs(legs: "np.ndarray") -> "np.ndarray":
    """The leggings for a legs grid: every shade, without the lifted-foot outline pixels."""
    out = legs.copy()
    out[out == grid.INK] = grid.CLEAR
    return out


def walk() -> tuple[dict, dict, dict, dict]:
    body, near, far, anchors = {}, {}, {}, {}
    # facing s and n the legs and swings are drawn in screen space (the n stance matches s)
    right_left = {"s": ("arm_far", "arm_near"), "n": ("arm_near", "arm_far")}
    for d in ("s", "n"):
        anchors[d] = []
        for i, dy in enumerate(WALK_UPPER_DY):
            upper = BODY0[d].copy()
            upper[HIP:] = grid.CLEAR
            body[(d, i)] = grid.overlay(skin_legs(LEGS_S[i]), grid.translate(upper, 0, dy))
            r_slot, l_slot = right_left[d]
            right = {0: ARM_LONG_RIGHT, 2: ARM_SHORT_RIGHT}.get(i, grid.translate(ARM_FAR_S, 0, dy))
            left = {0: ARM_SHORT_LEFT, 2: ARM_LONG_LEFT}.get(i, grid.translate(ARM_NEAR_S, 0, dy))
            (near if r_slot == "arm_near" else far)[(d, i)] = right
            (near if l_slot == "arm_near" else far)[(d, i)] = left
            hand_r = [19, {0: 24, 2: 22}.get(i, 22)]
            hand_l = [11, {0: 22, 2: 24}.get(i, 22)]
            a = shift_anchors(ANCHORS0[d], 0, dy)
            a["hip"] = [15, WALK_HIP[i]]
            a["hand_near"], a["hand_far"] = (hand_l, hand_r) if d == "s" else (hand_r, hand_l)
            left_foot = [[13, 27], [13, 27], [12, 26], [14, 26]][i]
            right_foot = [[17, 26], [15, 26], [17, 27], [17, 27]][i]
            a["foot_near"], a["foot_far"] = (left_foot, right_foot) if d == "s" else (right_foot, left_foot)
            planted_left = i in (0, 1)
            if d == "s":
                a["planted"] = ["foot_near"] if planted_left else ["foot_far"]
            else:
                a["planted"] = ["foot_far"] if planted_left else ["foot_near"]
            anchors[d].append(a)
    anchors["e"] = []
    near_e = [ARM_NEAR_E_BACK, None, ARM_NEAR_E_FWD, None]
    far_e = [ARM_FAR_E_FWD, None, ARM_FAR_E_BACK, None]
    # the far hand peeks out past the torso in the drawing; its grip anchor (where a shield
    # hangs) swings only 1 px so held items never jump
    hands_e = [([14, 23], [14, 23]), ([15, 22], [13, 22]), ([16, 23], [12, 23]), ([15, 22], [13, 22])]
    feet_e = [([18, 27], [13, 27]), ([15, 27], [16, 26]), ([13, 27], [18, 27]), ([16, 26], [15, 27])]
    planted_e = [["foot_near", "foot_far"], ["foot_near"], ["foot_near", "foot_far"], ["foot_far"]]
    for i, dy in enumerate(WALK_UPPER_DY):
        upper = BODY_E.copy()
        upper[HIP:] = grid.CLEAR
        body[("e", i)] = grid.overlay(skin_legs(LEGS_E[i]), grid.translate(upper, 0, dy))
        near[("e", i)] = near_e[i] if near_e[i] is not None else grid.translate(ARM_NEAR_E, 0, dy)
        far[("e", i)] = far_e[i] if far_e[i] is not None else grid.translate(ARM_FAR_E, 0, dy)
        a = shift_anchors(ANCHORS_E0, 0, dy)
        a["hip"] = [15, WALK_HIP[i]]
        a["hand_near"], a["hand_far"] = hands_e[i]
        a["foot_near"], a["foot_far"] = feet_e[i]
        a["planted"] = planted_e[i]
        anchors["e"].append(a)
    return body, near, far, anchors


def legs_frames() -> dict:
    """(anim, direction, frame) -> legs codes, for every drawn pose."""
    out = {("idle", d, i): LEGS_IDLE[d] for d in ("s", "e", "n") for i in range(len(IDLE_UPPER_DY))}
    for i in range(4):
        out[("walk", "s", i)] = out[("walk", "n", i)] = LEGS_S[i]
        out[("walk", "e", i)] = LEGS_E[i]
    return out


def arm_frames() -> dict:
    """(anim, direction, frame) -> (near arm codes, far arm codes)."""
    _, near, far, _ = idle()
    _, wnear, wfar, _ = walk()
    out = {("idle", d, i): (near[(d, i)], far[(d, i)]) for (d, i) in near}
    out.update({("walk", d, i): (wnear[(d, i)], wfar[(d, i)]) for (d, i) in wnear})
    return out


def main() -> None:
    body, near, far, anchors = idle()
    wbody, wnear, wfar, wanchors = walk()
    meta = {"material": "skin", "kind": "animated", "lags": False, "rigs": ["humanoid"]}
    write_part("body", "humanoid", {**meta, "notes": "Skin-only mannequin: bald head, bare "
                                                      "torso, legs. Arms are separate slots."},
               {"idle": body, "walk": wbody})
    write_part("arm_near", "humanoid", {**meta, "notes": "The near arm (the character's right; "
                                                          "viewer-left facing s). Holds held_near."},
               {"idle": near, "walk": wnear})
    write_part("arm_far", "humanoid", {**meta, "notes": "The far arm (the character's left; "
                                                         "viewer-right facing s). Holds held_far."},
               {"idle": far, "walk": wfar})
    write_anchors("humanoid", {"idle": anchors, "walk": wanchors})
    print("wrote the humanoid base body")


if __name__ == "__main__":
    main()
