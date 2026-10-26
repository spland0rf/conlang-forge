"""Stroke vocabularies built from hand-drawn stroke charts of real scripts (pen v3). Each is a family of recipes for the pen hand:

  headline  Devanagari and Bengali: a top bar (added by the caller) over a T-stem, with body atoms hung beside it: a triangle head, a
            two-hump "3", a ring, a hook hanging off the bar, a short drop with a body under it, an S, two hooked arms; and small extras
            (a curl at the foot, a short crossing bar, a mark at the top) that give the letters their many strokes and junctions;
  foot      Tamil: letters on a foot bar (an L with a post, an arch, a tick, or an inner loop), shoulders (a bar over two verticals with
            a hooked tail), chains of loops, a base swoop that starts in an oval, and the bells of pen v2;
  loop_head Thai: a loop at the head with a stem or cap, an arch, a foot bar or a hooked tail;
  jamo      Hangul: straight bars, drops and rings: corners, open boxes, boxes, ladders, a pair of diagonals, a ring with a tick,
            stems with ticks and bars with ticks.

Every recipe is a list of strokes: a stroke that is only horizontal or vertical segments is one stroke per segment, a smooth curve is
one stroke. Values are drawn from the pen's fixed vocabulary (guide lines, columns, arm lengths, radii), so letters line up."""
from __future__ import annotations

import math

from .geometry import stroke as _stroke
from .pen import (ARM, BASE, CENTER, DIAG, HI, LO, MID, RAD, RIGHT, TICK, TOP, Pen, _bell, _c, _stem, f_a, f_bell, f_h_bell,
                  f_v_bell, f_loop_tail, f_ring_tick, f_hook_stem, f_angle, f_cup_tick, f_arc_stem, f_spiral,
                  s_arm_bowl, s_two_arms, s_two_stems, s_bowl_stem, s_slant_stem, s_foot_hook, s_arm_loop, s_stem_ring, s_fork)

HEAD_EXTRA = 0.5       # chance that a headline letter gets one more small stroke at a fixed place


# ---- headline ---------------------------------------------------------------------------------------------------------------
def _hx(rng):
    return _c(rng, CENTER, RIGHT)


def _extra(p, rng, sx):
    """One more small stroke at a fixed place on the stem: a curl at the foot, a short bar across MID, a mark at HI on the right."""
    if rng.random() >= HEAD_EXTRA:
        return
    how = _c(rng, "curl", "cross", "mark")
    if how == "curl":
        p.begin(sx, BASE + .1, -90)
        p.arc(-120, .09)
    elif how == "cross":
        p.begin(sx - .12, MID - .05, 0)
        p.line(.24)
    else:
        p.begin(sx, HI, 0)
        p.line(TICK)


def h_tri(rng, style):                        # a stem with a triangle head hung on its left: two slants meeting at a point (ब ক ঘ ধ)
    p = Pen(rng, style)
    sx = _hx(rng)
    _stem(p, sx)
    w = _c(rng, .26, .34, .42)
    p.begin(sx, HI, 0)
    p.to(sx - w, MID)
    p.to(sx, LO)
    if rng.random() < .3:
        p.begin(sx - w, MID, 0)
        p.arc(360, .06)
    _extra(p, rng, sx)
    return p.done()


def h_hump2(rng, style):                      # a stem with a "3" on its left: two bumps one above the other, each an arm out, a half-turn and an arm back (अ आ ও)
    p = Pen(rng, style)
    sx = RIGHT
    _stem(p, sx)
    r = _c(rng, .11, .13)
    arm = _c(rng, .35, .42)
    y = _c(rng, HI, HI + .1)
    for k in range(2):
        p.begin(sx, y - 2 * r * k, 180)
        p.line(arm)
        p.arc(180, r)
        p.line(arm)
    _extra(p, rng, sx)
    return p.done()


def h_ring(rng, style):                       # a ring hung on the left of the stem, touching it (ठ ড ভ)
    p = Pen(rng, style)
    sx = _hx(rng)
    _stem(p, sx)
    r = _c(rng, RAD[1], RAD[2])
    p.begin(sx, _c(rng, MID, MID - .05), 90)
    p.arc(360, r)
    _extra(p, rng, sx)
    return p.done()


def h_hook_hang(rng, style):                  # no stem: a hook that hangs from the bar a little right of centre and swings left (र)
    p = Pen(rng, style)
    x = _c(rng, .65, .72)
    p.begin(x, TOP, -90)
    p.line(_c(rng, .3, .4))
    p.arc(-100, _c(rng, .28, .34))
    p.line(.15)
    _extra(p, rng, x)
    return p.done()


def h_drop_body(rng, style):                  # a drop from the bar that sweeps round into a hook (ह ध)
    p = Pen(rng, style)
    x = _c(rng, .2, .3)
    p.begin(x, TOP, -90)
    p.line(_c(rng, .28, .32))
    p.arc(150, _c(rng, .33, .37))
    return p.done()


def h_s(rng, style):                          # an S-curve of two half-turns beside a stem (জ ঞ)
    p = Pen(rng, style)
    sx = RIGHT
    _stem(p, sx)
    r = _c(rng, .11, .14)
    p.begin(sx - .3, HI, 0)
    p.arc(-180, r)
    p.arc(180, r)
    _extra(p, rng, sx)
    return p.done()


def h_two_hook(rng, style):                   # a stem with two arms to the left that turn down at their ends (घ ধ)
    p = Pen(rng, style)
    sx = _hx(rng)
    _stem(p, sx)
    for y in (HI, LO + .08):
        p.begin(sx, y, 180)
        p.line(_c(rng, .3, .4))
        p.arc(90, .12)
    _extra(p, rng, sx)
    return p.done()


# ---- bengali (a top bar over a stem: bowls, loops, S-curves and diagonals) -------------------------------------------------------
def b_bowl(rng, style):                       # a bowl hung on the left of the stem, its two ends on the stem (ঠ ড ভ)
    p = Pen(rng, style)
    sx = _c(rng, CENTER, RIGHT)
    _stem(p, sx)
    r = _c(rng, .2, .24, .27)
    y = _c(rng, HI, HI + .05)
    p.begin(sx, y, 180)
    p.arc(_c(rng, 180, 180, 150), r)
    return p.done()


def b_loop_arm(rng, style):                   # a stem with an arm to the left that ends turned down (ই ঈ forms; the tight loop is added after)
    p = Pen(rng, style)
    sx = _c(rng, CENTER, RIGHT)
    _stem(p, sx)
    p.begin(sx, _c(rng, MID, HI), 180)
    p.line(_c(rng, .3, .4))
    p.arc(_c(rng, 90, 120), _c(rng, .1, .14))
    return p.done()


def b_diag_x(rng, style):                     # two slants that cross each other beside the stem (ফ ষ শ)
    p = Pen(rng, style)
    sx = RIGHT
    _stem(p, sx)
    w = _c(rng, .4, .5)
    p.begin(sx - w, HI + .1, 0)
    p.to(sx, LO - .05)
    p.begin(sx - w, LO - .05, 0)
    p.to(sx, HI + .1)
    return p.done()


