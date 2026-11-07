"""Generate Devanagari-like compound letters as stroke GRAPHS: a skeleton (top bar + stem or short descender, or bodies hanging straight from
the bar) plus 1-3 body strokes whose ends are placed on chosen junctions, following the connection patterns mined from the real letters
(../body_connections). Each body stroke is a chain of line/arc/cup units (../body_units), rotated and scaled so that its ends land exactly on
the targets (bar, descender foot, stem, the end or middle of an earlier stroke). Nothing is left floating: a free end is allowed only where
the real letters have one. usage: python3 compound_gen.py [n] [seed]"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "body_units"))
import body_gen as BG
HERE = os.path.dirname(os.path.abspath(__file__))
from rules import R, active
# Everything below that used to be a module constant is read from the ACTIVE profile (script_config) at call time: frame heights via R["BAR_Y"] / R["BASE_Y"] /
# R["BAR_GAP"] / R["DESC_Y"], and recipes() / skcfg() / hist() for the skeleton mix, anchor ranges and review history.
def skcfg(): return active().skeleton
def hist(): return active().history
def recipes():
    """name: (weight, skeletons).  Devanagari (2026-11-03 feedback): chain / branch / land read as Devanagari; 'close' (bar -> stem), 'twohang' and 'cross'
    were too copy-like, too bland or too disconnected and are switched off.  The mix is per-script data (script_config/<script>.json "recipes")."""
    return {k: (v["weight"], tuple(v["skeletons"])) for k, v in active().recipes.items()}

# ---------- geometry helpers (model coordinates, y down; headings in degrees, 90 = down) ----------
def hd(a, b): return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
def angdiff(a, b): return abs((a - b + 180) % 360 - 180)
def rot(p, a): c, s = math.cos(math.radians(a)), math.sin(math.radians(a)); return (p[0]*c - p[1]*s, p[0]*s + p[1]*c)
def tangent(P, i, k=4):
    a, b = max(0, i - k), min(len(P) - 1, i + k); return hd(P[a], P[b])
def start_dir(P):
    sh = getattr(P, "sh", None)
    return sh if sh is not None else hd(P[0], P[min(len(P) - 1, 3)])
def length(P): return sum(math.dist(a, b) for a, b in zip(P, P[1:]))

class St(list):
    """A polyline that remembers the unit boundaries (indices) and unit kinds / turns it was built from; .sh = its exact start heading (templates)."""
    meta = None
    sh = None

RAW_MODE = {"ct": False}      # templates.raw_ct when True (constructive), the random unit chains otherwise

def raw(rng, legacy=False, **kw):
    if RAW_MODE["ct"] and not legacy:
        import templates; return templates.raw_ct(rng, **kw)
    return raw_random(rng)

def raw_random(rng):
    seq, marks, pts, (units, h) = BG.walk(rng, "free")
    P = St((p[0], -p[1]) for p in pts)
    if rng.random() < .5: P = St((-x, y) for x, y in P)
    P.meta = (marks, units)
    return P, seq

AXES = (0, 90, 180, 270)
def axis_diff(h): return min(angdiff(h, a) for a in AXES)

def orient_ok(Q, relaxed=False):
    """Orientation rules (user, 2026-11-03): a stroke starts pointing along an axis; a big open curve opens up / down / left / right;
    an S stands upright. Both-ends-attached strokes (relaxed) may sit at about 45 degrees."""
    marks, units = Q.meta; n = len(Q); tol = R["RELAXED_TOL"] if relaxed else 22
    if n < 8: return False
    if axis_diff(start_dir(Q) if getattr(Q, 'sh', None) is not None else hd(Q[0], Q[2])) > (25 if relaxed else R["START_AXIS_TOL"]): return False
    bounds = [(marks[i], marks[i + 1] if i + 1 < len(units) else n - 1) for i in range(len(units))]
    for (k, tr, ln), (a, b) in zip(units, bounds):
        if k == "line" or abs(tr) < R["CUP_MIN_TURN"] or b - a < 4: continue
        U = [Q[j] for j in range(a, b + 1)]; ch = (U[-1][0] - U[0][0], U[-1][1] - U[0][1]); lc = math.hypot(*ch) or 1
        apex = max(U, key=lambda p: abs((p[0] - U[0][0]) * ch[1] - (p[1] - U[0][1]) * ch[0]) / lc)
        cen = (sum(p[0] for p in U) / len(U), sum(p[1] for p in U) / len(U))
        if axis_diff(hd(apex, cen)) > (tol if relaxed else R["CUP_OPEN_TOL"]): return False
    if not relaxed:
        for i in range(len(units) - 1):
            if units[i][0] == "D" and units[i + 1][0] == "D":
                def cen(a, b): U = [Q[j] for j in range(a, b + 1)]; return (sum(p[0] for p in U) / len(U), sum(p[1] for p in U) / len(U))
                c1, c2 = cen(*bounds[i]), cen(*bounds[i + 1])
                if axis_diff(hd(c1, c2)) > R["THREE_STACK_TOL"]: return False                          # a '3' stands upright (or lies exactly sideways)
            (k1, t1, _), (k2, t2, _) = units[i], units[i + 1]
            if k1 == "D" or k2 == "D" or k1 == "line" or k2 == "line": continue
            if t1 * t2 < 0 and abs(t1) >= 50 and abs(t2) >= 50:                        # an S: its ends stack vertically
                c = hd(Q[bounds[i][0]], Q[bounds[i + 1][1]])
                if min(angdiff(c, 90), angdiff(c, 270)) > R["S_UPRIGHT_TOL"]: return False
    return True

def _mk(P, f, sh=None):
    Q = St(f(p) for p in P); Q.meta = P.meta; Q.sh = sh; return Q

def place_free(P, start, heading, sc):
    a = heading - start_dir(P)
    return _mk(P, lambda p: (start[0] + rot((p[0]-P[0][0], p[1]-P[0][1]), a)[0] * sc, start[1] + rot((p[0]-P[0][0], p[1]-P[0][1]), a)[1] * sc), sh=heading if getattr(P, "sh", None) is not None else None)

def place_fit(P, start, end):
    ch = (P[-1][0] - P[0][0], P[-1][1] - P[0][1]); want = (end[0] - start[0], end[1] - start[1])
    lc, lw = math.hypot(*ch), math.hypot(*want)
    if lc < 12 or lw < 8: return None, 0
    a = math.degrees(math.atan2(want[1], want[0]) - math.atan2(ch[1], ch[0])); sc = lw / lc
    return _mk(P, lambda p: (start[0] + rot((p[0]-P[0][0], p[1]-P[0][1]), a)[0] * sc, start[1] + rot((p[0]-P[0][0], p[1]-P[0][1]), a)[1] * sc)), sc

# ---------- one letter ----------
def skeleton(rng, kind):
    if kind == "stem": S = rng.uniform(*skcfg()["stem_x"]); return {"kind": kind, "S": S}
    if kind == "desc": return {"kind": kind, "x": rng.uniform(*skcfg()["desc_x"]), "y": R["DESC_Y"]}
    return {"kind": kind}

def anchor(rng, sk, avoid=()):
    """A starting junction for the first body stroke: (point, allowed start-heading test, role)."""
    k = sk["kind"]
    if k == "stem":
        return (rng.uniform(skcfg()["stem_anchor_x"][0], sk["S"] - skcfg()["stem_anchor_gap"]), R["BAR_Y"]), (lambda h: angdiff(h, 90) <= 12), "bar"
    if k == "desc": return (sk["x"], sk["y"]), (lambda h: min(angdiff(h, 90), angdiff(h, 0), angdiff(h, 180)) <= 12), "desc"
    return (rng.uniform(*skcfg()["bar_anchor_x"]), R["BAR_Y"]), (lambda h: angdiff(h, 90) <= 12), "bar"

def att_point(P, rng, p_end=None):
    """Where a second stroke meets the first: usually at its very end (the user prefers joints at the bottoms of strokes)."""
    p_end = R["JOIN_AT_END_P"] if p_end is None else p_end
    if length(P) < R["SHORT_FIRST_LEN"] or rng.random() < p_end: return len(P) - 1, P[-1]
    return mid_point(P, rng)

def mid_point(P, rng, lo=.3, hi=.7):
    s = [0.0]
    for a, b in zip(P, P[1:]): s.append(s[-1] + math.dist(a, b))
    t = rng.uniform(lo, hi) * s[-1]
    i = next(j for j, v in enumerate(s) if v >= t); return i, P[i]

def extend_vertical(Q):
    """A stroke ending in a straight vertical run is drawn on down to the baseline (vertical bars are full height)."""
    marks, units = Q.meta
    if units and units[-1][0] == "line" and R["VERT_FULL_BOTTOM"] > Q[-1][1] and angdiff(hd(Q[-2], Q[-1]), 90) < 4:
        Qx = St(Q); Qx.meta = Q.meta; x = Q[-1][0]
        y = Q[-1][1]
        while y < R["BASE_Y"]: y = min(R["BASE_Y"], y + 1.5); Qx.append((x, y))
        return Qx
    return Q

def stroke_free(rng, start, test, axes=AXES, scale=(.8, 1.3), tries=120, relaxed=False, raw_kw=None):
    for _ in range(tries):
        P, seq = raw(rng, **(raw_kw or {}))
        h = rng.choice(axes) + (0 if RAW_MODE["ct"] else rng.uniform(-5, 5)); Q = place_free(P, start, h, rng.uniform(*scale))
        Q = extend_vertical(Q)
        if test(start_dir(Q)) and orient_ok(Q, relaxed): return Q, seq
    return None, None

def stroke_arrive(rng, tgt, ttan, tries=60):
    """A stroke that ENDS on a target (the middle or end of an earlier stroke), arriving along an axis that is not parallel to it; its start is free."""
    for _ in range(tries):
        P, seq = raw(rng)
        a = rng.choice([x for x in AXES if 40 <= angdiff(x, ttan) <= 140 or 40 <= angdiff(x, ttan + 180) <= 140]); a = float(a)
        rot_a = a - (hd(P[-4], P[-1]) if getattr(P, 'eh', None) is None else P.eh); sc = rng.uniform(.8, 1.3)
        Q = _mk(P, lambda p: (tgt[0] + rot((p[0] - P[-1][0], p[1] - P[-1][1]), rot_a)[0] * sc, tgt[1] + rot((p[0] - P[-1][0], p[1] - P[-1][1]), rot_a)[1] * sc))
        if orient_ok(Q) and axis_diff(hd(Q[-1], Q[-4])) <= 12: return Q, seq
    return None, None

def stroke_land(rng, start, end, test_start=None, tries=200, relaxed=False):
    for _ in range(tries):
        P, seq = raw(rng, legacy=True); Q, sc = place_fit(P, start, end)
        if Q is None or not (.55 <= sc <= 1.8): continue
        if test_start and not test_start(start_dir(Q)): continue
        if not orient_ok(Q, relaxed): continue
        if axis_diff(hd(Q[-1], Q[-4])) > (30 if relaxed else 16): continue                 # it also arrives along an axis
        return Q, seq
    return None, None

def build(rng, recipe, skel):
    sk = skeleton(rng, skel); strokes = []; J = []; seqs = []
    def add(Q, seq, role="body"): strokes.append(Q); seqs.append(seq)
    A, test, arole = anchor(rng, sk)
    S = sk.get("S")
    if recipe in ("chain", "branch", "land", "loop3", "twohang", "close"):
        if recipe == "close":
            # first stroke leaves the anchor and ends on the stem
            end = (S, rng.uniform(*skcfg()["stem_cross_y"])); Q, seq = stroke_land(rng, A, end, test)
            if Q is None: return None
            add(Q, seq); J.append(["red" if arole != "stem" else "touch", *A]); J.append(["touch", *end]); extra_stem_touch = True
            if arole == "stem": return None
        else:
            Q, seq = stroke_free(rng, A, test, (90,) if arole == "bar" else (90, 0, 180), raw_kw={"first": "bend"} if arole == "bar" else None)
            if Q is None: return None
            mk, un = Q.meta
            if un[0][0] == "line" and angdiff(hd(Q[0], Q[mk[1]] if len(mk) > 1 else Q[-1]), 90) < 6 and Q[min(len(Q) - 1, mk[1] if len(mk) > 1 else len(Q) - 1)][1] < 84: return None
            add(Q, seq); J.append(["red", *A])
    if recipe == "chain" or recipe == "loop3":
        e = strokes[0][-1]; t = tangent(strokes[0], len(strokes[0]) - 1)
        axes = [a for a in AXES if angdiff(a, t + 180) > 60]                # never straight back along the first stroke
        Q, seq = stroke_free(rng, e, lambda hh: True, axes)
        if Q is None: return None
        add(Q, seq); J.append(["touch", *e])
        if recipe == "loop3":
            i, tgt = mid_point(strokes[0], rng); e2 = strokes[1][-1]
            Q, seq = stroke_land(rng, e2, tgt, lambda hh: True, relaxed=True)
            if Q is None: return None
            add(Q, seq); J.append(["touch", *e2]); J.append(["touch", *tgt])
    elif recipe == "branch":
        i, p = att_point(strokes[0], rng); t = tangent(strokes[0], i)
        side = rng.choice((-1, 1))
        Q, seq = stroke_free(rng, p, lambda hh: 40 <= angdiff(hh, t) <= 140 and (((hh - t + 180) % 360 - 180) * side > 0), AXES, tries=250)
        if Q is None: return None
        add(Q, seq); J.append(["touch", *p])
    elif recipe == "land":
        i, tgt = att_point(strokes[0], rng)
        if RAW_MODE["ct"]:
            Q, seq = stroke_arrive(rng, tgt, tangent(strokes[0], i))
            if Q is not None and Q[0] == tgt: Q = None
        else:
            for _ in range(60):
                st = (rng.uniform(10, 90), rng.uniform(30, 84))
                Q, seq = stroke_land(rng, st, tgt, lambda hh: True, tries=8)
                if Q and 40 <= angdiff(hd(Q[-8], Q[-1]), tangent(strokes[0], i)) <= 140 and math.dist(st, tgt) > 18: break
                Q = None
        if Q is None: return None
        add(Q, seq); J.append(["touch", *tgt])
    elif recipe == "twohang":
        i, tgt = mid_point(strokes[0], rng, .35, .75)
        A2 = (rng.uniform(24, 76), R["BAR_Y"])
        Q, seq = stroke_land(rng, A2, tgt, lambda h: 55 <= h <= 125)
        if Q is None or math.dist(A2, A) < 14: return None
        add(Q, seq); J.append(["red", *A2]); J.append(["touch", *tgt])
    elif recipe == "cross":
        A = None
        for _ in range(80):
            st = (S - rng.uniform(14, 36), rng.uniform(34, 72))
            Q, seq = stroke_free(rng, st, lambda hh: angdiff(hh, 0) < 55)
            if Q and any((a[0] - S) * (b[0] - S) < 0 for a, b in zip(Q, Q[1:])): break
            Q = None
        if Q is None: return None
        x = next((a, b) for a, b in zip(Q, Q[1:]) if (a[0] - S) * (b[0] - S) < 0)
        yx = x[0][1] + (x[1][1] - x[0][1]) * (S - x[0][0]) / (x[1][0] - x[0][0])
        if not (34 <= yx <= 76): return None
        add(Q, seq); J.append(["cross", S, yx])
        # and a second, ordinary body from the bar so the letter has substance
        Q2, seq2 = stroke_free(rng, (rng.uniform(26, S - 18), R["BAR_Y"]), lambda h: 55 <= h <= 125)
        if Q2 is None: return None
        add(Q2, seq2); J.append(["red", Q2[0][0], BAR])
    return {"sk": sk, "strokes": strokes, "J": J, "seqs": seqs, "recipe": recipe, "skel": skel}

# ---------- checks ----------
def stroke_ok(P):
    """Shape rules from the user's review: no closed / over-long loops, no free diagonal slashes."""
    xs = [p[0] for p in P]; ys = [p[1] for p in P]; L = length(P)
    if abs(total_turn(P)) > R["MAX_TURN"]: return False
    if max(max(xs) - min(xs), max(ys) - min(ys)) > R["MAX_SPAN"]: return False
    if L > R["RING_MIN_LEN"] and math.dist(P[0], P[-1]) < R["RING_FRAC"] * L: return False                    # a ring closed on itself
    marks, units = P.meta if getattr(P, "meta", None) else (None, None)
    if units:
        n = len(P)
        for i, (k, tr, ln) in enumerate(units):
            a_, b_ = marks[i], (marks[i + 1] if i + 1 < len(units) else n - 1)
            if b_ - a_ < 3: continue
            h0 = hd(P[a_], P[b_])
            if k == "line" and ln > R["LINE_MIN_LEN"] and axis_diff(h0) > R["LINE_AXIS_TOL"]: return False                 # lines are exactly vertical / horizontal
            if k == "line" and ln > R["VERT_MIN_LEN"] and min(angdiff(h0, 90), angdiff(h0, 270)) <= R["LINE_AXIS_TOL"] and max(P[a_][1], P[b_][1]) < R["VERT_FULL_BOTTOM"]: return False   # vertical bars are full height
            if k != "line" and abs(tr) < R["SLIGHT_TURN"] and ln > R["SLIGHT_MIN_LEN"] and min(angdiff(h0, 90), angdiff(h0, 270)) < R["SLIGHT_VERT_TOL"]: return False   # no slight curves hanging down
    return True

