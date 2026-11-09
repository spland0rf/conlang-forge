"""Hand adjustments to motif pool 1 (motif_bengali.json), from the owner's structural notes.
Principles recorded from the notes: free ends keep a buffer from other strokes; strokes under the bar are centred / share the space evenly;
nothing floats (accents attach); strokes that meet share exactly one point; near-vertical strokes are vertical.
usage: python3 curate3.py -> curated_bengali_round3.json (edited letters, each with a 'before')"""
import json, math, copy
from engine import parse, fmt, head, length, point_at, param_of, resample
from curate import pts, setp, warp, fix_junctions

def merge_junction(l, members, t="red"):
    """one junction point for these members (replaces any junction that only lists a subset of them)"""
    keys = {(m["stroke"], m["where"]) for m in members}
    l["junctions"] = [j for j in l["junctions"] if not {(m["stroke"], m["where"]) for m in j["members"]} <= keys]
    l["junctions"].append({"t": t, "x": 0, "y": 0, "members": members, "loose": False})
def M(s, w, at=None): return {"stroke": s, "where": w, "at": {"start": 0.0, "end": 1.0}.get(w, at)}
def sx(P, x0, k): return [(x0 + (x - x0) * k, y) for x, y in P]
def trim_free_end(P, other, which, gap):
    """cut a free end back until it is `gap` from the other stroke"""
    R = resample(P, 1.0); R = R if which == "start" else R[::-1]; o = resample(other, 1.0)
    i = 0
    while i < len(R) - 5 and min(math.dist(R[i], q) for q in o) < gap: i += 1
    R = R[i:]; return R if which == "start" else R[::-1]

def m001(l):
    setp(l, "s4", trim_free_end(pts(l, "s4"), pts(l, "s2"), "start", 16.0))                    # the free end keeps its distance from the descender
def m002(l):
    P = pts(l, "s4"); e = P[-1]; top = (e[0] - (e[1] - P[0][1]) * math.tan(math.radians(3)), P[0][1]); setp(l, "s4", warp(P, start=top))   # near vertical
def m005(l):
    bar = pts(l, "s1"); x = bar[0][0] + 0.16 * (bar[-1][0] - bar[0][0]); setp(l, "s7", [(x, 32.0), (x, 83.0)])   # vertical, and under the bar, not at its end
    l["junctions"] = [j for j in l["junctions"] if not any(m["stroke"] == "s7" for m in j["members"])]
    l["junctions"].append({"t": "red", "x": x, "y": 32, "members": [M("s1", "middle", 0.16), M("s7", "start")], "loose": False})
def m010(l):
    for sid in ("s2", "s5"): setp(l, sid, sx(pts(l, sid), 52.0, 2.6))                           # the left strokes open out, 2-3x wider
def m018(l):
    """the curl descends lower and the short purple bar less, so the curl's tip and the corner of the right stroke are further apart"""
    P = pts(l, "s5"); a = P[0]; setp(l, "s5", [(x, a[1] + (y - a[1]) * 1.25) for x, y in P])
    s2 = pts(l, "s2"); setp(l, "s2", [s2[0], (s2[1][0], 40.0)]); setp(l, "s3", warp(pts(l, "s3"), start=(s2[1][0], 40.0)))
def m021(l):
    """the green base reaches less far left; the curl then sits about one curl-width (18) from the vertical bar"""
    P = pts(l, "s3"); e0 = P[-1]; Q = sx(P, 60.0, 0.75); d = (Q[-1][0] - e0[0], Q[-1][1] - e0[1]); setp(l, "s3", Q)
    setp(l, "s2", [(x + d[0], y + d[1]) for x, y in pts(l, "s2")])
def m023(l):
    a = pts(l, "s3"); b = pts(l, "s4"); m = ((a[-1][0] + b[-1][0]) / 2, (a[-1][1] + b[-1][1]) / 2)
    setp(l, "s3", warp(a, end=m)); setp(l, "s4", warp(b, end=m)); merge_junction(l, [M("s3", "end"), M("s4", "end")])   # one sail
def m024(l):
    b = pts(l, "s2"); P = pts(l, "s4"); j = b[0]; k = 0.5                                      # accent: half size, same point as the curl's start, continuing its line
    ha = head(P[-2], P[-1]); hb = head(b[0], b[1]); q = [(j[0] + (x - P[-1][0]) * k, j[1] + (y - P[-1][1]) * k) for x, y in P]
    t = math.radians(hb - ha); c, s = math.cos(t), math.sin(t)
    q = [(j[0] + (x - j[0]) * c + (y - j[1]) * s, j[1] - (x - j[0]) * s + (y - j[1]) * c) for x, y in q]
    setp(l, "s4", q); merge_junction(l, [M("s1", "middle", 0.3), M("s2", "start"), M("s4", "end")])
    l["junctions"] = [j2 for j2 in l["junctions"] if j2["t"] != "red" or len(j2["members"]) > 1]
def m030(l):
    bot = pts(l, "s1")[-1]; setp(l, "s6", warp(pts(l, "s6"), end=bot)); merge_junction(l, [M("s1", "end"), M("s2", "start"), M("s6", "end")])
def m034(l):
    bar = pts(l, "s1"); P = pts(l, "s2"); cx = (bar[0][0] + bar[-1][0]) / 2; dx = cx - (min(x for x, y in P) + max(x for x, y in P)) / 2
    setp(l, "s2", [(x + dx, y) for x, y in P]); j = P[0][0] + dx
    for jn in l["junctions"]:
        for m in jn["members"]:
            if m["stroke"] == "s1": m["at"] = round((j - bar[0][0]) / (bar[-1][0] - bar[0][0]), 3)
def m037(l):
    bar = pts(l, "s1"); x = 79.0; P = pts(l, "s6"); a, d = P[0], pts(l, "s5")
    Q = [(x - (px - a[0]) * 0.6, 26 - (py - a[1]) * 0.6) for px, py in P]; setp(l, "s6", Q)                  # above the bar, right of the blue strokes' meeting point
    e = Q[-1]; setp(l, "s5", [(e[0], e[1]), (e[0], e[1] + 1.5)])
    l["junctions"] = [j for j in l["junctions"] if not any(m["stroke"] in ("s6",) for m in j["members"])]
    l["junctions"].append({"t": "red", "x": x, "y": 26, "members": [M("s1", "middle", round((x - bar[0][0]) / (bar[-1][0] - bar[0][0]), 3)), M("s6", "start")], "loose": False})
    l["junctions"].append({"t": "red", "x": e[0], "y": e[1], "members": [M("s6", "end"), M("s5", "start")], "loose": False})

EDITS = {"m001": m001, "m002": m002, "m005": m005, "m010": m010, "m018": m018, "m021": m021, "m023": m023, "m024": m024, "m030": m030, "m034": m034, "m037": m037}
if __name__ == "__main__":
    L = {l["iast"]: l for l in json.load(open("motif_bengali.json"))["letters"]}; out = []
    for k, f in EDITS.items():
        b = copy.deepcopy(L[k]); b["iast"] = k + " before"; l = copy.deepcopy(L[k]); f(l); fix_junctions(l); l["iast"] = k + " edited"; out += [b, l]
    json.dump({"script": "bengali", "box": 100, "letters": out}, open("curated_bengali_round3_draft.json", "w"), ensure_ascii=False, separators=(",", ":"))
