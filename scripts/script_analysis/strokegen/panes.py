"""Window-pane layout (owner's model, see project doc claude/bengali-layout-template.md). Script-neutral: the frame (centre line, split line, edges) comes from the script's model file.
Soft tendencies, applied by warping (so every junction stays shared):
  * a long vertical sits on the centre line when strokes go both ways, in the middle of a half-pane column when they go one way
  * the figure is stretched towards the pane edges (fill)
  * neighbouring elements (side by side: same row; stacked: same column) snap their matching edges together when they are already close
usage:  python3 panes.py measure letters.json         pattern counts and alignment rates
        python3 panes.py adjust in.json out.json      apply the soft adjustments"""
import json, math, os, sys, itertools, statistics as st
from engine import parse, fmt, length, point_at
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = {"cx": 48.6, "left": 15.0, "right": 82.0, "bar_y": 26.0, "top": 13.8, "bottom": 86.0, "split_y": 56.0,
           "strength": 0.4, "capture": 9.0, "stretch": [0.8, 1.25], "snap_tol": 8.0, "align_tol": 3.0, "min_len": 12.0}

def frame(script="bengali"):
    f = dict(DEFAULT)
    try: f.update(json.load(open(os.path.join(HERE, "models", script + ".json"))).get("panes", {}))
    except Exception: pass
    return f

def strokes(L): return {s[2]: (s[0], parse(s[1])) for s in L["strokes"]}
def bbox(Q): xs = [p[0] for p in Q]; ys = [p[1] for p in Q]; return min(xs), max(xs), min(ys), max(ys)
def bar_of(P):
    for i, (r, Q) in P.items():
        if r == "struct" and bbox(Q)[1] - bbox(Q)[0] >= 1.5 * (bbox(Q)[3] - bbox(Q)[2]) + 5: return i
def exact_vertical(Q): return len(Q) == 2 and abs(Q[0][0] - Q[1][0]) < 1e-6 and abs(Q[0][1] - Q[1][1]) >= 30


def own_frame(L, F):
    """the figure's own span of drawn strokes: x from its leftmost to rightmost stroke (the bar excluded), y from the bar (or the top of the strokes) to its lowest stroke.
    Placement metrics and pane lines use this, not the absolute box (owner decision 2026-11-11); the absolute frame F only says where to place the figure in the box."""
    P = strokes(L); b = bar_of(P); pts = [p for i, (r, Q) in P.items() if i != b for p in Q]
    if not pts: return F
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; top = P[b][1][0][1] if b else min(ys)
    G = dict(F); G.update(left=min(xs), right=max(xs), cx=(min(xs) + max(xs)) / 2, bar_y=top, top=top, bottom=max(ys), split_y=(top + max(ys)) / 2); return G

def pane_of(Q, F):
    x0, x1, y0, y1 = bbox(Q); cx = (x0 + x1) / 2; cy = (y0 + y1) / 2
    return ("L" if cx < F["cx"] else "R", "U" if cy < F["split_y"] else "D")

def pairs(L, F):
    """pane-based neighbours: side by side = same row, different columns; stacked = same column, different rows"""
    F = own_frame(L, F); P = strokes(L); b = bar_of(P); S = [(i, Q) for i, (r, Q) in P.items() if i != b and r != "struct" and length(Q) >= F["min_len"]]
    side, stack = [], []
    for (i, A), (k, B) in itertools.combinations(S, 2):
        pa, pb = pane_of(A, F), pane_of(B, F)
        if pa[1] == pb[1] and pa[0] != pb[0]: side.append((i, k))
        elif pa[0] == pb[0] and pa[1] != pb[1]: stack.append((i, k))
    return P, side, stack

def pattern(L, F):
    F = own_frame(L, F); P = strokes(L); b = bar_of(P); S = [Q for i, (r, Q) in P.items() if i != b and r != "struct"]
    pn = {pane_of(Q, F) for Q in S}; cols = {c for c, _ in pn}; rows = {r for _, r in pn}
    V = [Q for Q in S if exact_vertical(Q)]
    if len(pn) == 4: return "2x2"
    if len(cols) == 2 and len(rows) == 2: return "diagonal/3-pane"
    if len(cols) == 2: return "left+right"
    if len(rows) == 2: return "upper+lower"
    return "single pane" + (" (vertical)" if V else "")

