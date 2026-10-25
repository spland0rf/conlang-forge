"""Hand overrides applied to font drafts where the font draws a filled blob that a pen would draw as a loop.
python -m stroke_charts.overrides DRAFT.json   (edits in place)"""
import json, math, sys

def loop(cx, cy, rx, ry, start_angle, n=14, cw=True):
    """Closed loop starting/ending at the point on the ellipse at start_angle (degrees)."""
    pts = []
    for i in range(n + 1):
        a = math.radians(start_angle + (-1 if cw else 1) * 360 * i / n)
        pts.append([round(cx + rx * math.cos(a), 3), round(cy + ry * math.sin(a), 3)])
    return pts

def sha(strokes):
    # Bengali sha: two solid bulbs hang under the stem end (0.338, 0.652); draw each as a small loop.
    base = [s for s in strokes if s[0] != [0.205, 0.585]]
    left = loop(0.265, 0.585, 0.065, 0.065, 25, cw=False)
    right = loop(0.41, 0.585, 0.065, 0.065, 155, cw=True)
    left[0] = left[-1] = [0.338, 0.652]
    right[0] = right[-1] = [0.338, 0.652]
    return base + [left, right]

OVERRIDES = {"শ": sha}

if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    for ch, fn in OVERRIDES.items():
        if ch in d: d[ch]["strokes"] = fn(d[ch]["strokes"])
    json.dump(d, open(sys.argv[1], "w"), ensure_ascii=False)
