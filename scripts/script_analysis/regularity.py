"""How regular the strokes of generated scripts are (no real script needed): the spread of the near-vertical stroke angles
across letters, how many horizontal guide lines the letters' tops, bottoms and attachment points use, and how many tiny
strokes there are. Lower is more regular. Usage: python regularity.py preset[,preset...] [seeds]"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from conlang_forge.script.generate import generate          # noqa: E402
from conlang_forge.script.geometry import flatten           # noqa: E402
from conlang_forge.script.presets import BY_ID               # noqa: E402


def measure(script):
    r = script["spec"]["roundness"]
    devs, ws, ys, tiny, strokes = [], [], [], 0, 0
    for l in script["letters"]:
        if l["role"] not in ("consonant", "vowel") or not str(l.get("family", "")).startswith("stroke:"):
            continue
        for s in l["strokes"]:
            if s.get("dot") or s.get("stub"):
                continue
            pts = flatten(s, r)
            if len(pts) < 2:
                continue
            strokes += 1
            length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
            tiny += length < 0.15
            for a, b in zip(pts, pts[1:]):
                dx, dy = b[0] - a[0], b[1] - a[1]
                L = math.hypot(dx, dy)
                if L >= 0.12 and abs(dx) <= math.tan(math.radians(25)) * abs(dy):
                    devs.append(math.degrees(math.atan2(dx if dy > 0 else -dx, abs(dy))))     # leaning right is positive whichever way the stroke runs
                    ws.append(L)
            ys += [pts[0][1], pts[-1][1]]
            for i in range(1, len(pts) - 1):                      # tops and bottoms of curves
                if (pts[i][1] - pts[i - 1][1]) * (pts[i + 1][1] - pts[i][1]) < 0:
                    ys.append(pts[i][1])
    W = sum(ws) or 1
    mean = sum(d * w for d, w in zip(devs, ws)) / W
    sd = math.sqrt(sum(w * (d - mean) ** 2 for d, w in zip(devs, ws)) / W)
    bins = {}
    for y in ys:
        bins[round(y / 0.05)] = bins.get(round(y / 0.05), 0) + 1
    need, tot, acc = 0, len(ys) or 1, 0
    for c in sorted(bins.values(), reverse=True):
        acc += c
        need += 1
        if acc >= 0.8 * tot:
            break
    return dict(axis_sd=sd, axis_mean=mean, guide_bins=need, tiny=tiny / max(strokes, 1), strokes=strokes / max(1, len(script["letters"])))


if __name__ == "__main__":
    presets = sys.argv[1].split(",")
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    for pid in presets:
        rows = [measure(generate(s, BY_ID[pid]["pins"])) for s in range(1, seeds + 1)]
        avg = {k: sum(r[k] for r in rows) / len(rows) for k in rows[0]}
        print(f"{pid:11s} axis_sd {avg['axis_sd']:.1f}deg  guide_bins(80%) {avg['guide_bins']:.1f}  tiny_strokes {avg['tiny']:.2f}  strokes/letter {avg['strokes']:.1f}")
