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


def fillet(pts, closed, roundness, kind="m", pin=()):
    """Round corners with quadratic curves that start and end on the two sides of the corner. kind: 'm' smooth (every
    corner rounded; runs of short segments blend into one curve), 's'/'b' sharp or blocky (no rounding), 'h' hybrid
    (right angles on the left half stay crisp, everything else is rounded). Returns (start, [("L", p) | ("Q", c, p)])."""
    pts = [tuple(p) for p in pts]
    n = len(pts)
    R = 0.6 * roundness
    if R <= 0.005 or n < 3 or kind in ("s", "b"):
        segs = [("L", p) for p in pts[1:]] + ([("L", pts[0])] if closed else [])
        return pts[0], segs
    mid = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2

    def cut(a, b, d):
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-9
        return (a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L)

    def corner(i):
        p, q, r = pts[i - 1], pts[i], pts[(i + 1) % n]
        l1, l2 = math.hypot(q[0] - p[0], q[1] - p[1]), math.hypot(r[0] - q[0], r[1] - q[1])
        d = min(R, 0.5 * l1, 0.5 * l2)
        if i in pin:                       # another stroke starts on this corner: keep the point sharp so they stay joined
            return None
        if kind == "h":
            v1, v2 = (p[0] - q[0], p[1] - q[1]), (r[0] - q[0], r[1] - q[1])
            c = (v1[0] * v2[0] + v1[1] * v2[1]) / ((l1 * l2) or 1e-9)
            if abs(math.degrees(math.acos(max(-1.0, min(1.0, c)))) - 90) <= 18 and q[0] <= mid + 1e-6:
                return None
        return cut(q, p, d), q, cut(q, r, d)

    idx = range(n) if closed else range(1, n - 1)
    cs = {i: corner(i) for i in idx}
    cs = {i: v for i, v in cs.items() if v}
    if closed:
        start = cs[0][2] if 0 in cs else pts[0]
        order = list(range(1, n)) + [0]
    else:
        start = pts[0]
        order = list(range(1, n))
    segs = []
    for i in order:
        if i in cs:
            a, q, b = cs[i]
            segs.append(("L", a))
            segs.append(("Q", q, b))
        else:
            segs.append(("L", pts[i]))
    return start, segs


def pin_junctions(strokes, tol=0.03):
    """Mark the corners of a stroke where another stroke begins or ends (a stem on the tip of a diamond), so smoothing leaves
    them sharp and the stroke stays attached. Returns the strokes, each with a "pin" list of point indices where needed."""
    ends = [tuple(p) for s in strokes if not s.get("dot") for p in (s["p"][0], s["p"][-1])]
    out = []
    for si, s in enumerate(strokes):
        if s.get("dot") or len(s["p"]) < 3:
            out.append(s)
            continue
        others = [tuple(p) for sj, t in enumerate(strokes) if sj != si and not t.get("dot") for p in (t["p"][0], t["p"][-1])]
        pin = [i for i, p in enumerate(s["p"]) if any(abs(p[0] - q[0]) < tol and abs(p[1] - q[1]) < tol for q in others)
               and (s.get("closed") or 0 < i < len(s["p"]) - 1)]
        out.append(dict(s, pin=pin) if pin else s)
    return out


def flatten(s, roundness=0.0):
    """The drawn polyline of a stroke (list of points; a closed stroke repeats its first point)."""
    if s.get("dot"):
        return [tuple(s["p"][0])]
    if roundness <= 0.005 or len(s["p"]) < 3:
        pts = [tuple(p) for p in s["p"]]
        return pts + [pts[0]] if s.get("closed") else pts
    start, segs = fillet(s["p"], s.get("closed", False), roundness, s.get("k", "m"), s.get("pin", ()))
    out, cur = [start], start
    for seg in segs:
        if seg[0] == "L":
            cur = seg[1]
            out.append(cur)
        else:
            c, e = seg[1], seg[2]
            for k in range(1, 7):
                t = k / 6
                out.append(((1 - t) ** 2 * cur[0] + 2 * t * (1 - t) * c[0] + t * t * e[0],
                            (1 - t) ** 2 * cur[1] + 2 * t * (1 - t) * c[1] + t * t * e[1]))
            cur = e
    return out


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
    """SVG path data (y flipped) for one non-dot stroke; corners become quadratic curves."""
    def f(p):
        return f"{(p[0] + ox) * scale:.1f} {(oy - p[1]) * scale:.1f}"
    start, segs = fillet(s["p"], s.get("closed", False), roundness, s.get("k", "m"), s.get("pin", ()))
    parts = ["M" + f(start)]
    for seg in segs:
        parts.append("L" + f(seg[1]) if seg[0] == "L" else "Q" + f(seg[1]) + " " + f(seg[2]))
    return " ".join(parts) + (" Z" if s.get("closed") else "")
