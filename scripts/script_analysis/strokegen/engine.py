"""Script-neutral stroke-letter engine.

It knows nothing about any one writing system.  A script is two things: its real letters (a stroke graph: roles, polylines, junctions,
end styles) and a settings file (models/<script>.json).  New letters are made by
  1. taking the TOPOLOGY of a real letter (which strokes exist, which ends meet which, bar / verticals / bodies),
  2. re-drawing its skeleton (bar span, vertical positions and lengths) within the settings' jitter,
  3. re-drawing every body stroke from the real strokes' own turning profiles (optionally spliced from two real strokes), fitted onto its
     anchors so each junction lands exactly where it was declared,
  4. rejecting anything that crosses itself, touches a stranger, has junction angles outside the script's range, leaves the box, or is too
     close to a real letter (novelty).
Output uses the same graph format as the real letters, so the same loaders and renderers work.

usage: python3 engine.py <script> [count] [seed]  ->  generated_<script>.json  (frame y down, 100 x 100; headings in degrees, y up)"""
import json, math, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# ---------------------------------------------------------------- geometry
def parse(d): v = [float(x) for x in re.findall(r"-?\d+\.?\d*", d)]; return list(zip(v[0::2], v[1::2]))
def fmt(P): return "M" + " L".join("%.1f %.1f" % p for p in P)
def head(a, b): return math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))
def dh(a, b): return (b - a + 180) % 360 - 180
def length(P): return sum(math.dist(p, q) for p, q in zip(P, P[1:]))

def resample(P, step=1.0):
    out = [P[0]]
    for a, b in zip(P, P[1:]):
        n = max(1, int(round(math.dist(a, b) / step)))
        for i in range(1, n + 1): out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out

def point_at(P, f):
    """point at fraction f of the arc length"""
    L = length(P); t = f * L; acc = 0.0
    for a, b in zip(P, P[1:]):
        d = math.dist(a, b)
        if acc + d >= t and d > 0: u = (t - acc) / d; return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
        acc += d
    return P[-1]

def param_of(P, pt):
    """fraction of arc length of the point of P nearest to pt"""
    best = (1e9, 0.0); acc = 0.0; L = max(length(P), 1e-9)
    for a, b in zip(P, P[1:]):
        d = math.dist(a, b)
        if d > 0:
            u = max(0.0, min(1.0, ((pt[0] - a[0]) * (b[0] - a[0]) + (pt[1] - a[1]) * (b[1] - a[1])) / d / d))
            q = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u); dd = math.dist(q, pt)
            if dd < best[0]: best = (dd, (acc + u * d) / L)
        acc += d
    return best[1]

def profile(P, step):
    """turning profile: heading of each step of the resampled stroke (degrees, y up)"""
    R = resample(P, step); return [head(a, b) for a, b in zip(R, R[1:])]

def build(h, step, scale=1.0):
    P = [(0.0, 0.0)]
    for a in h: P.append((P[-1][0] + math.cos(math.radians(a)) * step * scale, P[-1][1] - math.sin(math.radians(a)) * step * scale))
    return P

def rotate(P, deg, about=(0.0, 0.0)):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(about[0] + (x - about[0]) * c + (y - about[1]) * s, about[1] - (x - about[0]) * s + (y - about[1]) * c) for x, y in P]   # y is down: +deg is anticlockwise on the page

def similarity(P, S, E):
    """scale and rotate P (whose own ends are P[0], P[-1]) so that it runs from S to E exactly; returns (points, scale)"""
    c0, c1 = P[0], P[-1]; dc = math.dist(c0, c1)
    if dc < 1e-6: return None, 0.0
    k = math.dist(S, E) / dc; rot = head(S, E) - head(c0, c1)
    Q = rotate([((x - c0[0]) * k, (y - c0[1]) * k) for x, y in P], rot)
    Q = [(x + S[0], y + S[1]) for x, y in Q]; Q[0] = S; Q[-1] = E
    return Q, k

def seg_cross(a, b, c, d):
    def o(p, q, r): return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0

