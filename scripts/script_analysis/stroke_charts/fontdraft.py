"""Stroke drafts from a font, with the topology of the real letters. Three rules make it work:
1. Fill the outline by winding number, not even-odd. Fonts draw a stem and a ring as overlapping outlines; even-odd leaves little white squares at every
   overlap and the skeleton traces a diamond round each one.
2. Junction pixels within about a stroke width of each other form one junction site; at a site the arriving pieces are paired by direction
   (a stroke runs straight through a + or X, or along the bar of a T) and an unpaired piece ends on the site.
3. A run of vertical and horizontal segments is split into one stroke per segment (the hand-drawn charts do this); smooth curves stay whole.
Output strokes are centre-lines in the glyph's unit box (y up), so chart them with inset=0."""
import json
import math
import unicodedata
import warnings
import numpy as np
from skimage.measure import approximate_polygon, label, regionprops
from skimage.morphology import skeletonize
from . import skeleton as _sk
from .common import glyph_polys

warnings.filterwarnings("ignore")

def raster_nonzero(polys):
    """Ink as the union of the outline pieces that wind the outer way, minus the pieces that wind the other way (the holes). Fonts draw a stem and a
    ring as overlapping outlines; filling those even-odd leaves little white squares at every overlap, which became the skeleton's diamonds."""
    area = lambda pl: 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pl, pl[1:] + pl[:1]))
    areas = [area(p) for p in polys]
    outer = 1 if areas[int(np.argmax(np.abs(areas)))] > 0 else -1
    wn = np.zeros((_sk.N + 2 * _sk.PAD,) * 2, int)               # winding number: +1 inside an outer piece, -1 inside a hole piece
    for p, a_ in zip(polys, areas):
        wn += _sk.raster([p]).astype(int) * (1 if a_ * outer > 0 else -1)
    return wn > 0

def _unit(v):
    n = math.hypot(*v) or 1.0
    return (v[0] / n, v[1] / n)

def junction_strokes(g, sw, spur_px):
    """Strokes from a pixel skeleton graph, by the straight-through rule: junction pixels that sit within about a stroke width of each other are
    one junction site; at a site the incident pieces are paired by direction (a piece continues on the far side of a + or X, or of a T's top bar)
    and a piece left unpaired ends on the site (the stem of a T). The little loops the skeleton draws inside a site are dropped."""
    paths = _sk._paths(g)
    deg = dict(g.degree())
    jn = [n for n in g if deg[n] >= 3]
    R = 1.3 * sw
    site = {}                                                     # junction pixel -> site id (union by distance)
    sites = []
    for n in jn:
        for k, members in enumerate(sites):
            if any(math.dist(n, m) <= R for m in members):
                members.append(n); site[n] = k; break
        else:
            sites.append([n]); site[n] = len(sites) - 1
    merged = True                                                 # sites may touch only through a later pixel: merge until stable
    while merged:
        merged = False
        for i in range(len(sites)):
            for j in range(i + 1, len(sites)):
                if sites[i] and sites[j] and any(math.dist(p, q) <= R for p in sites[i] for q in sites[j]):
                    sites[i] += sites[j]; sites[j] = []; merged = True
    site = {n: k for k, mem in enumerate(sites) for n in mem}
    changed = True                                                # corners of a diamond: sites joined by a very short piece are one site
    while changed:
        changed = False
        for p in paths:
            a, b = site.get(p[0]), site.get(p[-1])
            if a is not None and b is not None and a != b and len(p) < 2.0 * sw:
                sites[a] += sites[b]; sites[b] = []
                for n in sites[a]: site[n] = a
                changed = True
    centre = {k: (float(np.mean([n[0] for n in mem])), float(np.mean([n[1] for n in mem]))) for k, mem in enumerate(sites) if mem}
    keep = []
    for p in paths:
        a, b = site.get(p[0]), site.get(p[-1])
        if a is not None and a == b and len(p) < 2.2 * R:           # a side of the diamond inside one junction site
            continue
        free = (a is None and deg.get(p[0], 2) == 1) or (b is None and deg.get(p[-1], 2) == 1)
        if free and (a is not None or b is not None) and len(p) < spur_px:      # a short spur off a junction
            continue
        keep.append(p)
    arms = {}                                                     # site -> [(path index, end)]
    for i, p in enumerate(keep):
        for e, n in ((0, p[0]), (1, p[-1])):
            if n in site:
                arms.setdefault(site[n], []).append((i, e))
    def direction(i, e):
        p = keep[i] if e == 0 else keep[i][::-1]
        k = min(len(p) - 1, int(0.8 * sw) + 2)
        c = centre[site[p[0]]]
        return _unit((p[k][0] - c[0], p[k][1] - c[1]))
    link = {}
    for k, arm in arms.items():
        ds = [direction(i, e) for i, e in arm]
        cos = lambda x, y: ds[x][0] * ds[y][0] + ds[x][1] * ds[y][1]
        pairs = []
        for x in range(len(arm)):
            for y in range(x + 1, len(arm)):
                if cos(x, y) < -0.15:                              # nearly opposite: one stroke running through
                    pairs.append((cos(x, y), x, y))
        used = set()
        for _, x, y in sorted(pairs):
            if x not in used and y not in used:
                used |= {x, y}; link[arm[x]] = arm[y]; link[arm[y]] = arm[x]
    out, seen = [], set()
    def walk(i, e):                                               # start at end e of piece i, follow links
        pts = []
        while True:
            seen.add(i)
            p = keep[i] if e == 0 else keep[i][::-1]
            pts += [tuple(map(float, q)) for q in p]
            far = (i, 1 - e)
            n = p[-1]
            if far in link:
                if n in site: pts.append(centre[site[n]])
                i, e = link[far]
                if i in seen: break
            else:
                if n in site: pts.append(centre[site[n]])
                break
        return pts
    for i, p in enumerate(keep):
        if i in seen:
            continue
        for e in (0, 1):
            if (i, e) not in link:
                out.append(walk(i, e)); break
    for i, p in enumerate(keep):                                  # loops with every end linked
        if i not in seen:
            out.append(walk(i, 0))
    return out

def strokes_for(font, ch, tol=2.2, spur=.07, dot_area=.03):
    polys = glyph_polys(font, ch)
    if polys is None:
        return None
    img = raster_nonzero(polys)
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
        sw = max(2.0, float((lab == rp.label).sum()) / max(1, int(sk.sum())))
        for pts in junction_strokes(g, sw, int(spur * N)):
            arr = approximate_polygon(np.array(pts, float), tol)
            out.append([((x - PAD) / N, 1 - (y - PAD) / N) for y, x in arr])
    return _sk.order(out) + dots

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



def letter_strokes(font, ch):
    st = strokes_for(font, ch)
    if st is None:
        return None
    return [p for s in st for p in (split(s) if len(s) > 2 else [s])]


def draft(font, chars, title, out_prefix, per_page=12):
    """Draft every character that the font has, save <out_prefix>.json and the chart pages <out_prefix>_N.png."""
    from .render import chart, save
    items = []
    for ch in chars:
        st = letter_strokes(font, ch)
        if not st:
            continue
        nm = unicodedata.name(ch, ch).split(" ")[-1].title()
        items.append((ch, nm, st))
    save(items, out_prefix + ".json")
    return chart(font, items, out_prefix, title, per_page=per_page, inset=0)
