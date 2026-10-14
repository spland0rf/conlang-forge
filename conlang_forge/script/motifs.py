"""Letter bodies. A body is grown on a coarse 5x5 grid inside a unit box: pick a skeleton (stem, ring, diagonal pair,
open curve, arch...), then grow attachments that start on existing ink, so connectivity holds by construction. Only
connectivity and coarse placement are chosen here; roundness is applied later when drawing."""
from __future__ import annotations

import math

from .geometry import mirror_x, stroke, transform
from .graph import TOL, analyse, points

G = (0.0, 0.25, 0.5, 0.75, 1.0)

# open curves and bent strokes (control points on or near the grid)
CURVES = {
    "C": [(1, .9), (.3, 1), (0, .5), (.3, 0), (1, .1)],
    "U": [(0, 1), (.05, .3), (.5, 0), (.95, .3), (1, 1)],
    "S": [(1, .9), (.3, 1), (0, .75), (.5, .5), (1, .25), (.7, 0), (0, .1)],
    "hook": [(.75, 1), (.75, .25), (.5, 0), (0, .1)],
    "tail": [(.25, 1), (.25, .2), (.5, 0), (1, 0)],
    "wave": [(0, .5), (.25, 1), (.5, .5), (.75, 0), (1, .5)],
    "corner": [(0, 1), (0, 0), (1, 0)],
    "zig": [(0, 0), (0, 1), (1, 0), (1, 1)],
    "Z": [(0, 1), (1, 1), (0, 0), (1, 0)],
    "V": [(0, 1), (.5, 0), (1, 1)],
    "W": [(0, 1), (.25, 0), (.5, .6), (.75, 0), (1, 1)],
    "curl": [(.2, .2), (.25, 1), (.9, .9), (.9, .45), (.5, .35)],
}
STRAIGHT = ["stem", "diag", "bar"]


def _snap(v):
    return min(G, key=lambda g: abs(g - v))


def _on_ink(strokes, p, tol=TOL * 0.6):
    """Is point p on one of the strokes' segments?"""
    for s in strokes:
        pts = s["p"] + ([s["p"][0]] if s.get("closed") else [])
        for a, b in zip(pts, pts[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            d2 = dx * dx + dy * dy or 1e-9
            t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / d2))
            if math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy)) <= tol:
                return True
    return False


def skeleton(rng, family, aspect_hint=0.8):
    """One base shape in the unit box."""
    if family == "stem":
        x = rng.choice([0.0, 0.25, 0.5, 0.75, 1.0]) if rng.random() < 0.5 else 0.5
        return [stroke([(x, 0), (x, 1)])]
    if family == "diag":
        return [stroke([(0, 0), (1, 1)])] if rng.random() < 0.5 else [stroke([(0, 1), (1, 0)])]
    if family == "bar":
        y = rng.choice([0.0, 0.5, 1.0])
        return [stroke([(0, y), (1, y)])]
    if family == "ring":
        return [stroke([(.5, 0), (.87, .13), (1, .5), (.87, .87), (.5, 1), (.13, .87), (0, .5), (.13, .13)], True)]
    if family == "arch":                                    # a stem with an arch (n, h shapes) or two stems and a bar
        kind = rng.choice(["n", "u", "H", "A"])
        if kind == "n":
            return [stroke([(0, 0), (0, 1)]), stroke([(0, .7), (.13, .93), (.5, 1), (.87, .93), (1, .7), (1, 0)])]
        if kind == "u":
            return [stroke([(0, 1), (0, .3), (.13, .07), (.5, 0), (.87, .07), (1, .3)]), stroke([(1, 1), (1, 0)])]
        if kind == "H":
            return [stroke([(0, 0), (0, 1)]), stroke([(1, 0), (1, 1)]), stroke([(0, .5), (1, .5)])]
        return [stroke([(0, 0), (.5, 1), (1, 0)]), stroke([(.25, .4), (.75, .4)])]
    if family == "fork":
        kind = rng.choice(["Y", "K", "T", "ψ"])
        if kind == "Y":
            return [stroke([(0, 1), (.5, .5), (1, 1)]), stroke([(.5, .5), (.5, 0)])]
        if kind == "K":
            return [stroke([(0, 0), (0, 1)]), stroke([(1, 1), (0, .5), (1, 0)])]
        if kind == "T":
            return [stroke([(0, 1), (1, 1)]), stroke([(.5, 1), (.5, 0)])]
        return [stroke([(0, 1), (0, .5), (.5, 0), (1, .5), (1, 1)]), stroke([(.5, 0), (.5, 1)])]
    c = CURVES[family]
    return [stroke(c)]


