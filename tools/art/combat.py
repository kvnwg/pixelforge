"""Combat poses for the humanoid base body (COMBAT.md section 3, ANIMATION_SPEC.md sections 6-8).

A combat frame is built from four choices instead of being drawn whole:
  H, T    head and torso offsets from idle frame 0. The head may sit 1 px ahead of or behind the
          torso (a lean) and may sink into it (a squash), never float above it.
  stance  a legs grid per direction (feet, planted feet), drawn 4 rows tall so it fits any torso
          height: the lowered torso covers the top rows.
  arms    a near and a far arm pose per direction, a few pixels each, moved with the torso.
  held    the pose the held items take (a weapon raised, striking...), drawn per item.
The base body, its arms and every part derived from them (leggings, greaves, boots, gauntlets)
get a drawn frame from these; rigid parts (hair, clothes, helmets) follow the head and torso
anchors. Directions: s, e, n drawn (combat.view = topdown); w mirrors e.

Skin shades: 0 shadow, 1 mid, 2 light. Legs grids use leather shades and 'O' for a foot in shadow.
"""

from __future__ import annotations

import numpy as np

from artlib import g, grid

DIRS = ("s", "e", "n")
NECK = 20  # first torso row in idle frame 0 (the collar line)
HIP = 25  # first leg row in idle frame 0


def G(y0: int, rows: list[str]) -> np.ndarray:
    return g(rows, 8, y0)


# ============================================================================== stances
# Each stance: (legs grid, foot_near, foot_far, planted). Rows from y 24 down (airborne ones from
# y 21); the torso covers the top rows when it is at or below the height they were drawn for, so
# a stance fits a range of torso heights. Airborne stances list no planted feet.
def _stance(rows: list[str], near, far, planted=("foot_near", "foot_far"), y0: int = 24):
    return {"legs": G(y0, rows), "foot_near": list(near), "foot_far": list(far),
            "planted": list(planted)}


STANCES = {
    "e": {
        "idle": _stance([".....0021......", ".....0021......", ".....OO21......",
                         ".......222....."], (16, 27), (13, 26)),
        # ready: feet apart, the front foot 2 px ahead of the pivot, the back foot behind
        "ready": _stance([".....0022......", ".....0022......", "....00..22.....",
                          "...000..222...."], (17, 27), (12, 27)),
        # lunge: the front foot slides 1 px further forward (so only the back foot is planted)
        "lunge": _stance([".....0022......", ".....00.22.....", "....00...22....",
                          "...000...222..."], (18, 27), (12, 27), ("foot_far",)),
        # crouch: knees out front and back of a torso lowered 2 px, feet where ready has them
        "crouch": _stance([".....0022......", ".....0022......", "...00....22....",
                           "...000..222...."], (17, 27), (12, 27)),
        # kneel: the near knee on the ground in front, the far foot behind where it stood
        "kneel": _stance([".....0022......", ".....0022......", "...00.....22...",
                          "...000....22..."], (18, 27), (12, 27), ("foot_far",)),
        # tuck (airborne): knees up, feet off the ground; drawn 2 rows up
        "tuck": _stance([".....0022......", ".....0022......", ".....002222....",
                         ".....00..22....", ".....00..22...."], (17, 25), (13, 25), (), y0=21),
        # swing (airborne, vault): legs swung forward under the body
        "swing": _stance([".....0022......", ".....0022......", "......02222....",
                          ".......00222...", "..............."], (19, 24), (16, 24), (), y0=21),
    },
    "s": {
        "idle": _stance(["....211..11....", "....211..11....", "....220..OO....",
                         "....220........"], (13, 27), (17, 26)),
        "ready": _stance(["....2111112....", "....211.112....", "...220...022...",
                          "...220...022..."], (12, 27), (18, 27)),
        "crouch": _stance(["....2111112....", "....211.112....", "...22.....22...",
                           "...220...022..."], (12, 27), (18, 27)),
        "kneel": _stance(["....2111112....", "....2111112....", "....2111112....",
                          "....220.022...."], (13, 27), (17, 27), ()),  # on the knees
        "tuck": _stance(["....2111112....", "....2111112....", "....211.112....",
                         "....21...12....", ".....0...0....."], (13, 25), (17, 25), (), y0=21),
    },
}
# ready is drawn 4 rows tall, so a torso raised 1 px (a stretch) stands on the same feet
STANCES["e"]["tall"] = STANCES["e"]["ready"]
STANCES["s"]["tall"] = STANCES["s"]["ready"]
STANCES["s"]["lunge"] = STANCES["s"]["ready"]
STANCES["s"]["swing"] = STANCES["s"]["tuck"]
STANCES["n"] = STANCES["s"]  # facing n the stance matches s on screen


