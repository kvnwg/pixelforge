# Style Guide

Everything here was measured from `style/anchor.png`. The original reference was a screenshot at roughly 4x zoom with blurred edges; it was snapped back to its true pixel grid and 9 blended pixels were mapped to the real palette. `style/anchor_original_screenshot.png` is kept for comparison, and `style/anchor_annotated.png` shows the measurements below drawn on the sprite.

Coordinates are in the 32x32 canvas: x goes right, y goes down, (0,0) is top-left.

When this guide and the anchor disagree, the anchor wins. When a new design question comes up that neither answers, choose whatever keeps the silhouette readable at 1x and the look closest to the anchor, and record the decision here.

---

## 1. The style in one paragraph

Tiny chibi characters for a cozy top-down RPG, seen from slightly above (low top-down, about 3/4). About 11 px wide and 18 px tall, with a huge head (10 of the 18 rows). Muted, warm, low-saturation colors with no black and no white. A dark plum outline wraps the outer edge with rounded corners. Shading is minimal: two or three tones per material in flat clusters, no gradients, no dithering. The face is just two single-pixel eyes. A soft translucent shadow sits under the feet.

---

## 2. Pixel map of the anchor

```
x:      890123456789012
               ^            (x = 15, pivot column)
y= 9:   ...............
y=10:   ....OOOOOOO....
y=11:   ...OijjjjjiO...
y=12:   ..OijjjjijjiO..
y=13:   ..OijjjjijjiO..
y=14:   ..OiijjjiijiO..
y=15:   ..OhiijuuiihO..
y=16:   ..OhhuuuuuhhO..
y=17:   ..OhjjuuujjhO..
y=18:   ..OtueuuueutO..
y=19:   ...OsuuuuusO...
y=20:   ..OcdsssssddO..
y=21:   ..OccddddduuO..
y=22:   ..OscdddddtuO..
y=23:   ..OtcdddddtuO..
y=24:   ..OOGGgddcgOO..
y=25:   ...ONMgGGgMO...
y=26:   ...ONNLO~OO~...
y=27:   ..~ONNLO~~~~~..
y=28:   ..~~~~~~~~~~~..
y=29:   ...~~~~~~~~~...
```

Legend:

| Char | Material shade | Hex |
|---|---|---|
| `O` | outline | #3a263a |
| `h` `i` `j` | hair dark / mid / light | #735b51 / #826b5e / #957e6d |
| `s` `t` `u` | skin shadow / mid / light | #9f6f65 / #c08d80 / #dba292 |
| `c` `d` | cloth dark / mid | #4c445a / #5a556b |
| `e` | eyes | #5a556b |
| `g` `G` | accent dark / light | #bc8f5f / #d2ab70 |
| `L` `M` `N` | leather dark / mid / light | #5e494c / #735b51 / #826b5e |
| `~` | ground shadow (outline color, alpha 70) | #3a263a @ 27% |
| `.` | transparent | |

---

## 3. Canvas, pivot and proportions

| Measure | Value |
|---|---|
| Canvas | 32 x 32 |
| Sprite bounding box | x 10..20, y 10..27 (11 x 18 px) |
| Pivot | (15, 27): bottom center, on the feet baseline |
| Head (including outline) | rows 10..19, 10 rows, 11 px wide at its widest |
| Collar line | row 20: one row of skin shadow under the chin |
| Torso and arms | rows 20..24, 11 px wide including the arms |
| Belt / sash | rows 24..25 |
| Legs and feet | rows 25..27 |
| Eyes | (13, 18) and (17, 18): 1 px each, 3 px gap between them |
| Ground shadow | rows 26..29, centered on x = 15 (see section 9) |

These measurements are for the humanoid rig in the small size class. Monsters, other body plans and bigger size classes are defined in MONSTERS.md, and every other rule in this guide (palette, outline, shading, shadow, face) applies to them unchanged.

