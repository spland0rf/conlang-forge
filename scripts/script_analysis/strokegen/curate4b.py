"""n018 and m030 from the owner's green-ink redraw (photographed 2026-11-09).  Hand-built from the photo (400px patch = 100 units): the light ink defeated the tracer's ring/red-dot finder.
python3 curate4b.py -> updates curated_bengali_round4_reviewed.json and curated_bengali_round4.json"""
import json, math, os
from curate4 import refresh
HERE = os.path.dirname(os.path.abspath(__file__))
def cr(pts, n=10):
    P = [pts[0]] + list(pts) + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n; t2, t3 = t * t, t * t * t
            out.append(tuple(.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(tuple(pts[-1])); return out
def u(pts): return [(x / 4, y / 4) for x, y in pts]
def path(P): return "M" + " L".join("%.1f %.1f" % p for p in P)
def mk(glyph, iast, score, strokes, juncs, ends):
    S = {sid: (role, p) for sid, role, p in strokes}
    l = {"glyph": glyph, "iast": iast, "variant": 0, "strokes": [[r, path(p), sid] for sid, (r, p) in S.items()],
         "junctions": [{"t": t, "x": round(x, 1), "y": round(y, 1), "members": [{"stroke": m, "at": 0.0, "where": "start"} for m in ms], "loose": False} for t, (x, y), ms in juncs],
         "ends": ends, "score": score, "source": "redraw"}
    refresh(l, {k: [r, p] for k, (r, p) in S.items()}); return l

def n018(old):
    X = 41.0; top = (X, 15.5); r1 = (X, 29.3); r2 = (X, 52.5); bot = (X, 86.0); c_ll = (15.5, 57.0); c_w = (28.8, 22.8); c_r = (71.3, 51.8)
    arc = cr(u([(172, 62), (200, 57), (235, 60), (265, 78), (290, 105), (302, 130), (297, 148), (288, 152)])); arc[0] = top
    a = cr(u([(65, 162), (85, 168), (92, 185), (88, 205), (75, 220), (62, 228)])); a[-1] = c_ll
    b = cr(u([(62, 228), (85, 242), (110, 262), (130, 295), (145, 330), (150, 342)])); sh = bot[0] - 37.5; n = len(b) - 1; b = [(x + sh * (i / n) ** 2, y) for i, (x, y) in enumerate(b)]; b[0] = c_ll; b[-1] = bot
    g1 = cr(u([(35, 75), (40, 95), (60, 112), (85, 118), (105, 105), (115, 90)])); g1[-1] = c_w
    g2 = cr(u([(115, 90), (125, 105), (145, 115), (172, 118)])); g2[0] = c_w; g2[-1] = r1
    g3 = cr(u([(168, 210), (200, 222), (240, 220), (270, 212), (285, 207)])); g3[0] = r2; g3[-1] = c_r
    g4 = cr(u([(285, 207), (275, 240), (265, 290), (262, 348)])); g4[0] = c_r
    st = [("s1", "body", [top, bot]), ("s2", "body", arc), ("s3", "body", a), ("s4", "body", b), ("s5", "second", g1), ("s6", "second", g2), ("s7", "second", g3), ("s8", "second", g4)]
    J = [("touch", top, ["s1", "s2"]), ("red", r1, ["s1", "s6"]), ("red", r2, ["s1", "s7"]), ("touch", bot, ["s1", "s4"]), ("touch", c_ll, ["s3", "s4"]), ("touch", c_w, ["s5", "s6"]), ("touch", c_r, ["s7", "s8"])]
    return mk("n018", "n018", old["score"], st, J, {"s2": ["plain", "ball"], "s3": ["ball", "plain"]})

def m030(old):
    X = 44.0; top = (X, 9.0); mid = (X, 29.5); bot = (X, 88.5); c_w = (30.5, 18.0); c_l = (11.8, 60.8)
    bowl = cr(u([(175, 118), (210, 135), (250, 150), (285, 170), (300, 200), (305, 235), (290, 270), (265, 300), (230, 325), (177, 355)])); bowl[0] = mid; bowl[-1] = bot
    gt = cr(u([(175, 38), (200, 35), (235, 38), (270, 48), (300, 65), (318, 85), (320, 103), (310, 110), (298, 106)])); gt[0] = top
    g1 = cr(u([(62, 65), (66, 92), (85, 107), (108, 105), (121, 88), (122, 72)])); g1[-1] = c_w
    g2 = cr(u([(122, 72), (128, 90), (150, 108), (175, 118)])); g2[0] = c_w; g2[-1] = mid
    h1 = cr(u([(62, 180), (80, 178), (90, 192), (85, 215), (65, 232), (47, 243)])); h1[-1] = c_l
    h2 = cr(u([(47, 243), (85, 275), (130, 310), (160, 335), (177, 355)])); h2[0] = c_l; h2[-1] = bot
    st = [("s1", "body", [top, bot]), ("s2", "body", bowl), ("s3", "second", gt), ("s4", "second", g1), ("s5", "second", g2), ("s6", "second", h1), ("s7", "second", h2)]
    J = [("red", top, ["s1", "s3"]), ("red", mid, ["s1", "s2", "s5"]), ("red", bot, ["s1", "s2", "s7"]), ("touch", c_w, ["s4", "s5"]), ("touch", c_l, ["s6", "s7"])]
    return mk("m030", "m030", old["score"], st, J, {"s3": ["plain", "ball"], "s6": ["ball", "plain"]})

if __name__ == "__main__":
    for fn in ("curated_bengali_round4_reviewed.json", "curated_bengali_round4.json"):
        p = os.path.join(HERE, fn); d = json.load(open(p)); L = {l["glyph"]: l for l in d["letters"]}
        for g, f in (("n018", n018), ("m030", m030)):
            old = L.get(g) or {"score": 3}; new = f(old)
            if g in L: d["letters"][d["letters"].index(L[g])] = new
            else: d["letters"].append(new)
        json.dump(d, open(p, "w")); print(fn, len(d["letters"]))
