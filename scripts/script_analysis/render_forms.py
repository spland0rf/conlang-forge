"""Draw every form in a form library (forms/<script>.json) with the pen engine, to check that each entry can be regenerated.
   python render_forms.py devanagari --out forms.png"""
import argparse, json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from conlang_forge.script.pen import Pen

def draw(form, rng=None):
    p = Pen(rng or random.Random(0), "smooth")
    for st in form["strokes"]:
        if "dot" in st:
            x, y, r = st["dot"]; p.begin(x, y, 0); p.line(0.001); continue
        p.begin(*st["s"])
        for seg in st["segs"]:
            k = seg[0]
            if k == "L": p.line(seg[1])
            elif k == "A": p.arc(seg[1], seg[2])
            elif k == "T": p.turn(seg[1])
    return p.strokes

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--out", default="forms.png"); a = ap.parse_args()
    lib = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "conlang_forge", "script", "forms", a.script + ".json")))
    F = lib["forms"]; cols = 6; rows = (len(F) + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 2, rows * 2.4))
    for ax in axs.flat: ax.axis("off")
    for ax, f in zip(axs.flat, F):
        ax.plot([0.1, 0.95], [1, 1], color="#b0b", lw=1)
        for s in draw(f):
            xs, ys = zip(*s["p"]); ax.plot(xs, ys, "k", lw=1.6, solid_capstyle="round")
        ax.set_xlim(0, 1); ax.set_ylim(-0.1, 1.1); ax.set_aspect("equal"); ax.set_title(f["id"], fontsize=8)
    fig.savefig(a.out, dpi=100, bbox_inches="tight"); print(a.out)
