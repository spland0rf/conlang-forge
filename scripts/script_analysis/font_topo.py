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

def find_bar(mask):
    """the headline: a long horizontal band in the top third. Returns (row_lo, row_hi, col_lo, col_hi) or None"""
    H, W = mask.shape; rows = []
    for y in range(int(H * .4)):
        xs = np.nonzero(mask[y])[0]
        if not len(xs): continue
        runs = np.split(xs, np.nonzero(np.diff(xs) > 1)[0] + 1); r = max(runs, key=len)
        if len(r) >= .55 * W: rows.append((y, r[0], r[-1]))
    if not rows: return None
    y0_ = rows[0][0]; band = [r for r in rows if r[0] - y0_ < 40 and r[0] - rows[0][0] <= len([q for q in rows if q[0] <= r[0]]) + 2]
    return band[0][0], band[-1][0], min(r[1] for r in band), max(r[2] for r in band)

THREE_FORMS = set('अआऑओऔ')                   # letters with a '3' on the left joined to a barred form on the right: the bar covers only the right form

def spec_from(mask, y0=0, x0=0, S=None, top=0, left=0, ch=''):
    # thin the (thick) glyph to a medial skeleton; bridge hairline gaps first
    bar = find_bar(mask); body = mask.copy()
    if bar: body[bar[0]:bar[1] + 2, :] = False         # the bar is drawn as one perfectly straight line, so thin only what hangs from it
    pos, edges = extract(None, body, merge=18)
    H, W = mask.shape; s = S or max(H, W)           # one shared scale and baseline for the whole set, so small letters (yod) stay small
    nrm = lambda p: [round((p[1] + x0 - left) / s, 3), round(1 - (p[0] + y0 - top) / s, 3)]
    used = sorted({u for u, v, p in edges} | {v for u, v, p in edges})
    sp = {"aspect": round(W / H, 3), "nodes": {int(k): nrm(pos[k]) for k in used},
        "strokes": [{"a": int(u), "b": int(v), "type": classify(p)[0], "pts": [nrm(pos[u])] + [nrm(q) for q in rdp([tuple(map(float, q)) for q in p[::3] + [p[-1]]], 4.0)][1:-1] + [nrm(pos[v])]} for u, v, p in edges]}
    if bar:
        by = (bar[0] + bar[1]) / 2; bn = nrm((by, 0))[1]; sp["bar"] = {"y": bn, "x0": nrm((0, bar[2]))[0], "x1": nrm((0, bar[3]))[0]}
        touch = {int(k) for k in used if pos[k][0] < bar[1] + 18}
        near = {int(k) for k in used if pos[k][0] < bar[1] + 48}          # ends within reach of the bar join it
        for k in touch: sp["nodes"][k][1] = bn
        sp["on_bar"] = sorted(touch)
        # the bar spans the form that carries it: the bar run plus every part joined to it; a part with no bar of its own (a joined letter form) is left out
        import networkx as nx
        Gc = nx.Graph(); Gc.add_edges_from((st["a"], st["b"]) for st in sp["strokes"])
        attached = set()
        for comp in nx.connected_components(Gc):
            if comp & near: attached |= comp
        # the bar covers the forms that hang from it: from the leftmost to the rightmost point that touches it, with the font's overhang. A part that only
        # joins the stem (the 3 of अ आ ओ औ) is not under the bar
        txs = [sp["nodes"][k][0] for k in touch]
        if txs:
            oh = min(0.06, max(0.0, sp["bar"]["x1"] - max(txs))); sp["bar"]["x0"] = round(min(txs) - oh, 3); sp["bar"]["x1"] = round(max(sp["bar"]["x1"], max(txs)), 3)
        sp["bar_free"] = sorted({st["a"] for st in sp["strokes"] if st["a"] not in attached})        # strokes of forms without a bar
        for st in sp["strokes"]:
            if st["a"] in touch: st["pts"][0][1] = bn
            if st["b"] in touch: st["pts"][-1][1] = bn
    # descenders: a nearly vertical straight stroke is made exactly vertical (perpendicular to the bar)
    for st in sp["strokes"]:
        a, b = st["pts"][0], st["pts"][-1]
        if st["type"] == "line" and abs(b[1] - a[1]) > 0 and abs(math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))) % 180 < 14 or (st["type"] == "line" and abs(math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))) % 180 > 166):
            x = round((a[0] + b[0]) / 2, 3); st["pts"] = [[x, a[1]], [x, b[1]]]; sp["nodes"][st["a"]][0] = x if st["a"] not in sp.get("on_bar", []) or True else sp["nodes"][st["a"]][0]; sp["nodes"][st["b"]][0] = x; st["vertical"] = True
    if ch in THREE_FORMS and sp.get("bar"):
        vs = [st for st in sp["strokes"] if st.get("vertical")]
        if vs:
            sx = max(st["pts"][0][0] for st in vs)
            sp["bar"]["x0"] = round(max(sp["bar"]["x0"], sx - 0.10), 3); sp["bar"]["x1"] = round(min(sp["bar"]["x1"] + .0, sx + 0.08) if sp["bar"]["x1"] > sx else sp["bar"]["x1"], 3)
            sp["bar_note"] = "bar covers only the right-hand form; the 3 hangs free of it"
    return pos, edges, sp

def render(spec, S=420):
    img = Image.new("L", (S, S), 255); d = ImageDraw.Draw(img); X = lambda q: (20 + q[0] * (S - 40), 20 + (1 - q[1]) * (S - 40))
    if spec.get("bar"):
        b = spec["bar"]; d.line([X((b["x0"], b["y"])), X((b["x1"], b["y"]))], fill=0, width=8)
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
        pos, edges, spec = spec_from(m, y0, x0, SS, top, left, ch); m0 = metrics(pos, edges)
        r = render(spec); rm = np.asarray(r) < 128
        if spec.get('bar'):
            yy = int(20 + (1 - spec['bar']['y']) * (420 - 40)); rm[yy - 6:yy + 7, :] = False
        rpos, redges = extract(None, rm, merge=18); m1 = metrics(rpos, redges)
        ok = all(m0[k] == m1[k] for k in ("comps", "loops", "ends", "junctions"))
        good += ok; out[code] = {"char": ch, **spec, "metrics": {k: v for k, v in m0.items() if k != "kinds"}}
        t = Image.new("RGB", (480, 260), "white"); g = Image.fromarray((~m * 255).astype(np.uint8)).convert("RGB"); g.thumbnail((230, 230)); t.paste(g, (5, 20)); t.paste(r.resize((240, 240)).convert("RGB"), (245, 10))
        g = None; ImageDraw.Draw(t).text((5, 2), f"{code} {'OK' if ok else 'DIFF'} L{m0['loops']}J{m0['junctions']}E{m0['ends']}S{m0['strokes']} | L{m1['loops']}J{m1['junctions']}E{m1['ends']}S{m1['strokes']}", fill=(0, 140, 0) if ok else (200, 0, 0))
        t.thumbnail((240, 130)); tiles.append(t)
    json.dump(out, open(f"/home/claude/graph_{name}.json", "w"), ensure_ascii=False)
    cols = 5; W, H = 240, 130; M = Image.new("RGB", (cols * W, ((len(tiles) + cols - 1) // cols) * H), "white")
    for i, t in enumerate(tiles): M.paste(t, ((i % cols) * W, (i // cols) * H))
    M.save(f"/home/claude/graph_{name}.png"); print(f"{name}: {good}/{len(tiles)} round-trip")
