"""The "stroke" family: letters built like the Japanese kana. Unlike the other families (one figure plus a small variant),
every letter is its own arrangement of one to four short strokes, and the strokes need not touch: a letter may be two or
three pieces that read as one unit.

Three hands, chosen by the `stroke_hand` dial:
  angular  (katakana-like): straight strokes at a few angles, sharp corners, short slashes and hooks;
  flowing  (hiragana-like): curved strokes, hooks, and one small loop; the corners are rounded when drawn;
  bowed    (Elvish-like): a stem carrying one or two round bows (the stem may reach above or below the line), plus a few
           curls, rings and hooks; every letter is one connected piece, with vowel marks added above by the abugida machinery.

A letter is made from an archetype (a stroke arrangement such as "bar crossed by a slash", "two slashes", "stem with a loop")
whose positions, lengths and bends are jittered, so one archetype gives many different letters. Letters of one sound class
prefer one archetype, so related sounds look related (the same idea as the characteristic shapes of the other families).
Unit box, y up."""
from __future__ import annotations

import math

from .geometry import stroke

HANDS = ("angular", "flowing", "bowed")
MAX_PARTS = 4          # separate pieces a letter may have
MAX_GAP = 0.3          # how far apart two pieces may be and still read as one letter


def _j(rng, v, a=0.06):
    return v + rng.uniform(-a, a)


def _line(*c):
    """A stroke from flat coordinates x0, y0, x1, y1, ..."""
    return stroke([(round(min(max(c[i], .02), .98), 3), round(min(max(c[i + 1], .04), 1.0), 3)) for i in range(0, len(c), 2)])


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


def a_ho(rng):                                # a bar, a stem through it, two ticks beside the stem (ホ)
    y, x = _j(rng, .68), _j(rng, .5, .04)
    return [_line(.04, y, .96, y), _line(x, 1, x, .04), _line(_j(rng, .24), _j(rng, .4), _j(rng, .12), _j(rng, .1)), _line(_j(rng, .76), _j(rng, .4), _j(rng, .88), _j(rng, .1))]


def a_te(rng):                                # three bars with a hook (テ)
    x = _j(rng, .55, .05)
    return [_line(_j(rng, .22), _j(rng, .84), _j(rng, .78), _j(rng, .84)), _line(.06, _j(rng, .55), .94, _j(rng, .55)),
            _line(x, _j(rng, .55), x - .02, _j(rng, .3), _j(rng, .3), 0)]


def a_chi(rng):                               # a tick, a long bar and a crossing hook (チ)
    return [_line(_j(rng, .3), _j(rng, .92), _j(rng, .75), _j(rng, .98)), _line(.04, _j(rng, .62), .96, _j(rng, .62)),
            _line(_j(rng, .55), _j(rng, .62), _j(rng, .52), _j(rng, .3), _j(rng, .3), _j(rng, .02, .02))]


def a_mo(rng):                                # two bars through a hooked stem (モ)
    x = _j(rng, .46, .04)
    return [_line(.1, _j(rng, .86), .9, _j(rng, .86)), _line(.1, _j(rng, .55), .9, _j(rng, .55)),
            _line(x, 1, x, _j(rng, .22), _j(rng, .75), _j(rng, .06, .03))]


def a_ne(rng):                                # a dot-slash, a bar and a long hook (ネ)
    x = _j(rng, .5, .04)
    return [_line(_j(rng, .4), 1, _j(rng, .55), _j(rng, .86)), _line(.1, _j(rng, .76), .9, _j(rng, .76)), _line(x, _j(rng, .76), x, _j(rng, .2), _j(rng, .35), 0),
            _line(_j(rng, .12), _j(rng, .45), _j(rng, .3), _j(rng, .58), _j(rng, .12), _j(rng, .12))] if rng.random() < .5 else \
           [_line(.1, _j(rng, .76), .9, _j(rng, .76)), _line(x, 1, x, _j(rng, .2), _j(rng, .35), 0), _line(_j(rng, .12), _j(rng, .5), _j(rng, .3), _j(rng, .62))]


