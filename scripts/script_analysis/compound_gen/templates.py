"""Constructive stroke templates. Instead of drawing a random chain and throwing most of them away, a chain is assembled from a few
parametric pieces whose turns are multiples of 90 degrees (bends of ~90, cups of ~180, straight lines), so that with an axis-aligned start
every cup opens up/down/left/right and every line is axis-aligned BY CONSTRUCTION. Same output format as compound_gen.raw():
(polyline with .meta = (marks, units), kinds)."""
import math, random
import compound_gen as C

STEP = 1.5
def _arc(pts, state, kind, tr, ln, marks, units):
    n = max(3, int(ln / STEP)); marks.append(len(pts) - 1); units.append((kind, tr, ln))
    for _ in range(n):
        state[2] += tr / n
        state[0] += math.cos(math.radians(state[2])) * ln / n; state[1] += math.sin(math.radians(state[2])) * ln / n
        pts.append((state[0], state[1]))

def piece(rng, kind, sd):
    """(kind, turn, length) of one piece; sd = +-1 is the turning side."""
    if kind == "line": return ("line", 0.0, rng.uniform(12, 34))
    if kind == "bend": tr = rng.uniform(75, 105); r = rng.uniform(8, 18); return ("L" if sd > 0 else "R", sd * tr, r * math.radians(tr))
    if kind == "cup": tr = rng.uniform(168, 195); r = rng.uniform(6, 13); return ("L" if sd > 0 else "R", sd * tr, r * math.radians(tr))
    raise KeyError(kind)

GRAMMAR = {   # what may follow what (all turns stay multiples of ~90, rings and spirals are not generated)
    "start": (("bend", 5), ("cup", 4), ("three", 3), ("S", 2), ("line", 1)),
    "bend": (("cup", 4), ("line", 4), ("bend", 2), ("end", 4)),
    "cup": (("line", 3), ("bend", 2), ("end", 6)),
    "line": (("end", 1),),
    "line_": (("end", 1),),
    "S": (("line", 2), ("end", 5)), "three": (("line", 1), ("end", 6)),
}

def chain(rng, allow=("bend", "cup", "three", "S", "line"), force_three=None, max_units=4, first=None):
    marks = []; units = []; pts = [(0.0, 0.0)]; st = [0.0, 0.0, 0.0]; seq = []
    state = "start"; sd = rng.choice((-1, 1)); last_sign = None; n = 0; snap = None
    while True:
        opts = [(k, w) for k, w in GRAMMAR["line" if state == "line" else state] if k == "end" or k in allow]
        if state == "start" and force_three is True: opts = [("three", 1)]
        if state == "start" and force_three is False: opts = [(k, w) for k, w in opts if k != "three"]
        if state == "start" and first: opts = [(first, 1)]
        if n >= max_units: opts = [("end", 1)]
        k = rng.choices([o[0] for o in opts], [o[1] for o in opts])[0]
        if k == "end":
            if not units: continue
            break
        if k == "line":                                          # a line must be exactly axis-aligned: bend the previous arc to make it so
            if snap is None or state in ("three", "S"): continue
            target = round(st[2] / 90.0) * 90.0; delta = target - st[2]
            if abs(delta) > 25: continue
            sl, sstate, sm, su, kind_, tr_, ln_ = snap
            del pts[sl:]; del marks[sm:]; del units[su:]; st[:] = sstate
            tr2 = tr_ + delta; _arc(pts, st, kind_, tr2, ln_ * abs(tr2 / tr_), marks, units)
            _arc(pts, st, "line", 0.0, rng.uniform(9, 18), marks, units); seq.append("line"); state = "line"; n += 1; continue
        snap0 = (len(pts), list(st), len(marks), len(units))
        if k == "three":
            sd = rng.choice((-1, 1))
            for part in range(2):
                tr = sd * rng.uniform(165, 195); r = rng.uniform(5, 9)
                _arc(pts, st, "D", tr, r * math.radians(abs(tr)), marks, units)
                if part == 0: st[2] += -sd * rng.uniform(135, 165)
            seq.append("D"); snap = None
        elif k == "S":
            sd = rng.choice((-1, 1))
            for part in range(2):
                tr = (sd if part == 0 else -sd) * rng.uniform(150, 190); r = rng.uniform(5, 10)
                _arc(pts, st, "L" if tr > 0 else "R", tr, r * math.radians(abs(tr)), marks, units)
            seq.append("S"); snap = None
        else:
            sd = -last_sign if (last_sign and rng.random() < .35) else (last_sign or rng.choice((-1, 1))); last_sign = sd
            p = piece(rng, k, sd)
            if n == 0 and first == "bend": r = rng.uniform(9, 16); p = (p[0], p[1], r * math.radians(abs(p[1])))       # leaves the bar with room below it
            _arc(pts, st, p[0], p[1], p[2], marks, units); seq.append(p[0])
            snap = snap0 + (p[0], p[1], p[2])
        state = k; n += 1
    if snap is not None and state in ("bend", "cup"):                      # both ends of the stroke leave / arrive along an axis
        target = round(st[2] / 90.0) * 90.0; delta = target - st[2]
        if 0.5 < abs(delta) <= 25:
            sl, sstate, sm, su, kind_, tr_, ln_ = snap
            del pts[sl:]; del marks[sm:]; del units[su:]; st[:] = sstate
            _arc(pts, st, kind_, tr_ + delta, ln_ * abs((tr_ + delta) / tr_), marks, units)
    return pts, marks, units, seq

def rng_flip_false(P): return P[2][0] >= P[0][0] - 1e-9 or False

def raw_ct(rng, **kw):
    for _ in range(12):                                          # cheap local retry: a stroke must fit in a 44-unit box
        pts, marks, units, seq = chain(rng, **kw)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if max(max(xs) - min(xs), max(ys) - min(ys)) <= 44 and sum(u[2] for u in units) >= 22: break
    P = C.St((p[0], -p[1]) for p in pts)                  # y down like compound_gen.raw
    if rng.random() < .5: P = C.St((-x, y) for x, y in P)
    P.meta = (marks, units)
    P.sh = 180.0 if P[1][0] < P[0][0] else 0.0 if False else (0.0 if rng_flip_false(P) else 180.0)
    return P, [u[0] for u in units]
