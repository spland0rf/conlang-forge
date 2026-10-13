"""Name each letter's body by connectivity alone, and tabulate how often each motif is used per script."""
import json
from collections import Counter

from corpus import SCRIPTS
from render import glyph_bitmaps
from topology import analyse

NAMES = ["line/arc (open, 1 stroke)", "hook/bent (2 ends, 1 junction-free, long)", "ring (closed, no ends)", "ring with tail(s)",
         "T/Y branch (1 junction)", "ladder/multi-branch (2+ junctions)", "double ring/loop-chain", "ring + branches"]


def motif(p):
    j, e, l = len(p["junctions"]), p["ends"], p["loops"]
    if l == 0 and j == 0:
        return "open stroke" if e <= 2 else "open multi-stroke"
    if l == 0 and j == 1:
        return "branch (T/Y/fork)"
    if l == 0:
        return "branched tree (2+ junctions)"
    if l == 1 and j == 0:
        return "ring"
    if l == 1 and j == 1 and e <= 1:
        return "ring with tail"
    if l == 1:
        return "ring + branches"
    return "multi-loop"


if __name__ == "__main__":
    out = {}
    allm = set()
    for n in SCRIPTS:
        c = Counter()
        for ch, bm in glyph_bitmaps(n)[0]:
            if bm.sum() < 20:
                continue
            _, parts = analyse(bm)
            main = [q for q in parts if q["main"]][0]
            c[motif(main)] += 1
        tot = sum(c.values())
        out[n] = {k: round(v / tot, 2) for k, v in c.most_common()}
        allm |= set(out[n])
    json.dump(out, open("motifs.json", "w"), indent=1)
    ms = sorted(allm)
    print("%-11s" % "", " | ".join(m[:16].rjust(16) for m in ms))
    for n, d in out.items():
        print("%-11s" % n, " | ".join(("%.2f" % d.get(m, 0)).rjust(16) for m in ms))
