# Motion: how pixelforge sprites should move

Why this exists: the v1 animations were correct but stiff. Every pose was a rigid block moved 1 px at an even beat, so idles toggled, walks trudged and strikes snapped. This document collects what good pixel animation does (with sources), translates it to pixelforge's scale (an 18 px tall humanoid on a 32 px canvas), diagnoses the v1 set, and sets the rules new and reworked animations follow. ANIMATION_SPEC.md and COMBAT.md hold the frame tables; this file holds the reasons.

## 1. What the references say

**Raymond Schlitter (Slynyrd), Pixelblog 52, idle fighting stance** ([link](https://www.slynyrd.com/blog/2024/9/26/pixelblog-52-idle-fighting-stance)): an 8-frame idle on a 48 x 92 sprite. "Everything is anchored to the steady motion of the torso", but parts move by different amounts at different times: the legs lead, the torso moves 1 px, the head sometimes holds level while the body moves, the hands move 2 to 4 px. Timing is uneven on purpose: frames 1 to 4 at 100 ms, 5 to 8 at 50 ms, which "accentuates the force of gravity by speeding up the downward motion, and subtly slowing the motion at the max height". Hair and cloth get "sub movements" added after the base bounce works. "Calling them 'idle' animations makes it sound like there's not much going on."

**Slynyrd, Pixelblog 50, human walk cycle** ([link](https://www.slynyrd.com/blog/2024/5/24/pixelblog-50-human-walk-cycle)): 8 frames "strikes a solid balance between economy and fluidity"; 4 frames "highlights the most important key frames... but feels somewhat lacking". The keys: contact (heel down, limbs at the extremes of their swing, the figure lowest), down (foot flat, the back foot lifts), pass (legs cross, the figure tallest), swing (the free leg reaches forward); frames 5 to 8 mirror them. The head's path should be a triangle wave: "If the head position across the sequence creates a perfect sine wave, the uniform motion feels a bit unnatural." Arms and legs on opposite sides "track along with shared momentum".

**Slynyrd, Pixelblog 8, intro to animation** ([link](https://slynyrd.com/blog/2018/8/19/pixelblog-8-intro-to-animation)): "The most important thing when creating a run cycle for a game is the energy of the motion"; playback speed changes that energy (8 frames at 80 ms against 4 at 160 ms). "Too many in-between frames can make your motion look sluggish", and keyframes "should be the most dramatic poses that capture the essence of the motion".

**Slynyrd, Pixelblog 56, top-down character attack** ([link](https://www.slynyrd.com/blog/2025/5/23/pixelblog-56-top-down-character-attack-animation)) and **Pixelblog 9, melee attacks** ([link](https://slynyrd.com/blog/2018/9/8/pixelblog-9-melee-attacks)): an attack is anticipation (1 frame, held "at various delay durations"), a smear spanning a few brief frames, a follow-through at "full extension... moving into the target 1 more pixel without any smear effects" held longer, then a 1-frame recover. Sword 100, 50, 50, 50, 100, 50 ms (400 ms); spear 200, 50, 50, 50, 150, 50; hammer 250, 50, 50, 50, 300, 100 with a rebound frame and screen shake. The same frames and timing in every direction, with each view's arc adjusted to balance the hitbox; never rotate the sprite. Smears follow "a natural path from stance to follow through", gain smoothness from "color gradation", and never sit on the anticipation or recover frames. Elongate the arm or weapon a little at full extent; after recovering, bounce the stance 1 px for one frame. "Totally realistic poses sometimes feel stiff in pixel form."

**Sub-pixel animation** (Bradley Oberg, [link](https://someanimatorwannabe.substack.com/p/animator-techniques-sub-pixel-animation); Tiny Warrior Games, [link](https://tinywarriorgames.com/2019/01/04/game-development-pixel-art-sub-pixel-animation/)): motion smaller than a pixel is shown by changing colors instead of moving pixels. Metal Slug's Fio (34 px tall) breathes by color shifting while her outline barely moves. It works best on larger sprites and on areas without key detail; within a locked palette it means moving a shading boundary (a light, mid or dark run) by a pixel while the silhouette stays put.

**Principles translated to pixels** (sprite-ai's guide, [link](https://www.sprite-ai.art/guides/animation-principles); follow-through and overlap, [link](https://rebusfarm.net/blog/follow-through-and-overlapping-action-the-animation-principle-that-prevents-stiff-motion)): spacing can't vary below a pixel, so easing is done with frame timing; follow-through needs pixels to show, so it grows with sprite size; secondary layers trail the main motion, but if every layer lags by the same amount it reads as technical lag, not overlap.

## 2. Rules for pixelforge

1. **Waves, not blocks.** A move travels through the body: legs or torso first, then the head a frame later, then the hands, then hair and cloth. At most one part changes per in-between frame on an 18 px sprite, so each frame is a small, readable step. Splitting the head from the torso needs the neck to stretch or compress a pixel; draw it.
2. **Ease with time.** Hold the extremes, rush the in-betweens. Durations within an animation should differ (a cycle with one flat duration reads mechanical); falls are faster than rises.
3. **Eight frames for cycles the player watches.** Walk and run get 8 frames (contact, down, pass, up, mirrored); idles get 6 to 8. Monsters seen in crowds may keep 4 to 6.
4. **Triangle bobs.** The head path rises and falls in steps of uneven length (low on contact and down, high on pass and up), never a symmetric sine.
5. **Overlap and follow-through.** Lagging parts (hair locks, capes, tails, ears) trail by a frame and overshoot by a pixel when the body stops or reverses, then settle. Not every layer lags the same amount.
6. **Attacks: anticipation, smear, follow-through, settle.** The windup holds (stretched further for enemies by the timing profiles); the strike crosses in 2 to 3 short frames with smears only on those frames; the follow-through reaches 1 px further than the strike and holds; the recover settles with a 1 px overshoot. Same frames and timing in s, e and n. Every swing's smear is a white trail (`fx_ramps.swing`) that lingers a shade dimmer on the follow-through, so even a 50 ms strike frame is seen.
7. **Sub-pixel where it pays.** On medium and larger sprites, breathing and slow drift can move shading runs instead of outlines. On the 32 px humanoid, prefer 1 px part offsets; a shading shift is allowed only when it keeps clusters clean (W3, W10).
8. **Exaggerate a little.** Elongate an arm or weapon by a pixel at full extent; push the anticipation pose further than real life.
9. **Target first.** Before drawing an animation, write down what it is meant to look like: the key poses (anticipation, action, hold, recovery) in words, the silhouette each must make at 1x, and what the move is in the game it serves (read the game's code). Sketch the key pose in a scratch grid and look at it before building the frames, then judge the build against the written target, not against "does it render" (section 6).

## 3. Diagnosis of v1

| Animation | v1 | Against the rules |
|---|---|---|
| humanoid idle | 4 frames, the upper body as one block down 1 px and back, 450/150 ms | no wave (rule 1), symmetric timing (rule 2) |
| humanoid walk | 4 frames, 130 ms each, arms in two states | 4 frames (rule 3), flat timing (rule 2), no head lag (rule 1) |
| humanoid run | none; Rolling Knight's knights move about three times the walk's natural speed, so its feet slide | rule 3 |
| attack_slash | anticipation, one smear frame, recovery in two steps | short strike, no follow-through reach or settle bounce (rule 6) |
| hair locks, capes | lag 1 frame, clamped to 1 px, no overshoot | rule 5 |
| monsters | redrawn squash and stretch (slime), wing beats, gaits | mostly sound; the ogre and goblin idles share the block problem |

## 4. Decisions made in Motion pass 1

- **Follow-through is the compositor's job.** Every `lags: true` part (hair locks, ponytails, back hair, the wolf's tail) takes its anchor's position now and up to three frames ago: 1 px behind while the anchor moves, caught up when it stops, 1 px past it a frame later, then settled. A once-through animation's held last frame never overshoots (it would hang there). Nothing has to be drawn per part.
- **The idle wave moves three things, one at a time:** chest, head, hands (ANIMATION_SPEC.md section 3). Splitting the head from the chest needs a neck that stretches by a row; facing n that row is drawn dark (the head's shadow on the nape), because a doubled row of bare back read as a slab (W5).
- **Arms swing in phase with the legs:** at their extremes on the contact frames and through the rest pose as the legs cross. An earlier draft lagged them 1.5 frames behind the legs, which read as the arms dragging; a one-frame lag is the most overlap a 4-key step can take.
- **The dip absorbs the reach.** Facing s and n a forward hand reaches 1 px lower; on the down frames the body's drop takes that pixel instead, so a sword hanging from the hand never leaves the canvas.
- **The planted leg keeps its foot rows.** As the body sinks onto it the thigh row disappears and as it rises the thigh row doubles; the sole is the same pixels from contact to up (W1), even on a recolor that cleans up single pixels (the skeleton).
- **The free leg changes shade as it travels:** mid lifting back, dark passing behind, mid swinging forward, light once planted. This keeps the near and far legs apart without a fourth leg shade.
- **The run's speed comes from the game.** Rolling Knight's knights move about 54 px/s at 1x; the walk's natural speed is 17 px/s. Stretching the walk to that speed would slide its feet, so the run is its own 8-frame cycle with 4 px strides that match (GAMES.md).
- **The random characters were redrawn.** One random recipe went over the 16-color budget when the new up frame showed a third leggings shade under its robe; `pf random --seed 1 --count 12` (which redraws until every idle and walk frame fits) replaced the set. Recipes are generated, so this changes examples, not art.

## 5. Plan and status

| Step | Status |
|---|---|
| This document | done |
| Engine: lagging parts trail, catch up, overshoot by a pixel and settle (rule 5) | done (Motion pass 1) |
| Humanoid idle: 6-frame wave (chest, head, hands), gravity timing | done (Motion pass 1) |
| Humanoid walk: 8 frames, triangle bob, arms in phase with three reach states | done (Motion pass 1) |
| Humanoid run: 8 frames with flight frames, lean and arm pump, tuned to Rolling Knight's speed; in every humanoid player and monster recipe (orc, skeleton) | done (Motion pass 1) |
| Preview walk test: walk or run at each gait's natural speed | done (Motion pass 1) |
| attack_slash and attack_heavy: two-frame strike, follow-through reach, settle bounce | done (target-first pass: the Cleave and the Whirlwind) |
| The wolf's howl: the head arched back to the sky | done (target-first pass) |
| combat_idle, monsters' idles (goblin, ogre; the orc and skeleton inherit the humanoid's) | next |

## 6. Target-first pass (2026-11-05)

The human found three animations wrong: "attack heavy just slams his sword on the ground", "even the slash itself isn't dramatic enough" and "wolf howl is terrible, it should arch his head up to the sky", and asked whether the target was understood before anything was generated. It was not. Poses were typed as grids and offsets, rendered, and judged by whether they validated and looked clean, never against a written picture of the move. A howl that only lifts the head a pixel validates fine. Rule 9 came out of this.

How each one was redone:
- **Wolf howl** (MONSTERS.md section 5.2). Target: the head arches back until the snout points at the sky. The first sketch, a sitting howl, read as a bear at 1x because the legs vanished into the body. The standing version (chest lifted over braced front legs, the neck stretched, the snout straight up) kept the wolf readable and was chosen. Scratch sketches came before the art script.
- **Heavy attack** (COMBAT.md). Reading Rolling Knight's code showed the Blade's special is Whirlwind, a 2 s channelled spin, so the heavy became that spin. The target named what must read at 1x (the ring and the turning body), and the engine gained frames drawn from another view to make it possible (ARCHITECTURE.md section 21).
- **Slash** (ANIMATION_SPEC.md section 6). Target: a coil you can't miss, a two-frame strike with the blade a blur on the first, a crescent wider than the body and a step into it. It also matches the game's Cleave ("a wide arc").
