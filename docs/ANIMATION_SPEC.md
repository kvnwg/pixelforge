# Animation Spec

Frame-by-frame specs for locomotion and the core reactions of the humanoid rig. Write the spec first when adding a new animation, then draw it.

- The full combat set (combat_idle, attacks, bow, cast, block, dodge, stun, victory), plus phases, events, hitboxes and telegraph timing, is in COMBAT.md.
- Monster rigs and their animations are in MONSTERS.md.
- Everything in section 1 (principles) applies to all of them.

The pixel offsets below are tested conventions for sprites this size and the right starting point, but the final judge is how it looks in the preview at 1x and 4x. If a change from the spec looks better, make it and update this file so the spec stays true.

---

## 1. Principles at this size

- **One pixel is a big move.** The whole character is 18 px tall, so a 1 px shift is over 5% of its height. Most motion here is 1 px. 2 px is a lot. 3 px is a lunge.
- **Move only what should move.** In every frame, decide which regions move and keep everything else pixel-identical. Unplanned 1 px shifts of the whole sprite read as jitter.
- **Whole pixels only.** No sub-pixel motion, no rotation, no scaling. A "rotated" pose (lying down, a swung sword) is redrawn by hand.
- **The feet sell the weight.** A planted foot never moves while it is planted. Sliding feet are the most visible animation bug.
- **Overlapping action.** Loose parts (hair locks, capes, the back hair in side views) trail the body by one frame. This one-frame lag is most of what makes tiny animations feel alive.
- **Hold the key poses longest.** Breathing idles hold the extremes; attacks hold the wind-up and follow-through, and flash the strike.
- **Readability over realism.** At 1x the player should instantly tell the facing direction and the action. If a frame doesn't read at 1x, simplify it.
- **Big moves are root motion.** Lunges, dodges and knockbacks beyond 1 to 2 px are exported as root motion for the game to apply, not drawn off-center in the frame.

## 2. Vocabulary

- **upper body:** head, torso, arms and everything attached to them (hair, headwear, torso wear, belt, held items at rest). In the anchor that's rows 10 to 24.
- **upper offset (dx, dy):** how far the upper body is translated relative to idle frame 0. Positive dy is down.
- **legs:** rows 25 to 27 in idle frame 0. Redrawn per frame rather than translated.
- **hair locks:** the parts of hair marked `lags: true`. In S these are the side locks around rows 16 and 17 (the `hair_locks` slot: x 11-12 and 18-19, rows 15 to 17); in E and N, the back of the hair (`hair_back`).
- **planted foot:** a foot touching the baseline (row 27) and carrying weight. It may not move.
- **lifted foot:** raised 1 px (bottom at row 26).

When the upper body moves down 1 px and the legs stay, the belt covers the top leg row, so the legs look 1 px shorter. That compression is intended and is how this style shows weight settling.

---

## 3. idle (loop, all directions)

Breathing with a hair lag. Feet never move.

| Frame | ms | Upper offset | Hair locks | Legs | Notes |
|---|---|---|---|---|---|
| 0 | 450 | (0, 0) | (0, 0) | base | the anchor pose in S |
| 1 | 150 | (0, +1) | (0, 0) | base | body settles, hair lags behind |
| 2 | 450 | (0, +1) | (0, +1) | base | hair catches up |
| 3 | 150 | (0, 0) | (0, +1) | base | body rises, hair lags |

- Hands move with the upper body.
- Eyes move with the head and stay open (blink is separate).
- N: identical motion; the back hair is the lagging part.
- S: the side hair framing the face (rows 15 to 17) lags as one clump. Eyes are drawn above the locks, so a lowered lock never hides an eye. In the frame where the body settles, a row of skin shows under the lifted locks; in the frame where it rises, the locks hang a row lower beside the eyes.
- E: identical motion; the back of the hair lags.

## 4. blink (1 frame, all directions with visible eyes)

