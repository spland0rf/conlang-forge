"""Turn traced ink (trace/extracted/*.json, patch pixels) into stroke-graph letters in the standard format.
python3 assemble.py out.json [ids...]   (default: every scored 3/4 letter that has ink)"""
import os, sys, json, math, cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "trace"))
import ink
HERE = os.path.dirname(os.path.abspath(__file__)); PX = 4.0                      # patch pixels per unit
ROLE_ORDER = {"struct": 0, "body": 1, "second": 2, "accent": 3}

def seglen(P): return float(sum(math.dist(P[i], P[i + 1]) for i in range(len(P) - 1)))
def chaikin(P, n=2):
    for _ in range(n):
        Q = [P[0]]
        for a, b in zip(P, P[1:]): Q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        P = Q + [P[-1]]
    return P
def resample(P, step=1.0):
    if len(P) < 2: return P
    d = [0.0]
    for a, b in zip(P, P[1:]): d.append(d[-1] + math.dist(a, b))
    n = max(1, int(round(d[-1] / step))); out = []; j = 0
    for k in range(n + 1):
        t = d[-1] * k / n
        while j < len(d) - 2 and d[j + 1] < t: j += 1
        u = (t - d[j]) / (d[j + 1] - d[j]) if d[j + 1] > d[j] else 0
        out.append((P[j][0] + u * (P[j + 1][0] - P[j][0]), P[j][1] + u * (P[j + 1][1] - P[j][1])))
    return out
def nearest(P, pt):
    """(distance, index of nearest vertex, arc fraction) on a dense polyline"""
    best = (1e9, 0); 
    for i, p in enumerate(P):
        d = math.dist(p, pt)
        if d < best[0]: best = (d, i)
    tot = seglen(P) or 1.0; return best[0], best[1], seglen(P[:best[1] + 1]) / tot
def dev_from_chord(P):
    (x0, y0), (x1, y1) = P[0], P[-1]; L = math.hypot(x1 - x0, y1 - y0) or 1
    return max(abs((y1 - y0) * (x - x0) - (x1 - x0) * (y - y0)) / L for x, y in P)


def _dir(P, end, n=6.0):
    """unit vector pointing outward from the stroke at one end, measured over about n units"""
    Q = P if end == 0 else P[::-1]; acc = 0.0; k = 0
    while k < len(Q) - 1 and acc < n: acc += math.dist(Q[k], Q[k + 1]); k += 1
    v = (Q[0][0] - Q[k][0], Q[0][1] - Q[k][1]); l = math.hypot(*v) or 1.0; return (v[0] / l, v[1] / l)
def _ang(u, v): return math.degrees(math.acos(max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1]))))
def merge_pieces(S, rings=(), gap=7.0, cont=40.0):
    """join same-role pieces that continue each other through a red dot or a small gap; all purple pieces become one bar"""
    def barlike(s):
        xs = [p[0] for p in s["P"]]; ys = [p[1] for p in s["P"]]; return s["role"] == "struct" and (max(xs) - min(xs)) >= 1.5 * (max(ys) - min(ys)) and seglen(s["P"]) >= 12
    bars = [s for s in S if barlike(s)]; S = [s for s in S if not barlike(s)]
    if bars:
        xs = [p[0] for b in bars for p in b["P"]]; ys = [p[1] for b in bars for p in b["P"]]
        yb = float(np.mean([p[1] for p in max(bars, key=lambda b: seglen(b["P"]))["P"]])); S.append({"role": "struct", "bar": True, "P": [(min(xs), yb), (max(xs), yb)]})
    while True:
        best = None
        for i in range(len(S)):
            for j in range(i + 1, len(S)):
                a, b = S[i], S[j]
                if a["role"] != b["role"] or a["role"] == "struct": continue
                for ea in (0, -1):
                    for eb in (0, -1):
                        pa, pb = a["P"][ea], b["P"][eb]; d = math.dist(pa, pb)
                        if d > gap: continue
                        mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
                        if any(math.dist(mid, r[0]) < r[1] + 4 for r in rings): continue                      # a ring says: these are two strokes
                        ta, tb = _dir(a["P"], 0 if ea == 0 else 1), _dir(b["P"], 0 if eb == 0 else 1)
                        if _ang(ta, (-tb[0], -tb[1])) > cont: continue
                        if d >= 2.0 and _ang(ta, ((pb[0] - pa[0]) / d, (pb[1] - pa[1]) / d)) > 50: continue
                        if best is None or d < best[0]: best = (d, i, j, ea, eb)
        if best is None: break
        _, i, j, ea, eb = best; a, b = S[i], S[j]
        A = a["P"] if ea == -1 else a["P"][::-1]; B = b["P"] if eb == 0 else b["P"][::-1]
        S[i] = {"role": a["role"], "P": A + B}; del S[j]
    return S


