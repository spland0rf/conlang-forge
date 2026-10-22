// Run with: npx tsx tests/svg.test.ts
import assert from "node:assert/strict";
import { base64ToBytes } from "../src/base64";
import { fitSvg, lineSize, svgSize } from "../src/ui/svg";

const tests: [string, () => void][] = [];
const test = (n: string, f: () => void) => tests.push([n, f]);
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="929" height="156" viewBox="0 0 929 156"><rect width="100%" height="100%" fill="#fff"/></svg>';

test("reads the picture's own size", () => {
  assert.deepEqual(svgSize(svg), { w: 929, h: 156 });
  assert.deepEqual(svgSize('<svg width="40" height="20"></svg>'), { w: 40, h: 20 });
  assert.equal(svgSize("<svg></svg>"), null);
});
test("fits to the width available and never grows past its own size", () => {
  const a = fitSvg(svg, 361)!;
  assert.equal(a.width, 361); assert.ok(Math.abs(a.height - 361 * 156 / 929) < 1e-9);
  assert.equal(fitSvg(svg, 2000)!.width, 929);
  assert.equal(fitSvg(svg, 361, 0.5)!.width, 361);
  assert.equal(fitSvg(svg, 0), null);
});
test("base64 decodes like Buffer, with and without padding", () => {
  for (const len of [0, 1, 2, 3, 4, 5, 255, 1000]) {
    const raw = Uint8Array.from({ length: len }, (_, i) => (i * 37 + 11) & 255);
    const b64 = Buffer.from(raw).toString("base64");
    assert.deepEqual(Array.from(base64ToBytes(b64)), Array.from(raw));
    assert.deepEqual(Array.from(base64ToBytes(b64.replace(/=+$/, ""))), Array.from(raw));
  }
  assert.deepEqual(Array.from(base64ToBytes("a-_b")), Array.from(Buffer.from("a+/b", "base64")));
});

test("a sample line keeps a fixed height and narrows to fit the row", () => {
  const line = '<svg viewBox="0 0 600 156"></svg>';
  assert.deepEqual(lineSize(line, 1000, 34), { width: (34 * 600) / 156, height: 34 });
  const narrow = lineSize(line, 100, 34)!;
  assert.equal(narrow.width, 100);
  assert.ok(Math.abs(narrow.height - 26) < 0.01);
  assert.equal(lineSize(line, 0), null);
});

let failed = 0;
for (const [n, f] of tests) { try { f(); console.log("ok  ", n); } catch (e) { failed++; console.log("FAIL", n, "\n    ", (e as Error).message.split("\n").slice(0, 4).join("\n     ")); } }
if (failed) { console.log(failed + " failed"); process.exit(1); }
console.log(tests.length + " passed");
