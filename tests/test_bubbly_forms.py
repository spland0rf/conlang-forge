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
    for i in range(3):
        for j in range(i + 1, 3):
            d = math.dist(c[i][:2], c[j][:2])
            assert abs(d - 2 * c[i][2]) < 0.03           # each pair touches without overlapping
    ys = sorted(y for _, y, _ in c)
    assert ys[0] == ys[1] and ys[2] > ys[1]               # two below, one above


def test_it_can_be_chosen_by_name():
    assert forms.builder("three rings in a triangle") is FORMS["bubbly"]["ring3t"][0]