def _candidates(strokes):
    pts = []
    for s in strokes:
        base = [tuple(p) for p in s["p"]]
        pts += base
        for a, b in zip(base, base[1:]):
            pts.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    out = []
    for p in pts:
        sp = (round(_snap(p[0]), 3), round(_snap(p[1]), 3))
        q = p if _on_ink(strokes, sp) is False else sp
        if q not in out:
            out.append(q)
    return out


def grow(rng, strokes, loop_p, ortho=False):
    """Add one attachment starting on existing ink: a short walk over grid points, ending free or back on the ink."""
    cands = _candidates(strokes)
    for _ in range(12):
        a = rng.choice(cands)
        steps = rng.choice([1, 1, 2, 2, 3])
        path = [a]
        cur = a
        for _ in range(steps):
            dx, dy = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)] if ortho else
                                [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)])
            k = rng.choice([1, 1, 2])
            nx, ny = _snap(cur[0] + dx * 0.25 * k), _snap(cur[1] + dy * 0.25 * k)
            if (nx, ny) == cur or not (0 <= nx <= 1 and 0 <= ny <= 1):
                continue
            path.append((nx, ny))
            cur = (nx, ny)
        if len(path) < 2:
            continue
        if rng.random() < loop_p and len(path) >= 3:        # close back onto existing ink to make a loop
            tgt = [c for c in cands if c != path[-1] and math.hypot(c[0] - path[-1][0], c[1] - path[-1][1]) <= 0.55]
            if tgt:
                path.append(rng.choice(tgt))
        return strokes + [stroke(path)]
    return strokes


def valid(strokes, max_junctions, max_loops, max_ends):
    a = analyse(strokes)
    if a["parts"] != 1 or a["loops"] > max_loops or a["ends"] > max_ends or len(a["junctions"]) > max_junctions:
        return False
    if any(d > 4 for d in a["junctions"]):
        return False
    for s in strokes:
        p = s["p"] + ([s["p"][0]] if s.get("closed") else [])
        total = 0.0
        for u, v in zip(p, p[1:]):
            L = math.hypot(v[0] - u[0], v[1] - u[1])
            if L < 0.22:
                return False
            total += L
        if total < 0.42 and len(strokes) > 1:            # short stubs and scratches read as mistakes
            return False
        for u, v, w in zip(p, p[1:], p[2:]):             # no hairpin turns inside one stroke
            a1, a2 = math.atan2(v[1] - u[1], v[0] - u[0]), math.atan2(w[1] - v[1], w[0] - v[0])
            turn = abs((a2 - a1 + math.pi) % (2 * math.pi) - math.pi)
            if turn > math.radians(140):
                return False
    # nearly-touching but not touching strokes look like mistakes: demand clear gaps between unconnected strokes
    for i, s in enumerate(strokes):
        for t in strokes[i + 1:]:
            gap = _min_gap(s, t)
            if TOL * 0.8 < gap < 0.16:
                return False
            if gap <= TOL * 0.8 and _collinear_overlap(s, t):
                return False
    return not _redundant(strokes)


def _redundant(strokes):
    """True if some stroke lies entirely on top of the others (a doubled line)."""
    if len(strokes) < 2:
        return False
    for i, s in enumerate(strokes):
        mine = points([s], step=0.06)
        rest = points(strokes[:i] + strokes[i + 1:], step=0.03)
        if rest and all(min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in rest) < 0.04 for p in mine):
            return True
    return False


def _min_gap(s, t):
    pa, pb = points([s]), points([t])
    return min(math.hypot(p[0] - q[0], p[1] - q[1]) for p in pa for q in pb)


def _collinear_overlap(s, t):
    pa, pb = points([s], step=0.1), points([t], step=0.1)
    close = sum(1 for p in pa if min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in pb) < 0.03)
    return close >= 3


FAMILY_WEIGHTS = {
    "stem": 1.6, "diag": 0.5, "bar": 0.35, "ring": 1.7, "arch": 1.3, "fork": 1.0,
    "C": 0.9, "U": 0.7, "S": 0.5, "hook": 0.9, "tail": 0.7, "wave": 0.25, "corner": 0.4, "zig": 0.5, "Z": 0.3, "V": 0.5,
    "W": 0.2, "curl": 0.4,
}


