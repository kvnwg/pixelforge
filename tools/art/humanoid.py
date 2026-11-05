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


CHIN_ROW = 19  # the head's last row in idle frame 0; the torso starts below it
HEAD_POINTS = ("head", "chin", "eyes", "mouth")
HAND_POINTS = ("hand_near", "hand_far")
# Idle (MOTION.md rule 1, 2): a breath travels through the body one part per frame: the chest
# sinks, then the head, then the hands settle; the chest rises, then the head, then the hands.
# (torso dy, head dy, hands dy) per frame; durations in style.json hold the top and the bottom
# and make the fall quicker than the rise.
IDLE_WAVE = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1), (0, 0, 1)]


def body_pose(d: str, legs: "np.ndarray", t: tuple[int, int], h: tuple[int, int]) -> "np.ndarray":
    """The body with its head and torso moved separately (dx, dy each) over the given legs.
    When the torso drops below the head, the neck stretches: the torso's top row fills the gap.
    From behind (n) that row is the bare upper back, so the gap takes its dark shade: the
    head's shadow on the nape (a flat mid band there would read as a stretched slab, W5)."""
    head, torso = BODY0[d].copy(), BODY0[d].copy()
    head[CHIN_ROW + 1:] = grid.CLEAR
    torso[:CHIN_ROW + 1] = grid.CLEAR
    torso[HIP:] = grid.CLEAR
    layers = [legs, grid.translate(torso, *t)]
    for gap in range(h[1], t[1]):  # rows the head no longer covers
        top = torso.copy()
        top[CHIN_ROW + 2:] = grid.CLEAR
        if d == "n":
            top[(top != grid.CLEAR) & (top != grid.INK)] = 0
        layers.append(grid.translate(top, t[0], gap))
    layers.append(grid.translate(head, *h))
    return grid.overlay(*layers)


def pose_anchors(d: str, t: tuple[int, int], h: tuple[int, int], a: tuple[int, int]) -> dict:
    out = {}
    for name, value in ANCHORS0[d].items():
        if name in ("foot_near", "foot_far", "planted", "hip"):
            out[name] = value
        else:
            dx, dy = h if name in HEAD_POINTS else a if name in HAND_POINTS else t
            out[name] = [value[0] + dx, value[1] + dy]
    return out


def idle() -> tuple[dict, dict, dict, dict]:
    """Idle: a breath that travels chest, head, hands (IDLE_WAVE); legs and feet never move.
    Hair locks follow the head through their part's `lags` (trail, catch up, overshoot)."""
    body, near, far, anchors = {}, {}, {}, {}
    legs = {d: BODY0[d].copy() for d in BODY0}
    for d in legs:
        legs[d][:HIP] = grid.CLEAR
    for d in ("s", "e", "n"):
        anchors[d] = []
        for i, (t, h, a) in enumerate(IDLE_WAVE):
            body[(d, i)] = body_pose(d, legs[d], (0, t), (0, h))
            near[(d, i)] = grid.translate(ARM_NEAR0[d], 0, a)
            far[(d, i)] = grid.translate(ARM_FAR0[d], 0, a)
            anchors[d].append(pose_anchors(d, (0, t), (0, h), (0, a)))
    return body, near, far, anchors


# ---------------------------------------------------------------------------------------------
# Locomotion (ANIMATION_SPEC.md section 5, MOTION.md): the walk and the run have 8 frames each,
# contact, down, pass, up on one leg, then the same on the other. The body bobs on a triangle
# (low on down, high on up), arms swing a frame behind the legs (overlap), and facing e the planted
# foot moves back exactly the stride so it stays put on the ground.
# Facing s and n legs are small grids in screen space ('O' = a foot lifted back, in shadow);
# facing e each leg is drawn from its hip to its foot (leg_e), near leg light, far leg dark.
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


WALK_DY = [0, 1, 0, -1, 0, 1, 0, -1]
WALK_STRIDE_E = [2, 1, 2, 1, 2, 1, 2, 1]  # px the ground moves back between frames i and i + 1
RUN_DY = [0, 1, 0, -1, 0, 1, 0, -1]
RUN_STRIDE_E = [4, 4, 4, 3, 4, 4, 4, 3]
RUN_LEAN = 1  # the run's upper body leans 1 px into the facing (e)


