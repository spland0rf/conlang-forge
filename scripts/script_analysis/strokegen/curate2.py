"""Curated round 2 (pool 2: grown_bengali_pool2.json): owner picked g004 and g016; g002 once its blue stroke leaves the bar vertically.
usage: python3 curate2.py -> curated_bengali_round2.json"""
import json, copy
from engine import parse, fmt, resample, Script
from curate import pts, setp, fix_junctions

def vertical_start(P, run=50.0, pull=0.30, drop=16.0):
    """straight down from the start for `run` units, then one smooth cubic sweep back up to the old end, whose x is pulled `pull` closer to the stem"""
    R = resample(P, 1.0); x0, y0 = R[0]; ex, ey = R[-1]; ex = x0 + (ex - x0) * (1 - pull); yb = y0 + run
    out = [(x0, y0 + i) for i in range(int(run) + 1)]
    p0, p1, p2, p3 = (x0, yb), (x0, yb + drop), (ex + 0.0, yb + drop), (ex, ey)
    for i in range(1, 61):
        t = i / 60; u = 1 - t
        out.append((u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0], u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]))
    return out

if __name__ == "__main__":
    L = {l["iast"]: l for l in json.load(open("grown_bengali_pool2.json"))["letters"]}; sc = Script("bengali"); out = []
    for k in ("g004", "g016"): out.append(L[k])
    b = copy.deepcopy(L["g002"]); b["iast"] = "g002 before"; l = copy.deepcopy(L["g002"]); old = pts(l, "s3"); nw = vertical_start(old); d = (nw[-1][0] - old[-1][0], nw[-1][1] - old[-1][1]); setp(l, "s3", nw); setp(l, "s2", [(x + d[0], y + d[1]) for x, y in pts(l, "s2")]); fix_junctions(l); l["iast"] = "g002 edited"
    print("g002 check:", sc.why(l) or "ok"); out += [b, l]
    json.dump({"script": "bengali", "box": 100, "letters": out}, open("curated_bengali_round2.json", "w"), ensure_ascii=False, separators=(",", ":"))