def align_rates(letters, F):
    tol = F["align_tol"]; r = {"side": [0, 0, 0], "stack": [0, 0, 0]}                     # n, at least one edge, both edges
    for L in letters:
        P, side, stack = pairs(L, F)
        for kind, lst in (("side", side), ("stack", stack)):
            for i, k in lst:
                A, B = bbox(P[i][1]), bbox(P[k][1])
                d = (abs(A[2] - B[2]), abs(A[3] - B[3])) if kind == "side" else (abs(A[0] - B[0]), abs(A[1] - B[1]))
                r[kind][0] += 1; r[kind][1] += min(d) <= tol; r[kind][2] += max(d) <= tol
    return r

def one_sided(L, F):
    """(vertical id, side the strokes go to or None when balanced)"""
    P = strokes(L); b = bar_of(P); V = [(length(Q), i) for i, (r, Q) in P.items() if exact_vertical(Q) and r != "struct" or (r == "struct" and i != b and exact_vertical(Q))]
    if not V: return None, None
    v = max(V)[1]; x = P[v][1][0][0]; xs = [p[0] for i, (r, Q) in P.items() if i not in (v, b) and r != "struct" for p in Q]
    if not xs: return v, None
    Lw = max(0.0, x - min(xs)); Rw = max(0.0, max(xs) - x)
    if min(Lw, Rw) >= 0.45 * max(Lw, Rw): return v, None
    return v, ("R" if Rw > Lw else "L")

def warp(pts, anchors):
    def f(t):
        if t <= anchors[0][0]: return anchors[0][1] + (t - anchors[0][0])
        if t >= anchors[-1][0]: return anchors[-1][1] + (t - anchors[-1][0])
        for (a, A), (b, B) in zip(anchors, anchors[1:]):
            if a <= t <= b: return A + (B - A) * (t - a) / (b - a) if b > a else A
    return f

def anchors_for(lo, mid, hi, new_lo, new_mid, new_hi, lim):
    """monotone anchors; each side may stretch only within lim"""
    A = []
    if mid is not None and lo < mid - 1: new_lo = min(new_lo, new_mid - lim[0] * (mid - lo)) if False else new_lo
    k = lambda a, b, na, nb: min(max((nb - na) / (b - a), lim[0]), lim[1]) if b > a else 1.0
    if mid is None:
        s = k(lo, hi, new_lo, new_hi); c = (new_lo + new_hi) / 2; return [(lo, c - s * (hi - lo) / 2), (hi, c + s * (hi - lo) / 2)]
    sl = k(lo, mid, new_lo, new_mid) if lo < mid - 1 else 1.0; sr = k(mid, hi, new_mid, new_hi) if hi > mid + 1 else 1.0
    out = []
    if lo < mid - 1: out.append((lo, new_mid - sl * (mid - lo)))
    out.append((mid, new_mid))
    if hi > mid + 1: out.append((hi, new_mid + sr * (hi - mid)))
    return out

def resync(L):
    P = {s[2]: parse(s[1]) for s in L["strokes"]}
    for j in L["junctions"]:
        pts = [P[m["stroke"]][0] if m["where"] == "start" else P[m["stroke"]][-1] if m["where"] == "end" else point_at(P[m["stroke"]], m["at"]) for m in j["members"]]
        j["x"] = sum(p[0] for p in pts) / len(pts); j["y"] = sum(p[1] for p in pts) / len(pts)

def refit(L):
    """recompute every junction member's position along its stroke after the strokes moved"""
    from curate4 import refresh
    refresh(L, {i: [r, Q] for i, (r, Q) in strokes(L).items()})

