"""Stroke-vocabulary statistics: what kinds of strokes a script's letters use and where strokes join, for real drafts and generated presets.
   python vocab_stats.py tamil [--seed 1]      (real = stroke_charts/font_drafts/<name>.json, generated = the preset)"""
import argparse, json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
DRAFTS = os.environ.get("DRAFTS", os.path.join(HERE, "stroke_charts", "font_drafts"))   # font drafts live on branch feat/stroke-charts
NEAR = 0.07


def norm(letter):
    allp = np.array([p for s in letter for p in s])
    lo, hi = allp.min(0), allp.max(0); span = np.maximum(hi - lo, 1e-6)
    return [np.array([(np.array(p) - lo) / span for p in s]) for s in letter]


def length(s): return float(np.sum(np.hypot(*np.diff(s, axis=0).T))) if len(s) > 1 else 0.0


def turning(s):
    """total absolute turning angle (radians) along the stroke"""
    d = np.diff(s, axis=0); d = d[np.hypot(*d.T) > 1e-6]
    if len(d) < 2: return 0.0
    a = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    return float(np.abs(np.diff(a)).sum())


def corners(s, ang=50, span=0.06):
    """sharp corners in a stroke: places where the heading changes by >= ang degrees within `span` of arclength"""
    s = np.asarray(s, float); p = [s[0]]
    for q in s[1:]:
        if np.hypot(*(q - p[-1])) > 0.015: p.append(q)
    p = np.array(p)
    if len(p) < 3: return 0
    d = np.diff(p, axis=0); a = np.degrees(np.arctan2(d[:, 1], d[:, 0])); seg = np.hypot(*d.T)
    n, i = 0, 0
    while i < len(a) - 1:
        tot, acc, j = 0.0, 0.0, i
        while j < len(a) - 1 and acc < span:
            tot += (a[j + 1] - a[j] + 180) % 360 - 180; acc += seg[j + 1]; j += 1
        if abs(tot) >= ang: n += 1; i = j + 1
        else: i += 1
    return n


def kind(s):
    L = length(s); chord = float(np.hypot(*(s[-1] - s[0])))
    if L < 0.12: return "dot/tick"
    if chord < 0.18 * L and L > 0.3: return "loop"          # ends back near its start
    t = turning(s)
    if t < 0.35:
        d = s[-1] - s[0]; ang = abs(math.degrees(math.atan2(d[1], d[0]))) % 180
        if ang < 15 or ang > 165: return "line-H"
        if 75 < ang < 105: return "line-V"
        return "line-diag"
    return "curve" if t < 3.8 else "coil"


def self_cross(s):
    n = 0
    for i in range(len(s) - 1):
        for j in range(i + 2, len(s) - 1):
            p, r, q, w = s[i], s[i + 1] - s[i], s[j], s[j + 1] - s[j]
            den = r[0] * w[1] - r[1] * w[0]
            if abs(den) < 1e-9: continue
            t = ((q - p)[0] * w[1] - (q - p)[1] * w[0]) / den; u = ((q - p)[0] * r[1] - (q - p)[1] * r[0]) / den
            if 0 < t < 1 and 0 < u < 1: n += 1
    return n


def seg_dist(pt, s):
    """distance and relative arclength position of pt on polyline s"""
    best, pos, acc, tot = 9, 0, 0.0, max(length(s), 1e-6)
    for i in range(len(s) - 1):
        a, b = s[i], s[i + 1]; ab = b - a; l2 = float(ab @ ab)
        t = 0 if l2 == 0 else max(0, min(1, float((pt - a) @ ab) / l2)); q = a + t * ab
        d = float(np.hypot(*(pt - q)))
        if d < best: best, pos = d, (acc + t * math.sqrt(l2)) / tot
        acc += math.sqrt(l2)
    return best, pos


def letter_stats(letter):
    S = norm(letter); out = {"kinds": [], "joins": [], "selfx": 0, "crossings": 0}
    for i, s in enumerate(S):
        out["kinds"].append(kind(s)); out["selfx"] += self_cross(s)
        for end, name in ((s[0], "start"), (s[-1], "end")):
            hit = None
            for j, o in enumerate(S):
                if j == i: continue
                d, pos = seg_dist(end, o)
                if d < NEAR:
                    hit = ("corner" if pos < 0.1 or pos > 0.9 else "T", "top" if end[1] > .66 else "mid" if end[1] > .33 else "foot", round(pos, 1))
                    break
            if hit is None:
                d, pos = seg_dist(end, s[:max(2, len(s) // 2)] if name == "end" else s[len(s) // 2:])
                hit = ("self" if d < NEAR and length(s) > .5 else "free", "top" if end[1] > .66 else "mid" if end[1] > .33 else "foot", None)
            out["joins"].append(hit)
    return out


def summarise(letters):
    from collections import Counter
    K, J, JP, ns, sx = Counter(), Counter(), Counter(), [], 0
    cn = sum(corners(s) for lt in letters for s in lt)
    for lt in letters:
        st = letter_stats(lt); ns.append(len(lt)); K.update(st["kinds"]); sx += st["selfx"]
        for j in st["joins"]: J[j[0]] += 1; JP[(j[0], j[1])] += 1
    n = len(letters); tk = sum(K.values()); tj = sum(J.values())
    return {"letters": n, "strokes/letter": round(float(np.mean(ns)), 2), "self-crossings/letter": round(sx / n, 2), "sharp-corners/letter": round(cn / n, 2),
            "kinds": {k: round(v / tk, 3) for k, v in sorted(K.items())}, "joins": {k: round(v / tj, 3) for k, v in sorted(J.items())},
            "join_by_height": {f"{a}/{b}": round(v / tj, 3) for (a, b), v in sorted(JP.items())}}


def real(name):
    d = json.load(open(os.path.join(DRAFTS, name + ".json")))
    return [v["strokes"] for v in d.values()]


def generated(preset, seed):
    from conlang_forge.script.generate import generate
    from conlang_forge.script.presets import PRESETS
    pins = dict(next(p for p in PRESETS if p["id"] == preset)["pins"])
    return [[st["p"] for st in l["strokes"] if len(st["p"]) > 1] for l in generate(seed, pins)["letters"] if l["strokes"]]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--seed", type=int, default=1); a = ap.parse_args()
    for label, L in (("real", real(a.script)), ("generated", generated(a.script, a.seed))):
        print(label, json.dumps(summarise(L)))
