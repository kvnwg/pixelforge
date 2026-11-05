# Combat

Combat art has a job beyond looking good: it has to tell the player what is about to happen, exactly when it happens, and what it hit. This doc covers the combat animation set for humanoids, the gameplay data exported with it (phases, events, hitboxes, root motion), timing rules for telegraphs, and the FX library. Monster-specific combat animations are in MONSTERS.md and follow the same rules.

`style/examples/battle_mock_6x.png` shows the intended look: muted characters, bright FX.

---

## 0. First decision: combat view

Set `combat.view` in `style/style.json` during Phase 0. It decides which directions combat animations are drawn in.

| View | Combat directions drawn | Typical game | Art cost |
|---|---|---|---|
| `side` | `e` only (`w` mirrored) | turn-based or auto-battle scenes where units face each other, usually with a top-down overworld for exploring | 1x |
| `topdown` | `s`, `e`, `n` (`w` mirrored) | real-time action where you attack in the direction you face | about 3x |

Locomotion (idle, walk) stays 4-directional either way. With `side`, every combat animation below is drawn once, which lets each one get more frames and polish for the same effort.

**Decision (Phase 0): `topdown`.** Rolling Knight, the first game using pixelforge, is a real-time top-down action game whose knights turn to face what they attack in down, side and up views (see GAMES.md). Going from `side` to `topdown` later would only have added the S and N rows, but the game needs them, so combat is drawn in `s`, `e` and `n` from the start. Monster rigs may still need fewer directions than knights; that is decided per rig in Phase 7.

---

## 1. Anatomy of an attack

Every attack has three phases, and every frame belongs to exactly one:

| Phase | Purpose | Rules |
|---|---|---|
| **windup** | the tell: shows what's coming and from where | a distinct pose, readable at 1x; includes at least one `hold` frame; for enemies, long enough to react to (section 2) |
| **active** | the hit: when damage can happen | 1 to 2 frames, short (50 to 80 ms each); hitboxes only exist here; a smear or impact FX makes it unmistakable |
| **recovery** | the aftermath: vulnerability, follow-through | at least as long as the active phase, usually 2 to 3 times longer; this is the punish window for enemy attacks |

Phases are declared per frame in the animation definition and exported, so the game can use them (for example, interrupting an enemy during windup).

---

## 2. Timing profiles and telegraphs

The same art serves player characters and enemies, with different timing. Each recipe sets `timing_profile`:

| Profile | Windup-to-hit minimum | Hold frame scale |
|---|---|---|
| player | none | 1.0 |
| enemy | 300 ms | 1.7 |
| elite | 350 ms | 1.8 |
| boss | 500 ms (heavy attacks: aim for 600+) | 2.2 |

How it works: frames flagged `hold` in the animation definition are multiplied by `hold_scale`; then, if the time from the first windup frame to the `hit` event is still under the minimum, the last hold frame is extended until it meets it. Player attacks stay snappy; enemy attacks become readable without redrawing anything.

Telegraph rules:

- The windup pose must differ clearly from `combat_idle` (the validator warns if the silhouette changes by less than 8%).
- Enemy tells should involve the whole body (a crouch, a rear-back, a squash), not just the weapon.
- Optional tell FX: a 1 to 2 frame glint on the weapon or a flash of glow eyes at the start of the hold. Never cover the tell pose with FX.

---

## 3. Humanoid combat set

Specced for `e`. For `topdown`, S and N versions follow the same frames with the motion turned toward or away from the camera (forward motion in S is `(0, +1)`, in N is `(0, -1)`).

Notation as in ANIMATION_SPEC.md: upper offset is relative to idle frame 0. "Root motion" is how far the game should move the character's position, exported as data. Moves bigger than 1 to 2 px happen through root motion, never by drawing the character off-center.

Required for v1: `combat_idle`, `attack_slash`, `shoot_bow` or `cast` (per class), `hurt`, `death`, `victory`. Optional depending on the game: `attack_heavy`, `block`, `dodge`, `stun`.

### combat_idle (loop)

