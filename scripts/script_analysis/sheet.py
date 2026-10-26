"""A contact sheet of a generated preset's letters (strokes in the unit box, smoothed as the app draws them; the top bar is drawn for
scripts that have one).   python sheet.py bengali [--seed 1] [--n 40] [--pins '{}'] [--out x.png]"""
import argparse
import json
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from conlang_forge.script.generate import generate     # noqa: E402
from conlang_forge.script.geometry import flatten      # noqa: E402
from conlang_forge.script.presets import PRESETS       # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("preset"); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--n", type=int, default=40); ap.add_argument("--out", default=None)
    ap.add_argument("--pins", default="{}")
    a = ap.parse_args()
    pins = dict(next(p for p in PRESETS if p["id"] == a.preset)["pins"]); pins.update(json.loads(a.pins))
    script = generate(a.seed, pins)
    letters = script["letters"][:a.n]
    cols = 10
    rows = (len(letters) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 1.1 * max(1.0, (max([1.0] + [max(x for st in l['strokes'] for x, _ in st['p']) for l in letters]) + .2) / 1.2), rows * 1.3), squeeze=False)
    bar = script["spec"].get("topline") == "bar"
    for ax in axes.flat:
        ax.axis("off")
    wmax = max([1.0] + [max(x for st in l["strokes"] for x, _ in st["p"]) for l in letters])      # letters can be wider than the unit box
    for ax, l in zip(axes.flat, letters):
        ax.set_xlim(-.1, wmax + .1); ax.set_ylim(-.45, 1.15); ax.set_aspect("equal")
        for s in l["strokes"]:
            if s.get("stub"):
                continue
            if s.get("dot"):
                ax.plot(*s["p"][0], "ko", ms=3); continue
            xs, ys = zip(*flatten(s, script["spec"]["roundness"]))
            ax.plot(xs, ys, "k", lw=1.6, solid_capstyle="round", solid_joinstyle="round")
        ys = [y for s in l["strokes"] for _, y in s["p"]]
        if bar and max(ys) > .9:
            ax.plot([0, 1], [1, 1], "k", lw=1.6)
    fig.tight_layout()
    out = a.out or f"/tmp/claude-0/-home-claude/9df3cbd6-5590-5857-9ad9-4bf9abf1a96b/scratchpad/sheet_{a.preset}.png"
    fig.savefig(out, dpi=90); print(out)
