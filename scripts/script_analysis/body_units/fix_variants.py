"""Repair the bodies the user liked 'but ...' (2026-11-03): rescale about the attach point until the stated problem is gone."""
import json, math, os, random, itertools
import body_gen as BG
HERE = os.path.dirname(os.path.abspath(__file__))
def fixed(g, rng):
    ox, oy = g["attach"]; P0 = g["pts"]; desc = (tuple(map(tuple, g["desc"])), g["h"])
    best = None
    for _ in range(20000):
        sx, sy = rng.uniform(.7, 2.4), rng.uniform(.7, 2.4)
        P = [(ox + (p[0]-ox)*sx, oy + (p[1]-oy)*sy) for p in P0]
        if not BG.ok(P, g["mode"], ox): continue
        ys = [p[1] for p in P]; xs = [p[0] for p in P]
        if max(ys)-min(ys) < 24 or BG.self_gap(P) < 7 or ys[-1] < BG.BAR + BG.GAP + 3: continue
        if g["mode"] == "one" and 1.0 < abs(P[-1][0]-ox) < 7: continue
        arcs = [k for k, c in desc[0] if k in ("L", "R")]
        if len(desc[0]) <= 2 and len(arcs) == 2 and arcs[0] != arcs[1] and max(xs)-min(xs) < .7*(max(ys)-min(ys)): continue
        cost = abs(math.log(sx)) + abs(math.log(sy))            # the smallest change that fixes it
        if best is None or cost < best[0]: best = (cost, P)
    return best and dict(g, pts=[[round(p[0], 1), round(p[1], 1)] for p in best[1]])
if __name__ == "__main__":
    rng = random.Random(3); B = json.load(open(os.path.join(HERE, "bodies.json")))[:15] + json.load(open(os.path.join(HERE, "generated_rest.json"))); F = json.load(open(os.path.join(HERE, "fix_me.json")))
    out = []
    for g in F:
        f = fixed(g, rng); print("B%d" % g["old"], "fixed" if f else "NO FIX"); 
        if f: out.append(f)
    keep = B[:15]; rest = B[15:]
    def rel(g): return BG.thin([(p[0]-g["attach"][0], p[1]-g["attach"][1]) for p in g["pts"]])
    fixed_rel = [rel(g) for g in out]
    rest = [g for g in rest if all(BG.chamfer(rel(g), r) >= 4.0 for r in fixed_rel)]
    allb, fams = [], []
    for g in keep + out + rest:
        fm = BG.family(g)
        if any(BG.same_family(fm, x) for x in fams): continue
        fams.append(fm); allb.append(g)
    keep, out, rest = allb, [], []
    json.dump(keep + out + rest, open(os.path.join(HERE, "bodies.json"), "w"), separators=(",", ":"))
    print(len(keep + out + rest), "bodies")
