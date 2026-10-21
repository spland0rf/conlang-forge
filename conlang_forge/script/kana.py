"""The "stroke" family: letters built like the Japanese kana. Unlike the other families (one figure plus a small variant),
every letter is its own arrangement of one to four short strokes, and the strokes need not touch: a letter may be two or
three pieces that read as one unit.

Two hands, chosen by the `stroke_hand` dial:
  angular  (katakana-like): straight strokes at a few angles, sharp corners, short slashes and hooks;
  flowing  (hiragana-like): curved strokes, hooks, and one small loop; the corners are rounded when drawn.

A letter is made from an archetype (a stroke arrangement such as "bar crossed by a slash", "two slashes", "stem with a loop")
whose positions, lengths and bends are jittered, so one archetype gives many different letters. Letters of one sound class
prefer one archetype, so related sounds look related (the same idea as the characteristic shapes of the other families).
Unit box, y up."""
from __future__ import annotations

import math

from .geometry import stroke

HANDS = ("angular", "flowing")
MAX_PARTS = 3          # separate pieces a letter may have
MAX_GAP = 0.3          # how far apart two pieces may be and still read as one letter


def _j(rng, v, a=0.06):
    return v + rng.uniform(-a, a)


def _line(*c):
    """A stroke from flat coordinates x0, y0, x1, y1, ..."""
    return stroke([(round(c[i], 3), round(c[i + 1], 3)) for i in range(0, len(c), 2)])


# ---- angular archetypes (katakana-like) -------------------------------------------------------------------------------
def a_cross_slash(rng):                       # a bar crossed by a slash (ナ メ)
    y = _j(rng, .66)
    return [_line(_j(rng, .02), y, _j(rng, .98), y), _line(_j(rng, .55), 1, _j(rng, .12), _j(rng, .02, .03))]


def a_bar_hook(rng):                          # a bar that drops on the right, with a slash through it (カ)
    y = _j(rng, .7)
    return [_line(_j(rng, .02), y, _j(rng, .92), y, _j(rng, .86), _j(rng, .12), _j(rng, .6), 0),
            _line(_j(rng, .42), 1, _j(rng, .32), _j(rng, .4), _j(rng, .05), 0)]


def a_two_slash(rng):                         # two slashes that part like a roof (ハ)
    return [_line(_j(rng, .38, .04), _j(rng, .88), _j(rng, .06), 0), _line(_j(rng, .6, .04), _j(rng, .88), _j(rng, .94), _j(rng, .1, .08))]


def a_box_open(rng):                          # an open box, with a middle bar for some (コ ヨ)
    s = [_line(_j(rng, .08), _j(rng, .85), _j(rng, .9), _j(rng, .85), _j(rng, .9), _j(rng, .08), _j(rng, .08), _j(rng, .08))]
    if rng.random() < .5:
        s.append(_line(.08, .47, _j(rng, .9), .47))
    return s


def a_angle_slash(rng):                       # a small slash, then a bar that turns and slants down (ク マ)
    return [_line(_j(rng, .45), 1, _j(rng, .12), _j(rng, .55)),
            _line(_j(rng, .3, .04), _j(rng, .82), _j(rng, .94), _j(rng, .82), _j(rng, .82), _j(rng, .45), _j(rng, .3), 0)]


def a_bars_spine(rng):                        # two slanted bars crossed by a spine (キ)
    return [_line(.08, _j(rng, .78), .92, _j(rng, .9)), _line(.04, _j(rng, .44), .96, _j(rng, .55)),
            _line(_j(rng, .52), 1, _j(rng, .4), 0)]


def a_stem_branch(rng):                       # a stem with a short branch (ト)
    x = _j(rng, .3)
    return [_line(x, 1, x, 0), _line(x, _j(rng, .55), _j(rng, .96, .03), _j(rng, .32))]


def a_two_stems(rng):                         # two upright strokes, the right one hooked (リ)
    return [_line(_j(rng, .2, .03), 1, _j(rng, .2, .03), _j(rng, .12)), _line(_j(rng, .8, .03), 1, _j(rng, .8, .03), _j(rng, .22), _j(rng, .42), 0)]