ANGULAR = {"cross_slash": a_cross_slash, "bar_hook": a_bar_hook, "two_slash": a_two_slash, "box_open": a_box_open,
           "angle_slash": a_angle_slash, "bars_spine": a_bars_spine, "stem_branch": a_stem_branch, "two_stems": a_two_stems,
           "zig": a_zig, "ticks": a_ticks, "hook": a_hook, "chevron": a_chevron, "two_bars": a_two_bars, "roof_stem": a_roof_stem,
           "n_hook": a_n_hook, "ho": a_ho, "te": a_te, "chi": a_chi, "mo": a_mo, "ne": a_ne}


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


def f_ru(rng):                                # a bar sweeping into a loop at the bottom (る ろ); the end crosses the path, so the loop closes
    return [_line(_j(rng, .15), _j(rng, .88), _j(rng, .72), _j(rng, .9), _j(rng, .35), _j(rng, .55), _j(rng, .6), _j(rng, .42), _j(rng, .85), _j(rng, .25),
                  _j(rng, .6), _j(rng, .05), _j(rng, .3), _j(rng, .2), _j(rng, .5), _j(rng, .52))]


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
    s.append(_line(_j(rng, .42), 1, _j(rng, .48), _j(rng, .6), _j(rng, .2), _j(rng, .25), _j(rng, .5), _j(rng, .02, .03), _j(rng, .88), _j(rng, .26), _j(rng, .3), _j(rng, .47)))
    return s


def f_sweep_dot(rng):                         # a falling sweep and a dot-like tick (や か)
    return [_line(_j(rng, .12), _j(rng, .66), _j(rng, .5), _j(rng, .76), _j(rng, .8), _j(rng, .62), _j(rng, .5), _j(rng, .2), _j(rng, .34), 0),
            _line(_j(rng, .58), 1, _j(rng, .7), _j(rng, .86))]


def f_s(rng):                                 # a bar and a stem that loops (す)
    return [_line(_j(rng, .12), _j(rng, .84), _j(rng, .88), _j(rng, .86)),
            _line(_j(rng, .56), .98, _j(rng, .52), _j(rng, .6), _j(rng, .78), _j(rng, .5), _j(rng, .72), _j(rng, .1), _j(rng, .4), _j(rng, .3), _j(rng, .62), _j(rng, .72))]


def f_two_curves(rng):                        # a stem and a long curve beside it (に た け)
    return [_line(_j(rng, .2), 1, _j(rng, .22), _j(rng, .08)), _line(_j(rng, .42), _j(rng, .78), _j(rng, .94), _j(rng, .8)),
            _line(_j(rng, .42), _j(rng, .3), _j(rng, .94), _j(rng, .28))]


def f_hook_line(rng):                         # a hooked stem and a crossing bar (て り)
    return [_line(_j(rng, .1), _j(rng, .82), _j(rng, .9), _j(rng, .88)),
            _line(_j(rng, .55), _j(rng, .9), _j(rng, .5), _j(rng, .42), _j(rng, .36), _j(rng, .08), _j(rng, .8), _j(rng, .1, .04))]


def f_wave(rng):                              # a double-humped stroke (ね れ わ)
    return [_line(_j(rng, .24), 1, _j(rng, .24), _j(rng, .08)),
            _line(_j(rng, .24), _j(rng, .62), _j(rng, .55), _j(rng, .88), _j(rng, .7), _j(rng, .55), _j(rng, .52), _j(rng, .3), _j(rng, .88), _j(rng, .12))]


def f_a(rng):                                 # a bar, a stem that loops, and a long tail (あ)
    return [_line(_j(rng, .12), _j(rng, .78), _j(rng, .5), _j(rng, .82), _j(rng, .88), _j(rng, .78)),
            _line(_j(rng, .46), 1, _j(rng, .44), _j(rng, .55), _j(rng, .18), _j(rng, .3), _j(rng, .36), _j(rng, .05), _j(rng, .74), _j(rng, .2), _j(rng, .6), _j(rng, .5), _j(rng, .44), _j(rng, .55)),
            _line(_j(rng, .76), _j(rng, .92), _j(rng, .9), _j(rng, .5), _j(rng, .78), _j(rng, .12), _j(rng, .52), _j(rng, .03, .03))]