def b_foot_curl(rng, style):                  # a stem that curls to the left at its foot (ক খ forms)
    p = Pen(rng, style)
    sx = _c(rng, CENTER, RIGHT)
    s0 = p.begin(sx, TOP, -90)
    p.line(TOP - .25)
    p.arc(-_c(rng, 120, 150, 180), _c(rng, .14, .18, .22))
    return p.done()


def b_angle(rng, style):                      # a drop from the bar that turns hard and climbs back as a slant: an acute apex (ত ন forms)
    p = Pen(rng, style)
    x = _c(rng, .25, .35)
    p.begin(x, TOP, -90)
    p.line(_c(rng, .75, .85))
    p.turn(_c(rng, 140, 155))
    p.line(_c(rng, .45, .6))
    return p.done()


def b_zigzag(rng, style):                     # a drop, a hard turn up-right, a second hard turn down: a Z or N body (ন ণ)
    p = Pen(rng, style)
    x = _c(rng, .15, .25)
    p.begin(x, TOP, -90)
    p.line(_c(rng, .75, .85))
    p.turn(_c(rng, 140, 155))
    p.line(_c(rng, .7, .85))
    p.turn(-_c(rng, 140, 155))
    p.line(_c(rng, .4, .55))
    return p.done()


def b_vee(rng, style):                        # a stem with a V of two straight slants meeting in a sharp point, its ends on the stem (ম য)
    p = Pen(rng, style)
    sx = RIGHT
    _stem(p, sx)
    w = _c(rng, .4, .5)
    y0, y1 = _c(rng, HI, HI + .05), _c(rng, LO, LO + .08)
    p.begin(sx, y0, 0)
    p.to(sx - w, (y0 + y1) / 2 + _c(rng, -.1, 0, .1))
    p.to(sx, y1)
    return p.done()


def b_flag(rng, style):                       # a slant from the bar to the stem and a straight leg out below it, joined at corners (ক ত)
    p = Pen(rng, style)
    sx = _c(rng, CENTER, RIGHT)
    _stem(p, sx)
    w = _c(rng, .4, .55)
    ym = _c(rng, MID, MID + .1)
    p.begin(sx - w, TOP, 0)
    p.to(sx, ym)
    p.to(sx - w * _c(rng, .6, 1.0), LO)
    return p.done()


def b_arrow(rng, style):                      # a stem with a horizontal leg and a slant that leave it at one point (ণ ন forms)
    p = Pen(rng, style)
    sx = _c(rng, CENTER, RIGHT)
    _stem(p, sx)
    w = _c(rng, .55, .65)
    y = _c(rng, MID - .1, MID + .1)
    p.begin(sx - w, y + _c(rng, .25, .35), 0)
    p.to(sx, y)
    p.to(sx - w, y - _c(rng, .3, .4))
    return p.done()


def b_drop_loop(rng, style):                  # a drop from the bar that loops and crosses itself, then runs on (হ)
    p = Pen(rng, style)
    x = _c(rng, .45, .55, .65)
    p.begin(x, TOP, -90)
    p.line(_c(rng, .5, .58))
    r = _c(rng, .1, .13)
    p.arc(_c(rng, 1, -1) * 270, r)
    p.line(_c(rng, .4, .5))
    return p.done()


def b_s_hook(rng, style):                     # an S-curve that hangs from the bar and ends in a hook beside a short stem (জ ঞ)
    p = Pen(rng, style)
    x = _c(rng, .3, .45)
    p.begin(x, TOP, -90)
    p.line(.1)
    r = _c(rng, .12, .15)
    p.arc(90, r)
    p.arc(-180, r)
    p.arc(_c(rng, 150, 200), r)
    return p.done()


HEADLINE = {"h_tri": h_tri, "h_hump2": h_hump2, "h_ring": h_ring, "h_hook_hang": h_hook_hang, "h_drop_body": h_drop_body, "h_s": h_s,
            "h_two_hook": h_two_hook}
HEADLINE_OLD = {"arm_bowl": s_arm_bowl, "two_arms": s_two_arms, "two_stems": s_two_stems, "bowl_stem": s_bowl_stem, "slant_stem": s_slant_stem,
                "foot_hook": s_foot_hook, "arm_loop": s_arm_loop, "stem_ring": s_stem_ring, "fork": s_fork}


# ---- foot (Tamil) -----------------------------------------------------------------------------------------------------------
def t_cup(rng, style):                        # an L (a vertical and a foot bar) with a post, an arch, a tick, or an inner loop and tail (ட ப ம ய ழ)
    p = Pen(rng, style)
    w = _c(rng, .6, .8)
    p.begin(0, TOP, -90)
    p.line(TOP)
    p.begin(0, BASE, 0)
    p.line(w)
    kind = _c(rng, "post", "post", "arch", "loop")
    if kind == "post":
        p.begin(w, BASE, 90)
        p.line(_c(rng, TOP, HI))
        if rng.random() < .6:                                   # a small ring or curl at the top of the post
            p.arc(-_c(rng, 200, 320), _c(rng, .07, .1))
    elif kind == "arch":
        p.begin(w * .4, BASE, 90)
        p.line(.2)
        p.arc(-180, .15)
        p.line(.2)
    elif kind == "tick":
        p.begin(0, MID, 180)
        p.line(.15)
        p.begin(w, BASE, 90)
        p.line(HI)
    else:
        p.begin(.3, MID, 90)
        p.arc(360, .15)
        p.begin(w, BASE, 0)
        p.arc(-120, .2)
    return p.done(rng.random() < .3, fit=True, hang=False)


def t_shoulder(rng, style):                   # a bar over two verticals, the right one ending in a hooked tail (ந ர ற)
    p = Pen(rng, style)
    w = _c(rng, .6, .8)
    p.begin(0, TOP, 0)
    p.line(w)
    p.begin(0, TOP, -90)
    p.line(TOP)
    p.begin(w, TOP, -90)
    p.line(_c(rng, TOP, .8))
    if rng.random() < .6:
        p.arc(-110, _c(rng, .15, .2))
    return p.done(rng.random() < .3, fit=True, hang=rng.random() < .3)


def t_chain(rng, style):                      # two or three small rings in a row, each ring touching the arm before it, and a vertical from the last (ண ள ன)
    p = Pen(rng, style)
    r = _c(rng, .1, .12)
    xe = .12 + 2 * r                            # the east point of the first ring
    for _ in range(_c(rng, 2, 2, 3)):
        p.begin(xe, MID, 90)
        p.arc(360, r)                           # a ring whose far side is its start
        p.turn(-90)
        p.line(_c(rng, .12, .18))               # the arm, leaving from the ring's east point
        xe = p.x + 2 * r                        # the next ring touches the arm's end with its west point
    p.begin(p.x, p.y, -90)
    p.line(_c(rng, MID, .7))
    return p.done(False, fit=True, hang=False)


def t_oval_swoop(rng, style):                 # a base swoop that starts in a closed oval and rises at its far end (the foot of ஶ்ரீ)
    p = Pen(rng, style)
    r = _c(rng, .1, .12)
    p.begin(.3, MID - .3, 90)
    p.arc(360, r)
    p.turn(-90)
    p.line(_c(rng, .3, .45))
    p.arc(90, _c(rng, .2, .28))
    p.begin(.3 - r, TOP, -90)                   # a vertical that comes down onto the top of the oval
    p.line(TOP - (MID - .3) - r)
    return p.done(False, fit=True, hang=False)