def end_line(P, end, a=5.0, b=13.0):
    """(point at arc a from the end, unit direction pointing out through the end) from the clean ink away from the ring"""
    D = resample(P, 0.5)
    if end == 0: D = D[::-1]                       # D[-1] is the end in question
    D = D[::-1]                                    # now D[0] is the end
    acc = [0.0]
    for p, q in zip(D, D[1:]): acc.append(acc[-1] + math.dist(p, q))
    def at(t): return D[min(range(len(D)), key=lambda i: abs(acc[i] - min(t, acc[-1])))]
    pa, pb = at(a), at(b); d = (pa[0] - pb[0], pa[1] - pb[1]); l = math.hypot(*d) or 1.0
    return pa, (d[0] / l, d[1] / l)

def corner_point(Pa, ea, Pb, eb, c, reach=14.0):
    """where the straight end-tangents of two strokes meet (the real corner), or None when they do not meet near the ring"""
    (a1, d1), (a2, d2) = end_line(Pa, ea), end_line(Pb, eb)
    cr = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(cr) < 0.17: return None
    w = (a2[0] - a1[0], a2[1] - a1[1]); s1 = (w[0] * d2[1] - w[1] * d2[0]) / cr; s2 = (w[0] * d1[1] - w[1] * d1[0]) / cr
    if not (-3 <= s1 <= reach and -3 <= s2 <= reach): return None
    X = (a1[0] + s1 * d1[0], a1[1] + s1 * d1[1])
    return X if math.dist(X, c) <= reach else None

def set_corner(s, end, X, keep=5.0):
    """cut the stroke back to clean ink (arc `keep` from the end) and run straight into the corner X"""
    P = s["P"]
    if s.get("axis"): s["P"] = [X, P[1]] if end == 0 else [P[0], X]; return
    D = resample(P, 0.5)
    if end == 0:
        acc = 0.0; k = 0
        while k < len(D) - 1 and acc < keep: acc += math.dist(D[k], D[k + 1]); k += 1
        s["P"] = [X] + D[k:]
    else:
        acc = 0.0; k = len(D) - 1
        while k > 0 and acc < keep: acc += math.dist(D[k], D[k - 1]); k -= 1
        s["P"] = D[:k + 1] + [X]

def sid_of(S, i): return next(s for s in S if s["id"] == i)


def drop_ghosts(S, tol=4.0, frac=0.8):
    """a stroke lying along a longer one (a doubled trace of the same ink) is a ghost: drop it; purple bar pieces are left for the bar merge"""
    S = sorted(S, key=lambda s: -seglen(s["P"])); keep = []
    for s in S:
        pts = resample(s["P"], 1.0); ghost = False
        for k in keep:
            if s["role"] == "struct" and k["role"] == "struct": continue
            D = resample(k["P"], 0.5)
            if np.mean([min(math.dist(p, q) for q in D) <= tol for p in pts]) >= frac: ghost = True; break
        if not ghost: keep.append(s)
    return keep


def short_ok(s, E, reach=12.0):
    """a short stroke is real only if both of its ends sit on a marker (red dot or ring): a stem between two marks, not a spur at one"""
    M = [(c[0] / PX, c[1] / PX) for c in E["red"]] + [(c[0] / PX, c[1] / PX) for c in E["rings"]]
    return all(any(math.dist(e, m) <= reach for m in M) for e in (s["P"][0], s["P"][-1]))