Head to body ratio is 10:8, so the head is about 55% of the height. This ratio is the single most important thing to preserve. Proportion drift (heads shrinking in side views, legs getting longer in walk frames) is the most common way this style breaks.

Rules:

- Head height stays 10 rows in every direction and every frame, except frames explicitly flagged as squash (hurt, death).
- Standing height stays 18 rows. Headgear may add at most 2 rows above row 10.
- In S and N views, nothing except held items and effects is wider than the head (11 px).
- All art stays inside x 2..29 and y 2..30 so effects and outlines never clip the canvas.

Stance: the viewer-left foot is planted on the baseline (row 27) and the viewer-right foot is set back one pixel higher (row 26, drawn as two outline-colored pixels). This relaxed, weight-on-one-leg stance is the idle base pose, and the anchor is exactly `idle_s` frame 0.

---

## 4. Palette

| Name | Hex | OKLCH (L, C, h) | Role |
|---|---|---|---|
| outline | #3a263a | 0.301, 0.045, 327 | outer outline, darkest value, hand-placed dark details |
| cloth_dark | #4c445a | 0.403, 0.038, 301 | clothing shadow side |
| cloth_mid | #5a556b | 0.463, 0.036, 295 | clothing base |
| leather_dark | #5e494c | 0.428, 0.029, 9 | boots, leg shadow |
| hair_dark | #735b51 | 0.492, 0.035, 44 | hair framing the face, leg mid |
| hair_mid | #826b5e | 0.546, 0.035, 51 | hair strands, center part, leg light |
| hair_light | #957e6d | 0.610, 0.038, 58 | top of hair (catches light) |
| skin_shadow | #9f6f65 | 0.588, 0.064, 32 | under chin, shadow-side arm |
| skin_mid | #c08d80 | 0.689, 0.065, 35 | cheeks, hands, mid planes |
| skin_light | #dba292 | 0.762, 0.072, 36 | face, lit arm |
| accent_dark | #bc8f5f | 0.682, 0.084, 67 | sash shadow, trims |
| accent_light | #d2ab70 | 0.763, 0.089, 77 | sash lit side |

Twelve colors total, plus the translucent ground shadow.

Rules for any new color (checked by the validator and by eye):

- Lightness (OKLCH L) between 0.30 and 0.80. The outline is the darkest value in any sprite. Nothing is near white, except the effect flash color in flash frames.
- Chroma (OKLCH C) at most 0.09. Most colors sit between 0.03 and 0.07. This low chroma is what makes the style feel soft and cozy.
- Shades within a ramp step by about 0.05 to 0.10 in L.
- Hue shifts warmer as shades get lighter: hair goes 44 to 51 to 58 degrees, accent goes 67 to 77. Use 3 to 10 degrees per step. Darker shades lean redder or cooler; lighter shades lean yellower.
- At most 16 colors in any single frame (the anchor uses 12).
- Never pure black (#000000) or pure white (#ffffff), anywhere.

How `pf palette --check` enforces these (decided in Phase 0; settings in `style.json` under `constraints`):

- **Errors** (block a build): L or C outside the limits, pure black or white, shades not ordered dark to light, a color darker than the outline. Limits get a tolerance of 0.002 (`limit_tolerance`), less than one hex step, because colors placed exactly on a limit (the slime gloss at L 0.80, the brightest fire at C 0.14) round slightly past it in 8-bit hex.
- **Warnings** (guidance for new presets): the lightness step (0.05 to 0.10, with 0.005 of slack) and the hue shift (+3 to +10 degrees per lighter step, the hue angle increasing). The hue rule is skipped for near-gray ramps (mean C under 0.02: steel, iron, silver), where hue is meaningless.
- **Accepted:** the anchor's own ramps break the hue guide (skin shifts only 1.5 to 2.6 degrees, the navy dress turns 6 degrees cooler, the leather's dark shade is redder than its hair browns). The anchor wins, so these, the fair and tan skins that copy the anchor's small skin shift, and ivory bone (0.1 degrees short) are listed in `accepted_ramp_warnings` with their reasons. A new preset must pass the guide or be added there with a reason; the tests fail otherwise.
- **Brighter limits:** glow eye presets (`materials.eyes.glow_presets`) use `glow_constraints` (L up to 0.85, C up to 0.14); FX ramps and the flash color use `fx_constraints` (L up to 0.93, C up to 0.14).

