"""Generate new Devanagari-like body forms as chains of units (line / left arc / right arc / cusp), sampled from the units of the real
bodies (units.json): the number of units, the kind sequence (a Markov chain), each unit's length and turn (a real unit of that kind,
scaled by 0.75-1.3), the start heading and any cusp turn. Built by integrating a pen from the attach point. A body is kept only if it
stays inside the letter box, keeps the clear gap from the bar, is not a copy of a real body and not close to another new one.
usage: python3 body_gen.py [n] [seed] > bodies.json"""
import json, math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import script_config as SC
B = json.load(open(SC.path("units")))
BAR, GAP, BASE = 20.0, 7.0, 88.0

def kinds(b): return [u["kind"] for u in b["units"]]
COUNT = [len(b["units"]) for b in B]
START = [kinds(b)[0] for b in B]
TRANS = {}
for b in B:
    k = kinds(b)
    for a, c in zip(k, k[1:]): TRANS.setdefault(a, []).append(c)
UNITS = {k: [u for b in B for u in b["units"] if u["kind"] == k] for k in ("line", "L", "R")}
CUSPS = [u["jump"] for b in B for u in b["units"] if u["cusp_before"]]
CUSP_P = len(CUSPS) / max(1, sum(len(b["units"]) - 1 for b in B))
H0 = {"one": [b["units"][0]["h0"] for b in B if b["attach"] == "one"], "free": [b["units"][0]["h0"] for b in B if b["attach"] != "one"]}

def walk(rng, mode):
    n = min(4, rng.choice(COUNT))
    k = rng.choice(START); seq = [k]
    for _ in range(n - 1): seq.append(rng.choice(TRANS.get(seq[-1]) or ["line", "L", "R"]))
    h = rng.choice(H0[mode]) + rng.uniform(-12, 12)
    pts = [(0.0, 0.0)]; x = y = 0.0; marks = []; units = []; h_start = h
    DC_P, SHARP_P = 0.18, 0.15                      # a double cup replaces an arc; some joints become sharp (acute) cusps
    seq = ["D" if k in ("L", "R") and rng.random() < DC_P else k for k in seq]
    def arc(kind_, tr, ln):
        nonlocal h, x, y
        n_steps = max(2, int(ln / 1.5)); marks.append(len(pts) - 1); units.append((kind_, tr, ln))
        for s_ in range(n_steps):
            h += tr / n_steps
            x += math.cos(math.radians(h)) * ln / n_steps; y += math.sin(math.radians(h)) * ln / n_steps
            pts.append((x, y))
    for i, kind in enumerate(seq):
        if i and rng.random() < CUSP_P: h += rng.choice(CUSPS) * rng.uniform(.8, 1.1)
        elif i and rng.random() < SHARP_P: h += rng.choice((-1, 1)) * rng.uniform(110, 150)     # an acute joint between two strokes
        if kind == "D":                                  # a '3': two connected cups, one pen stroke, a sharp notch between them
            sd = rng.choice((-1, 1)); ln1, ln2 = rng.uniform(16, 30), rng.uniform(16, 30)
            arc("D", sd * rng.uniform(150, 190), ln1)
            h += -sd * rng.uniform(135, 170)
            arc("D", sd * rng.uniform(150, 190), ln2)
            continue
        u = rng.choice(UNITS[kind]); ln = u["len"] * rng.uniform(.75, 1.3); tr = u["turn"] * rng.uniform(.75, 1.3)
        arc(kind, tr if kind != "line" else 0.0, ln)
    return seq, marks, pts, (units, h_start)

def place(pts, mode, rng):
    """pts are in y-up pen coordinates from (0,0); return model coordinates (y down) at the attach point."""
    if mode == "one":
        S = rng.uniform(62, 74); ys = rng.uniform(36, 56); ox, oy = S, ys
    else:
        ox, oy = rng.uniform(34, 56), rng.uniform(33, 37)         # the lower end of a short descender
    return [(ox + p[0], oy - p[1]) for p in pts], (ox, oy)

def ok(P, mode, ox):
    xs, ys = [p[0] for p in P], [p[1] for p in P]
    if min(xs) < 6 or max(xs) > 94 or max(ys) > BASE or min(ys[1:]) < BAR + GAP - 0.5: return False
    if mode == "one" and max(xs) > ox + 1.5: return False          # a stem body stays on the stem's left
    L = sum(math.dist(a, b) for a, b in zip(P, P[1:]))
    return 25 <= L <= 190

def _seg_x(p, q, r, s):
    def o(a, b, c): return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    return o(p, q, r) * o(p, q, s) < 0 and o(r, s, p) * o(r, s, q) < 0

def crossings(P):
    P = thin(P, 2.0); out = []
    for i in range(len(P) - 1):
        for j in range(i + 4, len(P) - 1):
            if _seg_x(P[i], P[i+1], P[j], P[j+1]): out.append(((P[i][0]+P[j][0])/2, (P[i][1]+P[j][1])/2))
    return out

def self_gap(P):
    """Smallest distance between two parts of the path that are far apart along it and not at a crossing."""
    P = thin(P, 2.0); X = crossings(P); s = [0.0]
    for a, c in zip(P, P[1:]): s.append(s[-1] + math.dist(a, c))
    g = 99.0
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            if s[j] - s[i] > 14 and not any(math.dist(P[i], x) < 9 or math.dist(P[j], x) < 9 for x in X):
                g = min(g, math.dist(P[i], P[j]))
    return g

