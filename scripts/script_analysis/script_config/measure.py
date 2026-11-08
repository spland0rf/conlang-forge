"""Measure a script's real letters (its stroke graph) in its own frame, to set rule values from data instead of copying them.
usage: python3 measure.py bengali devanagari"""
import json, math, os, sys, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", ".."))
from conlang_forge.script import stroke_graph as G
def heading(a, b): return math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))
def dh(a, b): return (b - a + 180) % 360 - 180
def length(P): return sum(math.dist(p, q) for p, q in zip(P, P[1:]))
def turn(P):
    P = [p for i, p in enumerate(P) if i == 0 or math.dist(p, P[i - 1]) > 0.5]
    hs = [heading(a, b) for a, b in zip(P, P[1:])]; return sum(abs(dh(a, b)) for a, b in zip(hs, hs[1:]))
def q(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else float("nan")
def measure(script):
    L = G.real_letters(script)
    out = {"letters": 0, "bar": 0, "bar_w": [], "len": [], "turn": [], "straight_vert_dev": [], "x_min": [], "x_max": [], "y_min": [], "y_max": [], "start_axis_dev": [], "n_body": []}
    for l in L:
        out["letters"] += 1
        body = []
        for it in l["strokes"]:
            role = it[0]; P = [(float(x), float(y)) for x, y in G.polyline(it[1])]
            if role == "struct" and len(P) >= 2 and abs(P[0][1] - P[-1][1]) < 1.0 and abs(P[0][0] - P[-1][0]) > 30: out["bar"] += 1; out["bar_w"].append(abs(P[0][0] - P[-1][0])); continue
            if role not in ("body", "second"): continue
            body.append(P); out["len"].append(length(P)); out["turn"].append(turn(P))
            if turn(P) < 12 and length(P) > 14: h = heading(P[0], P[-1]); out["straight_vert_dev"].append(min(abs(abs(h) - 90), abs(h), abs(abs(h) - 180)))
            h0 = heading(P[0], P[min(len(P) - 1, 3)]); out["start_axis_dev"].append(min(abs(abs(h0) - 90), abs(h0), abs(abs(h0) - 180)))
        out["n_body"].append(len(body))
        pts = [p for P in body for p in P]
        if pts: out["x_min"].append(min(p[0] for p in pts)); out["x_max"].append(max(p[0] for p in pts)); out["y_min"].append(min(p[1] for p in pts)); out["y_max"].append(max(p[1] for p in pts))
    return out
if __name__ == "__main__":
    for s in sys.argv[1:] or ["devanagari"]:
        m = measure(s); print("==", s, m["letters"], "letters; bars", m["bar"])
        for k in ("bar_w", "len", "turn", "straight_vert_dev", "start_axis_dev", "x_min", "x_max", "y_min", "y_max", "n_body"):
            v = m[k]; print("  %-18s n=%-4d min %.1f  p10 %.1f  med %.1f  p90 %.1f  max %.1f" % (k, len(v), min(v), q(v, .1), q(v, .5), q(v, .9), max(v)) if v else "  %s (none)" % k)
