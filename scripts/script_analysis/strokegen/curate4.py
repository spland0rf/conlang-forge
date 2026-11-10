"""Round 4: owner corrections on top of the traced redrawings.  python3 curate4.py  ->  curated_bengali_round4_reviewed.json"""
import json, math, os
from assemble import resample, seglen, corner_point, set_corner, nearest
HERE = os.path.dirname(os.path.abspath(__file__))

def load(l): return {i: [r, [tuple(map(float, x.split())) for x in p[1:].split(" L")]] for r, p, i in l["strokes"]}
def put(l, S):
    order = [i for _, _, i in l["strokes"] if i in S]
    l["strokes"] = [[S[i][0], "M" + " L".join("%.1f %.1f" % p for p in S[i][1]), i] for i in order]
    l["ends"] = {k: v for k, v in (l.get("ends") or {}).items() if k in S}
def refresh(l, S):
    """recompute where/at of every junction member from the geometry; drop members/junctions that no longer hold"""
    J = []
    for j in l["junctions"]:
        pt = (j["x"], j["y"]); mem = []
        for m in j["members"]:
            if m["stroke"] not in S: continue
            P = S[m["stroke"]][1]; D = resample(P, 0.5); d, i, f = nearest(D, pt)
            if d > 1.5: continue
            where = "start" if math.dist(P[0], pt) < 0.7 else "end" if math.dist(P[-1], pt) < 0.7 else "middle"
            mem.append({"stroke": m["stroke"], "at": 0.0 if where == "start" else 1.0 if where == "end" else round(f, 3), "where": where})
        if len({m["stroke"] for m in mem}) >= 2: j["members"] = mem; J.append(j)
    l["junctions"] = J
def drop(l, S, sid):
    del S[sid]; l["junctions"] = [dict(j, members=[m for m in j["members"] if m["stroke"] != sid]) for j in l["junctions"]]
def junction(l, t, pt, ids):
    l["junctions"].append({"t": t, "x": round(pt[0], 1), "y": round(pt[1], 1), "members": [{"stroke": i, "at": 0.0, "where": "start"} for i in ids], "loose": False})
def drop_junction_at(l, pt, tol=1.0):
    l["junctions"] = [j for j in l["junctions"] if math.dist((j["x"], j["y"]), pt) > tol]
def end_idx(P, pt): return 0 if math.dist(P[0], pt) <= math.dist(P[-1], pt) else -1
def ball(l, sid, end):
    e = l.setdefault("ends", {}).setdefault(sid, ["plain", "plain"]); e[0 if end == 0 else 1] = "ball"
def smooth(P, passes=2, w=2, keep=2):
    P = list(P)
    for _ in range(passes):
        Q = list(P)
        for i in range(keep, len(P) - keep):
            a, b = max(0, i - w), min(len(P), i + w + 1); Q[i] = (sum(p[0] for p in P[a:b]) / (b - a), sum(p[1] for p in P[a:b]) / (b - a))
        P = Q
    return P
def smooth_tail(P, end, ang=25.0, span=14.0):
    """a tail leaving the top of a vertical: curve away from the first unit (no straight run alongside it, no kink)"""
    Q = resample(P if end == 0 else P[::-1], 0.5); acc = 0.0; ik = 0
    while ik < len(Q) - 6 and acc < span: acc += math.dist(Q[ik], Q[ik + 1]); ik += 1
    pk = Q[ik]; tk = (Q[ik + 4][0] - Q[ik - 4][0], Q[ik + 4][1] - Q[ik - 4][1]); l = math.hypot(*tk) or 1; tk = (tk[0] / l, tk[1] / l)
    P0 = Q[0]; side = 1 if pk[0] >= P0[0] else -1; a = math.radians(ang); u0 = (side * math.sin(a), math.cos(a)); L = math.dist(P0, pk) * 0.4
    P1 = (P0[0] + u0[0] * L, P0[1] + u0[1] * L); P2 = (pk[0] - tk[0] * L, pk[1] - tk[1] * L)
    B = [((1 - t) ** 3 * P0[0] + 3 * (1 - t) ** 2 * t * P1[0] + 3 * (1 - t) * t * t * P2[0] + t ** 3 * pk[0], (1 - t) ** 3 * P0[1] + 3 * (1 - t) ** 2 * t * P1[1] + 3 * (1 - t) * t * t * P2[1] + t ** 3 * pk[1]) for t in [k / 24 for k in range(25)]]
    R = smooth(B + Q[ik + 1:], 2, 2, 2); R[0] = P0
    return R if end == 0 else R[::-1]
