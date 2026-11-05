# Animation Spec

Frame-by-frame specs for locomotion and the core reactions of the humanoid rig. Write the spec first when adding a new animation, then draw it.

- The full combat set (combat_idle, attacks, bow, cast, block, dodge, stun, victory), plus phases, events, hitboxes and telegraph timing, is in COMBAT.md.
- Monster rigs and their animations are in MONSTERS.md.
- Everything in section 1 (principles) applies to all of them, and MOTION.md says why: what good pixel animation does (with sources) and the eight motion rules every new or reworked animation follows.

The pixel offsets below are tested conventions for sprites this size and the right starting point, but the final judge is how it looks in the preview at 1x and 4x. If a change from the spec looks better, make it and update this file so the spec stays true.

---

## 1. Principles at this size

- **One pixel is a big move.** The whole character is 18 px tall, so a 1 px shift is over 5% of its height. Most motion here is 1 px. 2 px is a lot. 3 px is a lunge.
- **Move only what should move.** In every frame, decide which regions move and keep everything else pixel-identical. Unplanned 1 px shifts of the whole sprite read as jitter.
- **Whole pixels only.** No sub-pixel motion, no rotation, no scaling. A "rotated" pose (lying down, a swung sword) is redrawn by hand.
- **The feet sell the weight.** A planted foot never moves while it is planted. Sliding feet are the most visible animation bug.
- **Waves, not blocks.** A move travels through the body: chest, then head a frame later, then hands, then hair. Moving the whole upper body as one block reads mechanical (MOTION.md rule 1).
- **Overlapping action and follow-through.** Loose parts (hair locks, capes, the back hair in side views, tails) trail their anchor by a pixel while it moves, catch up when it stops, swing 1 px past it a frame later and settle (the compositor does this for every `lags: true` part; MOTION.md rule 5). This is most of what makes tiny animations feel alive.
- **Hold the key poses longest; fall faster than you rise.** Spacing can't go below a pixel, so easing is done with frame times: idles hold the top of the breath, sink quickly and rise slower; attacks hold the wind-up and follow-through, and flash the strike. A cycle with one flat duration reads mechanical.
- **Readability over realism.** At 1x the player should instantly tell the facing direction and the action. If a frame doesn't read at 1x, simplify it.
- **Big moves are root motion.** Lunges, dodges and knockbacks beyond 1 to 2 px are exported as root motion for the game to apply, not drawn off-center in the frame.

## 2. Vocabulary

