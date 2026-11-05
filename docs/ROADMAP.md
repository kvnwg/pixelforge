# Roadmap

Build in this order. Each phase ends with acceptance criteria; phases marked **CHECKPOINT** end by showing the human the review images and preview, then waiting for approval. Do not start the next phase without it.

Keep the status line of each phase updated: `Status: not started | in progress | done (commit abc123)`.

Why this order: everything is built on the base body and its walk cycle. If those are mediocre, every character will be. So the early phases go slowly and get human approval; later phases go fast.

**Approval waived (2026-11-05):** after Phase 0 the human asked for every remaining phase to run without stopping for approval. Checkpoints still happen as self-reviews: the review images are rendered, looked at and scored with the rubric, fixed until every score is 4 or higher, and the checkpoint material is published for the human to look at later. The human can still send any phase back.

---

## Phase 0: Foundation

Status: done (commit c81464e)

Tasks:
1. `git init`, `.gitignore` (out/ except out/examples/, review/, caches, venvs), private GitHub repo named `pixelforge` via `gh repo create pixelforge --private --source=. --push` (if `gh` is missing or not logged in, stop and tell the human how to install and log in).
2. Python project: `pyproject.toml`, package `src/pixelforge`, `pf` CLI entry point via typer, dependencies Pillow, numpy, PyYAML, typer, pytest.
3. `style.py`: load and validate `style/style.json` (fail loudly on missing keys), including size classes, rigs, fx ramps and combat settings. Ask the human which combat view the game uses (`side` or `topdown`, see COMBAT.md section 0) and set `combat.view`.
4. `color.py`: hex, rgb, OKLCH conversion; ramp constraint checks.
5. `outline.py`: the algorithm in ARCHITECTURE.md section 10.
6. `pf palette --check` with swatch output.
7. Tests: outline reproduction on the anchor; palette constraints on every preset; style.json loads.

Acceptance:
- `pytest` green, including the exact outline reproduction test.
- `pf palette --check` passes for character, monster and FX ramps, and renders swatches.
- `combat.view` is set.
- Pushed to GitHub.

Notes: the GitHub repo `kvnwg/pixelforge` already existed, so the work was pushed to it with git instead of `gh repo create`. `combat.view` is `topdown`, chosen for Rolling Knight (COMBAT.md section 0, GAMES.md). Palette check rules: STYLE_GUIDE.md section 4.

Commit: `Phase 0: foundation, style loader, outline pass`

---

## Phase 1: Decompose the anchor (CHECKPOINT)

Status: done (commit 096c0f5)

Tasks:
1. Sheet I/O, part loading, recipe loading, compositor, recolor, shadow, validator (E1 to E14, W1 to W6), export, `pf review` with all review images.
2. Split the anchor into parts for `idle` frame 0, direction S only:
   - `body/humanoid`: skin-only mannequin (complete head shape under where the hair goes, torso, arms as `arm_near` and `arm_far`, legs)
   - `eyes/dots`, `hair_back/long_straight` (if any hair sits behind the body), `hair_front/long_straight`, `torso_wear/dress`, `belt/sash`, `legs_wear/leggings` (leather)
   - Each part single-material, no outer outline, hand-placed outline pixels where the anchor has them.
3. `characters/anchor_girl.yaml`.

Acceptance:
- `pf build anchor_girl` produces `idle_s` frame 0 identical to `style/anchor_with_shadow.png` (pixel diff 0). This is a test.
- Recoloring `anchor_girl` with the eight combinations from `style/recolor_test_6x.png` matches that image's look, and eyes and legs recolor independently of cloth and hair.
- Validator passes.

**CHECKPOINT:** show the exploded view, the rebuilt anchor, and a recolor grid. Explain how the hidden parts (head under hair, body under dress) were drawn.

Commit: `Phase 1: anchor decomposed into parts, pixel-exact rebuild`

---

## Phase 2: Turnaround (CHECKPOINT)

Status: done (commit 5097766)

Tasks:
1. Draw the base body and every anchor_girl part for E and N, idle frame 0. W comes from mirroring.
2. Follow STYLE_GUIDE.md section 10 for side and back views.
3. Anchor points for idle frame 0 in all directions.

Acceptance:
- `turnaround.png` shows the same character from four sides: same head height (10 rows), same total height, same colors.
- Validator passes; mirror test passes.

**CHECKPOINT:** show `turnaround.png` at 8x and the 1x strip. The human approves the side and back designs before anything is animated. Expect a few rounds here; this is where the character's 3D shape gets decided.

Commit: `Phase 2: four-direction turnaround`

---

## Phase 3a: Idle (CHECKPOINT)

Status: done (commit a13814a)

Tasks:
1. Base body and all parts for idle frames 0 to 3, all directions, per ANIMATION_SPEC.md section 3.
2. Blink frames.
3. Preview tool (`tools/preview`) with the features in ARCHITECTURE.md section 16.

Acceptance:
- Diff strips show only upper body and hair changing; legs identical in all frames.
- Hair lag verified (W6 clean).

**CHECKPOINT:** the human watches the idle in the preview at 1x and 4x, all directions.