def adjust(L, F, strength=None):
    """soft pane adjustment; returns a new letter (or the same one if nothing sensible can be done)"""
    s = F["strength"] if strength is None else strength; L = json.loads(json.dumps(L)); P = strokes(L); b = bar_of(P)
    body = [(i, Q) for i, (r, Q) in P.items() if i != b]
    if not body: return L
    xs = [p[0] for _, Q in body for p in Q]; ys = [p[1] for _, Q in body for p in Q]
    v, side = one_sided(L, F); lo, hi = min(xs), max(xs)
    lerp = lambda a, t: a + s * (t - a) if abs(t - a) <= F["capture"] else a            # a pull, only when the target is close: a tendency, not a rule
    # --- horizontal: vertical placement + fill
    if v is not None:
        xv = P[v][1][0][0]
        tx = F["cx"] if side is None else (F["left"] + F["cx"]) / 2 if side == "R" else (F["cx"] + F["right"]) / 2
        tx = xv + s * (tx - xv) if abs(tx - xv) <= F["capture"] + 4 else xv
        if side is None: nlo, nhi = lerp(lo, F["left"]), lerp(hi, F["right"])
        elif side == "R": nlo, nhi = tx - (xv - lo), lerp(hi, F["right"])
        else: nlo, nhi = lerp(lo, F["left"]), tx + (hi - xv)
        ax = anchors_for(lo, xv, hi, nlo, tx, nhi, F["stretch"])
    else:
        ax = anchors_for(lo, None, hi, lerp(lo, F["left"]), None, lerp(hi, F["right"]), F["stretch"])
    fx = warp(None, ax)
    # --- vertical: fill down to the bottom edge, up to the accent zone
    bar_y = P[b][1][0][1] if b else None; top = min(ys); bot = max(ys)
    ay = []
    if bar_y is not None:
        if top < bar_y - 4: ay.append((top, lerp(top, F["top"])))
        ay.append((bar_y, bar_y))
        if bot > bar_y + 10: ay.append((bot, lerp(bot, F["bottom"])))
    else:
        if bot - top > 20: ay = [(top, top), (bot, lerp(bot, F["bottom"]))]
    ay = [a for i, a in enumerate(ay) if i == 0 or a[0] > ay[i - 1][0] + 1]
    fy = warp(None, ay) if len(ay) >= 2 else (lambda t: t)
    new = {i: ([(fx(x), fy(y)) for x, y in Q] if i != b else [(fx(x), y) for x, y in Q]) for i, (r, Q) in P.items()}
    for i, (r, Q) in P.items():                                                         # verticals stay exact
        if exact_vertical(Q): new[i] = [(new[i][0][0], new[i][0][1]), (new[i][0][0], new[i][1][1])]
    L["strokes"] = [[r, fmt(new[i]), i] for r, _, i in L["strokes"]]; resync(L); refit(L)
    # --- snap matching edges of neighbours that are already close
    P2, side_p, stack_p = pairs(L, F); jp = {i: [(j["x"], j["y"]) for j in L["junctions"] if any(m["stroke"] == i for m in j["members"])] for i in P2}
    def snap(i, axis, which, target):
        Q = P2[i][1]; c = lambda p: p[axis]; ext = (min if which == 0 else max)(c(p) for p in Q)
        if abs(ext - target) < 0.2 or any(abs(c(q) - ext) < 1.5 and math.dist(q, p) < 1.5 for q in jp[i] for p in Q if abs(c(p) - ext) < 1.5): return False   # the extreme is tied to a junction: leave it
        far = [c(q) for q in jp[i]]; a = (max if which == 0 else min)(far + [(max if which == 0 else min)(c(p) for p in Q)]) if far else (max if which == 0 else min)(c(p) for p in Q)
        if abs(ext - a) < 6: return False
        k = (target - a) / (ext - a)
        if not F["stretch"][0] <= k <= F["stretch"][1]: return False
        R = [tuple((a + (p[t] - a) * k) if t == axis else p[t] for t in (0, 1)) for p in Q]
        if any(math.dist(q, min(R, key=lambda r: math.dist(r, q))) > 1.0 for q in jp[i]): return False
        P2[i] = (P2[i][0], R); return True
    for lst, ax_pair in ((side_p, (1, (0, 1))), (stack_p, (0, (0, 1)))):
        axis = ax_pair[0]
        for i, k in lst:                                                                  # side by side: align tops and bottoms (y); stacked: left and right edges (x)
            for which in (0, 1):
                A, B = P2[i][1], P2[k][1]; ea = (min if which == 0 else max)(p[axis] for p in A); eb = (min if which == 0 else max)(p[axis] for p in B)
                if 0.2 < abs(ea - eb) <= F["snap_tol"]:
                    t = (ea + eb) / 2; snap(i, axis, which, t); snap(k, axis, which, t)
    for i, (r, Q) in P2.items():
        if exact_vertical(P[i][1]): continue
    L["strokes"] = [[r, fmt(P2[i][1]), i] for r, _, i in L["strokes"]]; resync(L); refit(L); return L


