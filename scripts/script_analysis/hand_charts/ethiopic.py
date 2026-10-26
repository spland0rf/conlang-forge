"""Draft Ethiopic (Amharic) stroke data from the user's page 1: 13 consonant bases (the ä column) plus one mark per vowel column.
Base shapes are read from the chart; vowel marks are placed at the base's right edge. The per-letter exceptions the user listed (the a and o columns
for s b v t, the i and o columns for r, and a few others) are not encoded yet.   python ethiopic.py [out.png]"""
import json, math, os, sys

def arc(cx, cy, r, a0, a1, n=24, ry=None):
    ry = ry or r
    return [[cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))] for i in range(n + 1)]
def ring(cx, cy, r, ry=None): return {"p": arc(cx, cy, r, 0, 360, 28, ry), "closed": True}
def S(*pts): return {"p": [list(p) for p in pts]}
def P(pts): return {"p": pts}

def cup(x0, x1, top=.9, bot=.1, r=None):                      # a U: down the left, round the foot, up the right
    r = r or (x1 - x0) / 2
    return P([[x0, top], [x0, bot + r]] + arc(x0 + r, bot + r, r, 180, 360, 14)[1:] + [[x1, top]])
def arch(x0, x1, top=.9, bot=.1):                              # an upside-down U
    r = (x1 - x0) / 2
    return P([[x0, bot], [x0, top - r]] + arc(x0 + r, top - r, r, 180, 0, 14)[1:] + [[x1, bot]])

BASES = {   # name: (strokes, right edge x, bottom y)
    "h": ([cup(.15, .85)], .85, .1),
    "l": ([S((.5, .9), (.9, .1)), S((.1, .1), (.5, .9))], .9, .1),
    "ḥ": ([S((.15, .9), (.15, .1)), arch(.35, .85, .75, .1), S((.6, .9), (.6, .75))], .85, .1),
    "m": ([ring(.25, .5, .17, .38), ring(.65, .5, .17, .38)], .82, .12),
    "ś": ([cup(.1, .45), cup(.45, .8), S((.8, .9), (.8, .5))], .8, .1),
    "r": ([P(arc(.55, .75, .25, 90, 220, 10) + arc(.5, .35, .25, 140, 330, 14)[1:])], .75, .15),
    "s": ([arch(.2, .8, .8, .1), S((.5, 1.0), (.5, .85))], .8, .1),
    "q": ([S((.5, 1.0), (.5, .0)), ring(.5, .5, .25, .22)], .75, .0),
    "b": ([arch(.15, .85, .85, .1)], .85, .1),
    "v": ([arch(.15, .85, .75, .1), S((.1, 1.0), (.9, 1.0)), S((.25, 1.0), (.25, .75)), S((.75, 1.0), (.75, .75))], .85, .1),
    "t": ([S((.3, 1.0), (.3, .0)), S((.3, .6), (.85, .6))], .85, .0),
    "č": ([S((.25, 1.0), (.25, .0)), S((.1, .65), (.8, .65)), S((.55, .65), (.55, .3)), S((.1, 1.0), (.8, 1.0))], .8, .0),
    "ḫ": ([S((.2, 1.0), (.2, .1)), P([[.2, .9], [.5, .75], [.5, .45], [.75, .3], [.8, .1]])], .8, .1),
}
VOWELS = ["ä", "u", "i", "a", "e", "ɨ", "o"]

def mark(v, xr, yb):
    if v == "u": return [S((xr, .5), (xr + .2, .5))]
    if v == "i": return [S((xr, yb + .1), (xr + .14, yb + .1), (xr + .14, yb - .08 if yb > 0 else .0))]
    if v == "a": return [S((xr, yb), (xr, yb - .22))]
    if v == "e": return [ring(xr + .1, yb + .06, .07)]
    if v == "ɨ": return [S((xr, .55), (xr + .12, .45), (xr + .2, .55), (xr + .12, .65))]
    if v == "o": return [ring(xr + .1, .92, .07)]
    return []

def letters():
    out = {}
    for c, (st, xr, yb) in BASES.items():
        for v in VOWELS:
            out[c + v] = st + mark(v, xr, yb)
    return out

if __name__ == "__main__":
    L = letters()
    here = os.path.dirname(os.path.abspath(__file__))
    json.dump(L, open(os.path.join(here, "ethiopic_page1.json"), "w"))
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(BASES), len(VOWELS), figsize=(9, 15))
    for i, c in enumerate(BASES):
        for j, v in enumerate(VOWELS):
            ax = axes[i][j]; ax.set_xlim(-.1, 1.3); ax.set_ylim(-.35, 1.15); ax.set_aspect("equal"); ax.axis("off")
            for s in L[c + v]:
                xs, ys = zip(*s["p"]); ax.plot(xs, ys, "k", lw=1.6, solid_capstyle="round")
            if j == 0: ax.text(-.1, .5, c, fontsize=11, ha="right")
            if i == 0: ax.set_title(v, fontsize=10)
    fig.savefig(sys.argv[1] if len(sys.argv) > 1 else "ethiopic_page1.png", dpi=80)