def legs_s(rows: list[str]) -> "np.ndarray":
    """A legs grid whose last row is the ground row 27."""
    return g(["..............."] * (18 - len(rows)) + rows)


def mirror_s(rows: list[str]) -> list[str]:
    """The other leg's pose: legs grids mirror around the pivot column (x 15 = column 7)."""
    flip = {"2": "2", "1": "1", "0": "0", "O": "O", ".": "."}
    return ["".join(flip[c] for c in reversed(r)) for r in rows]


WALK_S_A = [  # left leg planted (frames 0 to 3); the right leg lifts back, passes, reaches
    ["....211..11....", "....220..OO....", "....220........"],                     # contact
    ["....220..OO....", "....220........"],                                        # down (+1)
    ["....21100......", "....220OO......", "....220........"],                     # pass
    ["....211..11....", "....211..11....", "....220..11....", "....220........"],  # up (-1)
]
# The planted leg keeps its foot rows ("220") from contact to up: the body sinks onto it (the
# down frame drops the thigh row, so the sole never changes, W1) and rises off it (the thigh
# row doubles). The free leg darkens as it passes behind (pass, "00") and comes back to mid
# as it swings forward (up), on its way to planted light.
RUN_S_A = [  # the run: the free knee lifts high, and both feet leave the ground on the up frame
    ["....211..11....", "....220..OO....", "....220........"],
    ["....220..OO....", "....220........"],
    ["....211..11....", "....220..11....", "....220........"],
    ["....211..11....", "....220..11....", "....OO...11....", "..............."],  # flight
]


def leg_e(codes: "np.ndarray", hip: tuple[int, int], foot: tuple[int, int], shade: int) -> None:
    """A side-view leg: 2 px wide from the hip down to the foot row, then a 3 px foot pointing
    ahead. A lifted foot is simply a foot above the ground row."""
    (hx, hy), (fx, fy) = hip, foot
    span = max(fy - hy, 1)
    for r in range(hy, fy):
        x = hx + round((fx - hx) * (r - hy) / span)
        codes[r, x:x + 2] = shade
    codes[fy, fx:fx + 3] = shade


def legs_e(dy: int, lean: int, near_foot: tuple[int, int], far_foot: tuple[int, int]) -> "np.ndarray":
    codes = empty()
    hip_y = HIP + dy
    leg_e(codes, (13 + lean, hip_y), far_foot, 0)   # far leg first, dark
    leg_e(codes, (15 + lean, hip_y), near_foot, 2)  # near leg over it, light
    return codes


# facing e: (near foot, far foot) back pixel and row per frame; a foot on row 27 is planted
WALK_FEET_E = [((17, 27), (11, 27)), ((15, 27), (11, 26)), ((14, 27), (14, 26)), ((12, 27), (17, 26)),
               ((11, 27), (17, 27)), ((11, 26), (15, 27)), ((14, 26), (14, 27)), ((17, 26), (12, 27))]
RUN_FEET_E = [((18, 27), (10, 25)), ((14, 27), (13, 25)), ((10, 27), (16, 26)), ((11, 25), (18, 26)),
              ((10, 25), (18, 27)), ((13, 25), (14, 27)), ((16, 26), (10, 27)), ((18, 26), (11, 25))]
# facing s, (left foot, right foot) for the first half; the second half mirrors them
WALK_FEET_S = [([13, 27], [17, 26]), ([13, 27], [17, 26]), ([13, 27], [15, 26]), ([13, 27], [17, 26])]
RUN_FEET_S = [([13, 27], [17, 26]), ([13, 27], [17, 26]), ([13, 27], [17, 26]), ([12, 26], [17, 26])]
# arms swing a frame behind the legs: 'f' forward, 'm' middle, 'b' back (near arm; far opposite)
WALK_NEAR_ARM = "bbmfffmb"  # opposite the near leg: back while it leads (7, 0, 1), forward while it trails
RUN_NEAR_ARM = "bbffffbb"


