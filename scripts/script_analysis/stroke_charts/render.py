"""Render build-up charts (the user's hand-drawn format): glyph, then one panel per stage, new stroke red, earlier strokes black.
The font outline is drawn faintly under the strokes, and each letter gets a fit score so bad stroke guesses are visible."""
import json
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from .common import glyph_polys, ink_path, coverage


UNIFORM = set("ㅡㅣΙ")
INSET = .08           # stroke centre-lines lie about half a stroke width inside the ink bbox


def place(strokes, inset=INSET):
    return [[(inset + (1 - 2 * inset) * x, inset + (1 - 2 * inset) * y) for x, y in s] for s in strokes]


def chart(font, items, out_png, title, per_page=12, ncols_max=None, inset=INSET):
    pages = [items[i:i + per_page] for i in range(0, len(items), per_page)]
    report = []
    for pi, page in enumerate(pages):
        ncols = 2 + max(len(s) for _, _, s in page)
        fig, axes = plt.subplots(len(page), ncols, figsize=(1.25 * ncols, 1.35 * len(page)), squeeze=False)
        for r, (ch, name, strokes) in enumerate(page):
            polys = glyph_polys(font, ch, uniform=ch in UNIFORM)
            strokes = place(strokes, inset)
            if polys is None:
                continue
            on, cov = coverage(polys, strokes)
            report.append({"char": ch, "name": name, "strokes": len(strokes), "on_ink": round(on, 2), "ink_covered": round(cov, 2)})
            for c in range(ncols):
                ax = axes[r][c]
                ax.set_xlim(-.15, 1.15); ax.set_ylim(-.15, 1.15); ax.set_aspect("equal"); ax.axis("off")
                if c == 0:
                    ax.text(.5, .5, name, ha="center", va="center", fontsize=11)
                    continue
                ax.add_patch(PathPatch(ink_path(polys), fc="#e4e4e4", ec="none"))
                if c == 1:
                    ax.add_patch(PathPatch(ink_path(polys), fc="black", ec="none"))
                    ax.text(1.12, -.12, f"{on:.2f}/{cov:.2f}", fontsize=5, ha="right", color="#888")
                    continue
                k = c - 2
                if k >= len(strokes):
                    continue
                for j in range(k + 1):
                    xs, ys = zip(*strokes[j])
                    ax.plot(xs, ys, color="#d00" if j == k else "black", lw=2.2, solid_capstyle="round", solid_joinstyle="round")
        fig.suptitle(f"{title} (page {pi + 1}/{len(pages)})", fontsize=9)
        fig.tight_layout()
        fig.savefig(f"{out_png}_{pi + 1}.png", dpi=110)
        plt.close(fig)
    return report


def save(items, path):
    json.dump({ch: {"name": n, "strokes": [[list(map(lambda v: round(v, 3), p)) for p in s] for s in strokes]} for ch, n, strokes in items}, open(path, "w"), ensure_ascii=False, indent=1)