def thin2(P): return BG.thin([tuple(p) for p in P], 2.0)
def crowding(L, cols=4, rows=5):
    """Relative crowding for comparing two variants of one letter (never a cap: crossings and joins naturally stack strokes):
    sum over grid boxes of the strokes beyond two that pass through the box (bar and stem count as strokes)."""
    ink = [thin2(P) for P in L["strokes"]]; sk = L["sk"]
    def line(a, b, n=40): return [(a[0] + (b[0]-a[0])*k/n, a[1] + (b[1]-a[1])*k/n) for k in range(n + 1)]
    bar = L.get("bar")
    if bar: ink.append(line((bar[0], R["BAR_Y"]), (bar[1], R["BAR_Y"])))
    if sk["kind"] == "stem": ink.append(line((sk["S"], R["BAR_Y"]), (sk["S"], R["BASE_Y"])))
    if sk["kind"] == "desc": ink.append(line((sk["x"], R["BAR_Y"]), (sk["x"], R["DESC_Y"]), 10))
    x0, x1 = (bar[0], bar[1]) if bar else (min(p[0] for P in ink for p in P), max(p[0] for P in ink for p in P))
    cell = {}
    for k, P in enumerate(ink):
        for p in P:
            ix = min(max(int((p[0] - x0) / (x1 - x0) * cols), 0), cols - 1); iy = min(max(int((p[1] - R["BAR_Y"]) / (R["BASE_Y"] - R["BAR_Y"]) * rows), 0), rows - 1)
            cell.setdefault((ix, iy), set()).add(k)
    return sum(max(0, len(v) - 2) for v in cell.values())