def t_vertical(rng, style):                   # a vertical, a bar off it, and a bell swoop that ends in an open curl; sometimes crossed (அ ஆ எ ஏ)
    p = Pen(rng, style)
    p.begin(0, TOP, -90)
    p.line(TOP)
    yb = _c(rng, .25, .3)
    p.begin(0, yb, 0)
    p.line(_c(rng, .15, .25))
    p.arc(_c(rng, 150, 180), _c(rng, .2, .27))
    p.arc(-_c(rng, 150, 190), _c(rng, .1, .14))
    if rng.random() < .4:
        p.begin(-.1, _c(rng, MID, .6), 0)
        p.line(.3)
    return p.done(False, fit=True, hang=False)


def t_ring_swoop(rng, style):                 # a ring, and a bell swoop from it that ends in an open (not closed) curl (ஐ ஒ ஓ ஔ)
    p = Pen(rng, style)
    r = _c(rng, .12, .15)
    p.begin(.15 + r, HI, 90)
    p.arc(360, r)
    p.turn(-90)
    p.line(_c(rng, .3, .4))
    p.arc(-_c(rng, 150, 180), _c(rng, .2, .26))
    p.arc(_c(rng, 150, 200), _c(rng, .09, .13))
    if rng.random() < .35:
        p.begin(.15, TOP, -90)
        p.line(.35)
    return p.done(False, fit=True, hang=False)


def t_loop_cross(rng, style):                 # a vertical that curls at its foot back onto itself, with a bar across where the curl closes (க ச)
    p = Pen(rng, style)
    p.begin(.2, TOP, -90)
    p.line(_c(rng, .5, .6))
    r = _c(rng, .1, .13)
    y0 = p.y
    p.arc(-270, r)                              # round to the left and back up to the vertical
    p.line(r)                                   # ... ending on it
    yb = y0 + 2 * r + .12                       # the bar sits above the curl, clear of it
    p.begin(.2 - .25, yb, 0)
    p.line(_c(rng, .5, .6))
    return p.done(False, fit=True, hang=False)


def t_s_circle(rng, style):                   # an S-curve that ends in a closed circle (ஜ)
    p = Pen(rng, style)
    r = _c(rng, .12, .14)
    p.begin(.25, TOP, 0)
    p.arc(-_c(rng, 150, 180), _c(rng, .15, .2))
    p.arc(_c(rng, 150, 180), _c(rng, .15, .2))
    p.arc(360, r)
    return p.done(False, fit=True, hang=False)


def t_self_cross(rng, style):                 # one stroke that runs down, loops round and crosses itself at a right angle (இ ச ட forms)
    p = Pen(rng, style)
    r = _c(rng, .1, .14)
    p.begin(.2, TOP, -90)
    p.line(_c(rng, .45, .6))
    p.arc(270, r)                               # down, east, up, then west across the vertical
    p.line(_c(rng, .35, .5))                    # carried on past the crossing
    if rng.random() < .5:
        p.arc(-_c(rng, 150, 200), _c(rng, .1, .14))
    if rng.random() < .4:
        p.begin(.2, TOP, 0)
        p.line(_c(rng, .35, .5))
    return p.done(False, fit=True, hang=False)


def t_stacked_loops(rng, style):              # one stroke down a vertical that loops and crosses itself two or three times (ஐ ஜ forms)
    p = Pen(rng, style)
    r = _c(rng, .08, .1)
    p.begin(.25, TOP, -90)
    p.line(.1)
    for _ in range(_c(rng, 2, 2, 3)):
        p.arc(270, r)                           # round to the right and back across the line
        p.arc(-90, r)                           # swing down again, left of the vertical
        p.line(.04)
    return p.done(False, fit=True, hang=False)


def t_bowl(rng, style):                       # a wide bowl that ends in a vertical, with a curl or a ring at the foot (ம ய வ ல forms)
    p = Pen(rng, style)
    w = _c(rng, .5, .7)
    p.begin(0, MID + .1, -90)
    p.line(_c(rng, .15, .25))
    p.arc(90, _c(rng, .18, .24))
    p.line(w)
    p.arc(90, _c(rng, .18, .24))
    p.line(_c(rng, .35, .55))
    kind = _c(rng, "curl", "ring", "none")
    if kind == "curl":
        p.arc(_c(rng, 150, 200), _c(rng, .07, .1))
    elif kind == "ring":
        p.arc(360, _c(rng, .08, .11))
    return p.done(False, fit=True, hang=False)


def t_wave(rng, style):                       # a long wave: two or three humps in one stroke, ending in a ring or a hook (ள ழ ண forms)
    p = Pen(rng, style)
    r = _c(rng, .1, .13)
    p.begin(0, MID, 90)
    for i in range(_c(rng, 2, 2, 3)):
        p.arc((-1) ** i * 180, r)
    kind = _c(rng, "ring", "hook", "none")
    if kind == "ring":
        p.arc(360, _c(rng, .08, .1))
    elif kind == "hook":
        p.arc(-_c(rng, 120, 180), _c(rng, .08, .12))
    p.begin(0, BASE, 90)
    p.line(TOP)
    return p.done(False, fit=True, hang=False)


def t_ring_stem(rng, style):                  # a stem ending tangent in a closed circle, with a crossing bar (ஞ ங forms)
    p = Pen(rng, style)
    r = _c(rng, .1, .14)
    p.begin(.3, TOP, -90)
    p.line(_c(rng, .4, .5))
    p.arc(_c(rng, 1, -1) * 360, r)
    if rng.random() < .6:
        p.begin(-.05, _c(rng, HI, MID), 0)
        p.line(_c(rng, .4, .6))
    if rng.random() < .5:
        p.begin(.3 + 2 * r + .05, BASE + .15, 90)
        p.arc(-_c(rng, 150, 200), _c(rng, .1, .14))
    return p.done(False, fit=True, hang=False)


# ---- attached parts (Tamil) -------------------------------------------------------------------------------------------------
def _along(pts, f):
    """The point at fraction f of the way along a polyline, and the unit direction there."""
    seg = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    tot = sum(seg) or 1e-6
    d, i = f * tot, 0
    while i < len(seg) - 1 and d > seg[i]:
        d -= seg[i]
        i += 1
    a, b = pts[i], pts[i + 1]
    t = d / (seg[i] or 1e-6)
    ux, uy = (b[0] - a[0]) / (seg[i] or 1e-6), (b[1] - a[1]) / (seg[i] or 1e-6)
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), (ux, uy)


