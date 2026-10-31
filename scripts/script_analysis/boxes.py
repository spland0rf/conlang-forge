"""Find the green box around each drawn glyph (seeded by the blue glyph), so that only the ink strictly inside it is analysed.
   Colour classes: blue, red, green, purple (bar and its descenders), black."""
import glob, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import matplotlib.colors as mc
from topo2 import PAGES, glyph_boxes

def classes(a):
    hsv = mc.rgb_to_hsv(a / 255.); h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    r, g, b = [a[..., i].astype(int) for i in range(3)]
    blue = (h > 185) & (h < 260) & (s > .35) & (v > .3)
    green = (h > 55) & (h < 165) & (s > .22) & (v > .25) & (v < .85) & (g - b > 20)
    red = ((h < 18) | (h > 340)) & (s > .55) & (v > .5)
    purple = (((h > 260) & (h < 345)) | (h < 18) | (h > 340)) & (s > .2) & (v < .5) & (r - g > 15)
    black = (v < .38) & (s < .3)
    return {"blue": blue, "green": green, "red": red & ~purple, "purple": purple, "black": black & ~purple}

_CACHE = {}
def find_box_components(green, bx, pad=70):
    """the green box = the smallest green connected component (outline) whose bbox contains the blue glyph"""
    key = id(green)
    if key not in _CACHE:
        lab, n = ndi.label(ndi.binary_dilation(green, iterations=3)); _CACHE.clear()
        _CACHE[key] = [(s[1].start, s[0].start, s[1].stop, s[0].stop) for s in ndi.find_objects(lab) if s[0].stop - s[0].start > 60 and s[1].stop - s[1].start > 50]
    x0, y0, x1, y1 = bx; cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    cand = [c for c in _CACHE[key] if c[0] - 15 <= x0 + 10 and c[2] + 15 >= x1 - 10 and c[1] - 15 <= y0 + 10 and c[3] + 15 >= y1 - 10 and (c[2] - c[0]) < 420 and (c[3] - c[1]) < 420]
    if not cand: return None, None, None, None
    c = min(cand, key=lambda c: (c[2] - c[0]) * (c[3] - c[1]))
    return c[1] + 3, c[3] - 3, c[0] + 3, c[2] - 3

def find_box(green, bx, pad=70):
    x0, y0, x1, y1 = bx; H, W = green.shape
    gx = ndi.binary_dilation(green, iterations=4)
    def best_row(lo, hi, xa, xb):
        lo, hi = max(0, lo), min(H, hi)
        if hi <= lo: return None
        cnt = gx[lo:hi, xa:xb].sum(1); i = int(np.argmax(cnt)); return (lo + i) if cnt[i] > .30 * (xb - xa) else None
    def best_col(lo, hi, ya, yb):
        lo, hi = max(0, lo), min(W, hi)
        if hi <= lo: return None
        cnt = gx[ya:yb, lo:hi].sum(0); i = int(np.argmax(cnt)); return (lo + i) if cnt[i] > .30 * (yb - ya) else None
    cx = (x0 + x1) // 2
    top = best_row(y0 - pad, y0 + 5, x0 - 10, x1 + 10); bot = best_row(y1 - 5, y1 + pad, x0 - 10, x1 + 10)
    left = best_col(x0 - pad, x0 + 5, y0 - 10, y1 + 10); right = best_col(x1 - 5, x1 + pad, y0 - 10, y1 + 10)
    return top, bot, left, right

if __name__ == "__main__":
    base = glob.glob("/mnt/user-data/attachments/*/")[0]
    for n in (1, 2, 3):
        im = Image.open(base + PAGES[n] + "-image.jpg").convert("RGB"); a = np.asarray(im); C = classes(a)
        d = ImageDraw.Draw(im); miss = 0
        for i, bx in enumerate(glyph_boxes(a)):
            t, b_, l, r = find_box(C["green"], bx)
            if None in (t, b_, l, r): miss += 1; d.rectangle(bx, outline="orange", width=5); continue
            d.rectangle((l, t, r, b_), outline="magenta", width=5)
        print(n, "boxes missing a side:", miss)
        im.thumbnail((800, 1100)); im.save(f"/home/claude/boxes_p{n}.png")