def layout_cost(L, F):
    """lower = better laid out on the window pane: neighbouring elements share an edge, stacked ones have equal width, the figure fills the box.
    (owner's metrics 1, 2, 5; the objective for choosing between candidate placements)"""
    G = own_frame(L, F); P, side, stack = pairs(L, F); e = []
    for kind, lst in (("side", side), ("stack", stack)):
        for i, k in lst:
            A, B = bbox(P[i][1]), bbox(P[k][1])
            d = (abs(A[2] - B[2]), abs(A[3] - B[3])) if kind == "side" else (abs(A[0] - B[0]), abs(A[1] - B[1]))
            e.append(min(min(d), 12.0) / 12.0)
    wmis = []
    for a, b in itertools.combinations(pane_elements(L, F), 2):
        wa, wb = a["bbox"][1] - a["bbox"][0], b["bbox"][1] - b["bbox"][0]
        if a["pane"][0] == b["pane"][0] and a["pane"][1] != b["pane"][1] and min(wa, wb) > 4: wmis.append(1 - min(wa, wb) / max(wa, wb))
    fill = (min(abs(G["left"] - F["left"]), 15) + min(abs(G["right"] - F["right"]), 15) + min(abs(G["bottom"] - F["bottom"]), 15)) / 45.0
    return (sum(e) / len(e) if e else 0.5) + 0.7 * (sum(wmis) / len(wmis) if wmis else 0.3) + 0.8 * fill

def adjust_valid(L, F, why):
    """adjust, but fall back to a weaker pull (then to none) whenever the letter stops being valid"""
    for k in (1.0, 0.5, 0.0):
        G = dict(F, strength=F["strength"] * k, capture=F["capture"] * (k if k else 1)); out = adjust(L, G, G["strength"]) if k else adjust(L, dict(F, capture=0.0), 0.0)
        if why(out) is None: return out, k
    return L, -1


# ---- owner's evaluation metrics (2026-11-11) -------------------------------------------------------------------------------------------
def pane_elements(L, F):
    """compound strokes: strokes of one pane that are joined to each other (bar excluded), each with its pane and bbox (panes from the figure's own span)"""
    F = own_frame(L, F); P = strokes(L); b = bar_of(P); ids = [i for i, (r, Q) in P.items() if i != b and r != "struct" and length(Q) >= F["min_len"]]
    pane = {i: pane_of(P[i][1], F) for i in ids}; par = {i: i for i in ids}
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for j in L["junctions"]:
        ms = [m["stroke"] for m in j["members"] if m["stroke"] in par]
        for a in ms[1:]:
            if pane[a] == pane[ms[0]]: par[find(a)] = find(ms[0])
    groups = {}
    for i in ids: groups.setdefault(find(i), []).append(i)
    out = []
    for g in groups.values():
        pts = [p for i in g for p in P[i][1]]; out.append({"pane": pane[g[0]], "bbox": bbox(pts), "ids": g})
    return out

