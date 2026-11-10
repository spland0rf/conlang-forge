"""Soft taste score learned from the owner's picks/rejects (review_log.json). usage: python3 taste.py  (prints feature table + fit)"""
import json, math, os
from engine import parse, turning, Script
HERE = os.path.dirname(os.path.abspath(__file__))

def features(l, sc):
    S = [parse(s[1]) for s in l["strokes"]]; roles = [s[0] for s in l["strokes"]]
    tl = [turning(P)[0] for P in S]; ln = [sum(math.dist(P[i], P[i+1]) for i in range(len(P)-1)) for P in S]
    xs = [x for P in S for x, y in P]; ys = [y for P in S for x, y in P]
    curls = sum(t > 240 for t in tl)
    return {"n": len(S), "ink": sum(ln) / 100, "curls": curls, "wig": sum(1 for t in tl if t > 150 and t <= 240) , "maxturn": max(tl) / 100,
            "nj": len(l.get("junctions", [])), "bar": int("struct" in roles and any(s[0] == "struct" and abs(parse(s[1])[0][1] - parse(s[1])[-1][1]) < 2 for s in l["strokes"])),
            "short": sum(x < 20 for x in ln), "w": (max(xs) - min(xs)) / 100, "h": (max(ys) - min(ys)) / 100}

def load():
    log = json.load(open(os.path.join(HERE, "review_log.json"))); sc = Script("bengali"); rows = []
    r1 = {l["iast"]: l for l in json.load(open(os.path.join(HERE, "grown_bengali_review2.json")))["letters"]}
    r2 = {l["iast"]: l for l in json.load(open(os.path.join(HERE, "grown_bengali_pool2.json")))["letters"]}
    for rd, pool in (("round1", r1), ("round2", r2)):
        liked = set(log[rd]["liked"]) | set(log[rd].get("liked_with_edit", {}))
        if rd == "round1": liked -= {"g004"}
        for k, l in pool.items(): rows.append((rd + ":" + k, int(k in liked), features(l, sc)))
    return rows

if __name__ == "__main__":
    rows = load(); keys = list(rows[0][2])
    for k in keys:
        p = [r[2][k] for r in rows if r[1]]; n = [r[2][k] for r in rows if not r[1]]
        print("%-8s liked %.2f  rejected %.2f" % (k, sum(p)/len(p), sum(n)/len(n)))
    print(len(rows), "letters,", sum(r[1] for r in rows), "liked")

KEYS = ["n", "ink", "curls", "wig", "maxturn", "nj", "bar", "w", "h"]

def fit(rows, l2=0.5, steps=3000, lr=0.05):
    X = [[r[2][k] for k in KEYS] for r in rows]; y = [r[1] for r in rows]; m = len(X)
    mu = [sum(x[j] for x in X) / m for j in range(len(KEYS))]; sd = [max(1e-6, (sum((x[j]-mu[j])**2 for x in X)/m)**.5) for j in range(len(KEYS))]
    Z = [[(x[j]-mu[j])/sd[j] for j in range(len(KEYS))] for x in X]; w = [0.0]*len(KEYS); b = math.log(sum(y)/(m-sum(y)))
    for _ in range(steps):
        g = [l2*wj for wj in w]; gb = 0.0
        for z, t in zip(Z, y):
            p = 1/(1+math.exp(-(b+sum(a*c for a, c in zip(w, z))))); e = p - t
            for j in range(len(w)): g[j] += e*z[j]/m
            gb += e/m
        w = [wj - lr*gj for wj, gj in zip(w, g)]; b -= lr*gb
    return {"keys": KEYS, "mu": mu, "sd": sd, "w": w, "b": b}

def score(model, f):
    z = sum(w*((f[k]-mu)/sd) for k, w, mu, sd in zip(model["keys"], model["w"], model["mu"], model["sd"])) + model["b"]
    return 1/(1+math.exp(-z))

def train():
    rows = load(); model = fit(rows); json.dump(model, open(os.path.join(HERE, "taste_bengali.json"), "w"), indent=1)
    s = sorted(((score(model, r[2]), r[1], r[0]) for r in rows), reverse=True)
    hit = sum(t for _, t, _ in s[:16]); print("weights:", {k: round(w, 2) for k, w in zip(KEYS, model["w"])}); print("liked in top-16 by score:", hit, "of", sum(r[1] for r in rows))

# ---- v2: also learn from the owner's 1-4 scores on the motif pools (sets A = m-, B = n-); soft labels, duplicates ignored
SOFT = {4: 1.0, 3: 0.7, 2: 0.15, 1: 0.0}
def load2():
    rows = load(); sc = Script("bengali"); own = json.load(open(os.path.join(HERE, "owner_scores.json")))
    for pool, key in (("motif_bengali.json", "A"), ("motif_bengali_pool2.json", "B")):
        L = {l["glyph"]: l for l in json.load(open(os.path.join(HERE, pool)))["letters"]}
        for g, s in own[key].items():
            if s in SOFT and g in L: rows.append(("owner:" + g, SOFT[s], features(L[g], sc)))
    return rows
def train2():
    rows = load2(); model = fit(rows); json.dump(model, open(os.path.join(HERE, "taste_bengali.json"), "w"), indent=1)
    print(len(rows), "rows;", "weights:", {k: round(w, 2) for k, w in zip(KEYS, model["w"])})
    own = sorted(((score(model, r[2]), r[1], r[0]) for r in rows if r[0].startswith("owner:")), reverse=True)
    top = own[:30]; print("owner 4s/3s in top 30 of %d: %d (of %d liked)" % (len(own), sum(t >= .7 for _, t, _ in top), sum(t >= .7 for _, t, _ in own)))
    print("lowest scored owner 4s:", [(g, round(p, 2)) for p, t, g in own if t == 1.0][-3:])
