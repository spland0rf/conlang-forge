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
    kind = _c(rng, "post", "post", "arch", "tick", "loop")
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


def t_chain(rng, style):                      # one to three small rings in a row, each with an arm to the right, and a vertical from the last (ண ள ன)
    p = Pen(rng, style)
    x = 0.12
    r = _c(rng, .12, .14)
    for _ in range(_c(rng, 1, 2, 3)):
        p.begin(x + r, MID, 90)
        p.arc(360, r)
        p.turn(-90)
        p.line(_c(rng, .12, .18))
        x = p.x
    if rng.random() < .7:
        p.begin(p.x, p.y, -90)
        p.line(MID)
    return p.done(False, fit=True, hang=False)


def t_oval_swoop(rng, style):                 # a base swoop that starts in a closed oval and rises at its far end (the foot of ஶ்ரீ)
    p = Pen(rng, style)
    r = _c(rng, .1, .12)
    p.begin(.3, MID - .3, 90)
    p.arc(360, r)
    p.turn(-90)
    p.line(_c(rng, .5, .7))
    p.arc(90, _c(rng, .2, .28))
    if rng.random() < .5:
        p.begin(.15, TOP, -90)
        p.line(.55)
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


def t_loop_cross(rng, style):                 # a vertical with a loop at its foot, a short bar across, and sometimes a small square corner hook (க ச)
    p = Pen(rng, style)
    p.begin(.2, TOP, -90)
    p.line(_c(rng, .6, .7))
    r = _c(rng, .1, .13)
    p.arc(-_c(rng, 270, 330), r)
    p.begin(.05, _c(rng, MID, .6), 0)
    p.line(_c(rng, .3, .45))
    if rng.random() < .5:
        p.begin(.6, MID, 90)
        p.line(.12)
        p.turn(-90)
        p.line(.12)
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
    p.arc(_c(rng, 90, 150), _c(rng, .1, .14))
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
    r = _c(rng, .12, .16)
    p.begin(0, MID, 90)
    for i in range(_c(rng, 2, 3)):
        p.arc((-1) ** i * 180, r)
    kind = _c(rng, "ring", "hook", "none")
    if kind == "ring":
        p.arc(360, _c(rng, .08, .1))
    elif kind == "hook":
        p.arc(-_c(rng, 120, 180), _c(rng, .08, .12))
    if rng.random() < .5:
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


def _part(rng, strokes):
    """One more stroke attached to the letter, at a fixed kind of place: a short bar leaving a stroke at a right angle (a T-join), a small
    tangent ring, or a short hooked curl carrying on from a stroke's end (a corner). Returns None if there is no stroke to attach to."""
    hosts = [st for st in strokes if len(st["p"]) > 2]
    if not hosts:
        return None
    host = rng.choice(hosts)
    pts = [tuple(q) for q in host["p"]]
    kind = _c(rng, "bar", "bar", "ring", "curl", "leg")
    end = rng.random() < .5
    f = _c(rng, 0.0, 1.0) if (end or kind in ("curl", "leg")) else _c(rng, .25, .5, .75)
    (x, y), (ux, uy) = _along(pts, f)
    sgn = _c(rng, 1, -1)
    nx, ny = -uy * sgn, ux * sgn                                  # a side normal
    if kind == "bar":
        l = _c(rng, .16, .22, .3)
        out = [(x, y), (x + nx * l, y + ny * l)]
    elif kind == "leg":
        l = _c(rng, .15, .22)
        dx, dy = (ux, uy) if f >= 1 else (-ux, -uy)
        out = [(x, y), (x + dx * l, y + dy * l), (x + dx * l + nx * l, y + dy * l + ny * l)]
    elif kind == "ring":
        r = _c(rng, .08, .1, .12)
        cx, cy = x + nx * r, y + ny * r
        a0 = math.atan2(y - cy, x - cx)
        out = [(cx + r * math.cos(a0 + sgn * 2 * math.pi * i / 20), cy + r * math.sin(a0 + sgn * 2 * math.pi * i / 20)) for i in range(21)]
    else:
        r = _c(rng, .08, .11)
        dx, dy = (ux, uy) if f >= 1 else (-ux, -uy)
        ang = math.atan2(dy, dx)
        out = [(x, y)]
        for i in range(1, 9):
            a = i * math.radians(150) / 8
            out.append((x + r * (math.cos(ang) * math.sin(a) - sgn * math.sin(ang) * (1 - math.cos(a))),
                        y + r * (math.sin(ang) * math.sin(a) + sgn * math.cos(ang) * (1 - math.cos(a)))))
    out = [(round(min(max(a, 0.0), 1.0), 3), round(min(max(b, -0.6), 1.6), 3)) for a, b in out]
    return dict(_stroke(out), k=host["k"])


def _with_parts(fn, first=.9, second=.45):
    def make(rng, style):
        strokes = fn(rng, style)
        for chance in (first, second):
            if rng.random() < chance:
                extra = _part(rng, strokes)
                if extra:
                    strokes = strokes + [extra]
        return strokes
    make.__name__ = fn.__name__
    return make


FOOT = {"t_cup": t_cup, "t_shoulder": t_shoulder, "t_chain": t_chain, "t_oval_swoop": t_oval_swoop, "t_vertical": t_vertical,
        "t_ring_swoop": t_ring_swoop, "t_loop_cross": t_loop_cross, "t_s_circle": t_s_circle,
        "t_self_cross": t_self_cross, "t_stacked_loops": t_stacked_loops, "t_bowl": t_bowl, "t_wave": t_wave, "t_ring_stem": t_ring_stem}
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

FAMILIES = {"headline": {**HEADLINE, **HEADLINE_OLD}, "foot": {**FOOT, **FOOT_OLD}, "loop_head": LOOP_HEAD, "jamo": JAMO}
NEW = {**HEADLINE, **FOOT, **LOOP_HEAD, **JAMO}
LIKE = {**{n: 1.6 for n in HEADLINE}, **{n: 1.8 for n in FOOT}, **{"t_cup": .8, "t_shoulder": .8, "t_self_cross": 3.0, "t_stacked_loops": 2.2, "t_ring_stem": 2.2, "t_bowl": 2.0, "t_wave": 1.8}, **{"angle": .35, "arc_stem": .4, "cup_tick": .5, "hook_stem": .6, "a": .5}, **{n: 1.0 for n in LOOP_HEAD}, **{n: 1.0 for n in JAMO}}
LOOPY = {"t_self_cross", "t_stacked_loops", "t_bowl", "t_wave", "t_ring_stem", "t_ring_swoop", "t_loop_cross", "t_s_circle", "h_ring", "h_hump2", "t_chain", "t_oval_swoop", "th_ring_stem", "th_ring_cap", "th_s", "th_loop_back", "th_double", "j_ring"}
