"""Extract the topology of a hand-drawn glyph: skeleton graph (nodes = ends and junctions, edges = strokes) of the blue ink inside a crop,
   plus the purple bar and the red anchor dots.   python topo.py   (pilot: Devanagari page 2)"""
import glob, numpy as np, sys
from PIL import Image, ImageDraw
from skimage.morphology import skeletonize
from scipy import ndimage as ndi
import networkx as nx

def masks(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    blue = (b - r > 30) & (b > g - 8)
    red = (r - g > 70) & (r - b > 60)
    purple = (b - g > 10) & (r - g > 10) & ~blue
    return blue, red, purple

def graph(mask, prune=8):
    sk = skeletonize(ndi.binary_closing(mask, iterations=1))
    G = nx.Graph(); ys, xs = np.nonzero(sk)
    P = set(zip(ys, xs))
    for y, x in P:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (dy or dx) and (y + dy, x + dx) in P: G.add_edge((y, x), (y + dy, x + dx))
    # drop tiny spurs
    for _ in range(prune):
        ends = [n for n in G if G.degree(n) == 1]
        if len(ends) <= 2: break
        for n in ends:
            if sum(1 for _ in nx.dfs_preorder_nodes(G, n, depth_limit=prune)) < prune: G.remove_node(n)
    return sk, G

def summarize(G):
    ends = [n for n in G if G.degree(n) == 1]
    junc = [n for n in G if G.degree(n) >= 3]
    # cluster adjacent junction pixels
    jm = np.zeros((1, 1), bool)
    return ends, junc

if __name__ == "__main__":
    base = glob.glob("/mnt/user-data/attachments/*/")[0]
    im = Image.open(base + "f06b4a5c-image.jpg").convert("RGB")
    S = 1 / 0.45; H = int(58 * S)
    items = [("ca", 650, 130), ("ja", 570, 218), ("ña", 580, 320), ("ṭa", 515, 355), ("ṭha", 515, 385), ("ḍa", 520, 447), ("ṇa", 525, 543), ("ta", 515, 598), ("tha", 515, 652), ("na", 450, 785), ("pa", 450, 825), ("ba", 510, 910)]
    tiles = []
    for name, cx, cy in items:
        c = im.crop((int(cx * S - H), int(cy * S - H), int(cx * S + H), int(cy * S + H)))
        a = np.asarray(c); blue, red, purple = masks(a)
        sk, G = graph(blue)
        ends = [n for n in G if G.degree(n) == 1]
        junc = [n for n in G if G.degree(n) >= 3]
        o = Image.fromarray((np.ones_like(a) * 255).astype(np.uint8)); d = ImageDraw.Draw(o)
        for y, x in zip(*np.nonzero(sk)): d.point((x, y), fill=(0, 0, 0))
        for y, x in junc: d.ellipse((x - 5, y - 5, x + 5, y + 5), outline=(220, 0, 0), width=2)
        for y, x in ends: d.rectangle((x - 4, y - 4, x + 4, y + 4), outline=(0, 90, 220), width=2)
        ry, rx = np.nonzero(ndi.binary_dilation(red, iterations=2)); 
        lab, k = ndi.label(ndi.binary_dilation(red, iterations=4))
        for s in ndi.find_objects(lab):
            cy_, cx_ = (s[0].start + s[0].stop) // 2, (s[1].start + s[1].stop) // 2
            d.ellipse((cx_ - 6, cy_ - 6, cx_ + 6, cy_ + 6), fill=(200, 0, 200))
        both = Image.new("RGB", (c.size[0] * 2, c.size[1]), "white"); both.paste(c, (0, 0)); both.paste(o, (c.size[0], 0))
        both.thumbnail((300, 150)); tiles.append((name, both, len(ends), len(junc)))
        print(name, "ends", len(ends), "junction-px", len(junc))
    cols = 3; W, Hh = 300, 150
    M = Image.new("RGB", (cols * W, ((len(tiles) + cols - 1) // cols) * (Hh + 12)), "white"); dm = ImageDraw.Draw(M)
    for i, (n, t, e, j) in enumerate(tiles):
        M.paste(t, ((i % cols) * W, (i // cols) * (Hh + 12) + 12)); dm.text(((i % cols) * W + 2, (i // cols) * (Hh + 12)), n, fill="black")
    M.save("/home/claude/topo_pilot.png")