def clean(P, mode, ox, desc):
    """What the user's 2026-11-03 picks have in common (and what their complaints rule out)."""
    ys = [p[1] for p in P]; xs = [p[0] for p in P]
    h, w = max(ys) - min(ys), max(xs) - min(xs)
    L = sum(math.dist(a, b) for a, b in zip(P, P[1:]))
    if h < 24 or L < 55: return False                                  # squashed / too simple
    if len(crossings(P)) > 1 or self_gap(P) < 7: return False         # cluttered, or a curve crowding itself
    if ys[-1] < BAR + GAP + 3: return False                            # the free end sits clear of the bar
    if mode == "one":
        d = abs(P[-1][0] - ox)
        if 1.0 < d < 7: return False                                   # the free end touches the stem or stays clear of it
    arcs = [k for k, c in desc[0] if k in ("L", "R")]
    if len(desc[0]) <= 2 and len(arcs) == 2 and arcs[0] != arcs[1] and w < 0.7 * h: return False   # an S is stretched sideways
    return True

def total_turn(P):
    th = [math.atan2(-(c[1]-a[1]), c[0]-a[0]) for a, c in zip(P, P[1:]) if math.dist(a, c) > 0.01]
    return sum((math.degrees(c - a) + 180) % 360 - 180 for a, c in zip(th, th[1:]))

def same_family(a, b):
    """Coarse form families (user, 2026-11-03: 'variants on the same underlying shape'): same attach mode, the same overall
    turning direction and amount (within 100 deg), and a similar number of units. Exact angles/lengths do not make a new form."""
    (ma, ta, na, da), (mb, tb, nb, db) = a, b
    return ma == mb and da == db and abs(ta - tb) < 100 and abs(na - nb) < 2

def family(g):
    return (g["mode"], total_turn([tuple(p) for p in g["pts"]]), len(g["desc"]), any(k == "D" for k, c in g["desc"]))

def chamfer(A, Bp):
    def half(X, Y): return sum(min(math.dist(x, y) for y in Y) for x in X) / len(X)
    return (half(A, Bp) + half(Bp, A)) / 2

# --- distinguishability: two bodies are "the same kind" when their coarse types agree, whatever their size ---
def size_class(turn):
    t = abs(turn)
    return 0 if t < 75 else 1 if t < 165 else 2 if t < 270 else 3          # small, half, three-quarter, loop

def descriptor(seq, turns, lens, h0):
    """Units with negligible straight runs dropped; an arc is (side, size class), loops ignore the side; plus the start heading."""
    total = sum(lens) or 1
    d = []
    for k, t, ln in zip(seq, turns, lens):
        if k == "line":
            if ln >= 0.2 * total and (not d or d[-1][0] != "line"): d.append(("line", 0))
        elif k == "D":
            if not d or d[-1][0] != "D": d.append(("D", 2))
        else:
            c = size_class(t)
            d.append(("loop" if c == 3 else k, c))
    return d, h0 % 360

def similar(a, b):
    (da, ha), (db, hb) = a, b
    if len(da) != len(db): return False
    if min((ha - hb) % 360, (hb - ha) % 360) > 45: return False
    for (ka, ca), (kb, cb) in zip(da, db):
        if ka != kb or abs(ca - cb) > 1: return False
    return True

def thin(P, step=3.0):
    out = [P[0]]
    for p in P[1:]:
        if math.dist(p, out[-1]) >= step: out.append(p)
    return out

REAL = [thin([(p[0] - b["pts"][0][0], p[1] - b["pts"][0][1]) for p in b["pts"]]) for b in B]

def generate(n=60, seed=1):
    rng = random.Random(seed); out = []; mine = []; kinds_seen = []; tries = 0
    fams = []
    for k in json.load(open(SC.path("keepers"))):          # the approved bodies come first, unchanged
        if any(same_family(family(k), f) for f in fams): continue          # (but only one of each coarse form)
        fams.append(family(k)); out.append(k)
        mine.append(thin([(p[0] - k["attach"][0], p[1] - k["attach"][1]) for p in k["pts"]]))
        kinds_seen.append((tuple(map(tuple, k["desc"])), k["h"]))
    while len(out) < n and tries < 60000:
        tries += 1
        mode = rng.choice(["one", "one", "free"])
        seq, marks, pts, (units, h_start) = walk(rng, mode)
        desc = descriptor(seq, [u[1] for u in units], [u[2] for u in units], h_start)
        P, (ox, oy) = place(pts, mode, rng)
        if not ok(P, mode, ox) or not clean(P, mode, ox, desc): continue
        rel = thin([(p[0] - ox, p[1] - oy) for p in P])
        near = min(chamfer(rel, r) for r in REAL)
        if near < 4.0 or near > 22: continue
        cand = (mode, total_turn(P), len(desc[0]), any(k == "D" for k, c in desc[0]))
        if any(chamfer(rel, m) < 4.0 for m in mine) or any(similar(desc, d) for d in kinds_seen) or any(same_family(cand, f) for f in fams): continue
        fams.append(cand)
        mine.append(rel); kinds_seen.append(desc)
        out.append({"mode": mode, "seq": [u[0] for u in units], "marks": marks, "pts": [[round(p[0], 1), round(p[1], 1)] for p in P], "attach": [round(ox, 1), round(oy, 1)], "near": round(near, 1), "desc": [list(x) for x in desc[0]], "h": round(desc[1])})
    return out

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    G = generate(n, seed)
    json.dump(G, open(os.path.join(HERE, "bodies.json"), "w"), separators=(",", ":"))
    from collections import Counter
    print(len(G), Counter(g["mode"] for g in G), Counter(len(g["seq"]) for g in G), "nearest real:", sorted(g["near"] for g in G)[:3], "...", sorted(g["near"] for g in G)[-3:])
