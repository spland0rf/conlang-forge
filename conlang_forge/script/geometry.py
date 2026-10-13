"""Strokes and their geometry. A stroke is a control polyline (optionally closed) or a dot. The same control points
are drawn angular or rounded depending on the script's `roundness`, so connectivity never depends on style.

Coordinates: x to the right, y up, baseline y = 0, x-height y = 1.0 (see `LINES`). A glyph's width is in the same units."""
from __future__ import annotations

import math

LINES = {"descender": -0.5, "baseline": 0.0, "xheight": 1.0, "ascender": 1.55}
EPS = 1e-9


def stroke(points, closed=False):
    return {"p": [[round(float(x), 4), round(float(y), 4)] for x, y in points], "closed": bool(closed)}


def dot(x, y, r=0.09):
    return {"p": [[round(float(x), 4), round(float(y), 4)]], "closed": False, "dot": True, "r": r}


def chaikin(pts, ratio, closed=False, iters=2):
    """Corner cutting. ratio 0 keeps the polyline angular; ~0.25 is the classic smooth curve."""
    if ratio <= 0.001 or len(pts) < 3:
        return [tuple(p) for p in pts]
    pts = [tuple(p) for p in pts]
    for _ in range(iters):
        out = []
        n = len(pts)
        rng = range(n) if closed else range(n - 1)
        if not closed:
            out.append(pts[0])
        for i in rng:
            p, q = pts[i], pts[(i + 1) % n]
            out.append((p[0] + ratio * (q[0] - p[0]), p[1] + ratio * (q[1] - p[1])))
            out.append((q[0] - ratio * (q[0] - p[0]), q[1] - ratio * (q[1] - p[1])))
        if not closed:
            out.append(pts[-1])
        pts = out
    return pts


def flatten(s, roundness=0.0):
    """The drawn polyline of a stroke (list of points; a closed stroke repeats its first point)."""
    if s.get("dot"):
        return [tuple(s["p"][0])]
    pts = chaikin(s["p"], 0.5 * roundness * 0.5, s.get("closed", False))
    if s.get("closed"):
        pts = pts + [pts[0]]
    return pts


def seg_len(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def length(pts):
    return sum(seg_len(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def sample(pts, step=0.05):
    """Points at roughly even spacing along a polyline."""
    if len(pts) == 1:
        return [pts[0]] * 3
    out = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        n = max(1, int(seg_len(a, b) / step))
        for k in range(n):
            t = k / n
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    out.append(pts[-1])
    return out


def bbox(strokes, roundness=0.0):
    xs, ys = [], []
    for s in strokes:
        pts = flatten(s, roundness)
        pad = s.get("r", 0) if s.get("dot") else 0
        for x, y in pts:
            xs += [x - pad, x + pad]
            ys += [y - pad, y + pad]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)


def transform(strokes, fx, fy):
    out = []
    for s in strokes:
        t = dict(s)
        t["p"] = [[round(fx(x), 4), round(fy(y), 4)] for x, y in s["p"]]
        out.append(t)
    return out


def place(strokes, box_to, box_from=(0.0, 0.0, 1.0, 1.0)):
    """Map strokes drawn in box_from onto box_to (x0, y0, x1, y1)."""
    fx0, fy0, fx1, fy1 = box_from
    tx0, ty0, tx1, ty1 = box_to
    sx = (tx1 - tx0) / (fx1 - fx0 or 1)
    sy = (ty1 - ty0) / (fy1 - fy0 or 1)
    out = transform(strokes, lambda x: tx0 + (x - fx0) * sx, lambda y: ty0 + (y - fy0) * sy)
    return out


def shift(strokes, dx=0.0, dy=0.0):
    return transform(strokes, lambda x: x + dx, lambda y: y + dy)


def mirror_x(strokes, width):
    return transform(strokes, lambda x: width - x, lambda y: y)


def svg_path(s, roundness=0.0, scale=100.0, ox=0.0, oy=0.0):
    """SVG path data (y flipped) for one non-dot stroke."""
    pts = flatten(s, roundness)
    cmds = []
    for i, (x, y) in enumerate(pts):
        cmds.append(("M" if i == 0 else "L") + f"{(x + ox) * scale:.1f} {(-(y) + oy) * scale:.1f}")
    return " ".join(cmds) + (" Z" if s.get("closed") else "")