| Frame | ms | Pose |
|---|---|---|
| 0 | 300 | ready stance: feet apart (front foot 2 px ahead of the pivot, back foot 2 px behind), knees bent so upper offset is (0, +1), weapon raised in front |
| 1 | 150 | upper (0, +2), hair lags |
| 2 | 300 | upper (0, +2), hair catches up |
| 3 | 150 | upper (0, +1), hair lags |

Distinct from the relaxed idle: wider stance, lower center, weapon up. At 1x, "ready to fight" should read immediately.

### attack_slash

This is the attack from ANIMATION_SPEC.md section 6.

| Frame | ms | Phase | Notes |
|---|---|---|---|
| 0 | 120 | windup (hold) | lean back (-1, 0), weapon up and back |
| 1 | 80 | windup (hold) | coil (-1, +1), weapon 1 px further back |
| 2 | 60 | active | lunge (+1, 0), weapon extended, smear; `hit` |
| 3 | 140 | recovery | follow-through, weapon low and forward |
| 4 | 160 | recovery | return toward combat_idle; `recover` |

Hitbox on frame 2: covers the smear and blade, roughly 10 x 12 px in front of the body.

### attack_heavy (overhead smash)

| Frame | ms | Phase | Notes |
|---|---|---|---|
| 0 | 140 | windup | weapon lifted overhead, body stretches up (upper (0, -1)) |
| 1 | 120 | windup (hold) | lean back (-1, -1), weapon behind the head: the big tell |
| 2 | 80 | windup (hold) | peak squash (-1, +1) |
| 3 | 50 | active | weapon slams down in front, vertical smear; `hit` |
| 4 | 60 | active | weapon on the ground, `vfx impact_big` at the weapon tip |
| 5 | 160 | recovery | weapon stuck low, body bent (0, +1) |
| 6 | 200 | recovery | heave back to combat_idle; `recover` |

### shoot_bow

| Frame | ms | Phase | Notes |
|---|---|---|---|
| 0 | 100 | windup | nock: arrow appears on the string |
| 1 | 120 | windup | draw: draw hand pulls back 2 px, bow arm extended |
| 2 | 200 | windup (hold, charge loop) | full draw, aim; can loop for charged shots |
| 3 | 60 | active | release: string snaps forward, `spawn arrow` at the nock point |
| 4 | 120 | recovery | recoil (-1, 0) |
| 5 | 140 | recovery | lower the bow; `recover` |

### cast

| Frame | ms | Phase | Notes |
|---|---|---|---|
| 0 | 120 | windup | raise the hand or staff |
| 1 | 120 | windup | gather: `vfx gather_glow` at the hand |
| 2 | 160 | windup (hold, charge loop) | channel; the glow FX loops here |
| 3 | 80 | active | release: thrust forward 1 px, `spawn` the spell at the hand point |
| 4 | 140 | recovery | hold the release pose |
| 5 | 160 | recovery | lower; `recover` |

The spell itself (projectile or area effect) comes from the FX library; the cast animation is the same for every element.

### block (three animations)

- `block_enter` (60, 80 ms): weapon or shield comes up, body turns slightly (front foot +1 px).
- `block_hold` (loop, 300, 300 ms): held guard with a 1 px breath.
- `block_impact` (60, 120 ms): pushed back 1 px, `vfx spark_small` at the shield or weapon front, then settle.

### dodge

| Frame | ms | Notes | Root motion (x, away from the facing direction) |
|---|---|---|---|
| 0 | 60 | crouch (0, +1) | 0 |
| 1 | 80 | airborne hop, legs tucked, shadow shrinks; flagged `airborne` | -4 |
| 2 | 80 | land squash (0, +1) | -3 |
| 3 | 100 | recover | -1 |

### hurt, death

As in ANIMATION_SPEC.md sections 7 and 8. Knockback beyond 1 px is root motion. Add `hurt_heavy` (knockdown and get up, about 6 frames) later if the game needs it.

### stun (loop)

Four 150 ms frames swaying the upper body (-1, 0), (0, 0), (+1, 0), (0, 0), eyes closed, with the `status_stun` FX overlay (circling stars) attached above the head.

### victory (loop)

