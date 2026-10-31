"""Rebuild every real letter of a script from its form library and draw the chart, to compare with the drawn sheets.
   python render_letters.py devanagari --out letters.png"""
import argparse, json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from render_forms import draw
D = os.path.join(os.path.dirname(__file__), "..", "..", "conlang_forge", "script", "forms")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--out", default="letters.png"); a = ap.parse_args()
    forms = {f["id"]: f for f in json.load(open(f"{D}/{a.script}.json"))["forms"]}
    L = json.load(open(f"{D}/{a.script}_letters.json"))["letters"]
    cols = 8; rows = (len(L) + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 1.9, rows * 2.3))
    for ax in axs.flat: ax.axis("off")
    for ax, l in zip(axs.flat, L):
        ax.plot([0.05, 0.95], [1, 1], color="k", lw=1.6)
        for part in l["parts"]:
            for s in draw(forms[part["form"]]):
                xs, ys = zip(*s["p"]); ax.plot([x + part["dx"] for x in xs], [y + part["dy"] for y in ys], "k", lw=1.6, solid_capstyle="round")
        ax.set_xlim(0, 1); ax.set_ylim(-0.1, 1.1); ax.set_aspect("equal"); ax.set_title(l["name"], fontsize=9)
    fig.savefig(a.out, dpi=90, bbox_inches="tight"); print(a.out)