def f_na(rng):                                # a cross, a tick and a loop (な)
    return [_line(_j(rng, .08), _j(rng, .76), _j(rng, .46), _j(rng, .8)), _line(_j(rng, .3), 1, _j(rng, .26), _j(rng, .5), _j(rng, .1), _j(rng, .2)),
            _line(_j(rng, .62), _j(rng, .9), _j(rng, .72), _j(rng, .74)),
            _line(_j(rng, .58), _j(rng, .55), _j(rng, .42), _j(rng, .34), _j(rng, .56), _j(rng, .08), _j(rng, .86), _j(rng, .2), _j(rng, .7), _j(rng, .46), _j(rng, .5), _j(rng, .36))]


def f_ki(rng):                                # two bars, a slanted stem and a hooked foot (き)
    return [_line(_j(rng, .12), _j(rng, .8), _j(rng, .85), _j(rng, .9)), _line(_j(rng, .1), _j(rng, .52), _j(rng, .88), _j(rng, .6)),
            _line(_j(rng, .5), 1, _j(rng, .42), _j(rng, .4)), _line(_j(rng, .2), _j(rng, .2), _j(rng, .4), _j(rng, .04), _j(rng, .8), _j(rng, .12))]


def f_fu(rng):                                # a tick over three small strokes (ふ)
    return [_line(_j(rng, .46), 1, _j(rng, .55), _j(rng, .88)), _line(_j(rng, .5), _j(rng, .7), _j(rng, .3), _j(rng, .46), _j(rng, .1), _j(rng, .2), _j(rng, .34), _j(rng, .08)),
            _line(_j(rng, .78), _j(rng, .64), _j(rng, .86), _j(rng, .5)), _line(_j(rng, .64), _j(rng, .36), _j(rng, .7), _j(rng, .12), _j(rng, .9), _j(rng, .2))]


def f_mu(rng):                                # a bar, a stem into a loop, and a tick (む も)
    x = _j(rng, .4)
    return [_line(_j(rng, .1), _j(rng, .8), _j(rng, .8), _j(rng, .84)), _line(x, 1, x - .02, _j(rng, .35), _j(rng, .3), _j(rng, .08), _j(rng, .62), _j(rng, .16), _j(rng, .84), _j(rng, .3), _j(rng, .7), _j(rng, .5), _j(rng, .3), _j(rng, .54)),
            _line(_j(rng, .84), _j(rng, .9), _j(rng, .92), _j(rng, .72))]


def f_ho(rng):                                # a stem, two bars and a looped stem (ほ)
    x = _j(rng, .64)
    return [_line(_j(rng, .16), 1, _j(rng, .18), _j(rng, .06)), _line(_j(rng, .3), _j(rng, .8), _j(rng, .52), _j(rng, .8)),
            _line(_j(rng, .4), _j(rng, .96), _j(rng, .92), _j(rng, .9)), _line(_j(rng, .4), _j(rng, .68), _j(rng, .92), _j(rng, .66)),
            _line(x, _j(rng, .62), x - .02, _j(rng, .2), _j(rng, .52), _j(rng, .02, .02), _j(rng, .4), _j(rng, .2), _j(rng, .88), _j(rng, .22))]


def f_nu(rng):                                # a slanted stroke crossed by a long looping one (ぬ)
    return [_line(_j(rng, .2), _j(rng, .96), _j(rng, .24), _j(rng, .55), _j(rng, .08), _j(rng, .12)),
            _line(_j(rng, .02, .02), _j(rng, .7), _j(rng, .5), _j(rng, .86), _j(rng, .66), _j(rng, .6), _j(rng, .4), _j(rng, .2), _j(rng, .62), _j(rng, .04),
                  _j(rng, .94), _j(rng, .3), _j(rng, .78), _j(rng, .56), _j(rng, .45), _j(rng, .4))]


