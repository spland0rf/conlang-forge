"""The bubbly figures made of several circles."""
import math

from conlang_forge.script.families import FORMS
from conlang_forge.script import forms


def _centres(strokes):
    out = []
    for s in strokes:
        xs, ys = [p[0] for p in s["p"]], [p[1] for p in s["p"]]
        out.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (max(xs) - min(xs)) / 2))
    return out


def test_triangle_of_rings_is_three_equal_touching_circles_inside_the_box():
    build, _ = FORMS["bubbly"]["ring3t"]
    strokes = build()
    assert len(strokes) == 3
    c = _centres(strokes)
    assert len({round(r, 2) for _, _, r in c}) == 1
    for x, y, r in c:
        assert -0.001 <= x - r and x + r <= 1.001 and -0.001 <= y - r and y + r <= 1.001
    ys = sorted(y for _, y, _ in c)
    assert ys[0] == ys[1] and ys[2] > ys[1]               # two below, one above
    low = [p for p in c if p[1] == ys[0]]
    top = c[[p[1] for p in c].index(ys[2])]
    for p in low:
        assert abs(math.dist(p[:2], top[:2]) - 2 * p[2]) < 0.01          # the top circle touches each lower one
    assert 0 < math.dist(low[0][:2], low[1][:2]) - 2 * low[0][2] < 0.12   # the lower pair stays a hair apart


def test_every_orientation_is_a_usable_figure():
    from conlang_forge.script.shapes import apply_variant, usable
    core = FORMS["bubbly"]["ring3t"][0]()
    for op in ("plain", "rot90", "rot180", "flip_y"):
        assert usable(apply_variant(core, op, False)), op          # no enclosed fourth loop to make it "too busy"


def test_it_can_be_chosen_by_name():
    assert forms.builder("three rings in a triangle") is FORMS["bubbly"]["ring3t"][0]
