# Quality: Validation and Review

Two layers keep the output good:

1. **The validator** catches everything a rule can catch: wrong colors, broken outlines, stray pixels, drifting feet, jitter.
2. **Visual review** catches what rules can't: whether it's cute, readable and alive. Claude does this by rendering review images and actually looking at them; the human does it at checkpoints by watching the preview.

Neither replaces the other. Passing validation means "not broken", not "good".

---

## 1. Validator rules

Errors block a build and a commit. Warnings must be read and either fixed or explicitly accepted in the commit message.

### Errors

| ID | Rule |
|---|---|
| E1 | Every frame cell is exactly 32 x 32. |
| E2 | Every opaque pixel is in the allowed palette: the base ramps of the recipe's chosen presets, the outline color, and the flash color only in frames listed in `flash_frames`. |
| E3 | Alpha is only 0 or 255, except ground shadow pixels, which must be exactly the outline color at alpha 70. |
| E4 | Closed outline: no silhouette pixel has a transparent or shadow-only neighbor directly up, down, left or right, except at open-sole positions. |
| E5 | No floating pixels: every opaque pixel has at least one opaque neighbor among its 8 surrounding pixels. |
| E6 | Baseline: in grounded frames, the feet (the lowest pixels of the body, legs wear and boots layers, even where a robe covers them) are on row 27. Held items may hang lower. Frames flagged `airborne` or `lying` in the animation definition are exempt. |
| E7 | Pivot drift: in idle and walk, the horizontal center of the silhouette, without held items, stays within 1 px of x = 15 in S and N, and within 2 px in E and W. Frames flagged `displaced` (knockback, lunge) are exempt. |
| E8 | Bounds: no opaque pixel outside x 2..29, y 2..30. |
| E9 | Mirror: every `w` frame equals its `e` frame mirrored around x = 15. |
| E10 | Head height: the head region is the same number of rows in every frame of a character, except frames flagged `squash`. Measured from the outline row above the topmost head-layer pixel (body, hair, eyes, headwear) to the `chin` anchor. A rig whose body layer also holds raised arms names the layers to measure instead (`validator.head_slots`; the ogre uses its topknot). |
| E11 | At most 24 distinct colors per frame (`constraints.max_colors_per_frame`; 16 until the 2026-11-05 design pass). |
| E12 | Export integrity: JSON frame rects match the sheet, every duration is positive, tags cover all frames with no overlap, events point at valid frames. |
| E13 | Part material: every pixel in a part file is from that part's declared material base ramp or the outline color. |
| E14 | Completeness: every animated part in a recipe has a sheet for every animation the recipe lists. |
| E15 | Hitboxes: every active frame of an attack has at least one hitbox; no other frame has any; all boxes lie inside the canvas. Attacks whose hit is a `spawn` (bow, spells) are exempt from the first part: the projectile carries the hit. |
| E16 | Events: every attack has `windup`, `hit` (or `spawn` for ranged and spells) and `recover`; event frames exist; spawn and vfx points are inside the canvas and within 3 px of a hand anchor or held item tip, or are body points (head, torso, feet, ground, back) or the rig's `emitters` (a boss's core). |
| E17 | Telegraph: for enemy, elite and boss timing profiles, the time from the first windup frame to `hit` or `spawn` meets the profile minimum. |
| E18 | Size class: sprites use their size class's canvas, pivot, safe bounds and mirror axis. Checked as: every part's cells are its rig's canvas size and every anchor lies inside the class's safe bounds (canvas, pivot and mirror axis themselves come from the class, so E1, E6 and E9 hold them). |
| E19 | FX colors: FX art uses only `fx_ramps` within `fx_constraints`; character art never uses FX ramp colors (glow eye presets are the only exception). Checked by `pf fx build` (each FX against its own ramp; every character preset against every FX ramp). |
| E20 | Root motion: animations that declare root motion have one value per frame. |

### Warnings