# ============================================================================== arms
# Arm poses as (x, y, shade) in idle frame 0 coordinates (they move with the torso), plus the
# hand anchor. 'O' marks a hand-placed outline pixel (the hip tuck under a hanging hand).
def _arm(points, hand):
    return {"points": list(points), "hand": list(hand)}


ARMS = {
    # Combat arm poses are 4-connected runs of one shade, so a raised or reaching arm never
    # breaks into single pixels (W3); the idle arms keep their two-tone drawing.
    ("e", "near"): {
        "rest": _arm([(15, 22, 2), (15, 23, 1)], (15, 23)),
        "ready": _arm([(16, 22, 2), (17, 22, 2)], (17, 22)),
        "fwd": _arm([(16, 21, 2), (17, 21, 2), (18, 21, 2), (19, 21, 2)], (19, 21)),  # full reach
        "low": _arm([(16, 22, 2), (16, 23, 2), (17, 23, 2), (17, 24, 2)], (17, 24)),
        "up_back": _arm([(14, 20, 2), (13, 20, 2), (13, 19, 2)], (13, 19)),
        "up": _arm([(16, 20, 2), (17, 20, 2), (17, 19, 2), (18, 19, 2)], (18, 19)),
        "overhead": _arm([], (14, 12)),  # behind the head: only the weapon shows above it
        "limp": _arm([(15, 22, 2), (15, 23, 2), (15, 24, 2)], (15, 24)),
        "tuck": _arm([(16, 21, 2), (16, 22, 2)], (16, 22)),
    },
    ("e", "far"): {  # behind the torso: only what reaches past it shows
        "rest": _arm([(13, 22, 1), (13, 23, 0)], (13, 23)),
        "fwd": _arm([(16, 22, 1), (17, 22, 1), (18, 22, 1)], (18, 22)),
        "guard": _arm([(16, 21, 1), (17, 21, 1), (18, 21, 1)], (18, 21)),
        "back": _arm([(12, 22, 1), (11, 22, 1), (11, 23, 1)], (11, 23)),
        "draw": _arm([(15, 21, 1), (15, 20, 1)], (15, 20)),
        "up": _arm([(14, 20, 1), (14, 19, 1)], (14, 19)),
        "limp": _arm([(13, 22, 1), (13, 23, 1), (13, 24, 1)], (13, 24)),
        "tuck": _arm([(15, 21, 1), (15, 22, 1)], (15, 22)),
    },
    ("s", "near"): {  # viewer-left, in shade
        "rest": _arm([(11, 22, 0), (11, 23, 1), (10, 24, "O")], (11, 23)),
        "ready": _arm([(11, 21, 1), (11, 22, 1)], (11, 22)),
        "fwd": _arm([(11, 22, 1), (12, 22, 1), (12, 23, 1)], (12, 23)),
        "low": _arm([(11, 22, 1), (11, 23, 1), (12, 23, 1), (12, 24, 1)], (12, 24)),
        "up_back": _arm([(10, 21, 1), (10, 20, 1)], (10, 20)),
        "up": _arm([(10, 21, 1), (10, 20, 1), (10, 19, 1)], (10, 19)),
        "overhead": _arm([(10, 21, 1), (10, 20, 1)], (10, 20)),
        "limp": _arm([(11, 22, 1), (11, 23, 1), (11, 24, 1)], (11, 24)),
        "tuck": _arm([(11, 22, 1), (12, 22, 1)], (12, 22)),
    },
    ("s", "far"): {  # viewer-right, lit, two columns like the idle arm
        "rest": _arm([(18, 21, 2), (19, 21, 2), (18, 22, 1), (19, 22, 2), (18, 23, 1),
                      (19, 23, 2), (20, 24, "O")], (19, 23)),
        "fwd": _arm([(18, 21, 2), (19, 21, 2), (18, 22, 1), (19, 22, 2)], (19, 22)),
        "guard": _arm([(18, 21, 2), (19, 21, 2), (17, 22, 2), (18, 22, 2)], (17, 22)),
        "back": _arm([(18, 21, 2), (19, 21, 2), (19, 22, 2), (20, 22, 2), (20, 23, 2)], (20, 23)),
        "draw": _arm([(18, 21, 2), (19, 21, 2), (17, 22, 2), (18, 22, 2)], (17, 22)),
        "up": _arm([(18, 21, 2), (19, 21, 2), (19, 20, 2), (20, 20, 2), (20, 19, 2)], (20, 19)),
        "limp": _arm([(18, 21, 2), (19, 21, 2), (18, 22, 1), (19, 22, 2), (18, 23, 1),
                      (19, 23, 2), (19, 24, 2)], (19, 24)),
        "tuck": _arm([(18, 21, 2), (19, 21, 2), (18, 22, 2), (19, 22, 2)], (18, 22)),
    },
}