def f_ne_loop(rng):                           # a stem, a crossing tick, and a stroke that loops back (ね)
    return [_line(_j(rng, .2), 1, _j(rng, .2), _j(rng, .1), _j(rng, .12), _j(rng, .02, .02)), _line(_j(rng, .04), _j(rng, .6), _j(rng, .4), _j(rng, .78)),
            _line(_j(rng, .36), _j(rng, .8), _j(rng, .66), _j(rng, .96), _j(rng, .62), _j(rng, .5), _j(rng, .48), _j(rng, .22), _j(rng, .82), _j(rng, .3), _j(rng, .62), _j(rng, .56), _j(rng, .88), _j(rng, .1))]


def f_sa(rng):                                # a bar, a bent stem with a crossing tick (さ)
    return [_line(_j(rng, .14), _j(rng, .7), _j(rng, .86), _j(rng, .76)), _line(_j(rng, .56), 1, _j(rng, .4), _j(rng, .52), _j(rng, .3), _j(rng, .12), _j(rng, .5), _j(rng, .02, .02), _j(rng, .86), _j(rng, .12)),
            _line(_j(rng, .36), _j(rng, .92), _j(rng, .62), _j(rng, .84))]


def f_ta(rng):                                # a bar, a hooked stem, and two short strokes (た)
    return [_line(_j(rng, .06), _j(rng, .82), _j(rng, .5), _j(rng, .86)), _line(_j(rng, .3), 1, _j(rng, .22), _j(rng, .4), _j(rng, .34), _j(rng, .06), _j(rng, .5), _j(rng, .22)),
            _line(_j(rng, .52), _j(rng, .52), _j(rng, .9), _j(rng, .56)), _line(_j(rng, .56), _j(rng, .2), _j(rng, .78), _j(rng, .08), _j(rng, .94), _j(rng, .14))]


def f_chi(rng):                               # a tick, a bar, and a long curving stroke (ち)
    return [_line(_j(rng, .36), 1, _j(rng, .68), _j(rng, .92)), _line(_j(rng, .1), _j(rng, .72), _j(rng, .9), _j(rng, .74)),
            _line(_j(rng, .5), _j(rng, .78), _j(rng, .26), _j(rng, .4), _j(rng, .5), _j(rng, .36), _j(rng, .82), _j(rng, .22), _j(rng, .66), _j(rng, .04), _j(rng, .4), _j(rng, .1))]


def f_se(rng):                                # a long bar, two stems and a hooked foot (せ)
    return [_line(_j(rng, .08), _j(rng, .64), _j(rng, .94), _j(rng, .68)), _line(_j(rng, .68), 1, _j(rng, .66), _j(rng, .3), _j(rng, .8), _j(rng, .1)),
            _line(_j(rng, .3), _j(rng, .94), _j(rng, .3), _j(rng, .36), _j(rng, .5), _j(rng, .12), _j(rng, .9), _j(rng, .16))]


FLOWING = {"loop_stem": f_loop_stem, "spiral": f_spiral, "ru": f_ru, "j": f_j, "ku": f_ku, "tick_arc": f_tick_arc,
           "bars_stem": f_bars_stem, "cross_loop": f_cross_loop, "sweep_dot": f_sweep_dot, "s": f_s, "two_curves": f_two_curves,
           "hook_line": f_hook_line, "wave": f_wave, "a": f_a, "na": f_na, "ki": f_ki, "fu": f_fu, "mu": f_mu,
            "ho": f_ho, "nu": f_nu, "ne_loop": f_ne_loop, "sa": f_sa, "ta": f_ta, "chi": f_chi, "se": f_se}

# ---- bowed archetypes (Elvish-like): a stem with round bows; strokes may reach below the baseline and above the x-height ----
def _f(*c):
    """Like _line, but the letter may run below the baseline (to -0.6) and above the x-height (to 1.6)."""
    return stroke([(round(min(max(c[i], .0), 1.0), 3), round(min(max(c[i + 1], -.6), 1.6), 3)) for i in range(0, len(c), 2)])


