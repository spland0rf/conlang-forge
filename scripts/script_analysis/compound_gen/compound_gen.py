"""Generate Devanagari-like compound letters as stroke GRAPHS: a skeleton (top bar + stem or short descender, or bodies hanging straight from
the bar) plus 1-3 body strokes whose ends are placed on chosen junctions, following the connection patterns mined from the real letters
(../body_connections). Each body stroke is a chain of line/arc/cup units (../body_units), rotated and scaled so that its ends land exactly on
the targets (bar, descender foot, stem, the end or middle of an earlier stroke). Nothing is left floating: a free end is allowed only where
the real letters have one. usage: python3 compound_gen.py [n] [seed]"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "body_units"))
import body_gen as BG
HERE = os.path.dirname(os.path.abspath(__file__))
BAR, GAP, BASE = 20.0, 7.0, 88.0

RECIPES = {   # name: (weight, skeletons) -- 2026-11-03 feedback: chain / branch / land (and the 3-stroke loop) read as Devanagari;
    # 'close' (bar -> stem), 'twohang' and 'cross' were too copy-like, too bland or too disconnected and are switched off.
    "chain":  (13, ("stem", "desc", "bar")),
    "branch": (16, ("stem", "desc", "bar")),
    "land":   (14, ("stem", "desc", "bar")),
}

# ---------- geometry helpers (model coordinates, y down; headings in degrees, 90 = down) ----------
def hd(a, b): return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
def angdiff(a, b): return abs((a - b + 180) % 360 - 180)
def rot(p, a): c, s = math.cos(math.radians(a)), math.sin(math.radians(a)); return (p[0]*c - p[1]*s, p[0]*s + p[1]*c)
def tangent(P, i, k=4):
    a, b = max(0, i - k), min(len(P) - 1, i + k); return hd(P[a], P[b])
def start_dir(P): return hd(P[0], P[min(len(P) - 1, 3)])
def length(P): return sum(math.dist(a, b) for a, b in zip(P, P[1:]))

class St(list):
    """A polyline that remembers the unit boundaries (indices) and unit kinds / turns it was built from."""
    meta = None

def raw(rng):
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
    marks, units = Q.meta; n = len(Q); tol = 45 if relaxed else 22
    if n < 8: return False
    if axis_diff(hd(Q[0], Q[3])) > (25 if relaxed else 12): return False
    bounds = [(marks[i], marks[i + 1] if i + 1 < len(units) else n - 1) for i in range(len(units))]
    for (k, tr, ln), (a, b) in zip(units, bounds):
        if k == "line" or abs(tr) < 100 or b - a < 4: continue
        U = [Q[j] for j in range(a, b + 1)]; ch = (U[-1][0] - U[0][0], U[-1][1] - U[0][1]); lc = math.hypot(*ch) or 1
        apex = max(U, key=lambda p: abs((p[0] - U[0][0]) * ch[1] - (p[1] - U[0][1]) * ch[0]) / lc)
        cen = (sum(p[0] for p in U) / len(U), sum(p[1] for p in U) / len(U))
        if axis_diff(hd(apex, cen)) > tol: return False
    if not relaxed:
        for i in range(len(units) - 1):
            (k1, t1, _), (k2, t2, _) = units[i], units[i + 1]
            if k1 == "D" or k2 == "D" or k1 == "line" or k2 == "line": continue
            if t1 * t2 < 0 and abs(t1) >= 50 and abs(t2) >= 50:                        # an S: its ends stack vertically
                c = hd(Q[bounds[i][0]], Q[bounds[i + 1][1]])
                if min(angdiff(c, 90), angdiff(c, 270)) > 30: return False
    return True

def _mk(P, f):
    Q = St(f(p) for p in P); Q.meta = P.meta; return Q

def place_free(P, start, heading, sc):
    a = heading - start_dir(P)
    return _mk(P, lambda p: (start[0] + rot((p[0]-P[0][0], p[1]-P[0][1]), a)[0] * sc, start[1] + rot((p[0]-P[0][0], p[1]-P[0][1]), a)[1] * sc))

def place_fit(P, start, end):
    ch = (P[-1][0] - P[0][0], P[-1][1] - P[0][1]); want = (end[0] - start[0], end[1] - start[1])
    lc, lw = math.hypot(*ch), math.hypot(*want)
    if lc < 12 or lw < 8: return None, 0
    a = math.degrees(math.atan2(want[1], want[0]) - math.atan2(ch[1], ch[0])); sc = lw / lc
    return _mk(P, lambda p: (start[0] + rot((p[0]-P[0][0], p[1]-P[0][1]), a)[0] * sc, start[1] + rot((p[0]-P[0][0], p[1]-P[0][1]), a)[1] * sc)), sc

# ---------- one letter ----------
def skeleton(rng, kind):
    if kind == "stem": S = rng.uniform(60, 76); return {"kind": kind, "S": S}
    if kind == "desc": return {"kind": kind, "x": rng.uniform(40, 60), "y": rng.uniform(33, 40)}
    return {"kind": kind}

def anchor(rng, sk, avoid=()):
    """A starting junction for the first body stroke: (point, allowed start-heading test, role)."""
    k = sk["kind"]
    if k == "stem":
        return (rng.uniform(26, sk["S"] - 16), BAR), (lambda h: angdiff(h, 90) <= 12), "bar"
    if k == "desc": return (sk["x"], sk["y"]), (lambda h: min(angdiff(h, 90), angdiff(h, 0), angdiff(h, 180)) <= 12), "desc"
    return (rng.uniform(28, 72), BAR), (lambda h: angdiff(h, 90) <= 12), "bar"

def mid_point(P, rng, lo=.3, hi=.7):
    s = [0.0]
    for a, b in zip(P, P[1:]): s.append(s[-1] + math.dist(a, b))
    t = rng.uniform(lo, hi) * s[-1]
    i = next(j for j, v in enumerate(s) if v >= t); return i, P[i]

def stroke_free(rng, start, test, axes=AXES, scale=(.8, 1.3), tries=120, relaxed=False):
    for _ in range(tries):
        P, seq = raw(rng)
        h = rng.choice(axes) + rng.uniform(-8, 8); Q = place_free(P, start, h, rng.uniform(*scale))
        if test(start_dir(Q)) and orient_ok(Q, relaxed): return Q, seq
    return None, None

def stroke_land(rng, start, end, test_start=None, tries=200, relaxed=False):
    for _ in range(tries):
        P, seq = raw(rng); Q, sc = place_fit(P, start, end)
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
            end = (S, rng.uniform(46, 80)); Q, seq = stroke_land(rng, A, end, test)
            if Q is None: return None
            add(Q, seq); J.append(["red" if arole != "stem" else "touch", *A]); J.append(["touch", *end]); extra_stem_touch = True
            if arole == "stem": return None
        else:
            Q, seq = stroke_free(rng, A, test, (90,) if arole == "bar" else (90, 0, 180))
            if Q is None: return None
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
        i, p = mid_point(strokes[0], rng); t = tangent(strokes[0], i)
        side = rng.choice((-1, 1))
        Q, seq = stroke_free(rng, p, lambda hh: 40 <= angdiff(hh, t) <= 140 and (((hh - t + 180) % 360 - 180) * side > 0), AXES, tries=250)
        if Q is None: return None
        add(Q, seq); J.append(["touch", *p])
    elif recipe == "land":
        i, tgt = mid_point(strokes[0], rng)
        for _ in range(60):
            st = (rng.uniform(10, 90), rng.uniform(30, 84))
            Q, seq = stroke_land(rng, st, tgt, lambda hh: True, tries=8)
            if Q and 40 <= angdiff(hd(Q[-8], Q[-1]), tangent(strokes[0], i)) <= 140 and math.dist(st, tgt) > 18: break
            Q = None
        if Q is None: return None
        add(Q, seq); J.append(["touch", *tgt])
    elif recipe == "twohang":
        i, tgt = mid_point(strokes[0], rng, .35, .75)
        A2 = (rng.uniform(24, 76), BAR)
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
        Q2, seq2 = stroke_free(rng, (rng.uniform(26, S - 18), BAR), lambda h: 55 <= h <= 125)
        if Q2 is None: return None
        add(Q2, seq2); J.append(["red", Q2[0][0], BAR])
    return {"sk": sk, "strokes": strokes, "J": J, "seqs": seqs, "recipe": recipe, "skel": skel}

# ---------- checks ----------
def stroke_ok(P):
    """Shape rules from the user's review: no closed / over-long loops, no free diagonal slashes."""
    xs = [p[0] for p in P]; ys = [p[1] for p in P]; L = length(P)
    if abs(total_turn(P)) > 300: return False
    if max(max(xs) - min(xs), max(ys) - min(ys)) > 45: return False
    if L > 70 and math.dist(P[0], P[-1]) < .25 * L: return False                    # a ring closed on itself
    Q = BG.thin([tuple(p) for p in P], 2.0); i = 0
    while i < len(Q) - 4:                                                              # straight runs
        h0 = hd(Q[i], Q[i + 2]); j = i + 2
        while j + 1 < len(Q) and angdiff(hd(Q[j], Q[j + 1]), h0) < 14 and angdiff(hd(Q[i], Q[j + 1]), h0) < 8: j += 1
        run = math.dist(Q[i], Q[j])
        if run > 16:
            vert = min(angdiff(h0, 90), angdiff(h0, 270)) <= 15; hor = min(angdiff(h0, 0), angdiff(h0, 180)) <= 15
            near_vert = min(angdiff(h0, 90), angdiff(h0, 270)) <= 32 and run <= 32
            if not (vert or hor or near_vert): return False
        i = max(j, i + 1)
    return True