- **upper body:** head, torso, arms and everything attached to them (hair, headwear, torso wear, belt, held items at rest). In the anchor that's rows 10 to 24.
- **upper offset (dx, dy):** how far the upper body is translated relative to idle frame 0. Positive dy is down. Where the head, torso and hands move separately (the idle's wave), each has its own offset; when the torso drops below the head, the neck stretches by a row (drawn, never a gap).
- **legs:** rows 25 to 27 in idle frame 0. Redrawn per frame rather than translated.
- **hair locks:** the parts of hair marked `lags: true`. In S these are the side locks around rows 16 and 17 (the `hair_locks` slot: x 11-12 and 18-19, rows 15 to 17); in E and N, the back of the hair (`hair_back`).
- **planted foot:** a foot touching the baseline (row 27) and carrying weight. It may not move.
- **lifted foot:** raised 1 px (bottom at row 26).

When the upper body moves down 1 px and the legs stay, the belt covers the top leg row, so the legs look 1 px shorter. That compression is intended and is how this style shows weight settling.

---

## 3. idle (loop, 6 frames, all directions)

A breath that travels through the body: the chest sinks, the head follows a frame later, the hands settle last; then the chest rises, the head, the hands. Feet and legs never move. Hair follows through.

| Frame | ms | Torso | Head | Hands | Hair locks | Notes |
|---|---|---|---|---|---|---|
| 0 | 360 | 0 | 0 | 0 | 0 | the anchor pose in S; the top of the breath, held |
| 1 | 100 | +1 | 0 | 0 | -1 | the chest sinks under a still head: the neck stretches a row; the hair swings 1 px up (past the head that just rose) |
| 2 | 100 | +1 | +1 | 0 | 0 | the head follows; the hair trails it |
| 3 | 260 | +1 | +1 | +1 | +1 | the hands settle: the bottom, held; the hair catches up |
| 4 | 140 | 0 | +1 | +1 | +2 | the chest rises (the head briefly overlaps the collar); the hair swings 1 px past |
| 5 | 140 | 0 | 0 | +1 | +1 | the head rises; the hair trails; the hands come up as the loop restarts |

- Timing: sinking frames are 100 ms, rising frames 140 ms, the top held longer than the bottom (gravity, MOTION.md rule 2); 1100 ms per breath.
- The neck stretch: the torso's top row fills the gap. Facing s and e that row is the collar's shadow; facing n it is the bare upper back, so the gap row takes the dark shade (the head's shadow on the nape).
- Eyes move with the head and stay open (blink is separate).
- S: the side hair framing the face (rows 15 to 17) is the following part. Eyes are drawn above the locks, so a lowered lock never hides an eye.
- E and N: the back of the hair follows.
- The hair column above is the compositor's follow-through (section 1), not drawn per frame: trail 1 px while the head moves, catch up when it stops, swing 1 px past a frame later, settle.

## 4. blink (1 frame, all directions with visible eyes)

- Idle frame 0 with each eye pixel replaced by skin shadow (#9f6f65, or the recolored skin shade 0).
- 100 ms. The game swaps it in at random intervals of 2.5 to 5 seconds. Exported as `blink_s`, `blink_e`, `blink_w`. N has no eyes, so no blink.

---

## 5. walk (loop, 8 frames)

Two steps of four keys each (Slynyrd's walk, MOTION.md): **contact** (the stride wide open, the arms at their extremes), **down** (the weight lands: the body drops 1 px, the back foot lifts), **pass** (the legs cross, the arms at rest), **up** (the body rises 1 px, the free foot reaches forward). Frames 4 to 7 repeat them with the other leg.

| Frame | Key | ms | Body dy | Near arm |
|---|---|---|---|---|
| 0 | contact A | 100 | 0 | back |
| 1 | down | 80 | +1 | back |
| 2 | pass | 90 | 0 | middle |
| 3 | up | 80 | -1 | forward |
| 4 | contact B | 100 | 0 | forward |
| 5 | down | 80 | +1 | forward |
| 6 | pass | 90 | 0 | middle |
| 7 | up | 80 | -1 | back |

- The bob is a triangle (MOTION.md rule 4): lowest on down, highest on up, 1 px either way, never more. Contact frames are held longest (100 ms) and the down and up frames are quick (80 ms): 700 ms per cycle.
- The near arm swings opposite the near leg, at its extremes on contact and through the rest pose as the legs cross; the far arm mirrors it. Arms swing by reach, never by sliding: a forward hand reaches 1 px further (e) or 1 px lower (s, n), a back hand pulls 1 px shorter, so sleeves never detach. Facing s and n, a forward reach on a down frame is taken up by the dip instead (the hand stays at its rest height), so hanging weapons never leave the canvas.
- Hair locks follow through (section 1).

### walk S (toward camera) and N (away)

- The viewer-left foot is planted on row 27 from contact A to up; the viewer-right leg lifts back (contact, heel up, drawn dark like the anchor's set-back foot), disappears under the hips as the body drops (down), passes in the dark shade (pass) and swings forward lifted 1 px in the mid shade (up), brightening as it comes forward. Frames 4 to 7 mirror 0 to 3 around x = 15, so the stance never shifts sideways.
- The planted leg keeps its foot rows from contact to up: the body sinks onto it (the down frame drops the thigh row) and rises off it (the up frame doubles the thigh row), so its sole never changes (W1).
- N: the same legs from behind; viewer-left is the character's left. No face; the back hair follows.

### walk E (screen-right)

Each foot is given by its heel pixel's x (the 3 px foot points ahead from it); a foot marked ^ is lifted 1 px.

| Frame | Near foot | Far foot | Planted |
|---|---|---|---|
| 0 contact A | 17 | 11 | both |
| 1 down | 15 | 11^ | near |
| 2 pass | 14 | 14^ | near |
| 3 up | 12 | 17^ | near |
| 4 contact B | 11 | 17 | both |
| 5 down | 11^ | 15 | far |
| 6 pass | 14^ | 14 | far |
| 7 up | 17^ | 12 | far |

- Near and far legs must be distinguishable: the far leg uses the darker leather shade, the near leg the lighter one (no twinning). Each leg is a 2 px strip from the hip to the foot row, then a 3 px foot pointing ahead.
- The head never tilts or changes shape.

### walk W

Generated by mirroring walk E.

### Speed and foot sliding

Facing e, a planted foot moves back by exactly the ground's travel: 2 px, then 1 px, alternating (`stride_px` [2, 1, 2, 1, 2, 1, 2, 1] in `style.json`, exported in `meta.pixelforge.stride_px`), 12 px per 700 ms cycle, about 17 px/s. At that speed the foot does not slide; W1 checks that each planted foot moves exactly that much. Facing s and n planted feet stay put. A game that moves faster should play the run (section 5b), not a sped-up walk; small differences can be taken up by shortening frame durations, never by adding frames. The preview's walk test shows both gaits at their natural speeds.

## 5b. run (loop, 8 frames)

The walk's keys with a flight: **contact**, **down** (the deepest frame), **push** (the back leg drives, the front knee lifts), **flight** (both feet leave the ground). The upper body leans 1 px into the facing (e and w; invisible in s and n) and the arms pump in long arcs.

| Frame | Key | ms | Body dy | Near arm | Near heel x (e) | Far heel x (e) |
|---|---|---|---|---|---|---|
| 0 | contact A | 70 | 0 | back | 18 | 10, 2 px up |
| 1 | down | 60 | +1 | back | 14 | 13, 2 px up |
| 2 | push | 70 | 0 | forward | 10 | 16, 1 px up |
| 3 | flight | 80 | -1 | forward | 11, 2 px up | 18, 1 px up |
| 4 | contact B | 70 | 0 | forward | 10, 2 px up | 18 |
| 5 | down | 60 | +1 | forward | 13, 2 px up | 14 |
| 6 | push | 70 | 0 | back | 16, 1 px up | 10 |
| 7 | flight | 80 | -1 | back | 18, 1 px up | 11, 2 px up |

- `stride_px` facing e is [4, 4, 4, 3, 4, 4, 4, 3]: 30 px per 560 ms, about 54 px/s, three times the walk and Rolling Knight's movement speed (GAMES.md). The flight frames are listed as `airborne_frames` [3, 7]: the shadow shrinks and the soles get their outline.
- Timing: the flight is held longest (80 ms) and the down frame is the quickest (60 ms), so the body hangs in the air and drops fast.
- Facing s and n the planted foot stays put; on the flight frame both feet lift (the planted one 1 px, showing its sole).
- The run is a cycle the player watches all game, so it gets 8 frames like the walk (MOTION.md rule 3).

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

Lagging parts (hair locks, ponytails) trail by one frame but never by more than 1 px, so they drift behind a 3 px lunge instead of detaching, and swing 1 px past the pose a frame after it stops (except on a once-through animation's held last frame, which stays put). In grounded frames nothing but held items is drawn below the baseline: a robe or tabard pushed down by a deep crouch folds onto the ground row.

## 10. Later animations (not in v1)

Specs to write here before drawing: jump (with shadow shrink), interact or pick up, sit, emotes (a 1 to 2 frame bounce with a small icon above the head). The run is section 5b; cast is in COMBAT.md.

## 11. Review checklist for any animation

- Planted feet never move.
- Head height constant, except frames flagged squash.
- Only the planned regions change between frames (check the diff strip).
- Hair and loose parts trail by one frame, never more than 1 px, and follow through (one overshoot pixel, then settle).
- Durations differ within the animation: extremes held, in-betweens quick, falls faster than rises.
- Loops are seamless: last frame to first frame is checked like any other pair.
- At 1x the action is obvious, and it doesn't look like vibrating noise.
- Timing feels right in the preview at true speed (the human judges this; review images can't show timing).