| Frame | ms | Pose |
|---|---|---|
| 0 | 200 | squash (0, +1), weapon lowered |
| 1 | 150 | hop: upper (0, -2), legs tucked, weapon raised high; `airborne` |
| 2 | 200 | land squash (0, +1) |
| 3 | 300 | proud stance, weapon up |

### Rolling Knight dodges: roll, backflip, vault

Rolling Knight dodges in any direction, so these are drawn in s, e and n like the attacks and the game picks the row from the dodge vector's dominant axis. Never rotated: the game's current quarter-turn roll becomes drawn frames. Root motion is in px along the facing (negative is backward); the game sets the real distance and may scale it.

**roll** (Guardian, Blade, Cleric): a tucked crouch-dash forward. A real somersault would need the head and helmet drawn upside down, which rigid parts can't do, so the knight balls up and shoots forward and the motion plus a dust puff sell it.

| Frame | ms | Pose | Root motion |
|---|---|---|---|
| 0 | 50 | crouch, leaning forward (head 1 px ahead of the torso); `vfx dust_puff` at `foot_near` | 4 |
| 1 | 80 | balled up: torso down 3 px, head down 1 more, knees out, weapon tucked | 14 |
| 2 | 80 | balled up (held) | 16 |
| 3 | 70 | crouch, rising | 14 |
| 4 | 60 | recover to the ready stance | 6 |

**backflip** (Ranger): spring up and back.

| Frame | ms | Pose | Root motion |
|---|---|---|---|
| 0 | 60 | crouch | 0 |
| 1 | 90 | airborne 3 px up, leaning back, arms up, legs tucked | -20 |
| 2 | 90 | airborne 4 px up, fully tucked (the peak) | -26 |
| 3 | 90 | land in a crouch | -20 |
| 4 | 90 | recover | -8 |

**vault** (Lancer): spring forward over the planted lance.

| Frame | ms | Pose | Root motion |
|---|---|---|---|
| 0 | 60 | crouch, leaning forward, lance couched | 0 |
| 1 | 90 | airborne 3 px up, the lance raised high | 20 |
| 2 | 120 | airborne 4 px up, legs swung forward under the body | 30 |
| 3 | 90 | land in a crouch | 20 |

The Arcanist's blink is FX plus a fade in the game; it uses `dodge` as its drawn fallback.

### Decisions made while drawing the set (Phase 5)

