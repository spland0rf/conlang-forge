"""User edits of 6 Nov 17:28 to the review-2 letters: make the '3' larger in D18, H27 and H30.
D18: the curved connector from the descender foot is shortened in height (drop 23 -> 10) so the 3 starts higher and can grow to 1.55x.
H27 / H30: the 3 grows about its attachment point (1.5x / 1.45x); H30's 3 also moves 3 units left (its connector grows to follow) to keep clear of the hook.
Idempotent: letters already carrying `edits` are skipped."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "compound_gen")); sys.path.insert(0, os.path.join(HERE, ".."))
import compound_gen as C, sig as SG
def scale(P, piv, f, dx=0.0): return [[round(piv[0] + dx + f * (x - piv[0]), 1), round(piv[1] + f * (y - piv[1]), 1)] for x, y in P]
def main():
    path = os.path.join(HERE, "approved_review2.json"); d = json.load(open(path))
    for l in d["liked"]:
        k = l["review_id"]
        if l.get("edits") or k not in ("D18", "H27", "H30"): continue
        if k == "D18":
            con, three = l["strokes"]; a = con[0]; end = con[-1]; new_end_y = a[1] + 10.4; g = (new_end_y - a[1]) / (end[1] - a[1])
            con2 = [[x, round(a[1] + g * (y - a[1]), 1)] for x, y in con]
            piv = con2[-1]; shift = piv[1] - end[1]; three2 = scale([[x, y + shift] for x, y in three], piv, 1.55); l["strokes"] = [con2, three2]      # the 3 rides up with the connector's new end, then grows
            l["J"] = [["red", a[0], a[1]], ["touch", piv[0], piv[1]]]; note = "connector shortened to drop 10.4; 3 scaled 1.55 about its start"
        else:
            f, dx = (1.5, 0.0) if k == "H27" else (1.45, -3.0)
            piv = next(j for j in l["J"] if j[0] == "red" and j[1] < 40); piv = (piv[1], piv[2])
            l["strokes"][0] = scale(l["strokes"][0], piv, f, dx)
            st = l["struct"]; ci = next(i for i, s in enumerate(st) if len(s) == 2 and abs(s[0][1] - s[1][1]) < .01 and s[0][0] < 40)
            st[ci][0] = [round(piv[0] + dx, 1), st[ci][0][1]]
            l["J"] = [[j[0], round(piv[0] + dx, 1) if (j[0] == "red" and j[1] < 40) else j[1], j[2]] for j in l["J"]]; note = "3 scaled %.2f about its attachment%s" % (f, ", moved 3 left" if dx else "")
        l["edits"] = note; print(k, note)
    json.dump(d, open(path, "w"), separators=(",", ":"))
if __name__ == "__main__": main()