def make_body(rng, density, loops, weights=None):
    """A connected body in the unit box. density 0..1 sets how many attachments; loops 0..1 how often loops arise."""
    w = dict(FAMILY_WEIGHTS)
    w["ring"] *= 0.3 + 1.6 * loops
    w["C"] *= 0.7 + 0.6 * loops
    if weights:
        w.update(weights)
    fams = list(w)
    for _ in range(200):
        fam = rng.choices(fams, [w[f] for f in fams])[0]
        strokes = skeleton(rng, fam)
        base = len(analyse(strokes)["junctions"])
        k = 0
        while k < 3 and rng.random() < (0.25 + 0.55 * density if k == 0 else 0.1 + 0.45 * density):
            k += 1
        if fam in ("arch", "fork") and k > 1:
            k = 1
        for _ in range(k):
            strokes = grow(rng, strokes, loops * 0.45)
        # random orientation flips multiply the variety (and are the basis of mirror families)
        if rng.random() < 0.5:
            strokes = mirror_x(strokes, 1.0)
        if rng.random() < 0.25:
            strokes = transform(strokes, lambda x: x, lambda y: 1 - y)
        if valid(strokes, max_junctions=1 + int(2.2 * density) + base, max_loops=2 if loops > 0.5 else 1, max_ends=4 + int(2 * density)):
            return strokes, fam
    return skeleton(rng, "stem"), "stem"


# ---------------------------------------------------------------------------------------------------------------
# Corner styles. A letter is drawn in exactly one way: sharp (V A W: crisp angular corners), smooth (O G S: every
# corner rounded), blocky (E H F: right angles only) or hybrid (D B P: crisp right angles beside rounded curves).
# Sharp and smooth are never mixed inside one letter.

RIGHT, GENTLE = 18.0, 125.0         # interior angle within 90 +- RIGHT is a right angle; >= GENTLE is part of a curve


def _interior(p, q, r):
    v1, v2 = (p[0] - q[0], p[1] - q[1]), (r[0] - q[0], r[1] - q[1])
    l1, l2 = math.hypot(*v1), math.hypot(*v2)
    c = (v1[0] * v2[0] + v1[1] * v2[1]) / ((l1 * l2) or 1e-9)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def classify(strokes):
    """Count right-angle, gentle (curve-like) and angular (acute or oblique) corners, including the angles where two
    strokes end at the same point, and whether any segment is diagonal."""
    right = gentle = angular = diag = apex = 0
    for s in strokes:
        if s.get("dot"):
            continue
        p = [tuple(x) for x in s["p"]]
        n = len(p)
        for i in (range(n) if s.get("closed") else range(1, n - 1)):
            a = _interior(p[i - 1], p[i], p[(i + 1) % n])
            if abs(a - 90) <= RIGHT:
                right += 1
            elif a >= GENTLE:
                gentle += 1
            else:
                angular += 1
        for u, v in zip(p, p[1:] + ([p[0]] if s.get("closed") else [])):
            ang = abs(math.degrees(math.atan2(v[1] - u[1], v[0] - u[0]))) % 90
            if 12 < ang < 78:
                diag += 1
    ends = []
    for si, s in enumerate(strokes):
        if s.get("dot") or s.get("closed") or len(s["p"]) < 2:
            continue
        ends.append((s["p"][0], s["p"][1]))
        ends.append((s["p"][-1], s["p"][-2]))
    for i, (a, na) in enumerate(ends):
        for b, nb in ends[i + 1:]:
            if math.hypot(a[0] - b[0], a[1] - b[1]) <= TOL:
                ang = _interior(na, a, nb)
                if abs(ang - 90) <= RIGHT:
                    right += 1
                elif ang < 160:
                    angular += 1
                    apex += 1
    return {"right": right, "gentle": gentle, "angular": angular, "diagonal": diag, "apex": apex}