def _mirror_arm(arm: dict, remap: dict) -> dict:
    pts = [(30 - x, y, remap.get(s, s)) for x, y, s in arm["points"]]
    return {"points": pts, "hand": [30 - arm["hand"][0], arm["hand"][1]]}


# Facing n the near arm is on the viewer's right and lit, the far arm on the left in shade: the
# s poses mirrored, so a swing reads the same from behind.
ARMS[("n", "near")] = {k: _mirror_arm(v, {0: 1, 1: 2}) for k, v in ARMS[("s", "near")].items()}
ARMS[("n", "far")] = {k: _mirror_arm(v, {2: 1, 1: 1}) for k, v in ARMS[("s", "far")].items()}
# rest stays exactly the idle drawing (the 2 px lit arm on the right, 1 px arm on the left)
ARMS[("n", "near")]["rest"] = ARMS[("s", "far")]["rest"]
ARMS[("n", "far")]["rest"] = ARMS[("s", "near")]["rest"]


def arm_grid(d: str, side: str, name: str, t: tuple[int, int]) -> tuple[np.ndarray, list[int]]:
    arm = ARMS[(d, side)][name]
    codes = np.full((32, 32), grid.CLEAR, np.int8)
    for x, y, s in arm["points"]:
        codes[y + t[1], x + t[0]] = grid.INK if s == "O" else s
    hx, hy = arm["hand"]
    return codes, [hx + t[0], hy + t[1]]


# ============================================================================== frame tables
# One entry per frame: H and T offsets, stance, arm poses, held poses. Directions differ only in
# offsets (forward is +x facing e, +y facing s, -y facing n), so each frame gives its offsets per
# direction; arms, stance and held poses are named once.
def F(e, s=None, n=None, *, legs="ready", near="ready", far="rest", held="ready", shield="rest",
      head=None, sdl=None, ndl=None, lift=0, planted=None):
    """e, s, n: torso offsets (x, y). head: extra head offset relative to the torso, per direction
    as a dict or one tuple for all. sdl / ndl: stance overrides for s and n. lift: raise the
    stance (airborne frames) by this many px."""
    s = s if s is not None else (0, e[1])
    n = n if n is not None else (0, e[1])
    head = head or {}
    if isinstance(head, tuple):
        head = {d: head for d in DIRS}
    return {"T": {"e": e, "s": s, "n": n}, "head": head, "legs": legs,
            "legs_dir": {"s": sdl, "n": ndl}, "near": near, "far": far,
            "held": held, "shield": shield, "lift": lift, "planted": planted}


