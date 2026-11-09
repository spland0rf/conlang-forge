"""trace every rectified patch: python3 batch.py  -> extracted/<id>.json and overlays/<id>.png"""
import os, sys, json, cv2, numpy as np
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
import ink
HERE = os.path.dirname(os.path.abspath(__file__))

def one(name):
    out = os.path.join(HERE, "extracted", name + ".json")
    if os.path.exists(out): return name, "cached"
    P = cv2.imread(os.path.join(HERE, "patches", name + ".png"))
    M, st, red, orr = ink.extract(P)
    json.dump({"strokes": [[r, ink.simplify(pl).round(1).tolist()] for r, pl in st], "red": [list(map(float, c)) for c in red],
               "rings": [list(map(float, c)) for c in orr]}, open(out, "w"))
    vis = P.copy()
    for r, pl in st:
        col = {"body": (255, 0, 0), "second": (0, 160, 0), "accent": (0, 140, 255), "struct": (200, 0, 200)}[r]
        q = ink.simplify(pl).astype(np.int32).reshape(-1, 1, 2); cv2.polylines(vis, [q], False, (0, 0, 0), 5); cv2.polylines(vis, [q], False, col, 2)
    for c in red: cv2.circle(vis, (int(c[0]), int(c[1])), 9, (0, 0, 255), 2)
    for c in orr: cv2.circle(vis, (int(c[0]), int(c[1])), 14, (0, 128, 255), 2)
    cv2.imwrite(os.path.join(HERE, "overlays", name + ".png"), np.hstack([P, vis]))
    return name, "%d strokes %d red %d rings" % (len(st), len(red), len(orr))

if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "extracted"), exist_ok=True); os.makedirs(os.path.join(HERE, "overlays"), exist_ok=True)
    names = sorted(f[:-4] for f in os.listdir(os.path.join(HERE, "patches")) if f.endswith(".png") and f[0] in "mn")
    with Pool(2) as p:
        for n, r in p.imap_unordered(one, names): print(n, r, flush=True)
