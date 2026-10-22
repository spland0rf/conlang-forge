"""Style families (from the owner's hand-drawn sheet): spikey, curvy, bubbly and boxy. Each family has base forms, built
from a few constructions (repeat x1/x2/x3, stack, side by side, close with a baseline, rotate, mirror), and a set of
modifiers, the lines added to a base form (through, stem, underline, flag, tail, curl...). A script draws one or two
families and a subset of their modifiers, so each script has its own consistent look.

Every base form is a list of strokes in the unit box (y up). `FORMS[family][name] = (builder, (lo, hi))` where
(lo, hi) is the complexity window in which the form is offered (0 ornate .. 1 bold)."""
from __future__ import annotations

import math

from .geometry import stroke

FAMILIES = ("spikey", "curvy", "bubbly", "boxy")
# which corner style each family is drawn in when a script is not mixed
NATIVE_STYLE = {"spikey": "sharp", "curvy": "smooth", "bubbly": "smooth", "boxy": "blocky"}


def _arc(cx, cy, rx, ry, a0, a1, n=8):
    return [(round(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), 3),
             round(cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n)), 3)) for i in range(n + 1)]


def _ring(cx, cy, rx, ry=None):
    return stroke(_arc(cx, cy, rx, ry or rx, 0, 360, 16)[:-1], True)


def _swap(pts):
    return [(y, x) for x, y in pts]


def _wave(n):
    pts = []
    for i in range(n * 8 + 1):
        t = i / (n * 8)
        pts.append((round(t, 3), round(.5 + .4 * math.sin(2 * math.pi * n * t), 3)))
    return pts


# ---- spikey -----------------------------------------------------------------------------------------------------------
def _peaks(n, closed):
    pts = [(0, 0)]
    for i in range(n):
        pts += [((2 * i + 1) / (2 * n), 1), ((2 * i + 2) / (2 * n), 0)]
    return [stroke(pts, False)] if not closed else [stroke(pts[:-1] + [(1, 0)], True)]


def _tri_chain(n):                       # n triangles sharing base corners (M with a baseline)
    return _peaks(n, True)


_SPIKEY = {
    "peak1": (lambda: _peaks(1, False), (.2, 1)), "peak2": (lambda: _peaks(2, False), (0, .9)), "peak3": (lambda: _peaks(3, False), (0, .6)),
    "tri": (lambda: _peaks(1, True), (.2, 1)), "tri2m": (lambda: _peaks(2, True), (0, .8)), "tri3m": (lambda: _peaks(3, True), (0, .5)),
    "chevron": (lambda: [stroke([(0, 1), (1, .5), (0, 0)])], (.2, 1)),
    "tri_r": (lambda: [stroke([(0, 1), (1, .5), (0, 0)], True)], (.2, 1)),
    "sidezig2": (lambda: [stroke(_swap([(0, 0), (.25, 1), (.5, 0), (.75, 1), (1, 0)]))], (0, .8)),
    "sidezig3": (lambda: [stroke(_swap([(0, 0), (1 / 6, 1), (2 / 6, 0), (.5, 1), (4 / 6, 0), (5 / 6, 1), (1, 0)]))], (0, .5)),
    "diamond": (lambda: [stroke([(.5, 0), (1, .5), (.5, 1), (0, .5)], True)], (.2, 1)),
    "diamond2": (lambda: [stroke([(0, .5), (.25, 1), (.5, .5), (.25, 0)], True), stroke([(.5, .5), (.75, 1), (1, .5), (.75, 0)], True)], (0, .75)),
    "diamond_v": (lambda: [stroke([(.5, .5), (1, .75), (.5, 1), (0, .75)], True), stroke([(.5, 0), (1, .25), (.5, .5), (0, .25)], True)], (0, .75)),
    "diamond_bar": (lambda: [stroke([(.5, 0), (1, .5), (.5, 1), (0, .5)], True), stroke([(0, .5), (1, .5)])], (0, .7)),
    "X": (lambda: [stroke([(0, 0), (1, 1)]), stroke([(0, 1), (1, 0)])], (.1, 1)),
    "tri_stack": (lambda: [stroke([(0, 1), (0, .5), (1, .75)], True), stroke([(0, .5), (0, 0), (1, .25)], True)], (0, .6)),
    "chevron_bar": (lambda: [stroke([(0, 1), (.5, .5), (0, 0)]), stroke([(0, .5), (1, .5)])], (0, .7)),
    "peak_x": (lambda: _peaks(1, True) + [stroke([(.5, 1), (.5, 0)])], (0, .6)),
}

