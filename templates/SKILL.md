---
name: pixelforge
description: Make pixel art game characters, monsters, bosses, NPCs, combat animations, spell and attack effects, and spritesheets using the pixelforge tool, in its locked tiny chibi style, with combat data (hitboxes, events, telegraph timing) exported for the game. Use this skill whenever the user asks for a sprite, a hero or class, an enemy or monster, a boss, attack or spell animations, FX, a spritesheet, or new outfits, weapons or recolors, even if they don't mention pixelforge by name. Do not generate pixel art any other way for these games.
---

# pixelforge

pixelforge lives at: `REPLACE_WITH_ABSOLUTE_PATH_TO_PIXELFORGE_REPO`

It builds characters by layering parts onto shared base animations, recoloring with material ramps, auto-outlining, validating and exporting PNG spritesheets with Aseprite-format JSON.

## Before doing anything

1. Read `<repo>/CLAUDE.md`. Its rules apply here too.
2. For new art, also read `<repo>/docs/STYLE_GUIDE.md` and the relevant part of `<repo>/docs/ANIMATION_SPEC.md`.
3. Run `pf --help` from the repo to see current commands.

## Making a character from existing parts

1. List parts and presets: browse `<repo>/parts/` and `materials` in `<repo>/style/style.json`.
2. Write a recipe in `<repo>/characters/<name>.yaml` (see `characters/knight.yaml`).
3. `pf build <name>`, then `pf validate`.
4. `pf review <name>` and open `turnaround.png`, `vs_anchor.png` and the 1x strip. Describe what you see before judging it.
5. Copy `out/<name>/<name>.png` and `<name>.json` into the current game project's asset folder (ask where if unclear).

## Monsters and combat

- Monsters use rigs (`rig:` in the recipe) and the `enemy`, `elite` or `boss` timing profile. Read `<repo>/docs/MONSTERS.md` before designing one and `<repo>/docs/COMBAT.md` before any attack, spell or FX work.
- A new monster type that needs a new rig is a big job: write its spec in MONSTERS.md first and get the user's approval on the silhouette before drawing.
- Copy the exported JSON along with the PNG; it carries events, hitboxes and root motion the game needs.

## When the character needs a part that doesn't exist

1. Tell the user which part is missing and ask before creating it, since new parts take real effort.
2. `pf template <slot> <variant> <anim>` for each animation, draw it against the guides, write `part.yaml`.
3. Follow the full review protocol in `<repo>/docs/QUALITY.md` until rubric scores are 4 or higher.
4. Show the user the review images and wait for approval.
5. Commit the new part to the pixelforge repo (not the game repo) so every game can use it.

## Rules

- Never resample, rotate, scale or antialias art. Only integer moves and mirroring.
- Only colors from `style.json`. New presets must pass `pf palette --check`.
- Never describe art as good without opening the review images first.
- `pf validate` must pass before copying anything into a game.
