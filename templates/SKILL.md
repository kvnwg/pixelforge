---
name: pixelforge
description: Make pixel art game characters, monsters, bosses, NPCs, combat animations, spell and attack effects, and spritesheets using the pixelforge tool, in its locked tiny chibi style, with combat data (hitboxes, events, telegraph timing) exported for the game. Use this skill whenever the user asks for a sprite, a hero or class, an enemy or monster, a boss, attack or spell animations, FX, a spritesheet, or new outfits, weapons or recolors, even if they don't mention pixelforge by name. Do not generate pixel art any other way for these games.
---

# pixelforge

pixelforge lives at: `REPLACE_WITH_ABSOLUTE_PATH_TO_PIXELFORGE_REPO` (below: `<repo>`).

It builds characters by layering parts onto shared base animations (rigs), recoloring with material ramps, auto-outlining, validating and exporting PNG spritesheets with Aseprite-format JSON whose `meta.pixelforge` block carries the pivot, events, hitboxes, points, root motion and timing profiles.

Run its commands from anywhere with the repo's venv and root:

```bash
PIXELFORGE_ROOT=<repo> <repo>/.venv/bin/pf --help
```

## Before doing anything

1. Read `<repo>/CLAUDE.md`. Its rules apply here too (no resampling, the locked palette, look at review images before judging art, `pf validate` and the tests pass before a commit).
2. For new art, also read `<repo>/docs/STYLE_GUIDE.md` and the relevant part of `<repo>/docs/ANIMATION_SPEC.md`, and for any animation `<repo>/docs/MOTION.md` (how motion should flow); for monsters `<repo>/docs/MONSTERS.md`; for attacks, spells and FX `<repo>/docs/COMBAT.md`.

## Making a character or monster from existing parts

1. Look for a recipe that already is what the user asked for in `<repo>/characters/` and `<repo>/characters/monsters/` (`ls` both): if one fits, use it as is instead of writing a duplicate. Otherwise browse `<repo>/parts/` (slot, then variant) and the presets under `materials` in `<repo>/style/style.json`; `goblin_archer.yaml`, `ogre.yaml` and `stone_warden.yaml` are good models.
2. Write a recipe (only when none fits; a variant of an existing one gets a new name and the same `family:`). Pick the rig (`humanoid`, `humanoid_small`, `humanoid_large`, `blob`, `flyer`, `quadruped`, `golem`) and the timing profile: `player` for heroes, `enemy` for mobs, `elite` for stronger variants, `boss` for bosses (the same art gets longer tells). A recolor or elite of an existing monster shares its `family:`.
3. `pf build <name>`, then `pf validate`.
4. `pf review <name> --combat` and open `review/<name>/turnaround.png`, `vs_anchor.png`, `<anim>_strip_1x.png` and, for each attack, `<anim>_<dir>_timeline.png`; `pf battle <name> knight --anim <attack>` writes `review/battle/battle_<name>_vs_knight_<attack>.png`; `pf roster` writes `review/roster_lineup.png` for a monster. Describe what you see before judging it.
5. Copy `<repo>/out/<name>/<name>.png` and `<name>.json` into the game's asset folder (ask where if unclear), and with them every FX its events name (`"fx"` in `meta.pixelforge.events`: an arrow, sparks, impacts): `<repo>/out/fx/<fx>/` after `pf fx build --all`, or the committed copies in `<repo>/out/examples/fx/`. For code, `<repo>/loaders/` has `pixelforge.ts` (any canvas renderer, Rolling Knight; it plays FX sheets too), `phaser.js` (Phaser 3) and `godot/pixelforge_sprite.gd` (Godot 4); copy the one the game needs. Under Node, build a `Sheet` from the parsed JSON (`loadSheet` is for browsers) and import the loader with its `.ts` extension.

## When something doesn't exist yet

1. Tell the user what is missing (a part, an animation for a rig, an FX) and ask before creating it, since new art takes real effort.
2. Draw it the way the repo does: character grids in a script under `<repo>/tools/art/` (see `goblin.py` for a weapon and an attack added to a small rig, `fx_art.py` for FX), or `pf template <slot> <variant> <anim>` for a PNG drawn against the guides.
3. Follow the review protocol in `<repo>/docs/QUALITY.md` until every rubric score is 4 or higher, show the user the review images, and wait for approval.
4. A new monster type that needs a new rig, or any boss, gets a written spec in `docs/MONSTERS.md` first.
5. Commit the new art to the pixelforge repo (not the game repo) so every game can use it.

## Using exports in a game

- Tags are `<anim>_<dir>` with `dir` in s, e, n, w; w is drawn, never flip at runtime. Choose the view from the aim vector's dominant axis.
- Place sprites by `meta.pixelforge.pivot` (their ground point), at integer positions and zoom.
- Events: `windup` (the tell), `hit` (damage and hit stop), `spawn` (a projectile from `point`, aimed from there at the target, not from the pivot; bosses add `pattern`, `count`, `spread`), `vfx` (play `fx` at `point`), `summon`, `recover`. FX pivots are per tag (`<anim>_<dir>`).
- `hitboxes` exist only on active frames; `root_motion` moves the entity; `loop_frames` may repeat while a move lasts (a charge, a held full draw).
- Moving entities play `run` (or `walk` when slow) and scale its playback to their speed so the feet don't slide: natural speed is the sum of `stride_px[<anim>_e]` over the cycle's duration (about 54 px/s running, 17 walking); in the TypeScript loader `animator.rate = speed / sheet.naturalSpeed("run")`, then back to 1 for other clips.

## Rules

- Never resample, rotate, scale or antialias character art. Only integer moves and mirroring.
- Only colors from `style.json`. New presets must pass `pf palette --check`.
- Never describe art as good without opening the review images first.
- `pf validate` must pass before copying anything into a game.
- Never commit, push or open pull requests in the Rolling Knight repository (kvnwg/rolling-knight), ever. Copy exports into its folder only when the user asks, and leave committing them to the user.
