"""Motif composer: build new letters by grafting small multi-stroke motifs (taken from real and owner-approved letters)
onto a base letter at a port, instead of assembling raw strokes. Every piece already has a good shape; only the join is new.
usage: python3 motif.py <script> N seed [procs] -> motif_<script>.json"""
import json, math, os, random, sys, copy
from engine import parse, fmt, point_at, param_of, seg_cross, resample, head
from grow import Grower
from panes import adjust_valid, frame as pane_frame
from curate import fix_bar_ends, fix_junctions
HERE = os.path.dirname(os.path.abspath(__file__))
PANES = pane_frame(os.environ.get('CF_SCRIPT', 'bengali'))
REAL = os.path.join(HERE, "..", "..", "..", "conlang_forge", "script", "forms", "%s_graph.json")
APPROVED = {"bengali": ["curated_bengali_round1.json", "curated_bengali_round2.json", "curated_bengali_round3.json", "curated_bengali_round4.json"]}

def xf(P, port, theta, k, to):
    c, s = math.cos(theta), math.sin(theta)
    return [(to[0] + k * ((x - port[0]) * c - (y - port[1]) * s), to[1] + k * ((x - port[0]) * s + (y - port[1]) * c)) for x, y in P]


def name_of(c): return c.cfg.get("id", "bengali")

def finish(L, sc):
    """owner post-processing: teardrops on curled free ends; junction coordinates repaired (pane layout is applied afterwards by panes.py)"""
    P = {s[2]: parse(s[1]) for s in L["strokes"]}; role = {s[2]: s[0] for s in L["strokes"]}
    used = {(m["stroke"], m["where"]) for j in L["junctions"] for m in j["members"]}
    for sid, Q in P.items():
        if role[sid] == "struct": continue
        R = resample(Q, 1.0)
        for w, seg in (("start", R[:17]), ("end", R[::-1][:17])):
            if (sid, w) in used or len(seg) < 12: continue
            a0 = head(seg[0], seg[6]); a1 = head(seg[10], seg[-1]); d = abs((a1 - a0 + 180) % 360 - 180)
            if d >= 45:
                e = L["ends"].setdefault(sid, ["plain", "plain"]); e[0 if w == "start" else 1] = "ball"
    L["junctions"] = [j for j in L["junctions"] if len({mm["stroke"] for mm in j["members"]}) >= 2]                  # no stray single-stroke dots
    P = {s[2]: parse(s[1]) for s in L["strokes"]}
    for j in L["junctions"]:                                                  # a motif's inner junctions keep the motif's old coordinates: put every junction where its members really meet
        pts = [P[mm["stroke"]][0] if mm["where"] == "start" else P[mm["stroke"]][-1] if mm["where"] == "end" else point_at(P[mm["stroke"]], mm["at"]) for mm in j["members"]]
        j["x"] = sum(p[0] for p in pts) / len(pts); j["y"] = sum(p[1] for p in pts) / len(pts)
    return L

def n_similar(L):
    """pairs of non-bar strokes with nearly the same shape (translation, mirror allowed): repetition makes a letter look busy"""
    Q = [resample(parse(s[1]), 2.0) for s in L["strokes"] if s[0] != "struct" and len(parse(s[1])) > 2]; n = 0
    def sig(P): cx = sum(x for x, _ in P) / len(P); cy = sum(y for _, y in P) / len(P); return [(x - cx, y - cy) for x, y in P]
    for i in range(len(Q)):
        for k in range(i + 1, len(Q)):
            A, B = sig(Q[i]), sig(Q[k])
            if abs(len(A) - len(B)) > 3: continue
            m = min(len(A), len(B))
            for BB in (B, [(-x, y) for x, y in B], B[::-1], [(-x, y) for x, y in B[::-1]]):
                if sum(math.dist(A[t], BB[t]) for t in range(m)) / m < 3.0: n += 1; break
    return n

