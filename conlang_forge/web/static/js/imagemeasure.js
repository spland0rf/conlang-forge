// Reading a picture of sample letters in the browser: shrink it, then measure it. Only the shrunken picture and a few
// numbers leave the page; the server never keeps the picture.
const BINS = 12;                         // stroke directions in 15 degree steps, 0 = horizontal strokes

function otsu(gray, n) {
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
function regions(mask, w, h, want, eight) {
  const seen = new Uint8Array(w * h), out = [], stack = [];
  for (let s = 0; s < w * h; s++) {
    if (seen[s] || mask[s] !== want) continue;
    let size = 0, border = false;
    stack.push(s); seen[s] = 1;
    while (stack.length) {
      const p = stack.pop(), x = p % w, y = (p - x) / w;
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

function longestRunShare(mask, w, y0, y1, x0, x1) {
  let best = 0;
  for (let y = y0; y <= y1; y++) {
    let run = 0;
    for (let x = x0; x <= x1; x++) { run = mask[y * w + x] ? run + 1 : 0; if (run > best) best = run; }
  }
  return best / Math.max(1, x1 - x0 + 1);
}

// The measurements, from the pixels (RGBA bytes, w x h). Pure, so the mobile app's port can be checked against it.
export function measureRgba(rgba, w, h) {
  const n = w * h, gray = new Uint8Array(n);
  for (let i = 0; i < n; i++) gray[i] = (rgba[i * 4] * 299 + rgba[i * 4 + 1] * 587 + rgba[i * 4 + 2] * 114) / 1000;
  const thr = otsu(gray, n);
  let mask = new Uint8Array(n), count = 0;
  for (let i = 0; i < n; i++) { mask[i] = gray[i] <= thr ? 1 : 0; count += mask[i]; }
  if (count > n / 2) { for (let i = 0; i < n; i++) mask[i] ^= 1; count = n - count; }      // light letters on a dark ground

  // stroke direction from the gradient of a lightly blurred mask
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
  const tot = bins.reduce((a, b) => a + b, 0) || 1;

  // shapes, loops, and long lines along the bottom or top of the inked area
  const minSize = Math.max(6, Math.round(n * 0.00015));
  const shapes = regions(mask, w, h, 1, true).filter((r) => r.size >= minSize);
  const loops = regions(mask, w, h, 0, false).filter((r) => !r.border && r.size >= minSize).length;
  let x0 = w, x1 = 0, y0 = h, y1 = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (mask[y * w + x]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  const band = Math.max(2, Math.round((y1 - y0) * 0.12));
  return {
    orientation: Array.from(bins, (b) => +(b / tot).toFixed(4)),
    ink: +(count / n).toFixed(4),
    components: shapes.length,
    holes: +(loops / Math.max(1, shapes.length)).toFixed(3),
    baseline: x1 > x0 ? +longestRunShare(mask, w, y1 - band, y1, x0, x1).toFixed(3) : 0,
    topline: x1 > x0 ? +longestRunShare(mask, w, y0, y0 + band, x0, x1).toFixed(3) : 0,
  };
}

export async function analyzeImage(file, maxEdge = 1024) {
  const bmp = await createImageBitmap(file);
  const k = Math.min(1, maxEdge / Math.max(bmp.width, bmp.height));
  const w = Math.max(16, Math.round(bmp.width * k)), h = Math.max(16, Math.round(bmp.height * k));
  const canvas = Object.assign(document.createElement("canvas"), { width: w, height: h });
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h); ctx.drawImage(bmp, 0, 0, w, h);
  const measures = measureRgba(ctx.getImageData(0, 0, w, h).data, w, h);
  const data = canvas.toDataURL("image/jpeg", 0.88).split(",")[1];
  return { image: { media_type: "image/jpeg", data }, measures };
}
