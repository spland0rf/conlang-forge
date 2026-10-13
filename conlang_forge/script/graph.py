"""Stroke-graph topology of a glyph, computed from its strokes (style independent: always the angular control polyline).
Contacts (crossings, T-joins, end-to-end joins) become nodes; strokes between nodes become edges. We read off free ends,
junction degrees, loops (cycle rank) and detached marks: the connectivity the grammar is built on.
Also the glyph-to-glyph distance used to keep letters distinguishable."""
from __future__ import annotations

import math

from .geometry import flatten, length, sample

TOL = 0.07          # strokes closer than this are considered touching


def _seg_point(p, a, b):
    """Nearest point on segment ab to p: (distance, t along the segment 0..1)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d2 = dx * dx + dy * dy
    t = 0.0 if d2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / d2))
    q = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - q[0], p[1] - q[1]), t, q


def _seg_cross(a, b, c, d):
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-12:
        return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    if 0 <= t <= 1 and 0 <= u <= 1:
        return t, u, (a[0] + t * r[0], a[1] + t * r[1])
    return None


def _cum(pts):
    out, acc = [0.0], 0.0
    for i in range(len(pts) - 1):
        acc += math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        out.append(acc)
    return out


def _pos(pts, cum, seg, t):
    return cum[seg] + t * (cum[seg + 1] - cum[seg])


def analyse(strokes):
    """-> dict(parts, ends, junctions [degrees], loops, edges, marks). Dots and tiny detached strokes are marks."""
    lines = [s for s in strokes if not s.get("dot")]
    dots = len(strokes) - len(lines)
    polys = [flatten(s, 0.0) for s in lines]
    cums = [_cum(p) for p in polys]
    closed = [bool(s.get("closed")) for s in lines]
    n = len(lines)
    contacts = []                           # (point, stroke i, pos i, stroke j, pos j)
    for i in range(n):
        for j in range(i + 1, n):
            found = []
            for a in range(len(polys[i]) - 1):
                for b in range(len(polys[j]) - 1):
                    c = _seg_cross(polys[i][a], polys[i][a + 1], polys[j][b], polys[j][b + 1])
                    if c:
                        found.append((c[2], _pos(polys[i], cums[i], a, c[0]), _pos(polys[j], cums[j], b, c[1])))
            for (si, sj) in ((i, j), (j, i)):               # an end of one stroke lying on the other
                if closed[si]:
                    continue
                for end in (0, len(polys[si]) - 1):
                    e = polys[si][end]
                    best = None
                    for b in range(len(polys[sj]) - 1):
                        d, t, q = _seg_point(e, polys[sj][b], polys[sj][b + 1])
                        if d <= TOL and (best is None or d < best[0]):
                            best = (d, b, t, q)
                    if best:
                        pe = 0.0 if end == 0 else cums[si][-1]
                        pj = _pos(polys[sj], cums[sj], best[1], best[2])
                        found.append((best[3], pe, pj) if si == i else (best[3], pj, pe))
            for pt, pi, pj in found:
                contacts.append((pt, i, pi, j, pj))
    # cluster contact points spatially into nodes
    parent = list(range(len(contacts)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a in range(len(contacts)):
        for b in range(a + 1, len(contacts)):
            if math.hypot(contacts[a][0][0] - contacts[b][0][0], contacts[a][0][1] - contacts[b][0][1]) <= TOL * 1.2:
                parent[find(a)] = find(b)
    nodes = {}                                       # node id -> {stroke: set(positions)}
    for k, c in enumerate(contacts):
        d = nodes.setdefault(find(k), {})
        d.setdefault(c[1], set()).add(round(c[2], 3))
        d.setdefault(c[3], set()).add(round(c[4], 3))
    # per stroke: ordered node positions
    stroke_nodes = [[] for _ in range(n)]
    for nid, d in nodes.items():
        for si, poss in d.items():
            stroke_nodes[si].append((sum(poss) / len(poss), nid))
    free_ends = 0
    edges = 0
    deg = {}
    vertices = set(nodes)
    uf = {}

    def uf_find(x):
        uf.setdefault(x, x)
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x
    comp_roots = set()
    for i in range(n):
        L = cums[i][-1]
        seq = sorted(stroke_nodes[i])
        ids = []
        if not closed[i]:
            for end, pos in (("a", 0.0), ("b", L)):
                if not any(abs(p - pos) <= TOL * 1.5 for p, _ in seq):
                    free_ends += 1
                    vid = ("end", i, end)
                    vertices.add(vid)
                    seq.append((pos, vid))
            seq.sort()
        # merge nodes closer than TOL along the stroke (a node reported twice)
        merged = []
        for pos, nid in seq:
            if merged and merged[-1][1] == nid:
                continue
            merged.append((pos, nid))
        if closed[i]:
            if len(merged) == 0:
                edges += 1
                vid = ("ring", i)
                vertices.add(vid)
                deg[vid] = 2
                uf_find(vid)
                continue
            seq2 = merged + [merged[0]]
        else:
            seq2 = merged
        for a in range(len(seq2) - 1):
            u, v = seq2[a][1], seq2[a + 1][1]
            edges += 1
            deg[u] = deg.get(u, 0) + 1
            deg[v] = deg.get(v, 0) + 1
            uf[uf_find(u)] = uf_find(v)
        if len(seq2) == 1:
            uf_find(seq2[0][1])
    V = len([v for v in vertices if v in deg or True])
    for v in vertices:
        uf_find(v)
    C = len({uf_find(v) for v in vertices})
    loops = max(0, edges - len(vertices) + C) if edges else 0
    junctions = sorted(d for v, d in deg.items() if d >= 3)
    return {"parts": C, "ends": free_ends, "junctions": junctions, "loops": loops, "edges": edges, "marks": dots}


def signature(strokes):
    a = analyse(strokes)
    return (min(a["loops"], 3), min(a["ends"], 6), tuple(min(d, 4) for d in a["junctions"]), min(a["parts"], 3))


def points(strokes, roundness=0.0, step=0.05):
    pts = []
    for s in strokes:
        pts += sample(flatten(s, roundness), step)
    return pts


def _nn(a, b):
    out = []
    for p in a:
        best = 9.0
        for q in b:
            d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
            if d < best:
                best = d
        out.append(math.sqrt(best))
    return out


def distance(pa, pb):
    """Symmetric 90th-percentile nearest-point distance (in em units, x-height = 1). Sensitive to a single extra stroke."""
    def q90(v):
        v = sorted(v)
        return v[min(len(v) - 1, int(0.9 * len(v)))]
    return max(q90(_nn(pa, pb)), q90(_nn(pb, pa)))