FRAMES: dict[str, list[dict]] = {
    # ready stance, weapon up; the body bobs 1 px like idle, the hair lags. The spec's +1/+2 bob
    # would leave 1-row legs (a squat at 1x), so the wide stance and raised weapon carry "ready".
    "combat_idle": [
        F((0, 0)), F((0, 1)), F((0, 1)), F((0, 0)),
    ],
    # windup (lean back, coil), strike with a smear, follow-through, return
    "attack_slash": [
        F((-1, 0), (0, -1), (0, 1), near="up_back", far="fwd", held="raised"),
        F((-1, 1), (0, 0), (0, 1), near="up_back", far="fwd", held="raised"),
        F((1, 0), (0, 1), (0, -1), near="fwd", far="back", held="strike", legs="lunge",
          head={"e": (1, 0)}),
        F((1, 0), (0, 1), (0, -1), near="low", far="back", held="low", legs="lunge"),
        F((0, 0), near="ready", held="ready"),
    ],
    # overhead smash: lift, lean back (the tell), squash, slam, weapon down, heave back
    "attack_heavy": [
        F((0, -1), (0, -1), (0, -1), near="up", far="up", held="overhead", legs="tall"),
        F((-1, -1), (0, -1), (0, -1), near="overhead", far="up", held="back", legs="tall",
          head={"e": (-1, 0)}),
        F((-1, 1), (0, 1), (0, 1), near="overhead", far="up", held="back", legs="crouch"),
        F((1, 1), (0, 1), (0, 0), near="fwd", far="back", held="slam", legs="lunge"),
        F((1, 2), (0, 2), (0, 1), near="low", far="back", held="ground", legs="crouch"),
        F((1, 1), (0, 1), (0, 1), near="low", far="back", held="ground", legs="crouch"),
        F((0, 0), near="ready", held="ready"),
    ],
    # nock, draw, full draw (charge loop), release, recoil, lower
    "shoot_bow": [
        F((0, 0), near="fwd", far="fwd", held="aim"),
        F((0, 0), (0, -1), (0, 1), near="fwd", far="draw", held="draw"),
        F((0, 0), (0, -1), (0, 1), near="fwd", far="draw", held="draw", head={"e": (-1, 0)}),
        F((0, 0), near="fwd", far="fwd", held="release"),
        F((-1, 0), (0, -1), (0, 1), near="fwd", far="back", held="release"),
        F((0, 0), near="ready", held="ready"),
    ],
    # raise, gather (glow at the hand), channel (charge loop), release (thrust), hold, lower
    "cast": [
        F((0, -1), near="up", far="up", held="raised", legs="tall"),
        F((0, -1), near="up", far="up", held="raised", legs="tall"),
        F((-1, -1), (0, -1), (0, -1), near="up", far="up", held="raised", legs="tall",
          head={"e": (-1, 0)}),  # channel: leaning back into it
        F((1, 0), (0, 1), (0, -1), near="fwd", far="back", held="aim", legs="lunge"),
        F((1, 0), (0, 1), (0, -1), near="fwd", far="back", held="aim", legs="lunge"),
        F((0, 0), near="ready", held="ready"),
    ],
    # guard up: the far arm (shield) forward, the body turns slightly
    "block_enter": [
        F((0, 0), near="ready", far="fwd", held="guard", shield="guard"),
        F((-1, 0), (0, 0), (0, 0), near="ready", far="guard", held="guard", shield="guard",
          legs="lunge"),
    ],
    "block_hold": [
        F((-1, 0), (0, 0), (0, 0), near="ready", far="guard", held="guard", shield="guard",
          legs="lunge"),
        F((-1, 1), (0, 1), (0, 1), near="ready", far="guard", held="guard", shield="guard",
          legs="lunge"),
    ],
    "block_impact": [
        F((-2, 0), (0, -1), (0, 1), near="ready", far="guard", held="guard", shield="guard",
          legs="lunge"),
        F((-1, 0), (0, 0), (0, 0), near="ready", far="guard", held="guard", shield="guard",
          legs="lunge"),
    ],
    # crouch, hop (airborne, legs tucked), land squash, recover; root motion moves it back
    "dodge": [
        F((0, 1), legs="crouch", near="ready", held="ready"),
        F((0, -3), legs="tuck", near="tuck", far="tuck", held="tuck"),
        F((0, 1), legs="crouch", near="ready", held="ready"),
        F((0, 0), near="ready", held="ready"),
    ],
    # flash and knock back, recoil (squash, eyes closed), recover
    "hurt": [
        F((-1, 0), (0, -1), (0, 1), near="rest", far="back", held="ready"),
        F((-1, 1), (0, 0), (0, 1), near="rest", far="back", held="ready",
          head={"e": (0, 1), "s": (0, 1), "n": (0, 1)}),
        F((0, 0), near="ready", held="ready"),
    ],
    # sway side to side with eyes closed; the stars are an FX overlay
    "stun": [
        F((-1, 0), (-1, 0), (-1, 0), near="limp", far="limp", held="low"),
        F((0, 0), near="limp", far="limp", held="low"),
        F((1, 0), (1, 0), (1, 0), near="limp", far="limp", held="low"),
        F((0, 0), near="limp", far="limp", held="low"),
    ],
    # hit, buckle, kneel, slump forward, still: ends kneeling with the head down
    "death": [
        F((-1, 0), (0, -1), (0, 1), near="rest", far="back", held="ready"),
        F((0, 1), near="limp", far="limp", held="low", legs="crouch"),
        F((0, 2), near="limp", far="limp", held="ground", legs="kneel"),
        F((0, 2), near="limp", far="limp", held="dropped", legs="kneel",
          head={"e": (1, 1), "s": (0, 1)}),
        F((0, 2), near="limp", far="limp", held="dropped", legs="kneel",
          head={"e": (1, 1), "s": (0, 1)}),
    ],
    # squash, hop with the weapon raised high, land, proud stance
    "victory": [
        F((0, 1), legs="crouch", near="ready", held="ready"),
        F((0, -3), legs="tuck", near="up", far="up", held="high"),
        F((0, 1), legs="crouch", near="up", held="high"),
        F((0, 0), near="up", held="high"),
    ],
    # Rolling Knight's roll: a tucked crouch-dash forward (the game moves it by root motion)
    "roll": [
        F((1, 1), (0, 1), (0, 1), legs="crouch", near="tuck", far="tuck", held="tuck",
          head={"e": (1, 0)}),
        F((1, 3), (0, 3), (0, 3), legs="kneel", near="tuck", far="tuck", held="tuck",
          head={"e": (1, 0), "s": (0, 1), "n": (0, 1)}, planted=()),  # balled up, rolling
        F((1, 3), (0, 3), (0, 3), legs="kneel", near="tuck", far="tuck", held="tuck",
          head={"e": (1, 0), "s": (0, 1), "n": (0, 1)}, planted=()),
        F((1, 1), (0, 1), (0, 1), legs="crouch", near="tuck", far="tuck", held="tuck",
          head={"e": (1, 0)}),
        F((0, 0), near="ready", held="ready"),
    ],
    # backflip (Ranger): crouch, spring up and back (airborne), tucked peak, land, recover
    "backflip": [
        F((0, 1), legs="crouch", near="ready", held="ready"),
        F((-1, -3), (0, -3), (0, -3), legs="tuck", near="up", far="up", held="tuck",
          head={"e": (-1, 0)}),
        F((-1, -4), (0, -4), (0, -4), legs="tuck", near="tuck", far="tuck", held="tuck", lift=1),
        F((0, 1), legs="crouch", near="ready", held="ready"),
        F((0, 0), near="ready", held="ready"),
    ],
    # vault (Lancer): crouch, spring forward (airborne), legs swung forward at the peak, land
    "vault": [
        F((1, 1), (0, 1), (0, 1), legs="crouch", near="fwd", far="fwd", held="ready",
          head={"e": (1, 0)}),
        F((1, -3), (0, -3), (0, -3), legs="tuck", near="up", far="up", held="high"),
        F((1, -4), (0, -4), (0, -4), legs="swing", near="tuck", far="tuck", held="tuck", lift=1),
        F((0, 1), legs="crouch", near="ready", held="ready"),
    ],
}


