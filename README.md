# pixelforge starter kit

Everything Claude Code needs to build a reusable pixel character and animation system that matches your reference sprite exactly.

## What's inside

| File | What it's for |
|---|---|
| `CLAUDE.md` | Rules Claude Code reads at the start of every session |
| `KICKOFF_PROMPT.md` | The prompt for each phase, plus prompts for resuming and debugging |
| `docs/STYLE_GUIDE.md` | Your style measured pixel by pixel: palette, proportions, outline rules, shading, face |
| `docs/ARCHITECTURE.md` | How the system works: parts, layers, recoloring, outlining, export, tools |
| `docs/ANIMATION_SPEC.md` | Frame-by-frame specs for idle, blink, walk, and the core attack, hurt and death |
| `docs/COMBAT.md` | The full combat set (stances, slash, heavy, bow, cast, block, dodge, stun, victory), telegraph timing for enemies, events, hitboxes, and the FX library |
| `docs/MONSTERS.md` | Body plans (rigs) for slimes, flyers, beasts, humanoid monsters and bosses, size classes, monster materials, design rules |
| `docs/QUALITY.md` | Validator rules, the visual review process, the scoring rubric |
| `docs/ROADMAP.md` | Build phases with acceptance tests and checkpoints, plus the knight brief |
| `style/style.json` | Palette, material ramps, recolor presets, canvas and timing data |
| `style/anchor.png` | Your reference sprite, cleaned to its true pixels (11 x 18 on 32 x 32) |
| `style/anchor_annotated.png` | The anchor at 12x with proportions, pivot and eyes marked |
| `style/recolor_test_*.png` | Eight recolors of the anchor proving the presets stay on-style |
| `style/monster_fx_swatches.png` | Every monster material and FX ramp next to the anchor's colors |
| `style/examples/` | A draft slime and a battle mockup (fireball FX) proving the style extends to monsters and effects |
| `templates/SKILL.md` | Installed in the last phase so any project can use pixelforge |

## Starting

1. Create an empty folder called `pixelforge` and put the contents of this kit in it, so `CLAUDE.md` is at the top level.
2. Open a terminal in that folder and run `claude`.
3. Paste the Phase 0 prompt from `KICKOFF_PROMPT.md`.
4. Approve its plan, let it work, and move to the next phase prompt when it stops.

You'll want Python 3.11+ installed, and the GitHub CLI (`gh`) logged in so it can create the private repo. If either is missing, Claude Code will tell you what to install.

## Developer setup

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

```bash
.venv/bin/pf palette --check
```

The last command checks every color in `style/style.json` and writes `review/palette_swatches.png`.

## How to approve checkpoints

The checkpoints are where quality is decided. At each one:

- Open the review images it points you to, and open the preview it builds (from Phase 3a on).
- Look at the sprites at 1x (true size), not just zoomed in. That's how players see them.
- Compare against `style/anchor_annotated.png`. Same head size? Same colors? Same outline?
- If something bugs you, say exactly what ("the head looks smaller in the side view", "the walk feels bouncy") rather than "make it better".

The base body turnaround (Phase 2) and the walk cycle (Phase 3b) matter most, since every future character inherits them. For combat, the Phase 5 checkpoint decides how every fight in your games will feel: watch the enemy-timing version and ask yourself whether you could react to it.

## Resuming

Start `claude` in the folder and use the "Resuming in a new session" prompt from `KICKOFF_PROMPT.md`.

## Tips

- Aseprite is the best tool for fixing a pixel by hand. Parts are plain PNGs in a 32 x 32 grid, so you can edit them directly and rebuild.
- If Claude Code says something "looks good", ask what it checked. It should have opened the review images and scored the rubric.
- Commit history is your undo button. If a change makes things worse, ask it to revert to the last good commit.
