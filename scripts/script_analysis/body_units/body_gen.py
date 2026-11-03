"""Generate new Devanagari-like body forms as chains of units (line / left arc / right arc / cusp), sampled from the units of the real
bodies (units.json): the number of units, the kind sequence (a Markov chain), each unit's length and turn (a real unit of that kind,
scaled by 0.75-1.3), the start heading and any cusp turn. Built by integrating a pen from the attach point. A body is kept only if it
stays inside the letter box, keeps the clear gap from the bar, is not a copy of a real body and not close to another new one.
usage: python3 body_gen.py [n] [seed] > bodies.json"""
import json, math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(HERE, "units.json")))
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
    pts = [(0.0, 0.0)]; x = y = 0.0; marks = []
    for i, kind in enumerate(seq):
        u = rng.choice(UNITS[kind]); ln = u["len"] * rng.uniform(.75, 1.3); tr = u["turn"] * rng.uniform(.75, 1.3)
        if i and rng.random() < CUSP_P: h += rng.choice(CUSPS) * rng.uniform(.8, 1.1)
        n_steps = max(2, int(ln / 1.5)); marks.append(len(pts) - 1)
        for s in range(n_steps):
            h += (tr / n_steps) if kind != "line" else 0
            x += math.cos(math.radians(h)) * ln / n_steps; y += math.sin(math.radians(h)) * ln / n_steps
            pts.append((x, -y if False else y))
    return seq, marks, pts

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

def chamfer(A, Bp):
    def half(X, Y): return sum(min(math.dist(x, y) for y in Y) for x in X) / len(X)
    return (half(A, Bp) + half(Bp, A)) / 2

def thin(P, step=3.0):
    out = [P[0]]
    for p in P[1:]:
        if math.dist(p, out[-1]) >= step: out.append(p)
    return out

REAL = [thin([(p[0] - b["pts"][0][0], p[1] - b["pts"][0][1]) for p in b["pts"]]) for b in B]

def generate(n=60, seed=1):
    rng = random.Random(seed); out = []; mine = []; tries = 0
    while len(out) < n and tries < 20000:
        tries += 1
        mode = rng.choice(["one", "one", "free"])
        seq, marks, pts = walk(rng, mode)
        P, (ox, oy) = place(pts, mode, rng)
        if not ok(P, mode, ox): continue
        rel = thin([(p[0] - ox, p[1] - oy) for p in P])
        near = min(chamfer(rel, r) for r in REAL)
        if near < 4.0 or near > 22: continue
        if any(chamfer(rel, m) < 4.0 for m in mine): continue
        mine.append(rel)
        out.append({"mode": mode, "seq": seq, "marks": marks, "pts": [[round(p[0], 1), round(p[1], 1)] for p in P], "attach": [round(ox, 1), round(oy, 1)], "near": round(near, 1)})
    return out

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    G = generate(n, seed)
    json.dump(G, open(os.path.join(HERE, "bodies.json"), "w"), separators=(",", ":"))
    from collections import Counter
    print(len(G), Counter(g["mode"] for g in G), Counter(len(g["seq"]) for g in G), "nearest real:", sorted(g["near"] for g in G)[:3], "...", sorted(g["near"] for g in G)[-3:])
