"""Stroke-graph topology of every letter: the connectivity grammar.
A glyph = detached components. Each component's skeleton is a graph: nodes are stroke ends and junctions,
edges are strokes. We keep only connectivity: ends, junction degrees, loops, where on the glyph they sit, and
what detached marks sit where. Exact curve shape is deliberately ignored."""
import json
import sys
from collections import Counter

import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

from corpus import SCRIPTS
from render import glyph_bitmaps

K8 = np.ones((3, 3), int)


def graph(skel, spur):
    """Skeleton -> (ends, junction_degrees, strokes, loops, positions). Spurs shorter than `spur` px are removed."""
    sk = skel.copy()
    for _ in range(3):                                   # prune short spurs a few times
        nb = ndi.convolve(sk.astype(int), K8, mode="constant") - 1
        junc = (nb >= 3) & sk
        jl = ndi.binary_dilation(junc, structure=K8)
        seg, ns = ndi.label(sk & ~jl, structure=K8)
        ends = (nb == 1) & sk
        changed = False
        for i in range(1, ns + 1):
            m = seg == i
            if m.sum() < spur and (m & ends).any() and (ndi.binary_dilation(m, structure=K8) & jl).any():
                sk &= ~m; changed = True
        sk = skeletonize(sk)
        if not changed:
            break
    nb = ndi.convolve(sk.astype(int), K8, mode="constant") - 1
    junc = (nb >= 3) & sk
    jl = ndi.binary_dilation(junc, structure=K8) & sk
    jlab, nj = ndi.label(jl, structure=K8)
    seg, ns = ndi.label(sk & ~jl, structure=K8)
    ends = (nb == 1) & sk
    degs = []
    for j in range(1, nj + 1):
        touch = ndi.binary_dilation(jlab == j, structure=K8)
        degs.append(len(set(np.unique(seg[touch])) - {0}))
    keep = [d for d in degs if d >= 3]
    # isolated rings and pure-loop strokes: cycle rank from Euler characteristic of the skeleton
    lab, nc = ndi.label(sk, structure=K8)
    V = int(sk.sum()); E = int((ndi.convolve(sk.astype(int), np.array([[0, 0, 0], [0, 0, 1], [0, 0, 0]]), mode="constant") * sk).sum())
    # count cycles via holes in the filled complement: simplest robust route
    bg, nbg = ndi.label(~ndi.binary_dilation(sk, structure=K8) | False)
    border = set(np.unique(np.r_[bg[0], bg[-1], bg[:, 0], bg[:, -1]]))
    loops = sum(1 for i in range(1, nbg + 1) if i not in border)
    ys, xs = np.nonzero(sk)
    return dict(ends=int(ends.sum()), junctions=keep, strokes=int(ns), loops=loops,
                end_pos=[(int(y), int(x)) for y, x in zip(*np.nonzero(ends))],
                junc_pos=[tuple(map(int, np.mean(np.argwhere(jlab == j), 0))) for j in range(1, nj + 1)])


def zone(p, box):
    y0, y1, x0, x1 = box
    y = (p[0] - y0) / max(y1 - y0, 1); x = (p[1] - x0) / max(x1 - x0, 1)
    return "TMB"[min(2, int(y * 3))] + "LCR"[min(2, int(x * 3))]


def analyse(bm):
    lab, n = ndi.label(bm, structure=K8)
    sizes = np.array([(lab == i).sum() for i in range(1, n + 1)])
    ys, xs = np.nonzero(bm)
    gbox = (ys.min(), ys.max(), xs.min(), xs.max())
    main_i = int(np.argmax(sizes)) + 1
    parts = []
    for i in range(1, n + 1):
        m = lab == i
        py, px = np.nonzero(m)
        box = (py.min(), py.max(), px.min(), px.max())
        g = graph(skeletonize(m), spur=max(5, int(0.12 * max(box[1] - box[0], box[3] - box[2]))))
        parts.append(dict(main=(i == main_i), size=float(sizes[i - 1] / sizes.max()), box=box, **g))
    return gbox, parts


def signature(parts):
    """Connectivity signature of the main body: loops, ends, junction degrees (sorted), stroke count."""
    p = [q for q in parts if q["main"]][0]
    return (p["loops"], min(p["ends"], 6), tuple(sorted(min(d, 4) for d in p["junctions"])))


