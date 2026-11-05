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
- Ground shadow scales with the footprint: width = footprint width + 2 (odd), height = width / 3 rounded up, same color and alpha.
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

### 5.5 Bosses

Each boss gets a written spec here before any drawing: concept in two sentences, signature feature, silhouette sketch as a character grid, size class, rig breakdown (which pieces animate separately, for example arms or a tail as separate layers so they can move independently), full animation list with frame tables, phases and telegraph times (boss profile: 500 ms minimum, 600+ for heavy attacks), and FX needs.

---

## 6. Variants: elites and families

- **Family variant** (frost wolf, fire slime): new material presets plus matching FX element. Change value pattern, not just hue, so it reads differently in grayscale.
- **Elite:** family colors plus one added trait (a helmet, a crown, a scar, bigger horns) and glow eyes. Uses the `elite` timing profile.
- **Champion:** elite plus a looping aura FX under the feet.

A variant that is only a hue shift is not enough; players need to tell a stronger enemy apart even when colors are hard to judge.

---

## 7. Roster readability

- `pf roster` renders `review/roster_lineup.png`: every monster and the player's anchor side by side at 1x and 2x, sorted by size, plus a row of solid silhouettes.
- The validator warns (W7) when two different monsters' `combat_idle` frame 0 silhouettes overlap by more than 85% (intersection over union). Fix it by changing the shape, not the color.
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
