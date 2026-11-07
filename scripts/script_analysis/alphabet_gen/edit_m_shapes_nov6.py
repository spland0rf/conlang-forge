"""User edit, 6 Nov 17:43: enlarge the small double-cup ("M" / sideways 3) stroke of H25, A4, A21 and A24.
Each is scaled about the end that joins the rest of the letter (so the join stays closed):  H25 x1.8 (and moved 8 right, connector shortened to follow),
A4 x1.55, A21 x1.45 (whole letter moved 9 left to keep it in the box), A24 x1.25 (its 3 is already tall; frame-limited).  Idempotent."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..")); sys.path.insert(0, os.path.join(HERE, "..", "compound_gen"))
import sig as SG
TAG = "M shape enlarged"
def cups(P): return len(SG.runs(SG.canon([tuple(p) for p in SG.dense([tuple(p) for p in P])]), 25))
def m_index(l): return max(range(len(l["strokes"])), key=lambda i: cups(l["strokes"][i]))
def scale(P, piv, f, dx=0.0): return [[round(piv[0] + dx + f * (x - piv[0]), 1), round(piv[1] + f * (y - piv[1]), 1)] for x, y in P]
def pivot(l, i):
    P = l["strokes"][i]; js = [(j[1], j[2]) for j in l["J"] if j[0] != "touch" or True]
    return min((P[0], P[-1]), key=lambda e: min(math.dist(e, j) for j in js if j[1] > 24 or True))
def edit(l, f, dx=0.0, shift_all=0.0):
    i = m_index(l); P = l["strokes"][i]
    # the joined end: the end nearest a junction that is not on the bar
    js = [(j[1], j[2]) for j in l["J"] if j[2] > 24]
    piv = min((P[0], P[-1]), key=lambda e: min(math.dist(e, j) for j in js))
    l["strokes"][i] = scale(P, piv, f, dx)
    if dx:      # half-bar: the connector that leaves the 3 follows it
        for s in l["struct"]:
            if len(s) == 2 and abs(s[0][1] - s[1][1]) < .01 and abs(s[0][0] - piv[0]) < .6: s[0] = [round(s[0][0] + dx, 1), s[0][1]]
        l["J"] = [[j[0], round(j[1] + dx, 1) if abs(j[1] - piv[0]) < .6 and abs(j[2] - piv[1]) < .6 else j[1], j[2]] for j in l["J"]]
    if shift_all:
        mv = lambda P: [[round(x + shift_all, 1), y] for x, y in P]
        l["strokes"] = [mv(P) for P in l["strokes"]]; l["struct"] = [mv(P) for P in l.get("struct") or []]
        if l.get("bar"): l["bar"] = [round(l["bar"][0] + shift_all, 1), round(l["bar"][1] + shift_all, 1)]
        if l["sk"].get("kind") == "desc": l["sk"]["x"] += shift_all
        if l["sk"].get("kind") == "stem": l["sk"]["S"] += shift_all
        l["J"] = [[j[0], round(j[1] + shift_all, 1), j[2]] for j in l["J"]]
    l["edits"] = (l.get("edits") + "; " if l.get("edits") else "") + "%s x%.2f%s" % (TAG, f, (", moved %g right" % dx) if dx else (", letter moved %g" % shift_all if shift_all else ""))
def main():
    for fn, key, spec in (("approved_review2.json", "liked", {"H25": (1.8, 8.0, 0.0)}), ("approved_review1.json", "letters", {"A4": (1.55, 0.0, 0.0), "A21": (1.45, 0.0, -9.0), "A24": (1.25, 0.0, 0.0)})):
        d = json.load(open(os.path.join(HERE, fn)))
        for l in d[key]:
            k = l["review_id"]
            if k in spec and TAG not in (l.get("edits") or ""): edit(l, *spec[k]); print(k, l["edits"])
        json.dump(d, open(os.path.join(HERE, fn), "w"), separators=(",", ":"))
if __name__ == "__main__": main()
