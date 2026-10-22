"""The "pen" hand of the stroke family: letters drawn as a pen would draw them, like the Brahmic scripts (Devanagari, Bengali,
Tamil...). Where the kana hands put a few short strokes side by side, a pen letter is a path: every stroke starts from
something already on the page and goes on from there.

A stroke begins
  - at the end of the stroke before it, carrying on in the direction it was going (the pen does not lift), or
  - at the middle of an earlier stroke, leaving it at a right angle (a short connector off a stem), or
  - free, at a point of its own;
and it ends free, or lands on the middle of another stroke (an arm that closes a bowl against the stem).

Two frames (the `pen_frame` dial):
  stem  a long vertical stroke (from the top bar, if the script has one) that the other strokes hang from: arms, bowls,
        hooks and loops attach to its middle and foot (Devanagari, Bengali);
  free  no stem: loops, curls, hooks and S-curves chained end to end, with a short stroke added at a middle (Tamil).

The corner style sets how the parts are drawn: smooth (arcs, round bowls), sharp (straight legs meeting at angles, with
acute turns) or mixed (some strokes of each). Unit box, y up; the stem frame reaches the top of the box.

A letter is built by an archetype (a recipe: "stem with an arm that curls into a bowl", "loop with a tail"), whose
lengths, radii and attachment points are jittered, so one archetype gives many different letters."""
from __future__ import annotations

import math

from .geometry import stroke

FRAMES = ("stem", "free")
LOOP_FILL = 0.9          # chance that a free-frame letter without a loop gets a ring
ADORN_FREE = 0.7       # chance of one more small feature (repeated) on a free-frame letter
DESCEND = 0.45          # share of free-frame letters that hang below the baseline


class Pen:
    """A pen that draws strokes one after another. Angles are degrees, 0 = east, 90 = north; a positive turn is to the left."""

    def __init__(self, rng, style):
        self.rng, self.style = rng, style
        self.strokes: list[dict] = []
        self.x = self.y = self.h = 0.0
        self.loops = 0                                 # complete turns drawn so far (rings and loops)

    def _kind(self):
        return "s" if self.style == "sharp" else "m" if self.style == "smooth" else self.rng.choice("sm")

    @property
    def curvy(self):
        return self.strokes[-1]["k"] == "m"

    def begin(self, x, y, heading):
        self.strokes.append({"p": [(x, y)], "k": self._kind()})
        self.x, self.y, self.h = x, y, heading
        return len(self.strokes) - 1

    def _go(self, x, y):
        self.strokes[-1]["p"].append((x, y))
        self.x, self.y = x, y

    def line(self, length):
        a = math.radians(self.h)
        self._go(self.x + length * math.cos(a), self.y + length * math.sin(a))
        return self

    def turn(self, deg):
        """A corner: the next leg goes off at a new heading."""
        self.h += deg
        return self

    def arc(self, deg, r):
        """A curve of `deg` degrees (left if positive) and radius r, starting along the current heading. Smooth strokes get
        a dense arc; sharp ones a few straight legs along it."""
        sg = 1 if deg > 0 else -1
        if abs(deg) >= 240:                            # a loop or ring is always drawn round, even in a sharp stroke
            self.strokes[-1]["k"] = "m"
            self.loops += abs(deg) >= 300
        a0 = math.radians(self.h)
        cx, cy = self.x + r * math.cos(a0 + sg * math.pi / 2), self.y + r * math.sin(a0 + sg * math.pi / 2)
        start = math.atan2(self.y - cy, self.x - cx)
        if not self.curvy and 100 <= abs(deg) <= 215:           # sharp: a point, not a bowl: two legs meeting at an acute angle
            mid = start + sg * math.radians(abs(deg)) / 2
            self._go(cx + r * 1.38 * math.cos(mid), cy + r * 1.38 * math.sin(mid))
            end = start + sg * math.radians(abs(deg))
            self._go(cx + r * math.cos(end), cy + r * math.sin(end))
            self.h += deg
            return self
        n = max(3, int(abs(deg) / 22)) if self.curvy else max(2, round(abs(deg) / 62))
        for i in range(1, n + 1):
            a = start + sg * math.radians(abs(deg)) * i / n
            self._go(cx + r * math.cos(a), cy + r * math.sin(a))
        self.h += deg
        return self

    def to(self, x, y):
        """End the stroke exactly at (x, y): on another stroke, to join it."""
        self._go(x, y)
        return self

    def at(self, si, t):
        """The point a fraction t of the way along stroke si, and the direction the stroke is heading there."""
        pts = self.strokes[si]["p"]
        segs = [(math.dist(a, b), a, b) for a, b in zip(pts, pts[1:])]
        want = t * sum(s[0] for s in segs)
        for ln, a, b in segs:
            if want <= ln or (a, b) == (segs[-1][1], segs[-1][2]):
                f = 0 if ln == 0 else min(1.0, want / ln)
                return a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]), math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            want -= ln
        return pts[-1][0], pts[-1][1], 0.0

    def done(self, mirror=False, fit=False):
        """The strokes, clamped to the box. fit: first stretch the letter to fill the box (free-frame letters have no stem to
        set their height, so they are drawn at any size and scaled up to the line)."""
        strokes = [{"p": list(s["p"]), "k": s["k"]} for s in self.strokes]
        if fit:
            xs = [x for s in strokes for x, _ in s["p"]]
            ys = [y for s in strokes for _, y in s["p"]]
            bw, bh = max(max(xs) - min(xs), .05), max(max(ys) - min(ys), .05)
            th, tw = self.rng.uniform(.86, 1.0), self.rng.uniform(.8, 1.0)
            sy, sx = th / bh, tw / bw
            sx = min(max(sx, sy * .7), sy * 1.45)                       # at most a modest stretch: rings stay roundish
            x0, y0 = min(xs), min(ys)
            dip = self.rng.uniform(.18, .4) if self.rng.random() < DESCEND else 0.0       # some letters hang below the line
            strokes = [{"p": [((x - x0) * sx, (y - y0) * sy - dip) for x, y in s["p"]], "k": s["k"]} for s in strokes]
        out = []
        for s in strokes:
            pts = [(1 - x if mirror else x, y) for x, y in s["p"]]
            pts = [(round(min(max(x, 0.0), 1.0), 3), round(min(max(y, -0.6), 1.6), 3)) for x, y in pts]
            out.append(dict(stroke(pts), k=s["k"]))
        return out


