// Sizing the server's SVG pictures (letters, sentences). Plain TypeScript so it can be tested with Node.
export function svgSize(xml: string): { w: number; h: number } | null {
  const vb = /viewBox="\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)\s*"/.exec(xml);
  if (vb && +vb[1] > 0 && +vb[2] > 0) return { w: +vb[1], h: +vb[2] };
  const w = /\swidth="([\d.]+)"/.exec(xml), h = /\sheight="([\d.]+)"/.exec(xml);
  return w && h && +w[1] > 0 && +h[1] > 0 ? { w: +w[1], h: +h[1] } : null;
}

/** The size to draw it at: the full width available, but never bigger than the picture's own size. */
export function fitSvg(xml: string, available: number, maxScale = 1): { width: number; height: number } | null {
  const s = svgSize(xml);
  if (!s || available <= 0) return null;
  const width = Math.min(available, s.w * maxScale);
  return { width, height: (width * s.h) / s.w };
}