def _thin_pts(L, bar=None):
    """All ink points of a letter (thinned strokes + bar/stem/descender lines), cached on L so max_void and white_fraction share one pass."""
    import numpy as np
    key = ("_pts", tuple(bar) if bar else None)
    c = L.setdefault("_cache", {})
    if key in c and c.get("_id") == id(L["strokes"]): return c[key]
    if c.get("_id") != id(L["strokes"]): c.clear(); c["_id"] = id(L["strokes"])
    ink = [thin2(P) for P in L["strokes"]]; sk = L["sk"]
    def line(a, b, n=40): return [(a[0] + (b[0]-a[0])*k/n, a[1] + (b[1]-a[1])*k/n) for k in range(n + 1)]
    bar = L.get("bar") or bar
    if bar: ink.append(line((bar[0], R["BAR_Y"]), (bar[1], R["BAR_Y"])))
    if sk["kind"] == "stem": ink.append(line((sk["S"], R["BAR_Y"]), (sk["S"], R["BASE_Y"])))
    if sk["kind"] == "desc": ink.append(line((sk["x"], R["BAR_Y"]), (sk["x"], R["DESC_Y"]), 10))
    c[key] = pts = np.array([p for P in ink for p in P])
    return pts

def _min_d2(g, p):
    """Squared distance from each grid point to its nearest ink point (matrix form: no 3-D temporary, no sqrt)."""
    import numpy as np
    d2 = (g * g).sum(1)[:, None] + (p * p).sum(1)[None, :] - 2.0 * (g @ p.T)
    return np.maximum(d2.min(1), 0.0)