def _ortho_skeleton(rng):
    k = rng.choices(["stem", "bar", "rect", "U", "C", "S", "hook", "step", "L", "H", "T", "E", "F", "P", "Z", "Pi", "J", "step2", "cross", "angle", "Gam", "perp", "ladder", "Ee"],
                    [1.2, .3, 1.3, 1, 1, .6, 1, .8, 1, .8, .8, .6, .6, .7, .5, .8, .8, .7, .6, .7, .7, .7, .5, .5])[0]
    y0 = rng.choice([0, .5, 1])
    x0 = rng.choice([0, .5, .5, 1])
    return k, {
        "stem": lambda: [stroke([(x0, 0), (x0, 1)])],
        "Pi": lambda: [stroke([(0, 0), (0, 1), (1, 1), (1, .4)])],
        "J": lambda: [stroke([(0, .4), (0, 0), (1, 0), (1, 1)])],
        "step2": lambda: [stroke([(0, 0), (0, .33), (.5, .33), (.5, .66), (1, .66), (1, 1)])],
        "cross": lambda: [stroke([(.5, 0), (.5, 1)]), stroke([(0, .5), (1, .5)])],
        "angle": lambda: [stroke([(0, 1), (1, 1), (1, 0)])],
        "Gam": lambda: [stroke([(0, 0), (0, 1), (1, 1)])],
        "perp": lambda: [stroke([(0, 0), (1, 0)]), stroke([(.5, 0), (.5, 1)])],
        "ladder": lambda: [stroke([(0, 0), (0, 1)]), stroke([(1, 0), (1, 1)]), stroke([(0, .33), (1, .33)]), stroke([(0, .66), (1, .66)])],
        "Ee": lambda: [stroke([(0, 1), (1, 1)]), stroke([(0, 1), (0, 0)]), stroke([(0, .5), (.7, .5)]), stroke([(0, 0), (1, 0)])],
        "Z": lambda: [stroke([(0, 1), (1, 1), (1, .5), (0, .5), (0, 0), (1, 0)])],
        "bar": lambda: [stroke([(0, y0), (1, y0)])],
        "rect": lambda: [stroke([(0, 0), (1, 0), (1, 1), (0, 1)], True)],
        "U": lambda: [stroke([(0, 1), (0, 0), (1, 0), (1, 1)])],
        "C": lambda: [stroke([(1, 1), (0, 1), (0, 0), (1, 0)])],
        "S": lambda: [stroke([(1, 1), (0, 1), (0, .5), (1, .5), (1, 0), (0, 0)])],
        "hook": lambda: [stroke([(.75, 1), (.75, 0), (0, 0)])],
        "step": lambda: [stroke([(0, 0), (0, .5), (1, .5), (1, 1)])],
        "L": lambda: [stroke([(0, 1), (0, 0), (1, 0)])],
        "H": lambda: [stroke([(0, 0), (0, 1)]), stroke([(1, 0), (1, 1)]), stroke([(0, .5), (1, .5)])],
        "T": lambda: [stroke([(0, 1), (1, 1)]), stroke([(.5, 1), (.5, 0)])],
        "E": lambda: [stroke([(1, 1), (0, 1), (0, 0), (1, 0)]), stroke([(0, .5), (.75, .5)])],
        "F": lambda: [stroke([(1, 1), (0, 1), (0, 0)]), stroke([(0, .5), (.75, .5)])],
        "P": lambda: [stroke([(0, 0), (0, 1), (1, 1), (1, .5), (0, .5)])],
    }[k]()


def _ortho_body(rng, density, loops):
    for _ in range(100):
        fam = None
        fam, strokes = _ortho_skeleton(rng)
        k = 0
        while k < 3 and rng.random() < (0.15 + 0.55 * density):
            k += 1
        for _ in range(k):
            strokes = grow(rng, strokes, loops * 0.3, ortho=True)
        if valid(strokes, 1 + int(2.2 * density) + 1, 2 if loops > 0.5 else 1, 4 + int(2 * density)):
            c = classify(strokes)
            if c["angular"] == 0 and c["gentle"] == 0 and c["diagonal"] == 0:
                return strokes, fam
    return [stroke([(.5, 0), (.5, 1)])], "stem"


def _tag(strokes, kind):
    return [dict(s, k=kind) if not s.get("dot") else s for s in strokes]


def make_styled_body(rng, density, loops, weights=None, style="mixed"):
    """A body plus its drawing kind: 's' sharp, 'm' smooth, 'b' blocky, 'h' hybrid. style is the script's corner_style
    (smooth, sharp, blocky or mixed)."""
    for _ in range(80):
        if style == "blocky":
            body, fam = _ortho_body(rng, density, loops)
            return _tag(body, "b"), fam, "b"
        body, fam = make_body(rng, density, loops, weights)
        c = classify(body)
        if style == "smooth":
            if c["apex"]:
                continue
            kind = "m"
        elif style == "sharp":
            kind = "s"
        else:                                   # mixed: each stroke is sharp, smooth, blocky or hybrid on its own
            pref = "m" if rng.random() < 0.45 else "s"          # how this letter treats its angular strokes
            tagged, kinds = [], []
            for st in body:
                c1 = classify([st]) if not st.get("dot") else {"angular": 0, "gentle": 0, "right": 0}
                if c1["angular"]:
                    k1 = pref
                elif c1["gentle"]:
                    k1 = "h" if c1["right"] and rng.random() < 0.6 else "m"
                elif c1["right"]:
                    k1 = rng.choices(["b", "m", "h"], [0.5, 0.3, 0.2])[0]
                else:
                    k1 = None                      # a straight stroke: takes the letter's prevailing kind
                kinds.append(k1)
                tagged.append(st)
            main = next((k for k in kinds if k), pref)
            out = [dict(st, k=(k1 or main)) if not st.get("dot") else st for st, k1 in zip(tagged, kinds)]
            return out, fam, main
        return _tag(body, kind), fam, kind
    return _tag([stroke([(.5, 0), (.5, 1)])], "m"), "stem", "m"
