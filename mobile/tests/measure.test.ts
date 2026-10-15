// Run with: npx tsx tests/measure.test.ts
// The phone's measuring must match the website's (imagemeasure.js) number for number.
import assert from "node:assert/strict";
import { measureRgba, flattenOnWhite, shrunkSize } from "../src/measure";
// @ts-ignore the website's file is plain JavaScript
import { measureRgba as web } from "../../conlang_forge/web/static/js/imagemeasure.js";

const W = 240, H = 160;
function canvas(draw: (set: (x: number, y: number) => void) => void, dark = false): Uint8Array {
  const px = new Uint8Array(W * H * 4).fill(dark ? 0 : 255);
  for (let i = 3; i < px.length; i += 4) px[i] = 255;
  draw((x, y) => { if (x >= 0 && y >= 0 && x < W && y < H) { const i = (y * W + x) * 4; px[i] = px[i + 1] = px[i + 2] = dark ? 255 : 0; } });
  return px;
}
const thick = (set: (x: number, y: number) => void, x: number, y: number) => { for (let a = 0; a < 3; a++) for (let b = 0; b < 3; b++) set(x + a, y + b); };
const line = (set: (x: number, y: number) => void, x0: number, y0: number, x1: number, y1: number) => {
  const n = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0));
  for (let i = 0; i <= n; i++) thick(set, Math.round(x0 + ((x1 - x0) * i) / n), Math.round(y0 + ((y1 - y0) * i) / n));
};
const ring = (set: (x: number, y: number) => void, cx: number, cy: number, r: number) => {
  for (let t = 0; t < 720; t++) thick(set, Math.round(cx + r * Math.cos((t * Math.PI) / 360)), Math.round(cy + r * Math.sin((t * Math.PI) / 360)));
};

const pictures: Record<string, Uint8Array> = {
  "vertical and diagonal": canvas((s) => { for (let k = 0; k < 6; k++) { line(s, 20 + k * 35, 30, 20 + k * 35, 120); line(s, 30 + k * 35, 30, 45 + k * 35, 120); } }),
  "rings": canvas((s) => { for (let k = 0; k < 5; k++) ring(s, 30 + k * 45, 80, 18); }),
  "boxy on a baseline": canvas((s) => { line(s, 10, 140, 230, 140); for (let k = 0; k < 5; k++) { line(s, 20 + k * 40, 60, 20 + k * 40, 140); line(s, 20 + k * 40, 60, 45 + k * 40, 60); } }),
  "light on dark": canvas((s) => { for (let k = 0; k < 4; k++) line(s, 30 + k * 50, 30, 60 + k * 50, 120); }, true),
};

const tests: [string, () => void][] = [];
const test = (n: string, f: () => void) => tests.push([n, f]);

for (const [name, px] of Object.entries(pictures)) {
  test(`same numbers as the website: ${name}`, () => assert.deepEqual(measureRgba(px, W, H), web(px, W, H)));
}
test("the measures mean what they should", () => {
  const rings = measureRgba(pictures["rings"], W, H);
  assert.equal(rings.components, 5);
  assert.ok(rings.holes >= 0.99, "each ring has a hole");
  const base = measureRgba(pictures["boxy on a baseline"], W, H);
  assert.ok(base.baseline > 0.8, "a long line along the bottom");
  const light = measureRgba(pictures["light on dark"], W, H);
  assert.ok(light.ink < 0.2, "light letters on a dark ground are still read as the ink");
  const sum = measureRgba(pictures["vertical and diagonal"], W, H).orientation.reduce((a, b) => a + b, 0);
  assert.ok(Math.abs(sum - 1) < 0.01);
});
test("shrinking keeps proportions and never grows a picture", () => {
  assert.deepEqual(shrunkSize(4000, 2000), { width: 1024, height: 512 });
  assert.deepEqual(shrunkSize(300, 200), { width: 300, height: 200 });
  assert.deepEqual(shrunkSize(2, 2000), { width: 16, height: 1024 });
});
test("transparent pixels become white", () => {
  const out = flattenOnWhite([0, 0, 0, 0, 10, 20, 30, 255, 0, 0, 0, 128]);
  assert.deepEqual(Array.from(out), [255, 255, 255, 255, 10, 20, 30, 255, 127, 127, 127, 255]);
});

let failed = 0;
for (const [n, f] of tests) { try { f(); console.log("ok  ", n); } catch (e) { failed++; console.log("FAIL", n, "\n    ", (e as Error).message.split("\n").slice(0, 4).join("\n     ")); } }
if (failed) { console.log(failed + " failed"); process.exit(1); }
console.log(tests.length + " passed");
