"""Round trip for one script page: drawn glyph -> topology spec (nodes + typed, simplified strokes, normalised to bar/baseline) -> re-rendered
   glyph -> topology re-extracted with the same pipeline -> compared with the original.   python topo3.py 2"""
import glob, json, math, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from topo import masks
from topo2 import PAGES, glyph_boxes, pix_graph, contract, classify
import networkx as nx

def rdp(pts, eps):
    if len(pts) < 3: return pts
    a, b = np.array(pts[0], float), np.array(pts[-1], float); ab = b - a; n = np.hypot(*ab) or 1e-9
    d = [abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / n for p in pts[1:-1]]
    i = int(np.argmax(d)) + 1
    if d[i - 1] > eps: return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [pts[0], pts[-1]]

def ink(c):
    blue, red, purple = masks(c)
    r, g, b = c[..., 0].astype(int), c[..., 1].astype(int), c[..., 2].astype(int)
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b); black = (mx < 100) & (mx - mn < 30)
    return blue, black, red, purple

def bar_of(c, gtop=None):
    r, g, b = c[..., 0].astype(int), c[..., 1].astype(int), c[..., 2].astype(int)
    best = None
    for lo, hi, rm in ((22, 75, 160), (12, 90, 190), (6, 110, 215)):
        purple = (r - g > lo) & (r - g < hi) & (r < rm) & (b - g > -14) & (b - r < 30)
        purple = ndi.binary_closing(purple, structure=np.ones((1, 7)))
        best = _longest(purple, gtop)
        if best and best[0] > 35: return best
    return best

def _longest(purple, gtop=None):
    rows = []
    for y in range(purple.shape[0]):
        xs = np.nonzero(purple[y])[0]
        if len(xs) > 25: rows.append((len(xs), y, xs.min(), xs.max()))
    if not rows: return None
    if gtop is not None:
        cand = [r for r in rows if r[1] <= gtop + 12]
        if cand:
            ymax = max(r[1] for r in cand); cand = [r for r in cand if r[1] >= ymax - 6]
            return max(cand)
    return max(rows)

def extract(c, mask, merge=14):
    sk = skeletonize(ndi.binary_dilation(mask, iterations=3)); G = pix_graph(sk)
    for comp in list(nx.connected_components(G)):
        if len(comp) < 25: G.remove_nodes_from(comp)
    pos, edges = contract(G, merge)
    edges = [e for e in edges if not (e[0] == e[1] and len(e[2]) < 25)]
    changed = True
    while changed:
        changed = False; inc = {}
        for e in edges: inc.setdefault(e[0], []).append(e); inc.setdefault(e[1], []).append(e)
        for nd, es in inc.items():
            if len(es) == 2 and es[0] is not es[1] and es[0][0] != es[0][1] and es[1][0] != es[1][1]:
                e1, e2 = es; p1 = e1[2] if e1[1] == nd else e1[2][::-1]; p2 = e2[2] if e2[0] == nd else e2[2][::-1]
                u = e1[0] if e1[1] == nd else e1[1]; v = e2[1] if e2[0] == nd else e2[0]
                edges = [e for e in edges if e is not e1 and e is not e2] + [(u, v, p1 + p2[1:])]; changed = True; break
    deg = {}
    for u, v, p in edges: deg[u] = deg.get(u, 0) + 1; deg[v] = deg.get(v, 0) + 1
    edges = [(u, v, p) for u, v, p in edges if len(p) > 12 or (deg[u] > 1 and deg[v] > 1)]
    return pos, edges

def metrics(pos, edges, dots=0):
    used = {u for u, v, p in edges} | {v for u, v, p in edges}
    G = nx.MultiGraph(); G.add_nodes_from(used); G.add_edges_from((u, v) for u, v, p in edges)
    comps = nx.number_connected_components(G) if used else 0
    loops = len(edges) - len(used) + comps
    ends = sum(1 for n in used if G.degree(n) == 1); junc = sum(1 for n in used if G.degree(n) >= 3)
    kinds = sorted(classify(p)[0] for u, v, p in edges)
    return {"comps": comps, "loops": loops, "ends": ends, "junctions": junc, "strokes": len(edges), "kinds": kinds}