---

## 5. Materials and ramps

Every pixel belongs to exactly one material. Recoloring works by mapping a material's ramp (shade 0 = darkest) onto a preset ramp of the same length.

| Material | Shades (dark to light) | Used for |
|---|---|---|
| skin | #9f6f65, #c08d80, #dba292 | face, collar line, arms, hands |
| hair | #735b51, #826b5e, #957e6d | hair |
| cloth | #4c445a, #5a556b | dress, tunic, robes |
| leather | #5e494c, #735b51, #826b5e | legs, boots, straps |
| accent | #bc8f5f, #d2ab70 | sash, belt, trims, buckles |
| eyes | #5a556b | the two 1 px eyes |
| metal | 4 shades, steel preset | armor, helmets, blades (not in the anchor) |

Two traps found in the anchor:

1. **Eyes share a hex value with cloth_mid.** If eyes aren't their own material, recoloring the dress also recolors the eyes. Eyes are always a separate material.
2. **Leather shares hex values with hair.** The legs use the same three browns as the hair. If legs aren't their own material, dyeing the hair blonde also dyes the legs. Leather is always a separate material.

This is why parts carry their material explicitly instead of the system guessing from colors.

Presets live in `style/style.json`. They were generated by keeping lightness and chroma inside the rules above and rotating hue. `style/recolor_test_6x.png` and `style/recolor_test_1x.png` show eight combinations applied to the anchor (black hair with crimson cloth, blonde with forest, auburn with teal and tan skin, silver with plum and deep skin, mint with mustard, an orc with green skin, and more). All of them read as the same style, which is the test any new preset must pass.

---

## 6. Outline rules (verified against the anchor)

These three rules, applied to the anchor's non-outline pixels, reproduce the anchor's outline exactly. That reproduction is a unit test.

1. **4-neighbor ring.** A pixel is outlined if it is transparent and directly up, down, left or right of a silhouette pixel. Pixels that only touch the silhouette diagonally are not outlined. This is what gives the rounded corners (look at the top of the head: rows 10 and 11 step in).
2. **Open soles.** A ring pixel is left open when it touches the silhouette only from above (no silhouette pixel to its left, right or below) and its row is at or below the lowest sprite row minus 2. The ground shadow shows through there instead, under the feet and in the gap between the legs.
3. **Hand-placed outline pixels are preserved.** Outline-colored pixels drawn inside parts are kept as they are and do not count as silhouette when generating the ring. In the anchor these are the two hip tucks at (10, 24) and (20, 24) and the dark set-back foot at (17, 26) and (18, 26).

Other outline facts:

- One outline color, everywhere, always 1 px. No colored or selective outlines, no 2 px outlines, no doubled lines where parts meet.
- There are no inner outlines between materials. Arms, dress, face and hair are separated by color contrast only. The one place outline color appears inside the silhouette is the gap between the legs.

---

## 7. Light and shading

- Light comes from above and slightly from the viewer's right. The viewer-left side is the shadow side: in the anchor, the viewer-left arm uses skin shadow and skin mid while the viewer-right arm uses skin light and mid.
- Each material uses its mid shade as the base, the light shade on top-facing and right-facing planes, and the dark shade in creases, under overhangs and on the shadow side.
- Hair: the light shade dominates the top of the head, mid tone marks the center part and strands, dark tone sits at the sides where hair frames the face.
- The collar line (row 20, skin shadow under the chin) separates head from body. Never lose it; without it the head merges into the torso at 1x.
- Shades come in clusters of 2 px or more. Single isolated pixels of a shade are only for eyes and rare deliberate highlights.
- Forbidden: gradients, pillow shading (darkening every edge evenly), dithering on characters, banding (stair-stepped parallel lines of shades), antialiasing, semi-transparent pixels.