def thin2(P): return BG.thin([tuple(p) for p in P], 2.0)
def valid(L):
    sk, St, J = L["sk"], L["strokes"], L["J"]; jp = [(j[1], j[2]) for j in J]
    S = sk.get("S")
    for i, P in enumerate(St):
        if not stroke_ok(P): return False
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        if min(xs) < 6 or max(xs) > 94 or max(ys) > BASE or min(ys) < BAR - .5: return False
        if not (18 <= length(P) <= 150): return False
        s = 0.0
        for a, b in zip(P, P[1:]):                                  # keep clear of the bar except right at a bar junction
            s += math.dist(a, b)
            if b[1] < BAR + GAP - .5 and s > 8 and not (abs(b[1] - BAR) < .5 and b is P[-1]): return False
        if BG.self_gap(P) < 7 or len(BG.crossings(P)) > (1 if L["recipe"] == "loop3" and False else 0): return False
        if S is not None and L["recipe"] != "cross" and max(xs) > S - 4 and True:
            if not any(math.dist((S, p[1]), p) < 1 for p in P): return False
    # strokes keep clear of each other and of the stem / descender, except around their junctions
    def near_j(p): return any(math.dist(p, q) < 9 for q in jp)
    for i in range(len(St)):
        for j in range(i + 1, len(St)):
            A, Bq = thin2(St[i]), thin2(St[j])
            for p in A:
                if near_j(p): continue
                for q in Bq:
                    if near_j(q): continue
                    if math.dist(p, q) < 5: return False
        if sk["kind"] == "stem":
            for p in thin2(St[i]):
                if not near_j(p) and abs(p[0] - S) < 5 and L["recipe"] != "cross": return False
        if sk["kind"] == "desc":
            for p in thin2(St[i]):
                if not near_j(p) and abs(p[0] - sk["x"]) < 5 and p[1] < sk["y"] + 6: return False
    return True

