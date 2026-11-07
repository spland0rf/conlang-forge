"""Build conlang_forge/script/forms/devanagari_library.json: the curated "Devanagari-like" forms for the engine, in the same
role + SVG-path schema as devanagari_corpus.json (model box 100x100, y down, headline y=20, baseline y=88).
Sources: (1) the Generator v2 page letters G1-G26 with the user's edits and the repair step (G21 skipped, duplicate of G3);
(2) the approved descender and half-bar letters of review 2 (D14, 16, 18, 19, 20, H25-H30); (3) the 18 approved letters of review 1 (A1...A31),
from the original generated set, repaired by the size rules where they failed them (A10 = A17's body plus the right vertical, per the user's spec)."""
import json, os, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "corpus_check"))
import corpus_load as CL, g_library as G
import sig as SG, compound_gen as C, repair as RP
from repair_corpus import fix
R = C.R
OUT = os.path.join(HERE, "..", "..", "..", "conlang_forge", "script", "forms", "devanagari_library.json")
def path(P):
    pts = [(round(x, 1), round(y, 1)) for x, y in P]
    out = [pts[0]]
    for p in pts[1:]:
        if p != out[-1]: out.append(p)
    if len(out) == 2: return "M%g %g L%g %g" % (*out[0], *out[1])
    return "M%g %g " % out[0] + " ".join("L%g %g" % p for p in out[1:])
def poly_pts(P, step=6):
    """thin a dense polyline (keep the ends and every ~step units) so the file stays small"""
    import math
    out = [P[0]]; acc = 0.0
    for a, b in zip(P, P[1:]):
        acc += math.dist(a, b)
        if acc >= step: out.append(b); acc = 0.0
    if out[-1] != P[-1]: out.append(P[-1])
    return out
def entry(lid, origin, family, items, J, nobar, notes=None):
    return {"id": lid, "origin": origin, "family": family, "s": [[r, path(poly_pts(P) if len(P) > 4 else P)] for r, P in items],
            "j": [[j[0], round(j[1], 1), round(j[2], 1)] for j in J], "nobar": nobar, **({"notes": notes} if notes else {})}
def items_of_form(form):
    it = []
    if form.get("bar"): it.append(("struct", [(form["bar"][0], 20.0), (form["bar"][1], 20.0)]))
    if form.get("stem_item"): it.append((form["stem_item"][0], form["stem_item"][1]))
    elif form["sk"]["kind"] == "stem": it.append(("body", [(form["sk"]["S"], 20.0), (form["sk"]["S"], 88.0)]))
    it += list(zip(form["stroke_roles"], form["strokes"])) + [("accent", P) for P in form["struct"]]
    return it
def from_alpha(L):
    """a compound_gen letter record (alphabet.json / alpha_orig.json shape) -> items"""
    sk = L["sk"]; it = []
    if L.get("bar"): it.append(("struct", [(L["bar"][0], 20.0), (L["bar"][1], 20.0)]))
    if sk.get("kind") == "stem": it.append(("body", [(sk["S"], 20.0), (sk["S"], 88.0)]))
    if sk.get("kind") == "desc": it.append(("struct", [(sk["x"], 20.0), (sk["x"], sk.get("y", 36.0))]))
    it += [("body", [tuple(p) for p in s]) for s in L["strokes"]]
    it += [("struct", [tuple(p) for p in s]) for s in (L.get("struct") or [])]
    return it
def as_L(l):
    L = dict(l); L["strokes"] = [[tuple(p) for p in s] for s in l["strokes"]]; L["struct"] = [[tuple(p) for p in s] for s in (l.get("struct") or [])]; return L
def main():
    letters = []; G.main(); skipped = []
    for f in G.FORMS:
        if f["dup"]: skipped.append((f["id"], "duplicate of " + f["dup"])); continue
        fam = {"stem": "stem", "desc": "descender", "hang": "hang"}[f["form"]["sk"]["kind"]]
        note = ", ".join(x for x in ("edited by the user" if f["edited"] else "", "repaired %s" % (list(f["repaired"]),) if f["repaired"] else "") if x) or None
        letters.append(entry(f["id"], "generator-v2-page-seed7", fam, items_of_form(f["form"]), f["form"]["J"], True, note))
    rv2 = json.load(open(os.path.join(HERE, "approved_review2.json")))["liked"]
    for l in rv2:
        fam = "half-bar" if l["bucket"] == "half" else "descender"
        letters.append(entry(l["review_id"], "review-2", fam, from_alpha(l), l["J"], l["bucket"] == "half"))
    # review 1 approved letters (original generated numbering), repaired where they fail the size rules
    orig = json.load(open("/tmp/alpha_orig.json"))["letters"]; real = SG.known_signatures()
    for n in (1, 3, 4, 6, 7, 10, 11, 12, 17, 20, 21, 22, 24, 25, 26, 29, 30, 31):
        src = orig[17 - 1] if n == 10 else orig[n - 1]; L = as_L(src); note = None
        if n == 10:      # user spec: A17's main body form plus a right-hand vertical stroke (placed 9 units right of the body, bar extended over it)
            xmax = max(p[0] for P in L["strokes"] for p in P); vx = xmax + 9.0
            L["bar"] = [L["bar"][0], max(L["bar"][1], vx + 8.0)]; note = "spec: A17 body + right vertical"
        half = "kind" not in src["sk"]            # a half-bar letter of the first set: no headline of its own, nothing to repair
        it = from_alpha(L)
        if n == 10: it.append(("body", [(vx, 20.0), (vx, 88.0)]))
        sg = SG.sig(SG.letter_strokes(L))
        if not half and not C.valid(L) and C.valid(L, size_rules=False) and n != 10:
            N, how = RP.repair_fast(L, sg)
            if N: L = N; it = from_alpha(L); note = "repaired %s" % (list(how),)
        letters.append(entry("A%d" % n, "review-1", "half-bar" if half else {"stem": "stem", "desc": "descender", "bar": "hang"}.get(src["sk"].get("kind"), "hang"), it, L["J"], half, note))
    real = SG.known_signatures(); seen = {}
    for l in letters:      # same structure as an earlier entry (or a real letter): kept for the record, skipped when the engine samples
        r = CL.build_record([(a, CL.parse(d)) for a, d in l["s"]], l["j"]); sg = SG.sig(SG.letter_strokes(r))
        if sg in real: l["duplicate_of"] = "real letter"
        elif sg in seen: l["duplicate_of"] = seen[sg]
        seen.setdefault(sg, l["id"])
    doc = {"version": 1, "source": "curated by the user: Generator v2 page letters (G), review 2 (D/H), review 1 approved letters (A); see claude/alphabet-review-1.md, -2.md",
           "box": {"w": 100, "h": 100, "top": 20, "base": 88}, "letters": letters}
    json.dump(doc, open(OUT, "w"), separators=(",", ":"))
    from collections import Counter
    print(len(letters), "letters,", sum(1 for l in letters if l.get("duplicate_of")), "marked duplicate;", dict(Counter(l["family"] for l in letters)), "| skipped:", skipped, "| bytes:", os.path.getsize(OUT))
if __name__ == "__main__": main()
