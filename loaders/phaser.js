// pixelforge for Phaser 3 (3.60 or newer).
//
// An export is a PNG spritesheet plus Aseprite-format JSON, so Phaser's Aseprite loader reads it
// directly: every tag (<anim>_<dir>, w drawn, never flipped) becomes an animation with the
// export's per-frame durations. `meta.pixelforge` adds the pivot, events, hitboxes, points and
// timing profiles (COMBAT.md). Assumes Phaser's AsepriteFile, which puts the JSON in
// scene.cache.json under the same key.
//
//   preload() { preloadPixelforge(this, "knight", "assets/knight.png", "assets/knight.json"); }
//   create() {
//     const knight = createPixelforge(this, "knight", 120, 90);
//     knight.on("pf-event", (e) => { if (e.type === "hit") strike(hitboxes(knight)); });
//     playDir(knight, "attack_slash", facing(dx, dy));
//   }

export function preloadPixelforge(scene, key, pngUrl, jsonUrl) {
  scene.load.aseprite(key, pngUrl, jsonUrl);
}

/** Create the animations (once per key) and a sprite whose position is its ground point. */
export function createPixelforge(scene, key, x, y) {
  const json = scene.cache.json.get(key);
  const pf = json.meta.pixelforge;
  if (!scene.anims.exists(json.meta.frameTags[0].name)) {
    scene.anims.createFromAseprite(key);
    for (const tag of json.meta.frameTags) {
      const anim = tag.name.slice(0, tag.name.lastIndexOf("_"));
      scene.anims.get(tag.name).repeat = pf.loop[anim] ? -1 : 0;
    }
  }
  const cell = json.frames[0].sourceSize.w;
  const sprite = scene.add.sprite(x, y, key);
  // the pivot pixel's top-left on (x, y): keep x and y integers and the art stays pixel exact
  sprite.setOrigin(pf.pivot[0] / cell, pf.pivot[1] / cell);
  sprite.pf = pf;
  sprite.on("animationstart", (anim) => fire(sprite, anim.key, 0));
  sprite.on("animationupdate", (anim, frame) => fire(sprite, anim.key, frame.index - 1));
  return sprite;
}

function fire(sprite, tag, index) {
  for (const e of sprite.pf.events[tag] || []) {
    if (e.frame === index) sprite.emit("pf-event", e, sprite);
  }
}

export function playDir(sprite, anim, dir) {
  sprite.play(`${anim}_${dir}`, true);
}

/** The view for a direction of travel or aim: the dominant axis. */
export function facing(dx, dy) {
  if (Math.abs(dx) >= Math.abs(dy)) return dx >= 0 ? "e" : "w";
  return dy >= 0 ? "s" : "n";
}

function current(sprite) {
  const a = sprite.anims.currentAnim;
  return a ? { tag: a.key, index: sprite.anims.currentFrame.index - 1 } : null;
}

function toWorld(sprite, boxes) {
  const [px, py] = sprite.pf.pivot;
  const z = sprite.scaleX;
  return (boxes || []).map((b) => new Phaser.Geom.Rectangle(
    sprite.x + (b.x - px) * z, sprite.y + (b.y - py) * z, b.w * z, b.h * z));
}

/** World-space damage boxes for the current frame (only on active frames). */
export function hitboxes(sprite) {
  const c = current(sprite);
  return c ? toWorld(sprite, (sprite.pf.hitboxes[c.tag] || {})[c.index]) : [];
}

export function hurtboxes(sprite) {
  const c = current(sprite);
  return c ? toWorld(sprite, (sprite.pf.hurtboxes[c.tag] || {})[c.index]) : [];
}

/** A named point (hand_near, weapon_tip, bow_nock, core...) in world space. */
export function point(sprite, name) {
  const c = current(sprite);
  const p = c && ((sprite.pf.points[c.tag] || [])[c.index] || {})[name];
  if (!p) return null;
  const [px, py] = sprite.pf.pivot;
  return { x: sprite.x + (p[0] - px) * sprite.scaleX, y: sprite.y + (p[1] - py) * sprite.scaleY };
}