def _bow(rng, x, top, bot, w, left=False, closed=None):
    """A round bow hanging on the stem at x, from height `top` to height `bot`, reaching w sideways; it closes back to the stem
    unless it is left open (more than half are)."""
    from .families import _arc
    closed = (rng.random() < .3) if closed is None else closed
    sg = -1 if left else 1
    ym, ry = (top + bot) / 2, (top - bot) / 2
    pts = _arc(x, ym, w, ry, 90, -90 if closed else -52, 9)
    return stroke([(round(x + sg * (px - x), 3), py) for px, py in pts])


def b_single(rng):                            # a stem and one bow at its top, the stem reaching below
    x, bh, w = _j(rng, .15, .04), _j(rng, .55, .06), _j(rng, 1.0, .12)
    return [_f(x, 1, x, _j(rng, -.42, .1)), _bow(rng, x, 1, 1 - bh, w)]


def b_double(rng):                            # two bows stacked on the stem
    x, w = _j(rng, .15, .04), _j(rng, 1.0, .1)
    m = _j(rng, .52, .04)
    return [_f(x, 1, x, _j(rng, -.4, .1)), _bow(rng, x, 1, m, w), _bow(rng, x, m, _j(rng, .05, .05), w)]


def b_left(rng):                              # the same with the bow on the left of the stem
    x, bh, w = _j(rng, .85, .04), _j(rng, .55, .06), _j(rng, 1.0, .12)
    return [_f(x, 1, x, _j(rng, -.42, .1)), _bow(rng, x, 1, 1 - bh, w, True)]


def b_left_double(rng):
    x, w = _j(rng, .85, .04), _j(rng, 1.0, .1)
    m = _j(rng, .52, .04)
    return [_f(x, 1, x, _j(rng, -.4, .1)), _bow(rng, x, 1, m, w, True), _bow(rng, x, m, _j(rng, .05, .05), w, True)]


def b_raised(rng):                            # a bow at the foot of a stem that rises above it
    x, bh, w = _j(rng, .15, .04), _j(rng, .55, .06), _j(rng, 1.0, .12)
    return [_f(x, _j(rng, 1.4, .12), x, 0), _bow(rng, x, bh, 0, w)]


def b_raised_double(rng):
    x, w = _j(rng, .15, .04), _j(rng, 1.0, .1)
    return [_f(x, _j(rng, 1.4, .12), x, 0), _bow(rng, x, .55, .27, w), _bow(rng, x, .27, 0, w)]


def b_raised_left(rng):
    x, bh, w = _j(rng, .85, .04), _j(rng, .55, .06), _j(rng, 1.0, .12)
    return [_f(x, _j(rng, 1.4, .12), x, 0), _bow(rng, x, bh, 0, w, True)]


def b_short(rng):                             # a bow the full height of a short stem (no reach)
    x, w = _j(rng, .15, .04), _j(rng, 1.0, .12)
    return [_f(x, 1, x, 0), _bow(rng, x, 1, 0, w, rng.random() < .3)]


def b_tall(rng):                              # a long stem with a bow in the middle
    x, w = _j(rng, .15, .04), _j(rng, .8, .1)
    return [_f(x, _j(rng, 1.3, .1), x, _j(rng, -.35, .1)), _bow(rng, x, 1, .45, w)]


def c_ring(rng):                              # a ring, with a short stem for some (vala, a vowel carrier)
    cx, r = _j(rng, .5, .05), _j(rng, .32, .05)
    from .families import _arc
    s = [stroke(_arc(cx, .5, r, r * _j(rng, 1.0, .1), 0, 360, 14)[:-1], True)]
    if rng.random() < .4:
        s.append(_f(cx, .5 - r, cx, _j(rng, -.4, .1)))
    return s


def c_hook(rng):                              # a stem that curls to one side at its foot (an anna/romen-like curl)
    x = _j(rng, .35, .05)
    return [_f(x, 1.0, x - .02, _j(rng, .3, .06), _j(rng, .2, .05), _j(rng, -.02, .03), _j(rng, .55, .06), _j(rng, .0, .04), _j(rng, .8, .06), _j(rng, .22, .05))]