def _hit(a, b, c, d):
    """Do segments ab and cd properly cross?"""
    r = (b[0] - a[0], b[1] - a[1])
    w = (d[0] - c[0], d[1] - c[1])
    den = r[0] * w[1] - r[1] * w[0]
    if abs(den) < 1e-9:
        return False
    t = ((c[0] - a[0]) * w[1] - (c[1] - a[1]) * w[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    return 0.02 < t < 0.98 and 0.02 < u < 0.98


def _cross_point(a, b, c, d):
    r = (b[0] - a[0], b[1] - a[1])
    w = (d[0] - c[0], d[1] - c[1])
    den = r[0] * w[1] - r[1] * w[0] or 1e-9
    t = ((c[0] - a[0]) * w[1] - (c[1] - a[1]) * w[0]) / den
    return (a[0] + t * r[0], a[1] + t * r[1])


def _thin(pts, step=.05):
    """The polyline with points at least `step` apart (the ends are kept): the rules need the shape, not every smoothing point."""
    out = [pts[0]]
    for q in pts[1:-1]:
        if math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) >= step:
            out.append(q)
    out.append(pts[-1])
    return out


def _box(pts):
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _apart(a, b, gap):
    """True if the bounding boxes a and b are more than `gap` apart."""
    return a[0] - b[2] > gap or b[0] - a[2] > gap or a[1] - b[3] > gap or b[1] - a[3] > gap


def _dist(pt, pts):
    """Distance from a point to a polyline."""
    best = 9.0
    for a, b in zip(pts, pts[1:]):
        abx, aby = b[0] - a[0], b[1] - a[1]
        l2 = abx * abx + aby * aby
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((pt[0] - a[0]) * abx + (pt[1] - a[1]) * aby) / l2))
        best = min(best, math.hypot(pt[0] - a[0] - t * abx, pt[1] - a[1] - t * aby))
    return best


def _inside(pt, ring):
    c = False
    for a, b in zip(ring, ring[1:]):
        if (a[1] > pt[1]) != (b[1] > pt[1]) and pt[0] < (b[0] - a[0]) * (pt[1] - a[1]) / (b[1] - a[1]) + a[0]:
            c = not c
    return c


def _dense(pts, step=.03):
    """The polyline with points every `step` or so, so that a straight two-point stroke is sampled along its length."""
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]
    return out


def _closed(pts):
    return len(pts) > 6 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < .04


def _parallel_close(P):
    """Two strokes that run side by side, close but not touching (parallel, a few hundredths apart over a stretch), look like a drawing error."""
    D = [_dense(pts, .04) for pts in P]
    B = [_box(pts) for pts in P]
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            if _apart(B[i], B[j], .1):
                continue
            hits = 0
            for k in range(1, len(D[i]) - 1):
                q = D[i][k]
                t1 = (D[i][k + 1][0] - D[i][k - 1][0], D[i][k + 1][1] - D[i][k - 1][1])
                best, bt = 9.0, None
                for m in range(1, len(D[j]) - 1):
                    dd = math.hypot(q[0] - D[j][m][0], q[1] - D[j][m][1])
                    if dd < best:
                        best, bt = dd, (D[j][m + 1][0] - D[j][m - 1][0], D[j][m + 1][1] - D[j][m - 1][1])
                if .012 < best < .09 and bt:
                    c = abs(t1[0] * bt[0] + t1[1] * bt[1]) / ((math.hypot(*t1) * math.hypot(*bt)) or 1e-9)
                    if c > .96:
                        hits += 1
            if hits >= 4:
                return True
    return False


def _sound(strokes, selfx=False, maxloops=3, bar=False):
    """The rules a Tamil letter keeps: every stroke is joined to the rest; no stroke runs through a closed ring or ends inside one; no two
    strokes run along each other; the letter fills its box."""
    P = [_thin([tuple(q) for q in st["p"]]) for st in strokes]
    if bar:                                                        # the top bar the caller draws is one more stroke, along y = 1
        P = P + [[(0.0, 1.0), (1.0, 1.0)]]
    n = len(P)
    xs = [x for pts in P for x, _ in pts]
    ys = [y for pts in P for _, y in pts]
    if max(ys) - min(ys) < (.4 if bar else .7) or max(xs) - min(xs) < .3:
        return False
    B = [_box(pts) for pts in P]
    near = {i: set() for i in range(n)}                          # joined: an end of one lies on the other
    for i in range(n):
        for j in range(n):
            if i < j and not _apart(B[i], B[j], .036) and (_dist(P[i][0], P[j]) < .035 or _dist(P[i][-1], P[j]) < .035 or _dist(P[j][0], P[i]) < .035 or _dist(P[j][-1], P[i]) < .035
                          or any(_hit(a, b, c, d) for a, b in zip(P[i], P[i][1:]) for c, d in zip(P[j], P[j][1:]))):
                near[i].add(j)                                 # joined: an end lies on the other, or they cross
                near[j].add(i)
    seen, todo = {0}, [0]
    while todo:
        for j in near[todo.pop()]:
            if j not in seen:
                seen.add(j)
                todo.append(j)
    if len(seen) < n:
        return False
    polys = []                                                     # the loops: a ring, or any stretch of a stroke that comes back to itself
    for i, pts in enumerate(P):
        d = _dense(pts, .05)
        k = 0
        while k < len(d) - 6:
            m = next((m for m in range(k + 6, len(d)) if math.hypot(d[k][0] - d[m][0], d[k][1] - d[m][1]) < .055), None)
            if m is None:
                k += 1
                continue
            polys.append((i, d[k:m + 1]))
            if not selfx:                                          # the rest of the same stroke must not cut back across its own loop
                rest = d[:k + 1], d[m:]
                for part in rest:
                    for a, b in zip(part, part[1:]):
                        for c, e in zip(d[k:m + 1], d[k + 1:m + 1]):
                            if _hit(a, b, c, e) and math.hypot(_cross_point(a, b, c, e)[0] - d[k][0], _cross_point(a, b, c, e)[1] - d[k][1]) > .05:
                                return False
            k = m
    for i, poly in polys:
        pb = _box(poly)
        for j in range(n):
            if j == i or _apart(pb, B[j], .05):
                continue
            if any(_inside(e, poly) and _dist(e, poly) > .03 for e in (P[j][0], P[j][-1])):
                return False                                       # a stroke ends inside a loop
            anchors = [e for e in (P[j][0], P[j][-1]) if _dist(e, poly) < .035]          # where it is attached to the loop
            for a, b in zip(P[j], P[j][1:]):
                for c, d in zip(poly, poly[1:]):
                    if _hit(a, b, c, d):
                        x = _cross_point(a, b, c, d)
                        if not any(math.hypot(x[0] - e[0], x[1] - e[1]) < .045 for e in anchors):
                            return False                           # a stroke runs through a loop (away from where it is attached)
    cents = [(i, (sum(q[0] for q in poly) / len(poly), sum(q[1] for q in poly) / len(poly))) for i, poly in polys]
    for u in range(len(cents)):
        for v in range(u + 1, len(cents)):
            if cents[u][0] != cents[v][0] and math.hypot(cents[u][1][0] - cents[v][1][0], cents[u][1][1] - cents[v][1][1]) < .26:
                return False                                       # two loops of different strokes crowded together
    if len(polys) > maxloops:
        return False
    if bar and any(_hit(a, b, (0.0, 1.0), (1.0, 1.0)) for pts in P[:-1] for a, b in zip(pts, pts[1:])):
        return False                                               # a stroke goes up through the bar
    if _parallel_close(P):
        return False
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if i < j and not _apart(B[i], B[j], .03):
                short = _dense(P[i] if len(P[i]) <= len(P[j]) else P[j])
                other = P[j] if short is not None and (P[i] if len(P[i]) <= len(P[j]) else P[j]) is P[i] else P[i]
                if sum(_dist(q, other) < .025 for q in short) > .3 * len(short):
                    return False                                   # running along another stroke
    return True


