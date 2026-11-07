"""Derive a proportional, structured description (and plain-English text) from the traced paths."""
import json, re, math

TOP, BOT = 20, 88          # headline and baseline of the 100x100 box
H = BOT - TOP
COLOR = {"body": "blue", "second": "green", "struct": "purple", "accent": "orange"}

def sample(d, n=24):
    toks = re.findall(r"[MHVLCQ]|-?\d+\.?\d*", d)
    pts, i, cur, cmd = [], 0, (0, 0), None
    def num():
        nonlocal i; v = float(toks[i]); i += 1; return v
    while i < len(toks):
        if toks[i].isalpha(): cmd = toks[i]; i += 1
        if cmd == "M": cur = (num(), num()); pts.append(cur)
        elif cmd == "H": x = num(); pts += [(cur[0] + (x - cur[0]) * t / n, cur[1]) for t in range(1, n + 1)]; cur = (x, cur[1])
        elif cmd == "V": y = num(); pts += [(cur[0], cur[1] + (y - cur[1]) * t / n) for t in range(1, n + 1)]; cur = (cur[0], y)
        elif cmd == "L":
            p = (num(), num()); pts += [(cur[0] + (p[0] - cur[0]) * t / n, cur[1] + (p[1] - cur[1]) * t / n) for t in range(1, n + 1)]; cur = p
        elif cmd == "Q":
            c, p = (num(), num()), (num(), num())
            for t in range(1, n + 1):
                t /= n; pts.append(tuple((1-t)**2*a + 2*(1-t)*t*b + t*t*e for a, b, e in zip(cur, c, p)))
            cur = p
        elif cmd == "C":
            c1, c2, p = (num(), num()), (num(), num()), (num(), num())
            for t in range(1, n + 1):
                t /= n; pts.append(tuple((1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*e for a, b, c, e in zip(cur, c1, c2, p)))
            cur = p
    return pts

def kind(d, pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if re.fullmatch(r"M[\d.]+ [\d.]+ H[\d.]+", d): return "horizontal"
    if re.fullmatch(r"M[\d.]+ [\d.]+ V[\d.]+", d): return "vertical"
    if re.fullmatch(r"M[\d.]+ [\d.]+ L[\d.]+ [\d.]+", d): return "diagonal"
    return "curve"

pct = lambda v: f"{round(v / 5) * 5:.0f}%"

def describe(L):
    strokes = []
    for s in L["strokes"]:
        pts = sample(s["d"]); xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        strokes.append(dict(role=s["role"], kind=kind(s["d"], pts), pts=pts,
                            x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys)))
    bar = next((s for s in strokes if s["role"] == "struct" and s["kind"] == "horizontal" and s["x1"] - s["x0"] > 40), None)
    bx0, bx1 = (bar["x0"], bar["x1"]) if bar else (min(t["x0"] for t in strokes), max(t["x1"] for t in strokes))
    curves = [t for t in strokes if t["kind"] == "curve" and t["role"] != "accent"]
    for t in curves:
        same = [u for u in curves if u["role"] == t["role"]]
        base = "connector" if t["role"] == "struct" else "curved form"
        t["name"] = f"{COLOR[t['role']]} {base}" + (f" {'ABCD'[same.index(t)]}" if len(same) > 1 else "")
    along = lambda x: (x - bx0) / (bx1 - bx0) * 100
    down = lambda y: (y - TOP) / H * 100
    stems = [s for s in strokes if s["kind"] == "vertical"]
    struct, text = [], []
    if bar: struct.append({"part": "top bar", "color": "purple"}); text.append("A horizontal top bar. Positions across are measured along the bar; positions down run from the bar (0%) to the baseline (100%).")
    elif any(s["kind"] == "horizontal" for s in strokes): text.append("No full top bar; only a short top segment. Positions across are measured over the letter's full width; positions down run from the top line (0%) to the baseline (100%).")
    else: text.append("No top bar. Positions across are measured over the letter's full width; positions down run from the top line (0%) to the baseline (100%).")

    def host_desc(x, y, skip=None):
        for s in stems:
            if abs(s["x0"] - x) < 2.5 and s["y0"] - 2 <= y <= s["y1"] + 2:
                if abs(y - TOP) < 3 and bar: return f"where the {COLOR[s['role']]} vertical meets the bar"
                return f"on the {COLOR[s['role']]} vertical, {pct(down(y))} of the way down"
        if bar and abs(y - TOP) < 3: return f"on the bar, {pct(along(x))} along it"
        for t in strokes:
            s = t
            if s is not skip and s["kind"] == "curve" and s["role"] != "accent" and min(math.dist(p, (x, y)) for p in s["pts"]) < 2.5:
                fx = (x - s["x0"]) / max(1, s["x1"] - s["x0"]); fy = (y - s["y0"]) / max(1, s["y1"] - s["y0"])
                v = "upper" if fy < .34 else "lower" if fy > .66 else "middle"
                hz = "left" if fx < .34 else "right" if fx > .66 else "centre"
                pos = "centre" if v == "middle" and hz == "centre" else f"{v}-{hz}" if v != "middle" else f"{hz} side"
                return f"at the {pos} of the {s['name']}"
        return f"at {pct(along(x))} across, {pct(down(y))} down"

    rank = {"horizontal": 1, "vertical": 0, "curve": 2, "diagonal": 3}
    for s in sorted(strokes, key=lambda t: (t["role"] == "accent", rank[t["kind"]])):
        c = COLOR[s["role"]]
        if s is bar: continue
        if s["kind"] == "vertical":
            ln = (s["y1"] - s["y0"]) / H * 100
            name = "stem" if ln > 60 else "short descender"
            e = {"part": name, "color": c, "at_along_bar": round(along(s["x0"])), "from_down": round(down(s["y0"])), "to_down": round(down(s["y1"]))}
            struct.append(e)
            text.append(f"A {c} {'vertical stem' if name == 'stem' else 'short vertical connector'} at {pct(along(s['x0']))} across, "
                        f"running from {pct(down(s['y0']))} to {pct(down(s['y1']))} down.")
        elif s["kind"] == "horizontal":
            struct.append({"part": "short horizontal", "color": c, "from_along": round(along(s["x0"])), "to_along": round(along(s["x1"]))})
            text.append(f"A short {c} horizontal at the top, from {pct(along(s['x0']))} to {pct(along(s['x1']))} across.")
        elif s["kind"] == "diagonal":
            (ax, ay), (zx, zy) = s["pts"][0], s["pts"][-1]
            ang = round(math.degrees(math.atan2(zy - ay, zx - ax)) / 5) * 5
            struct.append({"part": "diagonal", "color": c, "from": host_desc(ax, ay), "to": host_desc(zx, zy), "angle_deg": ang})
            text.append(f"A {c} diagonal, about {abs(ang)}° from horizontal, from a point {host_desc(ax, ay)} to a point {host_desc(zx, zy)}.")
        else:
            w, h = s["x1"] - s["x0"], s["y1"] - s["y0"]
            ar = w / h if h else 9
            shape = "wider than tall" if ar > 1.15 else "taller than wide" if ar < 0.87 else "about as wide as tall"
            side = ""
            if stems:
                mx = (s["x0"] + s["x1"]) / 2; st = min(stems, key=lambda t: abs(t["x0"] - mx))
                if st is not s: side = " left of the stem" if mx < st["x0"] - 3 else " right of the stem" if mx > st["x0"] + 3 else " around the stem"
            if s["role"] == "accent":
                dirn = "left" if s["pts"][-1][0] < s["pts"][0][0] else "right"
                struct.append({"part": "accent", "color": c, "curls": dirn, "rises_from": host_desc(*s["pts"][0])})
                text.append(f"An orange accent rising above the bar and curling {dirn}, from the point {host_desc(*s['pts'][0])}.")
                continue
            struct.append({"part": s["name"], "color": c, "x_from_along": round(along(s["x0"])), "x_to_along": round(along(s["x1"])),
                           "y_from_down": round(down(s["y0"])), "y_to_down": round(down(s["y1"])), "width_to_height": round(ar, 2),
                           "starts": host_desc(*s["pts"][0], skip=s), "ends": host_desc(*s["pts"][-1], skip=s)})
            text.append(f"The {s['name']}{side} spans {pct(along(s['x0']))}–{pct(along(s['x1']))} across and "
                        f"{pct(max(0, down(s['y0'])))}–{pct(down(s['y1']))} down, and is {shape}. It starts {host_desc(*s['pts'][0], skip=s)} and ends {host_desc(*s['pts'][-1], skip=s)}.")
    jt = {"red": "joins between forms", "touch": "touches (○)", "cross": "crossings (×)"}
    for t in ("red", "touch", "cross"):
        js = [j for j in L["junctions"] if j["t"] == t]
        if js: text.append(f"{jt[t][0].upper() + jt[t][1:]}: " + "; ".join(host_desc(j["x"], j["y"]) for j in js) + ".")
    fns = {}
    for st in L["strokes"]:
        if st.get("function"): fns.setdefault(st["function"], 0); fns[st["function"]] += 1
    if fns: text.append("Grammatical marks (orange): " + "; ".join(fns) + ".")
    L["structure"] = struct
    L["description"] = " ".join(text)

if __name__ == "__main__":
    data = json.load(open("/home/claude/geom/letters.json"))
    for L in data: describe(L)
    json.dump(data, open("/home/claude/geom/letters.json", "w"), ensure_ascii=False, indent=1)
    for L in data:
        if L["glyph"] in "बप": print(L["glyph"], L["description"], "\n")