def mark_kind(q, main):
    (y0, y1, x0, x1), (my0, my1, mx0, mx1) = q["box"], main["box"]
    h, w = y1 - y0 + 1, x1 - x0 + 1
    cy = (y0 + y1) / 2
    where = "above" if cy < my0 + 0.15 * (my1 - my0) else "below" if cy > my1 - 0.15 * (my1 - my0) else "inside"
    shape = "dot" if max(h, w) < 0.3 * (my1 - my0) and max(h, w) / max(min(h, w), 1) < 2.2 else \
            "bar" if q["loops"] == 0 and q["junctions"] == [] and q["strokes"] <= 2 else "complex"
    return where, shape


def run(name):
    gl, base = glyph_bitmaps(name)
    sigs, marks, zones_j, zones_e, rows = [], Counter(), Counter(), Counter(), []
    for ch, bm in gl:
        if bm.sum() < 20:
            continue
        gbox, parts = analyse(bm)
        main = [q for q in parts if q["main"]][0]
        sigs.append(signature(parts))
        # attachment: a detached component that is NOT tiny is a second body (Arabic 2-part, Hangul syllable, etc.)
        for q in parts:
            if not q["main"]:
                marks[mark_kind(q, main)] += 1 if q["size"] < 0.25 else 0
        for q in parts:
            if q["main"]:
                for p in q["junc_pos"]:
                    zones_j[zone(p, q["box"])] += 1
                for p in q["end_pos"]:
                    zones_e[zone(p, q["box"])] += 1
        rows.append(dict(ch=ch, parts=len(parts), loops=sum(q["loops"] for q in parts if q["main"]),
                         ends=main["ends"], junctions=main["junctions"], strokes=main["strokes"], marks=sum(1 for q in parts if not q["main"] and q["size"] < 0.25)))
    c = Counter(sigs)
    n = len(sigs)
    uniq = sum(1 for s in sigs if c[s] == 1) / n
    pairs_same = sum(v * (v - 1) / 2 for v in c.values()) / (n * (n - 1) / 2)
    ent = -sum(v / n * np.log2(v / n) for v in c.values())
    tot_j = sum(zones_j.values()) or 1; tot_e = sum(zones_e.values()) or 1
    yz = lambda Z, t, k: round(sum(v for z, v in Z.items() if z[0] == k) / t, 2)
    xz = lambda Z, t, k: round(sum(v for z, v in Z.items() if z[1] == k) / t, 2)
    loops = Counter(r["loops"] for r in rows)
    return dict(
        letters=n, topology_classes=len(c), topology_entropy_bits=round(float(ent), 2),
        share_letters_topologically_unique=round(uniq, 2), share_pairs_same_topology=round(float(pairs_same), 3),
        loops_0=round(loops[0] / n, 2), loops_1=round(loops[1] / n, 2), loops_2plus=round(sum(v for k, v in loops.items() if k >= 2) / n, 2),
        strokes_mean=round(float(np.mean([r["strokes"] for r in rows])), 2),
        ends_mean=round(float(np.mean([r["ends"] for r in rows])), 2),
        junction_mean=round(float(np.mean([len(r["junctions"]) for r in rows])), 2),
        junction_deg3=round(sum(1 for r in rows for d in r["junctions"] if d == 3) / max(1, sum(len(r["junctions"]) for r in rows)), 2),
        junc_top=yz(zones_j, tot_j, "T"), junc_mid=yz(zones_j, tot_j, "M"), junc_bot=yz(zones_j, tot_j, "B"),
        end_top=yz(zones_e, tot_e, "T"), end_mid=yz(zones_e, tot_e, "M"), end_bot=yz(zones_e, tot_e, "B"),
        end_left=xz(zones_e, tot_e, "L"), end_right=xz(zones_e, tot_e, "R"),
        share_letters_with_detached_mark=round(sum(1 for r in rows if r["marks"]) / n, 2),
        mark_kinds={f"{a}/{b}": v for (a, b), v in marks.most_common(4)},
        top_signatures=[(s[0], s[1], list(s[2]), v) for s, v in c.most_common(6)],
    )


if __name__ == "__main__":
    out = {}
    for nme in SCRIPTS:
        out[nme] = run(nme)
        print(nme, file=sys.stderr)
    json.dump(out, open("topology.json", "w"), indent=1, ensure_ascii=False)