def _s_arm(right: bool, state: str, dy: int) -> "np.ndarray":
    if state == "m":
        return grid.translate(ARM_FAR_S if right else ARM_NEAR_S, 0, dy)
    if right:
        return grid.translate(ARM_LONG_RIGHT if state == "f" else ARM_SHORT_RIGHT, 0, dy)
    return grid.translate(ARM_LONG_LEFT if state == "f" else ARM_SHORT_LEFT, 0, dy)


def locomotion(dys: list[int], s_legs_a: list[list[str]], s_feet_a: list, feet_e: list,
               near_arm: str, lean: int = 0) -> tuple[dict, dict, dict, dict]:
    """Body, arms and anchors for an 8-frame cycle in s, e and n."""
    body, near, far, anchors = {}, {}, {}, {}
    s_legs = [legs_s(r) for r in s_legs_a] + [legs_s(mirror_s(r)) for r in s_legs_a]
    s_feet = list(s_feet_a) + [([30 - r[0], r[1]], [30 - l[0], l[1]]) for l, r in s_feet_a]
    flip = {"f": "b", "b": "f", "m": "m"}
    for d in ("s", "n"):
        anchors[d] = []
        for i, dy in enumerate(dys):
            body[(d, i)] = body_pose(d, s_legs[i], (0, dy), (0, dy))
            # facing s the viewer's right arm is the far arm and swings with the left leg
            right_state = near_arm[i] if d == "s" else flip[near_arm[i]]
            left_state = flip[right_state]
            if dy > 0:  # as the body dips, the dip takes up the forward reach (a hanging sword's
                # tip stays on the canvas)
                right_state = "m" if right_state == "f" else right_state
                left_state = "m" if left_state == "f" else left_state
            right, left = _s_arm(True, right_state, dy), _s_arm(False, left_state, dy)
            if d == "s":
                near[(d, i)], far[(d, i)] = left, right
            else:
                near[(d, i)], far[(d, i)] = right, left
            reach = {"f": 1, "m": 0, "b": -1}
            hand_r = [19, 23 + dy + reach[right_state]]
            hand_l = [11, 23 + dy + reach[left_state]]
            a = pose_anchors(d, (0, dy), (0, dy), (0, dy))
            a["hip"] = [15, HIP + dy]
            a["hand_near"], a["hand_far"] = (hand_l, hand_r) if d == "s" else (hand_r, hand_l)
            left_foot, right_foot = s_feet[i]
            a["foot_near"], a["foot_far"] = (left_foot, right_foot) if d == "s" else (right_foot, left_foot)
            a["planted"] = [k for k in ("foot_near", "foot_far") if a[k][1] == 27]
            anchors[d].append(a)
    anchors["e"] = []
    for i, dy in enumerate(dys):
        (nf, ff) = feet_e[i]
        body[("e", i)] = body_pose("e", legs_e(dy, lean, nf, ff), (lean, dy), (lean, dy))
        n_state, f_state = near_arm[i], flip[near_arm[i]]
        near_art = {"b": ARM_NEAR_E_BACK, "f": ARM_NEAR_E_FWD, "m": ARM_NEAR_E}[n_state]
        far_art = {"f": ARM_FAR_E_FWD, "b": ARM_FAR_E_BACK, "m": ARM_FAR_E}[f_state]
        near[("e", i)] = grid.translate(near_art, lean, dy)
        far[("e", i)] = grid.translate(far_art, lean, dy)
        a = pose_anchors("e", (lean, dy), (lean, dy), (lean, dy))
        a["hip"] = [15 + lean, HIP + dy]
        a["hand_near"] = [{"b": 14, "m": 15, "f": 16}[n_state] + lean, 23 + dy]
        a["hand_far"] = [{"f": 14, "m": 13, "b": 12}[f_state] + lean, 23 + dy]
        a["foot_near"], a["foot_far"] = [nf[0] + 1, nf[1]], [ff[0] + 1, ff[1]]
        a["planted"] = [k for k, f in (("foot_near", nf), ("foot_far", ff)) if f[1] == 27]
        anchors["e"].append(a)
    return body, near, far, anchors


