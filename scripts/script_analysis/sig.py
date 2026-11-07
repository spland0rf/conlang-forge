"""Structural signature of a letter: strokes are merged when they continue end-to-end, each is labelled by coarse kind
(horizontal / vertical / other line / curve with size class and arc count), and the contact graph records which strokes touch
and whether the contact is at a stroke END or along its MIDDLE.  Where along a stroke a contact sits is ignored (ATTACH_SLIDE_TOL).
Two letters with the same signature are one letter."""
import math, sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import slide_check as S
import script_config as SC
CONTACT = 4.0; MERGE = 1.5
def turns(P):
    P = S.thin(P, 3.0); a = []
    for i in range(1, len(P) - 1):
        h1 = math.atan2(P[i][1]-P[i-1][1], P[i][0]-P[i-1][0]); h2 = math.atan2(P[i+1][1]-P[i][1], P[i+1][0]-P[i][0])
        d = math.degrees(h2 - h1); d = (d + 180) % 360 - 180; a.append(d)
    return a
def canon(P):
    return P[::-1] if P[0][1] > P[-1][1] + 3 else P
def runs(P, thr):
    r = []
    for x in turns(P):
        if abs(x) < 1.2: continue
        sg = 1 if x > 0 else -1
        if r and r[-1][0] == sg: r[-1][1] += abs(x)
        else: r.append([sg, abs(x)])
    return [(s_, v) for s_, v in r if v > thr]
def opening(P):
    cx = sum(p[0] for p in P) / len(P); cy = sum(p[1] for p in P) / len(P)
    mx = (P[0][0] + P[-1][0]) / 2; my = (P[0][1] + P[-1][1]) / 2; dx = mx - cx; dy = my - cy
    return ("E" if dx > 0 else "W") if abs(dx) >= abs(dy) else ("S" if dy > 0 else "N")
def label(P, thr=None):
    thr = RUN_THR if thr is None else thr
    L = S.plen(P); dx = P[-1][0]-P[0][0]; dy = P[-1][1]-P[0][1]
    t = turns(P); tot = sum(abs(x) for x in t)
    if tot < 35:
        if abs(dx) < 0.12*L + 1: return "V"
        return "S"
    P = canon(P); r = runs(P, thr)
    sg = "".join("+" if s_ > 0 else "-" for s_, _ in r)
    if len(r) <= 1:
        bins = [75, 165, 270, 360, 450, 540]; cls = sum(tot >= b for b in bins)
        return "C%s%d%s" % (sg, cls, opening(P))
    if len(r) == 2: return "C" + sg + "".join(str(sum(v >= b for b in (90, 180, 330))) for _, v in r)
    return "C" + sg
RUN_THR = 25
def merge(strokes):
    S_ = [list(s) for s in strokes]; ch = True
    while ch:
        ch = False
        for i in range(len(S_)):
            for j in range(len(S_)):
                if i != j and S_[i] and S_[j] and math.dist(S_[i][-1], S_[j][0]) < MERGE and S_[i][0] != S_[j][-1] and label(S_[i]) not in ("S", "V") and label(S_[j]) not in ("S", "V"):
                    S_[i] = S_[i] + S_[j][1:]; S_[j] = []; ch = True
    return [s for s in S_ if s]
def dense(P, step=2.0):
    o = [tuple(P[0])]
    for a, b in zip(P, P[1:]):
        n = max(1, int(math.dist(a, b) // step))
        for k in range(1, n + 1): o.append((a[0] + (b[0]-a[0])*k/n, a[1] + (b[1]-a[1])*k/n))
    return o
def sig(strokes):
    st = merge([dense(s) for s in strokes]); lab = [label(P) for P in st]; n = len(st); edges = []
    for i in range(n):
        for j in range(i + 1, n):
            best = (9e9, None, None)
            for a in S.thin(st[i], 2.0):
                for b in S.thin(st[j], 2.0):
                    d = math.dist(a, b)
                    if d < best[0]: best = (d, a, b)
            if best[0] <= CONTACT:
                def where(P, p):
                    k = min(range(len(P)), key=lambda q: math.dist(P[q], p)); f = k / max(1, len(P) - 1)
                    return "e" if (f < 0.1 or f > 0.9) else "m"
                w1 = where(S.thin(st[i], 2.0), best[1]); w2 = where(S.thin(st[j], 2.0), best[2])
                edges.append(tuple(sorted([(lab[i], w1), (lab[j], w2)])))
    return (tuple(sorted(lab)), tuple(sorted(edges)))
def real_strokes():
    return {k: [p for s in v[0] + v[1] for p in [s]] for k, v in S.real().items()}
def letter_strokes(l):
    FR = SC.active().frame; BAR_Y, BASE_Y, DESC_Y = FR["bar_y"], FR["base_y"], FR["desc_y"]      # frame of the active profile (script_config)
    st = [[tuple(p) for p in s] for s in l["strokes"]]
    if l.get("bar"): st.append([(l["bar"][0], BAR_Y), (l["bar"][1], BAR_Y)])
    if l["sk"].get("kind") == "stem": st.append([(l["sk"]["S"], BAR_Y), (l["sk"]["S"], BASE_Y)])
    if l["sk"].get("kind") == "desc": st.append([(l["sk"]["x"], BAR_Y), (l["sk"]["x"], DESC_Y)])
    for s in (l.get("struct") or []): st.append([tuple(p) for p in s])
    return st
def gen_strokes():
    L = json.load(open(os.path.join(HERE, "alphabet_gen/alphabet.json")))["letters"]
    return {"A%d" % (i + 1): letter_strokes(l) for i, l in enumerate(L)}
def known_signatures():
    """signatures of the 49 real letters: a generated letter may not equal any of them (nor an already accepted one)"""
    return {sig(v) for v in real_strokes().values()}
if __name__ == "__main__":
    R_ = real_strokes(); G_ = gen_strokes(); keep = ["A3","A6","A11","A17","A20","A21","A22","A24","A25","A26","A29","A30","A31"]
    RS = {k: sig(v) for k, v in R_.items()}; GS = {k: sig(v) for k, v in G_.items()}
    same = {}
    for k, v in RS.items(): same.setdefault(v, []).append(k)
    print("real letters sharing a signature:", [g for g in same.values() if len(g) > 1])
    print("A28 equals:", [k for k, v in RS.items() if v == GS["A28"]])
    for a in keep:
        m = [k for k, v in RS.items() if v == GS[a]] + [b for b in keep if b != a and GS[b] == GS[a]]
        if m: print(a, "collides with", m)
    print("done")