def evaluate(letters, F):
    """the owner's six metrics, measured on each figure's own span (panes = halves of the span, joints compared with the span's quarter points)"""
    sim_w, sim_h, fw, fh = [], [], [], []; edge = {"left": [], "right": [], "bottom": []}; ctr_v, ctr_h = [], []
    for L in letters:
        G = own_frame(L, F); pw = (G["right"] - G["left"]) / 2; ph = (G["bottom"] - G["top"]) / 2; E = pane_elements(L, F)
        for a, b in itertools.combinations(E, 2):
            wa, wb = a["bbox"][1] - a["bbox"][0], b["bbox"][1] - b["bbox"][0]; ha, hb = a["bbox"][3] - a["bbox"][2], b["bbox"][3] - b["bbox"][2]
            if a["pane"][0] == b["pane"][0] and a["pane"][1] != b["pane"][1] and min(wa, wb) > 4: sim_w.append(min(wa, wb) / max(wa, wb))
            if a["pane"][1] == b["pane"][1] and a["pane"][0] != b["pane"][0] and min(ha, hb) > 4: sim_h.append(min(ha, hb) / max(ha, hb))
        if pw > 8 and ph > 8:
            for e in E: fw.append((e["bbox"][1] - e["bbox"][0]) / pw); fh.append((e["bbox"][3] - e["bbox"][2]) / ph)
        P = strokes(L); b = bar_of(P); pts = [p for i, (r, Q) in P.items() if i != b for p in Q]
        if pts:
            edge["left"].append(abs(min(p[0] for p in pts) - F["left"])); edge["right"].append(abs(max(p[0] for p in pts) - F["right"])); edge["bottom"].append(abs(max(p[1] for p in pts) - F["bottom"]))
        W, H = G["right"] - G["left"], G["bottom"] - G["top"]
        if W < 20 or H < 25: continue
        for j in L["junctions"]:
            u = (j["y"] - G["top"]) / H; w = (j["x"] - G["left"]) / W
            if abs(w - 0.5) <= 0.15 and 0.1 < u < 0.92: ctr_v.append(min(abs(u - t) for t in (0.25, 0.5, 0.75)))
            elif abs(u - 0.5) <= 0.15 and 0.04 < w < 0.96 and abs(w - 0.5) > 0.15: ctr_h.append(min(abs(w - t) for t in (0.25, 0.75)))
    med = lambda v: round(st.median(v), 2) if v else None
    share = lambda v: round(sum(0.8 <= x <= 1.25 for x in v) / max(1, len(v)), 2)
    return {"stacked width similarity (min/max, median)": med(sim_w), "stacked pairs": len(sim_w), "side-by-side height similarity (median)": med(sim_h), "side-by-side pairs": len(sim_h),
            "element width / pane width (median, share within 0.8-1.25)": (med(fw), share(fw)), "element height / pane height (median, share within 0.8-1.25)": (med(fh), share(fh)),
            "outer edges to absolute frame, left/right/bottom (median units)": [med(edge[k]) for k in ("left", "right", "bottom")],
            "joints on the vertical axis: distance to .25/.5/.75 of the span (median fraction; random about 0.10)": (med(ctr_v), len(ctr_v)),
            "joints on the horizontal axis: distance to .25/.75 of the width (median fraction; random about 0.17)": (med(ctr_h), len(ctr_h))}

def drift(a, b):
    Pa, Pb = strokes(a), strokes(b); return st.mean(math.dist(p, q) for i in Pa for p, q in zip(Pa[i][1], Pb[i][1]))

if __name__ == "__main__":
    mode = sys.argv[1]; d = json.load(open(sys.argv[2])); F = frame(os.environ.get("CF_SCRIPT", "bengali")); Ls = d["letters"]
    if mode == "measure":
        import collections
        print("patterns:", dict(collections.Counter(pattern(l, F) for l in Ls)))
        for k, v in evaluate(Ls, F).items(): print("  ", k, v)
        r = align_rates(Ls, F); print("side-by-side pairs %d: >=1 edge aligned %.0f%%, both %.0f%% | stacked pairs %d: >=1 edge %.0f%%, both %.0f%%" % (r["side"][0], 100 * r["side"][1] / max(1, r["side"][0]), 100 * r["side"][2] / max(1, r["side"][0]), r["stack"][0], 100 * r["stack"][1] / max(1, r["stack"][0]), 100 * r["stack"][2] / max(1, r["stack"][0])))
    else:
        from motif import Composer
        why = Composer(os.environ.get("CF_SCRIPT", "bengali")).why; res = [adjust_valid(l, F, why) if why(l) is None else (l, -1) for l in Ls]; out = [r[0] for r in res]
        print("strength used (1=full,.5,0=snap only,-1=unchanged):", {k: sum(r[1] == k for r in res) for k in (1.0, 0.5, 0.0, -1)}); d["letters"] = out; json.dump(d, open(sys.argv[3], "w"), ensure_ascii=False, separators=(",", ":"))
        print("mean drift per point %.1f" % st.mean(drift(a, b) for a, b in zip(Ls, out)))


