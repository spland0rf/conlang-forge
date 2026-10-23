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

A letter is built by an archetype (a recipe: "stem with an arm that curls into a bowl", "loop with a tail") from a small
fixed vocabulary, not from free random numbers (pen v2):
  guide lines   every top, foot, attachment and bowl bottom sits on one of TOP, HI, MID, LO, BASE (and DESC for a letter that
                hangs below the line); stems stand in one of three columns (LEFT, CENTER, RIGHT);
  sizes         arms have one of three lengths (ARM), rings and bowls one of three radii (RAD), turns are quarter, half,
                three-quarter or full (90, 180, 270, 360 degrees), slanted strokes use one of two angles (DIAG);
  one axis      every near-vertical stroke is exactly upright in the design; a script's lean is a drawing style (the `slant` dial,
                applied when the letters are drawn), so all stems of a script lean the same way.
Letters differ by which recipe and which of these few values they pick, so they line up the way the letters of a real script do."""
from __future__ import annotations

import math

from .geometry import stroke

FRAMES = ("stem", "free", "headline", "foot", "loop_head", "jamo")
LOOP_FILL = 0.85         # chance that a free-frame letter without a loop gets a ring
ADORN_FREE = 0.3       # chance of one more small feature on a free-frame letter
DESCEND = 0.15          # share of free-frame letters that hang below the baseline

TOP, HI, MID, LO, BASE, DESC = 1.0, 0.75, 0.5, 0.25, 0.0, -0.3        # the guide lines (y); DESC is how far a hanging letter reaches below the line
LEFT, CENTER, RIGHT = 0.2, 0.5, 0.8                                    # the stem columns (x)
ARM = (0.2, 0.32, 0.46)                                                # arm lengths
RAD = (0.14, 0.2, 0.25)                                                # ring and bowl radii (0.25 is the bowl that hangs from MID to BASE)
DIAG = (35, 55)                                                        # slanted strokes: degrees from the horizontal
TICK = 0.14                                                            # the length of a tick
HEADLESS = 0.8                                                         # the top of a letter drawn without the bar


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
        if not self.curvy:                                      # sharp: the bowl is a polygon with sides at multiples of 45 degrees (a circumscribed octagon)
            n = max(1, round(abs(deg) / 45))
            side = 2 * r * math.tan(math.radians(22.5))
            for i in range(n + 1):
                self.line(side / 2 if i in (0, n) else side)
                if i < n:
                    self.turn(sg * 45)
            self.h += sg * (abs(deg) - 45 * n)                  # (the heading is already right when deg is a multiple of 45)
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

    def done(self, mirror=False, fit=False, hang=None):
        """The strokes, clamped to the box. fit: first stretch the letter to fill the box (free-frame letters have no stem to
        set their height, so they are drawn at any size and scaled up to the line)."""
        strokes = [{"p": list(s["p"]), "k": s["k"]} for s in self.strokes]
        if fit:
            xs = [x for s in strokes for x, _ in s["p"]]
            ys = [y for s in strokes for _, y in s["p"]]
            bw, bh = max(max(xs) - min(xs), .05), max(max(ys) - min(ys), .05)
            if hang is None:
                hang = self.rng.random() < DESCEND                       # a hanging letter reaches DESC; its top stays on the line
            sy = (TOP - (DESC if hang else BASE)) / bh                   # every letter is stretched to the same top and the same foot
            sx = min(max(1.0 / bw, sy * .75), sy * 1.3)                  # at most a modest sideways stretch: rings stay roundish
            x0, y0 = min(xs), min(ys)
            strokes = [{"p": [((x - x0) * sx, (y - y0) * sy + (DESC if hang else BASE)) for x, y in s["p"]], "k": s["k"]} for s in strokes]
        out = []
        for s in strokes:
            pts = [(1 - x if mirror else x, y) for x, y in s["p"]]
            pts = [(round(min(max(x, 0.0), 1.0), 3), round(min(max(y, -0.6), 1.6), 3)) for x, y in pts]
            out.append(dict(stroke(pts), k=s["k"]))
        return out


def _c(rng, *vals):
    """One of a few fixed values (the vocabulary of the hand)."""
    return rng.choice(vals)


def _arm_end(p, rng, how=None):
    """How an arm ends: nothing, a tick, or a quarter-turn flick up or down."""
    how = how or _c(rng, "none", "none", "up", "down")
    if how == "up":
        p.arc(-90, RAD[0])
    elif how == "down":
        p.arc(90, RAD[0])


def _foot_tick(p, rng, s, sx):
    """A short tick leaving the foot of the stem to the left (or a short arm to the right of a stem that stands left)."""
    x, y, _ = p.at(s, 1.0)
    p.begin(x, y, 180)
    p.line(TICK)


# ---- stem frame ---------------------------------------------------------------------------------------------------------
def _stem(p, sx, bottom=BASE):
    """The stem: from the top of the box down to `bottom`, upright, at x = sx. Returns its index."""
    s = p.begin(sx, TOP, -90)
    p.line(TOP - bottom)
    return s


GARNISH = 0.4          # chance that a stem letter gets one more small stroke at a fixed place on its stem


def _garnish(p, rng, s, sx):
    """One more small stroke on the stem, at a fixed place: a tick at its foot, a tick at HI, or (when the stem stands left of
    the middle) a short arm to the right at MID. The vocabulary of the stem hand, so letters stay alike where they should."""
    if rng.random() >= GARNISH:
        return
    how = _c(rng, "foot", "hi", "arm" if sx < .6 else "foot")
    y = {"foot": BASE, "hi": HI, "arm": MID}[how]
    d = 0 if how == "arm" else 180
    p.begin(sx, y if how != "foot" else BASE, d)
    p.line(ARM[0] if how == "arm" else TICK)


def s_fork(rng, style):                       # a stem that forks at MID into two slanting arms that reach the foot line (ऋ হ ह)
    p = Pen(rng, style)
    sx = CENTER
    _stem(p, sx, MID)
    a = _c(rng, 30, 45)
    reach = (MID - BASE) / math.cos(math.radians(a))
    curl = rng.random() < .4
    for sign in (1, -1):
        p.begin(sx, MID, -90 + sign * a)
        p.line(reach)
        if curl:
            p.arc(sign * 90, RAD[0])
    return p.done(False)


def s_slant_stem(rng, style):                 # a stem crossed by a slanting stroke from the head side (ঝ ऋ)
    p = Pen(rng, style)
    sx = _c(rng, RIGHT, RIGHT, CENTER + .15)
    s = _stem(p, sx)
    a = _c(rng, *DIAG)
    y0 = _c(rng, HI, MID + .1)
    p.begin(LEFT - .05, y0, -a)
    p.line(min((sx - LEFT + .05) / math.cos(math.radians(a)) * _c(rng, 1.0, 1.0, 1.15), y0 / math.sin(math.radians(a))))       # it stops at the foot line
    _garnish(p, rng, s, sx)
    return p.done(False)


def s_arm_bowl(rng, style):                   # a stem with an arm leaving MID to the left that curls round into a bowl down to the foot line (ख ग ক)
    p = Pen(rng, style)
    sx = RIGHT
    s = _stem(p, sx)
    p.begin(sx, MID, 180)
    p.line(_c(rng, *ARM[:2]))
    p.arc(180, RAD[2])                            # the bowl hangs from MID to BASE
    if rng.random() < .3:
        p.to(sx, BASE)                            # closed: the bowl lands on the stem's foot
    else:
        if rng.random() < .5:
            p.arc(90, RAD[0])                         # the end of the bowl turns up
        elif rng.random() < .5:
            p.line(TICK)
    _garnish(p, rng, s, sx)
    return p.done(False)


def s_two_arms(rng, style):                   # two arms off the stem at HI and LO, the upper one curling up, the lower one down (घ ঘ)
    p = Pen(rng, style)
    sx = RIGHT
    s = _stem(p, sx)
    n = _c(rng, ARM[1], ARM[2])
    for y, how in ((HI, "up"), (LO, "down")):
        p.begin(sx, y, 180)
        p.line(n)
        _arm_end(p, rng, how)
    _garnish(p, rng, s, sx)
    return p.done(False)


def s_foot_hook(rng, style):                  # a stem whose foot turns into a hook that ends on the foot line, with a bar across MID (त ত)
    p = Pen(rng, style)
    sx = _c(rng, RIGHT, CENTER + .15)
    s = _stem(p, sx, LO + .05)
    if rng.random() < .5:
        p.arc(-90, LO + .05)                      # a quarter turn of radius .3 lands the end on BASE, heading left
        p.line(_c(rng, 0, TICK))
    else:
        p.arc(-180, (LO + .05) / 2)               # a half turn: up and back
    if rng.random() < .75:
        p.begin(LEFT, MID, 0)
        p.to(sx, MID)
    return p.done(False)


def s_two_stems(rng, style):                  # two stems joined by a bar from the first that lands on the middle of the second (म ধ)
    p = Pen(rng, style)
    a = _stem(p, LEFT)
    b = _stem(p, RIGHT)
    y = _c(rng, MID, MID, LO)
    p.begin(LEFT, y, 0)
    p.to(RIGHT, y)
    if rng.random() < .3:
        p.begin(LEFT, HI, 0)
        p.to(RIGHT, HI)
    return p.done(False)


def s_arm_loop(rng, style):                   # an arm off the stem that goes round in a loop and carries on as a tail (क ক)
    p = Pen(rng, style)
    sx = RIGHT
    s = _stem(p, sx)
    p.begin(sx, MID, 180)
    p.line(_c(rng, *ARM[:2]))
    p.arc(_c(rng, 270, 360), RAD[2])
    p.line(_c(rng, *ARM[:2]))
    _garnish(p, rng, s, sx)
    return p.done(False)


def s_slash_arm(rng, style):                  # an arm that slants away down-left to the foot line and runs back along it to the stem's foot (ষ হ)
    p = Pen(rng, style)
    sx = RIGHT
    s = _stem(p, sx)
    a = 45
    p.begin(sx, MID, 180 + a)
    p.line(MID / math.sin(math.radians(a)))
    p.turn(180 - a)                              # now heading east along the foot line
    if rng.random() < .6:
        p.to(sx, BASE)
    else:
        p.line(ARM[0])
    _garnish(p, rng, s, sx)
    return p.done(False)


def s_bowl_stem(rng, style):                  # a C-shaped bowl hung on a stem that runs past it (ब ব ठ)
    p = Pen(rng, style)
    sx = RIGHT
    top, r = _c(rng, (MID, RAD[2]), (HI, RAD[2]), (MID, RAD[1]))
    p.begin(sx, top, 180)
    p.line(ARM[0])
    p.arc(180, r)
    p.line(ARM[0] if rng.random() < .6 else TICK)       # the bowl lands on the stem, or stops just short of it
    _stem(p, sx)
    return p.done(False)


def s_arm_tick(rng, style):                   # an arm off the stem with a short stroke turned off its end (ि ধ)
    p = Pen(rng, style)
    sx = RIGHT
    s = _stem(p, sx)
    p.begin(sx, _c(rng, MID, LO), 180)
    p.line(ARM[2])
    p.turn(_c(rng, -90, 90))
    p.line(_c(rng, TICK, ARM[0]))
    if rng.random() < .25:
        _foot_tick(p, rng, s, sx)
    _garnish(p, rng, s, sx)
    return p.done(False)


def s_stem_ring(rng, style):                  # a ring hung on a short arm from the stem, down to the foot line (ग ঞ)
    p = Pen(rng, style)
    sx = RIGHT
    s = _stem(p, sx)
    p.begin(sx, MID, 180)
    p.line(_c(rng, *ARM[:2]))
    p.arc(360, RAD[2])
    _garnish(p, rng, s, sx)
    return p.done(False)


def _adorn(p, rng, how="ring"):
    """One more small feature on a stroke already drawn, at its middle: a ring beside it or a short tick leaving at a right angle."""
    si = rng.randrange(len(p.strokes))
    x, y, h = p.at(si, _c(rng, .25, .5, .75))
    side = rng.choice([-1, 1])
    if how == "ring":
        p.begin(x, y, h)
        p.arc(side * 360, RAD[0])
    else:
        p.begin(x, y, h + side * 90)
        p.line(TICK)


def _finish_free(p, rng, ring=True):
    """Free-frame letters are mostly rings and loops: one with no loop of its own gets a ring beside it, and some get a tick as
    well. Then the letter is stretched to the same top and foot as every other."""
    if ring and not p.loops and rng.random() < LOOP_FILL:
        _adorn(p, rng, "ring")
    if ring and rng.random() < ADORN_FREE and len(p.strokes) < 3:
        _adorn(p, rng, "tick")
    return p.done(rng.random() < .4, fit=True)


# ---- free frame ---------------------------------------------------------------------------------------------------------
# ---- Tamil atoms: a full-height vertical (V), a connecting bar that leaves it at the lower guide (H), and the long enclosing "bell" ----
# swoop that ends in a circle (BELL), which recurs in many letters at different orientations ----------------------------------------
HJOIN = 0.3            # where the connecting bar leaves the vertical (about three quarters of the way down)


def _bell(p, x, y, heading, r=0.3, mirror=False):
    """The bell: from (x, y) round under (a half turn of radius r), up the far side, over in a quarter turn and out to a small
    circle. `heading` turns the whole shape (0 is the usual orientation, drawn from a bar that ends to the left); `mirror` flips it."""
    sg = -1 if mirror else 1
    p.begin(x, y, heading - 90 * sg)
    p.arc(sg * 180, r)
    p.line(r * 1.15)
    p.arc(sg * 90, r * .5)
    p.line(r * .25)
    p.arc(sg * 360, RAD[0] * .8)


def f_a(rng, style):                          # a vertical, a bar from it out to the left, and a bell that begins at the bar's end (அ)
    p = Pen(rng, style)
    sx = _c(rng, .5, .55)
    s = p.begin(sx, TOP, -90)
    p.line(TOP)
    p.begin(sx, HJOIN, 180)
    p.line(sx - .12)
    _bell(p, p.x, p.y, 0, r=_c(rng, .28, .3), mirror=False)
    return _finish_free(p, rng, ring=False)


def f_bell(rng, style):                       # the bell alone, turned a quarter, half or three quarters round, or mirrored
    p = Pen(rng, style)
    _bell(p, .3, .5, _c(rng, 0, 90, 180, 270), r=_c(rng, .25, .3), mirror=rng.random() < .5)
    return _finish_free(p, rng, ring=False)


def f_v_bell(rng, style):                     # a vertical with a bell that starts from its foot and rises beside it (ஆ ஊ)
    p = Pen(rng, style)
    sx = _c(rng, .25, .35)
    s = p.begin(sx, TOP, -90)
    p.line(TOP)
    _bell(p, sx, BASE + .02, _c(rng, 0, 90), r=_c(rng, .22, .28), mirror=rng.random() < .5)
    return _finish_free(p, rng, ring=False)


def f_h_bell(rng, style):                     # a bar with a bell hanging from its end (இ ஈ)
    p = Pen(rng, style)
    p.begin(.7, HJOIN + .3, 180)
    p.line(_c(rng, ARM[1], ARM[2]))
    _bell(p, p.x, p.y, _c(rng, 0, 180), r=.25, mirror=rng.random() < .5)
    return _finish_free(p, rng, ring=False)


def f_loop_tail(rng, style):                  # a loop that carries on into a tail (ல ல்)
    p = Pen(rng, style)
    p.begin(RIGHT, HI, 180)
    p.arc(_c(rng, 270, 360), RAD[2])
    p.line(_c(rng, *ARM))
    if rng.random() < .4:
        p.arc(-90, RAD[1])
    return _finish_free(p, rng)


def f_s_curve(rng, style):                    # two half-turns back to back, an S (ஸ ஞ)
    p = Pen(rng, style)
    p.begin(RIGHT, TOP, 180)
    r = _c(rng, *RAD[1:])
    p.arc(180, r)
    p.arc(-180, r)
    return _finish_free(p, rng)


def f_ring_tick(rng, style):                  # a ring with a short stroke leaving it at a right angle (ம ள ள)
    p = Pen(rng, style)
    ring = p.begin(CENTER + RAD[2], MID, 90)
    p.arc(360, RAD[2])
    x, y, h = p.at(ring, _c(rng, 0.0, .25, .5))
    p.begin(x, y, h - 90)                         # leaves the ring outwards (the ring runs counter-clockwise)
    p.line(_c(rng, TICK, ARM[0]))
    if rng.random() < .4:
        p.arc(-90, RAD[0])
    return _finish_free(p, rng)


def f_hook_stem(rng, style):                  # a stroke down that hooks at the foot, with a bar off its middle (த ந)
    p = Pen(rng, style)
    sx = _c(rng, LEFT + .1, CENTER)
    s = p.begin(sx, TOP, -90)
    p.line(MID)
    p.arc(_c(rng, 90, 180), RAD[2])
    if rng.random() < .65:
        x, y, _ = p.at(s, .5)
        p.begin(x, y, 0)
        p.line(_c(rng, *ARM[1:]))
    return _finish_free(p, rng)


def f_double_loop(rng, style):                # two loops, one after the other (அ ஐ)
    p = Pen(rng, style)
    p.begin(LEFT, MID, 90)
    r = RAD[1]
    p.arc(-270, r)
    p.arc(270, r)
    p.line(_c(rng, TICK, ARM[0]))
    return _finish_free(p, rng)


def f_angle(rng, style):                      # a stroke down that turns along the foot, with a short stroke added at its middle (ட ட்)
    p = Pen(rng, style)
    s = p.begin(LEFT, TOP, -90)
    p.line(HI)
    if rng.random() < .5:
        p.arc(90, RAD[0])
    else:
        p.turn(90)
    p.line(_c(rng, ARM[1], ARM[2], .6))
    if rng.random() < .5:
        x, y, _ = p.at(s, .5)
        p.begin(x, y, 0)
        p.line(TICK)
    return _finish_free(p, rng)


def f_cup_tick(rng, style):                   # a cup opening upward, with a stroke dropping from the middle of its foot (ம ய)
    p = Pen(rng, style)
    r = _c(rng, RAD[1], RAD[2])
    cup = p.begin(LEFT, MID, -90)
    p.arc(180, r)
    if rng.random() < .75:
        x, y, h = p.at(cup, .5)
        p.begin(x, y, h - 90 if h > 0 else h + 90)
        p.line(_c(rng, TICK, ARM[0]))
    return _finish_free(p, rng)


def f_wave(rng, style):                       # a wave of two or three humps (ஊ ய)
    p = Pen(rng, style)
    p.begin(LEFT - .1, MID, 90)
    r = RAD[0]
    for i in range(rng.choice([2, 3])):
        p.arc((-1) ** (i + 1) * 180, r)
    return _finish_free(p, rng)


def f_arc_stem(rng, style):                   # an arch whose end drops into a stem (ந ற)
    p = Pen(rng, style)
    p.begin(LEFT, MID, 90)
    p.arc(-180, RAD[2])
    p.line(_c(rng, MID, HI))
    return _finish_free(p, rng)


def f_spiral(rng, style):                     # an arm that winds inward (ஞ ழ)
    p = Pen(rng, style)
    p.begin(RIGHT, TOP, 180)
    p.line(_c(rng, 0.1, ARM[0]))
    r = RAD[2] + .05
    p.arc(180, r)
    p.arc(_c(rng, 180, 270), r * .55)
    return _finish_free(p, rng)


STEM = {"fork": s_fork, "slant_stem": s_slant_stem, "arm_bowl": s_arm_bowl, "two_arms": s_two_arms, "foot_hook": s_foot_hook, "two_stems": s_two_stems,
        "arm_loop": s_arm_loop, "slash_arm": s_slash_arm, "bowl_stem": s_bowl_stem, "arm_tick": s_arm_tick, "stem_ring": s_stem_ring}
FREE = {"loop_tail": f_loop_tail, "s_curve": f_s_curve, "ring_tick": f_ring_tick, "hook_stem": f_hook_stem,
        "double_loop": f_double_loop, "angle": f_angle, "cup_tick": f_cup_tick, "arc_stem": f_arc_stem,
        "spiral": f_spiral, "a": f_a, "bell": f_bell, "v_bell": f_v_bell, "h_bell": f_h_bell}
ARCHETYPES = {**STEM, **FREE}
LOOPY = {"arm_loop", "stem_ring", "loop_tail", "ring_tick", "double_loop", "spiral", "a", "bell", "v_bell", "h_bell"}       # archetypes that hold a loop or ring
FILL = (0.6, 0.4)                                # the least height and width of a letter


def archetypes(frame: str) -> list:
    """The archetypes a frame draws from: stem, free, one of the vocabulary families (pen_vocab.py), or both stem and free."""
    if frame in _V.FAMILIES:
        return list(_V.FAMILIES[frame])
    return (list(STEM) if frame == "stem" else list(FREE) if frame == "free" else list(ARCHETYPES))


# how much each archetype is liked: the recipes that close a hole (two stems with a bar, a bowl hung on the stem) are rarer than the
# open ones, as in the real scripts, where about a third of the letters hold a hole
LIKE = {"two_stems": 0.35, "bowl_stem": 0.4, "slash_arm": 0.7, "stem_ring": 0.7, "arm_loop": 0.7, "fork": 1.4, "slant_stem": 1.4, "two_arms": 1.3, "foot_hook": 1.2,
        "a": 2.5, "bell": 2.0, "v_bell": 2.0, "h_bell": 2.0, "loop_tail": .6, "s_curve": .5, "double_loop": .5, "spiral": .5, "ring_tick": .8}


def weights(loops: float, frame: str = "both") -> dict:
    names = archetypes(frame)
    return {n: ((0.3 + 2.2 * loops) if n in LOOPY else 1.0) * LIKE.get(n, 1.0) for n in names}


def _along(pts, t):
    """The point a fraction t of the way along a polyline, and the direction (radians) it is heading there."""
    segs = [(math.dist(a, b), a, b) for a, b in zip(pts, pts[1:])]
    total = sum(sg[0] for sg in segs) or 1e-9
    want = t * total
    for ln, a, b in segs:
        if want <= ln or (a, b) == (segs[-1][1], segs[-1][2]):
            f = 0 if ln == 0 else min(1.0, want / ln)
            return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])), math.atan2(b[1] - a[1], b[0] - a[0])
        want -= ln
    return tuple(pts[-1]), 0.0


def garnish(rng, strokes, ticks=0.0, crosses=0.0):
    """Small strokes added to a finished letter, at the places a pen adds them: a short tick leaving a stroke at a right angle (a T
    junction), and a short bar crossing a stroke (a four-way junction). Each is placed at a quarter, half or three quarters of a
    stroke, so the extras line up from letter to letter. The pen's `stroke_ticks` and `stroke_crossings` dials set how often."""
    out = list(strokes)
    body = [st for st in strokes if len(st["p"]) >= 2 and not st.get("dot")]
    for kind, share in (("tick", ticks), ("cross", crosses)):
        if not body or len(out) >= 8:
            break
        n = int(share) + (rng.random() < share - int(share))
        for _ in range(n):
            st = rng.choice(body)
            (x, y), a = _along(st["p"], _c(rng, .25, .5, .75))
            side = rng.choice([-1, 1])
            if kind == "tick":
                ends = [(x, y), (x + TICK * math.cos(a + side * math.pi / 2), y + TICK * math.sin(a + side * math.pi / 2))]
            else:
                h = TICK * .8
                ends = [(x - h * math.cos(a + math.pi / 2), y - h * math.sin(a + math.pi / 2)), (x + h * math.cos(a + math.pi / 2), y + h * math.sin(a + math.pi / 2))]
            if all(0.0 <= u <= 1.0 and -0.3 <= v <= 1.0 for u, v in ends):
                out.append(dict(stroke([(round(u, 3), round(v, 3)) for u, v in ends]), k="s"))
    return out


