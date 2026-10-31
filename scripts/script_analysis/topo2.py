"""Topology graph per drawn glyph: nodes = junctions, free ends, red anchor dots and bar contacts; edges = strokes (length, chord, turning -> line/curve/loop).
   python topo2.py 2     (Devanagari page 2; writes topo_p2.json and a check image)"""
import glob, json, math, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
import networkx as nx
from topo import masks

PAGES = {1: "b8241d0a", 2: "f06b4a5c", 3: "952333f4", "b1": "cdeed5b9", "b2": "fa305444", "b3": "89f2cafa", "b3b": "04c32bd4"}

def glyph_boxes(a, it=12):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    m = (b - r > 35) & (b > g - 8); m[:, :int(a.shape[1] * .55)] = False
    lab, k = ndi.label(ndi.binary_dilation(m, iterations=it))
    bx = [(s[1].start, s[0].start, s[1].stop, s[0].stop) for s in ndi.find_objects(lab) if s[0].stop - s[0].start > 60 and s[1].stop - s[1].start > 40]
    return sorted(bx, key=lambda t: (t[1] + t[3]))

def pix_graph(sk):
    P = set(zip(*np.nonzero(sk))); G = nx.Graph()
    for y, x in P:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (dy or dx) and (y + dy, x + dx) in P: G.add_edge((y, x), (y + dy, x + dx))
    return G

def contract(G, merge=14):
    nodes = [n for n in G if G.degree(n) != 2]
    for comp in nx.connected_components(G):
        if not any(G.degree(n) != 2 for n in comp): nodes.append(sorted(comp)[0])     # a closed ring has no junction: give it one
    # union nearby node pixels
    par = {n: n for n in nodes}
    def f(n):
        while par[n] != n: par[n] = par[par[n]]; n = par[n]
        return n
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if math.dist(a, b) < merge: par[f(a)] = f(b)
    groups = {}
    for n in nodes: groups.setdefault(f(n), []).append(n)
    nid = {}; pos = {}
    for k, (root, mem) in enumerate(groups.items()):
        for n in mem: nid[n] = k
        pos[k] = tuple(np.mean(mem, axis=0))
    edges = []; seen = set()
    for n in nodes:
        for nb in G[n]:
            if (n, nb) in seen: continue
            path = [n, nb]; seen.add((n, nb))
            while G.degree(path[-1]) == 2 and path[-1] not in nid:
                nxt = [q for q in G[path[-1]] if q != path[-2]][0]; path.append(nxt)
            seen.add((path[-1], path[-2]))
            if path[-1] in nid: edges.append((nid[n], nid[path[-1]], path))
    return pos, edges

def classify(path):
    pts = np.array(path, float)
    if len(pts) < 3: return "tick", 0
    d = np.diff(pts, axis=0); ang = np.unwrap(np.arctan2(d[:, 0], d[:, 1]))
    turn = float(np.degrees(ang[-1] - ang[0]))
    L = float(np.hypot(*d.T).sum()); chord = math.dist(path[0], path[-1])
    kind = "loop" if abs(turn) > 270 or (L > 20 and chord < .25 * L and abs(turn) > 200) else "line" if abs(turn) < 40 or chord / L > .93 else "curve"
    return kind, round(turn)