def walk() -> tuple[dict, dict, dict, dict]:
    return locomotion(WALK_DY, WALK_S_A, WALK_FEET_S, WALK_FEET_E, WALK_NEAR_ARM)


def run() -> tuple[dict, dict, dict, dict]:
    return locomotion(RUN_DY, RUN_S_A, RUN_FEET_S, RUN_FEET_E, RUN_NEAR_ARM, lean=RUN_LEAN)


def combat_frames() -> dict:
    """The combat animations (tools/art/combat.py), built on idle frame 0."""
    import combat
    return combat.combat(BODY0, ANCHORS0)


def legs_frames() -> dict:
    """(anim, direction, frame) -> legs codes, for every drawn pose."""
    out = {("idle", d, i): LEGS_IDLE[d] for d in ("s", "e", "n") for i in range(len(IDLE_WAVE))}
    for anim, (dys, s_a, feet, lean) in {"walk": (WALK_DY, WALK_S_A, WALK_FEET_E, 0),
                                          "run": (RUN_DY, RUN_S_A, RUN_FEET_E, RUN_LEAN)}.items():
        s_legs = [legs_s(r) for r in s_a] + [legs_s(mirror_s(r)) for r in s_a]
        for i, dy in enumerate(dys):
            out[(anim, "s", i)] = out[(anim, "n", i)] = s_legs[i]
            out[(anim, "e", i)] = legs_e(dy, lean, *feet[i])
    for anim, res in combat_frames().items():
        for (d, i), legs in res["legs"].items():
            out[(anim, d, i)] = legs
    return out


def arm_frames() -> dict:
    """(anim, direction, frame) -> (near arm codes, far arm codes, torso x offset, view)."""
    _, near, far, _ = idle()
    _, wnear, wfar, _ = walk()
    _, rnear, rfar, _ = run()
    out = {("idle", d, i): (near[(d, i)], far[(d, i)], 0, d) for (d, i) in near}
    out.update({("walk", d, i): (wnear[(d, i)], wfar[(d, i)], 0, d) for (d, i) in wnear})
    out.update({("run", d, i): (rnear[(d, i)], rfar[(d, i)], RUN_LEAN if d == "e" else 0, d)
                for (d, i) in rnear})
    for anim, res in combat_frames().items():
        for key in res["near"]:
            out[(anim, *key)] = (res["near"][key], res["far"][key], res["torso_dx"][key],
                                 res["view"][key])
    return out


def main() -> None:
    body, near, far, anchors = idle()
    wbody, wnear, wfar, wanchors = walk()
    rbody, rnear, rfar, ranchors = run()
    meta = {"material": "skin", "kind": "animated", "lags": False, "rigs": ["humanoid"]}
    combat = combat_frames()
    sheets = {key: {"idle": v0, "walk": v1, "run": v2} for key, v0, v1, v2 in
              (("body", body, wbody, rbody), ("near", near, wnear, rnear), ("far", far, wfar, rfar))}
    for anim, res in combat.items():
        for key in ("body", "near", "far"):
            sheets[key][anim] = res[key]
    write_part("body", "humanoid", {**meta, "notes": "Skin-only mannequin: bald head, bare "
                                                      "torso, legs. Arms are separate slots."},
               sheets["body"])
    write_part("arm_near", "humanoid", {**meta, "notes": "The near arm (the character's right; "
                                                          "viewer-left facing s). Holds held_near."},
               sheets["near"])
    write_part("arm_far", "humanoid", {**meta, "notes": "The far arm (the character's left; "
                                                         "viewer-right facing s). Holds held_far."},
               sheets["far"])
    write_anchors("humanoid", {"idle": anchors, "walk": wanchors, "run": ranchors,
                               **{anim: res["anchors"] for anim, res in combat.items()}})
    print("wrote the humanoid base body")


if __name__ == "__main__":
    main()
