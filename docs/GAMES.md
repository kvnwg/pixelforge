# Games

Notes on each game that uses pixelforge: what it needs, and which pixelforge decisions it drove. The core stays engine-agnostic; anything specific to one game lives here.

---

## Rolling Knight

Repo: https://github.com/kvnwg/rolling-knight (read at commit 72b26ae, 2026-11-05).

A real-time, top-down (3/4 view) pixel action roguelite with a slot-machine Summoning Altar that rolls knights. You field a squad of three knights in procedural dungeons, control one, and the other two fight by their class's AI. Knights auto-attack whatever is in range. Custom TypeScript canvas renderer (React UI, Vite), not Phaser or Godot.

### Decisions it drove

- **`combat.view = topdown`** (COMBAT.md section 0). Combat is real-time and knights turn to face what they attack: `face()` in `src/world/skills.ts` picks the `down`, `side` or `up` view from the aim vector. So attacks need S, E and N art, with W mirrored.

### What it needs from later phases

| Need | Rolling Knight today | pixelforge plan |
|---|---|---|
| Six knight classes | Guardian (great helm, flanged mace, kite shield), Blade (plumed sallet, sword), Ranger (hood, longbow), Cleric (mitre, holy staff), Arcanist (wizard hat, orb staff), Lancer (winged helm, lance with a pennant) | Phase 4 has great_helm, hood, sword, staff, bow and shield. Still to add: plumed sallet, mitre, wizard hat, winged helm, mace, lance |
| Dodges | roll (Guardian 0.26 s, Blade and Cleric 0.3 s), backflip (Ranger, 0.36 s), vault (Lancer, 0.36 s), blink (Arcanist, 0.2 s), in any direction | COMBAT.md only has a hop `dodge`. Phase 5 writes `roll`, `backflip` and `vault` specs before drawing them; blink can be FX plus a fade in the game |
| Attacks and rolls drawn, not rotated | the body plays idle or walk while the weapon sprite rotates toward the target in 22.5 degree steps; the roll rotates the whole knight in quarter turns (`src/render/renderer.ts`) | characters are never rotated (CLAUDE.md rule 1): attacks and rolls get drawn frames in S, E and N, and the game picks the direction from the aim vector's dominant axis |
| Rarity and mutation looks | rarity armor, capes from Epic, halos from Celestial, color cycling at Primordial; mutations Gilded, Shadow, Radiant and Void | presets (for example metal gold for Gilded), the `back` slot for capes, a halo part or FX; decide in Phase 4 |
| Mobs | built per floor: body plan, behavior (chaser, archer, charger, bomber, caster, tank, swarm), colors, size; poses idle, walk, wind (the tell) and strike; drawn from one front view and flipped left or right | rigs, presets and `pf random` (Phases 4, 7 and 8); `wind` maps to the windup phase with the enemy timing profile; monsters may need fewer directions than knights, decided per rig in Phase 7 |
| Bosses | three attacks each from ring, fan, charge, slam, summon and rain; enrage at half HP | Phase 9 boss spec |
| Walk speed | knights move at 50 to 64 px/s (`src/core/knights.ts`) | the humanoid walk's natural speed is about 19 px/s (10 px per 520 ms cycle), so at game speed the feet slide. Options: play the walk faster (frames down to about 90 ms, about 28 px/s, ANIMATION_SPEC.md section 5), or add the `run` animation listed in ANIMATION_SPEC.md section 9 with a longer stride; a run is the better fit and is recommended as the next locomotion addition |
| Size | knight frames are 22 x 19 (a 14 px body plus helmet) on a screen about 216 art px on its short side | pixelforge humanoids are 18 rows plus up to 2 of headwear: about the same size |
| Loading | custom canvas renderer | PNG spritesheet plus Aseprite JSON; the game needs a small loader (Phase 10 README) |

### Open question: palette

Rolling Knight's current sprites use their own bright palette (`src/render/pixel/palette.ts`: pure white, saturated reds and greens, a near-black outline `#1a1326`) under cinematic lighting with bloom. pixelforge characters are muted with a plum outline, and only FX are bright. Either the game's world art moves toward pixelforge's look, or Rolling Knight gets its own style folder (ARCHITECTURE.md section 19). Decide before Phase 2 locks the base body.