# ---- evaluation metrics (owner's list, 2026-11-11) ----
def elements(L, F):
    """compound strokes: connected groups of non-bar strokes (the main vertical is its own spine and is left out of the groups)"""
    P = strokes(L); b = bar_of(P); v, _ = one_sided(L, F); ids = [i for i, (r, Q) in P.items() if i != b and i != v and r != "struct" or (r == "struct" and i not in (b, v))]
    par = {i: i for i in ids}
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for j in L["junctions"]:
        ms = [m["stroke"] for m in j["members"] if m["stroke"] in par]
        for m in ms[1:]: par[find(m)] = find(ms[0])
    G = {}
    for i in ids: G.setdefault(find(i), []).append(i)
    out = []
    for g in G.values():
        pts = [p for i in g for p in P[i][1]]; x0, x1, y0, y1 = bbox(pts)
        if (x1 - x0) < 6 and (y1 - y0) < 6: continue
        out.append({"ids": g, "bbox": (x0, x1, y0, y1), "w": x1 - x0, "h": y1 - y0, "col": "L" if (x0 + x1) / 2 < F["cx"] else "R", "row": 0 if (y0 + y1) / 2 < F["bar_y"] else 1 if (y0 + y1) / 2 < F["split_y"] else 2})
    return out

def row_bounds(F): return {0: (F.get("accent_top", 13.8), F["bar_y"]), 1: (F["bar_y"], F["split_y"]), 2: (F["split_y"], F["bottom"])}

def metrics(letters, F):
    stack_w, side_h, fill_w, fill_h, edge, axis = [], [], [], [], [], []
    rb = row_bounds(F); qw = {"L": F["cx"] - F["left"], "R": F["right"] - F["cx"]}
    for L in letters:
        E = elements(L, F)
        for a, b in itertools.combinations(E, 2):
            if a["col"] == b["col"] and a["row"] != b["row"]: stack_w.append(abs(a["w"] - b["w"]) / max(a["w"], b["w"]))     # stacked: similar width?
            if a["row"] == b["row"] and a["col"] != b["col"]: side_h.append(abs(a["h"] - b["h"]) / max(a["h"], b["h"]))     # side by side: similar height?
        for e in E:
            fill_w.append(min(1.0, e["w"] / qw[e["col"]])); lo, hi = rb[e["row"]]; fill_h.append(min(1.0, e["h"] / (hi - lo)))   # fill the quadrant
        P = strokes(L); pts = [p for i, (r, Q) in P.items() for p in Q]; x0, x1, y0, y1 = bbox(pts)
        edge.append((abs(x0 - F["left"]), abs(x1 - F["right"]), abs(y0 - (F.get("accent_top", 13.8) if y0 < F["bar_y"] - 4 else F["top"])), abs(y1 - F["bottom"])))             # fill the whole box
        W = F["right"] - F["left"]; H = F["bottom"] - F["top"]
        px = [F["left"] + W * t for t in (0.25, 0.5, 0.75)]; py = [F["top"] + H * t for t in (0.25, 0.5, 0.75)]
        for j in L["junctions"]:
            if abs(j["x"] - F["cx"]) <= 6: axis.append(min(abs(j["y"] - y) for y in py))                                # on the vertical axis: near 25/50/75% height?
            if abs(j["y"] - F["split_y"]) <= 6: axis.append(min(abs(j["x"] - x) for x in px))                           # on the horizontal axis: near 25/50/75% width?
    m = lambda v: round(sum(v) / len(v), 2) if v else None
    return {"stacked width diff (rel, lower better)": (m(stack_w), len(stack_w)), "side-by-side height diff (rel, lower better)": (m(side_h), len(side_h)),
            "fill width of quadrant (higher better)": (m(fill_w), len(fill_w)), "fill height of quadrant (higher better)": (m(fill_h), len(fill_h)),
            "outer edge distance to box (L,R,T,B, lower better)": tuple(round(sum(e[k] for e in edge) / len(edge), 1) for k in range(4)),
            "axis junction distance to 25/50/75% points (lower better)": (m(axis), len(axis))}

def axis_baseline(F, n=4000):
    import random; rng = random.Random(1); W = F["right"] - F["left"]; H = F["bottom"] - F["top"]
    py = [F["top"] + H * t for t in (0.25, 0.5, 0.75)]; px = [F["left"] + W * t for t in (0.25, 0.5, 0.75)]
    return round(sum(min(abs(rng.uniform(F["top"], F["bottom"]) - y) for y in py) for _ in range(n)) / n, 2), round(sum(min(abs(rng.uniform(F["left"], F["right"]) - x) for x in px) for _ in range(n)) / n, 2)
