"""Build conlang_forge/script/forms/devanagari_library.json: the curated "Devanagari-like" forms for the engine, in the same
role + SVG-path schema as devanagari_corpus.json (model box 100x100, y down, headline y=20, baseline y=88).
Sources: (1) the Generator v2 page letters G1-G26 with the user's edits and the repair step (G21 skipped, duplicate of G3);
(2) the approved descender and half-bar letters of review 2 (D14, 16, 18, 19, 20, H25-H30); (3) the 18 approved letters of review 1 (A1...A31),
from the original generated set, repaired by the size rules where they failed them (A10 = A17's body plus the right vertical, per the user's spec)."""
import json, os, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "corpus_check")); sys.path.insert(0, os.path.join(HERE, ".."))
import corpus_load as CL, g_library as G
import sig as SG, compound_gen as C, repair as RP
from repair_corpus import fix
R = C.R
import script_config as SC
OUT = SC.path("library_out")
def path(P):
    pts = [(round(x, 1), round(y, 1)) for x, y in P]
    out = [pts[0]]
    for p in pts[1:]:
        if p != out[-1]: out.append(p)
    if len(out) == 2: return "M%g %g L%g %g" % (*out[0], *out[1])
    return "M%g %g " % out[0] + " ".join("L%g %g" % p for p in out[1:])
def poly_pts(P, step=2.0):
    """thin a dense polyline (keep the ends and every ~step units) so the file stays small"""
    import math
    out = [P[0]]; acc = 0.0
    for a, b in zip(P, P[1:]):
        acc += math.dist(a, b)
        if acc >= step: out.append(b); acc = 0.0
    if out[-1] != P[-1]: out.append(P[-1])
    return out
def entry(lid, origin, family, items, J, nobar, notes=None):
    return {"_items": items, "id": lid, "origin": origin, "family": family, "s": [[r, path(poly_pts(P) if len(P) > 4 else P)] for r, P in items],
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
        letters.append(entry(l["review_id"], "review-2", fam, from_alpha(l), l["J"], l["bucket"] == "half", ("edited by the user: " + l["edits"]) if l.get("edits") else None))
    # review 1 approved letters (original generated numbering; frozen with the size repair in approved_review1.json)
    for l in json.load(open(os.path.join(HERE, "approved_review1.json")))["letters"]:
        note = ", ".join(x for x in (l.get("notes"), ("edited by the user: " + l["edits"]) if l.get("edits") else None) if x) or None
        letters.append(entry(l["review_id"], "review-1", l["family"], from_alpha(as_L(l)), l["J"], l["half"], note))
    real = SG.known_signatures(); seen = {}
    for l in letters:      # same structure as an earlier entry (or a real letter): kept for the record, skipped when the engine samples
        r = CL.build_record(l["_items"], l["j"]); sg = SG.sig(SG.letter_strokes(r))      # judged on the full-resolution strokes, as the generator and the user saw them
        if sg in real: l["duplicate_of"] = "real letter"
        elif sg in seen: l["duplicate_of"] = seen[sg]
        seen.setdefault(sg, l["id"])
    for l in letters: l.pop("_items")
    doc = {"version": 1, "source": "curated by the user: Generator v2 page letters (G), review 2 (D/H), review 1 approved letters (A); see claude/alphabet-review-1.md, -2.md",
           "box": {"w": SC.get()["frame"]["box"], "h": SC.get()["frame"]["box"], "top": int(R["BAR_Y"]), "base": int(R["BASE_Y"])}, "letters": letters}
    json.dump(doc, open(OUT, "w"), separators=(",", ":"))
    from collections import Counter
    print(len(letters), "letters,", sum(1 for l in letters if l.get("duplicate_of")), "marked duplicate;", dict(Counter(l["family"] for l in letters)), "| skipped:", skipped, "| bytes:", os.path.getsize(OUT))
if __name__ == "__main__": main()