# ---- curvy ------------------------------------------------------------------------------------------------------------
def _arches(n, down=False):
    legs = [i / n for i in range(n + 1)]
    out = []
    for i in range(n):
        x0, x1 = legs[i], legs[i + 1]
        r = (x1 - x0) / 2
        top = _arc((x0 + x1) / 2, .55, r, .45, 180, 0, 8)
        pts = ([(x0, 0)] if i == 0 else []) + [(x0, .55)] + top[1:-1] + [(x1, .55), (x1, 0)]
        out.append(stroke(pts))
    if down:
        out = [dict(s, p=[[x, round(1 - y, 3)] for x, y in s["p"]]) for s in out]
    return out


_CURVY = {
    "C": (lambda: [stroke(_arc(.5, .5, .5, .5, 50, 310))], (.1, 1)),
    "Cr": (lambda: [stroke(_arc(.5, .5, .5, .5, 130, -130))], (.1, 1)),
    "arch": (lambda: _arches(1), (.1, 1)), "cup": (lambda: _arches(1, True), (.1, 1)),
    "arch2": (lambda: _arches(2), (0, .8)), "arch3": (lambda: _arches(3), (0, .5)),
    "cup2": (lambda: _arches(2, True), (0, .8)),
    "S": (lambda: [stroke([(1, .9), (.5, 1), (0, .75), (.5, .5), (1, .25), (.5, 0), (0, .1)])], (.1, 1)),
    "Sr": (lambda: [stroke([(0, .9), (.5, 1), (1, .75), (.5, .5), (0, .25), (.5, 0), (1, .1)])], (.1, 1)),
    "wave1": (lambda: [stroke(_wave(1))], (.2, 1)), "wave2": (lambda: [stroke(_wave(2))], (0, .4)), "wave3": (lambda: [stroke(_wave(3))], (0, .5)),
    "three": (lambda: [stroke([(0, .95), (.7, 1), (.95, .75), (.4, .55), (.95, .3), (.7, 0), (0, .05)])], (0, .8)),
    "eps": (lambda: [stroke([(1, .95), (.3, 1), (.05, .75), (.6, .55), (.05, .3), (.3, 0), (1, .05)])], (0, .8)),
    "six": (lambda: [_ring(.5, .3, .3), stroke([(.2, .3), (.2, .65), (.5, .95), (.85, .95)])], (0, .7)),
    "spiral": (lambda: [stroke(_arc(.5, .5, .45, .45, 90, 450, 14)[:-4] + [(.5, .5)])], (0, .6)),
    "ess_c": (lambda: [stroke(_arc(.5, .75, .45, .25, 40, 270)), stroke(_arc(.5, .25, .45, .25, 90, -140)[:])], (0, .6)),
}

# ---- bubbly -----------------------------------------------------------------------------------------------------------
def _stack(n):
    r = .5 / n
    return [_ring(.5, r + 2 * r * i, r) for i in range(n)]


def _row(n):
    r = .5 / n
    return [_ring(r + 2 * r * i, .5, r) for i in range(n)]


def _tri_rings():
    """Three touching circles in a triangle (two below, one above); the turned and mirrored variants point it other ways."""
    r = .25
    top = r + 2 * r * math.sqrt(3) / 2
    lift = (1 - (top + r)) / 2
    def ring(cx, cy):                     # 24 points a ring: the circles touch at 0, 60 and 120 degrees, which need vertices to meet
        return stroke(_arc(cx, cy, r, r, 0, 360, 24)[:-1], True)
    return [ring(r, r + lift), ring(1 - r, r + lift), ring(.5, top + lift)]


