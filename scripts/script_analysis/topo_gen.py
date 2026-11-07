"""Generate variants of captured letters by perturbing their topology graph (node positions, stroke bows) while every stroke keeps its end nodes,
   then verify that each variant still has the same topology as its source.   python topo_gen.py 2 3"""
import copy, json, math, random, sys
import numpy as np
from PIL import Image, ImageDraw
from topo3 import render, ink, extract, metrics
import numpy as np

def variant(spec, rng, amt=.05):
    s = copy.deepcopy(spec); nodes = {k: list(v) for k, v in s["nodes"].items()}
    on_bar = {str(k) for k in s["on_bar"]}
    for k, v in nodes.items():
        dx, dy = rng.uniform(-amt, amt), rng.uniform(-amt, amt) * (0 if k in on_bar else 1)
        v[0] = min(1, max(0, v[0] + dx)); v[1] = min(1, max(0, v[1] + dy)) if k not in on_bar else v[1]
    s["nodes"] = {k: v for k, v in nodes.items()}
    for st in s["strokes"]:
        a, b = nodes[str(st["a"])], nodes[str(st["b"])]; pts = st["pts"]; n = len(pts)
        ph = rng.uniform(0, 6.28); bow = rng.uniform(-amt, amt)
        new = [a]
        for i in range(1, n - 1):
            t = i / (n - 1); p0, p1 = spec["nodes"][str(st["a"])], spec["nodes"][str(st["b"])]
            # shift the interior point by the end displacement blended along the stroke, plus a small bow
            da = [a[0] - p0[0], a[1] - p0[1]]; db = [b[0] - p1[0], b[1] - p1[1]]
            new.append([pts[i][0] + (1 - t) * da[0] + t * db[0] + bow * math.sin(math.pi * t) * .6, pts[i][1] + (1 - t) * da[1] + t * db[1] + bow * math.sin(math.pi * t + ph) * .4])
        new.append(b); st["pts"] = new
    s["anchors"] = [dict(q, x=q["x"] if isinstance(q, dict) else q) for q in s.get("anchors", [])] if s.get("anchors") and isinstance(s["anchors"][0], dict) else s.get("anchors", [])
    return s

def topo_of_render(spec):
    r = np.asarray(render(spec)); b, k, _, _ = ink(r); pos, edges = extract(r, b | k); return metrics(pos, edges)

if __name__ == "__main__":
    rng = random.Random(7); rows = []; same = tot = 0
    for page in sys.argv[1:]:
        specs = json.load(open(f"/home/claude/topo3_p{page}.json"))
        for i, sp in specs.items():
            m0 = topo_of_render(sp); vs = []
            for _ in range(4):
                v = variant(sp, rng); m = topo_of_render(v); tot += 1; ok = all(m[k] == m0[k] for k in ("comps", "loops", "ends", "junctions")); same += ok; vs.append((v, ok))
            rows.append((f"p{page}-{i}", sp, vs))
    print(f"variants keeping their source topology: {same}/{tot}")
    W, H = 190, 170; n = len(rows)
    M = Image.new("RGB", (5 * W, n * H), "white"); d = ImageDraw.Draw(M)
    for r, (name, sp, vs) in enumerate(rows):
        for c, (spec, ok) in enumerate([(sp, True)] + vs):
            im = render(spec).resize((W - 10, int((W - 10) * 200 / 220))); M.paste(im, (c * W + 5, r * H + 14))
            d.text((c * W + 5, r * H + 2), (name + " source") if c == 0 else ("same topology" if ok else "CHANGED"), fill=(0, 120, 0) if ok else (200, 0, 0))
    M.save("/home/claude/topo_gen.png"); print(M.size)