def build(name, scores=None):
    E = json.load(open(os.path.join(HERE, "trace", "extracted", name + ".json"))); qa = []
    S = []
    for role, pl in E["strokes"]:
        P = [(x / PX, y / PX) for x, y in pl]
        if len(P) < 2: continue
        S.append({"role": role, "P": P})
    rg = [(c[0] / PX, c[1] / PX) for c in E["rings"]]
    for s in list(S):                                                   # orange ink that is only a speck, or a short arc beside a ring, is the markup circle itself
        if s["role"] != "accent": continue
        L = seglen(s["P"]); near = any(min(math.dist(s["P"][0], c), math.dist(s["P"][-1], c)) < 14 for c in rg)
        if L < 10 or (L < 18 and near):
            cx = float(np.mean([p[0] for p in s["P"]])); cy = float(np.mean([p[1] for p in s["P"]]))
            if not any(math.dist((cx, cy), c) < 10 for c in rg): rg.append((cx, cy)); E["rings"].append([cx * PX, cy * PX])
            S.remove(s); qa.append("orange speck at (%.0f,%.0f) treated as a markup circle" % (cx, cy))
    S = [s for s in S if s["role"] == "struct" or seglen(s["P"]) >= 10.5 or (seglen(s["P"]) >= 8.0 and short_ok(s, E))]               # colour fringes around the dots are shorter than any real stroke
    main = max([s for s in S if s["role"] == "struct"], key=lambda s: seglen(s["P"]), default=None)
    my = float(np.mean([p[1] for p in main["P"]])) if main and seglen(main["P"]) >= 25 else None
    def keep(s):
        if s["role"] != "struct": return True
        if seglen(s["P"]) >= 9.0: return True
        xs = [p[0] for p in s["P"]]; ys = [p[1] for p in s["P"]]                       # a short purple piece survives only as a continuation of the bar (e.g. past a red dot at its end)
        return my is not None and seglen(s["P"]) >= 3.5 and (max(xs) - min(xs)) >= 1.5 * (max(ys) - min(ys)) and abs(float(np.mean(ys)) - my) <= 3.0
    S = [s for s in S if keep(s)]
    S = drop_ghosts(S)
    S = merge_pieces(S, [((c[0] / PX, c[1] / PX), c[2] / PX if len(c) > 2 else 6.5) for c in E["rings"]])
    # purple fragments lying along the bar are bar ink (they may extend its ends) or ghosts of it: absorb, never keep as strokes
    bar = next((s for s in S if s.get("bar")), None)
    if bar:
        yb = bar["P"][0][1]; rest = []
        for s in S:
            if s is bar or s["role"] != "struct": rest.append(s); continue
            ys = [p[1] for p in s["P"]]
            if all(abs(y - yb) <= 5.0 for y in ys): bar["P"] = [(min(bar["P"][0][0], min(p[0] for p in s["P"])), yb), (max(bar["P"][1][0], max(p[0] for p in s["P"])), yb)]
            else: rest.append(s)
        S = rest
    # smooth + resample; flatten bars; straighten long straight verticals
    for s in S:
        P = s["P"]
        if s.get("bar"):
            y = float(np.mean([p[1] for p in P])); y = 26.0 if abs(y - 26.0) < 1.8 else y
            s["P"] = [(min(p[0] for p in P), y), (max(p[0] for p in P), y)]; continue
        Q = resample(chaikin(P, 2), 1.0)
        longv = seglen(Q) >= 30
        if seglen(Q) >= 12 and dev_from_chord(Q) <= (4.0 if longv else 3.0):
            dx, dy = Q[-1][0] - Q[0][0], Q[-1][1] - Q[0][1]; vt = 12 if longv else 8          # long strokes lean a little in a hand drawing: still meant vertical
            if abs(math.degrees(math.atan2(dx, dy))) <= vt or abs(math.degrees(math.atan2(dx, -dy))) <= vt:      # near vertical -> one exactly vertical segment
                x = float(np.mean([p[0] for p in Q])); Q = [(x, Q[0][1]), (x, Q[-1][1])]; s["axis"] = "v"
            elif abs(math.degrees(math.atan2(dy, dx))) <= 8 or abs(math.degrees(math.atan2(dy, -dx))) <= 8:   # near horizontal -> one exactly horizontal segment
                y = float(np.mean([p[1] for p in Q])); Q = [(Q[0][0], y), (Q[-1][0], y)]; s["axis"] = "h"
        s["P"] = Q
    # a short link stroke at a ring stands in for a sharp 2-stroke corner: drop it, the neighbours then extend to the ring centre
    reds_real = [(c[0] / PX, c[1] / PX) for c in E["red"]]; rg = [(c[0] / PX, c[1] / PX) for c in E["rings"]]
    def is_link(s):
        if s.get("bar") or s["role"] == "struct" or seglen(s["P"]) >= 14: return False
        near = [c for c in rg if min(math.dist(p, c) for p in resample(s["P"], 0.5)) <= 9.0]
        if not near: return False
        c = near[0]; far = s["P"][-1] if math.dist(s["P"][0], c) <= math.dist(s["P"][-1], c) else s["P"][0]
        return not any(math.dist(far, r) <= 9.0 for r in reds_real)       # a stem between a red dot and a ring is a real stroke
    for s in [s for s in S if is_link(s)]:
        S.remove(s); qa.append("short link at a ring removed (%.1f units)" % seglen(s["P"]))
    S.sort(key=lambda s: (ROLE_ORDER[s["role"]], s["P"][0][1], s["P"][0][0]))
    for i, s in enumerate(S): s["id"] = "s%d" % (i + 1)
    dense = lambda P: resample(P, 0.5)
    J = []
    def snap(s, pt):
        """make the stroke pass through pt: an end within reach of it moves/extends to pt; otherwise pt is inserted mid-stroke. Bars stay flat (their junction is the projection)."""
        P = s["P"]
        if s.get("bar"): return "middle"
        if s.get("axis"):
            ds, de = math.dist(P[0], pt), math.dist(P[-1], pt); ax = 0 if s["axis"] == "v" else 1
            if ds <= de and ds < 11.5 and ds < 0.4 * seglen(P) + 3: s["P"] = [pt, P[1]]; return "start"
            if de < ds and de < 11.5 and de < 0.4 * seglen(P) + 3: s["P"] = [P[0], pt]; return "end"
            return "middle"
        D = dense(P); d, i, f = nearest(D, pt); ds, de = math.dist(P[0], pt), math.dist(P[-1], pt)
        if ds <= de and ds < 11.5 and f < 0.4:
            s["P"] = [pt] + (P[1:] if ds < 3.0 else P); return "start"
        if de < ds and de < 11.5 and f > 0.6:
            s["P"] = (P[:-1] if de < 3.0 else P) + [pt]; return "end"
        bi, bd = 0, 1e9
        for k in range(len(P) - 1):
            a, b = P[k], P[k + 1]; L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2 or 1e-9
            u = max(0, min(1, ((pt[0] - a[0]) * (b[0] - a[0]) + (pt[1] - a[1]) * (b[1] - a[1])) / L2)); q = (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])); dd = math.dist(q, pt)
            if dd < bd: bi, bd = k, dd
        s["P"] = P[:bi + 1] + [pt] + P[bi + 1:]; return "middle"
    markers = []
    reds = []
    for c in E["red"]:
        c = (c[0] / PX, c[1] / PX)
        if not any(math.dist(c, r) < 3.5 for r in reds): reds.append(c)
    markers += [("red", c, 9.0) for c in reds] + [("touch", (c[0] / PX, c[1] / PX), c[2] / PX + 5.5 if len(c) > 2 else 11.5) for c in E["rings"]]
    mpts = [c for _, c, _ in markers]
    nid = [len(S)]; lone = []
    for t, c, R in markers:
        mem = []
        for s in S:
            d, i, f = nearest(dense(s["P"]), c)
            if d <= R:
                if t == "red" and s["role"] == "accent" and 0.08 < f < 0.92 and d > 5.0: continue         # passes by the dot without touching it
                if t == "touch" and not s.get("bar") and (f < 0.15 or f > 0.85):
                    endpt = s["P"][0] if f < 0.5 else s["P"][-1]
                    if d > 6 and any(s["id"] in j["ids"] and math.dist((j["x"], j["y"]), endpt) < 0.7 for j in J): continue      # that end already belongs to a red dot
                mem.append((d, s))
        if t == "touch" and len(mem) >= 3:                              # a ring marks two strokes meeting at a corner
            ends = sorted([m for m in mem if not (0.15 < nearest(dense(m[1]["P"]), c)[2] < 0.85) and not m[1].get("bar")], key=lambda m: m[0])
            if len(ends) >= 3: mem = [m for m in mem if m not in ends] + ends[:2]
        if t == "touch" and len(mem) >= 3:                              # two strokes ending at the ring form the corner; a stroke merely passing near it is a bystander
            fr = lambda m: nearest(dense(m[1]["P"]), c)[2]
            endm = [m for m in mem if (fr(m) < 0.15 or fr(m) > 0.85) and not m[1].get("bar")]
            if len(endm) >= 2: mem = endm[:2] + [m for m in mem if m[1].get("bar")]
        if len(mem) == 1 and not mem[0][1].get("bar"):
            # a lone stroke running through a ring/dot at a sharp corner = two strokes meeting there: split it at the marker
            s = mem[0][1]; D = dense(s["P"]); d, i, f = nearest(D, c)
            if 4 < i < len(D) - 5:
                nid[0] += 1; t2 = {"role": s["role"], "P": D[i:], "id": "s%d" % nid[0]}; s["P"] = D[:i + 1]; S.append(t2); mem = [(d, s), (d, t2)]
        if len(mem) < 2: lone.append((t, c, mem[0][1] if mem else None)); continue
        if t == "touch" and len(mem) == 2 and not any(m[1].get("bar") for m in mem):
            ea = [0 if nearest(dense(m[1]["P"]), c)[2] < 0.5 else -1 for m in mem]
            frs = [nearest(dense(m[1]["P"]), c)[2] for m in mem]
            if all(f < 0.15 or f > 0.85 for f in frs):
                X = corner_point(mem[0][1]["P"], ea[0], mem[1][1]["P"], ea[1], c)
                if X is None and all(math.dist(m[1]["P"][e], c) <= 14 for m, e in zip(mem, ea)): X = c          # a cusp: nearly parallel lines meeting at the ring tip
                if X is not None:                                       # two strokes meeting at a sharp corner: the corner is where their lines meet
                    for (d, st), e in zip(mem, ea): set_corner(st, e, X)
                    J.append({"t": t, "x": X[0], "y": X[1], "ids": [mem[0][1]["id"], mem[1][1]["id"]], "corner": True}); continue
        bar = next((s for d, s in mem if s.get("bar")), None); pt = (c[0], bar["P"][0][1]) if bar else c
        if not bar:                                                       # a stroke running through the marker hosts the junction: put it on that stroke, not on the dot centre
            host = None
            for d, s in mem:
                D = dense(s["P"]); dd, i, f = nearest(D, c)
                if 0.08 < f < 0.92 and (host is None or dd < host[0]): host = (dd, D[i])
            if host: pt = host[1]
        for d, s in mem:                                                  # the junction lies on any exactly-vertical / horizontal member
            if s.get("axis") == "v": pt = (s["P"][0][0], pt[1])
            elif s.get("axis") == "h": pt = (pt[0], s["P"][0][1])
        J.append({"t": t, "x": pt[0], "y": pt[1], "ids": []})
        for d, s in mem: snap(s, pt); J[-1]["ids"].append(s["id"])
    # unmarked contacts: a free endpoint lying on / next to another stroke (away from any marker)
    injn = lambda sid, pt: any(sid in j["ids"] and math.dist((j["x"], j["y"]), pt) < 0.7 for j in J)
    for s in list(S):
        if s.get("bar"): continue
        for end in (0, -1):
            e = s["P"][end]
            if injn(s["id"], e) or any(math.dist(e, m) < 8 for m in mpts): continue
            best = None
            for o in S:
                if o is s: continue
                d, i, f = nearest(dense(o["P"]), e)
                if o.get("bar"): d = abs(e[1] - o["P"][0][1]); q = (e[0], o["P"][0][1])
                else:
                    q = dense(o["P"])[i]
                    if o.get("axis") == "v": q = (o["P"][0][0], q[1])
                    elif o.get("axis") == "h": q = (q[0], o["P"][0][1])
                    d = math.dist(q, e)
                if d <= 4.0 and (best is None or d < best[0]): best = (d, o, q)
            if best:
                d, o, q = best; snap(o, q); s["P"] = ([q] + s["P"][1:]) if end == 0 else (s["P"][:-1] + [q])
                J.append({"t": "red", "x": q[0], "y": q[1], "ids": [s["id"], o["id"]]}); qa.append("unmarked contact %s/%s at (%.0f,%.0f)" % (s["id"], o["id"], q[0], q[1]))
    # standing rule: a stroke never hangs from the very end of the bar; the bar runs on past the junction
    for j in J:
        bar = next((sid_of(S, i) for i in j["ids"] if sid_of(S, i).get("bar")), None)
        if not bar: continue
        (x0, y), (x1, _) = bar["P"][0], bar["P"][-1]
        if j["x"] > x1 - 6: bar["P"][-1] = (min(98.5, j["x"] + 8.0), y)
        if j["x"] < x0 + 6: bar["P"][0] = (max(1.5, j["x"] - 8.0), y)
    # a ring on a lone stroke end: a neighbour that runs along it (overlapped by the drawing) and joined mid-way really starts at the ring
    for t, c, host in lone:
        done = False
        if host is not None:
            hp = host["P"]; end = 0 if math.dist(hp[0], c) < math.dist(hp[-1], c) else -1; ept = hp[end]
            for j in list(J):
                if j["t"] != "red" or host["id"] not in j["ids"] or len(j["ids"]) != 2: continue
                other = next(i for i in j["ids"] if i != host["id"]); o = sid_of(S, other)
                if math.dist((j["x"], j["y"]), ept) > 30: continue
                oe = 0 if math.dist(o["P"][0], (j["x"], j["y"])) < 0.7 else -1 if math.dist(o["P"][-1], (j["x"], j["y"])) < 0.7 else None
                if oe is None: continue
                o["P"] = ([ept] + o["P"][1:]) if oe == 0 else (o["P"][:-1] + [ept]); J.remove(j)
                J.append({"t": t, "x": ept[0], "y": ept[1], "ids": [host["id"], other]}); done = True; qa.append("ring at (%.0f,%.0f): %s extended along %s to the ring" % (c[0], c[1], other, host["id"])); break
        if not done: qa.append("%s marker at (%.0f,%.0f) has %d member(s)" % (t, c[0], c[1], 1 if host is not None else 0))
    # red dots only identify joints; they must not shape the strokes. Discard the ink around each dot and join straight into it.
    for j in J:
        if j["t"] != "red": continue
        pt = (j["x"], j["y"])
        for sid in dict.fromkeys(j["ids"]):
            st = sid_of(S, sid)
            if st.get("bar") or st.get("axis") or len(st["P"]) < 3: continue
            P = st["P"]; Rd = 7.0
            if math.dist(P[0], pt) < 0.7:
                k = next((i for i, p in enumerate(P) if math.dist(p, pt) >= Rd), None)
                if k is not None and k < len(P) - 2: st["P"] = [pt] + P[k:]
            elif math.dist(P[-1], pt) < 0.7:
                k = next((i for i in range(len(P) - 1, -1, -1) if math.dist(P[i], pt) >= Rd), None)
                if k is not None and k > 1: st["P"] = P[:k + 1] + [pt]
            else:
                i0 = min(range(len(P)), key=lambda i: math.dist(P[i], pt)); a = i0; b = i0
                while a > 0 and math.dist(P[a - 1], pt) < Rd: a -= 1
                while b < len(P) - 1 and math.dist(P[b + 1], pt) < Rd: b += 1
                after = seglen(P[b:]); before = seglen(P[:a + 1])
                if after < 9.0 and a > 0: st["P"] = P[:a] + [pt]                     # a stub poking past the joint: the stroke simply ends at the joint
                elif before < 9.0 and b < len(P) - 1: st["P"] = [pt] + P[b + 1:]
                elif a > 0 and b < len(P) - 1: st["P"] = P[:a] + [pt] + P[b + 1:]
    # a stroke that folds sharply at a red dot is two strokes meeting there
    for j in [j for j in J if j["t"] == "red" and not j.get("corner")]:
        pt = (j["x"], j["y"])
        for sid in list(dict.fromkeys(j["ids"])):
            st = sid_of(S, sid)
            if st.get("bar") or st.get("axis"): continue
            D = resample(st["P"], 0.5); i0 = min(range(len(D)), key=lambda i: math.dist(D[i], pt))
            if math.dist(D[i0], pt) > 1.5 or not 12 < i0 < len(D) - 13: continue
            vin = (D[i0][0] - D[i0 - 12][0], D[i0][1] - D[i0 - 12][1]); vout = (D[i0 + 12][0] - D[i0][0], D[i0 + 12][1] - D[i0][1])
            li, lo = math.hypot(*vin) or 1, math.hypot(*vout) or 1
            if _ang((vin[0] / li, vin[1] / li), (vout[0] / lo, vout[1] / lo)) < 70: continue
            nid[0] += 1; new = {"role": st["role"], "P": D[i0:], "id": "s%d" % nid[0]}; st["P"] = D[:i0 + 1]; S.append(new)
            for jj in J:
                if jj is not j and sid in jj["ids"] and math.dist((jj["x"], jj["y"]), D[-1]) < 0.7: jj["ids"] = [new["id"] if i == sid else i for i in jj["ids"]]
            j["ids"].append(new["id"])
    # a red dot in the middle of one straight stroke splits it in two: put it back together (the dot becomes a mid-stroke joint)
    changed = True
    while changed:
        changed = False
        for j in J:
            if j["t"] != "red" or j.get("corner"): continue
            pt = (j["x"], j["y"]); ends = []
            for sid in dict.fromkeys(j["ids"]):
                st = sid_of(S, sid)
                if st.get("bar"): continue
                if math.dist(st["P"][0], pt) < 0.7: ends.append((st, 0))
                elif math.dist(st["P"][-1], pt) < 0.7: ends.append((st, -1))
            done = False
            for ia in range(len(ends)):
                for ib in range(ia + 1, len(ends)):
                    (a, ea), (b, eb) = ends[ia], ends[ib]
                    if a["role"] != b["role"]: continue
                    da = end_line(a["P"], ea)[1]; db = end_line(b["P"], eb)[1]
                    if _ang(da, (-db[0], -db[1])) > 25: continue                    # not a straight continuation
                    A = a["P"] if ea == -1 else a["P"][::-1]; B = b["P"] if eb == 0 else b["P"][::-1]
                    a["P"] = A + B[1:]; a["axis"] = None
                    for jj in J: jj["ids"] = [a["id"] if i == b["id"] else i for i in jj["ids"]]
                    S.remove(b); done = True; break
                if done: break
            if done: changed = True; break
    # final pass: any stroke that is nearly vertical / horizontal becomes ONE exact segment (ring splits create such pieces after the first straightening)
    def regular(st):
        P = st["P"]; xs = [p[0] for p in P]; ys = [p[1] for p in P]
        if st.get("bar") or st.get("axis") or len(P) < 3: return
        w, h = max(xs) - min(xs), max(ys) - min(ys); L = seglen(P)
        if L > 1.3 * max(w, h) + 1: return                                  # folds back on itself: not a plain line, leave for review
        if h >= 5 and w <= 1.6 + 0.07 * h: ax = "v"
        elif w >= 5 and h <= 1.6 + 0.03 * w: ax = "h"
        else: return
        jp = [(j["x"], j["y"]) for j in J if st["id"] in j["ids"]]
        old = [P[0], P[-1]]
        if ax == "v":
            x = float(np.mean([q[0] for q in jp])) if jp else float(np.mean(xs)); new = [(x, P[0][1]), (x, P[-1][1])]
        else:
            y = float(np.mean([q[1] for q in jp])) if jp else float(np.mean(ys)); new = [(P[0][0], y), (P[-1][0], y)]
        st["P"] = new; st["axis"] = ax
        for j in J:
            if st["id"] not in j["ids"]: continue
            o = (j["x"], j["y"]); n = (x, o[1]) if ax == "v" else (o[0], y); j["x"], j["y"] = n
            for t2 in S:                                                    # other strokes ending at the junction follow it
                if t2 is st or t2["id"] not in j["ids"] or t2.get("bar"): continue
                for e in (0, -1):
                    if math.dist(t2["P"][e], o) < 0.7: t2["P"][e] = n
    for st in S: regular(st)
    # final geometry -> members with where/at
    sid2 = {s["id"]: s for s in S}; junc = []
    for j in J:
        mem = []
        for sid in dict.fromkeys(j["ids"]):
            P = sid2[sid]["P"]; pt = (j["x"], j["y"]); d, i, f = nearest(dense(P), pt)
            where = "start" if math.dist(P[0], pt) < 0.7 else "end" if math.dist(P[-1], pt) < 0.7 else "middle"
            mem.append({"stroke": sid, "at": 0.0 if where == "start" else 1.0 if where == "end" else round(f, 3), "where": where})
        junc.append({"t": j["t"], "x": round(j["x"], 1), "y": round(j["y"], 1), "members": mem, "loose": False})
    # ball ends: a free end whose ink is clearly thicker than the stroke
    ends = {}
    P0 = cv2.imread(os.path.join(HERE, "trace", "patches", name + ".png")); M = ink.masks(P0)
    for s in S:
        col = {"body": "blue", "second": "green", "accent": "orange", "struct": "purple"}[s["role"]]
        dt = cv2.distanceTransform((M[col] > 0).astype(np.uint8), cv2.DIST_L2, 3); st = []
        free = lambda pt: not any(math.dist(pt, (j["x"], j["y"])) < 0.7 for j in junc)
        ws = [dt[min(399, int(p[1] * PX)), min(399, int(p[0] * PX))] for p in s["P"][::3]]; med = float(np.median(ws)) if ws else 1
        for end in (0, -1):
            p = s["P"][end]; x, y = int(p[0] * PX), int(p[1] * PX); w = dt[max(0, y - 8):y + 9, max(0, x - 8):x + 9].max() if dt.size else 0
            st.append("ball" if free(p) and s["role"] != "struct" and w >= max(1.6 * med, med + 3) else "plain")
        if "ball" in st: ends[s["id"]] = st
    strokes = [[s["role"], "M" + " L".join("%.1f %.1f" % p for p in s["P"]), s["id"]] for s in S]
    sc = (scores or {}).get(name)
    return {"glyph": name, "iast": name, "variant": None, "strokes": strokes, "junctions": junc, "ends": ends, "score": sc, "source": "redraw"}, qa

if __name__ == "__main__":
    sc = json.load(open(os.path.join(HERE, "owner_scores.json"))); flat = {}
    for k in ("A", "B"): flat.update(sc.get(k, {}))
    ids = sys.argv[2:] or [k for k, v in sorted(flat.items()) if v in (3, 4) and os.path.exists(os.path.join(HERE, "trace", "extracted", k + ".json"))]
    L = []; 
    for n in ids:
        l, qa = build(n, flat); L.append(l); print(n, flat.get(n), "; ".join(qa) or "ok")
    json.dump({"script": "bengali", "box": 100, "letters": L}, open(sys.argv[1], "w"))