def spec_of(pos, edges, bar, bottom, dots):
    L, by, bx0, bx1 = bar
    W = max(1, bx1 - bx0); Hh = max(1, bottom - by)
    nrm = lambda p: [round((p[1] - bx0) / W, 3), round((by - p[0]) / Hh * 1.0 + 1.0 - 1.0 + 0.0, 3) * -1 + 1.0 if False else round(1 - (p[0] - by) / Hh, 3)]
    used = sorted({u for u, v, p in edges} | {v for u, v, p in edges})
    dg = {}
    for u, v, p in edges: dg[u] = dg.get(u, 0) + 1; dg[v] = dg.get(v, 0) + 1
    top = lambda k: nrm(pos[k])[1] > 0.84 or (dg.get(k, 0) == 1 and nrm(pos[k])[1] > 0.7)
    return {"on_bar": [int(k) for k in used if top(k)], "nodes": {int(k): nrm(pos[k]) for k in used},
            "strokes": [{"a": int(u), "b": int(v), "type": classify(p)[0], "pts": [nrm(pos[u])] + [nrm(q) for q in rdp([tuple(map(float, q)) for q in p[::2] + [p[-1]]], 3.0)][1:-1] + [nrm(pos[v])]} for u, v, p in edges],
            "anchors": [nrm((d[0], d[1])) for d in dots],
            "bar_links": [{"x": nrm(d)[0], "y": nrm(d)[1], "to": min(used, key=lambda k: math.dist(nrm(pos[k]), nrm(d))) if used else None} for d in dots if nrm(d)[1] > 0.6]}

def render(spec, size=(220, 200)):
    img = Image.new("RGB", size, "white"); d = ImageDraw.Draw(img); W, H = size
    X = lambda q: (30 + q[0] * (W - 60), 28 + (1 - q[1]) * (H - 56))
    d.line([(30, 28), (W - 30, 28)], fill=(150, 40, 150), width=3)
    for s in spec["strokes"]:
        pts = [X(q) for q in s["pts"]]
        for _ in range(2):                                   # chaikin smoothing keeps the ends
            if s["type"] == "line" or len(pts) < 3: break
            new = [pts[0]]
            for a, b in zip(pts, pts[1:]): new += [(.75 * a[0] + .25 * b[0], .75 * a[1] + .25 * b[1]), (.25 * a[0] + .75 * b[0], .25 * a[1] + .75 * b[1])]
            pts = new + [pts[-1]]
        d.line(pts, fill=(0, 100, 220), width=5, joint="curve")
    for k in spec["on_bar"]:
        q = spec["nodes"][str(k)] if str(k) in spec["nodes"] else spec["nodes"][k]; d.line([X(q), (X(q)[0], 28)], fill=(0, 100, 220), width=5)
    for bl in spec.get("bar_links", []):
        if bl["to"] is None: continue
        nd = spec["nodes"].get(str(bl["to"])) or spec["nodes"].get(bl["to"]); x1_, y1_ = X((bl["x"], 1.0)); x2_, y2_ = X((bl["x"], bl["y"])); x3_, y3_ = X(nd)
        d.line([(x1_, y1_), (x2_, y2_), (x3_, y3_)], fill=(150, 40, 150), width=4)
    for q in spec["anchors"]: x, y = X(q); d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(220, 30, 30))
    return img

