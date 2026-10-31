"""Colour-aware topology capture, strictly inside each glyph's green box.
   black/blue = base glyph, red/green = modifier strokes, purple = bar and its descenders, small round red/purple blobs = anchor dots.
   Round trip: drawn glyph -> spec (nodes, coloured typed strokes, anchors, bar) -> render -> re-extract -> compare.   python topo4.py 1"""
import glob, json, math, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize
import networkx as nx
from boxes import classes, find_box
from topo2 import PAGES, glyph_boxes, pix_graph, contract, classify
from topo3 import rdp, metrics

RGB = {"blue": (0, 100, 220), "black": (20, 20, 20), "red": (220, 30, 30), "green": (60, 150, 40), "purple": (150, 40, 150)}

def drop_long_green(green):
    """remove the box lines: green runs longer than 38 px, horizontal or vertical"""
    out = green.copy()
    for k in (0, 1):
        g = green if k == 0 else green.T
        o = out if k == 0 else out.T
        for y in range(g.shape[0]):
            lab, n = ndi.label(g[y])
            for j in range(1, n + 1):
                xs = np.nonzero(lab == j)[0]
                if len(xs) > 38: o[y, xs] = False
    return ndi.binary_dilation(out, iterations=1) & green

def interior(a, bx, C):
    t, b_, l, r = find_box(C["green"], bx)
    x0, y0, x1, y1 = bx
    if None not in (t, b_, l, r) and l < x0 and r > x1 and t < y0 and b_ > y1:
        return (l + 7, t + 7, r - 7, b_ - 7), True
    return (x0 - 8, y0 - 70, x1 + 8, y1 + 8), False

def parts(a, C, rect):
    x0, y0, x1, y1 = rect; x0, y0 = max(0, x0), max(0, y0)
    sub = {k: v[y0:y1, x0:x1] for k, v in C.items()}
    sub["green"] = drop_long_green(sub["green"])
    return sub, (x0, y0, x1, y1)

def find_bar(purple, gtop):
    rows = []
    for y in range(purple.shape[0]):
        xs = np.nonzero(purple[y])[0]
        if len(xs) > 30: rows.append((len(xs), y, xs.min(), xs.max()))
    cand = [r for r in rows if r[1] <= gtop + 14]
    if not cand: return None
    ym = max(r[1] for r in cand); cand = [r for r in cand if r[1] >= ym - 7]
    return max(cand)

def dots_of(sub, bar):
    """small round red/purple blobs"""
    d = []
    for k in ("red", "purple"):
        m = sub[k].copy()
        if bar: m[max(0, bar[1] - 4):bar[1] + 5, :] = False
        lab, n = ndi.label(ndi.binary_dilation(m, iterations=2))
        for j in range(1, n + 1):
            ys, xs = np.nonzero(lab == j)
            if 25 < len(ys) < 420 and max(ys.max() - ys.min(), xs.max() - xs.min()) < 22: d.append((float(ys.mean()), float(xs.mean()), k))
    return d

def strokes_mask(sub, bar, dots):
    ink = {}
    for k in ("blue", "black", "red", "green", "purple"):
        m = sub[k].copy()
        if bar: m[max(0, bar[1] - 4):bar[1] + 5, :] = False          # the bar itself is a fixed node line, not a stroke
        for (dy, dx, kk) in dots:
            yy, xx = np.ogrid[:m.shape[0], :m.shape[1]]; m &= ~((yy - dy) ** 2 + (xx - dx) ** 2 < 11 ** 2) if kk == k else True
        ink[k] = m
    return ink

def colour_of(path, ink):
    votes = {k: sum(bool(ink[k][y, x]) for y, x in path[::2]) for k in ink}
    return max(votes, key=votes.get)