def max_void(L):
    """Radius of the largest empty circle inside the letter frame (bar width x bar-to-baseline): the 'large open expanse' a reader sees."""
    import numpy as np
    pts = _thin_pts(L)
    bar = L.get("bar")
    x0, x1 = (bar[0], bar[1]) if bar else (pts[:, 0].min(), pts[:, 0].max())
    gx, gy = np.meshgrid(np.arange(x0, x1, 2.5), np.arange(R["BAR_Y"], R["BASE_Y"], 2.5)); g = np.stack([gx.ravel(), gy.ravel()], 1)
    return float(np.sqrt(_min_d2(g, pts[::2]).max()))

def aspect_dev(L):
    """|ln(width/height)| of the largest body stroke's box: 0 for a square-ish stroke.  Soft preference only (user: on average keep height and width about equal)."""
    P = max(L["strokes"], key=lambda P: (max(p[0] for p in P) - min(p[0] for p in P)) * (max(p[1] for p in P) - min(p[1] for p in P)))
    w = max(p[0] for p in P) - min(p[0] for p in P); h = max(p[1] for p in P) - min(p[1] for p in P)
    return abs(math.log(max(w, 1.0) / max(h, 1.0)))

def primary_size(L):
    """Largest single body stroke: its extent as a fraction of the bar width (across) or the letter height (down), whichever is larger."""
    bw = (L["bar"][1] - L["bar"][0]) if L.get("bar") else R["DEFAULT_BAR_W"]
    return max(max((max(p[0] for p in P) - min(p[0] for p in P)) / bw, (max(p[1] for p in P) - min(p[1] for p in P)) / (R["BASE_Y"] - R["BAR_Y"])) for P in L["strokes"])

