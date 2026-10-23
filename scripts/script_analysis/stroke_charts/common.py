"""Stroke-vocabulary charts generated from font outlines + hand-written stroke sequences.
A letter is a list of strokes; a stroke is a polyline of (x, y) points in the glyph's own bounding box (0..1, y up).
Purely horizontal/vertical runs are one stroke per segment (the user's convention); curves stay one stroke."""
import math
import numpy as np
from fontTools.ttLib import TTFont, TTCollection
from fontTools.pens.recordingPen import DecomposingRecordingPen
from matplotlib.path import Path


def load_font(path, index=0):
    if path.endswith(".ttc"):
        return TTCollection(path).fonts[index]
    return TTFont(path)


def _flatten(rec, steps=12):
    polys, cur = [], []
    for op, args in rec.value:
        if op == "moveTo":
            cur = [args[0]]
        elif op == "lineTo":
            cur.append(args[0])
        elif op == "qCurveTo":
            pts = list(args)
            p0 = cur[-1]
            if pts[-1] is None:                      # closed all-off-curve contour (rare)
                pts = pts[:-1]
            offs, end = pts[:-1], pts[-1]
            ons = []
            for i, o in enumerate(offs):
                nxt = offs[i + 1] if i + 1 < len(offs) else end
                on = ((o[0] + nxt[0]) / 2, (o[1] + nxt[1]) / 2) if i + 1 < len(offs) else end
                ons.append((o, on))
            for o, on in ons:
                for t in np.linspace(0, 1, steps)[1:]:
                    cur.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * o[0] + t * t * on[0],
                                (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * o[1] + t * t * on[1]))
                p0 = on
        elif op == "curveTo":
            p0 = cur[-1]
            c1, c2, p1 = args
            for t in np.linspace(0, 1, steps)[1:]:
                u = 1 - t
                cur.append((u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p1[0],
                            u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p1[1]))
        elif op in ("closePath", "endPath"):
            if cur:
                polys.append(cur)
            cur = []
    return polys


def glyph_polys(font, ch, uniform=False):
    """Glyph outline flattened to polygons, normalised to its own bbox -> unit box (y up)."""
    gs = font.getGlyphSet()
    name = font.getBestCmap().get(ord(ch))
    if name is None:
        return None
    pen = DecomposingRecordingPen(gs)
    gs[name].draw(pen)
    polys = _flatten(pen)
    pts = np.array([p for poly in polys for p in poly])
    x0, y0 = pts.min(0)
    x1, y1 = pts.max(0)
    if min(x1 - x0, y1 - y0) < .3 * max(x1 - x0, y1 - y0):
        uniform = True                             # a bar or a dot: never stretch it to a square
    if uniform:                                   # a bare bar: keep its true proportions inside the unit box
        m = max(x1 - x0, y1 - y0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        x0, x1, y0, y1 = cx - m / 2, cx + m / 2, cy - m / 2, cy + m / 2
    return [[((x - x0) / (x1 - x0), (y - y0) / (y1 - y0)) for x, y in poly] for poly in polys]


def ink_path(polys):
    verts, codes = [], []
    for poly in polys:
        verts += poly + [poly[0]]
        codes += [Path.MOVETO] + [Path.LINETO] * (len(poly) - 1) + [Path.CLOSEPOLY]
    return Path(verts, codes)


def sample(stroke, n=40):
    out = []
    for (ax, ay), (bx, by) in zip(stroke, stroke[1:]):
        for t in np.linspace(0, 1, max(2, int(n * math.hypot(bx - ax, by - ay))), endpoint=False):
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    out.append(stroke[-1])
    return out


def coverage(polys, strokes, tol=.07):
    """Share of stroke sample points lying within `tol` of the glyph's ink, and share of ink covered by strokes (grid cells)."""
    path = ink_path(polys)
    offs = [(0, 0)] + [(tol * math.cos(a), tol * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    pts = np.array([p for s in strokes for p in sample(s)])
    on = np.zeros(len(pts), bool)
    for dx, dy in offs:
        on |= path.contains_points(pts + (dx, dy))
    g = np.linspace(0, 1, 40)
    grid = np.array([(x, y) for x in g for y in g])
    ink = path.contains_points(grid)
    near = np.zeros(len(grid), bool)
    sp = pts[:, None, :] - grid[None, :, :]
    near = (np.hypot(sp[..., 0], sp[..., 1]) < .14).any(0)
    return float(on.mean()), float((near & ink).sum() / max(ink.sum(), 1))


def circle(cx, cy, rx, ry=None, a0=90, n=24, turn=360):
    ry = rx if ry is None else ry
    return [(cx + rx * math.cos(math.radians(a0 + turn * i / n)), cy + ry * math.sin(math.radians(a0 + turn * i / n))) for i in range(n + 1)]


def arc(cx, cy, rx, ry, a0, a1, n=16):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