def run(n, only=None):
    base = glob.glob("/mnt/user-data/attachments/*/")[0]
    im = Image.open(base + PAGES[n] + "-image.jpg").convert("RGB"); a = np.asarray(im)
    out = []; specs = {}
    for i, bx in enumerate(glyph_boxes(a)):
        x0, y0, x1, y1 = bx; X0, Y0, X1, Y1 = max(0, x0 - 6), max(0, y0 - 75), x1 + 6, y1 + 6
        c = a[Y0:Y1, X0:X1]; blue, black, red, purple = ink(c)
        lab, k = ndi.label(ndi.binary_dilation(blue | black, iterations=8))
        if not k: continue
        core = ndi.binary_dilation(blue, iterations=10) if blue.any() else ndi.binary_dilation(black, iterations=10)
        keep = [j for j in range(1, k + 1) if (core & (lab == j)).any()]
        glyph = np.isin(lab, keep) & (blue | black)
        gx0, gy0 = x0 - X0, y0 - Y0
        win = np.zeros_like(glyph); win[max(0, gy0 - 4):gy0 + (y1 - y0) + 8, max(0, gx0 - 10):gx0 + (x1 - x0) + 10] = True
        bar = bar_of(c, gy0)
        if bar is not None: win[max(0, bar[1] - 2):, :] &= True; win[:max(0, bar[1] - 2), :] = False
        glyph &= win
        if bar is None: continue
        gy = np.nonzero(glyph)[0]; bottom = gy.max() if len(gy) else bar[1] + 80
        pos, edges = extract(c, glyph)
        rl, rk = ndi.label(ndi.binary_dilation(red, iterations=4)); dots = [ndi.center_of_mass(rl == j + 1) for j in range(rk)]
        spec = spec_of(pos, edges, bar, bottom, dots); m0 = metrics(pos, edges)
        L_, by_, bx0_, bx1_ = bar; Wn = max(1, bx1_ - bx0_); Hn = max(1, bottom - by_)
        osk = np.argwhere(skeletonize(glyph)); opts = np.c_[(osk[:, 1] - bx0_) / Wn, 1 - (osk[:, 0] - by_) / Hn]
        r = np.asarray(render(spec)); rb, rbk, _, _ = ink(r); rpos, redges = extract(r, rb | rbk); m1 = metrics(rpos, redges)
        rsk = np.argwhere(skeletonize(rb)); rpts = np.c_[(rsk[:, 1] - 30) / 160.0, 1 - (rsk[:, 0] - 28) / 144.0]
        from scipy.spatial import cKDTree
        cham = float((cKDTree(rpts).query(opts)[0].mean() + cKDTree(opts).query(rpts)[0].mean()) / 2) if len(rpts) and len(opts) else 9.0
        m1["chamfer"] = round(cham, 3)
        ok = all(m0[k_] == m1[k_] for k_ in ("comps", "loops", "ends", "junctions")) and cham < 0.06
        specs[i] = spec; out.append((i, c, r, m0, m1, ok))
    return out, specs

if __name__ == "__main__":
    n = int(sys.argv[1]); res, specs = run(n)
    json.dump(specs, open(f"/home/claude/topo3_p{n}.json", "w"))
    cols = 3; W, H = 330, 150; M = Image.new("RGB", (cols * W, ((len(res) + cols - 1) // cols) * H), "white"); dm = ImageDraw.Draw(M)
    good = 0
    for k, (i, c, r, m0, m1, ok) in enumerate(res):
        t = Image.new("RGB", (c.shape[1] + 220, max(c.shape[0], 200)), "white"); t.paste(Image.fromarray(c), (0, 0)); t.paste(Image.fromarray(r), (c.shape[1], 0)); t.thumbnail((W - 6, H - 22))
        M.paste(t, ((k % cols) * W, (k // cols) * H + 18))
        dm.text(((k % cols) * W + 2, (k // cols) * H + 2), f"{i} {'OK' if ok else 'DIFF'} d{m1['chamfer']} orig L{m0['loops']} J{m0['junctions']} E{m0['ends']} S{m0['strokes']} | new L{m1['loops']} J{m1['junctions']} E{m1['ends']} S{m1['strokes']}", fill="green" if ok else "red")
        good += ok
    M.save(f"/home/claude/topo3_p{n}.png"); print(f"{good}/{len(res)} glyphs round-trip with the same topology")
