"""Topology graphs for scripts that have a font: render each letter, skeletonise, extract nodes + typed strokes, normalise to the glyph box,
   re-render from the spec and compare (same checks as the hand-drawn pipeline).   python font_topo.py hebrew"""
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize
from topo2 import classify
from topo3 import extract, metrics, rdp

FONT = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
SETS = {"hebrew": [(chr(c), f"U+{c:04X}") for c in list(range(0x5D0, 0x5EB))],
        "devanagari": [(chr(c), f"U+{c:04X}") for c in list(range(0x905, 0x914)) + list(range(0x915, 0x939))],
        "bengali": [(chr(c), f"U+{c:04X}") for c in list(range(0x985, 0x98D)) + list(range(0x98F, 0x991)) + list(range(0x993, 0x9A9)) + list(range(0x9AA, 0x9B1)) + [0x9B2] + list(range(0x9B6, 0x9BA))]}

def glyph_mask(ch, font, size=260):
    img = Image.new("L", (size * 2, size * 2), 0); d = ImageDraw.Draw(img); d.text((size // 2, size // 3), ch, font=font, fill=255)
    m = np.asarray(img) > 128; ys, xs = np.nonzero(m)
    if not len(ys): return None
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1], int(ys.min()), int(xs.min())

def spec_from(mask, y0=0, x0=0, S=None, top=0, left=0):
    # thin the (thick) glyph to a medial skeleton; bridge hairline gaps first
    pos, edges = extract(None, mask, merge=18)
    H, W = mask.shape; s = S or max(H, W)           # one shared scale and baseline for the whole set, so small letters (yod) stay small
    nrm = lambda p: [round((p[1] + x0 - left) / s, 3), round(1 - (p[0] + y0 - top) / s, 3)]
    used = sorted({u for u, v, p in edges} | {v for u, v, p in edges})
    return pos, edges, {"aspect": round(W / H, 3), "nodes": {int(k): nrm(pos[k]) for k in used},
        "strokes": [{"a": int(u), "b": int(v), "type": classify(p)[0], "pts": [nrm(pos[u])] + [nrm(q) for q in rdp([tuple(map(float, q)) for q in p[::3] + [p[-1]]], 4.0)][1:-1] + [nrm(pos[v])]} for u, v, p in edges]}

def render(spec, S=420):
    img = Image.new("L", (S, S), 255); d = ImageDraw.Draw(img); X = lambda q: (20 + q[0] * (S - 40), 20 + (1 - q[1]) * (S - 40))
    for s in spec["strokes"]:
        pts = [X(q) for q in s["pts"]]
        for _ in range(2):
            if s["type"] == "line" or len(pts) < 3: break
            new = [pts[0]]
            for a, b in zip(pts, pts[1:]): new += [(.75 * a[0] + .25 * b[0], .75 * a[1] + .25 * b[1]), (.25 * a[0] + .75 * b[0], .25 * a[1] + .75 * b[1])]
            pts = new + [pts[-1]]
        d.line(pts, fill=0, width=8, joint="curve")
    return img

if __name__ == "__main__":
    name = sys.argv[1]; font = ImageFont.truetype(FONT, 200); out = {}; tiles = []; good = 0
    G = {code: (ch, glyph_mask(ch, font)) for ch, code in SETS[name]}; G = {k: v for k, v in G.items() if v[1] is not None}
    top = min(v[1][1] for v in G.values()); bot = max(v[1][1] + v[1][0].shape[0] for v in G.values()); left = min(v[1][2] for v in G.values())
    SS = max(bot - top, max(v[1][2] + v[1][0].shape[1] for v in G.values()) - left)
    for ch, code in SETS[name]:
        if code not in G: continue
        m, y0, x0 = G[code][1]
        pos, edges, spec = spec_from(m, y0, x0, SS, top, left); m0 = metrics(pos, edges)
        r = render(spec); rm = np.asarray(r) < 128; rpos, redges = extract(None, rm, merge=18); m1 = metrics(rpos, redges)
        ok = all(m0[k] == m1[k] for k in ("comps", "loops", "ends", "junctions"))
        good += ok; out[code] = {"char": ch, **spec, "metrics": {k: v for k, v in m0.items() if k != "kinds"}}
        t = Image.new("RGB", (480, 260), "white"); g = Image.fromarray((~m * 255).astype(np.uint8)).convert("RGB"); g.thumbnail((230, 230)); t.paste(g, (5, 20)); t.paste(r.resize((240, 240)).convert("RGB"), (245, 10))
        g = None; ImageDraw.Draw(t).text((5, 2), f"{code} {'OK' if ok else 'DIFF'} L{m0['loops']}J{m0['junctions']}E{m0['ends']}S{m0['strokes']} | L{m1['loops']}J{m1['junctions']}E{m1['ends']}S{m1['strokes']}", fill=(0, 140, 0) if ok else (200, 0, 0))
        t.thumbnail((240, 130)); tiles.append(t)
    json.dump(out, open(f"/home/claude/graph_{name}.json", "w"), ensure_ascii=False)
    cols = 5; W, H = 240, 130; M = Image.new("RGB", (cols * W, ((len(tiles) + cols - 1) // cols) * H), "white")
    for i, t in enumerate(tiles): M.paste(t, ((i % cols) * W, (i // cols) * H))
    M.save(f"/home/claude/graph_{name}.png"); print(f"{name}: {good}/{len(tiles)} round-trip")
