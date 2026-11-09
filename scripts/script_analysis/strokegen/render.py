"""Contact sheet of letters in graph format (real or generated): python3 render.py file.json out.png [cols]"""
import json, sys, cv2, numpy as np, re
COL = {"struct": (200, 0, 200), "body": (255, 0, 0), "second": (0, 150, 0), "accent": (0, 130, 255)}
def parse(d): v = [float(x) for x in re.findall(r"-?\d+\.?\d*", d)]; return list(zip(v[0::2], v[1::2]))
HEAD = 30                                                                  # header strip for the label
def render(l, sc=2.0, pad=6, label=""):
    img = np.full((int(100 * sc) + 2 * pad + HEAD, int(100 * sc) + 2 * pad, 3), 255, np.uint8); f = lambda p: (int(pad + p[0] * sc), int(pad + HEAD + p[1] * sc))
    for role, d, sid in l["strokes"]:
        P = [f(p) for p in parse(d)]; cv2.polylines(img, [np.array(P, np.int32)], False, COL[role], 2, cv2.LINE_AA)
        for k, e in enumerate(l.get("ends", {}).get(sid, [])):
            if e == "ball": cv2.circle(img, P[0 if k == 0 else -1], 3, COL[role], -1)
    for j in l["junctions"]:
        c = f((j["x"], j["y"]))
        if j["t"] == "red": cv2.circle(img, c, 4, (0, 0, 255), -1)
        elif j["t"] == "touch": cv2.circle(img, c, 6, (0, 140, 255), 2)
        else: cv2.drawMarker(img, c, (0, 140, 255), cv2.MARKER_TILTED_CROSS, 12, 2)
    cv2.putText(img, label or l["iast"], (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2, cv2.LINE_AA); return img
if __name__ == "__main__":
    L = json.load(open(sys.argv[1]))["letters"]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    ims = [render(l, label="%s<%s %s" % (l["iast"], l.get("donor", ""), l.get("novelty", ""))) for l in L]; h, w = ims[0].shape[:2]; rows = (len(ims) + cols - 1) // cols
    S = np.full((rows * h, cols * w, 3), 255, np.uint8)
    for i, im in enumerate(ims): S[(i // cols) * h:(i // cols + 1) * h, (i % cols) * w:(i % cols + 1) * w] = im
    cv2.imwrite(sys.argv[2], S)