def white_fraction(L, bw=None, bx0=None, r=None):
    """Share of the letter's frame (bar level down to the lowest ink, bar-wide) farther than WHITE_R from any ink."""
    import numpy as np
    r = R["WHITE_R"] if r is None else r
    pts = _thin_pts(L, None if L.get("bar") else ([bx0, bx0 + bw] if bw else None))
    x0, x1 = pts[:, 0].min(), pts[:, 0].max(); y1 = pts[:, 1].max()
    gx, gy = np.meshgrid(np.arange(x0, x1, 2.5), np.arange(R["BAR_Y"], y1, 2.5)); g = np.stack([gx.ravel(), gy.ravel()], 1)
    return float((_min_d2(g, pts[::3]) > r * r).mean())

def valid(L, minlen=None, size_rules=True):
    minlen = R["MIN_STROKE_LEN"] if minlen is None else minlen
    sk, St, J = L["sk"], L["strokes"], L["J"]; jp = [(j[1], j[2]) for j in J]
    S = sk.get("S")
    if sk["kind"] != "stem":                                          # bodies hang from the middle of the bar, not from an end
        x0, x1 = bar_span(L, min(p[0] for P in St for p in P))
        cs = [j[1] for j in J if abs(j[2] - R["BAR_Y"]) < .5] + ([sk["x"]] if sk["kind"] == "desc" else [])
        cx = sum(p[0] for P in St for p in P) / sum(len(P) for P in St)
        if x1 > R["EDGE_HI"] + .5 or not cs or not (R["BAR_CENTER_LO"] <= (cx - x0) / (x1 - x0) <= R["BAR_CENTER_HI"]) or not (R["ANCHOR_LO"] <= (sum(cs) / len(cs) - x0) / (x1 - x0) <= R["ANCHOR_HI"]): return False
    # review 1: the strokes together must fill the letter -- not leave a lot of unfilled whitespace (A1, A4, A7 originals were too sparse)
    if size_rules and primary_size(L) < R["PRIMARY_MIN"]: return False
    for i, P in enumerate(St):
        if not stroke_ok(P): return False
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        if min(xs) < R["EDGE_LO"] or max(xs) > R["EDGE_HI"] or max(ys) > R["BASE_Y"] or min(ys) < R["BAR_Y"] - .5: return False
        if not (minlen <= length(P) <= R["MAX_STROKE_LEN"]): return False
        s = 0.0
        for a, b in zip(P, P[1:]):                                  # keep clear of the bar except right at a bar junction
            s += math.dist(a, b)
            if b[1] < R["BAR_Y"] + R["BAR_GAP"] - .5 and s > 8 and not (abs(b[1] - R["BAR_Y"]) < .5 and b is P[-1]): return False
        if BG.self_gap(P) < R["MIN_SELF_GAP"] or len(BG.crossings(P)) > (1 if L["recipe"] == "loop3" and False else 0): return False
        if S is not None and L["recipe"] != "cross" and max(xs) > S - 4 and True:
            if not any(math.dist((S, p[1]), p) < 1 for p in P) and not any((a[0] - S) * (b[0] - S) <= 0 for a, b in zip(P, P[1:])): return False   # a stroke reaching the stem must touch or cross it
    for i in range(len(St)):
        for j in range(i + 1, len(St)):
            A, Bq = thin2(St[i]), thin2(St[j])
            for a, b in zip(A, A[1:]):
                for c, d in zip(Bq, Bq[1:]):
                    if BG._seg_x(a, b, c, d) and not any(math.dist(((a[0]+b[0])/2, (a[1]+b[1])/2), q) < 3 for q in jp): return False
    # strokes keep clear of each other and of the stem / descender, except around their junctions
    def near_j(p): return any(math.dist(p, q) < 9 for q in jp)
    for i in range(len(St)):
        for j in range(i + 1, len(St)):
            A, Bq = thin2(St[i]), thin2(St[j])
            for p in A:
                if near_j(p): continue
                for q in Bq:
                    if near_j(q): continue
                    if math.dist(p, q) < R["MIN_STROKE_CLEAR"]: return False
        if sk["kind"] == "stem":
            for p in thin2(St[i]):
                if not near_j(p) and abs(p[0] - S) < R["STROKE_STEM_CLEAR"] and L["recipe"] != "cross": return False
        if sk["kind"] == "desc":
            for p in thin2(St[i]):
                if not near_j(p) and abs(p[0] - sk["x"]) < R["STROKE_STEM_CLEAR"] and p[1] < sk["y"] + 6: return False
    # the two numpy size tests run last: most candidates have already failed a cheaper geometric check by now
    if size_rules and sk["kind"] in ("stem", "desc") and max_void(L) > R["MAX_VOID"]: return False
    if size_rules and white_fraction(L, (x1 - x0) if sk["kind"] != "stem" else None, x0 if sk["kind"] != "stem" else None) > R["WHITE_MAX"]: return False
    return True