def _u(rng, a, b):
    return rng.uniform(a, b)


def _adorn(p, rng, how=None):
    """A small extra feature on a stroke already drawn: a ring beside it, a short tick or a hook leaving it at a right angle."""
    si = rng.randrange(len(p.strokes))
    x, y, h = p.at(si, _u(rng, .12, .88))
    side = rng.choice([-1, 1])
    how = how or rng.choice(["ring", "tick", "hook", "ring"])
    if how == "ring":
        p.begin(x, y, h)
        p.arc(side * 360, _u(rng, .07, .12))
    else:
        p.begin(x, y, h + side * 90)
        p.line(_u(rng, .09, .17))
        if how == "hook":
            p.arc(-side * _u(rng, 60, 100), _u(rng, .05, .09))


# ---- stem frame ---------------------------------------------------------------------------------------------------------
def _stem(p, rng, sx, foot=0.0):
    """The stem: from the top of the box down (to its foot), at x = sx. Returns its index."""
    s = p.begin(sx, 1.0, -90)
    p.line(1.0 - foot)
    return s


def _extra(p, rng, s, sx):
    """A second feature on the stem: a flick at its head, a little arm to its right, or a tick at its foot."""
    kind = rng.choice(["head", "right", "foot"])
    if kind == "head":
        x, y, _ = p.at(s, _u(rng, .08, .2))
        p.begin(x, y, 180 + _u(rng, -15, 15))
        p.line(_u(rng, .12, .26))
        p.arc(_u(rng, 60, 110) * rng.choice([1, -1]), _u(rng, .06, .1))
    elif kind == "right" and sx < .8:
        x, y, _ = p.at(s, _u(rng, .3, .7))
        p.begin(x, y, _u(rng, -25, 25))
        p.line(min(_u(rng, .12, .2), .98 - sx))
    else:
        x, y, _ = p.at(s, _u(rng, .9, 1.0))
        p.begin(x, y, 180 + _u(rng, -20, 20))
        p.line(_u(rng, .1, .24))


