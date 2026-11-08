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

def smooth_keep_corners(P, w=9, corner=60.0):
    """Moving-average smoothing of a resampled path (step 1) with its end points fixed, but NOT across real sharp corners (a heading change of
    `corner` degrees or more over 3 units each side).  Traced hand drawings are polylines; this turns their jitter back into curves."""
    n = len(P)
    if n < 2 * w or w < 3: return P
    def hd(a, b): return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    turns = [abs((hd(P[i], P[min(n - 1, i + 3)]) - hd(P[max(0, i - 3)], P[i]) + 180) % 360 - 180) if 3 <= i < n - 3 else 0.0 for i in range(n)]
    cuts = [0] + [i for i in range(3, n - 3) if turns[i] >= corner and turns[i] == max(turns[max(0, i - 4):i + 5])] + [n - 1]
    out = []
    for c0, c1 in zip(cuts, cuts[1:]):
        seg = P[c0:c1 + 1]; m = len(seg); h = min(w // 2, max(1, m // 4)); res = []
        for i in range(m):
            k = min(h, i, m - 1 - i); lo, hi = i - k, i + k + 1
            res.append((sum(p[0] for p in seg[lo:hi]) / (hi - lo), sum(p[1] for p in seg[lo:hi]) / (hi - lo)))
        out += res if not out else res[1:]
    return out

def letters(path=None):
    """Letters of the script's unit source, as dicts with role/d/id/kind strokes.  A traced stroke graph ([role, d, id] triples, e.g. bengali_graph.json) is accepted too."""
    doc = json.load(open(path or MODEL)); L = doc["letters"] if isinstance(doc, dict) else doc
    for l in L:
        l["strokes"] = [s if isinstance(s, dict) else {"role": s[0], "d": s[1], "id": s[2], "kind": _kind(s[1])} for s in l["strokes"]]
    return L
def _kind(d):
    pts = G.polyline(d, n=6); xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return "vertical" if len(d.split("L")) <= 2 and max(xs) - min(xs) < 1.0 and max(ys) - min(ys) > 12 else "curve"

def bodies():
    L = letters()
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
            sm = SC.get().get('traits', {}).get('unit_smooth', 0)      # traced scripts (Bengali) are polylines: smooth them, keep sharp corners
            if sm: P = resample(smooth_keep_corners(P, sm))
            if len(P) < 6: continue
            units, P = segment(P)
            out.append({"letter": l["iast"] + (" " + l["variant"] if l["variant"] else ""), "glyph": l["glyph"], "stroke": s["id"], "attach": "both" if len(ends) == 2 else "one" if ends else "free", "units": units, "pts": [[round(x, 1), round(y, 1)] for x, y in P]})
    return out

if __name__ == "__main__":
    B = bodies()
    json.dump(B, open(SC.path("units"), "w"), ensure_ascii=False, separators=(",", ":"))
    from collections import Counter
    print(len(B), "bodies;", Counter(len(b["units"]) for b in B), Counter(u["kind"] for b in B for u in b["units"]), Counter(b["attach"] for b in B))