def c_curl(rng):                              # a curl like a 6 or a 9
    return [_f(_j(rng, .75, .05), _j(rng, .92, .04), _j(rng, .35, .05), _j(rng, 1.0, .04), _j(rng, .1, .04), _j(rng, .6, .05), _j(rng, .4, .06), _j(rng, .22, .04),
               _j(rng, .8, .06), _j(rng, .46, .05), _j(rng, .5, .06), _j(rng, .66, .04))]


def c_lambda(rng):                            # two strokes that meet and part (a lambda)
    mx, my = _j(rng, .5, .04), _j(rng, .55, .05)
    return [_f(_j(rng, .12, .04), 1, mx, my, _j(rng, .8, .05), _j(rng, -.02, .03)), _f(_j(rng, .12, .04), 0, mx, my)]


def c_arch(rng):                              # an arch on a short stem (a cup turned over), reaching below
    x0, x1 = _j(rng, .15, .04), _j(rng, .85, .04)
    from .families import _arc
    arch = _arc((x0 + x1) / 2, .6, (x1 - x0) / 2, .4, 180, 0, 10)
    return [stroke([(x0, _j(rng, .0, .03))] + [(round(px, 3), round(py, 3)) for px, py in arch] + [(x1, _j(rng, -.35, .1))])]


BOWED = {"single": b_single, "double": b_double, "left": b_left, "left_double": b_left_double, "raised": b_raised,
         "raised_double": b_raised_double, "raised_left": b_raised_left, "short": b_short, "tall": b_tall,
         "ring": c_ring, "hook": c_hook, "curl": c_curl, "lambda": c_lambda, "arch": c_arch}
BOWED_WEIGHT = {"single": 3.0, "double": 3.0, "left": 2.0, "left_double": 2.0, "raised": 2.0, "raised_double": 2.0, "raised_left": 1.0,
                "short": 1.0, "tall": 1.0, "ring": 0.6, "hook": 0.6, "curl": 0.6, "lambda": 0.4, "arch": 0.5}


ARCHETYPES = {"angular": ANGULAR, "flowing": FLOWING, "bowed": BOWED}


def archetypes(hand: str) -> list:
    return list(ARCHETYPES[hand])


_STROKES: dict = {}


LOOPY = {"ring", "curl", "spiral", "ru", "s", "cross_loop", "a", "na", "mu", "loop_stem", "ne_loop", "nu"}      # archetypes that hold a closed loop


def weights(hand: str, complexity: float, loops: float = 0.4) -> dict:
    """How much each archetype is liked at a complexity: ornate scripts (low complexity) lean on archetypes with more strokes,
    bold ones on the plainest. Strokes per archetype are counted once, from a few draws."""
    import random
    if hand not in _STROKES:
        _STROKES[hand] = {n: sum(len(f(random.Random(k))) for k in range(8)) / 8 for n, f in ARCHETYPES[hand].items()}
    if hand == "bowed":                       # the bowed hand has its own fixed preferences (most letters are a stem with bows)
        return dict(BOWED_WEIGHT)
    power = (0.5 - complexity) * 4            # complexity .5 is neutral; .25 favours busy letters; .75 favours plain ones
    return {n: c ** power * ((0.3 + 2.2 * loops) if n in LOOPY else 1.0) for n, c in _STROKES[hand].items()}


EXTRA_TICK = {"angular": 0.1, "flowing": 0.25, "bowed": 0.0}     # how often a letter gets a small detached tick (ツ ミ シ, こ う); the basic katakana are mostly one piece


CROSS = {"angular": 0.25, "flowing": 0.6, "bowed": 0.0}           # how often a short stroke crosses another (キ ホ ま き): more junctions and ends


def _cross(rng, strokes):
    """A short stroke that crosses one of the letter's strokes about its middle."""
    from .graph import points
    body = [s for s in strokes if not s.get("dot")]
    pts = points([rng.choice(body)], step=0.05)
    if len(pts) < 5:
        return []
    i = rng.randrange(2, len(pts) - 2)
    (x0, y0), (x1, y1) = pts[i - 2], pts[i + 2]
    a = math.atan2(y1 - y0, x1 - x0) + math.radians(rng.choice([-1, 1]) * rng.uniform(55, 90))
    x, y = pts[i]
    r = rng.uniform(.13, .2)
    ends = [(x - r * math.cos(a), y - r * math.sin(a)), (x + r * math.cos(a), y + r * math.sin(a))]
    if any(not (.02 <= u <= .98 and .02 <= v <= .98) for u, v in ends):
        return []
    return [_line(ends[0][0], ends[0][1], ends[1][0], ends[1][1])]


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


