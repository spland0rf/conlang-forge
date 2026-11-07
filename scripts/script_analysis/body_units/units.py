"""Split the real Devanagari body strokes (blue pen paths of the stroke-graph model) into UNITS: straight runs, left or right arcs and
cusps, each with a length and a turn. Bodies are read from where they attach (a stem or a descender) outward.
usage: python3 units.py > units.json   (model coordinates: 100 x 100, y down; headings are measured with y up, degrees, 0 = east)"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "../../..")))
from conlang_forge.script import stroke_graph as G
sys.path.insert(0, os.path.join(HERE, ".."))
import script_config as SC
MODEL = SC.path("unit_source")

KTH = 0.9          # degrees of turn per unit length below which a stretch counts as straight
CUSP = 70.0        # a heading jump larger than this between neighbouring samples is a cusp (break)
MINRUN = 4         # shortest unit, in samples

def resample(pts, step=1.0):
    out, acc = [pts[0]], 0.0
    for a, b in zip(pts, pts[1:]):
        d = math.dist(a, b)
        if d == 0: continue
        n = max(1, int(d // step))
        for i in range(1, n + 1):
            t = min(1.0, i * step / d) if i < n or d % step else 1.0
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out

def headings(P):
    th = [math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0])) for a, b in zip(P, P[1:])]
    return th

def unwrap(th):
    out, off = [th[0]], 0.0
    for a, b in zip(th, th[1:]):
        d = b - a
        if d > 180: off -= 360
        elif d < -180: off += 360
        out.append(b + off)
    return out

def segment(P):
    """-> list of units {kind: line|L|R, len, turn, a:(index range)}; cusps recorded as unit boundaries with kind 'cusp' marks."""
    th = headings(P)
    jumps = [abs(((b - a + 180) % 360) - 180) for a, b in zip(th, th[1:])]
    cusps = {i + 1 for i, j in enumerate(jumps) if j > CUSP}          # segment index where a new heading starts
    U = unwrap(th)
    # smoothed curvature (deg per unit length) with a +-2 window, ignoring windows that cross a cusp
    n = len(U)
    lab = []
    for i in range(n):
        lo, hi = max(0, i - 2), min(n - 1, i + 2)
        if any(c in cusps for c in range(lo + 1, hi + 1)):
            lab.append(lab[-1] if lab else "S"); continue
        k = (U[hi] - U[lo]) / max(1, hi - lo)
        lab.append("L" if k > KTH else "R" if k < -KTH else "S")
    # runs
    runs, start = [], 0
    for i in range(1, n + 1):
        if i == n or lab[i] != lab[start] or i in cusps:
            runs.append([lab[start], start, i]); start = i
    # merge short runs into the previous one (or next if first)
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for k, r in enumerate(runs):
            if r[2] - r[1] < MINRUN and not (r[1] in cusps) and k + 1 < len(runs) or (r[2] - r[1] < MINRUN and k > 0):
                j = k - 1 if k > 0 else k + 1
                a, b = runs[min(j, k)], runs[max(j, k)]
                if b[1] in cusps and a is not r and b is not r: continue
                lab_keep = runs[j][0]
                runs[min(j, k):max(j, k) + 1] = [[lab_keep, a[1], b[2]]]
                changed = True; break
    # join adjacent runs with the same label that are not separated by a cusp
    merged = [runs[0]]
    for r in runs[1:]:
        if r[0] == merged[-1][0] and r[1] not in cusps: merged[-1][2] = r[2]
        else: merged.append(r)
    units = []
    for lab_, a, b in merged:
        length = sum(math.dist(P[i], P[i + 1]) for i in range(a, min(b, len(P) - 1)))
        turn = U[min(b, n) - 1] - U[a]
        jump = round(((th[a] - th[a - 1] + 180) % 360) - 180, 1) if a in cusps and a > 0 else 0.0
        units.append({"kind": "line" if lab_ == "S" else lab_, "len": round(length, 1), "turn": round(turn, 1), "i0": a, "i1": min(b, n), "cusp_before": a in cusps, "jump": jump, "h0": round(U[a], 1)})
    return units, P

def bodies():
    L = json.load(open(MODEL))
    out = []
    for l in L:
        S = {s["id"]: s for s in l["strokes"]}
        att = {}
        for j in l["junctions"]:
            for m in j["members"]:
                other = [o for o in j["members"] if o["stroke"] != m["stroke"] and o["where"] == "middle"]
                if other and m["where"] in ("start", "end"):
                    att.setdefault(m["stroke"], set()).add(m["where"])
        for s in l["strokes"]:
            if s["role"] != "body" or s["kind"] == "vertical": continue
            pts = G.polyline(s["d"], n=20)
            ends = att.get(s["id"], set())
            rev = ends == {"end"}                  # attached at the end: read it from there outward
            if rev: pts = pts[::-1]
            P = resample(pts)
            if len(P) < 6: continue
            units, P = segment(P)
            out.append({"letter": l["iast"] + (" " + l["variant"] if l["variant"] else ""), "glyph": l["glyph"], "stroke": s["id"], "attach": "both" if len(ends) == 2 else "one" if ends else "free", "units": units, "pts": [[round(x, 1), round(y, 1)] for x, y in P]})
    return out

if __name__ == "__main__":
    B = bodies()
    json.dump(B, open(SC.path("units"), "w"), ensure_ascii=False, separators=(",", ":"))
    from collections import Counter
    print(len(B), "bodies;", Counter(len(b["units"]) for b in B), Counter(u["kind"] for b in B for u in b["units"]), Counter(b["attach"] for b in B))
