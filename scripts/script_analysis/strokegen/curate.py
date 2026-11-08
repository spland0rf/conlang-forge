"""Hand adjustments to grown letters, requested in review (round 1). Each edit works on the letter's own strokes and re-derives junction positions.
usage: python3 curate.py   -> curated_bengali_round1.json (+ sheet via render.py)"""
import json, math, copy
from engine import parse, fmt, head, dh, length, point_at, param_of, profile, build, rotate, resample, Script

SRC = "grown_bengali_review2.json"
def load(): return {l["iast"]: l for l in json.load(open(SRC))["letters"]}
def pts(l, sid): return next(parse(s[1]) for s in l["strokes"] if s[2] == sid)
def setp(l, sid, P):
    for s in l["strokes"]:
        if s[2] == sid: s[1] = fmt(P)
def warp(P, start=None, end=None):
    """move the ends, blending the displacement along the stroke"""
    n = len(P) - 1; d0 = (start[0] - P[0][0], start[1] - P[0][1]) if start else (0, 0); d1 = (end[0] - P[-1][0], end[1] - P[-1][1]) if end else (0, 0)
    return [(x + d0[0] * (1 - i / n) + d1[0] * i / n, y + d0[1] * (1 - i / n) + d1[1] * i / n) for i, (x, y) in enumerate(P)]
def bow(P, A):
    """push the middle of the stroke down by A (negative = up), ends fixed"""
    n = len(P) - 1; return [(x, y + A * math.sin(math.pi * i / n)) for i, (x, y) in enumerate(P)]
def gain(P, g):
    """exaggerate the stroke's turning by g, keeping its start, first heading and length"""
    R = resample(P, 1.0); h = [head(a, b) for a, b in zip(R, R[1:])]; d = [dh(a, b) for a, b in zip(h, h[1:])]; o = [h[0]]
    for x in d: o.append(o[-1] + g * x)
    Q = [R[0]]
    for a in o: Q.append((Q[-1][0] + math.cos(math.radians(a)), Q[-1][1] - math.sin(math.radians(a))))
    return Q
def fix_junctions(l):
    P = {s[2]: parse(s[1]) for s in l["strokes"]}
    for j in l["junctions"]:
        ps = [(P[m["stroke"]][0] if m["where"] == "start" else P[m["stroke"]][-1] if m["where"] == "end" else point_at(P[m["stroke"]], m["at"])) for m in j["members"]]
        j["x"] = round(sum(p[0] for p in ps) / len(ps), 1); j["y"] = round(sum(p[1] for p in ps) / len(ps), 1)
def snap_middle(l, sid_mid, other, ):
    """after a stroke moved, set the 'at' of every middle member to where the partner's end now lies"""
    P = {s[2]: parse(s[1]) for s in l["strokes"]}
    for j in l["junctions"]:
        ends = [m for m in j["members"] if m["where"] in ("start", "end")]
        for m in j["members"]:
            if m["where"] == "middle" and ends:
                e = ends[0]; pt = P[e["stroke"]][0] if e["where"] == "start" else P[e["stroke"]][-1]; m["at"] = round(param_of(P[m["stroke"]], pt), 2)

def edit_g007(l):
    """top stroke: a regular Bengali top stroke (real 'i' stroke: leaves the bar toward the upper left with a gentle curve)"""
    sc = Script("bengali"); acc = next(s for s in sc.letters if s["iast"] == "i")["S"]["s6"]["P"]; R = acc[::-1]          # from the bar end outward
    a = pts(l, "s4")[0]; R = [(x - R[0][0] + a[0], y - R[0][1] + a[1]) for x, y in R]
    k = 50.0 / length(R); R = [(a[0] + (x - a[0]) * k, a[1] + (y - a[1]) * k) for x, y in R]; setp(l, "s4", R)
def edit_g019(l):
    """the bottom tail moves to the top of the stem and points right"""
    P = pts(l, "s2"); top = pts(l, "s1")[0]; s0 = P[0]
    Q = [(top[0] - (x - s0[0]), top[1] - (y - s0[1])) for x, y in P]; setp(l, "s2", Q)
    for j in l["junctions"]:
        for m in j["members"]:
            if m["stroke"] == "s1" and m["where"] == "end" and any(o["stroke"] == "s2" for o in j["members"]): m["where"] = "start"; m["at"] = 0.0
def edit_g035(l):
    """long blue stroke exactly straight and upright; the two green strokes bow down much more"""
    P = pts(l, "s3"); x = P[0][0]; endy = P[-1][1]; setp(l, "s3", [(x, P[0][1]), (x, endy)])
    S4 = pts(l, "s4"); setp(l, "s4", warp(S4, start=(x, endy)))
    for sid, amp in (("s2", 13.0), ("s6", 15.0)):
        Q = pts(l, sid); setp(l, sid, bow(Q, amp))
    s6 = pts(l, "s6"); tgt = point_at([(x, P[0][1]), (x, endy)], 0.35); setp(l, "s6", warp(s6, end=tgt))
    s2 = pts(l, "s2"); s6 = pts(l, "s6"); setp(l, "s6", warp(s6, start=s2[-1]))
def edit_g039(l):
    """the top bar continues to the right and the blue stroke meets it"""
    B = pts(l, "s1"); setp(l, "s1", [B[0], (90.0, B[1][1])]); x = pts(l, "s2")[0][0]
    for j in l["junctions"]:
        for m in j["members"]:
            if m["stroke"] == "s1" and m["where"] == "middle": m["at"] = round((x - B[0][0]) / (90.0 - B[0][0]), 2)
    by = B[0][1]; Q = pts(l, "s4"); i = next(i for i in range(len(Q) - 1) if (Q[i][1] - by) * (Q[i + 1][1] - by) < 0)          # where the right-hand blue stroke crosses the bar
    u = (by - Q[i][1]) / (Q[i + 1][1] - Q[i][1]); cx = Q[i][0] + u * (Q[i + 1][0] - Q[i][0])
    l["junctions"].append({"t": "cross", "x": round(cx, 1), "y": by, "loose": False, "members": [
        {"stroke": "s1", "at": round((cx - B[0][0]) / (90.0 - B[0][0]), 2), "where": "middle"}, {"stroke": "s4", "at": round(param_of(Q, (cx, by)), 2), "where": "middle"}]})
def edit_g026(l):
    """far-right green stroke: a clear arch, up and to the right, then down"""
    A = pts(l, "s4")[0]; n = 32; step = 1.2; P = [A]
    for i in range(n):
        a = 60 - 150 * (i + .5) / n; P.append((P[-1][0] + step * math.cos(math.radians(a)), P[-1][1] - step * math.sin(math.radians(a))))
    setp(l, "s4", P)

EDITS = {"g007": edit_g007, "g019": edit_g019, "g026": edit_g026, "g035": edit_g035, "g039": edit_g039}
KEEP = ["g003", "g004", "g006", "g012", "g014", "g025", "g027", "g037", "g038"]
if __name__ == "__main__":
    L = load(); out = []; sc = Script("bengali")
    for k in KEEP: out.append(L[k])
    for k, f in EDITS.items():
        before = copy.deepcopy(L[k]); before["iast"] = k + " before"; l = copy.deepcopy(L[k]); f(l); fix_junctions(l); l["iast"] = k + " edited"
        out += [before, l]; print(k, "check:", sc.why(l) or "ok")
    json.dump({"script": "bengali", "box": 100, "letters": out}, open("curated_bengali_round1.json", "w"), ensure_ascii=False, separators=(",", ":"))