Commit: `Phase 3a: idle and blink`

---

## Phase 3b: Walk (CHECKPOINT)

Status: done (commit 4d102c8)

Tasks:
1. Base body and all parts for walk frames 0 to 3, all directions, per ANIMATION_SPEC.md section 5.
2. Movement test in the preview.

Acceptance:
- Planted feet identical across frames where planted (W1 clean).
- Near and far legs distinguishable in E.
- Loop seam (frame 3 to frame 0) as clean as the other transitions.

**CHECKPOINT:** the human watches walk at true speed in all four directions and in the movement test. This is the most important approval in the project.

Commit: `Phase 3b: walk cycle`

---

## Phase 4: Parts library, recoloring, knight (CHECKPOINT)

Status: done (commit 43c2c10)

Tasks:
1. `pf template` for drawing parts against the base body.
2. Add parts (each with idle, walk and blink frames in all directions):
   - hair_front / hair_back: long_straight (done), short, ponytail, bun, none (bald)
   - torso_wear: dress (done), tunic, robe, plate
   - over_torso: tabard
   - legs_wear: leggings (done), greaves
   - feet: boots
   - hands: gauntlets
   - headwear: none, hood, great_helm
   - held_near: none, sword, staff, bow
   - held_far: none, shield
3. The knight (brief below).
4. `parts/compat.yaml` and `pf random`.
5. Gallery mode in the preview.

Rolling Knight also needs its six class looks (plumed sallet, mitre, wizard hat, winged helm, mace, lance; GAMES.md). Done in this phase: `characters/rolling_knight/rk_*.yaml`.

Notes from building it:
- Greaves, boots and gauntlets are derived from every leg and arm frame of the base body (`tools/art/parts_library.py`), so they fit every pose. Gauntlets cover the whole visible arm: a knight in plate with bare forearms read wrong.
- The sword's blade is 4 px plus a 3 px crossguard and a grip pixel, not the brief's 6 to 7: the near hand bobs 1 px down in idle and walk, and the tip's outline has to stay inside the safe area (y 30).
- Trim slots `headwear_trim`, `belt_trim` and `held_near_trim` carry the second material of an item (plume, buckle, hilt, orb, spearhead).

Acceptance:
- Knight builds, validates, and reads as a knight at 1x.
- `pf random --seed 1 --count 12` produces 12 valid, on-style characters with no layering mistakes.

**CHECKPOINT:** show the knight's turnaround and walk, plus the gallery of 12 random characters.

Commit: `Phase 4: parts library, randomizer, knight`

### Knight brief

- **Helmet (`headwear/great_helm`, metal, rigid):** a rounded great helm covering the whole head; adds at most 1 row of height. Eye slit: a horizontal line in outline color across the eye row (row 18 in S), 5 to 7 px wide, replacing the eyes. Light metal shade across the top (it catches the light), dark shade on the viewer-left side. Hides `hair_front`, `hair_back` and `eyes`. Optional 1 to 2 px plume on top in accent or crimson cloth (a separate part, `headwear_trim`), only if it reads at 1x.
- **Body (`torso_wear/plate`, metal):** plate over the torso and shoulders. In S the shoulders get 1 px pauldron bumps that keep the total width at 11 px.
- **Tabard (`over_torso/tabard`, cloth crimson):** a front panel 3 to 5 px wide from collar to hip, so the knight isn't a gray blob. In N it's a back panel. In E it's a narrow strip at the front edge.
- **Belt (`belt/leather_belt`, leather):** 1 row at the waist, a 1 px accent buckle in S.
- **Legs (`legs_wear/greaves`, metal) and boots (`feet/boots`, leather dark).**
- **Hands (`hands/gauntlets`, metal):** the hand pixels in metal shades.
- **Sword (`held_near/sword`, metal + separate hilt part in accent):** at rest held low in the near hand, blade pointing down. Blade 1 px wide, 6 to 7 px long, light metal with a mid shade on the shadow side. Crossguard 3 px wide in accent. In N the sword is mostly hidden behind the body.
- **Colors:** metal steel, cloth crimson, leather dark, accent gold (anchor).
- **Silhouette test:** at 1x the knight should read as "armored" from the helmet's rounder top and the sword alone. If it reads as a gray blob, increase tabard size before adding detail.

---

## Phase 5: Humanoid combat (CHECKPOINT)

Status: done (commit cd0f89d)

Tasks:
1. Read COMBAT.md fully. Add any missing detail to it before drawing.
2. Combat data pipeline: phases, events, hitboxes (rig and held item), auto hurtboxes, root motion, timing profiles, export in `meta.pixelforge`, validator rules E15 to E20 and W8 to W9.
3. Review tooling: `pf review --combat` timelines, `pf battle`, and a target dummy plus hit stop in the preview.
4. Animations for the base body and all humanoid parts, in the directions `combat.view` requires: `combat_idle`, `attack_slash`, `attack_heavy`, `shoot_bow`, `cast`, `block_enter`, `block_hold`, `block_impact`, `dodge`, `hurt`, `stun`, `death`, `victory`. Held items get drawn frames for every attack.
5. Placeholder FX (single-frame smear and spark) so battle strips are meaningful before Phase 6.

