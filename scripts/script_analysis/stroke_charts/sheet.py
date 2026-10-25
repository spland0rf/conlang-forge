"""Contact sheets of a drafted script: the real letter (left of each pair) and its strokes, one colour per stroke (right).
python -m stroke_charts.sheet FONTFILE DRAFT.json OUT_PREFIX [per_sheet]"""
import json
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

COLS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#e377c2"]

def sheets(fontfile, data, out, per=60, ncols=6):
    F = ImageFont.truetype(fontfile, 110)
    keys = list(data)
    for s in range(0, len(keys), per):
        chunk = keys[s:s + per]
        nrows = -(-len(chunk) // ncols)
        fig, axes = plt.subplots(nrows, ncols * 2, figsize=(ncols * 2.1, nrows * 1.15), squeeze=False)
        for ax in axes.flat: ax.axis("off")
        for i, ch in enumerate(chunk):
            r, c = divmod(i, ncols)
            a, b = axes[r][2 * c], axes[r][2 * c + 1]
            im = Image.new("L", (150, 150), 255); ImageDraw.Draw(im).text((20, 5), ch, font=F, fill=0)
            a.imshow(im, cmap="gray")
            b.set_xlim(-.05, 1.05); b.set_ylim(-.05, 1.05); b.set_aspect("equal")
            for k, st in enumerate(data[ch]["strokes"]):
                xs, ys = zip(*st)
                if len(st) == 2 and abs(xs[0] - xs[1]) < .03 and abs(ys[0] - ys[1]) < .03:
                    b.plot(xs[:1], ys[:1], "o", color=COLS[k % 7], ms=3)
                else:
                    b.plot(xs, ys, color=COLS[k % 7], lw=1.5, solid_capstyle="round")
        fig.tight_layout()
        fig.savefig(f"{out}_{s // per + 1}.png", dpi=80)
        plt.close(fig)

if __name__ == "__main__":
    sheets(sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 60)
