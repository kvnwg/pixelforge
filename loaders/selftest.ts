// Plays a clip from an export with the loader and prints what fired, for tests/test_loaders.py:
//   node --experimental-strip-types loaders/selftest.ts <json> <anim> <dir> <profile>
import { readFileSync } from "node:fs";
import { Animator, Sheet, facing, type Dir } from "./pixelforge.ts";

const [path, anim, dir, profile] = process.argv.slice(2);
const sheet = new Sheet(JSON.parse(readFileSync(path, "utf8")));
const a = new Animator(sheet, profile);
const fired: [number, string, number][] = [];
let t = 0;
for (const e of a.play(anim, dir as Dir)) fired.push([t, e.type, e.frame]);
while (!a.done && t < 20000) {
  t += 5;
  for (const e of a.update(5)) fired.push([t, e.type, e.frame]);
}
const hitAt = (() => { const h = fired.find((f) => f[1] === "hit" || f[1] === "spawn"); return h ? h[0] : null; })();
console.log(JSON.stringify({
  fired, hitAt, total: t, durations: sheet.retime(anim, dir as Dir, profile),
  pivot: sheet.pivot, facings: [facing(1, 0), facing(-1, 0.2), facing(0, 1), facing(0.1, -1)],
}));
