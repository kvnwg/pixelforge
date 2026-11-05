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
| Six knight classes | Guardian (great helm, flanged mace, kite shield), Blade (plumed sallet, sword), Ranger (hood, longbow), Cleric (mitre, holy staff), Arcanist (wizard hat, orb staff), Lancer (winged helm, lance with a pennant) | Done in Phase 4: `characters/rolling_knight/rk_guardian.yaml` and the other five, built from great_helm, sallet + plume, hood, mitre, wizard_hat, winged_helm, mace, sword, bow, staff + orb, lance + spearhead and shield. The lance has no pennant yet (one trim slot per held item) |
| Dodges | roll (Guardian 0.26 s, Blade and Cleric 0.3 s), backflip (Ranger, 0.36 s), vault (Lancer, 0.36 s), blink (Arcanist, 0.2 s), in any direction | Done in Phase 5: `roll` (340 ms), `backflip` (420 ms) and `vault` (360 ms) drawn in s, e and n with root motion (COMBAT.md section 3); the game can scale their durations to its dodge times. Blink stays FX plus a fade; the Arcanist has `dodge` as a drawn fallback |
| Attacks and rolls drawn, not rotated | the body plays idle or walk while the weapon sprite rotates toward the target in 22.5 degree steps; the roll rotates the whole knight in quarter turns (`src/render/renderer.ts`) | Done in Phase 5: attacks, blocks, casts and dodges have drawn frames in s, e and n (w mirrored); the game picks the row from the aim vector's dominant axis. Each class lists the animations its kit uses: Guardian and Blade slash, heavy, block and roll; Ranger shoot_bow, backflip and dodge; Cleric cast and roll; Arcanist cast and dodge; Lancer slash (a thrust with the lance) and vault; all of them combat_idle, hurt, stun, death and victory |
| Combat data | auto-attacks in range; knights and mobs need hit timing | Every attack exports phases, events (`hit`, `spawn` with the nock or hand point, `vfx`), hitboxes on active frames, hurtboxes and timing profiles (COMBAT.md sections 4 and 5). Mobs use the `enemy` profile (at least 300 ms of tell); `knight_enemy` shows the knight's kit as a foe |
| Rarity and mutation looks | rarity armor, capes from Epic, halos from Celestial, color cycling at Primordial; mutations Gilded, Shadow, Radiant and Void | presets (for example metal gold for Gilded), the `back` slot for capes, a halo part or FX; decide in Phase 4 |
| Mobs | built per floor: body plan, behavior (chaser, archer, charger, bomber, caster, tank, swarm), colors, size; poses idle, walk, wind (the tell) and strike; drawn from one front view and flipped left or right | rigs, presets and `pf random` (Phases 4, 7 and 8); `wind` maps to the windup phase with the enemy timing profile; monsters may need fewer directions than knights, decided per rig in Phase 7 |
| Bosses | three attacks each from ring, fan, charge, slam, summon and rain; enrage at half HP | Phase 9 boss spec |
| Walk speed | knights move at 50 to 64 px/s (`src/core/knights.ts`) | the humanoid walk's natural speed is about 19 px/s (10 px per 520 ms cycle), so at game speed the feet slide. Options: play the walk faster (frames down to about 90 ms, about 28 px/s, ANIMATION_SPEC.md section 5), or add the `run` animation listed in ANIMATION_SPEC.md section 9 with a longer stride; a run is the better fit and is recommended as the next locomotion addition |
| Size | knight frames are 22 x 19 (a 14 px body plus helmet) on a screen about 216 art px on its short side | pixelforge humanoids are 18 rows plus up to 2 of headwear: about the same size |
| Loading | custom canvas renderer | PNG spritesheet plus Aseprite JSON; the game needs a small loader (Phase 10 README) |

### Open question: palette

Rolling Knight's current sprites use their own bright palette (`src/render/pixel/palette.ts`: pure white, saturated reds and greens, a near-black outline `#1a1326`) under cinematic lighting with bloom. pixelforge characters are muted with a plum outline, and only FX are bright. Either the game's world art moves toward pixelforge's look, or Rolling Knight gets its own style folder (ARCHITECTURE.md section 19). Decide before Phase 2 locks the base body.
