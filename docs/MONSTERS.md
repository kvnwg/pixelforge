# Monsters

Monsters follow every rule in STYLE_GUIDE.md: same 1 px plum outline with open soles, same palette constraints, same flat 2 to 4 tone shading, same light direction, same ground shadow treatment. What changes is the body plan, the size, and the materials. This doc defines rigs (body plans), size classes, monster materials, design rules, and the animation set for each new rig.

`style/examples/slime_draft.png` is a proof of concept drawn in this style (a draft, not canonical: replace it if you don't like it). `style/examples/slime_draft_vs_anchor_8x.png` shows it next to the anchor for scale.

---

## 1. Design principles

1. **Silhouette first.** Every monster must be identifiable from its solid silhouette at 1x. Design the shape before any color.
2. **One signature feature.** Horns, a single huge eye, wings, a gaping maw, a shell. Exactly one thing the player remembers. Extra details compete with it at this size.
3. **Chibi, but threatening.** The world is cozy, so monsters get the same big-head, rounded treatment as the cast. Menace comes from posture, glow eyes, 1 px fangs and claws, and timing, not gore or detail. No blood; damage reads through flashes, poofs and FX.
4. **1 px eyes by default.** Glow eye presets (red, yellow, ghost) are allowed for monsters and elites and are the one character element allowed past the normal chroma and lightness limits. They make threats read instantly, so don't give them to allies.
5. **Same light, same outline.** Top light, slightly from the viewer's right. Outline is generated, 1 px, never thicker on big monsters.
6. **Bigger, not busier.** Larger size classes get bigger shade clusters (3 to 6 px), not more detail. A 64 px monster should look like a 32 px monster that grew, not like a different art style.

---

## 2. Rigs

A rig is a body plan with its own base body, anchor points, slots, z-order, animation set and size class. Parts declare which rigs they fit (`rigs: [humanoid, humanoid_small]` in `part.yaml`). Recipes pick a rig.

| Rig | Size class | Examples | Body plan | Notes |
|---|---|---|---|---|
| `humanoid` | small | player characters, orcs, skeletons | defined by the anchor (18 rows, head 10) | skeleton = `body/skeleton` variant in bone material with glow eyes |
| `humanoid_small` | small | goblin, imp, kobold | 14 rows, head 8, legs 2 | shares humanoid animation specs; most humanoid parts need resized versions |
| `humanoid_large` | medium | ogre, troll, minotaur | about 28 rows, head 12 (43%) | heavier timing (enemy heavy) |
| `blob` | small | slime, ooze, mimic jelly | dome, 9 to 13 px wide | no limbs; all motion is squash and stretch, redrawn |
| `quadruped` | small (medium for bears) | wolf, boar, fox, rat | big head, short legs, tail | side view is the primary view |
| `flyer` | small | bat, crow, wisp | small body, large wings, hovers | pivot and shadow stay on the ground; body floats 7 px up |
| `boss` | large or huge | dragon, golem, demon | custom per boss | spec written here before drawing |

Later candidates: `serpent` (snakes, worms), `arachnid` (spiders, crabs), `floating` (eyes, ghosts, no wings).

---

## 3. Size classes

| Class | Canvas | Pivot | Mirror axis | Typical height |
|---|---|---|---|---|
| small | 32 x 32 | (15, 27) | x = 15 | up to about 22 px |
| medium | 48 x 48 | (23, 43) | x = 23 | up to about 36 px |
| large | 64 x 64 | (31, 59) | x = 31 | up to about 52 px |
| huge | 96 x 96 | (47, 91) | x = 47 | up to about 84 px |

Rule: pivot = (canvas / 2 - 1, canvas - 5). West mirrors use `x_new = 2 * axis - x`.

- Same pixel scale everywhere. Never upscale a small sprite to make a big one; that doubles the outline and breaks the style instantly.
- Ground shadow scales with the footprint: width = footprint width + 2 (odd), height = width / 3 rounded up, same color and alpha. As built (Phase 8): `effects.footprint_shadow` draws it centered half a row under the baseline with rows rounded off like a cubic superellipse; a 9 px footprint gives exactly the anchor's shadow, so the small class and the rule agree. A rig on a bigger class declares `footprint` in `style.json` (the ogre: 19, so 21 x 7); a shadow taller than the rows under the baseline allow is lifted to end on the class's safe row instead of being cut.
- Proportions relax as size grows: the head is about 55% of height for small creatures, 40 to 45% for medium, 30 to 40% for large and huge. Still rounder and cuter than "realistic".

---

## 4. Monster materials

All in `style/style.json` under `materials`, generated within the same constraints as the cast (L 0.30 to 0.80, C up to 0.09) except glow eyes. `style/monster_fx_swatches.png` shows every ramp next to the anchor's materials.

| Material | Shades | Presets |
|---|---|---|
| fur | 4 | gray, brown |
| scales | 4 | green, red |
| bone | 4 | ivory |
| chitin | 4 | dusk |
| slime | 4 | mint |
| slime_highlight | 1 | mint |
| hide | 3 | goblin |
| membrane | 2 | dusk |
| horn | 3 | pale |
| eyes (glow presets) | 1 | glow red, glow yellow, glow ghost |

Monster families are made by adding presets (frost wolf: fur in a pale blue-gray ramp; fire slime: slime in a muted ember ramp), always checked with `pf palette --check`.

**Translucency without alpha:** slimes and ghosts look translucent through value, not transparency: a lighter interior, a 1 to 2 px gloss in the highlight shade, a darker lower rim, and optionally a darker shape inside (a swallowed bone, a core). Alpha stays binary.

---

## 5. Rig specs and animations

Directions follow `combat.view` (COMBAT.md section 0): with `side`, combat animations are drawn in `e` only; locomotion follows the game's overworld needs. Timings below are base (player-profile) timings; enemy profiles scale hold frames automatically.

### 5.1 blob (slime)

Body: a dome 11 px wide at the base, 9 rows tall including a small top nub; eyes are 1 px, 3 px apart, in the lower half of the body (that's what makes it cute); gloss of 2 px in the upper right. Bottom outline is open (soles rule), so it sits into its shadow. See the draft.

Squash and stretch are redrawn, never scaled: a squash frame is 2 px wider and 1 to 2 rows shorter; a stretch frame is 2 px narrower and 1 to 2 rows taller. Eyes and gloss move with the body.

| Animation | Frames (ms) | Notes |
|---|---|---|
| idle (loop) | base 200, squash 150, base 200, stretch 150 | the jiggle |
| move (hop, loop) | squash 80, launch stretch 60, airborne 80, peak 80, falling stretch 60, land squash 100 | airborne frames rise 3 to 4 px with the shadow shrinking; root motion forward on frames 1 to 4 |
| attack_slam | deep squash 160 (hold), squash with narrowed eyes 160 (hold), leap stretch 60, slam 60 (`hit`, `vfx impact_big`), wobble 120, recover 160 | leap and slam use root motion toward the target |
| attack_spit (ranged) | swell 140 (hold), swell more 140 (hold), spit 60 (`spawn poison_glob` at the mouth point), recoil 120, recover 140 | |
| hurt | flash 80, splat squash 120, recover 140 | |
| death | flash 80, squash 140, melt into a 15 x 4 puddle 140, puddle 400, then dissolve 4 x 100 | |

### 5.2 quadruped (wolf)

Side view (`e`) is primary. Body about 18 to 20 px long and 13 to 14 px tall: head about 8 x 7 (big, chibi), body about 10 x 6, legs 3 px, tail 4 to 5 px. The near legs use lighter fur shades than the far legs so the legs never read as a blob.

| Animation | Frames (ms) | Notes |
|---|---|---|
| idle (loop) | 400, 150, 400, 150 | breathing (body +1 px, legs fixed); tail tip lags a frame; ear flick on frame 2 |
| walk (loop) | 4 x 120 | diagonal leg pairs move together; body bob 1 px, head bob lags a frame |
| run (loop) | 6 x 80 | gallop: gather (legs under, back arched 1 px up), extend (legs stretched, airborne frame), land front, land back |
| attack_bite | crouch 160 (hold), snarl 140 (hold), lunge 60 (`hit`), jaws closed 120, recover 160 | crouch: front down 1 px, rear up 1 px, ears back; snarl: 1 px mouth opening and glow eyes if enemy; lunge: body stretched, jaws open, root motion +4 |
| howl (buff) | head up 120, howl 300, howl 300 (hold), lower 150 | `vfx` sound rings at the mouth |
| hurt | flash 80, recoil 120, recover 140 | rear squashes 1 px |
| death | flash 80, legs buckle 140, fall onto side 160 (redrawn lying pose), hold 600 | or `poof_smoke` for despawning enemies |

For `topdown`: the S view is foreshortened (head over chest, front legs visible, body behind) and the N view shows rump and tail. Expect these to take extra review rounds; keep them simpler (fewer frames) than the side view.

### 5.3 flyer (bat)

Body about 7 x 6 px with 1 px ears; wings span up to 17 px. The pivot stays on the ground at (15, 27) so game logic sees the bat's ground position; the body floats with its bottom about 7 px above the baseline. The ground shadow stays on the ground, smaller (7 x 2) because the bat is airborne, and does not bob.

| Animation | Frames (ms) | Notes |
|---|---|---|
| hover (loop) | wings up 90, mid 90, down 90, mid 90 | body rises 1 px on the down-stroke, sinks 1 px on the up-stroke |
| attack_swoop | rise 140 (hold), hold with glow eyes 140 (hold), dive 60 (`hit`), contact 60 (active), pull up 140 | rise: body 2 px higher, wings wide; dive: body 4 px lower toward the target, wings swept back, root motion toward the target |
| hurt | flash 80, tumble 120 (wings crumpled), recover 140 | |
| death | flash 80, tumble 120, fall 100 (body 3 px lower), fall 100 (on the ground, shadow at full size), lie 400, dissolve | |

### 5.4 Humanoid monsters

- **Skeleton:** `humanoid` rig with `body/skeleton` (bone material, ribs suggested with 1 px cloth-dark gaps, glow eyes). Uses all humanoid animations. Death: `bone_crumble` FX instead of a lying pose.
- **Orc:** `humanoid` rig, skin preset `green (orc)`, a `tusks` part (2 x 1 px in horn material), heavier armor parts.
- **Goblin / imp / kobold:** `humanoid_small`. Ears or horns as headwear-like rigid parts. Same animation tables as humanoid; offsets stay 1 px.
- **Ogre / troll:** `humanoid_large`, medium canvas. Walk at 160 ms per frame; attacks use `attack_heavy`; add `roar` (3 frames, buff). Timing profile `elite` or `boss`.

As built (Phase 8):
- **Skeleton** (`tools/art/monsters_humanoid.py`): `body/skeleton`, `arm_near/skeleton` and `arm_far/skeleton` are the humanoid sheets converted to bone (skin shadow, mid, light to bone 1, 2, 3), with sockets, a nose hole and ribs carved from each frame's own anchors, then despeckled. Every humanoid animation comes for free; the recipe adds a sword, a shield, ghost-blue glow eyes and `death_crumble` (the humanoid death's first frames, then `bone_crumble`).
- **Orc:** the `green (orc)` skin preset, `tusks/orc` (two 1 px horn tusks at the jaw corners), plate, greaves, gauntlets, a mace and a horned helm (`headwear/horned_helm` plus `headwear_trim/horns`): the horns rise above any human head, which is what keeps the orc apart from the knight and the skeleton in the roster.
- **Goblin and goblin chief** (`tools/art/goblin.py`): their own 14-row `humanoid_small` body (an 8-row head, a 4-row pot-bellied body, 2-row legs) drawn per pose from a head, torso, legs, arms and a club; wide pointed ears (`ears/goblin`) are the signature. The humanoid's parts do not fit a body this size, so the goblin carries its own loincloth, club, eyes and crown. Its animations are its own short set (quick 110 ms steps, a club swing as `attack_slash`, a kneel-and-poof death).
- **Ogre** (`tools/art/ogre.py`): 48 x 48, pivot (23, 43), 28 rows to the soles plus a topknot. Heads, torsos and legs are hand-drawn grids (the s view a left half mirrored around x = 23, the n view the same silhouette shaded as a back); arms and the club are shaded tubes through three joints per pose, despeckled against what is actually visible. An arm in front of the body gets a 1 px outline-colored contour where it crosses the torso; a club behind the body stops 1 px short of it so the generated outline separates them. The club rests on the shoulder at idle and stays 13 to 16 px long in every pose (foreshortened facing s and n). `attack_heavy` (lift, lean back, squash, slam with a drawn smear, club on the ground with `impact_big`, stuck, heave) has a 628 ms tell on the `elite` profile; `roar` drops the jaw (tusks follow a `jaw` anchor) and raises both arms under `sound_rings`; death kneels, drops the club and slumps before `poof_smoke`.

### 5.5 Bosses

Each boss gets a written spec here before any drawing: concept in two sentences, signature feature, silhouette sketch as a character grid, size class, rig breakdown (which pieces animate separately, for example arms or a tail as separate layers so they can move independently), full animation list with frame tables, phases and telegraph times (boss profile: 500 ms minimum, 600+ for heavy attacks), and FX needs.

#### The Stone Warden (first boss, Phase 9)

Spec written before drawing (the human waived approval checkpoints on 2026-11-05; see ROADMAP.md).

**Concept.** An old guardian of mossy boulders held together by a glowing core: it lumbers, pounds the ground, hurls shards and wakes the stones around it. At half health its core and eyes burn red and it fights faster.

**Signature.** Floating stones: every boulder is parted from the next by a 1 px outline, so the pieces read (and move) separately around a glowing chest core; fists as big as its head resting on the ground; a crown of three stones.

**Silhouette** (facing s; one character is 4 x 4 px of the 64 px canvas):

```
................
................
.......###......
......#####.....
..##..#####..##.
.####.######.###
.###.########.##
.###.###@@###.##
..##.########.##
..##..######..##
.###..##..##..###
.###..##..##..###
.####.###.###.###
................
```

**Size class.** Large: 64 x 64, pivot (31, 59), mirror axis 31; about 51 rows from the crown to the soles and 51 px wide; a 23 px footprint, so a 25 x 9 shadow.

**Rig `golem`.** Layers, back to front: `arm_far` (shoulder, upper arm, forearm, fist), `body` (pelvis, legs, torso, head, crown), `arm_near` (the same four stones), then `moss` (hide material on the tops of stones), `core` and `eyes` (eyes material, glow presets: rigid, riding the `core` and `eyes` anchors). Arms are separate layers so they move independently of the body; every stone is a shaded rounded box drawn per frame, and any stone over another gets a 1 px outline-colored contour where they overlap, so pieces never merge. New material `stone`: 4 shades, presets granite, basalt, sandstone, frost. Points: `core` (spawns the ring of shards), `hand_near`, `fist_far`, `slam` (the ground between the fists), `foot_near`, `foot_far`, `head`, `torso`.

**Animations** (base ms; the `boss` profile scales hold frames x 2.2, so tells are the totals shown). Every attack has a whole-body tell.

| Animation | Frames (ms, phase) | What happens | Tell on `boss` |
|---|---|---|---|
| idle (loop) | 600, 200, 600, 200 | the body settles 1 px; the arms' stones follow a frame later | |
| combat_idle | alias of idle | | |
| walk (loop) | 220 x 4 | step, pass (body up 1), step, pass; `footstep` dust at the planted foot | |
| attack_slam (Rolling Knight's `slam`) | 160 windup, 200 hold, 120 hold, 60 active (`hit`), 80 active (`vfx impact_big`, `vfx shockwave` at `slam`), 280, 260 (`recover`) | fists rise, go overhead with the body stretched (the tell), lean back, slam down in front, rest on the ground, heave up | 864 ms |
| cast_ring (`ring`) | 160 windup, 200 hold (charge loop, `vfx gather_glow` ice at `core`), 140 hold, 80 active (`spawn rock_shard` at `core`, pattern ring, count 14), 200, 220 (`recover`) | arms spread wide, the core flares, arms pull back, a burst | 908 ms |
| attack_fan (`fan`) | 160 windup, 200 hold, 100 hold, 60 active (`spawn rock_shard` at `hand_near`, pattern fan, count 5, spread 0.22 rad), 160, 220 (`recover`) | the near fist draws back, crouch, punch forward | 820 ms |
| charge (`charge`) | 200 windup, 300 hold (`vfx dust_puff` at the back foot), 100 active (`hit`), 100 active, 200 (`vfx dust_puff`), 200 (`recover`); root motion 0, 0, 8, 8, 2, 0 | head down and crouch, a foot scrapes, the rush (frames 2 and 3 loop while the game's charge lasts: `loop_frames`), skid | 860 ms |
| summon (`summon`) | 160 windup, 260 hold (`vfx summon_circle` at `summon_point`), 100 (`summon`), 260 (`recover`) | both arms rise, the core flares, the arms sweep down and the stones wake | 732 ms |
| stomp (`rain`) | 160 windup, 300 hold, 60 (`vfx impact_big` and `vfx shockwave` at `foot_near`), 240, 200 (`recover`) | the near leg lifts high (the tell) and stomps; the game then drops rocks (`falling_rock`) | 820 ms |
| enrage (half health) | 160, 520 hold (`vfx sound_rings` at `head`, `vfx gather_glow` fire at `core`), 240 | rears back and roars with arms spread; the recipe `stone_warden_enraged` (red core and eyes) takes over | |
| hurt | 80 flash, 140, 180 | the stones jolt back and settle | |
| death | 80 flash, 200, 200, 280 (`vfx poof_smoke` at `torso`), 700 | cracks apart, head and arms drop, the torso falls, a rubble pile with the core dark | |

**Rolling Knight.** Its bosses pick three moves from ring, fan, charge, slam, summon and rain (ring always) with a 0.7 to 0.8 s wind, and enrage at half health (`src/world/ai.ts`, `mobgen.ts`): each move has its animation above, the wind is the windup phase, and `spawn` events carry `pattern`, `count` and `spread` for the game's projectiles.

**FX.** New: `shockwave` (48 px dust ring along the ground, below the characters), `rock_shard` (16 px spinning shard, rotates) and `rock_shard_impact` (24 px), `summon_circle` (48 px rune ring on the ground, loops, below), `falling_rock` (32 px rock that falls and shatters). Reused: `impact_big`, `dust_puff`, `gather_glow` (ice and fire tints), `sound_rings`, `poof_smoke`.

**As built (Phase 9).** `tools/art/stone_warden.py`; recipes `characters/monsters/stone_warden.yaml` and `stone_warden_enraged.yaml` (family `stone_warden`). Built to the spec, with these changes found while drawing: facing e the warden is laid out in three columns (far arm behind, a 16 px deep torso, the near arm hanging forward of the chest) because an arm over the chest turned the profile into a pile; raised arms there pass behind the head so the face stays seen; arms are lowered 3 px from the first sketch so raised fists stay inside the safe area; the stones' cracks are 4-connected staircases and moss is shaded by rows of the stone's box, so neither leaves single pixels. Rubric and review notes are in ROADMAP.md, Phase 9.

---

### 5.6 As built (Phase 7)

The slime, bat and wolf are drawn by `tools/art/slime.py`, `bat.py` and `wolf.py`; recipes are in `characters/monsters/` on the `enemy` timing profile.

- **Every rig keeps its own animation set** in `style.json` (`rigs.<rig>.animations`, over the global ones), with aliases: `combat_idle` is the idle loop for all three, the bat's `move` is its hover.
- **Directions: s, e and n for all three** (w mirrored), because Rolling Knight moves its mobs in every direction. The slime's body is the same from every side and only its eyes move (forward facing e, none facing n). The bat's body and wings are shared by s and e, with the eyes forward facing e and the furry back with the wings over it facing n. The wolf is drawn in profile first; facing s its head sits over the chest with the front legs below; facing n the rump, tail and hind legs show with the ears peeking over.
- **The slime** follows the kit's draft exactly (it matched the spec); its squash, stretch, deep squash, swell, melt and puddle shapes are redrawn with thicker dark lower rims than the draft, so the mid shade never covers half the body (W5) and it reads rounder. Eyes and gloss are separate parts on anchors. Dark eyes keep it cute; elites get glow eyes.
- **The bat** floats with its bottom 7 px above the baseline; its rig sets `hover` (every frame airborne unless flagged `grounded`) and a small shadow (7 x 2) that never bobs. It dies by tumbling and landing, wings flat, the shadow back to full size. Glow red eyes: it is always a threat.
- **The wolf** is assembled per frame from a torso, a head (rest, flick, ears back, snarl, bite, howl), four legs posed separately (stand, fwd, back, lift, tuck, kneel; far legs one shade darker and 2 px behind their near leg) and a tail that trails by a frame. A despeckle pass merges any lone shading pixel the assembly leaves (W3). Its death is a redrawn lying pose (the tail part is hidden there; the drawing has its own). Glow yellow eyes. The `howl` plays the new `sound_rings` FX.
- **Monster hitboxes are authored on the rig** (`"hitboxes"` in anchors.json on active frames: the slime's landing, the bat's dive, the wolf's jaws), clipped so the mirrored west box stays on the canvas.
- **Validator motion checks are off for these rigs** (`rigs.<rig>.validator.motion_checked_anims: []`): squash and stretch, wing beats and gaits reshape the silhouette by design, so W2, W4 and E7 would only flag the intended motion. Review the strips instead.

### 5.7 As built (Phase 8)

Recipes in `characters/monsters/`: `skeleton`, `orc`, `goblin`, `goblin_chief` (elite), `frost_wolf` (family variant), `ogre` (elite, medium). All validate with 0 errors and 0 warnings; `tests/test_humanoid_monsters.py` covers them, the medium size class (canvas, pivot, mirror, export, shadow scale), W10, drawn smears and W7 across sizes and families.

Rubric (skeleton / orc / goblin / goblin chief / frost wolf / ogre):
1. Style match 4 / 4 / 4 / 4 / 4 / 4: generated outline, open soles, the locked palette; the ogre keeps the 32 px pixel scale on its 48 px canvas.
2. 1x readability 4 / 4 / 4 / 4 / 4 / 4: each reads on beige, light and dark; the ogre's slam and smear read at 1x.
3. Silhouette 4 / 5 / 5 / 5 / 4 / 5: ribs and sockets; horns; ears; ears plus crown; the wolf's shape (a family); bulk, topknot and club.
4. Motion 4 / 4 / 4 / 4 / 4 / 4: the skeleton and orc inherit the humanoid set; the goblin and ogre are drawn per pose.
5. Consistency 4 / 4 / 4 / 4 / 5 / 4: one light and one pixel scale throughout.
6. Cleanliness 4 / 4 / 4 / 4 / 4 / 4: W3, W5 and (for the ogre) W10 clean after despeckle passes.
7. Part fit 4 / 4 / 4 / 4 / 5 / 4: horns, tusks, ears, crown, topknot and loincloth follow their anchors in every frame.
8. Appeal 4 / 4 / 5 / 5 / 4 / 4: chibi brutes with glow eyes; the goblins are the cutest.
9. Combat readability 4 / 4 / 4 / 4 / 4 / 5: whole-body tells at or over the profile minimum; the ogre's lean-back and lifted club are a 628 ms tell.

Elites differ from their base in grayscale: the goblin chief's bog hide is darker (68% of the shared pixels change by more than 8 gray levels) and its crown changes the silhouette; the frost wolf's fur is lighter (64%).

Known limits: the ogre's arms are tubes, simpler than its hand-drawn torso; its s and n swings land on the weapon side, as the humanoid's do, so the club stays visible.

---

## 6. Variants: elites and families

- **Family variant** (frost wolf, fire slime): new material presets plus matching FX element. Change value pattern, not just hue, so it reads differently in grayscale.
- A recipe names its family with `family: <name>` (the wolf and frost wolf are `wolf`; the goblin and goblin chief are `goblin`). W7 does not compare members of one family: an elite keeps its base's shape on purpose and is told apart by its added trait and value pattern instead.
- **Elite:** family colors plus one added trait (a helmet, a crown, a scar, bigger horns) and glow eyes. Uses the `elite` timing profile.
- **Champion:** elite plus a looping aura FX under the feet.

A variant that is only a hue shift is not enough; players need to tell a stronger enemy apart even when colors are hard to judge.

---

## 7. Roster readability

- `pf roster` renders `review/roster_lineup.png`: every monster and the player's anchor side by side at 1x and 2x, sorted by size, plus a row of solid silhouettes.
- The validator warns (W7) when two different monsters' `combat_idle` frame 0 silhouettes overlap by more than 85% (intersection over union), facing s or e. Fix it by changing the shape, not the color. Recolored variants of one monster (same rig and parts) and monsters of one recipe `family` are not compared. Sprites of different size classes are compared standing on the same pivot. `pf validate` (everything) and `pf roster` both run it.
- Size tells danger: within a region, bigger means stronger. Keep that consistent.

---

## 8. Build order

1. **Slime** (blob): validates squash and stretch, the hop, and open-sole outlines on a limbless body.
2. **Bat** (flyer): validates the floating body with a grounded pivot and shadow.
3. **Wolf** (quadruped): validates four legs, near and far leg separation, and the lunge.
4. **Skeleton** (humanoid body variant): validates swapping the base body.
5. **Goblin** (humanoid_small): validates part reuse across rigs.
6. **Ogre** (humanoid_large): validates the medium size class.
7. **First boss** (large): validates multi-part rigs and boss telegraphs.

Each new rig ends with a checkpoint (see ROADMAP.md).