def extract_all(ink, merge=14):
    m = np.zeros_like(ink["blue"])
    for v in ink.values(): m |= v
    m = ndi.binary_dilation(m, iterations=2)
    sk = skeletonize(m); G = pix_graph(sk)
    for comp in list(nx.connected_components(G)):
        if len(comp) < 18: G.remove_nodes_from(comp)
    pos, edges = contract(G, merge)
    edges = [e for e in edges if not (e[0] == e[1] and len(e[2]) < 25)]
    changed = True
    while changed:
        changed = False; inc = {}
        for e in edges: inc.setdefault(e[0], []).append(e); inc.setdefault(e[1], []).append(e)
        for nd, es in inc.items():
            if len(es) == 2 and es[0] is not es[1] and es[0][0] != es[0][1] and es[1][0] != es[1][1]:
                e1, e2 = es; c1, c2 = colour_of(e1[2], ink), colour_of(e2[2], ink)
                if c1 != c2: continue                                        # a colour change is a real compound boundary: keep the node
                p1 = e1[2] if e1[1] == nd else e1[2][::-1]; p2 = e2[2] if e2[0] == nd else e2[2][::-1]
                u = e1[0] if e1[1] == nd else e1[1]; v = e2[1] if e2[0] == nd else e2[0]
                edges = [e for e in edges if e is not e1 and e is not e2] + [(u, v, p1 + p2[1:])]; changed = True; break
    deg = {}
    for u, v, p in edges: deg[u] = deg.get(u, 0) + 1; deg[v] = deg.get(v, 0) + 1
    edges = [(u, v, p) for u, v, p in edges if len(p) > 12 or (deg[u] > 1 and deg[v] > 1)]
    return pos, edges

def build_spec(pos, edges, ink, bar, bottom, dots, shape):
    L, by, bx0, bx1 = bar; W = max(1, bx1 - bx0); Hh = max(1, bottom - by)
    nrm = lambda p: [round((p[1] - bx0) / W, 3), round(1 - (p[0] - by) / Hh, 3)]
    used = sorted({u for u, v, p in edges} | {v for u, v, p in edges})
    dg = {}
    for u, v, p in edges: dg[u] = dg.get(u, 0) + 1; dg[v] = dg.get(v, 0) + 1
    spec = {"bar": [0, 1], "nodes": {int(k): nrm(pos[k]) for k in used},
            "on_bar": [int(k) for k in used if nrm(pos[k])[1] > 0.84 or (dg[k] == 1 and nrm(pos[k])[1] > 0.7)],
            "strokes": [{"a": int(u), "b": int(v), "type": classify(p)[0], "colour": colour_of(p, ink),
                         "pts": [nrm(pos[u])] + [nrm(q) for q in rdp([tuple(map(float, q)) for q in p[::2] + [p[-1]]], 3.0)][1:-1] + [nrm(pos[v])]} for u, v, p in edges],
            "anchors": [{"x": nrm(d[:2])[0], "y": nrm(d[:2])[1], "colour": d[2]} for d in dots]}
    return spec

def render(spec, size=(220, 200)):
    img = Image.new("RGB", size, "white"); d = ImageDraw.Draw(img); W, H = size
    X = lambda q: (30 + q[0] * (W - 60), 28 + (1 - q[1]) * (H - 56))
    d.line([(30, 28), (W - 30, 28)], fill=RGB["purple"], width=3)
    for s in spec["strokes"]:
        pts = [X(q) for q in s["pts"]]
        for _ in range(2):
            if s["type"] == "line" or len(pts) < 3: break
            new = [pts[0]]
            for a, b in zip(pts, pts[1:]): new += [(.75 * a[0] + .25 * b[0], .75 * a[1] + .25 * b[1]), (.25 * a[0] + .75 * b[0], .25 * a[1] + .75 * b[1])]
            pts = new + [pts[-1]]
        d.line(pts, fill=RGB[s["colour"]], width=5, joint="curve")
    for k in spec["on_bar"]:
        q = spec["nodes"][str(k)] if str(k) in spec["nodes"] else spec["nodes"][k]; d.line([X(q), (X(q)[0], 28)], fill=RGB["purple"], width=4)
    for q in spec["anchors"]:
        x, y = X((q["x"], q["y"])); d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=RGB[q["colour"]])
    return img

