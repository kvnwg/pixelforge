# Prompts for Claude Code

Paste these one at a time. Wait for each phase to finish and, at checkpoints, review the images yourself before approving.

---

## Phase 0 (first session)

```
This folder is the starter kit for pixelforge, a reusable pixel art character,
monster, combat and FX system I'll use for fantasy combat across multiple games.
Before doing anything else, read CLAUDE.md and every file in docs/ in full, and
open the images in style/ and style/examples/ (anchor_annotated.png,
anchor_with_shadow.png, recolor_test_6x.png, monster_fx_swatches.png,
battle_mock_6x.png) so you've actually seen the style.

Then write me a short plan for Phase 0 from docs/ROADMAP.md and wait for my OK.

Also ask me which combat view the game uses (side or topdown, see COMBAT.md
section 0) so you can set combat.view.

After I approve: do Phase 0 only. Set up git and a private GitHub repo called
pixelforge with the gh CLI (if gh isn't installed or logged in, stop and tell me
how to fix it). The outline reproduction test on the anchor must pass exactly; if
it doesn't, the algorithm is wrong, not the test.

When Phase 0 meets its acceptance criteria, commit, push, update the status in
ROADMAP.md, and stop. Tell me what you built and what's next.
```

---

## Phase 1

```
Continue with Phase 1 in docs/ROADMAP.md. Re-read STYLE_GUIDE.md sections 2 to 6
and ARCHITECTURE.md sections 4 to 11 first.

The key acceptance test: the anchor_girl recipe must rebuild
style/anchor_with_shadow.png exactly (pixel diff 0) as idle_s frame 0. Build the
compositor, recolor, outline, validator and review tooling needed for that, then
decompose the anchor into single-material parts.

Draw art as character grids with a legend, converted to PNG, so each pixel is
deliberate. Follow the review protocol in QUALITY.md: render the review images,
open them, describe what you see, then judge.

Stop at the checkpoint and show me the exploded view, the rebuilt anchor and a
recolor grid.
```

---

## Phase 2

```
Continue with Phase 2: the four-direction turnaround. Re-read STYLE_GUIDE.md
sections 3, 8 and 10 first.

Design the E and N views of the base body and every anchor_girl part. Keep the
head at exactly 10 rows and the total height at 18 rows. Before drawing, describe
in words how you'll handle the head shape, hair volume, eye position and arms in
the side view, and the hair in the back view.

Iterate with the review protocol until the rubric scores are all 4 or higher,
then stop at the checkpoint and show me turnaround.png at 8x and the 1x strip.
```

---

## Phase 3a

```
Continue with Phase 3a: idle and blink, then the preview tool. Re-read
ANIMATION_SPEC.md sections 1 to 4.

For every frame, check the diff strip: only the upper body and the hair may
change, and the hair must lag by one frame. Build the preview with all the
features in ARCHITECTURE.md section 16.

Stop at the checkpoint and tell me exactly how to open the preview.
```

---

## Phase 3b

```
Continue with Phase 3b: the walk cycle. Re-read ANIMATION_SPEC.md section 5.

Planted feet must never move. In side views, the near and far legs must use
different leather shades. Check the loop seam (frame 3 to frame 0) as carefully
as the other transitions. Add the movement test to the preview.

Stop at the checkpoint. This is the most important approval in the project, so
also list anything you're unsure about.
```

---

## Phase 4

```
Continue with Phase 4: parts library, randomizer and the knight. Re-read the
knight brief in ROADMAP.md and ARCHITECTURE.md sections 5, 7 and 8.

Build pf template first and use its guides for every new part. Do the knight
before the other parts so we validate the pipeline on a full armored character.
Then the remaining parts, compat.yaml, pf random and the gallery.

Stop at the checkpoint with the knight's turnaround and walk, and a gallery of
pf random --seed 1 --count 12.
```

---

## Phase 5

```
Continue with Phase 5: humanoid combat. Read COMBAT.md in full and re-read
ANIMATION_SPEC.md sections 1, 6, 7 and 8. Add anything missing to COMBAT.md
before drawing.

Build the combat data pipeline first (phases, events, hitboxes, hurtboxes, root
motion, timing profiles, export, validator rules E15 to E20), then the review
tools (pf review --combat, pf battle, the target dummy with hit stop in the
preview), then the animations in the directions combat.view requires.

For every attack, check the timeline image: the windup must read as a different
pose from combat_idle at 1x, the active phase must be short with a smear, and
hitboxes must only exist on active frames.

Stop at the checkpoint and show me the knight fighting the dummy with both the
player and the enemy timing profile.
```

---

## Phase 6

```
Continue with Phase 6: the FX library. Re-read COMBAT.md section 6.

FX use only fx_ramps, hard pixels and binary alpha, no outlines by default, and
are brighter than characters on purpose. Build the pipeline, then the v1 set,
then wire spawn and vfx events to real FX in the preview.

Review every FX at 1x on beige, light and dark backgrounds, and in battle strips.
Stop at the checkpoint.
```

---

## Phase 7

```
Continue with Phase 7: monster rigs I. Read MONSTERS.md in full.

Do one monster at a time: slime, then bat, then wolf. For each, describe the
silhouette and signature feature in words and draw the base pose as a character
grid first; show me before animating it. Use the enemy timing profile. Build
pf roster when the second monster exists.

Stop at a checkpoint after each monster with its animations in the preview and
a battle strip against the knight.
```

---

## Phase 8

```
Continue with Phase 8: skeleton, goblin, orc, ogre, then one family variant and
one elite. Re-read MONSTERS.md sections 2 to 7.

The ogre is the first medium size class sprite: same pixel scale, bigger shade
clusters, 1 px outline, never upscaled. Check W7 and W10 and the roster lineup.

Stop at the checkpoint with the roster lineup and each new monster in the preview.
```

---

## Phase 9

```
Continue with Phase 9: the first boss. Before drawing anything, write the boss
spec in MONSTERS.md section 5.5 (concept, signature feature, silhouette grid,
size class, rig breakdown, animation tables, telegraph times, FX) and wait for
my approval.

After approval, build it with the boss timing profile. Every heavy attack needs
a whole-body tell of at least 600 ms. Stop at the checkpoint.
```

---

## Phase 10

```
Continue with Phase 10: package pixelforge for reuse. Write the README (including
how to use events, hitboxes and root motion in Phaser and Godot), commit example
exports, install the skill from templates/SKILL.md into
~/.claude/skills/pixelforge/ with this repo's absolute path filled in, tag v1.0
and push. Then tell me how to test the skill from another project.
```

---

## Resuming in a new session

```
Read CLAUDE.md and docs/ROADMAP.md, run git log --oneline -20, and tell me where
we are. Then continue the current phase.
```

## When something looks off

```
Run pf review for <character> <animation> <direction>, open the sheet, diff strip
and onion skin, and describe frame by frame what you see compared with the table
in ANIMATION_SPEC.md. Don't fix anything yet; just tell me what's wrong.
```
