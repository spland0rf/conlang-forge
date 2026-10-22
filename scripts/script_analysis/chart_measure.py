"""Measure kana cut from real chart images with the same code as the font glyphs, and print them next to the font numbers.
    python chart_measure.py   (images listed in CHARTS)"""
import json, os, sys
import cv2, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import measure, topology
from chart_glyphs import cut
from render import CELL, SIZE
U = "/root/.claude/uploads/9df3cbd6-5590-5857-9ad9-4bf9abf1a96b/"
CHARTS = {  # name: (file, script, dil, minh, region)
    "katakana thin gothic": ("2d46fc05-image.png", "Katakana", 7, 30, (60, 250, 940, 1230)),
    "katakana poster (mincho/brush)": ("b5a917ec-image.webp", "Katakana", 9, 24, (60, 60, 590, 590)),
    "hiragana chart (rounded sans)": ("9339998e-image.webp", "Hiragana", 11, 24, (70, 140, 380, 1000)),
}
meas = json.load(open(os.path.join(HERE, "measurements.json"))); topo = json.load(open(os.path.join(HERE, "topology.json")))
KEYS_M = ["aspect_median", "share_closed", "ends_mean", "junctions_mean", "horiz", "vert", "diag", "angular", "parts_mean", "share_with_marks", "symlr"]
KEYS_T = ["strokes_mean", "junction_deg3", "loops_0", "share_letters_with_detached_mark"]

def bitmaps(glyphs, ref):
    hs = [p.shape[0] for _, _, p in glyphs]; k = ref["height_median"] * SIZE / float(np.median(hs))
    out = []
    for i, (_, _, p) in enumerate(glyphs):
        im = cv2.resize(p.astype("uint8") * 255, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) > 127
        c = np.zeros((CELL * 2, CELL * 2), bool); h, w = im.shape
        y0 = int(CELL * 1.2) - h; x0 = int(CELL * 0.6)
        c[y0:y0 + h, x0:x0 + w] = im; out.append((str(i), c))
    return out, CELL * 1.2

def main():
    res = {}
    for name, (f, script, dil, minh, reg) in CHARTS.items():
        gl = cut(U + f, dil, minh, region=reg); ref = meas[script]["summary"]
        bm = bitmaps(gl, ref); measure.glyph_bitmaps = topology.glyph_bitmaps = lambda n, bm=bm: bm
        rows, _ = measure.measure("x"); m = measure.summarise(rows); t = topology.run("x")
        sw = float(np.mean([r["stroke_w"] for r in rows]))
        res[name] = dict(script=script, n=len(gl), stroke_w=sw, **{k: m[k] for k in KEYS_M}, **{k: t[k] for k in KEYS_T})
    for s in ("Katakana", "Hiragana"):
        res["font " + s] = dict(script=s, n=0, stroke_w=meas[s]["summary"]["stroke_w"], **{k: meas[s]["summary"][k] for k in KEYS_M}, **{k: topo[s][k] for k in KEYS_T})
    json.dump(res, open(os.path.join(HERE, "chart_measurements.json"), "w"), indent=1)
    cols = ["n", "stroke_w"] + KEYS_M + KEYS_T
    print("%-34s" % "" + " ".join(c[:9].rjust(9) for c in cols))
    for k, v in res.items():
        print("%-34s" % k + " ".join(("%9.2f" % v[c]) for c in cols))
main()