def s_fork(rng, style):                       # a stem that forks into two slanting arms (ऋ হ ह)
    p = Pen(rng, style)
    sx = _u(rng, .4, .6)
    s = p.begin(sx, 1.0, -90)
    p.line(_u(rng, .42, .62))
    x, y = p.x, p.y
    for sign in (1, -1):
        p.begin(x, y, -90 + sign * _u(rng, 28, 55))
        p.line(_u(rng, .4, .56))
        if rng.random() < .5:
            p.arc(-sign * _u(rng, 40, 90), _u(rng, .08, .14))
    if rng.random() < .35:
        _adorn(p, rng, rng.choice(["tick", "hook"]))
    return p.done(False)


def s_slant_stem(rng, style):                 # a stem crossed low by a slanting stroke from the head (ঝ ऋ)
    p = Pen(rng, style)
    sx = _u(rng, .5, .72)
    s = _stem(p, rng, sx)
    p.begin(_u(rng, .08, .22), _u(rng, .72, .86), -_u(rng, 24, 42))
    p.line(_u(rng, .7, .95))
    if rng.random() < .5:
        p.arc(_u(rng, 40, 90), _u(rng, .1, .18))
    if rng.random() < .4:
        _adorn(p, rng, rng.choice(["tick", "hook"]))
    return p.done(rng.random() < .3)


def s_arm_bowl(rng, style):                   # a stem with an arm leaving its middle to the left that curls round into a bowl (ख ग ক)
    p = Pen(rng, style)
    sx = _u(rng, .62, .8)
    s = _stem(p, rng, sx, _u(rng, -.02, .08))
    x, y, _ = p.at(s, _u(rng, .42, .6))
    p.begin(x, y, 180 + _u(rng, 0, 26))
    p.line(_u(rng, .1, .24))
    if rng.random() < .15:
        p.arc(_u(rng, 170, 235), _u(rng, .22, .32))
        p.to(sx, max(.04, p.y))                    # the arm comes back and lands on the stem: a closed bowl
    else:                                          # the bowl stays open: it swings round but does not return to the stem
        p.arc(_u(rng, 95, 150), _u(rng, .22, .32))
        p.line(_u(rng, .04, .14)).arc(-_u(rng, 50, 90), _u(rng, .1, .16))
    if rng.random() < .45:
        _extra(p, rng, s, sx)
    if rng.random() < .4:
        _adorn(p, rng, rng.choice(["tick", "hook"]))
    return p.done(rng.random() < .3)


def s_two_arms(rng, style):                   # two short arms off the stem, the upper one curling up, the lower one down (घ ঘ)
    p = Pen(rng, style)
    sx = _u(rng, .66, .82)
    s = _stem(p, rng, sx)
    t1, t2 = _u(rng, .22, .36), _u(rng, .6, .78)
    for t, sign in ((t1, 1), (t2, -1)):
        x, y, _ = p.at(s, t)
        p.begin(x, y, 180)
        p.line(_u(rng, .3, .52))
        p.arc(-_u(rng, 70, 110) if sign > 0 else _u(rng, 70, 110), _u(rng, .1, .17))
    return p.done(rng.random() < .3)


def s_foot_hook(rng, style):                  # a stem whose foot turns into a hook, with a bar across its middle (त ত)
    p = Pen(rng, style)
    sx = _u(rng, .58, .74)
    s = _stem(p, rng, sx, _u(rng, .24, .38))
    p.arc(-_u(rng, 100, 160), _u(rng, .2, .3))
    if rng.random() < .7:
        x, y, _ = p.at(s, _u(rng, .35, .55))
        p.begin(x - _u(rng, .36, .54), y + _u(rng, -.04, .04), _u(rng, -8, 8))
        p.to(x, y)
    if rng.random() < .45:
        _extra(p, rng, s, sx)
    if rng.random() < .4:
        _adorn(p, rng, rng.choice(["tick", "hook"]))
    return p.done(rng.random() < .3)