def _D(x0=0, x1=1):
    w = x1 - x0
    return stroke([(x0, 0), (x0, 1), (x0 + .55 * w, 1), (x0 + .95 * w, .75), (x0 + .95 * w, .25), (x0 + .55 * w, 0)], True)


_BUBBLY = {
    "ring": (lambda: [_ring(.5, .5, .5)], (.1, 1)),
    "ring2": (lambda: _stack(2), (0, 1)), "ring3": (lambda: _stack(3), (0, .55)),
    "ring2h": (lambda: _row(2), (0, .8)), "ring3h": (lambda: _row(3), (0, .5)),
    "ring3t": (lambda: _tri_rings(), (0, .55)),
    "D": (lambda: [_D()], (.2, 1)),
    "Bb": (lambda: [stroke([(0, .5), (0, 1), (.5, 1), (1, .8), (1, .7), (.5, .5)], True),      # both bumps the same size
                    stroke([(0, 0), (0, .5), (.5, .5), (1, .3), (1, .2), (.5, 0)], True)], (0, .7)),
    "dome": (lambda: [stroke(_arc(.5, 0, .5, .95, 0, 180)[:-0 or None], True)], (.2, 1)),
    "dome2": (lambda: [stroke(_arc(.25, 0, .25, .95, 0, 180), True), stroke(_arc(.75, 0, .25, .95, 0, 180), True)], (0, .7)),
    "ring_dome": (lambda: [stroke(_arc(.5, 0, .5, .95, 0, 180), True), _ring(.5, .4, .2), stroke([(.5, .6), (.5, .95)])], (0, .5)),
    "ring_tri": (lambda: [stroke([(.5, 1), (1, 0), (0, 0)], True), _ring(.5, .35, .2), stroke([(.5, .55), (.5, 1)])], (0, .5)),
}

# ---- boxy -------------------------------------------------------------------------------------------------------------
def _crenel(n):
    pts, w = [(0, 0), (0, .85)], 1 / (2 * n - 1)
    x = 0.0
    for i in range(n):
        pts += [(x + w, .85), (x + w, .15)] if i < n - 1 else [(x + w, .85), (x + w, 0)]
        if i < n - 1:
            pts += [(x + 2 * w, .15), (x + 2 * w, .85)]
        x += 2 * w
    return [stroke(pts)]


_BOXY = {
    "box": (lambda: [stroke([(0, 0), (1, 0), (1, 1), (0, 1)], True)], (.15, 1)),
    "cup": (lambda: [stroke([(0, 1), (0, 0), (1, 0), (1, 1)])], (.1, 1)),
    "cap": (lambda: [stroke([(0, 0), (0, 1), (1, 1), (1, 0)])], (.1, 1)),
    "bracket_l": (lambda: [stroke([(1, 0), (0, 0), (0, 1), (1, 1)])], (.1, 1)),
    "bracket_r": (lambda: [stroke([(0, 0), (1, 0), (1, 1), (0, 1)])], (.1, 1)),
    "T": (lambda: [stroke([(0, 1), (1, 1)]), stroke([(.5, 1), (.5, 0)])], (.2, 1)),
    "Tinv": (lambda: [stroke([(0, 0), (1, 0)]), stroke([(.5, 0), (.5, 1)])], (.2, 1)),
    "step": (lambda: [stroke([(0, 0), (0, .5), (.5, .5), (.5, 1), (1, 1)])], (.1, 1)),
    "step2": (lambda: [stroke([(0, 1), (.4, 1), (.4, .5), (1, .5), (1, 0)])], (.1, 1)),
    "crenel2": (lambda: _crenel(2), (0, .8)), "crenel3": (lambda: _crenel(3), (0, .5)),
    "box2": (lambda: [stroke([(0, 0), (1, 0), (1, .5), (0, .5)], True), stroke([(0, .5), (1, .5), (1, 1), (0, 1)], True)], (0, .7)),
    "box2h": (lambda: [stroke([(0, 0), (.5, 0), (.5, 1), (0, 1)], True), stroke([(.5, 0), (1, 0), (1, 1), (.5, 1)], True)], (0, .7)),
    "boxbar": (lambda: [stroke([(0, 0), (1, 0), (1, 1), (0, 1)], True), stroke([(.5, 0), (.5, 1)])], (0, .6)),
    "pi_step": (lambda: [stroke([(0, 0), (0, 1), (.5, 1), (.5, .4), (1, .4), (1, 0)])], (0, .7)),
}

