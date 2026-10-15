// Measuring a picture of sample letters: a line-for-line port of measureRgba in the website's imagemeasure.js, so a
// picture gives the same numbers on the phone and in the browser (tests/measure.test.ts checks this). Nothing here
// depends on React Native.
export const BINS = 12;                         // stroke directions in 15 degree steps, 0 = horizontal strokes

export type Measures = { orientation: number[]; ink: number; components: number; holes: number; baseline: number; topline: number };

function otsu(gray: Uint8Array, n: number): number {
  const hist = new Float64Array(256);
  for (let i = 0; i < n; i++) hist[gray[i]]++;
  let sum = 0;
  for (let t = 0; t < 256; t++) sum += t * hist[t];
  let wB = 0, sumB = 0, best = 0, thr = 128;
  for (let t = 0; t < 256; t++) {
    wB += hist[t]; if (!wB) continue;
    const wF = n - wB; if (!wF) break;
    sumB += t * hist[t];
    const between = wB * wF * (sumB / wB - (sum - sumB) / wF) ** 2;
    if (between > best) { best = between; thr = t; }
  }
  return thr;
}

// size of the connected regions of `mask` (value `want`), 8-connected for ink and 4-connected for background
function regions(mask: Uint8Array, w: number, h: number, want: number, eight: boolean): { size: number; border: boolean }[] {
  const seen = new Uint8Array(w * h), out: { size: number; border: boolean }[] = [], stack: number[] = [];
  for (let s = 0; s < w * h; s++) {
    if (seen[s] || mask[s] !== want) continue;
    let size = 0, border = false;
    stack.push(s); seen[s] = 1;
    while (stack.length) {
      const p = stack.pop() as number, x = p % w, y = (p - x) / w;
      size++;
      if (x === 0 || y === 0 || x === w - 1 || y === h - 1) border = true;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if ((!dx && !dy) || (!eight && dx && dy)) continue;
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
        const q = ny * w + nx;
        if (!seen[q] && mask[q] === want) { seen[q] = 1; stack.push(q); }
      }
    }
    out.push({ size, border });
  }
  return out;
}

function longestRunShare(mask: Uint8Array, w: number, y0: number, y1: number, x0: number, x1: number): number {
  let best = 0;
  for (let y = y0; y <= y1; y++) {
    let run = 0;
    for (let x = x0; x <= x1; x++) { run = mask[y * w + x] ? run + 1 : 0; if (run > best) best = run; }
  }
  return best / Math.max(1, x1 - x0 + 1);
}

/** The numbers the server turns into style settings, from RGBA bytes (w x h). */
export function measureRgba(rgba: ArrayLike<number>, w: number, h: number): Measures {
  const n = w * h, gray = new Uint8Array(n);
  for (let i = 0; i < n; i++) gray[i] = (rgba[i * 4] * 299 + rgba[i * 4 + 1] * 587 + rgba[i * 4 + 2] * 114) / 1000;
  const thr = otsu(gray, n);
  const mask = new Uint8Array(n);
  let count = 0;
  for (let i = 0; i < n; i++) { mask[i] = gray[i] <= thr ? 1 : 0; count += mask[i]; }
  if (count > n / 2) { for (let i = 0; i < n; i++) mask[i] ^= 1; count = n - count; }      // light letters on a dark ground

  const blur = new Float32Array(n);
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    let s = 0; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) s += mask[(y + dy) * w + x + dx];
    blur[y * w + x] = s / 9;
  }
  const bins = new Float64Array(BINS);
  for (let y = 2; y < h - 2; y++) for (let x = 2; x < w - 2; x++) {
    const i = y * w + x;
    const gx = blur[i - w + 1] + 2 * blur[i + 1] + blur[i + w + 1] - blur[i - w - 1] - 2 * blur[i - 1] - blur[i + w - 1];
    const gy = blur[i + w - 1] + 2 * blur[i + w] + blur[i + w + 1] - blur[i - w - 1] - 2 * blur[i - w] - blur[i - w + 1];
    const m = Math.hypot(gx, gy);
    if (m < 0.3) continue;
    let dir = (Math.atan2(gy, gx) * 180 / Math.PI + 90) % 180;      // the stroke runs across the gradient
    if (dir < 0) dir += 180;
    bins[Math.min(BINS - 1, Math.floor(dir / 15))] += m;
  }
  let tot = 0;
  for (let i = 0; i < BINS; i++) tot += bins[i];
  tot = tot || 1;

  const minSize = Math.max(6, Math.round(n * 0.00015));
  const shapes = regions(mask, w, h, 1, true).filter((r) => r.size >= minSize);
  const loops = regions(mask, w, h, 0, false).filter((r) => !r.border && r.size >= minSize).length;
  let x0 = w, x1 = 0, y0 = h, y1 = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (mask[y * w + x]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  const band = Math.max(2, Math.round((y1 - y0) * 0.12));
  const r = (v: number, d: number) => +v.toFixed(d);
  return {
    orientation: Array.from(bins, (b) => r(b / tot, 4)),
    ink: r(count / n, 4),
    components: shapes.length,
    holes: r(loops / Math.max(1, shapes.length), 3),
    baseline: x1 > x0 ? r(longestRunShare(mask, w, y1 - band, y1, x0, x1), 3) : 0,
    topline: x1 > x0 ? r(longestRunShare(mask, w, y0, y0 + band, x0, x1), 3) : 0,
  };
}

/** The size to shrink a picture to before measuring: at most `maxEdge` on a side, never smaller than 16. */
export function shrunkSize(width: number, height: number, maxEdge = 1024): { width: number; height: number } {
  const k = Math.min(1, maxEdge / Math.max(width, height));
  return { width: Math.max(16, Math.round(width * k)), height: Math.max(16, Math.round(height * k)) };
}

/** Pictures with transparency are laid on white first (the website does the same), then measured. */
export function flattenOnWhite(rgba: ArrayLike<number>): Uint8Array {
  const out = new Uint8Array(rgba.length);
  for (let i = 0; i < rgba.length; i += 4) {
    const a = rgba[i + 3] / 255;
    for (let c = 0; c < 3; c++) out[i + c] = Math.round(rgba[i + c] * a + 255 * (1 - a));
    out[i + 3] = 255;
  }
  return out;
}