def s_two_stems(rng, style):                  # two stems joined by a bar that leaves the first and lands on the middle of the second (म ধ)
    p = Pen(rng, style)
    xl, xr = _u(rng, .16, .3), _u(rng, .7, .84)
    a = p.begin(xl, 1.0, -90)
    p.line(_u(rng, .85, 1.0))
    b = p.begin(xr, 1.0, -90)
    p.line(_u(rng, .85, 1.0))
    x, y, _ = p.at(a, _u(rng, .42, .6))
    p.begin(x, y, _u(rng, -20, 20))
    if rng.random() < .5:
        p.line(_u(rng, .12, .22)).arc(-_u(rng, 20, 50), _u(rng, .2, .3))
    xe, ye, _ = p.at(b, _u(rng, .38, .62))
    p.to(xe, ye)
    return p.done(rng.random() < .3)


def s_arm_loop(rng, style):                   # an arm off the stem that goes round in a loop and carries on as a tail (क ক)
    p = Pen(rng, style)
    sx = _u(rng, .66, .82)
    s = _stem(p, rng, sx, _u(rng, 0, .1))
    x, y, _ = p.at(s, _u(rng, .45, .65))
    p.begin(x, y, 180)
    p.line(_u(rng, .16, .3))
    p.arc(_u(rng, 280, 330), _u(rng, .18, .26))
    p.line(_u(rng, .14, .32))
    return p.done(rng.random() < .3)


def s_slash_arm(rng, style):                  # an arm that slants away down-left and turns sharply back to the stem's foot (acute triangle) (ষ হ)
    p = Pen(rng, style)
    sx = _u(rng, .64, .8)
    s = _stem(p, rng, sx)
    x, y, _ = p.at(s, _u(rng, .4, .6))
    p.begin(x, y, 180 + _u(rng, 28, 55))
    p.line(_u(rng, .46, .66))
    p.turn(_u(rng, 95, 135))
    p.line(_u(rng, .2, .34))
    if rng.random() < .25:
        p.to(sx, max(.02, p.y))
    if rng.random() < .45:
        _extra(p, rng, s, sx)
    if rng.random() < .4:
        _adorn(p, rng, rng.choice(["tick", "hook"]))
    return p.done(rng.random() < .3)


def s_bowl_stem(rng, style):                  # a C-shaped bowl hung on a stem that runs past it (ब ব ठ)
    p = Pen(rng, style)
    sx = _u(rng, .66, .82)
    r = _u(rng, .26, .36)
    top = _u(rng, .66, .92)
    p.begin(sx, top, 180)
    p.arc(_u(rng, 180, 250), r)
    if rng.random() < .25:
        p.to(sx, max(.02, p.y))
    p.begin(sx, 1.0, -90)
    p.line(_u(rng, .92, 1.0))
    return p.done(rng.random() < .3)


def s_arm_tick(rng, style):                   # an arm off the stem with a short stroke turned off its end (ि ধ)
    p = Pen(rng, style)
    sx = _u(rng, .62, .8)
    s = _stem(p, rng, sx, _u(rng, 0, .1))
    x, y, _ = p.at(s, _u(rng, .3, .62))
    p.begin(x, y, 180 + _u(rng, -30, 30))
    p.line(_u(rng, .36, .56))
    p.turn(_u(rng, -100, -60) if rng.random() < .6 else _u(rng, 60, 100))
    p.line(_u(rng, .12, .24))
    if rng.random() < .45:
        _extra(p, rng, s, sx)
    if rng.random() < .4:
        _adorn(p, rng, rng.choice(["tick", "hook"]))
    return p.done(rng.random() < .3)


def s_stem_ring(rng, style):                  # a ring on a short arm from the stem (ग ঞ)
    p = Pen(rng, style)
    sx = _u(rng, .66, .82)
    s = _stem(p, rng, sx, _u(rng, 0, .1))
    x, y, _ = p.at(s, _u(rng, .38, .62))
    p.begin(x, y, 180)
    p.line(_u(rng, .16, .3))
    p.arc(_u(rng, 330, 360), _u(rng, .18, .26))
    if rng.random() < .45:
        _extra(p, rng, s, sx)
    if rng.random() < .4:
        _adorn(p, rng, rng.choice(["tick", "hook"]))
    return p.done(rng.random() < .3)


