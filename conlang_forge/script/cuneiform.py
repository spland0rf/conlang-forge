"""The cuneiform hand of the stroke family (Akkadian-, Sumerian-like signs): a sign is a small cluster of wedges pressed into
clay. A wedge is a filled triangle, wide at the head and thin at the tail. The strokes are the usual dicts (a closed
polygon) with `fill: True`, so every other step (placing, stretching, measuring, the SVG) treats them like any stroke.

Wedge kinds, as in the Neo-Assyrian script: a horizontal one (head on the left, tail to the right), a vertical one (head
at the top, tail down), a diagonal one (head at the upper left, tail to the lower right, or the other way up), and the
Winkelhaken, a small "<" made of two short wedges that meet at a point. A sign is rows of horizontals, columns of
verticals, crossed or hung wedges and corner wedges. Archetypes are `rng -> strokes` in the unit box (y up)."""
from __future__ import annotations

import math

K = "s"                  # wedges are straight-edged and sharp


def _r(v):
    return round(v, 3)


def wedge(x, y, deg, length, head=.19):
    """A wedge whose head is centred on (x, y) and whose tail points `deg` degrees (0 = right, -90 = down) for `length`."""
    a = math.radians(deg)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy * head / 2, dx * head / 2
    tip = (x + dx * length, y + dy * length)
    return {"p": [[_r(x + px), _r(y + py)], [_r(x - px), _r(y - py)], [_r(tip[0]), _r(tip[1])]], "closed": True, "fill": True, "k": K}


def winkel(x, y, size=.2, head=.12):
    """The corner wedge: two short wedges whose tails meet at the point (x, y), opening to the right (a small "<")."""
    dy = size * .6
    L = math.hypot(size, dy)
    t = math.degrees(math.atan2(dy, size))
    return [wedge(x + size, y + dy, 180 + t, L, head), wedge(x + size, y - dy, 180 - t, L, head)]


def _j(rng, v, a=.04):
    return v + rng.uniform(-a, a)


def _hs(rng, n, y0=.12, y1=.88, x0=.06, w=.8, head=.19):
    """n horizontal wedges stacked from y1 down to y0, heads on the left; lengths differ a little."""
    gap = min((y1 - y0) / max(n - 1, 1), .3)                 # rows lie close, so their heads touch as in a pressed sign
    ys = [(y0 + y1) / 2 + (i - (n - 1) / 2) * -gap for i in range(n)] if n > 1 else [(y0 + y1) / 2]
    return [wedge(_j(rng, x0, .02), _j(rng, y, .03), _j(rng, 0, 3), _j(rng, w, .06), head) for y in ys]


def _vs(rng, n, x0=.12, x1=.88, top=.96, ln=.9, head=.19):
    """n vertical wedges side by side from x0 to x1, heads at the top."""
    gap = min((x1 - x0) / max(n - 1, 1), .26)
    xs = [(x0 + x1) / 2 + (i - (n - 1) / 2) * gap for i in range(n)] if n > 1 else [(x0 + x1) / 2]
    return [wedge(_j(rng, x, .03), _j(rng, top, .02), _j(rng, -90, 3), _j(rng, ln, .05), head) for x in xs]


# ---- archetypes ------------------------------------------------------------------------------------------------------------
def c_hrows(rng):                         # rows of horizontal wedges, one under another
    return _hs(rng, rng.choice([2, 3, 3, 4]))


def c_vrow(rng):                          # columns of vertical wedges side by side
    return _vs(rng, rng.choice([2, 3, 3, 4]), .1, .9)


def c_cross(rng):                         # a horizontal wedge crossed by a vertical one (and sometimes a second)
    s = _hs(rng, 1, .5, .5, .05, .88, .2) + _vs(rng, 1, .42, .42, .98, .95, .2)
    if rng.random() < .5:
        s += _vs(rng, 1, .72, .72, .98, .95, .2)
    return s


def c_hang(rng):                          # a long horizontal wedge with verticals hanging from it
    return _hs(rng, 1, .9, .9, .05, .9, .19) + _vs(rng, rng.choice([2, 3]), .12, .85, .82, .72, .19)


def c_stand(rng):                         # verticals standing on a long horizontal wedge
    return _vs(rng, rng.choice([2, 3]), .12, .85, .98, .6, .19) + _hs(rng, 1, .16, .16, .05, .9, .19)


def c_winkel_v(rng):                      # corner wedges (a stack of 1-3) beside a vertical wedge: ten and one
    n = rng.choice([1, 2, 3])
    s = []
    for i in range(n):
        s += winkel(_j(rng, .02, .02), .74 - i * (.78 / max(n, 2)), rng.uniform(.26, .3))
    return s + _vs(rng, 1, .72, .72, .98, .96, .2)


def c_winkel_h(rng):                      # corner wedges over rows of horizontals
    s = winkel(.02, .76, .3) + winkel(.52, .76, .3) if rng.random() < .5 else winkel(.2, .76, .34)
    return s + _hs(rng, rng.choice([1, 2]), .1, .4, .05, .85, .19)


def c_roof(rng):                          # two diagonal wedges meeting at the bottom (a V), with a vertical or a bar in some
    s = [wedge(_j(rng, .08), .96, -rng.uniform(52, 66), rng.uniform(.82, .95), .19), wedge(_j(rng, .92), .96, -(180 - rng.uniform(52, 66)), rng.uniform(.82, .95), .19)]
    r = rng.random()
    if r < .35:
        s += _vs(rng, 1, .5, .5, .96, .95, .17)
    elif r < .7:
        s += _hs(rng, 1, .12, .12, .1, .8, .17)
    return s


def c_tri(rng):                           # a triangle of three verticals: two over one
    return [wedge(_j(rng, .2), .98, -90, .5, .19), wedge(_j(rng, .62), .98, -90, .5, .19), wedge(_j(rng, .41), .5, -90, .5, .19)]


def c_diag_h(rng):                        # a diagonal wedge across a horizontal one
    return _hs(rng, 1, rng.uniform(.4, .6), .5, .05, .9, .19) + [wedge(_j(rng, .12), .98, -rng.uniform(55, 70), .98, .19)]


def c_split(rng):                         # rows of horizontals on the left, columns of verticals on the right
    return _hs(rng, rng.choice([2, 3]), .1, .88, .04, .42, .17) + _vs(rng, rng.choice([2, 3]), .62, .92, .98, .94, .17)


def c_sandwich(rng):                      # a horizontal wedge above and below, a vertical through both
    return _hs(rng, 2, .08, .9, .05, .9, .19) + _vs(rng, 1, _j(rng, .5, .1), .98, .96, .19)


def c_rise(rng):                          # a rising diagonal with verticals behind it
    s = _vs(rng, rng.choice([1, 2]), .12, .5, .98, .9, .19)
    return s + [wedge(_j(rng, .3), .08, rng.uniform(38, 52), .8, .19)]


def c_double_cross(rng):                  # two horizontals through two verticals (a grid of wedges)
    return _hs(rng, 2, .3, .7, .05, .9, .17) + _vs(rng, 2, .3, .7, .98, .95, .17)


ARCHETYPES = {"hrows": c_hrows, "vrow": c_vrow, "cross": c_cross, "hang": c_hang, "stand": c_stand, "winkel_v": c_winkel_v,
              "winkel_h": c_winkel_h, "roof": c_roof, "tri": c_tri, "diag_h": c_diag_h, "split": c_split, "sandwich": c_sandwich,
              "rise": c_rise, "double_cross": c_double_cross}
FILL = (.62, .5)           # the least height and width of a sign
