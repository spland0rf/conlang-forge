"""Repair step: a letter that fails the whitespace test is not thrown away.  The whole body group is scaled about its bar anchor (curves get
bigger and more dramatic, topology unchanged) and the anchor may slide along the bar (strokes spread into the empty regions).  Smallest change
that makes the letter valid and fills enough of the frame wins.  Topology is preserved by construction (same strokes, same junction list);
crossings and bar/stem clearance are re-checked by valid()."""
import copy, math, itertools
import os, sys
import compound_gen as C
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sig as SG    # same stroke kinds and the same contacts before and after
from rules import RULES as R
SCALES = [1.0, 1.15, 1.3, 1.45, 1.6, 1.8, 2.0, 2.25, 2.5]
SHIFTS = [0, -5, 5, -10, 10, -15, 15, -20, 20, -30, 30, -40, 40]
def transform(L, f, g, dx, pivot="anchor", fr=None):
    N = copy.deepcopy(L); a = next(j for j in L["J"] if j[0] == "red"); ax, ay = a[1], a[2]
    px = L["sk"]["S"] if pivot == "stem" else ax      # pivot on the stem keeps every stem contact on the stem
    jy = next((j[2] for j in L["J"] if j[0] != "red" and abs(j[1] - px) < 3), None) if fr is not None else None
    def T(p):
        if fr is not None and p[0] > px + 0.8 and jy is not None:
            return (p[0], p[1] + (g - 1.0) * (jy - ay))      # stem pivot: stretch only the part left of the stem; the part right of it keeps its shape and rides down with the crossing
        return (px + dx + f * (p[0] - px), ay + g * (p[1] - ay))
    if N["sk"]["kind"] == "desc": N["sk"]["x"] = L["sk"]["x"] + dx      # the descender moves with the body so the join stays closed
    N["strokes"] = [[T(p) for p in P] for P in L["strokes"]]
    N["J"] = [[j[0]] + list(T((j[1], j[2]))) + list(j[3:]) for j in L["J"]]
    return N
def repair(L):
    """returns (new letter, (f, g, dx)) or (None, None)"""
    best = None; s0 = SG.sig(SG.letter_strokes(L))
    for f in SCALES:
        for g in (f, f * 0.9, f * 1.1, f * 1.3, f * 1.5, 1.0, 1.15):
            if g > 2.5 or g < 1.0 or not (0.6 <= f / g <= 2.2): continue
            for dx, pv in [(d, "anchor") for d in SHIFTS] + ([(0, "stem"), (0, "stemL")] if L["sk"]["kind"] == "stem" else []):
                N = transform(L, f, g, dx, "stem" if pv.startswith("stem") else pv, 1.0 if pv == "stemL" else None)
                try:
                    if not C.valid(N): continue
                except Exception: continue
                if SG.sig(SG.letter_strokes(N)) != s0: continue
                w = C.white_fraction(N)
                if w > R["WHITE_MAX"]: continue
                cost = 10 * max(0.0, w - R["WHITE_TARGET"]) + 0.5 * abs(math.log(f)) + abs(math.log(g / f)) * 2 + abs(dx) / 150 + 5 * max(0.0, 0.5 - C.primary_size(N)) + 0.05 * max(0.0, C.max_void(N) - 30.0) + 0.15 * max(0, C.crowding(N) - C.crowding(L)) + 0.6 * C.aspect_dev(N)   # relative only: a variant that stacks more strokes than the original is penalised, none is capped   # prefer a clearly fuller letter, not one that just squeaks under the limit
                if best is None or cost < best[0]: best = (cost, N, (round(f, 2), round(g, 2), dx, pv))
    return (best[1], best[2]) if best else (None, None)
if __name__ == "__main__":
    import json, os, sys
    L = json.load(open(sys.argv[1]))["letters"]; ok = 0
    for i, l in enumerate(L, 1):
        if l["bucket"] == "half": continue
        w = C.white_fraction(l)
        if w <= R["WHITE_MAX"] and C.valid(l): continue
        N, p = repair(l); print("A%d white %.2f -> %s" % (i, w, ("%s white %.2f" % (p, C.white_fraction(N))) if N else "no repair")); ok += bool(N)
    print("repaired", ok)


FAST_SCALES = [1.25, 1.5, 1.8, 2.2, 2.5]
FAST_GS = [1.0, 1.25, 1.5]
def repair_fast(L, s0=None):
    """Bounded repair for the sampler: at most ~40 candidate transforms, cheap size checks first (no geometry validation until a candidate
    already fills the frame and has a big enough main stroke), first success wins (smallest change in scale order).  Returns (letter, params) or (None, None)."""
    s0 = SG.sig(SG.letter_strokes(L)) if s0 is None else s0
    opts = [(0, "anchor"), (15, "anchor"), (-15, "anchor")] + ([(0, "stem"), (0, "stemL")] if L["sk"]["kind"] == "stem" else [])
    for strict in (True, False):       # first look for a clearly fuller, clearly larger letter; then settle for any that passes the rules
        for f in FAST_SCALES:
            for gm in FAST_GS:
                g = f * gm
                if g > 2.5 or g < 1.0: continue
                for dx, pv in opts:
                    N = transform(L, f, g, dx, "stem" if pv.startswith("stem") else pv, 1.0 if pv == "stemL" else None)
                    pr = C.primary_size(N)
                    if pr < (0.5 if strict else R["PRIMARY_MIN"]): continue
                    if C.max_void(N) > R["MAX_VOID"]: continue
                    if C.white_fraction(N) > (R["WHITE_TARGET"] if strict else R["WHITE_MAX"]): continue
                    try:
                        if not C.valid(N): continue
                    except Exception: continue
                    if SG.sig(SG.letter_strokes(N)) != s0: continue
                    return N, (round(f, 2), round(g, 2), dx, pv)
    return None, None