def run(n):
    base = glob.glob("/mnt/user-data/attachments/*/")[0]
    im = Image.open(base + PAGES[n] + "-image.jpg").convert("RGB"); a = np.asarray(im); C = classes(a)
    res = []; specs = {}
    for i, bx in enumerate(glyph_boxes(a)):
        rect, found = interior(a, bx, C); sub, (X0, Y0, X1, Y1) = parts(a, C, rect)
        bl = np.nonzero(sub['blue'].any(1))[0]; gtop = int(bl.min()) if len(bl) else sub['blue'].shape[0] // 2
        bar = find_bar(sub["purple"], gtop)
        if bar is None: res.append((i, a[Y0:Y1, X0:X1], None, None, None, False, found)); continue
        dots = dots_of(sub, bar); ink = strokes_mask(sub, bar, dots)
        any_ink = np.zeros_like(ink["blue"])
        for v in ink.values(): any_ink |= v
        rows = np.nonzero(any_ink.any(1))[0]; bottom = int(rows.max()) if len(rows) else bar[1] + 60
        pos, edges = extract_all(ink); m0 = metrics(pos, edges)
        spec = build_spec(pos, edges, ink, bar, bottom, dots, sub["blue"].shape)
        r = np.asarray(render(spec)); C2 = classes(r.astype(float)); ink2 = {k: C2[k] for k in ink}
        for k in ("red", "purple"): ink2[k] = ink2[k] & False                   # compare strokes only; dots and bar are drawn by the renderer
        rpos, redges = extract_all({**ink2, "purple": C2["purple"] & False})
        m1 = metrics(rpos, redges)
        osk = np.argwhere(skeletonize(any_ink)); opts = np.c_[(osk[:, 1] - bar[2]) / max(1, bar[3] - bar[2]), 1 - (osk[:, 0] - bar[1]) / max(1, bottom - bar[1])]
        rsk = np.argwhere(skeletonize(ink2["blue"] | ink2["black"] | ink2["green"] | ink2["red"])); rpts = np.c_[(rsk[:, 1] - 30) / 160.0, 1 - (rsk[:, 0] - 28) / 144.0]
        cham = float((cKDTree(rpts).query(opts)[0].mean() + cKDTree(opts).query(rpts)[0].mean()) / 2) if len(rpts) and len(opts) else 9.0
        m1["chamfer"] = round(cham, 3)
        ok = all(m0[k] == m1[k] for k in ("comps", "loops", "ends", "junctions")) and cham < 0.07
        specs[i] = spec; res.append((i, a[Y0:Y1, X0:X1], r, m0, m1, ok, found))
    return res, specs

if __name__ == "__main__":
    n = int(sys.argv[1]); res, specs = run(n); json.dump(specs, open(f"/home/claude/topo4_p{n}.json", "w"))
    cols = 3; W, H = 330, 150; M = Image.new("RGB", (cols * W, ((len(res) + cols - 1) // cols) * H), "white"); dm = ImageDraw.Draw(M); good = 0
    for k, (i, c, r, m0, m1, ok, found) in enumerate(res):
        t = Image.new("RGB", (c.shape[1] + 220, max(c.shape[0], 200)), "white"); t.paste(Image.fromarray(c), (0, 0))
        if r is not None: t.paste(Image.fromarray(r), (c.shape[1], 0))
        t.thumbnail((W - 6, H - 22)); M.paste(t, ((k % cols) * W, (k // cols) * H + 18))
        txt = f"{i} {'box' if found else 'nobox'} " + ("no bar" if m0 is None else f"{'OK' if ok else 'DIFF'} d{m1['chamfer']} o L{m0['loops']}J{m0['junctions']}E{m0['ends']}S{m0['strokes']} n L{m1['loops']}J{m1['junctions']}E{m1['ends']}S{m1['strokes']}")
        dm.text(((k % cols) * W + 2, (k // cols) * H + 2), txt, fill="green" if ok else "red"); good += ok
    M.save(f"/home/claude/topo4_p{n}.png"); print(f"page {n}: {good}/{len(res)}")
