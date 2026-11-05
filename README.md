# pixelforge

pixelforge makes tiny chibi pixel-art characters, monsters, bosses and combat effects in one locked style, and exports them with the combat data a game needs. It was built for **Rolling Knight** and is engine-agnostic: the output is PNG spritesheets plus Aseprite-format JSON.

The style is pinned to one reference sprite, `style/anchor.png` (11 x 18 px on a 32 x 32 canvas): a muted locked palette, a generated 1 px plum outline with open soles, hard pixels, never any scaling or rotation of character art. Everything else is measured against it.

How a character is made: hand-authored **parts** (bodies, hair, armor, weapons, ears, tusks...) are layered onto a **rig**'s base animations, recolored with **material ramps**, outlined as one silhouette, checked by a validator and exported. A recipe is a few lines of YAML:

```yaml
name: knight
rig: humanoid
timing_profile: player
parts: {headwear: great_helm, torso_wear: plate, held_near: sword, held_far: shield, ...}
colors: {metal: steel, cloth: crimson, leather: dark}
anims: [idle, walk, run, combat_idle, attack_slash, attack_heavy, block_hold, dodge, hurt, death, victory]
```

## What's in it

| | |
|---|---|
| Rigs | `humanoid` (the player cast), `humanoid_small` (goblins), `humanoid_large` (ogres, on a 48 px canvas), `blob` (slimes), `flyer` (bats), `quadruped` (wolves), `golem` (the Stone Warden boss, on a 64 px canvas) |
| Characters | the anchor girl, a knight and a dark knight, the six Rolling Knight classes, six heroes (`characters/heroes/`: paladin, corsair, dwarf, catfolk scout, frost elf, ember warlock), a randomizer that draws varied, validated characters; monsters: slime, bat, wolf and frost wolf, skeleton, orc, goblin, goblin chief, goblin archer, ogre, and the Stone Warden boss with its enraged form |
| Design | every character gets its own silhouette and signature color: bold presets (royal, scarlet, emerald, violet, gold, fire, frost...), two-tone outfits (`slot_colors`), and silhouette parts: cloaks, scarves, pauldrons, beards, elf and cat ears, spiky hair, twin tails, a wide feathered hat, a bandana |
| Motion | a 6-frame idle that breathes through the body (chest, head, hands), 8-frame walk and run cycles (the run with flight frames, tuned to Rolling Knight's speed), and follow-through on hair, ponytails and tails; `docs/MOTION.md` has the research and rules behind them |
| Combat | attack_slash, attack_heavy, shoot_bow, cast, block, dodge, roll, backflip, vault, stun, hurt, death, victory; monster sets (hop, spit, swoop, bite, howl, roar...) and six boss moves; phases, events, hitboxes, hurtboxes, root motion and four timing profiles (player, enemy, elite, boss) |
| FX | 44 effects: hit sparks, slam impacts and shockwaves, projectiles and their impacts per element, charge glows, status overlays, death poofs, sound rings, summon circles, falling rocks |
| Tools | a validator with 30 rules, review renders, a browser preview with a combat arena, loaders for canvas/TypeScript, Phaser and Godot |

Finished examples are in [`out/examples/`](out/examples/): one character per rig, the boss and the FX set.

## Setup

Python 3.11 or newer.

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -e ".[dev]"
```

```bash
.venv/bin/pytest
```

`pf` finds the repo from the current folder, or from `$PIXELFORGE_ROOT` when run elsewhere.

## Everyday commands

```bash
.venv/bin/pf build knight
```

```bash
.venv/bin/pf validate
```

```bash
.venv/bin/pf review knight --combat
```

```bash
.venv/bin/pf preview
```

- `pf build <recipe>... | --all`: composite, validate and export to `out/<name>/` (PNG, JSON, GIFs).
- `pf validate`: every rule on every part and recipe; exits 1 on errors (QUALITY.md lists the rules).
- `pf review <recipe> [--combat]`: review images in `review/<name>/` (turnaround, side by side with the anchor, sheets, onion skins, silhouettes, 1x strips, timelines). Look at them before calling art good.
- `pf battle <attacker> <defender> --anim A [--profile P]`: an attack against a target, with FX and hit timing.
- `pf roster`: every monster in a size-sorted lineup with silhouettes (and the lookalike check).
- `pf preview [--bundle file.html]`: the browser preview (player, gallery, walk test, arena, FX).
- `pf fx build --all` and `pf fx review`: the FX library.
- `pf palette --check`, `pf template`, `pf random --seed N --count K`, `pf anchors --check`, `pf diff`.

## Making things

**A character from existing parts.** Browse `parts/<slot>/<variant>/` and the material presets in `style/style.json`, write `characters/<name>.yaml`, then build, validate and review. `pf random` shows what combinations look like.

**A monster.** Pick a rig and a timing profile (`enemy`, `elite` or `boss`: enemies get longer tells from the same art). A variant of an existing monster is a recipe with other presets and a shared `family:` (an elite adds a trait, like the goblin chief's crown, and must read differently in grayscale). Read `docs/MONSTERS.md` first.

**A part.** `pf template <slot> <variant> <anim>` writes an empty sheet and a guide with the base body ghosted in. Parts are drawn as character grids in Python (`tools/art/*.py`) or edited as PNGs in Aseprite; one material per part, no outer outline (the compositor draws it), outline-colored pixels inside a part are kept as details. Then build, validate, review, and score the rubric in `docs/QUALITY.md` until every score is 4 or higher.

**A rig or a boss.** A rig is a folder `parts/body/<rig>/` with sheets and `anchors.json`, plus an entry under `rigs` in `style.json` (size class, z-order, animations, events). Bosses get a written spec in `docs/MONSTERS.md` section 5.5 before any drawing; `tools/art/stone_warden.py` is the worked example (separate arm layers, a 64 px canvas, six moves).

**An FX.** Add it to `tools/art/fx_art.py` (drawn facing east in an `fx_ramps` ramp), run it, then `pf fx build --all`. FX may be brighter than characters, may rotate in 90 degree steps, and must read on beige, light and dark ground.

## Using the exports

Each export is `<name>.png` plus `<name>.json`:

- `frames` and `meta.frameTags`: standard Aseprite JSON. Tags are `<anim>_<dir>` with `dir` in `s`, `e`, `n`, `w`. West is drawn (mirrored at build time), so never flip sprites at runtime. Pick the view from the aim or travel vector's dominant axis.
- `meta.pixelforge`:
  - `pivot`: the pixel that stands on the ground point (`[15, 27]` small, `[23, 43]` medium, `[31, 59]` large). Place the sprite so this pixel is on the entity's position; use integer positions and integer zoom.
  - `events[tag]`: `{frame, type, fx?, point?, point_name?}` with types `windup` (the tell starts), `hit` (deal damage, hit stop), `spawn` (a projectile at `point`; bosses add `pattern: ring|fan`, `count`, `spread`), `vfx` (play `fx` at `point`), `footstep`, `summon`, `recover` (can act again).
  - `hitboxes[tag][frame]` and `hurtboxes[tag][frame]`: `{x, y, w, h}` in frame pixels; hitboxes exist only on active frames.
  - `points[tag][frame]`: named points per frame (`hand_near`, `weapon_tip`, `bow_nock`, `head`, `torso`, `core`...) for attaching FX and projectiles.
  - `phases[tag]`: `windup`, `active` or `recovery` per frame.
  - `root_motion[tag]`: pixels to move along the facing per frame (dodges, a boss's charge); `loop_frames[tag]`: frames to repeat while a move lasts.
  - `stride_px[tag]`: ground pixels a gait's planted feet travel per frame (walk and run, facing e and w). Their sum over the cycle's duration is the gait's natural speed (about 17 px/s walking, 54 running); move at it, or scale the playback rate to the entity's speed, and the feet never slide.
  - `holds`, `base_durations`, `timing_profiles`: frame durations in the sheet are already timed for the recipe's profile; these let a game retime the same art for another profile (hold frames x `hold_scale`, then the last hold grows until the tell meets `telegraph_min_ms`).
- FX exports (`out/fx/<name>/`) use the same format; their `pivot` is per tag, and `layer` (above or below characters), `space` (world or follow an anchor) and `loops` say how to play them.

### Rolling Knight, or any canvas renderer (TypeScript)

`loaders/pixelforge.ts` has no dependencies: `Sheet` reads an export, `Animator` plays clips, fires events in order, retimes for a profile, gives world-space hitboxes and points, and draws with the pivot on the entity's position. FX exports load the same way (their pivot is per tag), so the arrow a `spawn` event names is one more `Sheet`; copy the FX a character's events name along with it (`out/fx/<fx>/`, or `out/examples/fx/`). In Node, build `new Sheet(JSON.parse(text))` and import the file with its `.ts` extension.

```ts
import { loadSheet, Animator, facing } from "./pixelforge";

const sheet = await loadSheet("art/goblin_archer.png", "art/goblin_archer.json");
const goblin = new Animator(sheet);            // its recipe's timing (enemy)
goblin.play("shoot_bow", facing(target.x - x, target.y - y));

// every tick:
for (const ev of goblin.update(dtMs)) {
  if (ev.type === "spawn") fireArrow(arrowSheet, goblin.toWorld(ev.point!, x, y, zoom));  // aim from the point
  if (ev.type === "hit") damage(goblin.hitboxes(x, y, zoom));
}
goblin.draw(ctx, x, y, zoom);

// a moving knight plays the run at its own speed, so its feet never slide
const knightSheet = await loadSheet("art/knight.png", "art/knight.json");
const knight = new Animator(knightSheet);
knight.play("run", facing(vx, vy));
knight.rate = speed / knightSheet.naturalSpeed("run")!;   // px/s; set it back to 1 for attacks
```

### Phaser 3

`loaders/phaser.js` uses Phaser's own Aseprite loader, sets each sprite's origin to its pivot, applies the loop flags and emits `pf-event` as frames show.

```js
preloadPixelforge(this, "ogre", "art/ogre.png", "art/ogre.json");   // in preload()
const ogre = createPixelforge(this, "ogre", 160, 120);               // in create()
ogre.on("pf-event", (e) => { if (e.type === "hit") smash(hitboxes(ogre)); });
playDir(ogre, "attack_heavy", facing(dx, dy));
```

### Godot 4

`loaders/godot/pixelforge_sprite.gd` is an `AnimatedSprite2D` (`PixelforgeSprite`) that builds its `SpriteFrames` from an export, can retime for another profile, puts its origin on the pivot and emits `pf_event`.

```gdscript
var boss := PixelforgeSprite.new()
boss.texture = load("res://art/stone_warden.png")
boss.json_path = "res://art/stone_warden.json"
add_child(boss)
boss.pf_event.connect(func(e): if e.type == "spawn": shoot(e.get("pattern"), e.get("count")))
boss.play_dir("cast_ring", PixelforgeSprite.facing(to_player))
```

## Using pixelforge from another project

`templates/SKILL.md` is a Claude Code skill. Copy it to `~/.claude/skills/pixelforge/SKILL.md` and set the repo path in it; then, from any game's folder, asking Claude Code for "a goblin archer enemy" or "a fire variant of the slime" goes through pixelforge: recipes, parts, validation, review and an export copied into the game.

## Documents

| | |
|---|---|
| `CLAUDE.md` | the rules (read them before changing anything) |
| `docs/STYLE_GUIDE.md` | the style, measured from the anchor |
| `docs/ARCHITECTURE.md` | how the system is built |
| `docs/ANIMATION_SPEC.md` | frame-by-frame specs for locomotion and reactions |
| `docs/MOTION.md` | how sprites should move: research with sources, the motion rules, decisions |
| `docs/COMBAT.md` | the combat set, timing profiles, events, hitboxes, the FX library |
| `docs/MONSTERS.md` | rigs, size classes, monster design, the boss spec |
| `docs/QUALITY.md` | validator rules, the review protocol and rubric |
| `docs/ROADMAP.md` | the phases, with the decisions and self-reviews made along the way |
| `docs/GAMES.md` | what each game needs (Rolling Knight first) |

pixelforge was built phase by phase from a starter kit (`KICKOFF_PROMPT.md` holds its prompts).