def vertical_tails(l, S):
    """strokes meeting the top of an exactly-vertical stroke at a ring: return [(tail id, end)]"""
    out = []
    for j in l["junctions"]:
        if j["t"] != "touch": continue
        ids = [m["stroke"] for m in j["members"]]
        for v in ids:
            P = S[v][1]
            if len(P) == 2 and abs(P[0][0] - P[1][0]) < 1e-6 and min(P[0][1], P[1][1]) >= j["y"] - 0.7 and min(P[0][1], P[1][1]) <= j["y"] + 0.7:
                for t in ids:
                    if t != v: out.append((t, end_idx(S[t][1], (j["x"], j["y"]))))
    return out

def run():
    d = json.load(open(os.path.join(HERE, "curated_bengali_round4_draft.json"))); Ls = {l["glyph"]: l for l in d["letters"]}
    def edit(g, fn):
        l = Ls[g]; S = load(l); fn(l, S); put(l, S); refresh(l, S)

    # --- orange bits that are markup, not strokes ---
    def m009(l, S):
        drop(l, S, "s6"); drop_junction_at(l, (46.4, 34.9)); ball(l, "s1", 0); ball(l, "s8", 0)      # two curved strokes meeting at a filled drop
        for j in l["junctions"]:
            if math.dist((j["x"], j["y"]), (34.8, 34.7)) < 1: j["t"] = "touch"
    edit("m009", m009)
    def m010(l, S):
        drop(l, S, "s7"); drop_junction_at(l, (59.8, 35.9)); drop_junction_at(l, (62.6, 32.9)); drop_junction_at(l, (61.8, 36.2))
        x = 41.4; S["s1"][1] = [(x, 13.8), (x, 83.8)]; del S["s4"]                                     # one long vertical blue stroke
        for j in l["junctions"]:
            for m in j["members"]:
                if m["stroke"] == "s4": m["stroke"] = "s1"
            if math.dist((j["x"], j["y"]), (40.6, 47.6)) < 1: j["x"] = x
            if math.dist((j["x"], j["y"]), (42.2, 13.8)) < 1: j["x"] = x
        for sid, e in (("s5", 0), ("s6", 0), ("s2", 0)): S[sid][1][e] = (x, S[sid][1][e][1])
        X = corner_point(S["s2"][1], -1, S["s3"][1], 0, (61.0, 34.5), reach=20)                          # the markup circle marked a sharp corner between two blue strokes
        X = X or (61.2, 34.4); set_corner(types_s(S, "s2"), -1, X); set_corner(types_s(S, "s3"), 0, X); junction(l, "touch", X, ["s2", "s3"])
    edit("m010", m010)
    def n035(l, S): drop(l, S, "s5")
    edit("n035", n035)

    # --- stubs and overshoots ---
    def m021(l, S): drop(l, S, "s2")
    edit("m021", m021)
    def m029(l, S):
        pt = (47.9, 44.4); P = resample(S["s1"][1], 0.5); k = min(range(len(P)), key=lambda i: math.dist(P[i], pt)); S["s1"][1] = P[:k] + [pt]   # the bowl ends where the cups meet
        S["s4"][1][-1] = pt; drop_junction_at(l, (54.5, 39.1)); drop_junction_at(l, pt)
        junction(l, "red", pt, ["s1", "s3", "s4"])
    edit("m029", m029)

    # --- n015: the top green stroke is the lower one turned 180 degrees about the vertical's middle ---
    def n015(l, S):
        c = (49.0, (31.3 + 55.7) / 2); S["s6"][1] = [(2 * c[0] - x, 2 * c[1] - y) for x, y in S["s7"][1]]
        e = l["ends"].get("s7"); 
        if e: l["ends"]["s6"] = list(e)
        junction(l, "red", (49.0, 31.3), ["s2", "s6"])
    edit("n015", n015)

    # --- n025: the orange stroke is one continuous curve (the box edge hid a stretch) ---
    def n025(l, S):
        A = S["s5"][1][::-1]; B = S["s6"][1]
        t0 = (A[-1][0] - A[-6][0], A[-1][1] - A[-6][1]); t1 = (B[5][0] - B[0][0], B[5][1] - B[0][1])
        n0 = math.hypot(*t0) or 1; n1 = math.hypot(*t1) or 1; t0 = (t0[0] / n0, t0[1] / n0); t1 = (t1[0] / n1, t1[1] / n1)
        p0, p1 = A[-1], B[0]; L = math.dist(p0, p1) * 0.9
        br = [((2*t**3-3*t*t+1)*p0[0] + (t**3-2*t*t+t)*t0[0]*L + (-2*t**3+3*t*t)*p1[0] + (t**3-t*t)*t1[0]*L,
               (2*t**3-3*t*t+1)*p0[1] + (t**3-2*t*t+t)*t0[1]*L + (-2*t**3+3*t*t)*p1[1] + (t**3-t*t)*t1[1]*L) for t in [k / 16 for k in range(1, 16)]]
        br = [(x, min(y, 99.5)) for x, y in br]
        S["s5"][1] = A + br + B; drop(l, S, "s6")
        for j in l["junctions"]:
            for m in j["members"]:
                if m["stroke"] == "s6": m["stroke"] = "s5"
    edit("n025", n025)

    # --- n030: blue arc ends in a drop on the green vertical's foot, no extra loop ---
    def n030(l, S): drop(l, S, "s2"); ball(l, "s3", -1)
    edit("n030", n030)
    # --- n036: one gently upward-bowed blue stroke from the bar to the corner; the lower arc starts at that corner ---
    def n036(l, S):
        drop(l, S, "s2")
        P3 = (67.8, 35.9); P0 = (43.3, 22.6); mx, my = (P0[0] + P3[0]) / 2, (P0[1] + P3[1]) / 2; dx, dy = P3[0] - P0[0], P3[1] - P0[1]; n = math.hypot(dx, dy)
        nx, ny = dy / n, -dx / n
        if ny > 0: nx, ny = -nx, -ny                                  # bow upwards
        C = (mx + nx * 3.2 * 2, my + ny * 3.2 * 2)
        S["s6"][1] = [((1 - t) ** 2 * P0[0] + 2 * (1 - t) * t * C[0] + t * t * P3[0], (1 - t) ** 2 * P0[1] + 2 * (1 - t) * t * C[1] + t * t * P3[1]) for t in [k / 30 for k in range(31)]]
        P = resample(S["s3"][1], 0.5); k = min(range(len(P)), key=lambda i: math.dist(P[i], P3)); S["s3"][1] = P[:k] + [P3]      # the arc stops at the corner
        drop_junction_at(l, P3); junction(l, "touch", P3, ["s3", "s6"])
        for j in l["junctions"]:
            if math.dist((j["x"], j["y"]), P0) < 1: j["members"] = [m for m in j["members"] if m["stroke"] != "s3"] + [{"stroke": "s6", "at": 0.0, "where": "start"}]
    edit("n036", n036)
    # --- n038: the two green strokes meet in a green drop ---
    def n038(l, S): ball(l, "s4", -1); ball(l, "s5", -1)
    edit("n038", n038)
    # --- n033: smooth the kink at the top of the green stroke ---
    def n033(l, S): S["s4"][1] = smooth(S["s4"][1], 3, 3, 2)
    edit("n033", n033)
    # --- tails leaving the top of a vertical curve away at once and without kinks ---
    for g in ("n008", "n009", "n015", "n023", "n030", "n038"):
        def tails(l, S):
            for t, e in vertical_tails(l, S): S[t][1] = smooth_tail(S[t][1], e)
        edit(g, tails)
    d["letters"] = [Ls[l["glyph"]] for l in d["letters"]]
    json.dump(d, open(os.path.join(HERE, "curated_bengali_round4_reviewed.json"), "w"))
    print("wrote", len(d["letters"]), "letters")

def types_s(S, sid):
    class W(dict): pass
    w = W(); w["P"] = S[sid][1]
    class H:                                    # adapter so assemble.set_corner can edit a stroke held as [role, pts]
        def __init__(s): s.d = {"P": S[sid][1]}
        def get(s, k, default=None): return s.d.get(k, default)
        def __getitem__(s, k): return s.d[k]
        def __setitem__(s, k, v): s.d[k] = v; S[sid][1] = v if k == "P" else S[sid][1]
    return H()

if __name__ == "__main__": run()
