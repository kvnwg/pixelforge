/**
 * pixelforge loader for canvas renderers (framework-free TypeScript; Rolling Knight's renderer,
 * or any game that draws with CanvasRenderingContext2D).
 *
 * A pixelforge export is a PNG spritesheet plus Aseprite-format JSON. Every tag is
 * `<anim>_<dir>` (dir is s, e, n or w; w is drawn, never flipped at runtime), and
 * `meta.pixelforge` carries the combat data: the pivot, per-tag events, phases, hitboxes and
 * hurtboxes per frame, named points per frame, root motion, hold frames, base durations and the
 * timing profiles (COMBAT.md sections 2, 4 and 5).
 *
 * FX exports (out/fx/<name>/) load the same way: their pivot is per tag, and `layer`, `space`
 * and `attach` say how to play them (an event's `fx` names one; spawn it at the event's point).
 *
 * In a browser: `loadSheet(pngUrl, jsonUrl)`. In Node (tests, tools): `new Sheet(JSON.parse(text))`
 * (no image, so nothing draws), and with Node's type stripping import this file with its `.ts`
 * extension.
 *
 * Usage:
 *   const sheet = await loadSheet("assets/knight.png", "assets/knight.json");
 *   const anim = new Animator(sheet);
 *   anim.play("attack_slash", facing(dx, dy));
 *   // each tick:
 *   for (const ev of anim.update(dtMs)) if (ev.type === "hit") dealDamage(anim.hitboxes(x, y));
 *   anim.draw(ctx, x, y, zoom);   // (x, y) is the entity's ground point: the pivot lands there
 *
 * Moving: play "run" (or "walk") and match its feet to the entity's speed, so they don't slide:
 *   anim.play("run", facing(vx, vy));
 *   anim.rate = speed / sheet.naturalSpeed("run");   // px/s at zoom 1; back to 1 for other clips
 */

export type Dir = "s" | "e" | "n" | "w";
export interface Box { x: number; y: number; w: number; h: number }
export interface PFEvent {
  frame: number;
  type: string;            // windup, hit, spawn, vfx, footstep, summon, recover, ...
  fx?: string;             // the FX to play (out/fx/<fx>)
  point?: [number, number]; // in frame pixels (relative to the cell's top-left)
  point_name?: string;     // the anchor the point came from (hand_near, bow_nock, core...)
  pattern?: string;        // spawn volleys: "ring" or "fan"
  count?: number;
  spread?: number;         // radians between the shots of a fan
  [key: string]: unknown;
}
export interface TimingProfile { telegraph_min_ms: number; hold_scale: number }
export interface Frame { x: number; y: number; w: number; h: number; duration: number }
export interface Clip {
  tag: string; anim: string; dir: Dir; loop: boolean;
  frames: Frame[];
  events: PFEvent[];
  phases: string[];                 // windup | active | recovery | "" per frame
  hitboxes: Box[][];                // per frame (empty outside the active phase)
  hurtboxes: Box[][];
  points: Record<string, [number, number]>[];  // per frame
  rootMotion: number[] | null;      // px along the facing per frame (dodges, charges)
  holds: number[];                  // frames a timing profile stretches
  baseDurations: number[];          // durations before the recipe's profile was applied
  loopFrames: number[] | null;      // frames the game may repeat while a move lasts (a charge)
}

/** The view to play for a direction of travel or aim: the dominant axis (as Rolling Knight's face()). */
export function facing(dx: number, dy: number): Dir {
  if (Math.abs(dx) >= Math.abs(dy)) return dx >= 0 ? "e" : "w";
  return dy >= 0 ? "s" : "n";
}

/** Python's round(): halves go to the even neighbor, so retimed durations match the exporter. */
function roundHalfEven(v: number): number {
  const f = Math.floor(v), d = v - f;
  if (Math.abs(d - 0.5) > 1e-9) return Math.round(v);
  return f % 2 === 0 ? f : f + 1;
}

export class Sheet {
  readonly json: any;
  readonly image: CanvasImageSource | null;
  /** The ground point of a character (FX: their first tag's pivot; use pivotFor). */
  readonly pivot: [number, number];
  /** FX only: drawn above or below characters, in world space or following an anchor. */
  readonly isFx: boolean;
  readonly layer: string;
  readonly space: string;
  readonly attach: string | null;
  readonly cell: number;
  readonly sizeClass: string;
  readonly timingProfile: string;
  readonly profiles: Record<string, TimingProfile>;
  private clips = new Map<string, Clip>();