def total_turn(P): return BG.total_turn([tuple(p) for p in P])
def family(L):
    return (L["skel"], L["recipe"], tuple(total_turn(P) for P in L["strokes"]), any("D" in s for s in L["seqs"]))
def same_family(a, b):
    if a[:2] != b[:2] or a[3] != b[3]: return False
    return all(abs(x - y) < 110 for x, y in zip(a[2], b[2]))

def finish(L):
    sk = L["sk"]; pts = [p for P in L["strokes"] for p in P]
    contacts = [j[1] for j in L["J"] if abs(j[2] - R["BAR_Y"]) < .5] + ([sk["S"]] if sk["kind"] == "stem" else [])
    if sk["kind"] == "stem": x1 = sk["S"] + BG.__dict__.get("OVER", 8)
    elif contacts: x1 = max(contacts) + 8
    else: x1 = None
    return L, x1

def bar_span(L, left):
    """Standard bar: from the left of the ink to 8 past the last contact, never narrower than 56."""
    sk = L["sk"]; cont = [j[1] for j in L["J"] if abs(j[2] - R["BAR_Y"]) < .5]
    x1 = (sk["S"] + R["BAR_OVERHANG"]) if sk["kind"] == "stem" else (max(cont) + R["BAR_OVERHANG"] if cont else sk.get("x", 50) + R["BAR_OVERHANG"])
    if sk["kind"] != "stem": x1 = max(x1, max(p[0] for P in L["strokes"] for p in P) + 2)       # the bar always covers the body
    x0 = min(left - 2, sk.get("x", 99) - 4)
    if x1 - x0 < R["BAR_MIN_WIDTH"] and sk["kind"] != "stem":                      # a narrow letter gets a standard-width bar centred on it
        c = (x0 + x1) / 2; x0, x1 = c - R["BAR_MIN_WIDTH"] / 2, c + R["BAR_MIN_WIDTH"] / 2
    elif x1 - x0 < R["BAR_MIN_WIDTH"]: x0 = x1 - R["BAR_MIN_WIDTH"]
    x0 = max(R["BAR_X_LO"], x0); x1 = min(R["BAR_X_HI"], max(x1, x0 + R["BAR_MIN_WIDTH"])); return x0, x1

