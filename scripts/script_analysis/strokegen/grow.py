"""Compositional letter generator (script-neutral): builds NEW letter structures from parts instead of re-drawing a real letter.

Parts are mined from the script's real letters (models/<script>.json names the graph):
  skeleton parts  - bar spans, vertical stems (position along the bar, top, bottom), how many stems a letter has
  stroke parts    - every real body stroke seen from the end where it is attached: WHAT it attaches to (bar / top, middle or bottom of a stem /
                    free end of another stroke / middle of another stroke / nothing), at what heading relative to that site, its turning
                    profile, its ball ends, and what its far end does (free, or lands on another kind of site).
A letter is grown: sample a skeleton, then add strokes one at a time at sites that exist in the figure so far.  The structure (the multiset of
attachment kinds) of a grown letter must differ from every real letter and from every letter already grown, and its shape must be far from
every real letter after the best affine deformation, so neither a re-skinned real letter nor a twin of another new letter gets through.

usage: python3 grow.py <script> [count] [seed]   ->  generated_<script>.json"""
import json, math, os, random, sys
import numpy as np
from engine import *      # geometry, Script (checks, shape helpers)


def out_heading(P, where):
    """heading in which a stroke leaves the point at `where` (start / end), pointing away from the stroke"""
    return head(P[1], P[0]) if where == "start" else head(P[-2], P[-1])