def headless(rng, strokes):
    """A letter drawn without the top bar: a little shorter, so it stops short of the bar line (Bengali has many)."""
    top = max(y for st in strokes for _, y in st["p"])
    f = HEADLESS / max(top, .1)
    return [dict(st, p=[[x, round(y * f if y > 0 else y, 3)] for x, y in st["p"]]) for st in strokes]


# ---- vowel signs: small pen strokes that sit beside a letter, one family of shapes per side ------------------------------
def sign_strokes(rng, slot, style):
    """A small pen-drawn sign for a slot, in a unit box (the caller sizes it): a stem with a flick on the right (ा), a stem that
    curls over at the left (ि), a hook under the letter (ु ू), a slash or arc over it (े ै ं). The same vocabulary as the letters:
    upright stems, quarter and half turns, one of two slants. Returns (kind, strokes)."""
    p = Pen(rng, style)
    if slot == "right":
        kind = rng.choice(["stem", "stem_hook", "stem_arm"])
        p.begin(.5, 1.0, -90)
        p.line(1.0 if kind == "stem" else .72)
        if kind == "stem_hook":
            p.arc(-90, RAD[1])
        elif kind == "stem_arm":
            x, y, _ = p.at(0, .5)
            p.begin(x, y, 0)
            p.line(.5)
    elif slot == "left":
        kind = rng.choice(["curl_stem", "stem_arc"])
        p.begin(.3, 0, 90)
        p.line(.65)
        p.arc(-180 if kind == "curl_stem" else -90, RAD[1])
    elif slot == "below":
        kind = rng.choice(["hook", "hook2", "tick_hook"])
        p.begin(.6, 1.0, -90)
        p.line(.3)
        p.arc(180 if kind != "hook2" else 90, RAD[1])
        if kind == "hook2":
            p.arc(-90, RAD[0])
        elif kind == "tick_hook":
            x, y, _ = p.at(0, .2)
            p.begin(x, y, 0)
            p.line(.4)
    else:                                                  # above
        kind = rng.choice(["slash", "arc", "double_slash", "flag"])
        a = _c(rng, 45, 60)
        if kind == "slash":
            p.begin(.15, .1, a)
            p.line(.85)
        elif kind == "double_slash":
            for dx in (0.0, .38):
                p.begin(.1 + dx, .1, a)
                p.line(.6)
        elif kind == "arc":
            p.begin(.1, .15, 60)
            p.arc(-120, .4)
        else:
            p.begin(.2, .1, 90)
            p.line(.65)
            p.turn(-90)
            p.line(.4)
    strokes = p.done()
    xs, ys = [x for st in strokes for x, _ in st["p"]], [y for st in strokes for _, y in st["p"]]
    x0, y0, bw, bh = min(xs), min(ys), max(max(xs) - min(xs), .02), max(max(ys) - min(ys), .02)
    return "pen_" + kind, [dict(st, p=[[round((x - x0) / bw, 4), round((y - y0) / bh, 4)] for x, y in st["p"]]) for st in strokes]


# ---- the vocabulary families (pen v3), registered last because they build on everything above -------------------------------
from . import pen_vocab as _V    # noqa: E402

ARCHETYPES.update(_V.NEW)
ARCHETYPES.update({n: f for fam in _V.FAMILIES.values() for n, f in fam.items()})
LOOPY |= _V.LOOPY
LIKE.update(_V.LIKE)
