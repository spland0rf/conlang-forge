"""photo | assembled graph pairs: python3 review_sheet.py graphs.json out_prefix [per_page]"""
import sys, json, cv2, numpy as np
from render import render
L = json.load(open(sys.argv[1]))["letters"]; pre = sys.argv[2]; per = int(sys.argv[3]) if len(sys.argv) > 3 else 4
for p in range(0, len(L), per):
    rows = []
    for l in L[p:p + per]:
        ph = cv2.imread("trace/patches/%s.png" % l["glyph"]); ph = cv2.resize(ph, (412, 412)); g = render(l, sc=3.4, pad=6, label="%s  score %s" % (l["glyph"], l.get("score")))
        g = g[:, :]; h = max(ph.shape[0], g.shape[0]); pad = lambda im: np.vstack([im, np.full((h - im.shape[0], im.shape[1], 3), 255, np.uint8)])
        rows.append(np.hstack([pad(g), pad(ph)]))
    for k in range(0, len(rows), 2):
        pass
    r2 = [np.hstack(rows[i:i + 2]) if len(rows[i:i + 2]) == 2 else np.hstack([rows[i], np.full_like(rows[i], 255)]) for i in range(0, len(rows), 2)]
    cv2.imwrite("%s_%d.png" % (pre, p // per + 1), np.vstack(r2))
