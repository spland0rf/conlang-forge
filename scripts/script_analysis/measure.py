"""Structural measurements of each reference script (letters only, rendered from the fonts in corpus.py).
Everything is a ratio or a share, so scripts of different sizes are comparable. Writes measurements.json."""
import json
import math
import sys

import cv2
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

from corpus import SCRIPTS
from render import glyph_bitmaps

EM = 120.0


def components(bm):
    lab, n = ndi.label(bm, structure=np.ones((3, 3)))
    sizes = ndi.sum(bm, lab, range(1, n + 1))
    return lab, n, sizes


def holes(bm):
    """Enclosed counters: background regions not connected to the outside."""
    lab, n = ndi.label(~bm)
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    sizes = ndi.sum(~bm, lab, range(1, n + 1))
    return sum(1 for i in range(1, n + 1) if i not in border and sizes[i - 1] > 12)


def run_median(bm, axis):
    """Median length of ink runs along an axis (axis=1: horizontal runs = thickness of vertical strokes)."""
    runs = []
    arr = bm if axis == 1 else bm.T
    for row in arr:
        d = np.diff(np.r_[0, row.astype(np.int8), 0])
        s, e = np.where(d == 1)[0], np.where(d == -1)[0]
        runs += list(e - s)
    return float(np.median(runs)) if runs else 0.0


def skel_stats(bm):
    sk = skeletonize(bm)
    nb = ndi.convolve(sk.astype(int), np.ones((3, 3), int), mode="constant") - 1
    ends = int(((nb == 1) & sk).sum())
    junc = int(((nb >= 3) & sk).sum())
    # merge adjacent junction pixels into one junction
    jl, jn = ndi.label((nb >= 3) & sk, structure=np.ones((3, 3)))
    return sk, ends, jn


def orientation_shares(sk):
    """Share of skeleton pixels running horizontal / vertical / diagonal (structure tensor over a 7px window)."""
    ys, xs = np.nonzero(sk)
    if len(xs) < 8:
        return (0, 0, 0)
    f = sk.astype(float)
    gy, gx = np.gradient(ndi.gaussian_filter(f, 1.5))
    Jxx, Jyy, Jxy = (ndi.uniform_filter(a, 7) for a in (gx * gx, gy * gy, gx * gy))
    theta = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)           # gradient direction; stroke runs perpendicular
    ang = (np.degrees(theta[ys, xs]) + 90) % 180             # stroke angle: 0 = horizontal, 90 = vertical
    h = np.mean((ang < 20) | (ang > 160))
    v = np.mean(np.abs(ang - 90) < 20)
    return (float(h), float(v), float(1 - h - v))


def bend_angularity(bm):
    """Share of the total turning along stroke centre lines that happens at sharp bends (over 40 degrees) rather than smooth curves.
    Measured on the skeleton with a patch around every junction removed, so where strokes cross or meet (a loop crossing a stem, a T,
    the inside of a cup) the angle between the strokes does not count: only how each single stroke bends along its own length."""
    K = np.ones((3, 3), int)
    sk = skeletonize(bm)
    if sk.sum() < 8:
        return 0.0
    sw = max(2.0, float(bm.sum()) / sk.sum())                       # stroke width in pixels
    nb = ndi.convolve(sk.astype(int), K, mode="constant") - 1
    zone = ndi.binary_dilation((nb >= 3) & sk, structure=K, iterations=max(1, int(round(sw * 0.8))))
    lab, n = ndi.label(sk & ~zone, structure=K)
    step = max(3, int(round(sw * 1.3)))
    sharp = smooth = 0.0
    for i in range(1, n + 1):
        pts = {tuple(p) for p in np.argwhere(lab == i)}
        if len(pts) < 2 * step:
            continue
        deg = {p: sum((p[0] + dy, p[1] + dx) in pts for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)) for p in pts}
        cur = min(pts, key=lambda p: (deg[p], p))                   # an end if there is one
        order, seen = [cur], {cur}
        while True:
            nxt = [(p[0] + dy, p[1] + dx) for p in [order[-1]] for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                   if (dy, dx) != (0, 0) and (p[0] + dy, p[1] + dx) in pts and (p[0] + dy, p[1] + dx) not in seen]
            if not nxt:
                break
            c = min(nxt, key=lambda q: abs(q[0] - order[-1][0]) + abs(q[1] - order[-1][1]))
            order.append(c)
            seen.add(c)
        p = np.array(order[::step], float)
        if len(p) < 3:
            continue
        v = np.diff(p, axis=0)
        a = np.arctan2(v[:, 0], v[:, 1])
        d = np.abs((np.diff(a) + np.pi) % (2 * np.pi) - np.pi)
        sharp += d[d > np.radians(40)].sum()
        smooth += d[d <= np.radians(40)].sum()
    t = sharp + smooth
    return float(sharp / t) if t else 0.0