# ============================================================================== building
def _bands(body: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    head = body.copy()
    head[NECK:] = grid.CLEAR
    torso = body.copy()
    torso[:NECK] = grid.CLEAR
    torso[HIP:] = grid.CLEAR
    return head, torso


def frame_parts(d: str, spec: dict, base_body: np.ndarray, base_anchors: dict) -> dict:
    """The body, legs, arms and anchors of one combat frame facing d."""
    tx, ty = spec["T"][d]
    hx, hy = spec["head"].get(d, (0, 0))
    hx, hy = tx + hx, ty + hy
    assert hy >= ty and abs(hx - tx) <= 1, (spec, d)  # the head never floats above the torso
    stance_name = spec["legs_dir"].get(d) or spec["legs"]
    stance = STANCES[d][stance_name]
    head, torso = _bands(base_body)
    lift = spec["lift"]
    legs = grid.translate(stance["legs"], 0, -lift)
    body = grid.overlay(grid.overlay(legs.copy(), grid.translate(torso, tx, ty)),
                        grid.translate(head, hx, hy))
    near, hand_near = arm_grid(d, "near", spec["near"], (tx, ty))
    far, hand_far = arm_grid(d, "far", spec["far"], (tx, ty))
    a = {}
    for name in ("head", "chin"):
        x, y = base_anchors[name]
        a[name] = [x + hx, y + hy]
    for name in ("torso", "back"):
        x, y = base_anchors[name]
        a[name] = [x + tx, y + ty]
    a["hip"] = [15 + tx, HIP + ty]
    a["hand_near"], a["hand_far"] = hand_near, hand_far
    a["foot_near"] = [stance["foot_near"][0], stance["foot_near"][1] - lift]
    a["foot_far"] = [stance["foot_far"][0], stance["foot_far"][1] - lift]
    a["planted"] = list(stance["planted"] if spec["planted"] is None else spec["planted"])
    front = {"e": (19, 21), "s": (15, 24), "n": (15, 19)}[d]
    a["shield_front"] = [front[0] + tx, front[1] + ty]  # where a guard is hit with no shield
    a["pose"] = {"held_near": spec["held"], "held_far": spec["shield"]}
    return {"body": body, "legs": legs, "near": near, "far": far, "anchors": a,
            "torso_dx": tx}


def combat(base_bodies: dict, base_anchors: dict) -> dict:
    """anim -> {"body": {(d, i): codes}, "near": ..., "far": ..., "legs": ..., "anchors":
    {d: [..]}, "torso_dx": {(d, i): int}}"""
    out = {}
    for anim, frames in FRAMES.items():
        res = {"body": {}, "near": {}, "far": {}, "legs": {}, "anchors": {}, "torso_dx": {}}
        for d in DIRS:
            res["anchors"][d] = []
            for i, spec in enumerate(frames):
                p = frame_parts(d, spec, base_bodies[d], base_anchors[d])
                for key in ("body", "near", "far", "legs", "torso_dx"):
                    res[key][(d, i)] = p[key]
                res["anchors"][d].append(p["anchors"])
        out[anim] = res
    return out
