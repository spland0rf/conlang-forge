"""Ethiopic (Amharic) stroke data of the 91 letters on the user's page 1, taken from the skeleton of Noto Sans Ethiopic so the topology matches the real
letters, then split the way the user's charts split them: a run of vertical and horizontal segments is one stroke per segment; smooth curves stay whole.
    python ethiopic_from_font.py [sheet.png]      (needs the stroke_charts package from branch feat/stroke-charts on sys.path via SC=)"""
import json, math, os, sys
SC = os.environ.get("SC", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, SC)
from fontTools.ttLib import TTFont
import numpy as np, networkx as nx
from skimage.draw import polygon as _poly
from skimage.measure import approximate_polygon, label, regionprops
from skimage.morphology import skeletonize, remove_small_holes
import warnings; warnings.filterwarnings('ignore')
from stroke_charts import skeleton as _sk
from stroke_charts.common import glyph_polys

def contract_filled_cycles(g, img):
    """A skeleton cycle that encloses solid ink (where two thick strokes cross) is an artefact: collapse it to one junction."""
    for cyc in nx.cycle_basis(g):
        if len(cyc) > 80 or any(n not in g for n in cyc):
            continue
        ys = np.array([n[0] for n in cyc]); xs = np.array([n[1] for n in cyc])
        rr, cc = _poly(ys, xs, img.shape)
        if len(rr) and img[rr, cc].mean() > .9:
            c = (float(ys.mean()), float(xs.mean()))
            outside = {m for n in cyc for m in g.neighbors(n) if m not in cyc}
            g.remove_nodes_from(cyc)
            g.add_node(c)
            for m in outside:
                if m in g: g.add_edge(c, m)
    return g

def strokes_for(font, ch, tol=2.2, spur=.07, dot_area=.03):
    polys = glyph_polys(font, ch)
    if polys is None:
        return None
    img = remove_small_holes(_sk.raster(polys), 260)          # the tiny counters where a stem crosses a ring are not letter holes
    lab = label(img)
    out, dots = [], []
    N = _sk.N; PAD = _sk.PAD
    for rp in regionprops(lab):
        if rp.area / (N * N) < dot_area:
            cy, cx = rp.centroid
            dots.append([((cx - PAD) / N - .012, 1 - (cy - PAD) / N), ((cx - PAD) / N + .012, 1 - (cy - PAD) / N)])
            continue
        sk = skeletonize(lab == rp.label)
        g = _sk._graph(sk)
        if not g:
            continue
        for _ in range(3):
            g = contract_filled_cycles(g, img)
        paths = _sk._prune(_sk._merge(_sk._prune(_sk._paths(g), int(spur * N))), int(spur * N))
        for p in paths:
            arr = approximate_polygon(np.array(p, float), tol)
            out.append([((x - PAD) / N, 1 - (y - PAD) / N) for y, x in arr])
    return _sk.order(out) + dots

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", ".fonts", "NotoSansEthiopic[wdth,wght].ttf")
STARTS = [("h", 0x1200), ("l", 0x1208), ("ḥ", 0x1210), ("m", 0x1218), ("ś", 0x1220), ("r", 0x1228), ("s", 0x1230), ("q", 0x1240), ("b", 0x1260),
          ("v", 0x1268), ("t", 0x1270), ("č", 0x1278), ("ḫ", 0x1280)]
VOWELS = ["ä", "u", "i", "a", "e", "ɨ", "o"]

def axis(a, b, tol=18):
    ang = abs(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))) % 180
    return min(ang, abs(ang - 90), abs(ang - 180)) < tol

def split(stroke):
    """Break a polyline at right-angle corners between axis-aligned segments (the L, U and T shapes); leave curves alone."""
    out, cur = [], [stroke[0]]
    for i in range(1, len(stroke) - 1):
        a, b, c = stroke[i - 1], stroke[i], stroke[i + 1]
        cur.append(b)
        if axis(a, b) and axis(b, c):
            d1 = math.atan2(b[1] - a[1], b[0] - a[0]); d2 = math.atan2(c[1] - b[1], c[0] - b[0])
            if abs((d2 - d1 + math.pi) % (2 * math.pi) - math.pi) > math.radians(60):
                out.append(cur); cur = [b]
    cur.append(stroke[-1]); out.append(cur)
    return out

def build():
    font = TTFont(FONT)
    data = {}
    for c, cp in STARTS:
        for j, v in enumerate(VOWELS):
            ch = chr(cp + j)
            st = strokes_for(font, ch) or []
            parts = [p for s in st for p in (split(s) if len(s) > 2 else [s])]
            data[c + v] = dict(char=ch, strokes=[[[round(x, 3), round(y, 3)] for x, y in p] for p in parts])
    return data

if __name__ == "__main__":
    data = build()
    json.dump(data, open(os.path.join(HERE, "ethiopic_page1_font.json"), "w"), ensure_ascii=False)
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image, ImageDraw, ImageFont
    F = ImageFont.truetype(FONT, 110)
    cols = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#e377c2"]
    fig, axes = plt.subplots(13, 14, figsize=(14, 15))
    for i, (c, cp) in enumerate(STARTS):
        for j, v in enumerate(VOWELS):
            a, b = axes[i][2 * j], axes[i][2 * j + 1]
            im = Image.new("L", (150, 150), 255); ImageDraw.Draw(im).text((20, 5), chr(cp + j), font=F, fill=0)
            a.imshow(im, cmap="gray"); a.axis("off")
            b.set_xlim(-.05, 1.05); b.set_ylim(-.05, 1.05); b.set_aspect("equal"); b.axis("off")
            for k, s in enumerate(data[c + v]["strokes"]):
                xs, ys = zip(*s); b.plot(xs, ys, color=cols[k % 7], lw=1.5, solid_capstyle="round")
            if i == 0: a.set_title(v, fontsize=9, loc="left")
        axes[i][0].text(-5, 75, c, fontsize=11, ha="right")
    fig.suptitle("Amharic page 1: real letter (left of each pair) and its stroke skeleton, one colour per stroke (right)", fontsize=11)
    fig.tight_layout(); fig.savefig(sys.argv[1] if len(sys.argv) > 1 else "ethiopic_from_font.png", dpi=75)
    print(sum(len(d["strokes"]) for d in data.values()) / len(data), "strokes per letter")
