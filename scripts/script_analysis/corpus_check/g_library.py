"""Devanagari-like form library from the 26 'Generator v2' page letters (seed 7), with the user's 7 Nov edits (G1, G4, G13, G20, G24),
repair where the size tests asked for it.  Writes ../alphabet_gen/devanagari_like_library.json."""
import json, math, copy, collections
import corpus_load as CL
import sig as SG, compound_gen as C
from repair_corpus import fix
R = C.R
RAW = json.load(open(CL.os.path.join(CL.HERE, "page_seed7_letters.json")))["letters"]
def raw_of(key):
    l = next(x for x in RAW if x["head"] == key)
    return [[q["cls"].split()[0], CL.parse(q["d"])] for q in l["paths"] if q["cls"].split()[:1] and q["cls"].split()[0] in ("body", "second", "struct", "accent")], \
           [["red" if "#c9372c" in m.split("<circle")[1] else "touch", float(CL.re.search(r'cx="([\d.]+)"', m).group(1)), float(CL.re.search(r'cy="([\d.]+)"', m).group(1))] for m in l["marks"] if "<circle" in m]
def bez(p0, c1, c2, p3, n=14):
    return [tuple((1-t)**3*p0[i] + 3*(1-t)**2*t*c1[i] + 3*(1-t)*t*t*c2[i] + t**3*p3[i] for i in (0, 1)) for t in [k / n for k in range(n + 1)]]
def rot(P, c, deg):
    a = math.radians(deg); ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in P]
def edit(key, raw, J):
    raw = [[r, list(P)] for r, P in raw]
    if key == "G1":      # smaller bulge, centred on the stem; inner curl becomes an outward (left) flourish on the bulge
        stem_x = 73.8; y0, y1 = 38.0, 68.0
        bulge = bez((stem_x, y0), (38.5, y0 - 6.5), (38.5, y1 + 6.5), (stem_x, y1), 24)
        raw[2][1] = bulge
        L = min(bulge, key=lambda p: p[0])
        hook = bez(L, (L[0] - 5.5, L[1] - 5.0), (L[0] - 12.0, L[1] - 1.0), (L[0] - 9.0, L[1] + 4.0), 10)
        raw[3] = ["accent", hook]
        J = [["red", 73.8, 20.0], ["touch", stem_x, y0], ["touch", L[0], L[1]]]
    elif key == "G4":    # J-hook centred under the bar
        bar = raw[0][1]; cx = (bar[0][0] + bar[1][0]) / 2; xs = [p[0] for p in raw[1][1]]; dx = cx - (min(xs) + max(xs)) / 2
        raw[1][1] = [(x + dx, y) for x, y in raw[1][1]]; J = [["red", J[0][1] + dx, J[0][2]]]
    elif key == "G13":   # more room between the curl and the bar: the body hangs 8 lower on a longer descender
        dy = 8.0
        for i, (r, P) in enumerate(raw):
            if r == "body": raw[i][1] = [(x, y + dy) for x, y in P]
            if r == "struct" and len(P) == 2 and abs(P[0][0] - P[1][0]) < .5 and P[0][1] < 24: raw[i][1] = [P[0], (P[1][0], P[1][1] + dy)]
        J = [[j[0], j[1], j[2] + (dy if j[2] > 24 else 0)] for j in J]
    elif key in ("G20", "G24"):   # bottom-left diagonal leans left: rotated 45 degrees about its start (37.6 deg right of vertical -> 7 deg left)
        d = raw[-1] if key == "G24" else raw[4]
        d[1] = rot(d[1], d[1][0], 45.0)
    return raw, J
def main():
    out = []; seen = {}; real = SG.known_signatures(); log = []
    for key in [x["head"] for x in RAW]:
        raw, J = raw_of(key); changed = key in ("G1", "G4", "G13", "G20", "G24")
        if changed: raw, J = edit(key, raw, J)
        r = CL.build_record([(a, b) for a, b in raw], J, key=key)
        sg = SG.sig(SG.letter_strokes(r)); dup = seen.get(sg); seen.setdefault(sg, key)
        wf, pr = C.white_fraction(r), C.primary_size(r); mv = C.max_void(r) if r["sk"]["kind"] in ("stem", "desc") else 0
        fail = [n for n, b in (("primary", pr < R["PRIMARY_MIN"]), ("white", wf > R["WHITE_MAX"]), ("void", mv > R["MAX_VOID"])) if b]
        form, rep = r, None
        if fail and not dup and key != "G1": N, how = fix(r, sg); form, rep = (N, how) if N else (r, None)
        elif fail and key == "G1": log.append("G1 custom form fails %s (w%.2f p%.2f v%.0f)" % (fail, wf, pr, mv))
        paths = [{"role": role, "pts": [[round(x, 1), round(y, 1)] for x, y in P]} for role, P in (
            ([("struct", [(form["bar"][0], 20.0), (form["bar"][1], 20.0)])] if form.get("bar") else [])
            + ([("body", [(form["sk"]["S"], 20.0), (form["sk"]["S"], 88.0)])] if False else [])
            + list(zip(form["stroke_roles"], form["strokes"])) + [("accent", P) for P in form["struct"]])]
        out.append({"id": key, "source": "Generator v2 page, seed 7", "edited": changed, "repaired": rep and list(rep), "duplicate_of": dup,
                    "size_fail_as_drawn": fail, "bar": form.get("bar"), "sk": form["sk"], "J": [[j[0], round(j[1], 1), round(j[2], 1)] for j in form["J"]],
                    "strokes": paths, "stem_line": form["sk"]["kind"] == "stem", "sig": repr(sg)[:200]})
        print(key, "edited" if changed else "", "dup of " + dup if dup else "", "repaired %s" % (rep,) if rep else "", fail or "", "real-copy" if sg in real else "")
    for l in log: print(l)
    json.dump({"note": "Devanagari-like form library. 'strokes' are polylines in the 100x100 model box (y down, bar y=20, baseline y=88) with roles body/second/struct/accent; the full-height stem (red) is implied by sk.kind == 'stem' at x = sk.S. duplicate_of: same structure as an earlier entry (kept for the record, skip when sampling).",
               "letters": out}, open(CL.os.path.join(CL.HERE, "..", "alphabet_gen", "devanagari_like_library.json"), "w"), separators=(",", ":"))
    return out
if __name__ == "__main__": main()