def turning(P, step=3.0):
    """(total absolute turn, reversals) of a stroke, measured at a coarse step so rounding noise in the stored coordinates does not count"""
    R = resample(P, 0.5); k = max(1, int(step / 0.5)); R = R[::k] + ([R[-1]] if (len(R) - 1) % k else [])
    h = [head(a, b) for a, b in zip(R, R[1:])]; return sum(abs(dh(a, b)) for a, b in zip(h, h[1:])), _reversals(h)

def _turn(P):
    """signed total turn of a polyline in degrees (+ anticlockwise on the page)"""
    h = profile(P, 1.0); return sum(dh(a, b) for a, b in zip(h, h[1:]))

def _reversals(h, arc=25.0):
    """how many times the stroke changes its turning side, ignoring turns smaller than `arc` degrees in total"""
    side = 0; run = 0.0; n = 0; h = [x for x in h]
    for a, b in zip(h, h[1:]):
        d = dh(a, b)
        if abs(d) < 0.5: continue
        sg = 1 if d > 0 else -1
        if sg == side: run += abs(d)
        else:
            if run >= arc or side == 0:
                if side != 0: n += 1
                side = sg; run = abs(d)
            else: run += 0
    return n

# ---------------------------------------------------------------- the model of one script
class Script:
    def __init__(self, name):
        self.cfg = json.load(open(os.path.join(HERE, "models", name + ".json"))); self.name = name
        G = json.load(open(os.path.join(ROOT, self.cfg["graph"])))
        self.letters = [self._read(l) for l in G["letters"]]
        self.ranges = self._ranges()
        ex = set(self.cfg["donors"]["exclude_junction_types"]); self.donors = []
        for l in self.letters:
            if any(j["t"] in ex for j in l["junctions"]): continue
            if self.cfg["donors"]["exclude_self_junctions"] and any(len({m["stroke"] for m in j["members"]}) < 2 for j in l["junctions"]): continue
            self.donors.append(l)
        sh = self.cfg["shape"]; self.step = sh["resample_step"]
        # shape library: every real non-straight stroke, by role
        self.shapes = []
        for l in self.letters:
            for sid, s in l["S"].items():
                if s["kind"] == "body" and len(s["P"]) > 2 and length(s["P"]) >= sh["min_len"]: self.shapes.append(s)

    def _ranges(self):
        """what the real letters span, measured here so that no number about the script is written in the engine"""
        def q(xs, p): xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))]
        W, H, I, T, V = [], [], [], [], []
        for l in self.letters:
            pts = [p for s in l["S"].values() for p in s["P"]]; W.append(max(p[0] for p in pts) - min(p[0] for p in pts)); H.append(max(p[1] for p in pts) - min(p[1] for p in pts))
            I.append(sum(length(s["P"]) for s in l["S"].values()))
            for s in l["S"].values():
                if s["kind"] == "body": t, v = turning(s["P"]); T.append(t); V.append(v)
        return {"w": (q(W, .05), q(W, 1)), "h": (q(H, .05), q(H, 1)), "ink": (q(I, .05), q(I, .97)), "turn_max": q(T, .95), "reversals_max": max(V)}

    def _read(self, l):
        S = {}
        for r, d, sid in l["strokes"]:
            P = parse(d); kind = "bar" if r == "struct" and len(P) == 2 and abs(P[0][1] - P[1][1]) < .6 and abs(P[0][0] - P[1][0]) > 30 else \
                "vertical" if len(P) == 2 and abs(P[0][0] - P[1][0]) < 1.0 else "body" if len(P) > 2 or r in ("body", "second") else "other"
            S[sid] = {"id": sid, "role": r, "P": P, "kind": kind, "ends": l.get("ends", {}).get(sid, ["plain", "plain"])}
        return {"iast": l["iast"], "S": S, "junctions": l["junctions"]}

    # ---------------------------------------------------------------- one letter
    def make(self, rng):
        c = self.cfg; sk = c["skeleton"]; fr = c["frame"]; sh = c["shape"]
        D = rng.choice(self.donors); S = D["S"]; new = {}
        # --- skeleton: bar, verticals, floating bits
        bar = next((s for s in S.values() if s["kind"] == "bar"), None)
        by = fr["bar_y"]
        if bar:
            x0, x1 = sorted((bar["P"][0][0], bar["P"][1][0])); j = sk["bar_jitter_x"]
            nx0 = x0 + rng.uniform(-j, j); nx1 = x1 + rng.uniform(-j, j)
            if nx1 - nx0 < sk["bar_min_width"]: nx1 = nx0 + sk["bar_min_width"]
            ordered = bar["P"][0][0] <= bar["P"][1][0]; bp = [(nx0, by), (nx1, by)] if ordered else [(nx1, by), (nx0, by)]
            new[bar["id"]] = dict(bar, P=bp); bx0, bx1 = nx0, nx1
        for sid, s in S.items():
            if s["kind"] != "vertical": continue
            x = s["P"][0][0]
            if bar: f = (x - x0) / (x1 - x0) + rng.uniform(-sk["vertical_x_frac_jitter"], sk["vertical_x_frac_jitter"]); x = bx0 + f * (bx1 - bx0)
            else: x += rng.uniform(-sk["vertical_x_jitter_no_bar"], sk["vertical_x_jitter_no_bar"])
            ya, yb = s["P"][0][1], s["P"][1][1]
            jy = sk["vertical_y_jitter"]
            ya2 = by if abs(ya - by) < 1.0 else ya + rng.uniform(-jy, jy); yb2 = min(sk["vertical_bottom_max"], yb + rng.uniform(-jy, jy)) if abs(yb - by) > 1 else by
            if abs(ya2 - yb2) < 1.0: ya2, yb2 = ya, yb
            new[sid] = dict(s, P=[(x, ya2), (x, yb2)])
        for sid, s in S.items():
            if s["kind"] == "other": d = (rng.uniform(-sk["float_shift"], sk["float_shift"]), rng.uniform(-sk["float_shift"], sk["float_shift"])); new[sid] = dict(s, P=[(x + d[0], y + d[1]) for x, y in s["P"]])
        # --- bodies, in dependency order (a stroke waits until the strokes its ends meet are drawn; a cycle is broken by drawing the first)
        todo = [sid for sid, s in S.items() if s["kind"] == "body"]; refs = self._refs(D)
        while todo:
            ready = [sid for sid in todo if all(not refs[(sid, w)] or self._anchor(refs, sid, w, new) is not None for w in ("start", "end"))]
            sid = (ready or todo)[0]
            r = self._draw(rng, S[sid], self._anchor(refs, sid, "start", new), self._anchor(refs, sid, "end", new), new)
            if r is None: return None
            new[sid] = dict(S[sid], P=r[0], ends=r[1]); todo.remove(sid)
        return self._finish(D, new)

    def _refs(self, D):
        """for every stroke end: the other members of its junction(s)"""
        R = {(sid, w): [] for sid in D["S"] for w in ("start", "end")}
        for j in D["junctions"]:
            for m in j["members"]:
                if m["where"] in ("start", "end"):
                    R[(m["stroke"], m["where"])] += [(o["stroke"], o["where"], o["at"]) for o in j["members"] if o["stroke"] != m["stroke"]]
        return R

    def _anchor(self, refs, sid, w, new):
        for o, ow, at in refs[(sid, w)]:
            if o in new:
                P = new[o]["P"]; return P[0] if ow == "start" else P[-1] if ow == "end" else point_at(P, at)
        return None

    # ---------------------------------------------------------------- a body stroke
    def _pick(self, rng, like):
        """a real stroke of similar length to `like` (turning profile donor)"""
        sh = self.cfg["shape"]; L = length(like["P"]); T = _turn(like["P"])
        cand = [s for s in self.shapes if 0.6 * L <= length(s["P"]) <= 1.6 * L and abs(_turn(s["P"]) - T) <= sh["turn_match"]] or \
               [s for s in self.shapes if abs(_turn(s["P"]) - T) <= 2 * sh["turn_match"]] or self.shapes
        return rng.choice(cand)

    def _shape(self, rng, like):
        sh = self.cfg["shape"]; A = self._pick(rng, like); hA = profile(A["P"], self.step); ends = list(A["ends"])
        if rng.random() < sh["splice_prob"] and len(hA) > 12:
            B = self._pick(rng, like); hB = profile(B["P"], self.step)
            if len(hB) > 12:
                ka = int(len(hA) * rng.uniform(*sh["splice_cut"])); kb = int(len(hB) * rng.uniform(*sh["splice_cut"]))
                off = hA[ka - 1] - hB[kb]; hA = hA[:ka] + [h + off for h in hB[kb:]]; ends = [ends[0], B["ends"][1]]
        return hA, ends

    def _draw(self, rng, like, a_s, a_e, placed):
        sh = self.cfg["shape"]; fr = self.cfg["frame"]
        for _ in range(30):
            h, ends = self._shape(rng, like); P0 = build(h, self.step, rng.uniform(*sh["length_scale"]))
            if a_s is not None and a_e is not None:
                if math.dist(a_s, a_e) < sh["min_chord"]: return None
                P, k = similarity(P0, a_s, a_e)
                if P is None or not (sh["fit_scale"][0] <= k <= sh["fit_scale"][1]): continue
                if abs(dh(head(P[0], P[1]), head(like["P"][0], like["P"][1]))) > sh["fit_heading_tol"] and rng.random() < .85: continue
            elif a_s is not None or a_e is not None:
                anchor = a_s if a_s is not None else a_e; rev = a_s is None
                Q = P0[::-1] if rev else P0; hh = head(like["P"][-1], like["P"][-2]) if rev else head(like["P"][0], like["P"][1])
                Q = rotate(Q, hh + rng.uniform(-1, 1) * sh["start_heading_jitter"] - head(Q[0], Q[1]), Q[0]); Q = [(x - Q[0][0] + anchor[0], y - Q[0][1] + anchor[1]) for x, y in Q]
                P = Q[::-1] if rev else Q
            else:
                d = (rng.uniform(-4, 4), rng.uniform(-4, 4)); R = like["P"]; Q = rotate(P0, head(R[0], R[1]) - head(P0[0], P0[1]), P0[0])
                P = [(x - Q[0][0] + R[0][0] + d[0], y - Q[0][1] + R[0][1] + d[1]) for x, y in Q]
            if not (sh["min_len"] <= length(P) <= sh["max_len"]) or not self._stroke_ok(P, placed): continue
            return P, ends
        return None

    def _stroke_ok(self, P, placed):
        """checks that need only this stroke and the ones already drawn: inside the box, no loop, plausible turning, no crossing"""
        fr = self.cfg["frame"]; rg = self.ranges
        if any(not (fr["margin_lo"] <= x <= fr["margin_hi"] and fr["margin_lo"] <= y <= fr["max_y"]) for x, y in P): return False
        t, v = turning(P)
        if t > rg["turn_max"] or v > min(rg["reversals_max"], self.cfg["shape"].get("max_reversals", 99)): return False
        R = resample(P, 0.5); R = R[::6]; hh = [head(a, b) for a, b in zip(R, R[1:])]
        if hh and max((abs(dh(a, b)) for a, b in zip(hh, hh[1:])), default=0) > self.cfg["shape"].get("max_corner", 360): return False
        for i in range(len(P) - 1):
            for k in range(i + 2, len(P) - 1):
                if seg_cross(P[i], P[i + 1], P[k], P[k + 1]): return False
        for o in placed.values():
            Q = o["P"]
            for i in range(len(P) - 1):
                for k in range(len(Q) - 1):
                    if seg_cross(P[i], P[i + 1], Q[k], Q[k + 1]): return False
        return True

    # ---------------------------------------------------------------- assemble + check
    def _finish(self, D, new):
        S = D["S"]; strokes = []; ends = {}
        for sid, s in S.items():
            P = new[sid]["P"]; strokes.append([s["role"], fmt(P), sid])
            e = new[sid].get("ends", s["ends"])
            if e != ["plain", "plain"]: ends[sid] = e
        J = []
        for j in D["junctions"]:
            mem = []; pts = []
            for m in j["members"]:
                P = new[m["stroke"]]["P"]
                if m["where"] == "start": pt = P[0]; at = 0.0
                elif m["where"] == "end": pt = P[-1]; at = 1.0
                else:
                    other = next((o for o in j["members"] if o["stroke"] != m["stroke"] and o["where"] in ("start", "end")), None)
                    pt = (new[other["stroke"]]["P"][0 if other["where"] == "start" else -1]) if other else point_at(P, m["at"]); at = param_of(P, pt)
                mem.append({"stroke": m["stroke"], "at": round(at, 2), "where": m["where"] if m["where"] != "middle" else "middle"}); pts.append(pt)
            J.append({"t": j["t"], "x": round(sum(p[0] for p in pts) / len(pts), 1), "y": round(sum(p[1] for p in pts) / len(pts), 1), "members": mem, "loose": len(mem) < 2})
        return {"glyph": "", "iast": "", "variant": None, "donor": D["iast"], "strokes": strokes, "junctions": J, "ends": ends}

    def why(self, L):
        """None if the letter is acceptable, else the name of the first check it fails"""
        c = self.cfg["checks"]; fr = self.cfg["frame"]; P = {s[2]: parse(s[1]) for s in L["strokes"]}
        pts = [p for Q in P.values() for p in Q]
        if any(not (fr["margin_lo"] <= x <= fr["margin_hi"] and fr["margin_lo"] <= y <= fr["max_y"]) for x, y in pts): return "box"
        rg = self.ranges
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if not (rg["w"][0] <= max(xs) - min(xs) <= rg["w"][1] + 2 and rg["h"][0] <= max(ys) - min(ys) <= rg["h"][1] + 2): return "extent"
        if not (rg["ink"][0] <= sum(length(Q) for Q in P.values()) <= rg["ink"][1]): return "ink"
        for sid, Q in P.items():
            if len(Q) > 2:
                tt, vv = turning(Q)
                if tt > rg["turn_max"] or vv > rg["reversals_max"]: return "turn/rev"
        for j in L["junctions"]:                                                 # every junction is one point: its members really meet
            pp = []
            for m in j["members"]:
                Q = P[m["stroke"]]; pp.append(Q[0] if m["where"] == "start" else Q[-1] if m["where"] == "end" else point_at(Q, m["at"]))
            if max(math.dist(a, b) for a in pp for b in pp) > 1.5: return "meet"
        ids = list(P)
        role = {x[2]: x[0] for x in L["strokes"]}; par = {i: i for i in ids}                  # one connected figure (accent marks may float)
        def find(a):
            while par[a] != a: par[a] = par[par[a]]; a = par[a]
            return a
        for j in L["junctions"]:
            ms = [m["stroke"] for m in j["members"]]
            for m in ms[1:]: par[find(m)] = find(ms[0])
        if len({find(i) for i in ids if role[i] != "accent"}) > 1: return "disconnected"
        for sid in ids:                                                          # no stroke crosses itself
            Q = P[sid]
            for i in range(len(Q) - 1):
                for k in range(i + 2, len(Q) - 1):
                    if seg_cross(Q[i], Q[i + 1], Q[k], Q[k + 1]): return "selfcross"
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                A, B = P[ids[a]], P[ids[b]]
                for i in range(len(A) - 1):
                    for k in range(len(B) - 1):
                        if seg_cross(A[i], A[i + 1], B[k], B[k + 1]): return "cross"
                RA = resample(A, 1.0); RB = resample(B, 1.0); rad = c["clearance_free_radius"]
                shared = [(j["x"], j["y"]) for j in L["junctions"] if {m["stroke"] for m in j["members"]} >= {ids[a], ids[b]}]
                for p in RA:
                    if any(math.dist(p, s) < rad for s in shared): continue
                    if any(math.dist(p, q) < c["clearance"] for q in RB if not any(math.dist(q, s) < rad for s in shared)): return "clear"
        for j in L["junctions"]:                                                 # junction angles
            ms = j["members"]
            for i in range(len(ms)):
                for k in range(i + 1, len(ms)):
                    d = []
                    for m in (ms[i], ms[k]):
                        Q = resample(P[m["stroke"]], 1.0); n = len(Q) - 1; ix = int(round(m["at"] * n)); w = 5
                        d.append(head(Q[ix], Q[min(n, ix + w)]) if m["where"] == "start" else head(Q[ix], Q[max(0, ix - w)]) if m["where"] == "end" else head(Q[ix], Q[min(n, ix + w)]))
                    ang = abs(dh(d[0], d[1]))
                    if ms[i]["where"] == "middle" or ms[k]["where"] == "middle": ang = min(ang, 180 - ang)
                    if ang < (c["min_touch_angle"] if j["t"] == "touch" else c["min_other_angle"]): return "angle"
        if c.get("accent_attached"):                                             # accents never float
            main = {find(i) for i in ids if role[i] != "accent"}
            if any(find(i) not in main for i in ids if role[i] == "accent"): return "floating"
        if c.get("free_end_gap"):                                                # a free end keeps its distance from every other stroke
            used = {(m["stroke"], m["where"]) for j in L["junctions"] for m in j["members"]}
            for sid in ids:
                for w, e in (("start", P[sid][0]), ("end", P[sid][-1])):
                    if (sid, w) in used: continue
                    if any(math.dist(e, q) < c["free_end_gap"] for o in ids if o != sid for q in resample(P[o], 1.0)): return "free end"
        if c.get("bar_balance_max"):                                             # what hangs under the bar is centred on it
            bars = [Q for sid, Q in P.items() if role[sid] == "struct" and len(Q) == 2 and abs(Q[0][1] - Q[1][1]) < 1]
            below = [p for sid, Q in P.items() if role[sid] in ("body", "second") for p in resample(Q, 2.0) if bars and p[1] > bars[0][0][1] + 2]
            if bars and below and abs(sum(p[0] for p in below) / len(below) - (bars[0][0][0] + bars[0][1][0]) / 2) > c["bar_balance_max"]: return "unbalanced"
        return None

    def valid(self, L): return self.why(L) is None

    def novelty(self, L):
        n = self.cfg["checks"]["novelty_points"]
        def cloud(strokes):
            pts = [p for s in strokes for p in resample(parse(s[1]), 1.0)]; st = max(1, len(pts) // n); return pts[::st]
        A = cloud(L["strokes"]); best = 1e9
        for r in self.letters:
            B = cloud([[s["role"], fmt(s["P"]), sid] for sid, s in r["S"].items()])
            d = (sum(min(math.dist(p, q) for q in B) for p in A) / len(A) + sum(min(math.dist(p, q) for q in A) for p in B) / len(B)) / 2
            best = min(best, d)
        return best

    def generate(self, count, seed=1):
        rng = random.Random(seed); out = []; tries = 0
        while len(out) < count and tries < count * self.cfg["attempts_per_letter"]:
            tries += 1; L = self.make(rng)
            if L is None or not self.valid(L): continue
            if sum(o["donor"] == L["donor"] for o in out) >= self.cfg["checks"]["max_per_donor"]: continue
            nv = self.novelty(L)
            if nv < self.cfg["checks"]["min_novelty"]: continue
            L["novelty"] = round(nv, 1); L["glyph"] = L["iast"] = "g%03d" % (len(out) + 1); out.append(L)
        return out, tries


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "bengali"; n = int(sys.argv[2]) if len(sys.argv) > 2 else 40; seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    sc = Script(name); L, tries = sc.generate(n, seed)
    json.dump({"script": name, "box": 100, "letters": L}, open(os.path.join(HERE, "generated_%s.json" % name), "w"), ensure_ascii=False, separators=(",", ":"))
    print(len(L), "letters from", tries, "tries;", len(sc.donors), "donor topologies of", len(sc.letters))