- **combat_idle bobs between 0 and +1**, like idle, instead of +1 and +2: the humanoid's legs are 3 rows, and +2 leaves one row, which reads as a squat at 1x. The wide stance and the raised weapon carry "ready".
- **Facing s and n, swings happen on the weapon side.** The weapon arm is on the viewer's left facing s and the right facing n, so the windup raises the weapon beside the head and the strike chops down past the body on that side, with the smear running down that side. A swing across the front would be hidden by the body facing n and would cover it facing s.
- **Weapon poses are drawn per item** (`ready`, `raised`, `strike`, `low`, `overhead`, `back`, `slam`, `ground`, `aim`, `draw`, `release`, `guard`, `tuck`, `high`, `dropped`); the base body's frames name the pose each held item takes (anchors.json `pose`). An item with no drawing for a pose falls back to its rest cell. Swords and maces share one geometry; staffs, lances and bows have their own. A weapon cocked behind the head is drawn behind the character (a `_behind` cell) so only the part sticking out shows.
- **Unarmed** characters hold the `fist` (the humanoid rig's default `held_near`): no art, only accent-light smears (a crescent burst in front of a punch, an arc over a hammer fist), reach hitboxes and the fist as `weapon_tip`.
- **block** works with or without a shield: a shield is raised in front (it rides the torso, so it never swings off the body); a weapon is held upright in front as a parry.
- **cast** is the same body animation for every caster; a staff is raised then thrust forward, other items do what their poses say.
- **hurt** keeps the weapon up (`ready`) while the body is knocked back, so a long item never swings off the canvas.
- **death ends in a slumped kneel** (ANIMATION_SPEC.md section 8).

---

## 4. Hitboxes and hurtboxes

- **Hurtbox** (where this character can be hit): generated automatically for every frame as the body's bounding box inside its outline (the silhouette inset by 1 px), leaving out held items and smears. Can be overridden per animation.
- **Hitbox** (where this attack deals damage): authored rectangles, only on `active` frames. For weapon attacks they live with the held item part, per pose (`parts/held_near/sword/hitboxes.json`), so a spear and a dagger can share the same body animation with different reach. Unarmed humanoids get theirs from the `fist`; monster attacks author them on the rig.
- Coordinates are pixels in the frame's canvas. In `hitboxes.json` they are in idle-hand coordinates, like the item's cells: the compositor moves them with the hand and clips them to the canvas.
- Facing e a hitbox covers the weapon and its smear. Facing s and n it also reaches toward the target (below the feet facing s, above the head facing n), since a top-down game resolves hits in front of the attacker.
- Attacks whose hit is a `spawn` (bow, spells) have no hitbox: the projectile carries the hit.

```json
{
  "hitboxes": { "strike": { "s": [[6, 11, 16, 21]], "e": [[15, 12, 9, 15]], "n": [[9, 3, 16, 27]] } },
  "points":   { "strike": { "weapon_tip": { "s": [8, 28], "e": [21, 25], "n": [22, 28] } } }
}
```

The preview shows hitboxes (red) and hurtboxes (blue) as overlays, and `pf review` draws them on the timeline image.

---

## 5. Events

| Type | Meaning | Data |
|---|---|---|
| `windup` | the attack has started (the tell begins) | |
| `active_start` / `active_end` | damage window; derived automatically from the phases | |
| `hit` | the damage moment, used for hit stop and sounds | |
| `spawn` | create a projectile or spell | `fx`, `point` (anchor name or pixel), optional `angle` in multiples of 90 |
| `vfx` | play an effect that isn't a projectile | `fx`, `point`, `layer` (above or below) |
| `sfx` | sound cue name, for the game to map | `name` |
| `impact` | a projectile or slam landed | |
| `footstep` | for sounds and dust puffs | `foot` (near or far) |
| `recover` | the character can act again | |
| `cancel` | from this frame the game may cancel into another action | |

Required: every attack has `windup`, `hit` (or `spawn` for ranged), and `recover`. Points must be within 3 px of a hand anchor or a held item's tip.

Named points come from the rig's anchors (`hand_near`, `foot_near`, `shield_front`...) and from the held items' poses (`weapon_tip`, `bow_nock`, `shield_front`). The export resolves them per frame: an event with `"point": "weapon_tip"` is written as `"point": [25, 26], "point_name": "weapon_tip"`.

Export (in the JSON `meta.pixelforge` block):

```json
"events": {
  "attack_slash_e": [ {"frame": 0, "type": "windup"},
                      {"frame": 2, "type": "hit"},
                      {"frame": 4, "type": "recover"} ],
  "cast_e": [ {"frame": 3, "type": "spawn", "point": [21, 18]} ]
},
"phases": { "attack_slash_e": ["windup", "windup", "active", "recovery", "recovery"] },
"hitboxes": { "attack_slash_e": { "2": [ {"x": 17, "y": 13, "w": 11, "h": 13} ] } },
"hurtboxes": { "attack_slash_e": { "0": [ {"x": 11, "y": 11, "w": 9, "h": 16} ] } },
"root_motion": { "dodge_e": [0, -4, -3, -1] },
"holds": { "attack_slash_e": [0, 1] },
"base_durations": { "attack_slash_e": [120, 80, 60, 140, 160] },
"timing_profiles": { "enemy": {"telegraph_min_ms": 300, "hold_scale": 1.7} }
```

Frame durations in the sheet are already retimed for the recipe's profile; `holds`, `base_durations` and `timing_profiles` let a game (or the preview) retime the same art for another profile with the rule in section 2.

---

## 6. FX library

FX are their own assets in `fx/<name>/`, reused by every character: `fx.yaml` plus one sheet per animation, cells sized to the effect (16, 24, 32 or 48 px square).

### FX art rules

- Colors only from `fx_ramps` in `style.json`: fire, ice, poison, arcane, holy, shadow, impact. FX are the only art allowed to go brighter (L up to 0.93) and more saturated (C up to 0.14) than characters. That contrast is the point: tells and hits pop against the muted cast.
- Hard pixels, binary alpha, no gradients. Light is suggested with ramp steps, never transparency.
- No outline by default. Projectiles may get a 1 px rim in their ramp's darkest shade if they disappear against light backgrounds.
- Short and snappy: 3 to 8 frames at 40 to 80 ms.
- Authored facing east. West is mirrored. FX (and only FX) may also be rotated in exact 90-degree steps for other directions, since that's lossless on a pixel grid. 45-degree versions must be drawn by hand. Characters are never rotated, because their lighting would be wrong.
- `fx.yaml` declares the pivot, whether it loops, whether it's drawn above or below characters, and whether it follows the character or stays in the world.

### v1 set

| Category | Effects | Notes |
|---|---|---|
| Smears | `smear_arc` (slash), `smear_vertical` (overhead), `smear_thrust` | 1 frame each, matched to attack_slash, attack_heavy, thrust |
| Impacts | `spark_small` (4 frames, about 9 px), `impact_big` (6 frames, about 17 px, with a 2 to 3 px dust ring), and one elemental impact per element | neutral impacts use the `impact` ramp |
| Projectiles | `arrow`, `fireball`, `ice_shard`, `poison_glob`, `arcane_orb` | each has `travel` (loop, 2 to 4 frames) and `impact` (4 to 6 frames) |
| Casting | `gather_glow` (loop, 3 frames, at the hand), one tint per element | |
| Status overlays | `status_burn`, `status_poison`, `status_freeze`, `status_stun`, `status_sleep`, `status_shield` | loops attached to the head or body anchor; small (stun stars orbit 9 to 11 px wide above the head) |
| Death | `poof_smoke`, `soul_wisp`, `bone_crumble` | monsters mostly use these instead of lying bodies |
| Support | `heal_sparkle`, `buff_up`, `debuff_down` | |

`style/examples/battle_mock_6x.png` includes a draft fireball travel frame (10 x 5 px, fire ramp, no outline) next to the anchor and a draft slime.

---

## 7. Feedback the game should add

These are engine-side, not pixelforge's job, but the art is timed assuming them:

- **Hit stop:** freeze both attacker and target for 50 to 90 ms on `hit` (longer for heavy attacks). Makes 1-frame strikes feel powerful.
- **Flash:** the target plays hurt frame 0 (the flash) on the same tick as the hit.
- **Knockback:** from root motion, 2 to 6 px depending on the attack.
- **Screen shake:** 1 to 2 px for heavy hits only.
- **Damage numbers:** a small pixel font, using the impact ramp for normal hits and fire's lightest shade for crits.

---

## 8. Combat readability rules

- Characters stay muted; FX and glow eyes carry the brightness. Never make a character brighter to make it "pop".
- An enemy's tell must be visible for the full telegraph time; FX never cover it.
- Different enemies need different silhouettes (MONSTERS.md section 7), not just different colors.
- Allies and enemies should be distinguishable at a glance. Glow eyes are reserved for enemies by default.
- At 1x, a player who has never seen an attack should be able to guess when it will land.

---

## 9. Combat review

In addition to the standard review images:

- `pf review <recipe> --combat` adds `<anim>_<dir>_timeline.png`: frames laid out with widths proportional to duration, phases colored (windup amber, active red, recovery gray), events as markers, hitboxes and hurtboxes drawn.
- `pf battle <attacker> <defender> --anim <attack>` renders `battle_<a>_vs_<b>.png`: the attacker's frames with the defender reacting on the hit frame and FX at their spawn and impact points, at 1x and 4x. This is the closest a still image gets to how the fight will feel.
- The human judges actual timing in the preview, which plays the attack against a target dummy with hit stop applied.

Built in Phase 5: the timeline and battle renders, and the preview's Arena view (`#arena`): a fighter attacks a training dummy, `hit` freezes both for 70 ms (90 ms for `attack_heavy`), the dummy flashes and is knocked back 1 px, `spawn` launches a projectile, and a profile toggle (player, enemy, elite, boss) retimes the attack. Sparks and projectiles are placeholders in the `impact` and `arcane` FX ramps until the Phase 6 library; the dummy is a preview prop, not exported art.
