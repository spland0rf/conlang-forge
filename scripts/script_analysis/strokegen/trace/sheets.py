"""Rectify every redrawn box from the owner's photos into patches/<id>.png (400x400 = the 100x100 frame).
Each photo lists its rows of (id,id,id) for the RIGHT-hand boxes; rows set to None are cut off in that photo."""
import cv2, numpy as np, os, glob, sys
from boxes import find, S
A = "/mnt/user-data/attachments/9df3cbd6-5590-5857-9ad9-4bf9abf1a96b/"
PHOTOS = {
 "p6": ("367d9df8", [["n001","n002","n003"],["n004","n005","n006"],["n007","n008","n009"],["n010","n011","n012"]]),
 "p5": ("17970468", [["n010","n011","n012"],["n013","n014","n015"],["n016","n017","n018"],["n019","n020","n021"]]),
 "p8": ("9af1eafe", [["n022","n023","n024"],["n025","n026","n027"],["n028","n029","n030"],None]),
 "p7": ("81a1133e", [["n031","n032","n033"],["n034","n035","n036"],["n037","n038","n039"],["n040","n041","n042"]]),
 "p2": ("c0ff1f68", [["m001","m002","m003"],["m004","m005","m007"],["m008","m009","m010"],["m011","m012","m013"]]),
 "p1": ("54e4ab3d", [None,["m011","m012","m013"],["m014","m017","m018"],["m019","m020","m021"]]),
 "p4": ("46fb5dd1", [["m023","m024","m025"],["m026","m027","m028"],["m029","m030","m031"],["m032","m033","m034"]]),
 "p3": ("0be65fc5", [None,["m026","m027","m028"],["m029","m030","m031"],["m032","m033","m034"],["m037","m038","m039"]]),
}
def run(pk):
    fn, rows = PHOTOS[pk]; im = cv2.imread(glob.glob(A + fn + "*")[0]); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV); allb = find(im); ink = []
    for x, y, w, h in allb:                                                 # the owner's boxes carry bright ink: they anchor the right-hand lattice
        P = hsv[y + 8:y + h - 8, x + 8:x + w - 8]
        if ((P[..., 1] > 90) & (P[..., 2] > 50)).sum() >= 1200: ink.append((x, y, w, h))
    w = float(np.median([b[2] for b in allb])); h = float(np.median([b[3] for b in allb])); xs = sorted(b[0] for b in ink); xref = xs[0]
    ds = [d for d in np.diff(xs) if d > 400]; P = float(np.median(ds)) if ds else 2.29 * w; ds = [d / round(d / P) for d in np.diff(xs) if d > 400] or [P]; P = float(np.median(ds))
    lat = []; 
    for b in allb:
        k = round((b[0] - xref) / P)
        if abs(b[0] - xref - k * P) < 70: lat.append((k, b))
    kmin = min(k for k, _ in lat); B = np.array([b for _, b in lat], float); col = np.array([k - kmin for k, _ in lat])
    first = next(i for i, r in enumerate(rows) if r); dy = []
    for c in set(col):
        yy = np.sort(B[col == c, 1]); dy += [v for v in np.diff(yy) if 250 < v < 520]
    pitch = float(np.median(dy)) if dy else 1.3 * h; row = np.round((B[:, 1] - B[:, 1].min()) / pitch).astype(int) + first
    M = np.column_stack([np.ones(len(B)), col, row]); cx = np.linalg.lstsq(M, B[:, 0], rcond=None)[0]; cy = np.linalg.lstsq(M, B[:, 1], rcond=None)[0]; out = {}
    for r, ids in enumerate(rows):
        if not ids: continue
        for c, i in enumerate(ids):
            x = int(cx @ [1, c, r]); y = int(cy @ [1, c, r]); hit = [b for b in B if abs(b[0] - x) < 60 and abs(b[1] - y) < 60]
            if hit: x, y = int(hit[0][0]), int(hit[0][1])
            x, y = max(0, x), max(0, y); crop = im[y:y + int(h), x:x + int(w)]
            if crop.size: out[i] = cv2.resize(crop, (S, S), interpolation=cv2.INTER_AREA)
    print(pk, len(ink), "ink boxes;", len(lat), "lattice; P", round(P), "pitch", round(pitch), "cols", sorted(set(col)), "->", len(out), "patches; residual", np.abs(M @ cx - B[:, 0]).max().round(1), np.abs(M @ cy - B[:, 1]).max().round(1))
    return out
if __name__ == "__main__":
    os.makedirs("patches", exist_ok=True); allp = {}
    for pk in PHOTOS:
        for i, p in run(pk).items():
            if i not in allp: allp[i] = p                                    # first photo wins; photos are ordered best-first
    for i, p in allp.items(): cv2.imwrite("patches/%s.png" % i, p)
    ids = sorted(allp); cols = 10; rows = -(-len(ids) // cols); sh = np.full((rows * 200, cols * 200, 3), 255, np.uint8)
    for n, i in enumerate(ids):
        t = cv2.resize(allp[i], (190, 190)); cv2.putText(t, i, (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1); sh[(n // cols) * 200:(n // cols) * 200 + 190, (n % cols) * 200:(n % cols) * 200 + 190] = t
    cv2.imwrite("patches_sheet.png", sh); print(len(ids), "patches")
