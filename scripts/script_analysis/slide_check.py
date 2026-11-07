"""Near-duplicate test with the attachment-slide tolerance: the body strokes may slide (up to ATTACH_SLIDE_TOL x their length)
relative to the fixed skeleton before the ink distance is measured.  usage: python3 slide_check.py"""
import json, re, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "compound_gen")); sys.path.insert(0, os.path.join(HERE, "body_units"))
sys.path.insert(0, HERE)
import script_config as SC
from rules import RULES as R
import body_gen as BG
def bez(p, n=14):
    out = []
    for i in range(n + 1):
        t = i / n
        if len(p) == 4: out.append(tuple((1-t)**3*p[0][k] + 3*(1-t)**2*t*p[1][k] + 3*(1-t)*t*t*p[2][k] + t**3*p[3][k] for k in (0, 1)))
        elif len(p) == 3: out.append(tuple((1-t)**2*p[0][k] + 2*(1-t)*t*p[1][k] + t*t*p[2][k] for k in (0, 1)))
        else: out.append(tuple(p[0][k] + t*(p[1][k]-p[0][k]) for k in (0, 1)))
    return out
def path(d):
    t = re.findall(r"[A-Za-z]|-?[\d.]+", d); i = 0; cur = None; pts = []
    while i < len(t):
        c = t[i]; i += 1
        def num(n):
            nonlocal i; v = [float(x) for x in t[i:i+n]]; i += n; return v
        if c == "M": cur = tuple(num(2)); pts.append(cur)
        elif c == "C": a = num(6); pts += bez([cur, tuple(a[0:2]), tuple(a[2:4]), tuple(a[4:6])])[1:]; cur = tuple(a[4:6])
        elif c == "Q": a = num(4); pts += bez([cur, tuple(a[0:2]), tuple(a[2:4])])[1:]; cur = tuple(a[2:4])
        elif c == "V": y = num(1)[0]; n = (cur[0], y); pts += bez([cur, n])[1:]; cur = n
        elif c == "H": x = num(1)[0]; n = (x, cur[1]); pts += bez([cur, n])[1:]; cur = n
        elif c == "L": n = tuple(num(2)); pts += bez([cur, n])[1:]; cur = n
    return pts
def plen(P): return sum(math.dist(a, b) for a, b in zip(P, P[1:]))
def real():
    G = json.load(open(SC.path("real_graph")))["letters"]; out = {}
    for l in G:
        body = [path(s[1]) for s in l["strokes"] if s[0] == "body"]; rest = [path(s[1]) for s in l["strokes"] if s[0] != "body"]
        out[l["glyph"] + ("" if l["variant"] in (0, None, "") else str(l["variant"]))] = (body, rest)
    return out
def gen():
    L = json.load(open(os.path.join(HERE, "alphabet_gen/alphabet.json")))["letters"]; out = {}
    for i, l in enumerate(L):
        rest = []
        if l.get("bar"): rest.append([(l["bar"][0], 20.0), (l["bar"][1], 20.0)])
        if l["sk"].get("kind") == "stem": rest.append([(l["sk"]["S"], 20.0), (l["sk"]["S"], 88.0)])
        for s in (l.get("struct") or []): rest.append([tuple(p) for p in s])
        out["A%d" % (i + 1)] = ([[tuple(p) for p in s] for s in l["strokes"]], rest)
    return out
def thin(P, step=3.0):
    o = [P[0]]
    for p in P[1:]:
        if math.dist(p, o[-1]) >= step: o.append(p)
    return o
def dist(X, Y, slide=True):
    bx = [p for P in X[0] for p in thin(P)]; by = [p for P in Y[0] for p in thin(P)]
    rx = [p for P in X[1] for p in thin(P)]; ry = [p for P in Y[1] for p in thin(P)]
    base = BG.chamfer(bx + rx, by + ry)
    if not slide or not bx: return base, base
    s = R["ATTACH_SLIDE_TOL"] * (sum(plen(P) for P in X[0]) / len(X[0])); best = base
    for dx in (-s, -s/2, 0, s/2, s):
        for dy in (-s, -s/2, 0, s/2, s):
            best = min(best, BG.chamfer([(x+dx, y+dy) for x, y in bx] + rx, by + ry))
    return base, best
if __name__ == "__main__":
    RL, GL = real(), gen()
    keep = ["A3","A6","A11","A17","A20","A21","A22","A24","A25","A26","A29","A30","A31"]
    T = R["INK_MIN_DIST"]
    print("threshold", T)
    print("\nA28 vs real (plain, slid):")
    for k, v in sorted(((k, dist(GL["A28"], v)) for k, v in RL.items()), key=lambda x: x[1][1])[:4]: print(" ", k, "%.1f %.1f" % v)
    print("\nkeepers: closest real letter (plain, slid)")
    for a in keep:
        k, v = min(((k, dist(GL[a], v)) for k, v in RL.items()), key=lambda x: x[1][1]); print(" ", a, k, "%.1f %.1f" % v, "DUP" if v[1] < T else "")
    print("\nkeepers pairwise under", T)
    for i, a in enumerate(keep):
        for b in keep[i+1:]:
            v = dist(GL[a], GL[b])
            if v[1] < T * 1.5: print(" ", a, b, "%.1f %.1f" % v, "DUP" if v[1] < T else "close")
    print("\nreal pairs under", T)
    ks = list(RL)
    for i, a in enumerate(ks):
        for b in ks[i+1:]:
            v = dist(RL[a], RL[b])
            if v[1] < T: print(" ", a, b, "%.1f %.1f" % v)