---

## 8. Face and hair

- Eyes are single pixels in the eye color on row 18, at x 13 and 17. No pupils, highlights, eyebrows, mouth or nose. A blink replaces each eye pixel with skin shadow.
- Row 18 is the widest face row (x 11..19), with skin mid on the outer cheeks. Row 19 is the chin: narrower (x 12..18), skin shadow at both ends, rounded by the outline.
- Hair covers rows 11..17 and frames the face. The center part is a 1 px mid-tone line at x = 16 (one right of center) on rows 12..14. The forehead first appears under the part on rows 15..16, and locks of hair come down over the sides of the face on row 17.
- In side views, show one eye near the front edge of the face and give the hair volume at the back of the head. In the N view, hair covers the whole back of the head down to row 18 and no eyes are visible.

---

## 9. Ground shadow

- An 11 x 4 ellipse with cut corners: row 26 spans x 11..19, rows 27 and 28 span x 10..20, row 29 spans x 11..19. Centered on x = 15.
- Color: the outline color #3a263a at alpha 70 (about 27.5%). Over the preview beige #c3bc9d this gives exactly #9d9382, the shadow color in the original screenshot.
- `style/recolor_test_1x.png` and `_6x.png` were rendered without the shadow's row 26, so two shadow pixels (x 16 and 19) differ from `anchor_with_shadow.png`. The shadow here and in `style.json` is the reference; every character pixel of the eight recolors matches exactly (tested).
- Always drawn behind the character. It is never outlined and never part of the silhouette.
- For airborne frames (future jumps), shrink it by 2 px of width for every 2 px of height, minimum 5 px wide, and never move it vertically.
- Lying-down poses (death) get a wider, flatter shadow matched to the body.

---

## 10. Directions

| Code | Meaning |
|---|---|
| `s` | facing the camera (moving down the screen) |
| `e` | facing screen-right |
| `n` | facing away (moving up the screen) |
| `w` | facing screen-left, generated by mirroring `e` |

- West is the mirror of East around the pivot column: `x_new = 30 - x`. Never flip the whole canvas (that would move the pivot from 15 to 16 and make the character jump 1 px when turning).
- Mirroring swaps handedness, so a sword in the right hand facing east ends up in the left hand facing west. This is standard for top-down RPGs and accepted by default.
- Facing east, the near side (toward the camera) is the character's right side.
- Side-view proportions (design guidance, not measured): head 9 to 10 px wide including outline, hair adding volume at the back; one eye visible near the front; body 7 to 8 px wide; near arm drawn in front of the torso; far arm mostly hidden.
- N view: no face, hair covers the head, the collar line becomes a hair-to-cloth boundary, the belt continues around the back.

---

## 11. Brightness belongs to FX

Characters and monsters stay inside the palette limits above. Only effects (fire, ice, poison, arcane, holy, shadow, impact; see `fx_ramps` in `style.json`) and glow eye presets may go brighter and more saturated. In combat, that contrast is what makes attacks, spells and enemy tells pop without the characters losing their soft look. `style/examples/battle_mock_6x.png` shows the balance.

## 12. What breaks this style

These are the mistakes to watch for in every review:

- Faces getting bigger or more detailed (2 px eyes, mouths, noses, eye highlights)
- Black outlines or black shading
- Highlights near white, or saturated colors
- Antialiased or semi-transparent edges
- Gradients, pillow shading, dithering, banding
- Outlines thickening to 2 px, or doubling where parts meet
- Head shrinking or legs lengthening in some frames or directions
- Side views where both arms or both legs do the same thing at the same time (twinning)
- Single stray pixels and noisy one-pixel clusters
- The collar line disappearing so the head merges into the body