class Composer(Grower):
    def __init__(self, name):
        super().__init__(name); self.lib = []
        for l in json.load(open(REAL % name))["letters"]: self.lib.append(dict(l, _src="real"))
        for f in APPROVED.get(name, []):
            p = os.path.join(HERE, f)
            if os.path.exists(p):
                for l in json.load(open(p))["letters"]:
                    if "before" not in l["iast"]: self.lib.append(dict(l, _src="approved:" + f, iast=("r4_" + l["iast"]) if "round4" in f else l["iast"]))
        self.lib = [self.repair(l) for l in self.lib]
        self.appr = [l for l in self.lib if l["_src"] != "real"]; self.bases = [l for l in self.lib if not self.why(l)]; self.cl = dict(self.cfg.get("compose", {}), **json.loads(os.environ.get("CF_COMPOSE", "{}")))
        self.lib_clouds = [self._cloud(l["strokes"]) for l in self.lib]

    def repair(self, L):
        """hand-fitted junctions can miss by a few units: pull each loose end onto its junction point, tapering the move along the stroke"""
        L = copy.deepcopy(L); P = {s[2]: parse(s[1]) for s in L["strokes"]}
        for j in L["junctions"]:
            mids = [m for m in j["members"] if m["where"] == "middle"]
            tgt = point_at(P[mids[0]["stroke"]], mids[0]["at"]) if mids else (j["x"], j["y"])
            for m in j["members"]:
                if m["where"] == "middle": continue
                Q = P[m["stroke"]]; e = Q[0] if m["where"] == "start" else Q[-1]; dx, dy = tgt[0] - e[0], tgt[1] - e[1]; n = len(Q) - 1
                P[m["stroke"]] = [(x + dx * (1 - (i if m["where"] == "start" else n - i) / n), y + dy * (1 - (i if m["where"] == "start" else n - i) / n)) for i, (x, y) in enumerate(Q)]
        L["strokes"] = [[r, fmt(P[i]), i] for r, _, i in L["strokes"]]; return L

    # ---- motifs: one body-ish stroke, optionally with the stroke it is joined to
    def motifs(self, L):
        S = {s[2]: s for s in L["strokes"]}; out = []
        for sid, s in S.items():
            if s[0] == "struct": continue
            out.append([sid])
            for j in L["junctions"]:
                ids = [m["stroke"] for m in j["members"]]
                if sid in ids:
                    for o in ids:
                        if o != sid and S[o][0] != "struct" and sorted([sid, o]) not in [sorted(m) for m in out]: out.append([sid, o])
        return out

    def pull(self, L, ids):
        """copy the motif out of its letter: strokes, internal junctions, ends"""
        S = {s[2]: (s[0], parse(s[1])) for s in L["strokes"] if s[2] in ids}
        J = [j for j in L["junctions"] if all(m["stroke"] in ids for m in j["members"])]
        ends = {i: L["ends"].get(i, ["plain", "plain"]) for i in ids}
        busy = {(m["stroke"], m["where"]) for j in J for m in j["members"] if m["where"] != "middle"}
        ports = [(i, w) for i in ids for w in ("start", "end") if (i, w) not in busy]
        return S, J, ends, ports

    def _hits(self, T, base, site, near=6.0):
        """does a grafted stroke cross a base stroke away from the join? (the join itself may touch)"""
        for Q in T.values():
            q = Q[::2] + [Q[-1]]
            for B in base.values():
                b = B[::2] + [B[-1]]
                for i in range(len(q) - 1):
                    for k in range(len(b) - 1):
                        if seg_cross(q[i], q[i + 1], b[k], b[k + 1]) and math.dist(q[i], site) > near and math.dist(q[i + 1], site) > near: return True
        return False

    def compose(self, rng):
        cl = self.cl; base = rng.choice(self.appr if rng.random() < cl.get("approved_base", 0.5) else self.bases)
        src = rng.choice(self.lib)
        if src is base: return None
        base = copy.deepcopy(base); strokes = {s[2]: [s[0], parse(s[1])] for s in base["strokes"]}; J = copy.deepcopy(base["junctions"]); ends = dict(base["ends"])
        if rng.random() < cl.get("swap_prob", 0.4):                              # swap: drop one non-structural stroke, graft another in
            cand = [i for i, v in strokes.items() if v[0] != "struct" and v[0] != "accent"]
            if not cand: return None
            d = rng.choice(cand); strokes.pop(d); ends.pop(d, None); J = [dict(j, members=[m for m in j["members"] if m["stroke"] != d]) for j in J]; J = [j for j in J if len(j["members"]) > 1]
        if not strokes or len(strokes) >= self.g["max_strokes"]: return None
        ms = self.motifs(src)
        if not ms: return None
        ids = rng.choice(ms); S, mJ, mE, ports = self.pull(src, ids)
        if not ports: return None
        pid, pw = rng.choice(ports); port = S[pid][1][0 if pw == "start" else -1]
        # site on the base: an end of a stroke or a point along it
        sites = []
        for i, (r, P) in strokes.items():
            sites += ([] if r == "struct" else [(i, "start", P[0], 0.0), (i, "end", P[-1], 1.0)]) + [(i, "middle", point_at(P, f), f) for f in (0.2, 0.35, 0.5, 0.65, 0.8)]
        fr = self.cfg["frame"]; flip = rng.random() < cl.get("flip_prob", 0.0); placed = None
        for _ in range(24):                                                       # re-draw the join until the motif lies inside the frame
            sid_, sw, site, a = rng.choice(sites)
            th = math.radians(rng.uniform(-cl.get("rot", 30), cl.get("rot", 30))); k = rng.uniform(*cl.get("scale", [0.8, 1.25]))
            T = {i: xf([(-x, y) for x, y in P] if flip else P, (-port[0], port[1]) if flip else port, th, k, site) for i, (r, P) in S.items()}
            if not all(fr["margin_lo"] <= x <= fr["margin_hi"] and fr["margin_lo"] <= y <= fr["max_y"] for Q in T.values() for x, y in Q): continue
            if self._hits(T, {i: v[1] for i, v in strokes.items()}, site): continue
            placed = T; break
        if placed is None: return None
        n = max(int(i[1:]) for i in strokes) if strokes else 0; ren = {}
        for i in ids: n += 1; ren[i] = "s%d" % n
        for i, (r, P) in S.items():
            strokes[ren[i]] = [r, placed[i]]; ends[ren[i]] = mE[i]
        for j in mJ: J.append(dict(j, members=[dict(m, stroke=ren[m["stroke"]]) for m in j["members"]]))
        t = "red" if sw == "middle" or rng.random() < 0.5 else "touch"
        J.append({"t": t, "x": site[0], "y": site[1], "loose": False, "members": [{"stroke": sid_, "at": a, "where": sw}, {"stroke": ren[pid], "at": 0.0 if pw == "start" else 1.0, "where": pw}]})
        L = {"glyph": "", "iast": "", "variant": None, "strokes": [[r, fmt(P), i] for i, (r, P) in strokes.items()], "junctions": J, "ends": {i: e for i, e in ends.items() if e != ["plain", "plain"]}}
        if fix_bar_ends(L): fix_junctions(L)                                       # nothing hangs from the very end of the bar
        return L, (base.get("iast"), src.get("iast"))

    def generate_m(self, count, seed=1, tries_max=None):
        rng = random.Random(seed); out = []; clouds = []; rej = {}; tries = 0; tries_max = tries_max or count * 300
        while len(out) < count and tries < tries_max:
            tries += 1; r = self.compose(rng)
            if r is None: rej["compose"] = rej.get("compose", 0) + 1; continue
            L, parent = r; why = self.why(L)
            if why: rej[why] = rej.get(why, 0) + 1; continue
            if len(L["strokes"]) >= 5 and n_similar(L) >= 2: rej["repetitive"] = rej.get("repetitive", 0) + 1; continue
            if len(L["strokes"]) >= 6 and sum(len(x["strokes"]) >= 6 for x in out) >= max(1, 0.15 * count): rej["too many busy"] = rej.get("too many busy", 0) + 1; continue
            st = self.stems(L)
            if len(st) > self.g["max_stems"] or any(abs(a - b) < self.g["min_stem_gap"] for i, a in enumerate(st) for b in st[i + 1:]): rej["parallel stems"] = rej.get("parallel stems", 0) + 1; continue
            A = self._cloud(L["strokes"]); dr = min(self.distance(A, B) for B in self.lib_clouds)
            if dr < self.g["min_real_distance"]: rej["near library"] = rej.get("near library", 0) + 1; continue
            if clouds and min(self.distance(A, B) for B in clouds) < self.g["min_generated_distance"]: rej["near generated"] = rej.get("near generated", 0) + 1; continue
            clouds.append(A); L = finish(L, self)
            if os.environ.get("CF_PANES"):                                           # window-pane layout prior (panes.py): small, validated nudges
                import panes
                if not hasattr(self, "_F"): self._F = panes.frame_of(name_of(self))
                L, done = panes.adjust(L, self._F, ok=lambda X: self.why(X) is None)
                if done: L["panes_done"] = done
            L["novelty"] = round(dr, 1); L["parents"] = list(parent); L["glyph"] = L["iast"] = "m%03d" % (len(out) + 1); out.append(L)
        self.rejected = rej; return out, tries