# review history (per-script data, "history" in the config): letters the user called near copies, and the picks that seed a run
def rejected(fname): return hist()["rejected"].get(fname, [])          # letters of an earlier round the user called near copies
def seeds(): return list(hist()["seeds"])                              # the picks of the first round that seed a run

def fix_seed(v, idx):
    """Apply the 2026-11-03 12:58 rules to a kept letter: a short blue vertical from the bar becomes a purple descender of the standard
    height; a second stroke that meets the first in its middle meets it at its end instead (the tail beyond the joint is dropped)."""
    DESC_Y = R["DESC_Y"]; SHORT_BLUE = set(hist()["short_blue"]); JOIN_AT_END = set(hist()["join_at_end"])    # user: short blue verticals of random height -> purple descender of standard height
    St0 = [list(map(tuple, P)) for P in v["strokes"]]; J = [list(j) for j in v["J"]]; descs = []; sk = dict(v["sk"]); skel = v["skel"]
    P = St0[0]
    if idx in SHORT_BLUE and abs(P[0][1] - R["BAR_Y"]) < .6 and len(P) > 4 and abs(P[1][0] - P[0][0]) < .4:
        k = 1
        while k + 1 < len(P) and abs(P[k + 1][0] - P[0][0]) < .5 and P[k + 1][1] > P[k][1]: k += 1
        ye = P[k][1]
        if ye < 84:                                              # a short vertical blue stroke of intermediate height
            if ye < DESC_Y: return None
            cut = next(j for j, p in enumerate(P) if p[1] >= DESC_Y)
            St0[0] = [(P[0][0], DESC_Y)] + P[cut + 1:]
            descs.append([round(P[0][0], 1), DESC_Y])
            for j in J:
                if abs(j[2] - R["BAR_Y"]) < .5 and abs(j[1] - P[0][0]) < .6: j[2] = DESC_Y
    P = St0[0]
    for j in J:                                                   # a touch on the first stroke's interior -> make it the end
        if idx not in JOIN_AT_END or j[0] != "touch": continue
        i = min(range(len(P)), key=lambda q: math.dist(P[q], (j[1], j[2])))
        if math.dist(P[i], (j[1], j[2])) < 1.2 and 4 < i < len(P) - 4:
            St0[0] = P[:i + 1]; break
    seqs = list(v["seqs"])
    if length(St0[0]) < 12 and len(St0) > 1:                       # only a stub of the blue stroke is left: the joint sits on the descender's foot
        foot = (descs[0][0], DESC_Y) if descs else None
        St0.pop(0); seqs.pop(0)
        if foot:
            for Q in St0:
                for end in (0, -1):
                    if math.dist(Q[end], foot) < 6: Q[end] = foot
            J = [j for j in J if not (j[0] == "touch" and math.dist((j[1], j[2]), foot) < 6)]
            J.append(["red", foot[0], foot[1]]) if not any(math.dist((j[1], j[2]), foot) < .6 for j in J) else None
    if skel == "desc":                                              # uniform descender height
        dy = sk["y"] - DESC_Y; sk["y"] = DESC_Y
        for Q in St0:
            if math.dist(Q[0], (sk["x"], R["BAR_Y"] + (v["sk"]["y"] - R["BAR_Y"]))) < 1: Q[0] = (Q[0][0], DESC_Y)
        for j in J:
            if abs(j[1] - sk["x"]) < .6 and abs(j[2] - v["sk"]["y"]) < .6: j[2] = DESC_Y
    L = {"sk": sk, "strokes": St0, "J": J, "seqs": seqs, "recipe": v["recipe"], "skel": skel}
    return L, descs