def _finish_free(p, rng):
    """Free-frame letters are mostly rings and loops: one with no loop of its own gets a ring beside it, and some get a tick or
    hook as well. Then the letter is stretched to fill the box."""
    if not p.loops and rng.random() < LOOP_FILL:
        _adorn(p, rng, "ring")
    if rng.random() < ADORN_FREE and len(p.strokes) < 4:
        _adorn(p, rng, rng.choice(["tick", "hook", "ring"]))
    return p.done(rng.random() < .4, fit=True)


# ---- free frame ---------------------------------------------------------------------------------------------------------
def f_loop_tail(rng, style):                  # a loop that carries on into a tail (ல ல்)
    p = Pen(rng, style)
    p.begin(_u(rng, .62, .78), _u(rng, .7, .9), _u(rng, 170, 215))
    p.arc(_u(rng, 280, 330), _u(rng, .2, .28))
    p.line(_u(rng, .18, .4))
    if rng.random() < .4:
        p.arc(-_u(rng, 50, 90), _u(rng, .1, .16))
    return _finish_free(p, rng)


def f_s_curve(rng, style):                    # two curves back to back, an S (ஸ ஞ)
    p = Pen(rng, style)
    p.begin(_u(rng, .66, .8), _u(rng, .86, .98), _u(rng, 175, 200))
    r = _u(rng, .16, .24)
    p.arc(_u(rng, 150, 200), r)
    p.arc(-_u(rng, 150, 200), r * _u(rng, .9, 1.2))
    return _finish_free(p, rng)


def f_ring_tick(rng, style):                  # a ring with a short stroke leaving it at a right angle (ம ள ள)
    p = Pen(rng, style)
    r = _u(rng, .2, .3)
    cx, cy = _u(rng, .4, .55), _u(rng, .45, .6)
    ring = p.begin(cx + r, cy, 90)
    p.arc(360, r)
    x, y, h = p.at(ring, _u(rng, .0, .45))
    p.begin(x, y, h - 90)                         # leaves the ring outwards (the ring runs counter-clockwise)
    p.line(_u(rng, .14, .26))
    if rng.random() < .55:
        p.arc(-_u(rng, 60, 110), _u(rng, .07, .12))
    return _finish_free(p, rng)


def f_hook_stem(rng, style):                  # a stroke down that hooks at the foot, with a bar off its middle (த ந)
    p = Pen(rng, style)
    sx = _u(rng, .3, .55)
    s = p.begin(sx, _u(rng, .86, 1.0), -90)
    p.line(_u(rng, .5, .66))
    p.arc(_u(rng, 110, 170), _u(rng, .14, .24))
    if rng.random() < .65:
        x, y, _ = p.at(s, _u(rng, .2, .6))
        p.begin(x, y, 0)
        p.line(_u(rng, .24, .4))
        if rng.random() < .5:
            p.arc(-_u(rng, 40, 80), _u(rng, .08, .14))
    return _finish_free(p, rng)


def f_double_loop(rng, style):                # two loops, one after the other (அ ஐ)
    p = Pen(rng, style)
    p.begin(_u(rng, .14, .3), _u(rng, .5, .7), _u(rng, 60, 110))
    r = _u(rng, .14, .2)
    p.arc(-_u(rng, 270, 330), r)
    p.arc(_u(rng, 270, 330), r * _u(rng, .9, 1.2))
    p.line(_u(rng, .08, .2))
    return _finish_free(p, rng)


