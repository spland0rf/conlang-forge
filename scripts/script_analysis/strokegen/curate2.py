"""Curated round 2 (pool 2: grown_bengali_pool2.json): owner picked g004 and g016; g002 once its blue stroke leaves the bar vertically.
usage: python3 curate2.py -> curated_bengali_round2.json"""
import json, copy
from engine import parse, fmt, resample, Script
from curate import pts, setp, fix_junctions

def vertical_start(P, run=22.0, blend=30.0):
    """the stroke leaves its start straight down for `run` units, then eases back onto its own course"""
    R = resample(P, 1.0); x0 = R[0][0]; n = len(R); xr = R[min(n - 1, int(run))][0]; out = []
    for i, (x, y) in enumerate(R):
        if i <= run: nx = x0
        elif i < run + blend: nx = x + (x0 - xr) * (1 - (i - run) / blend)
        else: nx = x
        out.append((nx, y))
    return out

if __name__ == "__main__":
    L = {l["iast"]: l for l in json.load(open("grown_bengali_pool2.json"))["letters"]}; sc = Script("bengali"); out = []
    for k in ("g004", "g016"): out.append(L[k])
    b = copy.deepcopy(L["g002"]); b["iast"] = "g002 before"; l = copy.deepcopy(L["g002"]); setp(l, "s3", vertical_start(pts(l, "s3"))); fix_junctions(l); l["iast"] = "g002 edited"
    print("g002 check:", sc.why(l) or "ok"); out += [b, l]
    json.dump({"script": "bengali", "box": 100, "letters": out}, open("curated_bengali_round2.json", "w"), ensure_ascii=False, separators=(",", ":"))
