"""Drawing sheets: each letter on the left, an empty box of the same size on the right, so the owner can redraw it.
usage: python3 pairs.py file.json out_prefix reject,ids [per_row] [per_page]"""
import json, sys, cv2, numpy as np
from render import render, HEAD
L = json.load(open(sys.argv[1]))["letters"]; pre = sys.argv[2]; rej = set(sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] else set()
per_row = int(sys.argv[4]) if len(sys.argv) > 4 else 3; per_page = int(sys.argv[5]) if len(sys.argv) > 5 else 18
keep = [l for l in L if l["iast"] not in rej]; sc = 2.6; pad = 8; FOOT = 38
for pg in range(0, len(keep), per_page):
    ims = []
    for l in keep[pg:pg + per_page]:
        a = render(l, sc=sc, pad=pad, label=l["iast"]); b = np.full_like(a, 255); cv2.rectangle(b, (pad, pad + HEAD), (a.shape[1] - pad, a.shape[0] - pad), (150, 150, 150), 1); cv2.putText(b, l["iast"], (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.rectangle(a, (pad, pad + HEAD), (a.shape[1] - pad, a.shape[0] - pad), (210, 210, 210), 1); foot = np.full((FOOT, a.shape[1], 3), 255, np.uint8); cv2.putText(foot, "1    2    3    4    D", (14, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
        a = np.vstack([a, foot]); b = np.vstack([b, np.full_like(foot, 255)])
        ims.append(np.hstack([a, np.full((a.shape[0], 10, 3), 255, np.uint8), b, np.full((a.shape[0], 40, 3), 255, np.uint8)]))
    h, w = ims[0].shape[:2]; rows = -(-len(ims) // per_row); S = np.full((rows * h, per_row * w, 3), 255, np.uint8)
    for i, im in enumerate(ims): S[(i // per_row) * h:(i // per_row + 1) * h, (i % per_row) * w:(i % per_row + 1) * w] = im
    cv2.imwrite("%s_%d.png" % (pre, pg // per_page + 1), S); print("%s_%d.png" % (pre, pg // per_page + 1), len(ims), "letters", S.shape)
print("kept", len(keep), "of", len(L))