| ID | Rule |
|---|---|
| W1 | Jitter: a region that the animation spec says is static (legs in idle, a planted foot in walk) changed between consecutive frames. Checked on each planted foot's bottom row (x - 1 to x + 1 around the `foot_*` anchor) in the lower-body layers, so a belt swinging in front of a foot is not jitter. A planted foot may move only by the animation's `stride_px` (the ground's travel in a side-view walk). |
| W2 | Change budget: more than 35% of silhouette pixels changed between consecutive frames of idle or walk, after undoing the planned motion (the upper body above the `hip` anchor moved by the head anchor's delta). Usually means boiling or a misaligned layer. A plain pixel count would flag the spec's own 1 px breathing, which moves about half the pixels. Pixels of lagging rigid parts (loose hair) are left out, since they move one frame late by design. |
| W3 | Singletons: more than 3 isolated pixels of a shade (no same-colored neighbor up, down, left or right) in one part of one frame, not counting eyes, pixels listed in a part's `allow_singletons`, or hurt-flash frames. Counted per part since the design pass: a pixel or two at the edge of each of several overlapping parts (a sword hanging across a pauldron's rim) is occlusion, not noise. |
| W4 | Silhouette area changed by more than 15% between consecutive frames of idle or walk. |
| W5 | A material uses a single shade over more than 22 connected pixels that are also more than half of that material's visible pixels (a flat, unshaded material). The doc first said 12 connected pixels, but the anchor's own hair light covers 22, and cloth has only two shades, so a big cluster alone is not a flat area. Frames flagged `flash` are skipped: they are one color on purpose. |
| W6 | Lag check: a part with `lags: true` moved in the same frame as the upper body instead of one frame later. |
| W7 | Roster distinctness: two different monsters' `combat_idle` frame 0 silhouettes overlap by more than 85% (intersection over union), facing s or e. Recolored variants of one monster (same rig and parts) and monsters of one recipe `family` (an elite and its base) are not compared. Sprites of different size classes are compared standing on the same pivot. |
| W8 | Weak tell: an attack's windup pose changes the silhouette by less than 8% compared with `combat_idle`. The strongest pose of the windup phase counts (a heavy attack lifts first, then cocks back). |
| W9 | Hidden tell: an FX played during the windup phase (a `vfx` or `spawn` event) covers more than 15% of the attacker's silhouette. A charge glow at the hand is fine; a burst over the body is not. |
| W10 | Busy big sprite: in medium, large and huge sprites, singletons exceed 0.5% of the silhouette area or the average shade cluster is under 3 px. As built (Phase 8): singletons are counted as for W3 (eyes and `allow_singletons` excepted) against the whole silhouette with its outline; clusters are 4-connected pixels of one material and color inside it. Thresholds `busy_singletons_share` and `busy_cluster_min_px` in `style.json`. A small sprite's few singletons are W3's business; on a 48 px sprite four stray pixels already read as noise. |
| W11 | FX timing (Phase 6): a one-shot FX has more than 8 frames, a frame outside 40 to 120 ms, or an empty frame before its last. COMBAT.md asks for 40 to 80 ms; death poofs and wisps linger up to 110 ms on purpose. |

Validator output must say which character, animation, direction, frame and pixel coordinates failed, and suggest the likely cause.

Thresholds live in `style.json` under `validator`.

---

## 2. Visual review protocol

After any change to art, run `pf review` and **open the images**. Never describe output as good without having viewed it in this session.

For each review, write down what you see before judging it:

1. **Turnaround** (`turnaround.png`): Do all four directions look like the same character? Same head size, same colors, same height?
2. **Versus anchor** (`vs_anchor.png`): Same outline weight, same palette feel, same head-to-body ratio, same eye treatment? Anything more detailed, saturated or contrasty than the anchor is wrong.
3. **Sheet** (`<anim>_<dir>_sheet.png`): Go frame by frame against the table in ANIMATION_SPEC.md. List the actual upper offset, leg state and hair lag you see in each frame and compare with the spec.
4. **Diff strip** (`<anim>_<dir>_diff.png`): This is how you see motion. Only the regions the spec says should move may light up. A whole-sprite outline of changed pixels means the entire character shifted (jitter). Check the last-to-first pair for loops.
5. **Onion skin** (`<anim>_<dir>_onion.png`): Are planted feet perfectly stacked? Does the bob read as one smooth arc?
6. **Silhouettes** (`<anim>_<dir>_silhouette.png`): With only the shape, can you tell the facing and the action? Do the legs read as two legs in side views?
7. **1x strip** (`<anim>_strip_1x.png`): At true size on beige, light and dark, does it read? Is the collar line still visible? Does anything look like noise?
8. **Exploded view** (`exploded_<dir>.png`), when parts are involved: Is each layer in the right z-order? Any gaps where a lower layer should show? Any part drawing its own outer outline (forbidden)?
9. **Combat timeline** (`<anim>_<dir>_timeline.png`, combat animations): Is the windup pose clearly different from combat_idle? Is the active phase 1 to 2 short frames with a smear or impact? Do the hitboxes cover the weapon or body part that's striking, and only on active frames? Do events sit on the right frames?
10. **Battle strip** (`battle_<a>_vs_<b>.png`): On the hit frame, does the defender visibly react? Do FX land where the weapon or projectile is? Does anything cover the tell?
10b. **FX** (`review/fx/<name>.png`, `fx_overview.png`): Does every frame read at 1x on beige, light and dark? Is it brighter than the cast without looking soft (no gradients, no alpha)? Does the pivot sit where the effect should touch the event point? Do the turned s and n versions still make sense?
11. **Roster lineup** (`roster_lineup.png`, monsters): Is every monster identifiable from its silhouette alone? Does size match danger? Does it sit comfortably next to the anchor at 1x?

Then score it with the rubric, list problems in priority order, fix the biggest one, re-render, and look again. Stop when every score is 4 or higher.

Claude cannot judge timing from still images. Timing and overall feel are judged by the human in the preview at checkpoints.

---

## 3. Rubric

Score each 1 to 5. A checkpoint needs 4 or higher on every line. Report the scores with one sentence of evidence each.

| # | Criterion | 5 looks like |
|---|---|---|
| 1 | Style match | Indistinguishable in style from the anchor: palette feel, outline, proportions, face |
| 2 | 1x readability | Facing and action obvious at true size on all three backgrounds |
| 3 | Silhouette | The solid silhouette alone reads clearly; no lumps or ambiguous shapes |
| 4 | Motion | Weight and follow-through feel right: the move travels through the body, timing eases, loose parts follow through (MOTION.md); no popping, sliding or jitter |
| 5 | Consistency | Same proportions and colors across all frames and directions |
| 6 | Cleanliness | No stray pixels, jaggies, banding, doubled outlines or noise |
| 7 | Part fit | Layers align in every frame; correct z-order; nothing peeking through |
| 8 | Appeal | Cute and charming; fits a cozy RPG; you'd want to play as it (or fight it) |
| 9 | Combat readability | Tell readable at 1x before the hit lands; hit moment unmistakable; FX never hide the tell; enemies distinct from allies (combat animations and monsters only) |

---

## 4. Common failure modes and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| Character "vibrates" in idle | whole sprite shifting 1 px, or legs moving | only the upper body and hair should move; check the diff strip |
| Feet slide in walk | planted foot changes x between frames | lock planted foot pixels; move the other leg only |
| Head looks smaller in E view | head redrawn narrower than 9 px or shorter than 10 rows | measure against the anchor; widen with back-of-head hair volume |
| Mushy, noisy look | too many singletons or shade changes | merge single pixels into neighboring clusters; fewer shades per area |
| Outline 2 px thick somewhere | a part drew its own outer outline | remove it from the part; the compositor outlines |
| Gap in outline at a part seam | hand-placed outline pixel missing or a part edge off by 1 | check the exploded view; align the part to the base body |
| Legs look like one blob in side view | both legs in the same shade | far leg darker leather shades, near leg lighter |
| Colors look harsher than the anchor | preset with too much chroma or contrast | run `pf palette --check`; pull chroma under 0.09 |
| Head merges into body at 1x | collar line lost under clothing | keep a skin shadow or cloth dark row under the chin |
| Hair snaps instead of swaying | hair moving with the body, not lagging | set `lags: true` on the part; check W6 |
| West facing jumps sideways on turn | mirrored around the canvas center | mirror around x = 15 (`x_new = 30 - x`) |
| Attack looks floaty | no hold on anticipation, smear too long | hold frame 0-1, keep the strike frame at 60 ms |
| Enemy attacks feel unfair | windup too short or too subtle | use the enemy timing profile; make the tell a whole-body pose (W8) |
| Hits don't feel impactful | no smear, no defender reaction, hit stop missing | smear on the active frame, defender flash on the hit tick, hit stop in the engine |
| FX look like a different game | FX using character ramps or soft gradients | FX ramps only, hard pixels, brighter than characters |
| Big monster looks like a different style | more detail instead of bigger clusters, or an upscaled sprite | redraw at native size with 3 to 6 px shade clusters; 1 px outline |
| Two monsters get confused | same silhouette, different colors | change the shape: signature feature, posture, size (W7) |
| Slime or ghost looks flat | translucency faked with alpha or not at all | lighter interior, gloss highlight, darker rim, inner shape |

---

## 5. Definition of done (any art task)

- `pf validate` passes with no errors; warnings fixed or explained.
- Review images rendered and viewed in this session; observations written down.
- Rubric scores all 4 or higher, reported with evidence.
- Tests pass.
- At a checkpoint: the human has approved in the preview.
- Committed with a clear message, and ROADMAP.md status updated.