def a_zig(rng):                               # a bar, a slash back, and a second slash out (ス)
    return [_line(_j(rng, .06), _j(rng, .82), _j(rng, .92), _j(rng, .82), _j(rng, .3), _j(rng, .42)),
            _line(_j(rng, .38), _j(rng, .52), _j(rng, .94), _j(rng, .04, .03))]


def a_ticks(rng):                             # two short ticks over a long sweep (ツ シ)
    return [_line(_j(rng, .14), _j(rng, .9), _j(rng, .28), _j(rng, .64)), _line(_j(rng, .4), _j(rng, .96), _j(rng, .54), _j(rng, .7)),
            _line(_j(rng, .92), _j(rng, .92), _j(rng, .78), _j(rng, .5), _j(rng, .3), 0)]


def a_hook(rng):                              # one bar that slants down and back (フ ワ)
    s = [_line(_j(rng, .08), _j(rng, .84), _j(rng, .92), _j(rng, .84), _j(rng, .82), _j(rng, .44), _j(rng, .28), 0)]
    if rng.random() < .45:
        s.append(_line(.08, .84, .08, _j(rng, .5)))
    return s


def a_chevron(rng):                           # a roof (ヘ) with an optional tick
    s = [_line(0, _j(rng, .12), _j(rng, .4), _j(rng, .96, .03), 1, _j(rng, .2))]
    if rng.random() < .5:
        s.append(_line(_j(rng, .42), _j(rng, .55), _j(rng, .55), 0))
    return s


def a_two_bars(rng):                          # a short bar, a stem and a long bar (エ)
    x = _j(rng, .5, .05)
    return [_line(_j(rng, .15), _j(rng, .86), _j(rng, .85), _j(rng, .86)), _line(x, _j(rng, .86), x, _j(rng, .14)),
            _line(_j(rng, .04, .03), _j(rng, .14), _j(rng, .96, .03), _j(rng, .14))]


def a_roof_stem(rng):                         # a roof and a stem (ヒ ビ without marks)
    x = _j(rng, .3)
    return [_line(x, 1, x, 0), _line(x, _j(rng, .78), _j(rng, .9), _j(rng, .78)), _line(x, _j(rng, .1), _j(rng, .92), _j(rng, .1))]


def a_n_hook(rng):                            # a slash and a long hooked stroke (ノ ン レ)
    return [_line(_j(rng, .12), 1, _j(rng, .22), _j(rng, .62)), _line(_j(rng, .14), _j(rng, .4), _j(rng, .92), _j(rng, .03, .02))] \
        if rng.random() < .5 else [_line(_j(rng, .2), 1, _j(rng, .2), _j(rng, .2), _j(rng, .94), _j(rng, .6))]


ANGULAR = {"cross_slash": a_cross_slash, "bar_hook": a_bar_hook, "two_slash": a_two_slash, "box_open": a_box_open,
           "angle_slash": a_angle_slash, "bars_spine": a_bars_spine, "stem_branch": a_stem_branch, "two_stems": a_two_stems,
           "zig": a_zig, "ticks": a_ticks, "hook": a_hook, "chevron": a_chevron, "two_bars": a_two_bars, "roof_stem": a_roof_stem,
           "n_hook": a_n_hook}


# ---- flowing archetypes (hiragana-like): control points of a path the renderer rounds ----------------------------------
def f_loop_stem(rng):                         # a bar, a stem and a small loop (は ま ほ)
    x = _j(rng, .42)
    s = [_line(_j(rng, .1), _j(rng, .84), _j(rng, .9), _j(rng, .86)), _line(x, 1, x + _j(rng, 0, .04), .1)]
    cx, cy = _j(rng, .55), _j(rng, .3)
    s.append(_line(x - .02, cy + .22, cx + .3, cy + .12, cx + .35, cy - .12, cx + .05, cy - .25, x - .22, cy - .02, cx + .1, cy + .18))
    return s