  constructor(json: any, image: CanvasImageSource | null = null) {
    this.json = json;
    this.image = image;
    const pf = json.meta.pixelforge;
    this.isFx = !Array.isArray(pf.pivot);
    this.pivot = this.isFx ? pf.pivot[json.meta.frameTags[0].name] : pf.pivot;
    this.layer = pf.layer ?? "above";
    this.space = pf.space ?? "world";
    this.attach = pf.attach ?? null;
    this.sizeClass = pf.size_class ?? "small";
    this.timingProfile = pf.timing_profile ?? "player";
    this.profiles = pf.timing_profiles ?? {};
    this.cell = json.frames[0]?.sourceSize?.w ?? 32;
    for (const tag of json.meta.frameTags) {
      const name: string = tag.name;
      const cut = name.lastIndexOf("_");
      const anim = name.slice(0, cut), dir = name.slice(cut + 1) as Dir;
      const frames: Frame[] = json.frames.slice(tag.from, tag.to + 1)
        .map((f: any) => ({ ...f.frame, duration: f.duration }));
      const perFrame = <T>(table: Record<string, T> | undefined, empty: T): T[] =>
        frames.map((_, i) => (table && table[String(i)]) ?? empty);
      this.clips.set(name, {
        tag: name, anim, dir, loop: !!pf.loop?.[anim], frames,
        events: pf.events?.[name] ?? [],
        phases: pf.phases?.[name] ?? frames.map(() => ""),
        hitboxes: perFrame<Box[]>(pf.hitboxes?.[name], []),
        hurtboxes: perFrame<Box[]>(pf.hurtboxes?.[name], []),
        points: pf.points?.[name] ?? frames.map(() => ({})),
        rootMotion: pf.root_motion?.[name] ?? null,
        holds: pf.holds?.[name] ?? [],
        baseDurations: pf.base_durations?.[name] ?? frames.map((f) => f.duration),
        loopFrames: pf.loop_frames?.[name] ?? null,
      });
    }
  }

  has(anim: string, dir: Dir): boolean { return this.clips.has(`${anim}_${dir}`); }

  /**
   * A gait's own ground speed in px/s (at zoom 1): the stride its planted feet travel per cycle
   * (`stride_px`, recorded facing e and w) over the cycle's duration. Moving at this speed, the
   * feet stay on the ground; set an Animator's `rate` to speed / naturalSpeed to match any other.
   */
  naturalSpeed(anim: string, dir: Dir = "e"): number | null {
    const stride: number[] | undefined = this.json.meta.pixelforge.stride_px?.[`${anim}_${dir}`];
    if (!stride || !this.has(anim, dir)) return null;
    const ms = this.clip(anim, dir).frames.reduce((a, f) => a + f.duration, 0);
    return (stride.reduce((a, b) => a + b, 0) / ms) * 1000;
  }

  /** The pixel placed on the world position for a tag: one pivot for characters, per tag for FX. */
  pivotFor(tag: string): [number, number] {
    const pv = this.json.meta.pixelforge.pivot;
    return Array.isArray(pv) ? pv : pv[tag];
  }

  clip(anim: string, dir: Dir): Clip {
    const c = this.clips.get(`${anim}_${dir}`);
    if (!c) throw new Error(`no ${anim}_${dir} in this sheet`);
    return c;
  }

  /**
   * Durations for another timing profile (COMBAT.md section 2): hold frames scale by
   * hold_scale; if the tell (first windup frame to the hit or spawn) is still under the
   * minimum, the last hold frame before the hit grows until it meets it.
   */
  retime(anim: string, dir: Dir, profileName: string): number[] {
    const c = this.clip(anim, dir);
    const p = this.profiles[profileName] ?? { hold_scale: 1, telegraph_min_ms: 0 };
    const holds = new Set(c.holds);
    const out = c.baseDurations.map((ms, i) => (holds.has(i) ? roundHalfEven(ms * p.hold_scale) : ms));
    const first = (types: string[]) => {
      const fs = c.events.filter((e) => types.includes(e.type)).map((e) => e.frame);
      return fs.length ? Math.min(...fs) : null;
    };
    const hit = first(["hit", "spawn"]);
    const start = first(["windup"]) ?? 0;
    if (hit !== null && p.telegraph_min_ms) {
      const tell = out.slice(start, hit).reduce((a, b) => a + b, 0);
      if (tell < p.telegraph_min_ms) {
        const before = c.holds.filter((i) => i >= start && i < hit);
        out[before.length ? Math.max(...before) : hit - 1] += p.telegraph_min_ms - tell;
      }
    }
    return out;
  }
}