def joints(bm):
    """The junctions of the skeleton, told apart: (crossings, t_joins, sharp_t_joins).
    A crossing has four arms that pair up into two nearly straight lines (a loop crossing a stem). A T or Y join has three arms: two form
    the body of one stroke and the third is the end of another stroke landing on it; it is sharp when that end has to turn more than
    40 degrees to run on along the body (a tangent join, where an end slides into a curve, is smooth)."""
    K = np.ones((3, 3), int)
    sk = skeletonize(bm)
    if sk.sum() < 8:
        return 0, 0, 0
    sw = max(2.0, float(bm.sum()) / sk.sum())
    nb = ndi.convolve(sk.astype(int), K, mode="constant") - 1
    jn = (nb >= 3) & sk
    zone = ndi.binary_dilation(jn, structure=K, iterations=max(1, int(round(sw * 0.8))))
    zlab, nz = ndi.label(zone, structure=K)
    ring = ndi.binary_dilation(zone, structure=K) & sk & ~zone
    crossings = tj = sharp = 0
    for i in range(1, nz + 1):
        zi = zlab == i
        if not (zi & jn).any():
            continue
        cy, cx = np.argwhere(zi & sk).mean(0)
        arms = ndi.label(ring & ndi.binary_dilation(zi, structure=K, iterations=2), structure=K)
        dirs = []
        for a in range(1, arms[1] + 1):
            py, px = np.argwhere(arms[0] == a).mean(0)
            dirs.append(math.atan2(py - cy, px - cx))
        if len(dirs) < 3:
            continue
        ang = lambda p, q: abs((dirs[p] - dirs[q] + math.pi) % (2 * math.pi) - math.pi)        # the angle between two arms, 0..pi
        if len(dirs) == 4:
            pairs = [((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))]
            if any(ang(*a) > math.radians(140) and ang(*b) > math.radians(140) for a, b in pairs):
                crossings += 1
                continue
        if len(dirs) == 3:
            idx = [(0, 1, 2), (0, 2, 1), (1, 2, 0)]
            body = max(idx, key=lambda t: ang(t[0], t[1]))                                        # the two most opposite arms are the body
            e = body[2]
            tj += 1
            turn = min(math.pi - ang(e, body[0]), math.pi - ang(e, body[1]))
            sharp += turn > math.radians(40)
    return crossings, tj, sharp


def angularity(bm):
    return bend_angularity(bm)