def _w(a):
    name, n, seed = a; c = Composer(name); L, t = c.generate_m(n, seed); return L, t, c.rejected

if __name__ == "__main__":
    name = sys.argv[1]; n = int(sys.argv[2]); seed = int(sys.argv[3]); procs = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    if procs > 1:
        from multiprocessing import Pool
        with Pool(procs) as P: parts = P.map(_w, [(name, -(-n // procs), seed + 1000 * i) for i in range(procs)])
        c = Composer(name); L = []; tries = sum(p[1] for p in parts); rej = {}; clouds = []
        for pl, _, rj in parts:
            for k, v in rj.items(): rej[k] = rej.get(k, 0) + v
        for pl, _, _ in parts:
            for l in pl:
                A = c._cloud(l["strokes"])
                if clouds and min(c.distance(A, B) for B in clouds) < c.g["min_generated_distance"]: rej["twin across seeds"] = rej.get("twin across seeds", 0) + 1; continue
                clouds.append(A); l["glyph"] = l["iast"] = "m%03d" % (len(L) + 1); L.append(l)
    else: c = Composer(name); L, tries = c.generate_m(n, seed); rej = c.rejected
    json.dump({"script": name, "box": 100, "letters": L}, open(os.path.join(HERE, "motif_%s%s.json" % (name, os.environ.get("CF_TAG", ""))), "w"), ensure_ascii=False, separators=(",", ":"))
    print(len(L), "letters from", tries, "tries; library", len(c.lib), "(approved", len(c.appr), "); rejected:", rej)
