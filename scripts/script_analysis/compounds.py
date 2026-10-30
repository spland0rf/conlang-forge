"""Mine recurring compound strokes: chains of 2-3 stroke atoms joined at a point, described by what each atom is and how they meet.
   python compounds.py bengali [--generated] [--top 25]
An atom is described by its kind (line / curve / coil / loop) and its chord direction; a join by its type (corner = end meets end,
T = end meets the middle of the other) and the angle between the two strokes where they meet (fold = under 35 degrees, sharp, right,
obtuse, through). Counts are the share of letters that contain each chain."""
import argparse, json, math, os, sys
from collections import Counter
import numpy as np
import vocab_stats as V

NEAR = V.NEAR


def body_dir(s, end):
    """unit vector from the stroke end into its body (over about 0.12 of arclength)"""
    p = s[-1] if end else s[0]
    pts = s[::-1] if end else s
    acc = 0.0
    for q in pts[1:]:
        acc += float(np.hypot(*(q - p)))
        if acc >= 0.12:
            break
    v = q - p
    n = float(np.hypot(*v)) or 1e-6
    return v / n


def chord(s):
    d = s[-1] - s[0]
    a = abs(math.degrees(math.atan2(d[1], d[0]))) % 180
    return "H" if a < 22 or a > 158 else "V" if 68 < a < 112 else "D"


def atom(s):
    k = V.kind(s)
    if k in ("line-H", "line-V", "line-diag"):
        return "line-" + chord(s)
    if k == "curve":
        u, w = s[len(s) // 2] - s[0], s[-1] - s[len(s) // 2]
        sgn = 1 if u[0] * w[1] - u[1] * w[0] > 0 else -1
        return "curve" + ("L" if sgn > 0 else "R")
    return k


def angle_bucket(a):
    return "fold" if a < 35 else "sharp" if a < 80 else "right" if a < 110 else "obtuse" if a < 150 else "through"


def joins(S):
    """all junctions between strokes: (i, j, type, angle bucket); i's end touches j"""
    out = []
    for i, s in enumerate(S):
        for end in (0, 1):
            e = s[-1] if end else s[0]
            for j, o in enumerate(S):
                if j == i:
                    continue
                d, pos = V.seg_dist(e, o)
                if d >= NEAR:
                    continue
                vi = body_dir(s, end)
                if pos < 0.1 or pos > 0.9:
                    vj = body_dir(o, 1 if pos > 0.9 else 0)
                    t = "corner"
                else:
                    k = int(pos * (len(o) - 1))
                    vj = o[min(k + 1, len(o) - 1)] - o[max(k, 0)] if k + 1 < len(o) else o[-1] - o[-2]
                    vj = vj / (float(np.hypot(*vj)) or 1e-6)
                    t = "T"
                a = math.degrees(math.acos(max(-1, min(1, float(vi @ vj)))))
                if t == "T":
                    a = min(a, 180 - a)                       # a T is the same whichever way the host runs
                out.append((i, j, t, angle_bucket(a), end))
                break
    return out


def mine(letters):
    pairs, triples, n = Counter(), Counter(), len(letters)
    for lt in letters:
        S = V.norm(lt)
        A = [atom(s) for s in S]
        J = joins(S)
        seen_p, seen_t = set(), set()
        for i, j, t, ab, end in J:
            key = tuple(sorted([A[i], A[j]])) + (t if t == "corner" else "T:" + A[j], ab)
            seen_p.add((A[i], t, ab, A[j]) if t == "T" else (min(A[i], A[j]), t, ab, max(A[i], A[j])))
        for (i, j, t, ab, end) in J:
            for (i2, j2, t2, ab2, end2) in J:
                if j2 == j and i2 != i and (i, t, ab) < (i2, t2, ab2):
                    seen_t.add((A[i], t, ab, A[j], t2, ab2, A[i2]))
        pairs.update(seen_p)
        triples.update(seen_t)
    return n, pairs, triples


def load(script, generated):
    return V.generated(script, 1) if generated else V.real(script)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--generated", action="store_true")
    ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args()
    n, pairs, triples = mine(load(a.script, a.generated))
    print(f"{a.script} ({'generated' if a.generated else 'real'}): {n} letters")
    print("-- pairs (atom, join, angle, atom): share of letters")
    for k, v in pairs.most_common(a.top):
        print(f"  {v / n:5.2f}  {k[0]}  --{k[1]}/{k[2]}--  {k[3]}")
    print("-- two joins at one stroke (A -> B <- C)")
    for k, v in triples.most_common(a.top // 2):
        print(f"  {v / n:5.2f}  {k[0]} -{k[1]}/{k[2]}-> {k[3]} <-{k[4]}/{k[5]}- {k[6]}")