/** Plays one character's clips, fires their events in order and draws the current frame. */
export class Animator {
  readonly sheet: Sheet;
  profile: string;
  clip: Clip | null = null;
  frame = 0;
  done = false;
  /** Playback speed: 1 plays the sheet's durations; a walk or run takes speed / naturalSpeed. */
  rate = 1;
  private t = 0;
  private durations: number[] = [];
  private holdLoop = false;

  constructor(sheet: Sheet, profile: string = sheet.timingProfile) {
    this.sheet = sheet;
    this.profile = profile;
  }

  /** Start a clip (no-op if it is already playing, unless restart). */
  play(anim: string, dir: Dir, restart = false): PFEvent[] {
    const tag = `${anim}_${dir}`;
    if (!restart && this.clip?.tag === tag && !this.done) return [];
    this.clip = this.sheet.clip(anim, dir);
    this.durations = this.profile === this.sheet.timingProfile
      ? this.clip.frames.map((f) => f.duration)
      : this.sheet.retime(anim, dir, this.profile);
    this.frame = 0; this.t = 0; this.done = false;
    return this.eventsAt(0);
  }

  /** While true, a clip with loop_frames (a boss's charge) repeats them instead of moving on. */
  setHoldLoop(on: boolean) { this.holdLoop = on; }

  /** Advance by dt ms; returns the events of every frame entered, in order. */
  update(dtMs: number): PFEvent[] {
    const c = this.clip;
    if (!c || this.done) return [];
    const fired: PFEvent[] = [];
    this.t += dtMs * this.rate;
    while (this.t >= this.durations[this.frame]) {
      this.t -= this.durations[this.frame];
      let next = this.frame + 1;
      const lf = c.loopFrames;
      if (this.holdLoop && lf && this.frame === lf[lf.length - 1]) next = lf[0];
      if (next >= c.frames.length) {
        if (!c.loop) { this.done = true; this.t = 0; break; }
        next = 0;
      }
      this.frame = next;
      fired.push(...this.eventsAt(next));
    }
    return fired;
  }

  private eventsAt(i: number): PFEvent[] { return this.clip!.events.filter((e) => e.frame === i); }

  /** The current phase: windup (the tell), active (it can hit), recovery or "". */
  get phase(): string { return this.clip?.phases[this.frame] ?? ""; }

  /** A frame-space point (from an event or the frame's named points) in world space, for an
   *  entity whose ground point (the pivot) is at (x, y), at a given zoom. */
  toWorld(p: [number, number], x: number, y: number, zoom = 1): [number, number] {
    const [px, py] = this.pivotHere();
    return [x + (p[0] - px) * zoom, y + (p[1] - py) * zoom];
  }

  point(name: string, x: number, y: number, zoom = 1): [number, number] | null {
    const p = this.clip?.points[this.frame]?.[name];
    return p ? this.toWorld(p, x, y, zoom) : null;
  }

  private pivotHere(): [number, number] {
    return this.clip ? this.sheet.pivotFor(this.clip.tag) : this.sheet.pivot;
  }

  private boxes(list: Box[], x: number, y: number, zoom: number): Box[] {
    const [px, py] = this.pivotHere();
    return list.map((b) => ({ x: x + (b.x - px) * zoom, y: y + (b.y - py) * zoom, w: b.w * zoom, h: b.h * zoom }));
  }

  /** Damage boxes in world space (non-empty only on active frames). */
  hitboxes(x: number, y: number, zoom = 1): Box[] {
    return this.clip ? this.boxes(this.clip.hitboxes[this.frame], x, y, zoom) : [];
  }

  hurtboxes(x: number, y: number, zoom = 1): Box[] {
    return this.clip ? this.boxes(this.clip.hurtboxes[this.frame], x, y, zoom) : [];
  }

  /** Root motion for the current frame, in px along the facing (dodges, a boss's charge). */
  get rootMotion(): number { return this.clip?.rootMotion?.[this.frame] ?? 0; }

  /** Draw the current frame with its pivot on (x, y); integer zoom keeps the pixels square. */
  draw(ctx: CanvasRenderingContext2D, x: number, y: number, zoom = 1) {
    const c = this.clip;
    if (!c || !this.sheet.image) return;
    const f = c.frames[this.frame];
    const [px, py] = this.pivotHere();
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(this.sheet.image, f.x, f.y, f.w, f.h,
      Math.round(x - px * zoom), Math.round(y - py * zoom), f.w * zoom, f.h * zoom);
  }
}

/** Fetch a sheet's JSON and image (browser). */
export async function loadSheet(pngUrl: string, jsonUrl: string): Promise<Sheet> {
  const [json, image] = await Promise.all([
    fetch(jsonUrl).then((r) => r.json()),
    new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = pngUrl;
    }),
  ]);
  return new Sheet(json, image);
}