def f_angle(rng, style):                      # a stroke down that turns along the foot, with a short stroke added at its middle (ட ட்)
    p = Pen(rng, style)
    s = p.begin(_u(rng, .14, .3), _u(rng, .8, .98), -90)
    p.line(_u(rng, .5, .74))
    if rng.random() < .5:
        p.arc(_u(rng, 80, 100), _u(rng, .06, .14))
    else:
        p.turn(_u(rng, 80, 100))
    p.line(_u(rng, .4, .66))
    if rng.random() < .55:
        x, y, _ = p.at(s, _u(rng, .2, .5))
        p.begin(x, y, 0)
        p.line(_u(rng, .14, .28))
    return _finish_free(p, rng)


def f_cup_tick(rng, style):                   # a cup opening upward, with a stroke dropping from the middle of its foot (ம ய)
    p = Pen(rng, style)
    r = _u(rng, .26, .34)
    cup = p.begin(_u(rng, .1, .2), _u(rng, .6, .8), -90)
    p.arc(_u(rng, 170, 200), r)
    if rng.random() < .75:
        x, y, h = p.at(cup, _u(rng, .4, .6))
        p.begin(x, y, h - 90 if h > 0 else h + 90)
        p.line(_u(rng, .14, .3))
    return _finish_free(p, rng)


def f_wave(rng, style):                       # a wave of two or three humps (ஊ ய)
    p = Pen(rng, style)
    p.begin(_u(rng, .06, .16), _u(rng, .4, .6), _u(rng, 50, 80))
    r = _u(rng, .13, .18)
    for i in range(rng.choice([2, 3])):
        p.arc((-1) ** (i + 1) * _u(rng, 120, 170), r)
    return _finish_free(p, rng)


def f_arc_stem(rng, style):                   # an arch whose end drops into a stem (ந ற)
    p = Pen(rng, style)
    p.begin(_u(rng, .14, .3), _u(rng, .55, .75), 90)
    p.arc(-_u(rng, 150, 190), _u(rng, .2, .3))
    p.line(_u(rng, .3, .55))
    return _finish_free(p, rng)


def f_spiral(rng, style):                     # an arm that winds inward (ஞ ழ)
    p = Pen(rng, style)
    p.begin(_u(rng, .7, .85), _u(rng, .85, .98), 180)
    p.line(_u(rng, .1, .2))
    r = _u(rng, .3, .36)
    p.arc(_u(rng, 200, 250), r)
    p.arc(_u(rng, 150, 220), r * _u(rng, .5, .65))
    return _finish_free(p, rng)


STEM = {"fork": s_fork, "slant_stem": s_slant_stem, "arm_bowl": s_arm_bowl, "two_arms": s_two_arms, "foot_hook": s_foot_hook, "two_stems": s_two_stems,
        "arm_loop": s_arm_loop, "slash_arm": s_slash_arm, "bowl_stem": s_bowl_stem, "arm_tick": s_arm_tick, "stem_ring": s_stem_ring}
FREE = {"loop_tail": f_loop_tail, "s_curve": f_s_curve, "ring_tick": f_ring_tick, "hook_stem": f_hook_stem,
        "double_loop": f_double_loop, "angle": f_angle, "cup_tick": f_cup_tick, "arc_stem": f_arc_stem,
        "spiral": f_spiral}
ARCHETYPES = {**STEM, **FREE}
LOOPY = {"arm_loop", "stem_ring", "loop_tail", "ring_tick", "double_loop", "spiral"}       # archetypes that hold a loop or ring
FILL = (0.6, 0.4)                                # the least height and width of a letter


def archetypes(frame: str) -> list:
    """The archetypes a frame draws from: stem, free, or both."""
    return (list(STEM) if frame == "stem" else list(FREE) if frame == "free" else list(ARCHETYPES))


# how much each archetype is liked: the recipes that close a hole (two stems with a bar, a bowl hung on the stem) are rarer than the
# open ones, as in the real scripts, where about a third of the letters hold a hole
LIKE = {"two_stems": 0.35, "bowl_stem": 0.4, "slash_arm": 0.7, "stem_ring": 0.7, "arm_loop": 0.7, "fork": 1.4, "slant_stem": 1.4, "two_arms": 1.3, "foot_hook": 1.2}


def weights(loops: float) -> dict:
    return {n: ((0.3 + 2.2 * loops) if n in LOOPY else 1.0) * LIKE.get(n, 1.0) for n in ARCHETYPES}
