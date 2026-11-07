"""Half-bar compounds (user, 2026-11-03): a curved form or a vertical '3' on the LEFT, without a top bar, joined by a short purple
connector that leaves the base of one of its cups (or its end) to a form with its own top stroke on the RIGHT -- either a
Russian-G shape (vertical bar with a top stroke) or a short top stroke with a body hanging from its left end. Same rules as compound_gen.
usage: python3 compound_half.py [n] [seed] -> letters_half.json"""
import json, math, os, random, sys
import compound_gen as C
BG = C.BG; HERE = C.HERE; R = C.R; BASE = R["BASE_Y"]
HC = C.CFG["half"]; TOP = C.CFG["frame"]["half_top"]
JOIN_Y = tuple(TOP + f * (BASE - TOP) for f in HC["join_y_frac"])       # connector height on the vertical (Devanagari: from the user's redraw measurements)

def cup_bases(Q):
    """Candidate connector starts, tagged by where they sit on the left form: the base of each cup / arc, and the stroke's end."""
    marks, units = Q.meta; n = len(Q); out = []
    for i, (k, tr, ln) in enumerate(units):
        a, b = marks[i], (marks[i + 1] if i + 1 < len(units) else n - 1)
        if k == "line" or abs(tr) < 90 or b - a < 4: continue
        j = max(range(a, b + 1), key=lambda q: Q[q][1]); out.append(Q[j])
    out.append(Q[-1])
    ys = [p[1] for p in Q]; lo, hi = min(ys), max(ys)
    return [(p, "top" if p[1] < lo + .33 * (hi - lo) else "bottom" if p[1] > lo + .67 * (hi - lo) else "mid") for p in out]

def hit_right(py, px, forms):
    """First point where the horizontal ray from (px, py) meets a stroke of the right-hand form, and that stroke's heading there."""
    best = None
    for P in forms:
        for a, b in zip(P, P[1:]):
            if (a[1] - py) * (b[1] - py) <= 0 and a[1] != b[1]:
                x = a[0] + (b[0] - a[0]) * (py - a[1]) / (b[1] - a[1])
                if x > px + 8 and (best is None or x < best[0]): best = (x, C.hd(a, b))
    return best

def build(rng, three, join_at=None, right_variant=None):
    variant = right_variant or rng.choice(("G", "hook"))
    Sx = rng.uniform(*HC["right_x"])
    if variant == "G":
        lo, hi = HC["g_top_len"]; tl = rng.uniform(lo, min(hi, R["EDGE_HI"] - Sx))                         # Devanagari redraws: top stroke ~0.30 of the vertical (generated 0.18-0.30)
        right = [[(Sx, TOP), (Sx, BASE)], [(Sx, TOP), (Sx + tl, TOP)]]; right_struct = right; body = []
    else:
        lo, hi = HC["hook_top_len"]; tl = rng.uniform(lo, min(hi, R["EDGE_HI"] - Sx))
        top = [(Sx, TOP), (Sx + tl, TOP)]
        Q, seq = C.stroke_free(rng, (Sx, TOP), lambda h: C.angdiff(h, 90) <= 12, (90,))
        if Q is None or not C.stroke_ok(Q) or max(p[0] for p in Q) > R["EDGE_HI"]: return None
        right = [top, Q]; right_struct = [top]; body = [Q]
    # the left form: a free-standing body stroke without a bar
    for _ in range(200):
        P, seq = C.raw(rng, force_three=three) if C.RAW_MODE["ct"] else C.raw(rng)
        if three and "D" not in seq: continue
        if not three and "D" in seq: continue
        st = (rng.uniform(*HC["left_start_x"]), rng.uniform(*HC["left_start_y"])); h = rng.choice((90, 0, 180)) + (0 if P.meta[1][0][0] == "line" else rng.uniform(-5, 5))
        Q = C.place_free(P, st, h, rng.uniform(.8, 1.3))
        if C.orient_ok(Q) and C.stroke_ok(Q): break
    else: return None
    xs = [p[0] for p in Q]; ys = [p[1] for p in Q]
    if min(xs) < R["EDGE_LO"] or max(xs) > Sx - 14 or min(ys) < TOP + 5 or max(ys) > BASE - 2 or not (HC["left_len"][0] <= C.length(Q) <= HC["left_len"][1]): return None
    if BG.self_gap(Q) < R["MIN_SELF_GAP"] or BG.crossings(Q): return None
    cands = cup_bases(Q); rng.shuffle(cands)
    for p, where in cands:
        if join_at and where != join_at: continue
        if not (JOIN_Y[0] <= p[1] <= JOIN_Y[1]): continue                  # redraws: connector meets the vertical at 0.31-0.52 of its height (was up to 0.69)
        i = min(range(len(Q)), key=lambda q: math.dist(Q[q], p))
        if min(C.angdiff(C.tangent(Q, i), 0), C.angdiff(C.tangent(Q, i), 180)) < 28: continue     # not a mere extension of a horizontal stroke
        h = hit_right(p[1], p[0], right)
        if not h or min(C.angdiff(h[1], 90), C.angdiff(h[1], 270)) > 12: continue          # the connector arrives square on a vertical
        end = (h[0], p[1])
        if end[0] - p[0] > HC["connector_max"] or (variant == "hook" and end[1] < 36): continue
        # the left form keeps clear of the connector and of the right form
        bad = any(math.dist(q, p) > 9 and abs(q[1] - p[1]) < 5 and q[0] > p[0] - 1 and q[0] < end[0] for q in C.thin2(Q))
        if bad: continue
        if any(math.dist(q, r) < 8 for q in C.thin2(Q) for P in right for r in C.thin2(P)): continue
        conn = [p, end]
        J = [["red", p[0], p[1]], ["red", end[0], end[1]], ["touch", Sx, TOP]]
        if variant == "hook" and body and BG.crossings(body[0]): return None
        return {"skel": "half", "join": where, "recipe": "half-" + variant + ("-3" if three else ""), "sk": {"S": Sx}, "bar": None,
                "struct": [[[round(x, 1), round(y, 1)] for x, y in s] for s in right_struct + [conn]],
                "strokes": [[[round(x, 1), round(y, 1)] for x, y in Q]] + [[[round(x, 1), round(y, 1)] for x, y in b] for b in body],
                "J": [[j[0], round(j[1], 1), round(j[2], 1)] for j in J], "seqs": [seq]}
    return None

def generate(n=14, seed=1):
    rng = random.Random(seed); out = []; ink = []; tries = 0
    while len(out) < n and tries < 30000:
        tries += 1
        L = build(rng, three=rng.random() < .5)
        if not L: continue
        pts = [p for P in L["strokes"] for p in BG.thin([tuple(q) for q in P], 2.0)]
        if sum(1 for o in out if o["recipe"] == L["recipe"]) >= n // 3 + 1: continue
        if any(BG.chamfer(pts, q) < 9 for q in ink): continue
        ink.append(pts); out.append(L)
    return out, tries

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 14; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    G, t = generate(n, seed); json.dump(G, open(os.path.join(HERE, "letters_half.json"), "w"), separators=(",", ":"))
    from collections import Counter
    print(len(G), "half-bar letters in", t, "tries;", Counter(g["recipe"] for g in G))