FORMS = {"spikey": _SPIKEY, "curvy": _CURVY, "bubbly": _BUBBLY, "boxy": _BOXY}

# ---- modifiers (lines added to a base form), by family -------------------------------------------------------------------
MODS = {
    "spikey": ["stem_up", "stem_down", "bar_h", "bar_lo", "underline", "overline", "slash", "flag", "arrow", "tail", "through_v", "stem_right"],
    "curvy": ["stem_up", "stem_down", "underline", "overline", "hook", "curl", "bar_h", "tail", "dot_in", "slash", "stem_left"],
    "bubbly": ["bar_h", "bar_v", "cross", "x_in", "through_v", "through_h", "stem_down", "stem_up", "tail", "underline", "dot_in", "slash", "hook"],
    "boxy": ["bar_h", "bar_v", "bar_lo", "cross", "stem_up", "stem_down", "stem_left", "stem_right", "underline", "overline", "flag", "through_v", "through_h"],
}


# ---- the earlier library, kept: every figure from shapes.py joins the family it fits (additive) ---------------------------
def _merge_earlier():
    from .shapes import LEVELS, MOTIFS, ORTHO_MOTIFS
    place = {
        "spikey": ["tri", "tri_down", "diamond", "tri2", "trident", "zigzag", "W", "V", "M", "N", "Z", "K", "Y", "comb", "harp",
                   "person", "fish", "X"],
        "curvy": ["S", "arc", "curl", "ring"],
        "bubbly": ["ring", "ring2", "ringcross", "target", "Q", "eye", "ankh", "B", "P", "house"],
    }
    for fam, names in place.items():
        for n in names:
            if n in MOTIFS and n not in FORMS[fam]:
                FORMS[fam][n] = (MOTIFS[n], LEVELS.get(n, (0, 1)))
    for n in ("plus", "boxplus", "ladder", "nest", "comb_top", "L", "H", "F", "P", "Pi", "Zq", "comb", "harp", "house"):
        if n in ORTHO_MOTIFS and n not in FORMS["boxy"]:
            FORMS["boxy"][n] = (ORTHO_MOTIFS[n], LEVELS.get(n, (0, 1)))
    # "classic": the letter-like structural figures and pictorial ones from the Egyptian-to-Latin chart, as a family of their own
    FORMS["classic"] = {n: (b, LEVELS.get(n, (0, 1))) for n, b in MOTIFS.items()}


_merge_earlier()
# A base letter repeats a peak, bump or wave at most twice (circles may repeat three times): three is too much to draw
# and to read. Repeats of three belong to modifiers that carry a grammatical meaning, not to the base forms.
UNEVEN_FORMS = ("fish",)          # a diamond with a smaller wedge for a tail: repeated parts must be the same size
TRIPLE_FORMS = UNEVEN_FORMS + ("peak3", "tri3m", "sidezig3", "zigzag", "arch3", "wave3", "crenel3", "eps")      # eps: an E-like sigma with three curves on one side
for _fam in FORMS:
    for _n in TRIPLE_FORMS:
        FORMS[_fam].pop(_n, None)
FORMS["classic"].pop("E", None)        # its short middle bar almost, but not quite, matches the other two: "comb" is the even version
# "stroke" has no figure table: its letters are made one by one by kana.py (each is its own arrangement of short strokes)
FORMS["stroke"] = {}
MODS["stroke"] = []
FAMILIES = ("spikey", "curvy", "bubbly", "boxy", "classic", "stroke")
NATIVE_STYLE["classic"] = "mixed"
NATIVE_STYLE["stroke"] = "mixed"
MODS["classic"] = ["stem_up", "stem_down", "stem_left", "stem_right", "bar_h", "bar_v", "dot_in", "open", "through_v", "through_h", "hook"]
for _fam in ("spikey", "bubbly", "boxy"):
    if "open" not in MODS[_fam]:
        MODS[_fam].append("open")