def f_spiral(rng):                            # one looping stroke (の)
    return [_line(_j(rng, .55), _j(rng, .84), _j(rng, .6), _j(rng, .42), _j(rng, .34), _j(rng, .06), _j(rng, .08), _j(rng, .3),
                  _j(rng, .28), _j(rng, .82), _j(rng, .8), _j(rng, .88), _j(rng, .94), _j(rng, .5), _j(rng, .85), _j(rng, .12))]


def f_ru(rng):                                # a bar sweeping into a loop at the bottom (る ろ)
    return [_line(_j(rng, .12), _j(rng, .9), _j(rng, .7), _j(rng, .92), _j(rng, .4), _j(rng, .6), _j(rng, .15), _j(rng, .5),
                  _j(rng, .55), _j(rng, .52), _j(rng, .85), _j(rng, .3), _j(rng, .6), _j(rng, .06), _j(rng, .24), _j(rng, .18))]


def f_j(rng):                                 # a stem curving into a hook (し)
    return [_line(_j(rng, .32), 1, _j(rng, .3), _j(rng, .36), _j(rng, .42), _j(rng, .06), _j(rng, .74), _j(rng, .08), _j(rng, .94), _j(rng, .36))]


def f_ku(rng):                                # a soft chevron (く)
    return [_line(_j(rng, .78), 1, _j(rng, .22), _j(rng, .52), _j(rng, .82), _j(rng, .02, .03))]


def f_tick_arc(rng):                          # a tick over an arc that falls back (う)
    return [_line(_j(rng, .34), 1, _j(rng, .55), _j(rng, .86)),
            _line(_j(rng, .16), _j(rng, .68), _j(rng, .66), _j(rng, .62), _j(rng, .82), _j(rng, .36), _j(rng, .55), _j(rng, .08), _j(rng, .28), _j(rng, .02, .03))]


def f_bars_stem(rng):                         # two curved bars on a stem that ends in a hook (ま without its loop, よ)
    x = _j(rng, .5)
    return [_line(_j(rng, .12), _j(rng, .88), _j(rng, .5), _j(rng, .94), _j(rng, .88), _j(rng, .88)),
            _line(_j(rng, .18), _j(rng, .6), _j(rng, .5), _j(rng, .66), _j(rng, .84), _j(rng, .6)),
            _line(x, 1, x - .02, _j(rng, .3), _j(rng, .34), _j(rng, .04, .03), _j(rng, .14), _j(rng, .14))]


def f_cross_loop(rng):                        # a bar crossed by a curve that loops (あ め ぬ)
    s = [_line(_j(rng, .1), _j(rng, .76), _j(rng, .55), _j(rng, .82), _j(rng, .92), _j(rng, .74))]
    s.append(_line(_j(rng, .42), 1, _j(rng, .48), _j(rng, .6), _j(rng, .2), _j(rng, .25), _j(rng, .5), _j(rng, .02, .03), _j(rng, .88), _j(rng, .26), _j(rng, .58), _j(rng, .52)))
    return s


def f_sweep_dot(rng):                         # a falling sweep and a dot-like tick (や か)
    return [_line(_j(rng, .12), _j(rng, .66), _j(rng, .5), _j(rng, .76), _j(rng, .8), _j(rng, .62), _j(rng, .5), _j(rng, .2), _j(rng, .34), 0),
            _line(_j(rng, .58), 1, _j(rng, .7), _j(rng, .86))]


def f_s(rng):                                 # an S with a head (す せ そ)
    return [_line(_j(rng, .12), _j(rng, .82), _j(rng, .88), _j(rng, .84)),
            _line(_j(rng, .55), 1, _j(rng, .5), _j(rng, .58), _j(rng, .22), _j(rng, .4), _j(rng, .6), _j(rng, .34), _j(rng, .48), _j(rng, .06), _j(rng, .18), _j(rng, .1))]


def f_two_curves(rng):                        # a stem and a long curve beside it (に た け)
    return [_line(_j(rng, .2), 1, _j(rng, .22), _j(rng, .08)), _line(_j(rng, .42), _j(rng, .78), _j(rng, .94), _j(rng, .8)),
            _line(_j(rng, .42), _j(rng, .3), _j(rng, .94), _j(rng, .28))]