def outline_angularity(bm):
    """(The old measure.) Share of total outline turning that happens at sharp corners (vs. smooth curves)."""
    cs, _ = cv2.findContours(bm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    sharp = smooth = 0.0
    for c in cs:
        c = c[:, 0, :].astype(float)
        if len(c) < 30:
            continue
        step = max(3, len(c) // 40)
        p = c[::step]
        v = np.roll(p, -1, 0) - p
        a = np.arctan2(v[:, 1], v[:, 0])
        d = np.abs((np.roll(a, -1) - a + np.pi) % (2 * np.pi) - np.pi)
        sharp += d[d > np.radians(40)].sum()
        smooth += d[d <= np.radians(40)].sum()
    t = sharp + smooth
    return float(sharp / t) if t else 0.0


def topline(bm):
    ys, xs = np.nonzero(bm)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    h, w = y1 - y0 + 1, x1 - x0 + 1
    band = bm[y0:y0 + max(3, int(h * 0.12)), x0:x1 + 1]
    return float(band.any(axis=0).mean()), float(bm[max(y0, y1 - max(3, int(h * 0.12))):y1 + 1, x0:x1 + 1].any(axis=0).mean())


def normalise(bm, n=32):
    ys, xs = np.nonzero(bm)
    c = bm[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8) * 255
    h, w = c.shape
    s = max(h, w)
    pad = np.zeros((s, s), np.uint8)
    pad[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = c
    return cv2.GaussianBlur(cv2.resize(pad, (n, n), interpolation=cv2.INTER_AREA), (0, 0), 1.2).astype(float) / 255


def shape_distance(a, b):
    return float(np.sqrt(((a - b) ** 2).mean()) / (np.sqrt((a ** 2).mean()) + np.sqrt((b ** 2).mean()) + 1e-9) * 2)


def measure(name):
    gl, base = glyph_bitmaps(name)
    rows, shapes, chars = [], [], []
    for ch, bm in gl:
        if bm.sum() < 20:
            continue
        lab, n, sizes = components(bm)
        main = bm
        if n > 1:                                   # drop detached marks for the body measurements
            keep = (sizes >= 0.25 * sizes.max())
            main = np.isin(lab, [i + 1 for i in range(n) if keep[i]])
        ys, xs = np.nonzero(main)
        top, bot = ys.min(), ys.max() + 1
        w, h = xs.max() - xs.min() + 1, bot - top
        sk, ends, junc = skel_stats(main)
        hr, vr = run_median(main, 1), run_median(main, 0)
        hs, vs, ds = orientation_shares(sk)
        tl, bl = topline(main)
        ink = int(main.sum())
        jt = joints(main)
        m = main[:, xs.min():xs.max() + 1]
        sym_lr = float((m & m[:, ::-1]).sum() / max((m | m[:, ::-1]).sum(), 1))
        rows.append(dict(
            ch=ch, w=w / EM, h=h / EM, aspect=w / h, above=(base - top) / EM, below=(bot - base) / EM,
            parts=int(n), marks=int(sum(sizes < 0.25 * sizes.max())) if n > 1 else 0,
            holes=holes(main), ends=ends, junctions=junc, skel_len=int(sk.sum()) / EM,
            stroke_w=ink / max(sk.sum(), 1) / EM, fill=ink / (w * h), contrast=(vr / hr) if hr else 1.0,
            horiz=hs, vert=vs, diag=ds, angular=angularity(main), crossings=jt[0], tjoins=jt[1], tsharp=jt[2], topbar=tl, basebar=bl, symlr=sym_lr))
        shapes.append(normalise(main)); chars.append(ch)
    # distinctiveness: nearest-neighbour shape distance between letters of the same script
    S = np.array(shapes)
    n = len(S)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            D[i, j] = D[j, i] = shape_distance(S[i], S[j])
    np.fill_diagonal(D, 9)
    nn = D.min(1)
    close = sorted(((D[i, j], chars[i], chars[j]) for i in range(n) for j in range(i + 1, n)))[:5]
    return rows, dict(nn_mean=float(nn.mean()), nn_min=float(nn.min()), nn_p10=float(np.percentile(nn, 10)),
                      closest=[(round(d, 3), a, b) for d, a, b in close])


def summarise(rows):
    f = lambda k: np.array([r[k] for r in rows], float)
    base_h = np.median(f("h"))
    return dict(
        letters=len(rows),
        height_median=round(float(base_h), 3), height_cv=round(float(f("h").std() / f("h").mean()), 3),
        width_median=round(float(np.median(f("w"))), 3), aspect_median=round(float(np.median(f("aspect"))), 2),
        aspect_cv=round(float(f("aspect").std() / f("aspect").mean()), 2),
        above_med=round(float(np.median(f("above"))), 3), above_p90=round(float(np.percentile(f("above"), 90)), 3),
        below_p90=round(float(np.percentile(f("below"), 90)), 3),
        share_descending=round(float((f("below") > 0.12).mean()), 2),
        share_tall=round(float((f("above") > np.median(f("above")) * 1.25).mean()), 2),
        parts_mean=round(float(f("parts").mean()), 2), share_with_marks=round(float((f("marks") > 0).mean()), 2),
        holes_mean=round(float(f("holes").mean()), 2), share_closed=round(float((f("holes") > 0).mean()), 2),
        ends_mean=round(float(f("ends").mean()), 2), junctions_mean=round(float(f("junctions").mean()), 2),
        stroke_w=round(float(np.median(f("stroke_w"))), 3), fill=round(float(np.median(f("fill"))), 2),
        contrast=round(float(np.median(f("contrast"))), 2),
        horiz=round(float(f("horiz").mean()), 2), vert=round(float(f("vert").mean()), 2), diag=round(float(f("diag").mean()), 2),
        angular=round(float(f("angular").mean()), 2),
        crossings_mean=round(float(f("crossings").mean()), 2), tjoins_mean=round(float(f("tjoins").mean()), 2),
        tsharp_share=round(float(f("tsharp").sum() / max(1.0, f("tjoins").sum())), 2),
        share_topbar=round(float((f("topbar") > 0.8).mean()), 2), share_basebar=round(float((f("basebar") > 0.8).mean()), 2),
        symlr=round(float(f("symlr").mean()), 2))


if __name__ == "__main__":
    out = {}
    for n in SCRIPTS:
        rows, dist = measure(n)
        out[n] = dict(summary=summarise(rows), distinct=dist, dir=SCRIPTS[n]["dir"])
        print(n, out[n]["summary"]["letters"], file=sys.stderr)
    json.dump(out, open("measurements.json", "w"), indent=1, ensure_ascii=False)
