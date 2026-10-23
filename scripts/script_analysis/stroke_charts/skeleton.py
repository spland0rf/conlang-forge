"""Draft strokes from a font outline: rasterise, thin to a centre-line, split the line at junctions, rejoin pieces that
continue in a straight-ish direction, simplify, and order them the way a hand would (connected strokes in sequence,
then top-to-bottom and left-to-right). Output strokes are already centre-lines in the glyph's unit box, so render with inset=0."""
import math
import numpy as np
import networkx as nx
from skimage.draw import polygon
from skimage.measure import approximate_polygon, label, regionprops
from skimage.morphology import skeletonize
from .common import glyph_polys

N = 200
PAD = 6


def raster(polys):
    img = np.zeros((N + 2 * PAD, N + 2 * PAD), bool)
    for poly in polys:
        xs = np.array([PAD + x * N for x, _ in poly])
        ys = np.array([PAD + (1 - y) * N for _, y in poly])
        rr, cc = polygon(ys, xs, img.shape)
        img[rr, cc] ^= True                                    # even-odd: counters stay empty
    return img


def _graph(sk):
    g = nx.Graph()
    ys, xs = np.nonzero(sk)
    pts = set(zip(ys.tolist(), xs.tolist()))
    for y, x in pts:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (dy or dx) and (y + dy, x + dx) in pts:
                    g.add_edge((y, x), (y + dy, x + dx))
    return g


def _paths(g):
    """Split into pixel paths between junctions/ends."""
    nodes = {n for n in g if g.degree(n) != 2}
    seen, out = set(), []
    for n in nodes:
        for m in g[n]:
            if (n, m) in seen:
                continue
            path = [n, m]
            seen.add((n, m))
            while path[-1] not in nodes:
                nxt = [k for k in g[path[-1]] if k != path[-2]]
                if not nxt:
                    break
                path.append(nxt[0])
            seen.add((path[-1], path[-2]))
            out.append(path)
    for comp in nx.connected_components(g):         # pure loops (rings) have no junction
        if not any(n in nodes for n in comp):
            start = next(iter(comp))
            path = [start]
            prev, cur = None, start
            while True:
                nxt = [k for k in g[cur] if k != prev]
                if not nxt or nxt[0] == start:
                    break
                prev, cur = cur, nxt[0]
                path.append(cur)
            out.append(path + [start])
    return out


def _dir(path, end, k=7):
    seg = path[-k:] if end else path[:k][::-1]
    (y0, x0), (y1, x1) = seg[0], seg[-1]
    return math.atan2(-(y1 - y0), x1 - x0)


def _ang(a, b):
    d = abs(a - b) % (2 * math.pi)
    return min(d, 2 * math.pi - d)


def _merge(paths, tol=math.radians(50)):
    """Join two paths that meet at a junction when one continues the other's direction."""
    paths = [list(p) for p in paths]
    changed = True
    while changed:
        changed = False
        ends = {}
        for i, p in enumerate(paths):
            ends.setdefault(p[0], []).append((i, 0))
            ends.setdefault(p[-1], []).append((i, 1))
        best = None
        for node, lst in ends.items():
            if len(lst) < 2:
                continue
            for a in range(len(lst)):
                for b in range(a + 1, len(lst)):
                    (i, ei), (j, ej) = lst[a], lst[b]
                    if i == j:
                        continue
                    da = _dir(paths[i], ei)
                    db = _dir(paths[j], ej)
                    turn = _ang(da, db + math.pi)               # 0 = straight through
                    if turn < tol and (best is None or turn < best[0]):
                        best = (turn, i, ei, j, ej)
        if best:
            _, i, ei, j, ej = best
            a = paths[i] if ei == 1 else paths[i][::-1]
            b = paths[j] if ej == 0 else paths[j][::-1]
            paths = [p for k, p in enumerate(paths) if k not in (i, j)] + [a + b[1:]]
            changed = True
    return paths


def _prune(paths, min_len):
    """Drop short spurs (a path with a free end that is much shorter than the glyph)."""
    deg = {}
    for p in paths:
        for e in (p[0], p[-1]):
            deg[e] = deg.get(e, 0) + 1
    return [p for p in paths if len(p) >= min_len or (deg[p[0]] == 1 and deg[p[-1]] == 1)]


def strokes_for(font, ch, tol=2.2, spur=.07, dot_area=.03):
    polys = glyph_polys(font, ch)
    if polys is None:
        return None
    img = raster(polys)
    lab = label(img)
    out, dots = [], []
    for rp in regionprops(lab):
        if rp.area / (N * N) < dot_area:                       # a dot: keep as a tiny mark
            cy, cx = rp.centroid
            dots.append([((cx - PAD) / N - .012, 1 - (cy - PAD) / N), ((cx - PAD) / N + .012, 1 - (cy - PAD) / N)])
            continue
        sk = skeletonize(lab == rp.label)
        g = _graph(sk)
        if not g:
            continue
        paths = _prune(_merge(_prune(_paths(g), int(spur * N))), int(spur * N))
        for p in paths:
            arr = approximate_polygon(np.array(p, float), tol)
            out.append([((x - PAD) / N, 1 - (y - PAD) / N) for y, x in arr])
    return order(out) + dots


def order(strokes):
    def start_first(s):
        a, b = s[0], s[-1]
        return s if (-a[1], a[0]) <= (-b[1], b[0]) else s[::-1]
    strokes = [start_first(s) for s in strokes]
    key = lambda s: (-round(s[0][1] * 5), s[0][0])
    left = sorted(strokes, key=key)
    done = []
    while left:
        if done:
            pts = [p for s in done for p in (s[0], s[-1])]
            touch = [s for s in left if any(math.hypot(p[0] - q[0], p[1] - q[1]) < .07 for p in (s[0], s[-1]) for q in pts)]
            nxt = touch[0] if touch else left[0]
        else:
            nxt = left[0]
        left.remove(nxt)
        done.append(nxt)
    return done