class Grower(Script):
    def __init__(self, name):
        super().__init__(name)
        self.g = self.cfg["grow"]; self._mine()
        for i, p in enumerate(self.parts):
            p["idx"] = i; p["h"] = profile(p["P"], self.step)
            # a long straight upright stroke is a stem: stems come from the skeleton, so it is not drawn again as a body stroke
            p["stem"] = p["len"] >= 35 and turning(p["P"])[0] < self.cfg["shape"]["straight_turn"] and abs(abs(head(p["P"][0], p["P"][-1])) - 90) < 15

    # ------------------------------------------------------------ mining
    def _kind_of(self, l, j, me, at_hint=None):
        """what the junction `j` attaches stroke `me` to: (kind, at, partner stroke id, partner where, junction type)"""
        S = l["S"]
        for m in j["members"]:
            if m["stroke"] == me: continue
            k = S[m["stroke"]]["kind"]
            if k == "bar": return ("bar", m["at"], m["stroke"], m["where"], j["t"])
            if k == "vertical": return ("vtop" if m["at"] < .12 else "vbot" if m["at"] > .88 else "vmid", m["at"], m["stroke"], m["where"], j["t"])
            return ("send" if m["where"] in ("start", "end") else "smid", m["at"], m["stroke"], m["where"], j["t"])
        return None

    def _ctx(self, l, sid, where):
        for j in l["junctions"]:
            if any(m["stroke"] == sid and m["where"] == where for m in j["members"]):
                c = self._kind_of(l, j, sid)
                if c: return c
        return ("free", 0.0, None, None, None)

    def _mine(self):
        sh = self.cfg["shape"]; self.parts = []; self.sigs = set(); self.bars = []; self.verts = {True: [], False: []}; self.nvert = {True: [], False: []}
        self.nbody = []; self.has_bar = []
        for l in self.letters:
            S = l["S"]; bar = next((s for s in S.values() if s["kind"] == "bar"), None); hb = bar is not None
            vs = [s for s in S.values() if s["kind"] == "vertical" and abs(s["P"][0][1] - s["P"][1][1]) >= 12]
            self.has_bar.append(hb); self.nvert[hb].append(len(vs))
            if bar: self.bars.append(sorted((bar["P"][0][0], bar["P"][1][0])))
            for v in vs:
                x = v["P"][0][0]; y0, y1 = sorted((v["P"][0][1], v["P"][1][1]))
                f = (x - self.bars[-1][0]) / (self.bars[-1][1] - self.bars[-1][0]) if bar else None
                self.verts[hb].append({"f": f, "x": x, "y0": y0, "y1": y1, "top_on_bar": bool(bar and abs(y0 - bar["P"][0][1]) < 1.0), "role": v["role"]})
            body = [s for s in S.values() if s["kind"] in ("body", "other") and length(s["P"]) >= sh["min_len"]]
            self.nbody.append(len(body)); sig = []
            for s in body:
                a = self._ctx(l, s["id"], "start"); b = self._ctx(l, s["id"], "end")
                end = "start" if a[0] != "free" or b[0] == "free" else "end"
                anc, far = (a, b) if end == "start" else (b, a)
                P = s["P"] if end == "start" else s["P"][::-1]; e = s["ends"] if end == "start" else s["ends"][::-1]
                if anc[0] in ("bar", "vtop", "vmid", "vbot", "free"): base = 0.0
                else:
                    Q = S[anc[2]]["P"]; base = out_heading(Q, anc[3]) if anc[3] in ("start", "end") else head(*[point_at(Q, max(0, anc[1] - .03)), point_at(Q, min(1, anc[1] + .03))])
                rel = dh(base, head(P[0], P[1]))
                self.parts.append({"iast": l["iast"], "role": s["role"], "P": P, "ends": e, "anc": anc[0], "at": anc[1], "t": anc[4], "rel": rel, "far": far[0], "far_t": far[4], "len": length(P)})
                sig.append((anc[0], far[0]))
            self.sigs.add(self._sig(hb, len(vs), sig))
        self.real_clouds = [self._cloud([[s["role"], fmt(s["P"]), k] for k, s in l["S"].items()]) for l in self.letters]

    @staticmethod
    def _sig(has_bar, nv, sig): return (has_bar, nv, tuple(sorted(sig)))

    def _cloud(self, strokes, n=150):
        pts = [p for s in strokes for p in resample(parse(s[1]), 1.0)]; k = max(1, len(pts) // n); return np.array(pts[::k])

    # ------------------------------------------------------------ growing
    def grow(self, rng):
        g = self.g; fr = self.cfg["frame"]; by = fr["bar_y"]; sk = self.cfg["skeleton"]
        hb = rng.random() < sum(self.has_bar) / len(self.has_bar)
        self._used = []
        figure = []          # strokes: dict(id, role, P, ends, kind)
        J = []; sig = []
        def add(role, P, ends, kind):
            sid = "s%d" % (len(figure) + 1); figure.append({"id": sid, "role": role, "P": P, "ends": ends, "kind": kind}); return sid
        bar = None
        if hb:
            x0, x1 = rng.choice(self.bars); j = sk["bar_jitter_x"]; x0 += rng.uniform(-j, j); x1 += rng.uniform(-j, j)
            if x1 - x0 < sk["bar_min_width"]: x1 = x0 + sk["bar_min_width"]
            bar = add("struct", [(x0, by), (x1, by)], ["plain", "plain"], "bar")
        verts = []
        for _ in range(rng.choice(self.nvert[hb])):
            t = rng.choice(self.verts[hb]); jy = sk["vertical_y_jitter"]
            x = (x0 + (t["f"] + rng.uniform(-sk["vertical_x_frac_jitter"], sk["vertical_x_frac_jitter"])) * (x1 - x0)) if hb else t["x"] + rng.uniform(-sk["vertical_x_jitter_no_bar"], sk["vertical_x_jitter_no_bar"])
            y0 = by if t["top_on_bar"] and hb else t["y0"] + rng.uniform(-jy, jy); y1 = min(sk["vertical_bottom_max"], t["y1"] + rng.uniform(-jy, jy))
            if y1 - y0 < 25: continue
            if any(abs(x - figure[i]["P"][0][0]) < 14 for i in verts): continue
            v = add(t["role"], [(x, y0), (x, y1)], ["plain", "plain"], "vertical"); verts.append(len(figure) - 1)
            if t["top_on_bar"] and hb: J.append({"t": "red", "members": [{"stroke": bar, "at": (x - x0) / (x1 - x0), "where": "middle"}, {"stroke": v, "at": 0.0, "where": "start"}]})
        nb = rng.choice(self.nbody)
        if nb == 0 and not verts: return None
        n_target = min(len(figure) + nb, g["max_strokes"])
        guard = 0
        while len(figure) < n_target and guard < 40:
            guard += 1
            r = self._place(rng, figure, J)
            if r is None: continue
            sig.append(r)
        if len(figure) < n_target: return None
        L = self._to_letter(figure, J)
        return L, self._sig(hb, len(verts), sig)

    def stems(self, L):
        """x of every long straight upright stroke"""
        out = []
        for r, d, sid in L["strokes"]:
            P = parse(d)
            if r != "struct" and length(P) >= 40 and turning(P)[0] < self.cfg["shape"]["straight_turn"] and abs(abs(head(P[0], P[-1])) - 90) < 6: out.append(P[0][0])
        return out

    def _sites(self, figure, used):
        """what can be attached to right now"""
        S = {"bar": [], "vtop": [], "vmid": [], "vbot": [], "send": [], "smid": []}
        for i, s in enumerate(figure):
            if s["kind"] == "bar": S["bar"].append(i)
            elif s["kind"] == "vertical": S["vtop"].append(i); S["vmid"].append(i); S["vbot"].append(i)
            else:
                for w in ("start", "end"):
                    if (i, w) not in used: S["send"].append((i, w))
                S["smid"].append(i)
        return S

    def _point(self, rng, figure, kind, at, site):
        """(point, base heading, member dict) of an attachment site"""
        if kind == "bar":
            s = figure[site]; f = min(.98, max(.02, at + rng.uniform(-.12, .12))); P = s["P"]; return (P[0][0] + (P[1][0] - P[0][0]) * f, P[0][1]), 0.0, {"stroke": s["id"], "at": f, "where": "middle"}
        if kind in ("vtop", "vbot", "vmid"):
            s = figure[site]; P = s["P"]; f = 0.0 if kind == "vtop" else 1.0 if kind == "vbot" else min(.9, max(.1, at + rng.uniform(-.1, .1)))
            return (P[0][0], P[0][1] + (P[1][1] - P[0][1]) * f), 0.0, {"stroke": s["id"], "at": f, "where": "start" if kind == "vtop" else "end" if kind == "vbot" else "middle"}
        if kind == "send":
            i, w = site; s = figure[i]; P = s["P"]; return (P[0] if w == "start" else P[-1]), out_heading(P, w), {"stroke": s["id"], "at": 0.0 if w == "start" else 1.0, "where": w}
        s = figure[site]; P = s["P"]; f = min(.85, max(.15, at + rng.uniform(-.1, .1))); a, b = point_at(P, max(0, f - .03)), point_at(P, min(1, f + .03))
        return point_at(P, f), head(a, b), {"stroke": s["id"], "at": f, "where": "middle"}

    def _place(self, rng, figure, J):
        g = self.g; sh = self.cfg["shape"]
        used = {(m["stroke"], m["where"]) for j in J for m in j["members"]}
        ids = {s["id"]: i for i, s in enumerate(figure)}
        used = {(ids[a], w) for a, w in used}
        S = self._sites(figure, used)
        cand = [p for p in self.parts if p["anc"] == "free" or S.get(p["anc"])]
        if not cand: return None
        joined = {m["stroke"] for j in J for m in j["members"]}                 # skeleton still waiting for a stroke: usually serve it first
        want = [i for i, s in enumerate(figure) if s["kind"] in ("bar", "vertical") and s["id"] not in joined]
        if want and rng.random() < self.g["serve_loose_prob"]:
            kinds = {"bar" if figure[i]["kind"] == "bar" else k for i in want for k in (("bar",) if figure[i]["kind"] == "bar" else ("vtop", "vmid", "vbot"))}
            pref = [p for p in cand if p["anc"] in kinds]; cand = pref or cand
        U = rng.choice(cand)
        if U["anc"] == "free":                                           # floating bit: keep it where the real one sat, shifted
            d = (rng.uniform(-4, 4), rng.uniform(-4, 4)); P = [(x + d[0], y + d[1]) for x, y in U["P"]]
            return None if not self._stroke_ok(P, {s["id"]: s for s in figure}) else (add_stroke(figure, U["role"], P, list(U["ends"])), ("free", "free"))[1]
        sites = S[U["anc"]]; sites = [x for x in sites if (x if isinstance(x, int) else x[0]) in want] or sites if U["anc"] in ("bar", "vtop", "vmid", "vbot") else sites
        site = rng.choice(sites); A, base, mem_a = self._point(rng, figure, U["anc"], U["at"], site)
        out = base + U["rel"] + rng.uniform(-1, 1) * sh["start_heading_jitter"]
        W = [s["P"] for s in figure]
        accent = U["role"] == "accent"
        for _ in range(12):
            h = list(U["h"]); ends = list(U["ends"])
            if rng.random() < sh["splice_prob"] and not accent and len(h) > 12:
                B = rng.choice([p for p in self.parts if p["anc"] == U["anc"]] or [U]); hB = B["h"]
                if len(hB) > 12:
                    ka = int(len(h) * rng.uniform(*sh["splice_cut"])); kb = int(len(hB) * rng.uniform(*sh["splice_cut"]))
                    h = h[:ka] + [x + (h[ka - 1] - hB[kb]) for x in hB[kb:]]; ends = [ends[0], B["ends"][1]]
            h = self._tidy(h, U["role"])
            C = build(h, self.step, rng.uniform(*sh["length_scale"]))
            C = rotate(C, out - head(C[0], C[1]), C[0])
            if turning(C)[0] < sh["straight_turn"] and abs(abs(head(C[0], C[-1])) - 90) <= sh["snap_vertical"]:       # a long straight stroke that is nearly upright is exactly upright
                C = rotate(C, (90 if head(C[0], C[-1]) > 0 else -90) - head(C[0], C[-1]), C[0]); C = [(x - C[0][0] + A[0], y - C[0][1] + A[1]) for x, y in C]
            far_kind = "free"; mem_f = None; far_t = None
            if U["far"] != "free" and not accent and S.get(U["far"]):
                for _t in range(6):
                    fs = rng.choice(S[U["far"]])
                    if fs == site: continue
                    T, _b, mf = self._point(rng, figure, U["far"], rng.random(), fs)
                    if math.dist(T, A) < sh["min_chord"]: continue
                    Q, k = similarity(C, A, T)
                    if Q is None or not (sh["fit_scale"][0] <= k <= sh["fit_scale"][1]): continue
                    if abs(dh(head(Q[0], Q[1]), out)) > sh["fit_heading_tol"]: continue
                    C = Q; far_kind = U["far"]; mem_f = mf; far_t = U["far_t"]; break
            if self._stem_like(C) and any(self._stem_like(s["P"]) and abs(s["P"][0][0] - C[0][0]) < self.g["min_stem_gap"] for s in figure): continue      # no second stem right beside a stem
            if not (sh["min_len"] <= length(C) <= sh["max_len"]) or not self._stroke_ok(C, {s["id"]: s for s in figure}): continue
            sid = add_stroke(figure, U["role"], C, ends)
            J.append({"t": U["t"] or "touch", "members": [{"stroke": sid, "at": 0.0, "where": "start"}, mem_a]})
            if mem_f: J.append({"t": far_t or "touch", "members": [{"stroke": sid, "at": 1.0, "where": "end"}, mem_f]})
            self._used.append(U["idx"]); return (U["anc"], far_kind)
        return None

    def _stem_like(self, P):
        return length(P) >= 40 and turning(P)[0] < self.cfg["shape"]["straight_turn"] and abs(abs(head(P[0], P[-1])) - 90) < 6

    def _tidy(self, h, role):
        """smooth out jitter in the turning profile (moving average of the turns) and give the role its curvature gain"""
        sh = self.cfg["shape"]; w = sh["smooth_window"]; d = [dh(a, b) for a, b in zip(h, h[1:])]
        if w > 1 and len(d) > w:
            d = [sum(d[max(0, i - w // 2): i + w // 2 + 1]) / len(d[max(0, i - w // 2): i + w // 2 + 1]) for i in range(len(d))]
        gain = sh["curve_gain"].get(role, 1.0); out = [h[0]]
        for x in d: out.append(out[-1] + gain * x)
        return out

    def _to_letter(self, figure, J):
        strokes = [[s["role"], fmt(s["P"]), s["id"]] for s in figure]; ends = {s["id"]: s["ends"] for s in figure if s["ends"] != ["plain", "plain"]}
        P = {s["id"]: s["P"] for s in figure}; JJ = []
        for j in J:
            pts = []
            for m in j["members"]:
                Q = P[m["stroke"]]; pts.append(Q[0] if m["where"] == "start" else Q[-1] if m["where"] == "end" else point_at(Q, m["at"]))
            JJ.append({"t": j["t"], "x": round(sum(p[0] for p in pts) / len(pts), 1), "y": round(sum(p[1] for p in pts) / len(pts), 1),
                       "members": [dict(m, at=round(m["at"], 2)) for m in j["members"]], "loose": False})
        return {"glyph": "", "iast": "", "variant": None, "strokes": strokes, "junctions": JJ, "ends": ends}

    # ------------------------------------------------------------ distinctness
    def _aff(self, A, B, it=10):
        A = A.copy()
        for _ in range(it):
            D = np.linalg.norm(A[:, None] - B[None], axis=2); T = B[D.argmin(1)]
            X = np.c_[A, np.ones(len(A))]; M = np.linalg.lstsq(X, T, rcond=None)[0]; A = X @ M
        D = np.linalg.norm(A[:, None] - B[None], axis=2); return (D.min(1).mean() + D.min(0).mean()) / 2

    def distance(self, A, B): return (self._aff(A, B) + self._aff(B, A)) / 2

    def generate(self, count, seed=1):
        rng = random.Random(seed); use = {}; out = []; sigs = []; clouds = []; tries = 0; c = self.cfg["checks"]; rej = {}
        while len(out) < count and tries < count * self.g["attempts_per_letter"]:
            tries += 1; r = self.grow(rng)
            if r is None: rej["grow"] = rej.get("grow", 0) + 1; continue
            L, sig = r; why = self.why(L)
            if not why and not sig[0] and sum(not s[0] for s in sigs) >= self.g["max_barless_share"] * count: why = "too many bar-less"
            if why: rej[why] = rej.get(why, 0) + 1; continue
            st = self.stems(L)
            if len(st) > self.g["max_stems"] or any(abs(a - b) < self.g["min_stem_gap"] for i, a in enumerate(st) for b in st[i + 1:]): rej["parallel stems"] = rej.get("parallel stems", 0) + 1; continue
            if any(use.get(i, 0) >= self.g["max_part_use"] for i in self._used): rej["part used up"] = rej.get("part used up", 0) + 1; continue
            if self.g["novel_structure"] and (sig in self.sigs or (self.g.get("unique_among_generated", False) and sig in sigs)): rej["same structure"] = rej.get("same structure", 0) + 1; continue
            A = self._cloud(L["strokes"])
            dr = min(self.distance(A, B) for B in self.real_clouds)
            if dr < self.g["min_real_distance"]: rej["near real"] = rej.get("near real", 0) + 1; continue
            if clouds and min(self.distance(A, B) for B in clouds) < self.g["min_generated_distance"]: rej["near generated"] = rej.get("near generated", 0) + 1; continue
            for i in self._used: use[i] = use.get(i, 0) + 1
            sigs.append(sig); clouds.append(A); L["novelty"] = round(dr, 1); L["glyph"] = L["iast"] = "g%03d" % (len(out) + 1); L["donor"] = ""; out.append(L)
        self.rejected = rej
        return out, tries


def add_stroke(figure, role, P, ends):
    sid = "s%d" % (len(figure) + 1); figure.append({"id": sid, "role": role, "P": P, "ends": ends, "kind": "body"}); return sid


def _worker(a):
    name, n, seed = a; gr = Grower(name); L, tries = gr.generate(n, seed); return L, tries, gr.rejected


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "bengali"; n = int(sys.argv[2]) if len(sys.argv) > 2 else 40; seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    procs = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    if procs > 1:                                                        # independent seeds in parallel, then drop twins across them
        from multiprocessing import Pool
        with Pool(procs) as P: parts = P.map(_worker, [(name, -(-n // procs), seed + 1000 * i) for i in range(procs)])
        gr = Grower(name); L = []; tries = sum(p[1] for p in parts); gr.rejected = {}
        for pl, _, rj in parts:
            for k, v in rj.items(): gr.rejected[k] = gr.rejected.get(k, 0) + v
        clouds = []
        for pl, _, _ in parts:
            for l in pl:
                A = gr._cloud(l["strokes"])
                if clouds and min(gr.distance(A, B) for B in clouds) < gr.g["min_generated_distance"]: gr.rejected["twin across seeds"] = gr.rejected.get("twin across seeds", 0) + 1; continue
                clouds.append(A); l["glyph"] = l["iast"] = "g%03d" % (len(L) + 1); L.append(l)
    else: gr = Grower(name); L, tries = gr.generate(n, seed)
    json.dump({"script": name, "box": 100, "letters": L}, open(os.path.join(HERE, "grown_%s.json" % name), "w"), ensure_ascii=False, separators=(",", ":"))
    print(len(L), "letters from", tries, "tries; real structures:", len(gr.sigs), "; rejected:", gr.rejected)
