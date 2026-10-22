"""Cut real chart images (photos/posters of kana charts) into single-letter bitmaps so they can be measured like font glyphs.

    python chart_glyphs.py <image> <name> [--dil 9] [--minh 28] [--blue] [--debug out.png]

Letters are the dark blobs left after a small dilation merges the pieces of one letter (strokes, voicing marks).
Latin romaji are dropped by size/colour. Only measured, never copied."""
import argparse
import cv2
import numpy as np
from scipy import ndimage as ndi


def cut(path, dil=9, minh=28, maxh=200, colour_max=110, region=None):
    im = cv2.imread(path)
    if region:
        x0, y0, x1, y1 = region
        im = im[y0:y1, x0:x1]
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    b, g, r = [im[..., i].astype(int) for i in range(3)]
    dark = (gray < colour_max) & (np.abs(r - b) < 60)            # near-black ink; blue/orange romaji and titles are excluded
    merged = cv2.dilate(dark.astype("uint8"), np.ones((dil, dil), "uint8"))
    lab, n = ndi.label(merged)
    out = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        ys, xs = sl
        h, w = ys.stop - ys.start, xs.stop - xs.start
        if h < minh or h > maxh or w > maxh * 1.3:
            continue
        piece = dark[sl] & (lab[sl] == i)
        if piece.sum() < 30:
            continue
        out.append((ys.start, xs.start, piece))
    return out


def stroke_width(bm):
    from skimage.morphology import skeletonize
    sk = skeletonize(bm)
    return bm.sum() / max(sk.sum(), 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("image"); ap.add_argument("--dil", type=int, default=9); ap.add_argument("--minh", type=int, default=28)
    ap.add_argument("--maxh", type=int, default=200); ap.add_argument("--debug")
    ap.add_argument("--region", type=int, nargs=4)
    a = ap.parse_args()
    gl = cut(a.image, a.dil, a.minh, a.maxh, region=a.region)
    print(len(gl), "letters; heights", sorted({p.shape[0] for _, _, p in gl})[:3], "...")
    if a.debug:
        im = cv2.imread(a.image)
        if a.region:
            x0, y0, x1, y1 = a.region; im = im[y0:y1, x0:x1]
        for y, x, p in gl:
            cv2.rectangle(im, (x, y), (x + p.shape[1], y + p.shape[0]), (0, 0, 255), 1)
        cv2.imwrite(a.debug, im)
