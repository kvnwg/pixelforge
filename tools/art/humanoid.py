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
    "....1222221....",  # y11 top of the skull (hidden under hair)
    "...122222221...",  # y12
    "...122222221...",  # y13
    "...122222221...",  # y14
    "...122222221...",  # y15 forehead shows under the center part
    "...122222221...",  # y16
    "...122222221...",  # y17
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
    ".....12222.....",  # y11 skull (under hair)
    "....1122222....",  # y12
    "...11122222....",  # y13
    "...11122222....",  # y14
    "...11122222....",  # y15 forehead peeks out at x 18
    "...11111222....",  # y16 face: x 15 mid, x 16-18 light
    "...11111222....",  # y17
    "...11111222....",  # y18 eye at x 17 (eyes part)
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
    "...122222221...",  # y12
    "...122222221...",  # y13
    "...122222221...",  # y14
    "...122222221...",  # y15
    "...122222221...",  # y16
    "...112222211...",  # y17
    "...111222111...",  # y18
    "....1122211....",  # y19 nape (under hair)
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


def main() -> None:
    body, near, far, anchors = idle()
    meta = {"material": "skin", "kind": "animated", "lags": False, "rigs": ["humanoid"]}
    write_part("body", "humanoid", {**meta, "notes": "Skin-only mannequin: bald head, bare "
                                                      "torso, legs. Arms are separate slots."},
               {"idle": body})
    write_part("arm_near", "humanoid", {**meta, "notes": "The near arm (the character's right; "
                                                          "viewer-left facing s). Holds held_near."},
               {"idle": near})
    write_part("arm_far", "humanoid", {**meta, "notes": "The far arm (the character's left; "
                                                         "viewer-right facing s). Holds held_far."},
               {"idle": far})
    write_anchors("humanoid", {"idle": anchors})
    print("wrote the humanoid base body")


if __name__ == "__main__":
    main()