- Idle frame 0 with each eye pixel replaced by skin shadow (#9f6f65, or the recolored skin shade 0).
- 100 ms. The game swaps it in at random intervals of 2.5 to 5 seconds. Exported as `blink_s`, `blink_e`, `blink_w`. N has no eyes, so no blink.

---

## 5. walk (loop, 4 frames, 130 ms each)

A cycle of two steps: contact, passing, contact (other foot), passing.

### walk S (toward camera)

| Frame | Upper offset | Legs | Arms |
|---|---|---|---|
| 0 contact A | (0, 0) | viewer-left foot planted on row 27, viewer-right foot back and lifted (row 26), exactly the anchor stance | viewer-right hand 1 px down (swinging forward), viewer-left hand 1 px up |
| 1 passing | (0, -1) | legs together under the body; viewer-left foot planted, viewer-right foot passing, lifted (row 26); legs extend 1 row to meet the raised body | both hands neutral |
| 2 contact B | (0, 0) | mirror of frame 0: viewer-right foot planted on row 27, viewer-left back and lifted | viewer-left hand 1 px down, viewer-right hand 1 px up |
| 3 passing | (0, -1) | legs together; viewer-right planted, viewer-left passing and lifted | both hands neutral |

- Hair locks lag one frame: they use the previous frame's upper offset.
- The body rises on passing frames and comes down on contact frames. This bob is 1 px, never more.
- Arm swing in S is subtle: a 1 px vertical shift of the hand, opposite to the forward leg. If it looks fidgety at 1x, remove it.

### walk N (away from camera)

Same timing and offsets as S, drawn from behind. Viewer-left is now the character's left. No face; the back hair lags.

### walk E (screen-right)

| Frame | Upper offset | Legs | Arms |
|---|---|---|---|
| 0 contact A | (0, 0) | legs apart: front foot 2 to 3 px ahead of the pivot, back foot 2 to 3 px behind, both on row 27 | near arm back (hand 1 px behind the torso), far arm forward (mostly hidden) |
| 1 passing | (0, -1) | legs together under the pivot; the back leg passing, foot lifted to row 26 | arms neutral at the sides |
| 2 contact B | (0, 0) | legs apart, swapped: the other leg in front | near arm forward, far arm back |
| 3 passing | (0, -1) | legs together; the other leg passing and lifted | arms neutral |

- Near and far legs must be distinguishable: the far leg uses the darker leather shades, the near leg the lighter ones. This prevents twinning.
- Back hair lags one frame (vertical only).
- The head never tilts or changes shape.

### walk W

Generated by mirroring walk E.

### How the humanoid walk was drawn (Phase 3b)

- **Facing e, planted feet travel with the ground.** The sprite stays on its pivot while the game moves it, so a planted foot moves back by exactly the ground's travel: front foot 3 px ahead of the pivot at contact, under the pivot at passing, 2 px behind at the next contact. Steps of 3 then 2 px give 10 px per cycle, the stride above, recorded per frame as `stride_px` in `style.json` (exported in `meta.pixelforge.stride_px`). At the walk's natural speed (10 px per 520 ms, about 19 px/s) the foot does not slide; W1 checks that each planted foot moves exactly that much.
- **Facing s and n, planted feet stay put** (stride 0), as in the tables above; the passing foot is lifted to row 26 and drawn dark like the anchor's set-back foot. Contact B mirrors contact A around x = 15, so the stance never shifts sideways.
- **Arms swing by reach, not by sliding:** the forward hand reaches 1 px lower (s, n) or 1 px further (e), the back hand pulls 1 px shorter, so sleeves never detach. Facing e, the far hand peeks 1 px past the torso in front or behind.
- **Legs:** 3 rows on contact frames, 4 on passing frames (the hip anchor rises with the body). Facing e the near leg is light leather and the far leg dark.

### Speed and foot sliding

Distance covered per cycle is about two strides (roughly 10 px in E/W). At 4 x 130 ms that matches about 19 px per second. Top-down RPGs usually move faster and tolerate some sliding, especially in S and N. If the game's movement speed is much faster, shorten frame durations (down to about 90 ms) rather than adding frames, and check it with the preview's movement test.

---

## 6. attack_slash (one shot, 5 frames)

Specced for E with a one-handed weapon in the near hand. Held items need drawn frames for this animation (never rotate a sprite). Phases, events, hitboxes and enemy timing for this attack are in COMBAT.md section 3.

| Frame | ms | Upper offset | Weapon | Legs | Notes |
|---|---|---|---|---|---|
| 0 anticipation | 120 | (-1, 0) | raised up and back behind the head | back foot planted, front foot planted | lean away from the target |
| 1 wind-up hold | 80 | (-1, +1) | 1 px further back | same | small squash, the coil before the strike |
| 2 strike | 60 | (+1, 0) | extended forward and down, plus a smear | front foot slides forward 1 px | event `hit` fires here |
| 3 follow-through | 140 | (+1, 0) | low and in front, past the target | same as frame 2 | no smear |
| 4 recover | 160 | (0, 0) | returning toward the idle hold | back to idle stance | |

**Smear (frame 2 only):** a 1 px wide arc tracing the weapon's path from high-back to low-front, 5 to 8 px long, in the weapon's lightest shade (or accent light for unarmed). It reads as speed. Never use white.

**S (attacking toward the camera):** lunge offset is (0, +1) instead of (+1, 0). As drawn (Phase 5) the weapon is raised beside the head on the weapon side (viewer-left) and chops down past the body on that side, with the smear running down it; a swing across the front would cover the body.

**N (attacking away):** lunge offset is (0, -1). As drawn, the s swing mirrored: up beside the head on the viewer-right, down past the body on that side. Across the front it would be hidden behind the body.

---

## 7. hurt (one shot, 3 frames)

| Frame | ms | Upper offset | Effects | Notes |
|---|---|---|---|---|
| 0 flash | 80 | knocked back 1 px away from the facing direction | flash: all fill pixels become #efe2c8, outline unchanged | the hit |
| 1 recoil | 120 | knockback 1 px plus (0, +1) squash | eyes closed (skin shadow), hair locks lag up (0, -1) | head height may drop 1 row here (flagged squash) |
| 2 recover | 140 | (0, 0) | eyes open | returns toward idle frame 0 |

Knockback direction: S is pushed up (0, -1), N down (0, +1), E left (-1, 0), W mirrored. Feet stay planted except that they may slide 1 px with the knockback.

---

## 8. death (one shot, holds the last frame)

| Frame | ms | Pose | Notes |
|---|---|---|---|
| 0 | 80 | hurt frame 0 (flash) | |
| 1 | 140 | buckle: upper (0, +1), knees bent, legs compressed 1 row | eyes closed |
| 2 | 140 | kneel: upper (0, +3), legs folded, hands close to the ground | |
| 3 | 160 | fall: a redrawn lying-down pose, about 16 to 18 px wide and 7 to 9 px tall, resting on the baseline, centered near the pivot | redraw, never rotate |
| 4 | 600 | lying still (hold) | shadow widens and flattens to match the body |

Optional despawn: 4 more frames of 100 ms using the dissolve effect (Bayer 4x4, removing 25%, 50%, 75%, 100%).

Directions: draw death for S and E (W mirrored). N reuses S frames 3 and 4 (the lying pose works from any facing) but frames 1 and 2 are drawn from behind.

**As drawn (Phase 5): death ends in a slumped kneel, not lying down.** Every part of a humanoid is drawn upright (hair, helmets, clothes follow the head and torso anchors), so a lying pose would mean redrawing every part on its side. Frames 3 and 4 kneel (torso down 2 px, legs folded, the head bowed 1 px into the collar facing s and e) with the weapon dropped on the ground in front. Each direction keeps its own view, n included. A lying pose can come later as its own drawn animation if a game needs it; most games add a fade or the dissolve effect.

---

## 9. How the combat set is built (Phase 5)

`tools/art/combat.py` builds every combat frame from a few choices instead of drawing it whole:

- **Head and torso offsets** from idle frame 0. The head may sit 1 px ahead of or behind the torso (a lean) and may sink into it by 1 px (a squash, a slump), never float above it. The body grid is split into head rows (to y 19), torso rows (y 20 to 24) and legs.
- **A stance** per direction: a legs grid drawn 4 rows tall (5 for airborne ones) so it fits any torso height; the lowered torso covers the top rows. Stances: `ready` (feet apart, the front foot 2 px ahead), `lunge` (front foot 1 px further), `crouch` (knees out), `kneel`, `tuck` and `swing` (airborne). Facing n the stance matches s on screen.
- **Arm poses** per direction and side (`ready`, `fwd`, `low`, `up_back`, `up`, `overhead`, `limp`, `tuck`, plus `guard`, `back` and `draw` for the far arm), a few pixels each, moved with the torso. Combat arm poses are 4-connected runs of one shade, so a reaching arm never breaks into single pixels. The forward arm reaches 4 px from the shoulder so a strike clears the body. Facing n the arm poses mirror s.
- **Held poses**: each frame names the pose its held items take (COMBAT.md section 3).

Lagging parts (hair locks, ponytails) trail by one frame but never by more than 1 px, so they drift behind a 3 px lunge instead of detaching. In grounded frames nothing but held items is drawn below the baseline: a robe or tabard pushed down by a deep crouch folds onto the ground row.

## 10. Later animations (not in v1)

Specs to write here before drawing: run (6 frames), jump (with shadow shrink), cast (staff raise and glow), interact or pick up, sit, emotes (a 1 to 2 frame bounce with a small icon above the head).

## 11. Review checklist for any animation

- Planted feet never move.
- Head height constant, except frames flagged squash.
- Only the planned regions change between frames (check the diff strip).
- Hair and loose parts lag by exactly one frame.
- Loops are seamless: last frame to first frame is checked like any other pair.
- At 1x the action is obvious, and it doesn't look like vibrating noise.
- Timing feels right in the preview at true speed (the human judges this; review images can't show timing).