def analyse(a, box, pad=30):
    x0, y0, x1, y1 = box; x0 -= 4; y0 -= 40; x1 += 4; y1 += 4
    c = a[max(0, y0):y1, max(0, x0):x1]
    blue, red, purple = masks(c)
    lab_, k_ = ndi.label(ndi.binary_dilation(blue, iterations=10)); keepc = [i for i in range(1, k_ + 1) if (lab_ == i).sum() > 800]
    if keepc:
        big = max(keepc, key=lambda i: (lab_ == i).sum()); blue = blue & ndi.binary_dilation(lab_ == big, iterations=2)
    sk = skeletonize(blue)
    G = pix_graph(sk)
    pos, edges = contract(G)
    # drop spur edges (< 10 px) ending at a free end
    changed = True
    while changed:
        changed = False
        inc = {}
        for e in edges:
            inc.setdefault(e[0], []).append(e); inc.setdefault(e[1], []).append(e)
        for nd, es in inc.items():
            if len(es) == 2 and es[0] is not es[1] and es[0][0] != es[0][1] and es[1][0] != es[1][1]:
                e1, e2 = es
                p1 = e1[2] if e1[1] == nd else e1[2][::-1]; p2 = e2[2] if e2[0] == nd else e2[2][::-1]
                u = e1[0] if e1[1] == nd else e1[1]; v = e2[1] if e2[0] == nd else e2[0]
                edges = [e for e in edges if e is not e1 and e is not e2] + [(u, v, p1 + p2[1:])]
                changed = True; break
    deg = {}
    for u, v, p in edges: deg[u] = deg.get(u, 0) + 1; deg[v] = deg.get(v, 0) + 1
    keep = [(u, v, p) for u, v, p in edges if len(p) > 10 or (deg[u] > 1 and deg[v] > 1)]
    lab, k = ndi.label(ndi.binary_dilation(red, iterations=4)); dots = [tuple(np.array(ndi.center_of_mass(lab == i + 1))) for i in range(k)]
    out = {"nodes": {i: [round(p[1]), round(p[0])] for i, p in pos.items()}, "dots": [[round(d[1]), round(d[0])] for d in dots],
           "strokes": [{"a": u, "b": v, "len": len(p), "type": classify(p)[0], "turn": classify(p)[1]} for u, v, p in keep]}
    return c, sk, out, keep, pos, dots

if __name__ == "__main__":
    n = int(sys.argv[1]); base = glob.glob("/mnt/user-data/attachments/*/")[0]
    im = Image.open(base + PAGES[n] + "-image.jpg").convert("RGB"); a = np.asarray(im)
    res = {}; tiles = []
    for i, bx in enumerate(glyph_boxes(a)):
        c, sk, out, keep, pos, dots = analyse(a, bx)
        res[i] = out
        o = Image.new("RGB", c.shape[1::-1], "white"); d = ImageDraw.Draw(o)
        cols = {"line": (0, 0, 0), "curve": (0, 110, 220), "loop": (0, 160, 60), "tick": (120, 120, 120)}
        for (u, v, p), s in zip(keep, out["strokes"]):
            for y, x in p: d.point((x, y), fill=cols[s["type"]]); d.point((x + 1, y), fill=cols[s["type"]])
        for k_, p in pos.items(): d.ellipse((p[1] - 5, p[0] - 5, p[1] + 5, p[0] + 5), outline=(220, 0, 0), width=2)
        for dx, dy in out["dots"]: d.ellipse((dx - 6, dy - 6, dx + 6, dy + 6), fill=(200, 0, 200))
        both = Image.new("RGB", (c.shape[1] * 2, c.shape[0]), "white"); both.paste(Image.fromarray(c), (0, 0)); both.paste(o, (c.shape[1], 0)); both.thumbnail((330, 170)); tiles.append(both)
        print(i, len(out["nodes"]), "nodes", len(out["strokes"]), "strokes", [s["type"] for s in out["strokes"]])
    json.dump(res, open(f"/home/claude/topo_p{n}.json", "w"))
    cols_ = 3; W, H = 330, 175; M = Image.new("RGB", (cols_ * W, ((len(tiles) + cols_ - 1) // cols_) * H), "white"); dm = ImageDraw.Draw(M)
    for i, t in enumerate(tiles): M.paste(t, ((i % cols_) * W, (i // cols_) * H + 4)); dm.text(((i % cols_) * W + 2, (i // cols_) * H), str(i), fill="red")
    M.save(f"/home/claude/topo_p{n}.png")
