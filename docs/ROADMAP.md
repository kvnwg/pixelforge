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

Status: not started

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

---

## Phase 6: FX library (CHECKPOINT)

Status: not started

Tasks:
1. FX pipeline: `fx/<name>/fx.yaml`, sheets, `pf fx build`, `pf fx review`, validation against `fx_ramps`, 90-degree rotation support.
2. The v1 set in COMBAT.md section 6: smears, impacts (neutral and per element), projectiles (travel and impact), gather glow, status overlays, death poofs, support effects.
3. Wire events to FX in the preview so `spawn` and `vfx` play the real effects.

Acceptance:
- Every FX validates; all read at 1x on beige, light and dark backgrounds.
- Battle strips for slash, heavy, bow and each spell element look like one game.

**CHECKPOINT:** the human watches every attack with its real FX in the preview.

Commit: `Phase 6: FX library v1`

---

## Phase 7: Monster rigs I: blob, flyer, quadruped (CHECKPOINT per rig)

Status: not started

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

---

## Phase 8: Monster rigs II: humanoid monsters and the medium size class (CHECKPOINT)

Status: not started

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

---

## Phase 9: First boss (CHECKPOINT)

Status: not started

Tasks:
1. Write the boss spec in MONSTERS.md section 5.5 first and get the human's approval on the concept and silhouette grid before drawing.
2. Build the boss rig (large size class, separately animated pieces as needed), all animations with the boss timing profile, and any boss-specific FX.

Acceptance:
- Every heavy attack telegraphs for at least 600 ms with a whole-body tell.
- Reads as the same style as the anchor despite its size (bigger clusters, 1 px outline).

**CHECKPOINT:** the human fights it (watches every attack against the knight) in the preview.

Commit: `Phase 9: first boss`

---

## Phase 10: Package for reuse

Status: not started

Tasks:
1. README.md for humans: what pixelforge is, how to make a character or monster, how to add a part, rig or FX, and how to use the exports (including events, hitboxes and root motion) in Phaser and Godot.
2. Commit finished example exports to `out/examples/`: the knight, one monster per rig, and the FX set.
3. Install the skill: copy `templates/SKILL.md` to `~/.claude/skills/pixelforge/SKILL.md`, fill in the absolute path to this repo, and test it from a different folder.
4. Tag `v1.0` and push.

Acceptance:
- From a fresh Claude Code session in another project, "make me a pixelforge goblin archer enemy" works end to end using the skill, with the enemy timing profile and a bow.

Commit: `Phase 10: docs, examples, skill, v1.0`
