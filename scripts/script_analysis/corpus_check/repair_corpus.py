import sys, json, copy, collections
from corpus_load import records
import sig as SG, compound_gen as C, repair as RP
R = C.R
def inside(N, O=None):
    """Stays inside the model box (2..98 across, 2..92 down), except where the original already went outside it (accents above the bar)."""
    pts = [p for P in N["strokes"] for p in P]; o = [p for P in (O or N)["strokes"] for p in P]
    lo_x, hi_x, lo_y, hi_y = min(2, min(p[0] for p in o)), max(98, max(p[0] for p in o)), min(2, min(p[1] for p in o)), max(92, max(p[1] for p in o))
    ok = all(lo_x <= p[0] <= hi_x and lo_y <= p[1] <= hi_y for p in pts)
    if N.get("bar"): ok = ok and all(N["bar"][0] - 1 <= j[1] <= N["bar"][1] + 1 for j in N["J"] if j[0] == "red" and abs(j[2] - 20) < 1.5)
    return ok
def fix(L, s0):
    opts = [(0, "anchor"), (15, "anchor"), (-15, "anchor")] + ([(0, "stem"), (0, "stemL")] if L["sk"]["kind"] == "stem" else [])
    if not any(j[0] == "red" for j in L["J"]):
        # bar-less letter: pivot on the point where the body meets the stem (a junction, else the body point nearest the stem)
        S = L["sk"].get("S"); pts = [p for P in L["strokes"] for p in P]
        if S is None or not pts: return None, "no anchor"
        j = next((j for j in L["J"] if abs(j[1] - S) < 3), None); p = (j[1], j[2]) if j else min(pts, key=lambda p: abs(p[0] - S))
        L = dict(L); L["J"] = [["red", p[0], p[1]]] + list(L["J"])
    a_x, ay = next((j[1], j[2]) for j in L["J"] if j[0] == "red"); ymax = max(p[1] for P in L["strokes"] for p in P)
    gmax = max(1.0, (90.0 - ay) / max(ymax - ay, 1.0))      # taller only as far as the frame allows (many letters already reach the baseline)
    for strict in (True, False):
        for f in [1.0] + RP.FAST_SCALES:
            for g in sorted({1.0, min(f, gmax), min(1.25 * f, gmax), min(1.5 * f, gmax)}):
                if f == 1.0 and g == 1.0: continue
                for dx, pv in opts:
                    try: N = RP.transform(L, f, g, dx, "stem" if pv.startswith("stem") else pv, 1.0 if pv == "stemL" else None)
                    except Exception as e: return None, "transform"
                    if dx and pv == "anchor": N["struct"] = [[(p[0] + dx if abs(P[0][0] - a_x) < 3 else p[0], p[1]) for p in P] for P in L["struct"]]
                    if C.primary_size(N) < (0.5 if strict else R["PRIMARY_MIN"]): continue
                    if not inside(N, L): continue
                    if C.white_fraction(N) > (R["WHITE_TARGET"] if strict else R["WHITE_MAX"]): continue
                    if N["sk"]["kind"] in ("stem", "desc") and C.max_void(N) > R["MAX_VOID"]: continue
                    if SG.sig(SG.letter_strokes(N)) != s0: continue
                    return N, (round(f, 2), round(g, 2), dx, pv)
    return None, "no candidate"
if __name__ == "__main__":
    recs = records(); real = SG.known_signatures(); seen = {}; res = []
    for r in recs:
        sg = SG.sig(SG.letter_strokes(r))
        if sg in real or sg in seen: continue
        seen[sg] = r
        fail = [n for n, bad in (("primary", C.primary_size(r) < R["PRIMARY_MIN"]), ("white", C.white_fraction(r) > R["WHITE_MAX"]),
                 ("void", r["sk"]["kind"] in ("stem", "desc") and C.max_void(r) > R["MAX_VOID"])) if bad]
        if not fail: res.append((r, None, "ok", sg)); continue
        N, how = fix(r, sg); res.append((r, N, how, sg))
    c = collections.Counter("ok" if h == "ok" else ("repaired" if N else "stuck") for r, N, h, _ in res)
    print(len(res), "distinct structures:", dict(c))
    print("stuck reasons:", collections.Counter(h for r, N, h, _ in res if h not in ("ok",) and not N))
    print("repair params (scale):", collections.Counter(h[0] for r, N, h, _ in res if N))
    import pickle; pickle.dump([(r, N, h) for r, N, h, _ in res], open("repair_res.pkl", "wb"))
