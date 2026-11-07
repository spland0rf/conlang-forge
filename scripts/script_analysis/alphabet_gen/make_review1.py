"""One-time: freeze the 18 approved review-1 letters (A1..A31, original generated numbering) as repo data, with the size repair applied
where they failed the rules, and A10 = A17's body + the right vertical (user spec).  Later edits are made on approved_review1.json."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "compound_gen")); sys.path.insert(0, os.path.join(HERE, ".."))
import compound_gen as C, repair as RP, sig as SG
def rd(L): return [[round(x, 1), round(y, 1)] for x, y in L]
def main(src="/tmp/alpha_orig.json"):
    orig = json.load(open(src))["letters"]; out = []
    for n in (1, 3, 4, 6, 7, 10, 11, 12, 17, 20, 21, 22, 24, 25, 26, 29, 30, 31):
        s = orig[(17 if n == 10 else n) - 1]; L = dict(s); L["strokes"] = [[tuple(p) for p in q] for q in s["strokes"]]; L["struct"] = [[tuple(p) for p in q] for q in (s.get("struct") or [])]
        half = "kind" not in s["sk"]; note = None
        if n == 10:
            xmax = max(p[0] for P in L["strokes"] for p in P); vx = xmax + 9.0; L["bar"] = [L["bar"][0], max(L["bar"][1], vx + 8.0)]
            L["strokes"].append([(vx, 20.0), (vx, 88.0)]); note = "spec: A17 body + right vertical"
        elif not half and not C.valid(L) and C.valid(L, size_rules=False):
            N, how = RP.repair_fast(L, SG.sig(SG.letter_strokes(L)))
            if N: L = N; note = "repaired %s" % (list(how),)
        out.append({"review_id": "A%d" % n, "half": half, "family": "half-bar" if half else {"stem": "stem", "desc": "descender", "bar": "hang"}[L["sk"]["kind"]],
                    "sk": L["sk"], "bar": L.get("bar") and [round(L["bar"][0], 1), round(L["bar"][1], 1)], "strokes": [rd(P) for P in L["strokes"]], "struct": [rd(P) for P in L["struct"]],
                    "J": [[j[0], round(j[1], 1), round(j[2], 1)] for j in L["J"]], **({"notes": note} if note else {})})
    json.dump({"review": "1 (6 Nov 2026), approved letters, original numbering", "letters": out}, open(os.path.join(HERE, "approved_review1.json"), "w"), separators=(",", ":"))
    print(len(out), "letters;", [(l["review_id"], l.get("notes")) for l in out if l.get("notes")])
if __name__ == "__main__": main()
