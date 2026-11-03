"""Turn letters.json into a stroke graph.

1. Reclassify grammatical marks as accents (orange), with a `function` tag.
2. Give every stroke an id and a shape kind.
3. For every junction, find the strokes it joins and where on each one
   (fraction of the stroke's length, and whether it is the start, end or middle).
4. Record frame info: headline extent, stems, bounding box.
5. Report any junction that doesn't sit on at least two stroke positions.
"""
import json, math, sys
sys.path.insert(0, "/home/claude/geom")
from semantic import sample, kind

P = "/home/claude/geom/letters.json"
data = json.load(open(P))

# ---- 1. grammatical marks -> accents ----
def retag(L, d, fn):
    for s in L["strokes"]:
        if s["d"] == d:
            s["role"] = "accent"; s["function"] = fn; return True
    raise SystemExit(f"stroke not found in {L['glyph']}: {d}")

for L in data:
    g, v = L["glyph"], L["variant"]
    if g == "आ":
        retag(L, "M82 22 V88", "vowel sign ā")
        for s in L["strokes"]:
            if s["d"] == "M82 22 H94": s["role"] = "struct"  # the headline running over the ā sign
        for j in L["junctions"]:
            if (j["x"], j["y"]) == (82, 22): j["t"] = "red"
    if g in "ओऔ":
        retag(L, "M80 22 V88", "vowel sign ā")
        for s in L["strokes"]:
            if s["role"] == "accent" and "function" not in s:
                s["function"] = "vowel sign e" if g == "ओ" else "vowel sign ai"
    if g == "ऐ":
        for s in L["strokes"]:
            if s["role"] == "accent": s["function"] = "vowel sign e"
    if g == "ई":
        for s in L["strokes"]:
            if s["role"] == "accent": s["function"] = "length"
    if g in "ऊॠॡ":
        # the green tail is the length marker
        for s in L["strokes"]:
            if s["role"] == "second": s["role"] = "accent"; s["function"] = "length"

# ---- split a path at an internal vertex where a touch junction sits (stem + flag, corner + cup) ----
import re as _re
def vertices(d):
    tk = _re.findall(r"[MHVLCQ]|-?\d+\.?\d*", d); out = []; i = 0; cur = None; cmd = None
    while i < len(tk):
        if tk[i].isalpha(): cmd = tk[i]; i += 1; start = i - 1
        else: start = i
        n = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "Q": 4}[cmd]
        vals = list(map(float, tk[i:i+n])); i += n
        if cmd == "H": cur = (vals[0], cur[1])
        elif cmd == "V": cur = (cur[0], vals[0])
        else: cur = (vals[-2], vals[-1])
        out.append((i, cur))
    return tk, out
def split(d, x, y):
    tk, vs = vertices(d)
    for k, (idx, p) in enumerate(vs[1:-1], start=1):
        if math.dist(p, (x, y)) < 1.6:
            a = " ".join(tk[:idx]); rest = tk[idx:]
            return a, f"M{p[0]:g} {p[1]:g} " + " ".join(rest)
    return None
# strokes that are ONE pen stroke although a touch sits on them (the long ऋ/ॠ sweep; the ञ cup that turns back into its hook)
# the long ऋ/ॠ sweep is ONE pen stroke that crosses the stem; the touch where the upper-left arc ends on it must not cut it in two
NO_SPLIT = {("ṛ", (46, 58)), ("ṝ", (46, 58)), ("ña", (41, 54))}
for L in data:
    for j in L["junctions"]:
        if j["t"] != "touch": continue
        if (L["iast"], (j["x"], j["y"])) in NO_SPLIT: continue
        for s in list(L["strokes"]):
            r = split(s["d"], j["x"], j["y"])
            if r:
                i = L["strokes"].index(s); a = dict(s, d=r[0]); b = dict(s, d=r[1])
                L["strokes"][i:i+1] = [a, b]; break