JOIN = {"angular": 0.1, "flowing": 0.6, "bowed": 0.0}          # how often a stroke is drawn on to another, making a T-junction (た な ほ, キ ホ): real kana touch more than ours did


def _join(rng, strokes):
    """Move the end of one stroke onto the nearest stroke (when one lies close) so the two meet in a T-junction."""
    from .graph import points
    order = list(range(len(strokes)))
    rng.shuffle(order)
    for i in order:
        s = strokes[i]
        if s.get("dot") or len(s["p"]) < 2:
            continue
        for end in (0, -1) if rng.random() < .5 else (-1, 0):
            ex, ey = s["p"][end]
            best = None
            for j, o in enumerate(strokes):
                if j == i or o.get("dot"):
                    continue
                for (u, v) in points([o], step=0.04):
                    d = math.hypot(ex - u, ey - v)
                    if 0.02 < d <= 0.24 and (best is None or d < best[0]):
                        best = (d, u, v)
            if best:
                p = [list(q) for q in s["p"]]
                p[end] = [round(best[1], 3), round(best[2], 3)]
                return [dict(strokes[k], p=p) if k == i else strokes[k] for k in range(len(strokes))]
    return strokes


def make(rng, hand: str, name: str | None = None, mirror_ok: bool = True, extra: float | None = None, cross: float | None = None, join: float | None = None):
    """One letter of the given hand: (archetype name, strokes in the unit box). The archetype is jittered every time; a
    mirrored copy is used now and then, so one archetype stretches over many letters."""
    table = ARCHETYPES[hand]
    name = name if name in table else rng.choice(sorted(table))
    strokes = table[name](rng)
    if extra is None:
        extra = EXTRA_TICK[hand]
    if rng.random() < extra and len(strokes) < 5:
        strokes = strokes + _tick(rng, hand, strokes)
    if rng.random() < (CROSS[hand] if cross is None else cross) and len(strokes) < 6:
        strokes = strokes + _cross(rng, strokes)
    p = JOIN[hand] if join is None else join
    for _ in range(2):                              # up to two strokes are drawn on to others
        if rng.random() < p:
            strokes = _join(rng, strokes)
            p *= 0.6
    if mirror_ok and hand != "bowed" and rng.random() < .2:
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


FILL = {"bowed": (0.7, 0.28)}                     # the least height and width of a letter, where the hand differs from the default (0.78, 0.55)


def fills(strokes, min_h=0.78, min_w=0.55) -> bool:
    """A kana fills its square: tall enough and wide enough (a lone short tick or a bar low in the box is not a letter)."""
    from .geometry import bbox
    x0, y0, x1, y1 = bbox(strokes)
    return (y1 - y0) >= min_h and (x1 - x0) >= min_w


def voicing_marks(hand: str) -> list:
    """The marks that stand for voicing and breathing: two short ticks (dakuten) and a small ring (handakuten), drawn in the hand's
    style. Part records for marks.py: each sits above and to the right of its letter, clear of it."""
    k = "s" if hand == "angular" else "m"
    ticks = [dict(stroke([(.0, 1.0), (.22, .0)]), k=k), dict(stroke([(.62, 1.0), (.84, .0)]), k=k)]
    ring = [dict(stroke([(math.cos(a) * .5 + .5, math.sin(a) * .5 + .5) for a in (i * math.pi / 4 for i in range(8))], closed=True), k=k)]
    return [{"kind": "dakuten", "strokes": ticks, "w": .26, "h": .26, "box": "unit", "touch": False, "valign": "top"},
            {"kind": "handakuten", "strokes": ring, "w": .17, "h": .17, "box": "unit", "touch": False, "valign": "top"}]