def total_turn(P): return BG.total_turn([tuple(p) for p in P])
def family(L):
    return (L["skel"], L["recipe"], tuple(total_turn(P) for P in L["strokes"]), any("D" in s for s in L["seqs"]))
def same_family(a, b):
    if a[:2] != b[:2] or a[3] != b[3]: return False
    return all(abs(x - y) < 110 for x, y in zip(a[2], b[2]))

def finish(L):
    sk = L["sk"]; pts = [p for P in L["strokes"] for p in P]
    contacts = [j[1] for j in L["J"] if abs(j[2] - BAR) < .5] + ([sk["S"]] if sk["kind"] == "stem" else [])
    if sk["kind"] == "stem": x1 = sk["S"] + BG.__dict__.get("OVER", 8)
    elif contacts: x1 = max(contacts) + 8
    else: x1 = None
    return L, x1

def bar_span(L, left):
    """Standard bar: from the left of the ink to 8 past the last contact, never narrower than 56."""
    sk = L["sk"]; cont = [j[1] for j in L["J"] if abs(j[2] - BAR) < .5]
    x1 = (sk["S"] + 8) if sk["kind"] == "stem" else (max(cont) + 8 if cont else sk.get("x", 50) + 8)
    x0 = min(left - 2, x1 - 56, sk.get("x", 99) - 4)
    x0 = max(8.0, x0); x1 = min(94.0, max(x1, x0 + 56)); return x0, x1

SEEDS = [9, 12, 19, 21, 25, 26, 38]          # the letters the user picked from the first round (letters_v1.json numbering), kept as they are

def generate(n=40, seed=1):
    rng = random.Random(seed); out = []; fams = []; ink = []; tries = 0
    names = list(RECIPES); wts = [RECIPES[k][0] for k in names]
    for i in SEEDS:
        v = json.load(open(os.path.join(HERE, "letters_v1.json")))[i - 1]
        L = {"sk": v["sk"], "strokes": v["strokes"], "J": v["J"], "seqs": v["seqs"], "recipe": v["recipe"], "skel": v["skel"]}
        pts = [p for P in L["strokes"] for p in thin2(P)]
        x0, x1 = bar_span(L, min(p[0] for p in pts))
        fams.append(family(L)); ink.append(pts)
        out.append(dict(v, bar=[round(x0, 1), round(x1, 1)], seed=i))
    while len(out) < n and tries < 40000:
        tries += 1
        r = rng.choices(names, wts)[0]; skel = rng.choice(RECIPES[r][1])
        L = build(rng, r, skel)
        if not L or not valid(L): continue
        f = family(L)
        if any(same_family(f, g) for g in fams): continue
        pts = [p for P in L["strokes"] for p in thin2(P)]
        if any(BG.chamfer(pts, q) < 7 for q in ink): continue
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
