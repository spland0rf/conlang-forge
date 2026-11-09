"""Find the owner's empty-box rectangles in a photo of a drawing sheet and rectify each to a 400x400 patch (= the 100x100 letter frame)."""
import cv2, numpy as np, sys, json
S = 400
def line_masks(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY); bl = cv2.GaussianBlur(g, (3, 3), 0)
    loc = cv2.adaptiveThreshold(bl, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 6)
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV); col = ((hsv[..., 1] > 70) & (hsv[..., 2] > 50)).astype(np.uint8) * 255
    dark = cv2.bitwise_and(loc, cv2.bitwise_not(cv2.dilate(col, np.ones((5, 5), np.uint8))))
    h = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))); h = cv2.morphologyEx(h, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (140, 1)))
    v = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))); v = cv2.morphologyEx(v, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 140)))
    return h, v
def segs(mask, horiz):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask); out = []
    for i in range(1, n):
        x, y, w, hh, a = st[i]
        if (horiz and w > 150 and hh < 20) or (not horiz and hh > 150 and w < 20):
            pts = np.column_stack(np.where(lab == i)[::-1]); out.append((x, y, w, hh, pts))
    return out
def find(im):
    """returns list of (cx, cy, corners[4x2]) for every box whose four sides were found"""
    h, v = line_masks(im); H = segs(h, True); V = segs(v, False); boxes = []
    for x, y, w, hh, pts in H:                                              # a top edge: look for a verticals pair below it, and a bottom edge
        pass
    # grid approach: cluster horizontal segments by (x-start) and y; pair each top with the bottom ~ same width below
    for t in H:
        for b in H:
            tx, ty, tw = t[0], t[1], t[2]; bx, by, bw = b[0], b[1], b[2]
            if abs(tx - bx) < 25 and abs(tw - bw) < 35 and 230 < by - ty < 340 and 230 < tw < 340:
                L = [s for s in V if abs(s[0] - tx) < 30 and abs(s[1] - ty) < 40]; R = [s for s in V if abs(s[0] - (tx + tw)) < 30 and abs(s[1] - ty) < 40]
                if L and R: boxes.append((tx, ty, tw, by - ty))
    # unique
    out = []
    for b in boxes:
        if not any(abs(b[0] - o[0]) < 30 and abs(b[1] - o[1]) < 30 for o in out): out.append(b)
    return out
def patch(im, b):
    x, y, w, h = b; pad = 0
    return cv2.resize(im[y:y + h, x:x + w], (S, S), interpolation=cv2.INTER_AREA)
if __name__ == "__main__":
    im = cv2.imread(sys.argv[1]); bs = find(im); print(len(bs), "boxes"); vis = im.copy()
    for x, y, w, h in bs: cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 0, 255), 4)
    cv2.imwrite(sys.argv[2], cv2.resize(vis, None, fx=0.5, fy=0.5))