def _refit(strokes, lo, hi):
    """Bring a letter whose added part stuck out of the box back in: squeezed if it is too big, otherwise moved: x into [0, 1], y into [lo, hi]."""
    xs = [x for st in strokes for x, _ in st["p"]]
    ys = [y for st in strokes for _, y in st["p"]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if x0 >= -1e-6 and x1 <= 1 + 1e-6 and y0 >= lo - 1e-6 and y1 <= hi + 1e-6:
        return strokes
    kx = 1.0 / (x1 - x0) if x1 - x0 > 1 else 1.0
    ky = (hi - lo) / (y1 - y0) if y1 - y0 > hi - lo else 1.0
    nx0, nx1 = x0 * kx, x1 * kx
    dx = -nx0 if nx0 < 0 else (1 - nx1 if nx1 > 1 else 0.0)
    ny0, ny1 = lo + (y0 - lo) * ky, lo + (y1 - lo) * ky
    dy = lo - ny0 if ny0 < lo else (hi - ny1 if ny1 > hi else 0.0)
    return [dict(_stroke([(round(x * kx + dx, 3), round(lo + (y - lo) * ky + dy, 3)) for x, y in st["p"]]), k=st["k"]) for st in strokes]


def _wrap(rng, strokes, gx, gy):
    """An encircling loop: an open cup that leaves the letter from one of its outermost stroke ends and swoops 180 to 270 degrees round the
    outside of the rest of the letter without touching it. None if it would cross a stroke."""
    ends = [tuple(st["p"][k]) for st in strokes for k in (0, -1)]
    ends.sort(key=lambda e: -math.hypot(e[0] - gx, e[1] - gy))
    e = rng.choice(ends[:3])
    R = math.hypot(e[0] - gx, e[1] - gy) * _c(rng, 1.05, 1.2)
    if R < .25:
        return None
    a0 = math.atan2(e[1] - gy, e[0] - gx)
    cx, cy = e[0] - R * math.cos(a0), e[1] - R * math.sin(a0)           # the circle's centre, on the far side of the letter from the end
    sg = _c(rng, 1, -1)
    sweep = math.radians(_c(rng, 180, 210, 240, 270))
    out = [(cx + R * math.cos(a0 + sg * sweep * i / 30), cy + R * math.sin(a0 + sg * sweep * i / 30)) for i in range(31)]
    for pts in ([tuple(q) for q in st["p"]] for st in strokes):
        for a, b in zip(out, out[1:]):
            for c, d in zip(pts, pts[1:]):
                if _hit(a, b, c, d) and min(math.hypot(_cross_point(a, b, c, d)[0] - e[0], _cross_point(a, b, c, d)[1] - e[1]), 9) > .06:
                    return None
    return dict(_stroke([(round(x, 3), round(y, 3)) for x, y in out]), k=strokes[0]["k"])


def _loop_end(rng, strokes):
    """Carry one stroke on past its end into a small loop that crosses the stroke itself at a right angle (the looping end of a Tamil stroke).
    Returns the letter with that stroke lengthened, or None."""
    cands = [(i, k) for i, st in enumerate(strokes) if len(st["p"]) >= 2 and not _closed(st["p"]) for k in (0, -1)]
    i, k = rng.choice(cands)
    pts = [tuple(q) for q in strokes[i]["p"]]
    if k == 0:
        pts = pts[::-1]
    e, q = pts[-1], pts[-2]
    L = math.hypot(e[0] - q[0], e[1] - q[1]) or 1e-6
    dx, dy = (e[0] - q[0]) / L, (e[1] - q[1]) / L
    r = _c(rng, .08, .1, .12)
    sg = _c(rng, 1, -1)
    cx, cy = e[0] - sg * dy * r, e[1] + sg * dx * r
    a0 = math.atan2(e[1] - cy, e[0] - cx)
    new = [(cx + r * math.cos(a0 + sg * math.radians(t)), cy + r * math.sin(a0 + sg * math.radians(t))) for t in range(10, 271, 10)]
    h = math.atan2(dy, dx) + sg * math.radians(270)                # heading when the loop is done: back across the stroke
    new.append((new[-1][0] + 1.3 * r * math.cos(h), new[-1][1] + 1.3 * r * math.sin(h)))
    pts = pts + new
    if k == 0:
        pts = pts[::-1]
    out = list(strokes)
    out[i] = dict(_stroke([(round(a, 3), round(b, 3)) for a, b in pts]), k=strokes[i]["k"])
    return out


def _part(rng, strokes, kinds=("bar", "bar", "ring")):
    """One more stroke on the outside of the letter: a bar leaving a stroke at a right angle (a T or an L), or a small ring touching it
    (a loop flourish). Never inside a shape, never tangent as a tick, never tiny. Returns None if there is nothing to attach to."""
    hosts = [st for st in strokes if len(st["p"]) >= 2 and not _closed(st["p"])]
    if not hosts:
        return None
    host = rng.choice(hosts)
    pts = [tuple(q) for q in host["p"]]
    allp = [q for st in strokes for q in st["p"]]
    gx, gy = sum(q[0] for q in allp) / len(allp), sum(q[1] for q in allp) / len(allp)
    kinds_pick = kinds
    if "wrap" in kinds_pick and rng.random() < 1.0 and kinds_pick[0] == "wrap":
        return _wrap(rng, strokes, gx, gy)
    kind = _c(rng, *kinds)
    f = _c(rng, 0.0, 1.0) if kind == "ring_end" else _c(rng, 0.0, 1.0, .35, .5, .65)
    (x, y), (ux, uy) = _along(pts, f)
    nx, ny = -uy, ux
    if nx * (x - gx) + ny * (y - gy) < 0:                          # leave on the side facing away from the letter's middle
        nx, ny = -nx, -ny
    if kind == "ring_end":                                         # a tangent circle that the stroke ends in (a loop flourish)
        r = _c(rng, .08, .1, .12)
        dx, dy = (ux, uy) if f >= 1 else (-ux, -uy)                # carry on out of the end
        sg = _c(rng, 1, -1)
        cx, cy = x - sg * dy * r, y + sg * dx * r                  # the ring's centre, to the left (sg 1) or right of the way on
        a0 = math.atan2(y - cy, x - cx)
        out = [(cx + r * math.cos(a0 + sg * 2 * math.pi * i / 24), cy + r * math.sin(a0 + sg * 2 * math.pi * i / 24)) for i in range(25)]
    elif kind == "long":                                           # a long straight stroke leaving at a right angle (not a tick)
        l = _c(rng, .4, .5, .6)
        out = [(x, y), (x + nx * l, y + ny * l)]
    elif kind == "arc":                                            # a curved stroke leaving at a right angle and bending away
        r = _c(rng, .2, .25, .3)
        sg = _c(rng, 1, -1)
        out = [(x, y)]
        for i in range(1, 17):
            a = i * math.radians(120) / 16
            out.append((x + r * (nx * math.sin(a) - sg * ux * (1 - math.cos(a))), y + r * (ny * math.sin(a) - sg * uy * (1 - math.cos(a)))))
    elif kind == "bar":
        l = _c(rng, .18, .24, .3)
        out = [(x, y), (x + nx * l, y + ny * l)]
    else:
        r = _c(rng, .09, .11, .13)
        cx, cy = x + nx * r, y + ny * r
        a0 = math.atan2(y - cy, x - cx)
        sg = _c(rng, 1, -1)
        out = [(cx + r * math.cos(a0 + sg * 2 * math.pi * i / 24), cy + r * math.sin(a0 + sg * 2 * math.pi * i / 24)) for i in range(25)]
    return dict(_stroke([(round(a, 3), round(b, 3)) for a, b in out]), k=host["k"])


def _turned(strokes, quarter, flip):
    """The letter turned a quarter turn `quarter` times (and mirrored if flip), then stretched back to fill the box."""
    pts = [[(x, y) for x, y in st["p"]] for st in strokes]
    xs = [x for p in pts for x, _ in p]
    ys = [y for p in pts for _, y in p]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    out = []
    for p in pts:
        q = []
        for x, y in p:
            u, v = (x - x0) / ((x1 - x0) or 1), (y - y0) / ((y1 - y0) or 1)
            for _ in range(quarter):
                u, v = 1 - v, u                                    # a quarter turn about the middle
            q.append((round(1 - u if flip else u, 3), round(v, 3)))
        out.append(q)
    return [dict(_stroke(q), k=st["k"]) for q, st in zip(out, strokes)]


ORIENT = {"t_cup_rings", "t_cup_tail", "t_cup_stem", "t_bowl", "t_s_circle", "t_oval_swoop"}      # recipes drawn open up, right, down or left too


STRUCT, STRUCT2, WRAP, WRAP_FIRST, LOOP_END = .4, .15, .4, .45, .35       # chance of one, then another, long stroke added to a Tamil letter


SELFX = {"t_coil", "t_stacked_loops", "t_self_cross"}       # recipes whose stroke crosses its own loops on purpose


def _with_parts(fn, first=.6, second=.25, bar=False, wrap=True, loopx=None, targets=(2, 3, 3, 4, 4), struct=(("long", "arc", "arc"),)):
    """A Tamil letter: the recipe's strokes, turned if it may be, then parts added one at a time, each kept only if the letter stays sound,
    until the letter has as many strokes as its target (two to four). So a rejected part never makes the letter simpler than it was meant to be."""
    selfx = fn.__name__ in SELFX

    def make(rng, style):
        target = _c(rng, *targets)
        best = None
        for attempt in range(24):
            strokes = fn(rng, style)
            clamped = Pen.last_clamped
            if fn.__name__ in ORIENT and not bar:
                q = _c(rng, 0, 0, 1, 2, 3)
                fl = rng.random() < .5
                if q or fl:
                    strokes = _turned(strokes, q, fl)
            if clamped or not _sound(strokes, selfx, 3, bar):
                continue
            wrapped = False
            if wrap and rng.random() < WRAP_FIRST:                     # an encircling loop first: it counts toward the target like any stroke
                for _ in range(5):
                    extra = _part(rng, strokes, ("wrap",))
                    if extra:
                        more = _refit(strokes + [extra], min(y for st in strokes for _, y in st["p"]), 1.0)
                        if _sound(more, selfx, 3, bar):
                            strokes, wrapped = more, True
                            break
            for _ in range(6):
                if len(strokes) >= min(max(target, len(strokes)), 5) and len(strokes) >= target:
                    break
                kinds = ("wrap",) if (wrap and not wrapped and rng.random() < WRAP) else _c(rng, *struct, ("ring_end",), ("ring_end",))
                extra = _part(rng, strokes, kinds)
                if not extra:
                    continue
                ys0 = min(y for st in strokes for _, y in st["p"])
                more = _refit(strokes + [extra], ys0, 1.0)
                if _sound(more, selfx, 3, bar):
                    strokes = more
                    wrapped = wrapped or kinds == ("wrap",)
            if rng.random() < (LOOP_END if loopx is None else loopx):  # a looping end that crosses its own stroke
                for _ in range(6):
                    more = _loop_end(rng, strokes)
                    if more:
                        more = _refit(more, min(y for st in more for _, y in st["p"]), 1.0)
                        if _sound(more, True, 3, bar):                  # at most three loops in all
                            strokes = more
                            break
            if best is None or len(strokes) > len(best):
                best = strokes
            if len(strokes) >= target:
                return strokes
        return best or fn(rng, style)
    make.__name__ = fn.__name__
    return make


def t_coil(rng, style):                       # a coil: one stroke of tall oval loops that cross themselves two or three times, then a vertical (ஐ ஜ ண forms)
    p = Pen(rng, style)
    n = _c(rng, 2, 2, 3)
    rx, ry = _c(rng, .1, .12), _c(rng, .22, .26, .3)
    adv = _c(rng, .6, .7) * rx * 2                # how far the pen moves right per loop: less than a loop's width, so it crosses itself
    p.begin(0, MID, 0)
    for k in range(1, 24 * n + 1):
        t = 2 * math.pi * k / 24
        p._go(adv * t / (2 * math.pi) - rx * math.sin(t), MID - ry + ry * math.cos(t) * -1 + ry)
    if rng.random() < .6:
        p.begin(p.x, p.y, -90)
        p.line(MID)
    return p.done(False, fit=True, hang=False)


def t_cup_rings(rng, style):                  # a big open cup that ends in a tangent circle at one end or both (ங ஞ ம forms)
    p = Pen(rng, style)
    r1, r2 = _c(rng, .08, .1), _c(rng, .08, .1)
    side = _c(rng, 1, -1)                         # the ring turns the same way as the cup (inside) or the other way (outside)
    p.begin(0, HI, -90)
    both = rng.random() < .5
    if both or rng.random() < .5:
        p.arc(side * 360, r1)
    p.arc(_c(rng, 150, 180), _c(rng, .3, .4))
    if both or not p.strokes[-1]["p"] or rng.random() < .5:
        p.arc(side * 360, r2)
    if rng.random() < .35:
        p.begin(0, TOP, -90)
        p.line(.2)
    return p.done(False, fit=True, hang=False)


def t_cup_tail(rng, style):                   # a big open cup with a tail that drops from its bottom and ends in a circle; a circle at one end (ம ய forms)
    p = Pen(rng, style)
    r1, r2 = _c(rng, .08, .1), _c(rng, .08, .1)
    side = _c(rng, 1, -1)
    R = _c(rng, .3, .36)
    p.begin(0, HI, -90)
    if rng.random() < .6:
        p.arc(side * 360, r1)
    p.arc(180, R)
    if rng.random() < .6:
        p.arc(side * 360, r2)
    xm, ym = (p.strokes[-1]["p"][len(p.strokes[-1]["p"]) // 2])      # a point near the middle of the cup (its bottom)
    ymin = min(y for _, y in p.strokes[-1]["p"])
    xs = [x for x, y in p.strokes[-1]["p"] if abs(y - ymin) < 1e-6]
    p.begin(xs[0] if xs else xm, ymin, -90)
    p.line(_c(rng, .15, .22))
    p.arc(_c(rng, 1, -1) * 360, _c(rng, .07, .09))
    return p.done(False, fit=True, hang=False)


def t_cup_stem(rng, style):                   # a big open cup that ends in a ring at one end and rises into a vertical at the other (ங ஞ forms)
    p = Pen(rng, style)
    R = _c(rng, .26, .32)
    side = _c(rng, 1, -1)
    p.begin(0, HI, -90)
    p.arc(side * 360, _c(rng, .08, .1))
    p.arc(180, R)
    p.line(_c(rng, .2, .3))
    return p.done(False, fit=True, hang=False)


FOOT = {"t_cup": t_cup, "t_shoulder": t_shoulder, "t_chain": t_chain, "t_oval_swoop": t_oval_swoop, "t_vertical": t_vertical,
        "t_ring_swoop": t_ring_swoop, "t_loop_cross": t_loop_cross, "t_s_circle": t_s_circle,
        "t_self_cross": t_self_cross, "t_coil": t_coil, "t_cup_rings": t_cup_rings, "t_cup_tail": t_cup_tail, "t_cup_stem": t_cup_stem, "t_stacked_loops": t_stacked_loops, "t_bowl": t_bowl, "t_wave": t_wave, "t_ring_stem": t_ring_stem}
FOOT = {n: _with_parts(f) for n, f in FOOT.items()}
FOOT_OLD = {"bell": f_bell, "a": f_a, "v_bell": f_v_bell, "h_bell": f_h_bell, "loop_tail": f_loop_tail, "ring_tick": f_ring_tick,
            "hook_stem": f_hook_stem, "angle": f_angle, "cup_tick": f_cup_tick, "arc_stem": f_arc_stem, "spiral": f_spiral}


# ---- loop head (Thai) -------------------------------------------------------------------------------------------------------
def _head(p, rng, cx=None, cy=None):
    """The loop at the head: a ring touching the point (x, y) from the left; returns that point."""
    r = _c(rng, RAD[0], RAD[1])
    cx = _c(rng, .18, .26, .34) if cx is None else cx
    cy = _c(rng, HI, .65) if cy is None else cy
    p.begin(cx + r, cy, 90)
    p.arc(360, r)
    return cx + r, cy


def _foot(p, rng):
    """How a stem ends: bare, a foot bar to the right, a hook to the left or right, or a short tick."""
    how = _c(rng, "none", "bar", "hook_l", "hook_r", "tick")
    if how == "bar":
        p.turn(90)
        p.line(_c(rng, .18, .3))
    elif how == "hook_l":
        p.arc(-150, _c(rng, .12, .18))
    elif how == "hook_r":
        p.arc(150, _c(rng, .12, .18))
    elif how == "tick":
        p.turn(_c(rng, 90, -90))
        p.line(TICK)


def th_ring_stem(rng, style):                 # a ring at the head, a stem from its right side down to the foot (ก ข ค ฆ)
    p = Pen(rng, style)
    x, y = _head(p, rng)
    p.begin(x, y, -90)
    p.line(y - BASE - .1)
    _foot(p, rng)
    if rng.random() < .35:
        r = RAD[0]
        p.begin(x + r, _c(rng, MID, LO + .1), 90)
        p.arc(_c(rng, 360, 180), r)
    return p.done(False, fit=True, hang=False)


def th_ring_cap(rng, style):                  # a ring, a cap that rises over it and comes down on the right into a stem (จ ฉ)
    p = Pen(rng, style)
    x, y = _head(p, rng, _c(rng, .3, .4), MID + .1)
    p.begin(x - .3, y - .1, 90)
    p.line(_c(rng, .1, .2))
    rc = _c(rng, .2, .28, .36)
    p.arc(-180, rc)
    p.line(y - BASE)
    _foot(p, rng)
    return p.done(False, fit=True, hang=False)


def th_arch_stem(rng, style):                 # an arch over a stem on its left and a longer one on its right (น บ ป ม)
    p = Pen(rng, style)
    r = _c(rng, .18, .25, .3)
    p.begin(0, _c(rng, MID, LO + .1), 90)
    p.line(_c(rng, .2, .3))
    p.arc(-180, r)
    p.line(_c(rng, .45, .6))
    _foot(p, rng)
    if rng.random() < .6:
        p.begin(0, _c(rng, MID, LO + .1), -90)
        p.line(_c(rng, .3, .5))
    if rng.random() < .4:
        _head(p, rng, _c(rng, .55, .7), _c(rng, .3, MID))
    return p.done(False, fit=True, hang=False)


def th_s(rng, style):                         # an S of two half-turns under a ring (ส ซ ศ)
    p = Pen(rng, style)
    x, y = _head(p, rng, _c(rng, .2, .3), HI + .1)
    r = _c(rng, .13, .17)
    p.begin(x, y - .1, -90)
    p.arc(180, r)
    p.arc(-180, r)
    _foot(p, rng)
    return p.done(False, fit=True, hang=False)


def th_loop_back(rng, style):                 # a ring, a stem, and a loop that turns back on the stem (ฆ ณ ญ)
    p = Pen(rng, style)
    x, y = _head(p, rng)
    p.begin(x, y, -90)
    p.line(_c(rng, .25, .35))
    p.arc(_c(rng, 270, 360), _c(rng, .1, .14))
    p.line(_c(rng, .15, .25))
    return p.done(False, fit=True, hang=False)


def th_double(rng, style):                    # two rings side by side joined at the top, with a stem from the second (ธ ฒ ฬ)
    p = Pen(rng, style)
    r = _c(rng, RAD[0], RAD[1])
    y = _c(rng, HI, .65)
    p.begin(.1 + 2 * r, y, 90)
    p.arc(360, r)
    p.begin(.1 + 2 * r, y, 0)
    p.line(_c(rng, .06, .12))
    p.arc(360, r)
    p.begin(p.x, p.y, -90)
    p.line(y - BASE - .1)
    _foot(p, rng)
    return p.done(False, fit=True, hang=False)


LOOP_HEAD = {"th_ring_stem": th_ring_stem, "th_ring_cap": th_ring_cap, "th_arch_stem": th_arch_stem, "th_s": th_s,
             "th_loop_back": th_loop_back, "th_double": th_double}


# ---- jamo (Hangul) ----------------------------------------------------------------------------------------------------------
def _seg(p, x, y, heading, length):
    p.begin(x, y, heading)
    p.line(length)


def j_corner(rng, style):                     # a bar and a drop at one end: ㄱ, or a drop and a foot bar: ㄴ
    p = Pen(rng, style)
    if rng.random() < .5:
        _seg(p, 0, TOP, 0, 1)
        _seg(p, 1, TOP, -90, _c(rng, TOP, .7))
    else:
        _seg(p, 0, TOP, -90, TOP)
        _seg(p, 0, BASE, 0, 1)
    return p.done(False, fit=True, hang=False)


def j_open(rng, style):                       # a bar, a drop and a bar under it (ㄷ), with a middle bar for some (ㅌ)
    p = Pen(rng, style)
    _seg(p, 0, TOP, 0, 1)
    _seg(p, 0, TOP, -90, TOP)
    _seg(p, 0, BASE, 0, 1)
    if rng.random() < .5:
        _seg(p, 0, MID, 0, _c(rng, .8, 1))
    return p.done(False, fit=True, hang=False)


def j_box(rng, style):                        # a box of four bars (ㅁ), or two uprights with a middle and a bottom bar (ㅂ)
    p = Pen(rng, style)
    _seg(p, 0, TOP, -90, TOP)
    if rng.random() < .5:
        _seg(p, 0, TOP, 0, 1)
        _seg(p, 1, TOP, -90, TOP)
        _seg(p, 0, BASE, 0, 1)
    else:
        _seg(p, 1, TOP, -90, TOP)
        _seg(p, 0, MID, 0, 1)
        _seg(p, 0, BASE, 0, 1)
    return p.done(False, fit=True, hang=False)


def j_ladder(rng, style):                     # a bar over two uprights over a bar (ㅍ), or a zig-zag of bars (ㄹ)
    p = Pen(rng, style)
    if rng.random() < .5:
        _seg(p, 0, TOP, 0, 1)
        _seg(p, .25, TOP, -90, TOP)
        _seg(p, .75, TOP, -90, TOP)
        _seg(p, 0, BASE, 0, 1)
    else:
        _seg(p, 0, TOP, 0, 1)
        _seg(p, 1, TOP, -90, .5)
        _seg(p, 1, MID, 180, 1)
        _seg(p, 0, MID, -90, .5)
        _seg(p, 0, BASE, 0, 1)
    return p.done(False, fit=True, hang=False)


def j_diag(rng, style):                       # two slants meeting at the top (ㅅ), with a bar over them (ㅈ) and a tick over the bar (ㅊ)
    p = Pen(rng, style)
    bar = rng.random() < .5
    top = HI if bar else TOP
    a = _c(rng, 55, 65)
    p.begin(.5, top, 180 + a)
    p.line(top / math.sin(math.radians(a)))
    p.begin(.45, top - .35, -a)
    p.line((top - .35) / math.sin(math.radians(a)))
    if bar:
        _seg(p, 0, TOP, 0, 1)
        if rng.random() < .35:
            _seg(p, .5, TOP, 90, .12)
    return p.done(False, fit=True, hang=False)


def j_ring(rng, style):                       # a ring (ㅇ), or a ring under a bar and a tick (ㅎ)
    p = Pen(rng, style)
    r = .3 if rng.random() < .5 else .26
    p.begin(.5 + r, .3, 90)
    p.arc(360, r)
    if rng.random() < .5:
        _seg(p, .1, .78, 0, .8)
        _seg(p, .5, TOP, -90, .22)
    return p.done(False, fit=True, hang=False)


def j_stem_ticks(rng, style):                 # an upright with one or two short ticks to one side (ㅏ ㅑ ㅓ ㅕ), or alone (ㅣ)
    p = Pen(rng, style)
    left = rng.random() < .5
    x = 1 if left else 0
    _seg(p, x, TOP, -90, TOP)
    for y in _c(rng, (MID,), (HI - .05, LO + .05), ()):
        _seg(p, x, y, 180 if left else 0, _c(rng, .5, .6))
    return p.done(False, fit=True, hang=False)


def j_bar_ticks(rng, style):                  # a bar with one or two ticks above (ㅗ ㅛ) or below (ㅜ ㅠ); a bare bar is ㅡ
    p = Pen(rng, style)
    up = rng.random() < .5
    y = BASE if up else TOP
    _seg(p, 0, y, 0, 1)
    for x in _c(rng, (.5,), (.28, .72), ()):
        _seg(p, x, y, 90 if up else -90, _c(rng, .45, .55))
    return p.done(False, fit=True, hang=False)


JAMO = {"j_corner": j_corner, "j_open": j_open, "j_box": j_box, "j_ladder": j_ladder, "j_diag": j_diag, "j_ring": j_ring,
        "j_stem_ticks": j_stem_ticks, "j_bar_ticks": j_bar_ticks}

BENGALI = {"b_tri": h_tri, "b_ring": h_ring, "b_two_hook": h_two_hook, "b_hook_hang": h_hook_hang, "b_s": h_s, "b_bowl": b_bowl, "b_loop_arm": b_loop_arm,
           "b_diag_x": b_diag_x, "b_foot_curl": b_foot_curl, "b_drop_loop": b_drop_loop, "b_s_hook": b_s_hook,
           "b_angle": b_angle, "b_zigzag": b_zigzag, "b_vee": b_vee, "b_flag": b_flag, "b_arrow": b_arrow}
BENGALI = {n: _with_parts(f, first=.4, second=.1, bar=True, wrap=False, loopx=.12, targets=(3, 3, 3, 4), struct=(("arc",),)) for n, f in BENGALI.items()}
FAMILIES = {"headline": {**HEADLINE, **HEADLINE_OLD}, "bengali": BENGALI, "foot": FOOT, "loop_head": LOOP_HEAD, "jamo": JAMO}
NEW = {**HEADLINE, **BENGALI, **FOOT, **LOOP_HEAD, **JAMO}
LIKE = {**{n: 1.6 for n in HEADLINE}, **{n: 1.6 for n in BENGALI}, **{"b_tri": .6, "b_two_hook": .8, "b_diag_x": .6, "b_ring": 1.2, "b_hook_hang": 1.2, "b_s": 1.5, "b_bowl": 3.0, "b_loop_arm": 2.0, "b_foot_curl": 1.5, "b_drop_loop": 1.2, "b_s_hook": 1.2, "b_angle": 2.5, "b_zigzag": 2.0, "b_vee": 3.0, "b_flag": 3.0, "b_arrow": 3.0}, **{n: 1.8 for n in FOOT}, **{"t_cup": .4, "t_shoulder": .4, "t_vertical": 1.0, "t_bowl": 1.2, "t_wave": 1.0, "t_self_cross": 5.5, "t_coil": 5.5, "t_cup_rings": 4.5, "t_cup_tail": 4.5, "t_cup_stem": 3.5, "t_stacked_loops": 5.0, "t_ring_stem": .6, "t_chain": 3.0, "t_ring_swoop": 3.0, "t_s_circle": 3.0, "t_loop_cross": 3.0, "t_oval_swoop": 2.5}, **{"angle": .35, "arc_stem": .4, "cup_tick": .5, "hook_stem": .6, "a": .5}, **{n: 1.0 for n in LOOP_HEAD}, **{n: 1.0 for n in JAMO}}
LOOPY = {"b_ring", "b_bowl", "b_loop_arm", "b_drop_loop", "b_s_hook", "t_coil", "t_cup_rings", "t_cup_tail", "t_cup_stem", "t_self_cross", "t_stacked_loops", "t_bowl", "t_wave", "t_ring_stem", "t_ring_swoop", "t_loop_cross", "t_s_circle", "h_ring", "h_hump2", "t_chain", "t_oval_swoop", "th_ring_stem", "th_ring_cap", "th_s", "th_loop_back", "th_double", "j_ring"}