def generate(n=40, seed=1):
    rng = random.Random(seed); out = []; fams = []; ink = []; tries = 0
    RECIPES = recipes(); names = list(RECIPES); wts = [RECIPES[k][0] for k in names]
    for i in rejected("letters_v7.json"):                                           # near copies of C12 and C14 in version 7
        v = json.load(open(os.path.join(HERE, "letters_v7.json")))[i - 1]
        ink.append([p for P in v["strokes"] for p in thin2(P)])
    for i in rejected("letters_v6.json"):                                           # near copies of C18 and C23 in version 6
        v = json.load(open(os.path.join(HERE, "letters_v6.json")))[i - 1]
        ink.append([p for P in v["strokes"] for p in thin2(P)])
    for i in rejected("letters_v5.json"):                                           # near-copies of kept letters, flagged by the user
        v = json.load(open(os.path.join(HERE, "letters_v5.json")))[i - 1]
        ink.append([p for P in v["strokes"] for p in thin2(P)])
    allv = json.load(open(os.path.join(HERE, "letters_v4.json")))
    for i in seeds():
        fx = fix_seed(allv[i - 1], i)
        if fx is None: print("seed C%d dropped: its vertical is too short to become a standard descender" % i); continue
        L, descs = fx
        if not valid(L, 10): print("seed C%d dropped: fails the shape checks after its fix" % i); continue
        pts = [p for P in L["strokes"] for p in thin2(P)]
        x0, x1 = bar_span(L, min(p[0] for p in pts))
        if any(BG.chamfer(pts, q) < 5 for q in ink) or any(same_family(family(L), g) for g in fams): print("seed C%d dropped: a near copy of another kept letter" % i); continue
        fams.append(family(L)); ink.append(pts)
        out.append({"skel": L["skel"], "recipe": L["recipe"], "sk": L["sk"], "bar": [round(x0, 1), round(x1, 1)], "descs": descs, "seed": i,
                    "J": [[j[0], round(j[1], 1), round(j[2], 1)] for j in L["J"]],
                    "strokes": [[[round(p[0], 1), round(p[1], 1)] for p in P] for P in L["strokes"]], "seqs": L["seqs"]})
    while len(out) < n and tries < 150000:
        tries += 1
        r = rng.choices(names, wts)[0]; skel = rng.choice(RECIPES[r][1])
        L = build(rng, r, skel)
        if not L or not valid(L): continue
        f = family(L)
        if any(same_family(f, g) for g in fams): continue
        pts = [p for P in L["strokes"] for p in thin2(P)]
        if any(BG.chamfer(pts, q) < 8 for q in ink): continue
        fams.append(f); ink.append(pts)
        sk = L["sk"]; left = min(p[0] for p in pts)
        bar_x0, bar_x1 = bar_span(L, left)
        out.append({"skel": skel, "recipe": r, "sk": sk, "bar": [round(bar_x0, 1), round(bar_x1, 1)], "J": [[j[0], round(j[1], 1), round(j[2], 1)] for j in L["J"]],
                    "strokes": [[[round(p[0], 1), round(p[1], 1)] for p in P] for P in L["strokes"]], "seqs": L["seqs"]})
    return out, tries

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    G, tries = generate(n, seed)
    json.dump(G, open(os.path.join(HERE, "letters.json"), "w"), separators=(",", ":"))
    from collections import Counter
    print(len(G), "letters in", tries, "tries;", Counter(g["recipe"] for g in G), Counter(g["skel"] for g in G))