Rolling Knight's dodges are a roll, a backflip and a vault in any direction, drawn rather than rotated (GAMES.md). Spec them in COMBAT.md alongside `dodge` before drawing.

Acceptance:
- Validator passes, including telegraph checks on an enemy-profile build of the knight.
- The knight's slash and heavy attack read clearly at 1x; strike frames have smears; hitboxes cover the weapon on active frames only.

**CHECKPOINT:** the human watches the knight and anchor_girl fight the target dummy in the preview, with both the player and enemy timing profiles.

Commit: `Phase 5: humanoid combat set and combat data`

### Phase 5 notes and self-review (checkpoint waived, see the top of this file)

What was built:
- All 16 combat animations (the 13 listed plus Rolling Knight's `roll`, `backflip` and `vault`, specced in COMBAT.md section 3) in s, e and n for the base body and every humanoid part, built from head and torso offsets, stances and arm poses (ANIMATION_SPEC.md section 9).
- Weapon poses for the sword and hilt, mace, staff and orb, lance and spearhead, bow, and the shield's guard; strike smears; the unarmed `fist` default; hitboxes and named points per pose.
- Combat data: phases, events with resolved points, hitboxes, hurtboxes, root motion, timing profiles (retimed at build time, exported with holds and base durations). Validator E15 to E18, E20 and W8 (E19 and W9 need FX: Phase 6).
- `pf review --combat` timelines, `pf battle`, and the preview's Arena view with a training dummy, hit stop and a timing profile toggle. Placeholder spark and projectiles until Phase 6.
- `knight_enemy` (enemy profile: slash tell 340 ms, heavy 480 ms, both over the 300 ms minimum).
- Rolling Knight classes list the combat animations their kit uses (GAMES.md).

Acceptance: `pf validate` passes all 41 parts and 21 recipes with 0 errors and 0 warnings, including the enemy-profile knight's telegraph checks; the knight's slash and heavy read at 1x on all three backgrounds, strike frames have smears, and hitboxes cover the weapon and smear on active frames only (tests/test_combat.py checks this).

What the review images show (knight, anchor_girl; strips at 1x and 2x, timelines, battle strips, arena screenshots):
- Slash facing e: frame 0 leans back with the sword cocked behind the helm (only the blade sticking out behind shows), frame 1 coils 1 px lower, frame 2 lunges with the arm fully reached and the blade down-forward under a light arc smear, frame 3 follows through low, frame 4 returns to ready. Facing s and n the sword rises beside the head on the weapon side and chops down past the body with the smear running down that side.
- Heavy: lift (sword up in front of the face), the tell (cocked far back behind the head, body leaning back), squash, slam with a vertical smear, sword flat on the ground in front (the `impact_big` point), heave back.
- Unarmed (anchor_girl): the same body motion; the punch reaches 4 px and bursts in an accent crescent. At 1x the burst is subtle on beige; the body lean and reach carry the read, and the arena's hit stop, flash and spark make the hit unmistakable.
- Reactions: hurt flashes cream and recoils; stun sways with limp arms; death buckles to a slumped kneel with the weapon dropped in front; victory hops with the weapon high. Dodge, backflip and vault leave the ground with tucked legs and a smaller shadow; the roll balls up low.
- Battle strip knight vs anchor_girl: the defender flashes on the hit frame and recoils after; the spark sits where the blade meets her.

Rubric (knight / anchor_girl):
1. Style match 4 / 4: same parts, palette and auto outline; weapons are 1 px lines in their own shades; smears use the weapon's lightest shade (or accent light), nothing brighter.
2. 1x readability 4 / 4: windup and strike shapes are obvious on beige, light and dark; the girl's punch reads from the reach and lean more than the burst.
3. Silhouette 4 / 4: the cocked weapon and the reach change the outline clearly; the solid silhouettes show lean back, lunge and crouch.
4. Motion 4 / 4: planted feet hold (W1 clean), the hair trails at most 1 px, holds before the strike and long recovery frames give weight. Timing is for the human to judge in the arena.
5. Consistency 4 / 4: head height constant (E10), same proportions in every direction; west mirrors east exactly.
6. Cleanliness 4 / 4: no isolated pixels or flat areas (W3, W5 clean); blades are drawn in pixel pairs.
7. Part fit 4 / 4: rigid parts follow the head and torso, the shield rides the torso, clothes never dip below the ground, weapons never leave the canvas (checked for every frame that uses each pose).
8. Appeal 4 / 4: the knight's slash and slam feel punchy; the girl's victory hop and kneel read cute.
9. Combat readability 4 / 4: tells are whole-body (W8 clean) and visible for the full windup; the hit has a smear, and in the arena hit stop, flash and spark; the enemy knight's tells are longer and its glowing eyes mark it as a foe.

Known limits, recorded in the docs: death ends kneeling rather than lying down (ANIMATION_SPEC.md section 8); the roll is a crouch-dash, not a somersault; facing n the strike is mostly the body motion and the side smear; smears and sparks are placeholders until Phase 6.

---

## Phase 6: FX library (CHECKPOINT)

Status: done (commit 57251de)

Tasks:
1. FX pipeline: `fx/<name>/fx.yaml`, sheets, `pf fx build`, `pf fx review`, validation against `fx_ramps`, 90-degree rotation support.
2. The v1 set in COMBAT.md section 6: smears, impacts (neutral and per element), projectiles (travel and impact), gather glow, status overlays, death poofs, support effects.
3. Wire events to FX in the preview so `spawn` and `vfx` play the real effects.

Acceptance:
- Every FX validates; all read at 1x on beige, light and dark backgrounds.
- Battle strips for slash, heavy, bow and each spell element look like one game.

**CHECKPOINT:** the human watches every attack with its real FX in the preview.

Commit: `Phase 6: FX library v1`

### Phase 6 notes and self-review (checkpoint waived, see the top of this file)

What was built:
- `src/pixelforge/fx.py`: `fx.yaml` loading, validation (E19, E3, E8 margins, W11 timing), tints, exact 90-degree rotation and mirroring, export to `out/fx/` with every direction and an index; `pf fx build`, `pf fx review`.
- `tools/art/fx_art.py`: the v1 set from COMBAT.md section 6, 29 folders exporting 38 FX (six elemental impacts and five gather glows are tints of one drawing each), plus `dust_puff` for the roll.
- Events name their FX (`hit` names `spark_small`); E16 checks that every event and overlay FX exists; W9 (hidden tell) is live.
- `pf battle` plays the real FX (with `--element` for casts); the preview's Arena plays them with an element picker; a new FX view plays the whole library; the player view draws the stun stars and `vfx` events. Character exports now carry per-frame points and overlays so a game can attach FX.

Acceptance: every FX validates with 0 errors and 0 warnings; `tests/test_fx.py` checks that every frame of every FX stands out on beige, light and dark ground (shadow FX on beige and light); battle strips for slash, heavy, bow and each spell element (fire, ice, poison, arcane, holy) were rendered and compared.

What the review images show (fx_overview, per-FX sheets, battle strips, arena screenshots):
- The fireball matches the kit's draft (bright head, flickering tail); ice shards glint, the poison glob wobbles with drips, the arcane orb carries an orbiting mote; each lands in its element's burst.
- Hits: a crisp 9 px spark on the target; the heavy slam adds a 17 px star, a breaking ring and dust running along the ground.
- The first drafts in the cream impact ramp and the pale holy ramp vanished on beige or light ground; giving every FX light cores and dark tips fixed that across the library. `impact_shadow` stays dim on dark ground by nature.
- Battle strips: the arcanist's charge motes gather at the hand, the projectile crosses, the knight flashes under the burst; the ranger's arrow leaves the nock and sparks on impact. Every element follows the same beats at the same pixel scale.

Rubric (FX):
1. Style match 4: hard pixels, binary alpha, no outlines, the kit's ramps; brighter than the cast as intended.
2. 1x readability 4: checked by test on all three grounds; the 1x rows of the battle strips show every hit.
3. Silhouette 4: stars, rings, crescents and projectiles each have a distinct shape.
4. Motion 4: bursts expand and thin over 4 to 6 frames, loops cycle cleanly (glows converge, stars orbit); timing is for the human to judge in the arena.
5. Consistency 4: one burst shape for all elements, one pixel scale, the same beats in every battle strip.
6. Cleanliness 4: lines in pixel pairs, no soft edges; poison glob redrawn by hand after the first pass came out blocky.
7. Part fit 4: pivots land on event points: sparks where the strike meets the target, impacts on the ground point, glows on the hand, overlays on the head.
8. Appeal 4: the fireball and the stun stars carry the cozy look; the poof is soft and round.
9. Combat readability 4: no FX covers a tell (W9 clean); the hit moment always has an impact.

Known limits: elemental impacts share one shape (elements differ by color and projectile); holy has no projectile; shadow FX are dim on dark ground.

---

## Phase 7: Monster rigs I: blob, flyer, quadruped (CHECKPOINT per rig)

Status: done (commits "Phase 7: slime", "Phase 7: bat", "Phase 7: wolf"; see the notes below)

Tasks (one rig at a time, in this order, following MONSTERS.md sections 5.1 to 5.3):
1. **Slime:** blob base body, all its animations, `characters/monsters/slime.yaml` with the enemy profile. Start from `style/examples/slime_draft.png` only if the human liked it.
2. **Bat:** flyer rig with the grounded pivot and shadow.
3. **Wolf:** quadruped rig, near and far legs separated by shade.
4. `pf roster` and W7.

Acceptance per monster:
- Validator passes with the enemy timing profile.
- Battle strips against the knight read clearly.
- Silhouette identifiable at 1x in the roster lineup.

**CHECKPOINT** after each monster: turnaround (or side view), every animation in the preview, battle strip vs the knight.

Commit per monster: `Phase 7: slime`, `Phase 7: bat`, `Phase 7: wolf`

### Phase 7 notes and self-review (checkpoints waived, see the top of this file)

Built: per-rig animation sets with aliases, rig-level z-order, closed-eye shade, shadow, hover, validator motion checks and rig-authored hitboxes (ARCHITECTURE.md section 20); the slime, bat and wolf in s, e and n on the enemy profile (MONSTERS.md section 5.6); `pf roster` and W7; the `sound_rings` FX; battle strips that apply root motion and fire an event's own projectile. All three validate with 0 errors and 0 warnings; `tests/test_monsters.py` covers squash and stretch, the hop, eyes per view, the hover and its shadow, wing beats, the bat's fall, the wolf's leg shading, tail lag, bite reach and lying death, and W7.

What the review images show:
- Slime: the draft's dome jiggles (base, squash, base, stretch); the hop squashes, stretches, rises 3 to 4 px with the shadow narrowing and lands; the slam flattens into a deep squash (the tell), leaps on root motion and lands on the knight with `impact_big`; the spit swells twice and fires a green `poison_glob` from the mouth; hurt splats; death melts into a 15 x 4 puddle.
- Bat: a brown fur ball with glowing red eyes and dark membrane wings beating up, mid, down; the swoop rises with wings wide, dives 4 px with wings swept back and pulls up; it tumbles when hurt and falls to lie with its wings flat.
- Wolf: a chibi wolf in profile with a big head, a bushy tail that trails a frame, two clear leg pairs (far legs darker); the walk alternates diagonal pairs, the gallop leaves the ground, the bite crouches with ears back, snarls and lunges with jaws wide, the howl lifts the snout under sound rings, death falls onto its side. Facing s a cat-like front view with two eyes; facing n the rump and tail.
- Roster: slime, bat, wolf and anchor_girl have clearly different silhouettes at 1x (dome, wings, quadruped, person); size grows from slime to wolf.

Rubric (slime / bat / wolf):
1. Style match 5 / 4 / 4: the slime is the kit's own draft; all use the generated outline, open soles and the monster ramps.
2. 1x readability 4 / 4 / 4: each reads on beige, light and dark; the bat's dark wings read as a silhouette.
3. Silhouette 5 / 4 / 4: one signature feature each (the dome, the wings, the tail and ears).
4. Motion 4 / 4 / 4: squash and stretch, wing beats and gaits are redrawn, never scaled; timing is for the human to judge.
5. Consistency 4 / 4 / 4: same shading and pixel scale in every frame and view.
6. Cleanliness 4 / 4 / 4: W3 and W5 clean (the wolf after its despeckle pass).
7. Part fit 4 / 4 / 4: eyes, gloss and tail follow their anchors; the lying wolf hides its tail part.
8. Appeal 5 / 4 / 4: the slime is cute; the bat and wolf are chibi but threatening (glow eyes, snarl).
9. Combat readability 4 / 4 / 4: whole-body tells (deep squash, rise, crouch) last at least 300 ms on the enemy profile; hits have impacts.

Known limits: the wolf's s and n views are simpler than its profile, as MONSTERS.md allows; the bat's e view is its front view with the eyes turned.

---

## Phase 8: Monster rigs II: humanoid monsters and the medium size class (CHECKPOINT)

Status: done (commits "Phase 8 (part 1): orc, skeleton, frost wolf", "Phase 8 (part 2): goblin and goblin chief", "Phase 8: humanoid monsters, ogre, variants"; see the notes below)

Tasks:
1. **Skeleton:** `body/skeleton` variant for the humanoid rig, bone material, glow eyes, `bone_crumble` death.
2. **Goblin:** `humanoid_small` rig, resized parts, ears as rigid parts.
3. **Orc:** green skin preset, tusks part, armor.
4. **Ogre:** `humanoid_large` rig on the medium canvas, `attack_heavy`, `roar`.
5. Families and elites: one family variant (for example frost wolf) and one elite (for example goblin chief) following MONSTERS.md section 6.

Acceptance:
- Medium size class verified (pivot, mirror axis, shadow scale, W10 clean).
- Roster lineup: every monster distinct by silhouette; elites distinct from their base in grayscale.

**CHECKPOINT:** the roster lineup plus each new monster's combat animations in the preview.

Commit: `Phase 8: humanoid monsters, ogre, variants`

### Phase 8 notes and self-review (checkpoints waived, see the top of this file)

Built: the skeleton, orc, goblin, goblin chief, frost wolf and ogre (MONSTERS.md sections 5.4 and 5.7); the `humanoid_small` and `humanoid_large` rigs; the medium size class end to end (48 px canvas, pivot (23, 43), west mirrored around x = 23, export, reviews, roster, battle strips and the preview's arena placing sprites by pivot); the footprint shadow rule (`effects.footprint_shadow`, which reproduces the anchor's own shadow from a 9 px footprint); W10; smears for weapons drawn per frame (`smear_<anim>.png`); recipe `family` for W7; rig `validator.head_slots` for E10. Every recipe validates with 0 errors and 0 warnings (68 parts, 30 recipes). `tests/test_humanoid_monsters.py` covers the new monsters, the medium class (canvas, pivot, mirror, baseline, export, shadow scale), W10 on a deliberately dithered sprite, drawn smears, W7 across families and sizes, and the ogre's tell. The preview bundle also gained a charset line so it reads right opened from disk.

What the review images show:
- Skeleton: a bone skull with ghost-blue eyes, dark sockets and rib lines over the humanoid body, sword and shield; every humanoid animation, crumbling into `bone_crumble` at death.
- Orc: green skin, red eyes, an iron cap with two horns rising above any human head, plate, greaves and a mace.
- Goblin: a tiny green body with wide pointed ears (the signature), yellow eyes, a mustard loincloth and a stubby club; quick steps, a raised-and-coiled club swing, a kneel and a poof at death. The chief adds a gold crown, a darker bog hide and red eyes.
- Frost wolf: the wolf's shape in pale frost fur with ghost-blue eyes.
- Ogre: a hunched brute twice the anchor's bulk, the head sunk between round shoulders, a topknot, tusks from an underbite, long arms and a club on the shoulder. The slam lifts the club, leans back with it behind the head, squashes, then brings it down in front under a drawn smear arc and leaves it on the ground with `impact_big`; facing s and n it swings down on the weapon side. The roar drops the jaw and raises both fists; death kneels, drops the club and slumps.
- Roster: nine monsters and the anchor in a size-sorted lineup; every silhouette is different (dome, wings, quadruped, ears, ears and crown, person, bald skull and shield, horns, the ogre's mass). The goblin chief differs from the goblin in grayscale (68% of shared pixels change by more than 8 levels) and in silhouette (the crown); the frost wolf by value (64%).
- Battle strips: ogre vs knight and knight vs ogre stand on one ground row; the club lands on the knight's hurtbox with a flash and `impact_big`.

Rubric: per monster in MONSTERS.md section 5.7; every score is 4 or higher.

Known limits: the ogre's arms are shaded tubes, simpler than its hand-drawn torso and head; elites so far are recolor-plus-trait (no champion aura yet); the goblin's parts are its own (the humanoid's do not resize).

---

## Phase 9: First boss (CHECKPOINT)

Status: done (commit "Phase 9: first boss"; see the notes below)

Tasks:
1. Write the boss spec in MONSTERS.md section 5.5 first and get the human's approval on the concept and silhouette grid before drawing.
2. Build the boss rig (large size class, separately animated pieces as needed), all animations with the boss timing profile, and any boss-specific FX.

Acceptance:
- Every heavy attack telegraphs for at least 600 ms with a whole-body tell.
- Reads as the same style as the anchor despite its size (bigger clusters, 1 px outline).

**CHECKPOINT:** the human fights it (watches every attack against the knight) in the preview.

Commit: `Phase 9: first boss`

### Phase 9 notes and self-review (checkpoints waived, see the top of this file)

Built: the spec first (MONSTERS.md section 5.5: the Stone Warden, written before any drawing and approved under the waiver); the `stone` material (granite, basalt, sandstone, frost); the `golem` rig on the large 64 px class with separate arm layers and `emitters`; `tools/art/stone_warden.py`, which draws every frame from shaded boulders (contours where stones overlap, each layer flattened to what it shows); twelve animations covering Rolling Knight's six boss moves plus enrage, hurt and death; `stone_warden` and `stone_warden_enraged` (red core and eyes) on the `boss` profile; four FX (`shockwave`, `rock_shard` with its impact, `summon_circle`, `falling_rock`); `spawn` volleys (`pattern`, `count`, `spread`), the `summon` event and exported `loop_frames`. Both recipes validate with 0 errors and 0 warnings (W10 included); `tests/test_boss.py` covers the large class, every move's tell, the exported move data, non-overlapping layers, the core going dark and the enraged recolor.

What the review images show: a guardian of mossy granite boulders, each parted from the next by an outline, a crown of three stones, a visor slit with two cyan eyes and a cyan core in a socket in the chest; fists as big as its head resting on the ground. Facing e its far arm hangs behind, the near arm in front of the chest, with a sliver of the core showing; facing n the back with moss on the shoulders. The slam raises both fists into a ring over the head (behind it facing e, so the face stays seen) and hammers the ground in front with `impact_big` and a dust ring; the ring spreads both arms into a Y while the core gathers light, then a shard flies; the fan cocks a fist and punches a shard out; the charge lowers the head like a ram, rushes on root motion and skids; summon lifts both fists over a rune circle; the stomp lifts a leg high and slams it down; death cracks it apart into a rubble pile with the core dark. Against the knight every tell is a whole-body pose held 732 to 908 ms on the boss profile, and the knight stands on the warden's ground row.

Rubric:
1. Style match 4: the 1 px outline, open soles and the anchor's flat, few-shade look on bigger shapes; contours separate stones like the anchor's hand-placed lines.
2. 1x readability 4: the silhouette and its glow read on beige, light and dark.
3. Silhouette 5: floating stones, a crown and huge fists; nothing else in the roster looks like it.
4. Motion 4: stones move independently, arms trail the body a frame, death tumbles.
5. Consistency 4: one light from the upper left on every stone in every view.
6. Cleanliness 4: W3, W5 and W10 clean (contours and despeckle passes against what is visible).
7. Part fit 4: core, eyes and moss follow their stones; the core is hidden once dark.
8. Appeal 4: a dignified old guardian rather than a monster: moss, a glowing core, a crown.
9. Combat readability 5: six distinct, long whole-body tells; FX never cover them (W9 clean).

Known limits: stones are procedural rounded boxes with seeded cracks, so they are tidier than hand-placed rock; the enraged form changes only the glow (the game's speed-up does the rest).

---

## Phase 10: Package for reuse

Status: done (commits "Phase 10 (part 1): ..." and "Phase 10: docs, examples, skill, v1.0", tag `v1.0`; see the notes below)

Tasks:
1. README.md for humans: what pixelforge is, how to make a character or monster, how to add a part, rig or FX, and how to use the exports (including events, hitboxes and root motion) in Phaser and Godot.
2. Commit finished example exports to `out/examples/`: the knight, one monster per rig, and the FX set.
3. Install the skill: copy `templates/SKILL.md` to `~/.claude/skills/pixelforge/SKILL.md`, fill in the absolute path to this repo, and test it from a different folder.
4. Tag `v1.0` and push.

Acceptance:
- From a fresh Claude Code session in another project, "make me a pixelforge goblin archer enemy" works end to end using the skill, with the enemy timing profile and a bow.

Commit: `Phase 10: docs, examples, skill, v1.0`

### Phase 10 notes and self-review (checkpoints waived, see the top of this file)

Built: `README.md` rewritten for humans (what pixelforge is, making characters, monsters, parts, rigs and FX, the export format, engine use); `loaders/pixelforge.ts` (framework-free TypeScript for canvas renderers like Rolling Knight: sheets, an animator that fires events in order and retimes for a profile, world-space boxes and points, FX sheets with per-tag pivots), `loaders/phaser.js` and `loaders/godot/pixelforge_sprite.gd`; `tools/make_examples.py` and `out/examples/` (the knight, the ranger, one monster per rig, the boss and the FX set); `templates/SKILL.md` filled in and installed to `~/.claude/skills/pixelforge/SKILL.md`; version 1.0.0. `tests/test_loaders.py` runs the TypeScript loader under Node against fresh exports and checks it against the exporter's timing.

Acceptance run ("make me a pixelforge goblin archer enemy" from a fresh project): goblins had no bow, so, as the skill says for missing art, the goblin got one first: `held_near/goblin_bow` drawn per frame, `shoot_bow` for the `humanoid_small` rig, a quiver, and the `goblin_archer` recipe (enemy profile, family `goblin`). Then a separate agent with no context but the installed skill did the request from a new game folder: found the recipe, built it (0 errors, 0 warnings), validated, opened the reviews, copied the PNG and JSON and the TypeScript loader into the game and played the shot (windup at 0 ms, the arrow spawned at `bow_nock` at 560 ms on the enemy profile, recover at 740 ms) in all four views. Its findings, all fixed before tagging: the skill now says to reuse an existing recipe, to copy the FX a character's events name, how to load under Node, and where the combat review files are; the loader plays FX sheets (per-tag pivots); `charge_loop_frame` is exported as `loop_frames` so a game can hold a full draw; COMBAT.md section 2 says the tell runs to `hit` or `spawn`; and the archer's tell now sinks the whole body into the draw in every view, with a quiver so it no longer looks like the club goblin at idle.

What the review images show: the goblin archer is the goblin with a tan short bow held at its side and a quiver over its shoulder; facing e it raises the bow, sinks into the draw with the string back and an arrow on it, looses (the arrow crosses to the knight, which flashes) and lowers the bow.

Rubric (goblin archer): style match 4, 1x readability 4 (the bow is thin at 1x; the quiver and pose carry it), silhouette 4, motion 4, consistency 4, cleanliness 4, part fit 4, appeal 4, combat readability 4.

Known limits: the Phaser and Godot loaders are written against their documented APIs (Phaser's Aseprite loader, Godot 4's `SpriteFrames`) but not run here; the skill is installed in this machine's `~/.claude/skills`, and each machine that uses pixelforge needs the same copy.

---

## Motion pass 1 (after v1.0)

Status: done (commit 37e3060)

Asked for after v1.0: the animations were "the most basic baseline trudging movements"; research how good pixel art moves and flows, then apply it. The research (Slynyrd's Pixelblogs on idles, walks and attacks; sub-pixel animation; the animation principles at pixel scale), the eight motion rules and every decision made here are in `docs/MOTION.md`.

Built:
- **Engine:** every `lags: true` part follows through (trails its anchor by a pixel while it moves, catches up when it stops, swings 1 px past a frame later, settles; never on a held last frame). Torso wear and tabards stretch with the neck when the idle drops the chest under a still head, in the dark shade facing n.
- **Humanoid idle:** 6 frames; the breath travels chest, head, hands, and the hair follows through; 360/100/100/260/140/140 ms (sinks fast, rises slower, holds the top).
- **Humanoid walk:** 8 frames (contact, down, pass, up, twice), a triangle bob, arms swinging in phase with the legs in three reach states; 100/80/90/80 ms; 12 px per cycle.
- **Humanoid run (new):** 8 frames with two flight frames, a 1 px lean, a long arm pump; 4 px strides, about 54 px/s, Rolling Knight's movement speed. Added to the anchor girl, both knights, the six Rolling Knight classes, the orc and the skeleton; the derived parts (greaves, boots, gauntlets, the skeleton's bones) follow automatically.
- **Preview:** the walk test plays the walk or the run at its natural speed. **Loader:** `Sheet.naturalSpeed(anim)` and `Animator.rate`, so a game plays the run at any entity speed without sliding feet (tested at 50 and 64 px/s, Rolling Knight's slowest and fastest knights).

Fixed on the way: hanging weapons left the canvas on the walk's down frames (the dip now absorbs a forward reach facing s and n); the skeleton's speckle cleanup moved planted foot pixels (the planted leg keeps its foot rows); a lone dark pixel in the passing leg showed through greaves; a 17-color random character (the random set was redrawn by `pf random`, which enforces the budget); a line of skin under helmets on the stretched-neck frame.

What the review images show: facing e the anchor girl walks with her feet alternating under a 1 px bob, lowest as the weight lands and highest as the free foot swings through; the knight's sword hangs from a hand that swings back while the same-side foot leads. Running, the stride opens wide with the back foot kicked up, the body leans forward, and on the flight frames both feet leave the ground with their soles outlined and the shadow shrinking. Idle, the chest sinks first, the head follows, the hands settle, and the hair locks swing a pixel past the head before settling; the knight's gorget stretches under the helmet instead of opening a line of skin.

Rubric (anchor girl, knight, orc; idle, walk, run in every view): style match 4 (same parts, palette and outline), 1x readability 4 (the run's open stride and the bob read at 1x; the arm swing is subtle where sleeves match the torso, clear with a held weapon), silhouette 4, motion 4 (the breath travels, timing eases, the hair follows through, feet never slide; how it feels at true speed is the human's call in the preview), consistency 4 (every humanoid recipe and derived part shares the cycles), cleanliness 4 (0 validator findings across 33 recipes), part fit 4 (held items stay on the canvas, armor follows the neck), appeal 4, combat readability 4 (locomotion never covers a tell).

Next (MOTION.md section 5): attack_slash and attack_heavy (a two-frame strike, a follow-through that reaches 1 px further and holds, a settle bounce), combat_idle, and the goblin and ogre idles.

---

## Design pass: a colorful, varied cast (after Motion pass 1)

Status: done (commit "Design pass: bold palette, silhouette parts, redesigned cast"; the arcanist got a witch hat when the silhouette test found it too close to the cleric)

Asked for: "u see how character's are different and interesting with different colours and designs. make it like that" (with a reference roster of chibi sprites; not to be copied). Also: "whenever something is swung, have a trail of white behind it" (done first, commit "White swing trails on every swing").

Built:
- **Palette:** character chroma up to 0.13 and lightness to 0.84 (from 0.09 and 0.80), 48 bold presets generated in OKLCH and checked by `pf palette --check` (0 errors, 0 warnings): cloth royal, scarlet, emerald, violet, sunflower, azure, rose, tangerine, ink, snow, jade, wine; hair fire, platinum, raven, bubblegum, lavender, sky, leaf, copper, golden; skin ebony, frost, dusk, ash, ember, porcelain; metal obsidian, royal gold, blued, rose gold, verdigris, crimson; accents, leathers and eye colors. 24 colors per frame (from 16).
- **Engine:** `slot_colors` in recipes (one part in its own preset of its material), new slots `cape`, `scarf`, `shoulders`, `ears`, `beard` in the z-order, W3 counted per part.
- **Parts** (`tools/art/parts_design.py`): cloak (follows through), scarf (tails follow through), pauldrons, full beard, elf ears, cat ears, spiky hair, twin tails (follow through), ranger hat with a feather, bandana; the horned helm lost two speckle pixels.
- **Cast:** the six Rolling Knight classes and both knights redesigned (GAMES.md), six heroes in `characters/heroes/`, and a randomizer with the new parts, two-tone chances and exclusions that redraws until every character validates (24 random characters).

What the lineup shows: next to the old cast (one domed silhouette in grey, brown and olive), every character now has a shape and a color of its own: the blue guardian with a red plume and cloak, the black-haired blade in a red scarf, the elf ranger under a wide hat with an orange feather, the cleric in gold and white, the white-bearded violet wizard, the gold-helmed lancer with white twin tails, the gold paladin with a blue cloak, the masked corsair, the copper-bearded dwarf, the pink cat-eared scout, the blue frost elf and the horned red warlock.

Rubric (the redesigned cast): style match 4 (same body, outline and shading; the colors are bolder by decision), 1x readability 5 (hats, hair, ears and capes read at 1x where the old cast blurred together), silhouette 5, motion 4 (cloaks, scarves and tails follow through), consistency 4, cleanliness 4 (0 validator findings across 51 recipes), part fit 4, appeal 5, combat readability 4 (the white swing trails stay the brightest thing on screen).

Next: the Stone Warden as a forest guardian (the human's reference), and new monsters: big, slow ones (a dragon) and a tall, quick humanoid duelist.