def f_hook_line(rng):                         # a hooked stem and a crossing bar (て り)
    return [_line(_j(rng, .1), _j(rng, .82), _j(rng, .9), _j(rng, .88)),
            _line(_j(rng, .55), _j(rng, .9), _j(rng, .5), _j(rng, .42), _j(rng, .36), _j(rng, .08), _j(rng, .8), _j(rng, .1, .04))]


def f_wave(rng):                              # a double-humped stroke (ね れ わ)
    return [_line(_j(rng, .24), 1, _j(rng, .24), _j(rng, .08)),
            _line(_j(rng, .24), _j(rng, .62), _j(rng, .55), _j(rng, .88), _j(rng, .7), _j(rng, .55), _j(rng, .52), _j(rng, .3), _j(rng, .88), _j(rng, .12))]


FLOWING = {"loop_stem": f_loop_stem, "spiral": f_spiral, "ru": f_ru, "j": f_j, "ku": f_ku, "tick_arc": f_tick_arc,
           "bars_stem": f_bars_stem, "cross_loop": f_cross_loop, "sweep_dot": f_sweep_dot, "s": f_s, "two_curves": f_two_curves,
           "hook_line": f_hook_line, "wave": f_wave}

ARCHETYPES = {"angular": ANGULAR, "flowing": FLOWING}


def archetypes(hand: str) -> list:
    return list(ARCHETYPES[hand])


EXTRA_TICK = {"angular": 0.3, "flowing": 0.25}      # how often a letter gets a small detached tick (ツ ミ シ, こ う): kana have about two pieces each


def _tick(rng, hand, strokes):
    """A short tick in a free spot close to the letter (clear of its strokes, but near enough to read as part of it)."""
    from .graph import points
    ink = [p for s in strokes for p in points([s], step=0.05)]
    for _ in range(14):
        x, y = rng.uniform(.08, .92), rng.uniform(.1, .92)
        d = min(math.hypot(x - u, y - v) for u, v in ink)
        if .16 <= d <= .27:
            if hand == "angular":
                return [_line(x - .05, y + .06, x + .06, y - .06)]
            return [_line(x - .05, y + .05, x, y + .01, x + .06, y - .05)]
    return []


def make(rng, hand: str, name: str | None = None, mirror_ok: bool = True, extra: float | None = None):
    """One letter of the given hand: (archetype name, strokes in the unit box). The archetype is jittered every time; a
    mirrored copy is used now and then, so one archetype stretches over many letters."""
    table = ARCHETYPES[hand]
    name = name if name in table else rng.choice(sorted(table))
    strokes = table[name](rng)
    if extra is None:
        extra = EXTRA_TICK[hand]
    if rng.random() < extra and len(strokes) < 4:
        strokes = strokes + _tick(rng, hand, strokes)
    if mirror_ok and rng.random() < .2:
        strokes = [dict(s, p=[[round(1 - x, 3), y] for x, y in s["p"]]) for s in strokes]
    return name, strokes


def reads_as_one(strokes) -> bool:
    """The pieces of a letter lie close enough together to read as one letter, and there are not too many."""
    from .graph import analyse
    a = analyse(strokes)
    if a["parts"] > MAX_PARTS:
        return False
    if a["parts"] == 1:
        return True
    from .graph import points
    pieces = [points([s], step=0.05) or [tuple(s["p"][0])] for s in strokes]
    # every stroke must come within MAX_GAP of another stroke (single-link): the letter has no far-off straggler
    for i, pi in enumerate(pieces):
        if not any(i != j and min(math.hypot(x - u, y - v) for x, y in pi for u, v in pj) <= MAX_GAP for j, pj in enumerate(pieces)):
            return False
    return True


def fills(strokes, min_h=0.78, min_w=0.55) -> bool:
    """A kana fills its square: tall enough and wide enough (a lone short tick or a bar low in the box is not a letter)."""
    from .geometry import bbox
    x0, y0, x1, y1 = bbox(strokes)
    return (y1 - y0) >= min_h and (x1 - x0) >= min_w