# ---- 2-4. graph ----
TOL = 3.2
def arclen(pts):
    acc = [0.0]
    for a, b in zip(pts, pts[1:]): acc.append(acc[-1] + math.dist(a, b))
    return acc

problems = []
for L in data:
    strokes = []
    for i, s in enumerate(L["strokes"]):
        pts = sample(s["d"], 40); al = arclen(pts)
        s["id"] = f"s{i+1}"; s["kind"] = kind(s["d"], pts)
        strokes.append((s, pts, al))
    for k, j in enumerate(L["junctions"]):
        j["id"] = f"j{k+1}"; members = []
        for s, pts, al in strokes:
            hits = [i for i, p in enumerate(pts) if math.dist(p, (j["x"], j["y"])) < TOL]
            if not hits: continue
            # split into separate passes (a stroke can pass a point twice, e.g. a self-crossing)
            groups, cur = [], [hits[0]]
            for h in hits[1:]:
                if h - cur[-1] > 3: groups.append(cur); cur = [h]
                else: cur.append(h)
            groups.append(cur)
            for gr in groups:
                best = min(gr, key=lambda i: math.dist(pts[i], (j["x"], j["y"])))
                frac = al[best] / al[-1] if al[-1] else 0
                where = "start" if best <= 2 else "end" if best >= len(pts) - 3 else "middle"
                members.append({"stroke": s["id"], "at": round(frac, 2), "where": where})
        j["members"] = members
        # branches meeting at this point: ends count 1, middles count 2
        j["branches"] = sum(1 if m["where"] != "middle" else 2 for m in members)
        if len(members) < 2:
            problems.append(f"{L['glyph']}{' ('+L['variant']+')' if L['variant'] else ''} {j['id']} {j['t']} at ({j['x']},{j['y']}): {len(members)} member(s)")
    # frame
    allp = [p for _, pts, _ in strokes for p in pts]
    barS = [s for s, pts, _ in strokes if s["role"] == "struct" and s["kind"] == "horizontal" and (max(p[0] for p in pts) - min(p[0] for p in pts)) > 40]
    stems = [s for s, pts, _ in strokes if s["kind"] == "vertical" and (max(p[1] for p in pts) - min(p[1] for p in pts)) > 40]
    xs, ys = [p[0] for p in allp], [p[1] for p in allp]
    L["frame"] = {
        "headline": None if not barS else {"from_x": round(min(p[0] for p in sample(barS[0]["d"]))), "to_x": round(max(p[0] for p in sample(barS[0]["d"]))), "y": 20},
        "stems": [{"stroke": s["id"], "x": round(sample(s["d"])[0][0], 1), "role": s["role"]} for s in stems],
        "bbox": {"x0": round(min(xs)), "y0": round(min(ys)), "x1": round(max(xs)), "y1": round(max(ys))},
        "width_to_height": round((max(xs) - min(xs)) / (max(ys) - min(ys)), 2),
    }

# ---- shape classes (what a stroke looks like, regardless of its color) ----
for L in data:
    for st in L["strokes"]:
        pts = sample(st["d"], 30); xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        w, h = max(xs) - min(xs), max(ys) - min(ys); k = st["kind"]
        closed = math.dist(pts[0], pts[-1]) < 4
        if k == "horizontal": sc = "headline" if w > 40 else ("flag" if min(ys) < 24 else "connector")
        elif k == "vertical": sc = "stem" if h > 40 else "short vertical"
        elif k == "diagonal": sc = "diagonal"
        elif st["role"] == "accent" and min(ys) < 20: sc = "accent hook"
        elif closed: sc = "loop"
        elif max(w, h) < 16: sc = "hook / tail"
        else: sc = "cup / curve"
        st["shape"] = sc

json.dump(data, open(P, "w"), ensure_ascii=False, indent=1)
print(f"{len(data)} letters, {sum(len(L['junctions']) for L in data)} junctions")
print("problems:", len(problems)); print("\n".join(problems))
