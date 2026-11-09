"""Turn one rectified photo patch (400x400 = the 100x100 frame) of the owner's hand-drawn letter into a stroke graph.
Colours: blue = body stroke, green = second stroke, orange open curve = accent, purple = bar; red blob = 'red' junction; orange ring = 'touch' junction."""
import cv2, numpy as np, math
from skimage.morphology import skeletonize
from scipy import ndimage as ndi
K = 4.0                                                                    # px per frame unit

def masks(P):
    hsv = cv2.cvtColor(cv2.GaussianBlur(P, (5, 5), 0), cv2.COLOR_BGR2HSV); H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    Sbg = cv2.medianBlur(S, 61); rel = S.astype(np.int16) - Sbg.astype(np.int16)                            # saturation above the local paper level
    ok = (rel > 22) & (V > 55)
    m = {"blue": ok & (H >= 90) & (H <= 120), "green": ok & (H >= 30) & (H <= 70), "orange": (rel > 16) & (V > 110) & (H >= 7) & (H <= 26),
         "purple": ok & (H >= 146) & (H <= 172), "red": ok & ((H <= 6) | (H >= 173)) & (S > 100)}
    k = np.ones((3, 3), np.uint8)
    return {c: cv2.morphologyEx(cv2.morphologyEx(v.astype(np.uint8) * 255, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, np.ones((9, 9) if c != "orange" else (5, 5), np.uint8)) for c, v in m.items()}

def blobs(mask, amin):
    n, lab, st, cen = cv2.connectedComponentsWithStats(mask); return [(tuple(cen[i]), st[i, 4], lab == i) for i in range(1, n) if st[i, 4] >= amin]

def _circle3(p, q, r):
    ax, ay = p; bx, by = q; cx, cy = r; d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-6: return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return ux, uy, math.hypot(ax - ux, ay - uy)

def rings(orange, rmin=16, rmax=31, tol=3.2, span=250, tries=900, seed=1):
    """orange rings (touch junctions): circles whose circumference is mostly covered by orange skeleton, found by RANSAC (gaps and tails allowed).
    returns [(centre, radius)] and the orange mask with the ring bands erased"""
    rng = np.random.default_rng(seed); out = []; er = orange.copy()
    sk = skeletonize(orange > 0); ys, xs = np.nonzero(sk); P = np.c_[xs, ys].astype(float)
    alive = np.ones(len(P), bool)
    while alive.sum() > 25:
        idx = np.nonzero(alive)[0]; best = None
        for _ in range(tries):
            i = rng.choice(idx); near = idx[np.hypot(*(P[idx] - P[i]).T) < 2 * rmax]
            if len(near) < 3: continue
            j, k = rng.choice(near, 2, replace=False); c = _circle3(P[i], P[j], P[k])
            if c is None or not rmin <= c[2] <= rmax: continue
            d = np.hypot(P[idx, 0] - c[0], P[idx, 1] - c[1]); inl = idx[np.abs(d - c[2]) < tol]
            if len(inl) < 20: continue
            ang = np.arctan2(P[inl, 1] - c[1], P[inl, 0] - c[0]); cover = len(set(((ang + np.pi) / (2 * np.pi) * 36).astype(int) % 36)) * 10
            if cover >= span and (best is None or cover * len(inl) > best[0]): best = (cover * len(inl), c, inl)
        if best is None: break
        _, c, inl = best
        # refine by least squares on the inliers
        A = np.c_[2 * P[inl, 0], 2 * P[inl, 1], np.ones(len(inl))]; sol = np.linalg.lstsq(A, P[inl, 0] ** 2 + P[inl, 1] ** 2, rcond=None)[0]
        cx, cy = sol[0], sol[1]; r = math.sqrt(max(sol[2] + cx * cx + cy * cy, 1)); out.append(((float(cx), float(cy)), float(r)))
        alive[inl] = False
        dd = np.hypot(P[:, 0] - cx, P[:, 1] - cy); alive &= ~(np.abs(dd - r) < tol + 1)
        yy, xx = np.ogrid[:orange.shape[0], :orange.shape[1]]; D = np.hypot(xx - cx, yy - cy); er[np.abs(D - r) < 11] = 0
    return out, er

def skel_graph(mask):
    sk = skeletonize(mask > 0); ys, xs = np.nonzero(sk); S = set(zip(xs, ys))
    nb = lambda p: [(p[0] + dx, p[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and (p[0] + dx, p[1] + dy) in S]
    deg = {p: len(nb(p)) for p in S}; nodes = {p for p in S if deg[p] != 2}
    # merge adjacent node pixels into clusters
    lab = {}; cl = []
    for p in nodes:
        if p in lab: continue
        stack = [p]; c = []; lab[p] = len(cl)
        while stack:
            q = stack.pop(); c.append(q)
            for r in nb(q):
                if r in nodes and r not in lab: lab[r] = len(cl); stack.append(r)
        cl.append(c)
    cen = [np.mean(c, axis=0) for c in cl]; seen = set(); edges = []
    for p in nodes:
        for q in nb(p):
            if q in nodes and lab[q] == lab[p]: continue
            if (p, q) in seen: continue
            path = [p, q]; seen.add((p, q)); cur, prev = q, p
            while cur not in nodes:
                nxt = [r for r in nb(cur) if r != prev]
                if not nxt: break
                prev, cur = cur, nxt[0]; path.append(cur)
            seen.add((cur, prev)); a = lab[p]; b = lab.get(cur, None)
            if b is None: b = len(cl); cl.append([cur]); cen.append(np.array(cur, float)); lab[cur] = b
            edges.append((a, b, np.array(path, float)))
    return cen, edges

def tangent(path, end, n=14):
    seg = path[:n] if end == 0 else path[::-1][:n]; v = seg[-1] - seg[0]; l = np.linalg.norm(v); return v / l if l else v

def strokes_from(mask, minlen=20, straight=-0.75):
    cen, edges = skel_graph(mask); edges = [e for e in edges if len(e[2]) >= 3 or e[0] != e[1]]
    # prune short spurs hanging off a junction
    deg = {}
    for a, b, p in edges: deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
    edges = [e for e in edges if not (len(e[2]) < 11 and (deg[e[0]] == 1) != (deg[e[1]] == 1))]
    inc = {}
    for i, (a, b, p) in enumerate(edges): inc.setdefault(a, []).append((i, 0)); inc.setdefault(b, []).append((i, 1))
    link = {}                                                              # (edge,end) -> (edge,end) joined straight through a node
    for n, L in inc.items():
        if len(L) < 2: continue
        cand = []
        for x in range(len(L)):
            for y in range(x + 1, len(L)):
                d = float(tangent(edges[L[x][0]][2], L[x][1]) @ tangent(edges[L[y][0]][2], L[y][1]))
                if d < straight: cand.append((d, L[x], L[y]))
        used = set()
        for d, u, v in sorted(cand):
            if u in used or v in used: continue
            used |= {u, v}; link[u] = v; link[v] = u
    out = []; done = set()
    for i, (a, b, p) in enumerate(edges):
        if i in done: continue
        # walk to one extremity of the chain
        cur, end = i, 0
        walked = {(cur, end)}
        while (cur, end) in link:
            nxt, ne = link[(cur, end)]; cur, end = nxt, 1 - ne
            if (cur, end) in walked: break                                  # closed cycle: start anywhere
            walked.add((cur, end))
        if cur == i and (cur, 0) in link and (cur, 1) in link: pass
        chain = []; e, s = cur, end                                       # s = end where we start reading
        seen = set()
        while e not in seen:
            seen.add(e); path = edges[e][2]; chain.append(path if s == 0 else path[::-1]); done.add(e)
            nxt = link.get((e, 1 - s))
            if nxt is None: break
            e, s = nxt[0], nxt[1]
        pl = np.vstack(chain)
        if len(pl) >= minlen: out.append(pl)
    return out

def simplify(pl, eps=2.2):
    ap = cv2.approxPolyDP(pl.astype(np.float32).reshape(-1, 1, 2), eps, False).reshape(-1, 2); return ap

def extract(P):
    M = masks(P); red = blobs(M["red"], 60); orr, orange_er = rings(M["orange"])
    strokes = []; width = {}
    # bridge the red dots into every colour so strokes that pass under a dot stay connected there
    redm = M["red"].copy(); redm = cv2.dilate(redm, np.ones((5, 5), np.uint8))
    for col, role in (("blue", "body"), ("green", "second"), ("purple", "struct"), ("orange", "accent")):
        m = M[col] if col != "orange" else orange_er; m = cv2.bitwise_or(m, redm) if col != "orange" else m
        for c, r in orr: cv2.circle(m, (int(c[0]), int(c[1])), int(r + 3), 0, -1) if col != "orange" and False else None
        for pl in strokes_from(m):
            if col == "orange":
                ln = np.linalg.norm(np.diff(pl, axis=0), axis=1).sum()
                near = any(min(math.dist(pl[0], c), math.dist(pl[-1], c)) < r + 18 for c, r in orr)            # an arm that really starts at a ring is kept
                if ln < (46 if near else 40): continue                                                         # stubs left where a ring was erased
            strokes.append((role, pl))
    return M, strokes, [c for c, a, _ in red], [c for c, r in orr]
if __name__ == "__main__":
    import sys
    P = cv2.imread(sys.argv[1]); M, st, red, orr = extract(P); vis = P.copy()
    for role, pl in st:
        col = {"body": (255, 0, 0), "second": (0, 160, 0), "accent": (0, 140, 255), "struct": (200, 0, 200)}[role]
        cv2.polylines(vis, [simplify(pl).astype(np.int32).reshape(-1, 1, 2)], False, (0, 0, 0), 5); cv2.polylines(vis, [simplify(pl).astype(np.int32).reshape(-1, 1, 2)], False, col, 2)
    for c in red: cv2.circle(vis, (int(c[0]), int(c[1])), 9, (0, 0, 255), 2)
    for c in orr: cv2.circle(vis, (int(c[0]), int(c[1])), 14, (0, 128, 255), 2)
    cv2.imwrite(sys.argv[2], np.hstack([P, vis])); print(len(st), "strokes", len(red), "red", len(orr), "rings")
