"""The pen hand of the stroke family: letters drawn as paths (Devanagari, Bengali, Tamil-like)."""
import math
import random

import pytest

from conlang_forge.script import kana, pen
from conlang_forge.script.describe import keywords
from conlang_forge.script.generate import generate
from conlang_forge.script.geometry import stroke
from conlang_forge.script.graph import analyse
from conlang_forge.script.presets import BY_ID
from conlang_forge.script.spec import resolve

STYLES = ("smooth", "sharp", "mixed")


def _dist_to_polyline(pt, pts):
    best = 9.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((pt[0] - x0) * dx + (pt[1] - y0) * dy) / L2))
        best = min(best, math.dist(pt, (x0 + t * dx, y0 + t * dy)))
    return best


def test_every_archetype_stays_in_the_box_in_every_style():
    for name, build in pen.ARCHETYPES.items():
        for style in STYLES:
            for seed in range(12):
                strokes = build(random.Random(seed), style)
                assert strokes and len(strokes) <= 6, (name, style, seed)
                for s in strokes:
                    assert len(s["p"]) >= 2
                    for x, y in s["p"]:
                        assert 0 <= x <= 1 and -0.6 <= y <= 1.6, (name, style, seed)


def test_style_sets_the_stroke_kind():
    for name, build in pen.ARCHETYPES.items():
        assert {s["k"] for s in build(random.Random(1), "smooth")} == {"m"} or name in {"s_curve"}   # loops are drawn round in every style
        sharp = {s["k"] for _ in range(1) for s in build(random.Random(2), "sharp")}
        assert sharp <= {"s", "m"}
    kinds = {s["k"] for seed in range(30) for s in pen.ARCHETYPES["arm_bowl"](random.Random(seed), "mixed")}
    assert kinds == {"s", "m"}


def test_a_stroke_can_start_on_the_middle_of_an_earlier_one_and_end_on_another():
    p = pen.Pen(random.Random(0), "smooth")
    a = p.begin(.7, 1.0, -90)
    p.line(1.0)
    x, y, h = p.at(a, .5)
    assert abs(x - .7) < 1e-9 and abs(y - .5) < 1e-9 and abs(h + 90) < 1e-6          # the middle of the stem, heading down
    p.begin(x, y, 180)
    p.line(.3)
    p.to(.7, .2)                                                                    # lands back on the stem
    s = p.strokes
    assert _dist_to_polyline(s[1]["p"][0], s[0]["p"]) < 1e-9
    assert _dist_to_polyline(s[1]["p"][-1], s[0]["p"]) < 1e-9
    assert analyse(p.done())["parts"] == 1


def test_an_arc_carries_on_in_the_direction_the_pen_was_going():
    p = pen.Pen(random.Random(0), "smooth")
    p.begin(.1, .5, 0)
    p.line(.2)
    p.arc(90, .2)
    (x0, y0), (x1, y1) = p.strokes[0]["p"][-3], p.strokes[0]["p"][-2]
    pts = p.strokes[0]["p"]
    first = math.degrees(math.atan2(pts[2][1] - pts[1][1], pts[2][0] - pts[1][0]))       # the first step of the arc leaves almost along the line (east)
    assert abs(first) < 30
    assert abs(p.h - 90) < 1e-9                                                          # and it ends heading north


def test_stem_letters_hang_from_the_top_and_read_as_one_piece():
    one = 0
    total = 0
    for name in pen.STEM:
        for seed in range(15):
            st = pen.STEM[name](random.Random(seed), "smooth")
            top = max(y for s in st for _, y in s["p"])
            assert top >= 0.99, name                                                     # the stem starts at the top bar
            one += kana.reads_as_one(st)
            total += 1
    assert one / total > 0.9


def test_free_letters_fill_the_box_and_some_hang_below_the_line():
    lows, heights = [], []
    for name in pen.FREE:
        for seed in range(15):
            st = pen.FREE[name](random.Random(seed), "mixed")
            ys = [y for s in st for _, y in s["p"]]
            lows.append(min(ys))
            heights.append(max(ys) - min(ys))
    assert any(l < -0.1 for l in lows) and any(l >= -0.01 for l in lows)
    assert sorted(heights)[len(heights) // 2] > 0.75


def test_frames_pick_their_archetypes():
    assert set(pen.archetypes("stem")) == set(pen.STEM) and set(pen.archetypes("free")) == set(pen.FREE)
    assert set(kana.archetypes("pen", "stem")) == set(pen.STEM)
    w = kana.weights("pen", 0.5, 0.0)
    assert set(w) >= set(pen.ARCHETYPES) and all(v > 0 for v in w.values())
    assert w["arm_loop"] < kana.weights("pen", 0.5, 1.0)["arm_loop"]                     # loops are liked more when the loops dial is high


def test_dials():
    spec = resolve(1, {"family": "stroke", "stroke_hand": "pen", "topline": "bar"})
    assert spec["stroke_hand"] == "pen" and spec["pen_frame"] == "stem"                  # a top bar means a stem frame
    assert resolve(1, {"family": "stroke", "stroke_hand": "pen", "pen_frame": "free"})["pen_frame"] == "free"
    with pytest.raises(ValueError):
        resolve(1, {"pen_frame": "sideways"})


@pytest.mark.parametrize("pid,frame,kind", [("devanagari", "stem", "m"), ("bengali", "stem", "s"), ("tamil", "free", None)])
def test_the_presets_are_pen_scripts(pid, frame, kind):
    s = generate(2, BY_ID[pid]["pins"])
    assert s["spec"]["stroke_hand"] == "pen" and s["spec"]["pen_frame"] == frame
    letters = [l for l in s["letters"] if l["role"] == "consonant" and l["family"].startswith("stroke:")]
    assert len(letters) >= 0.6 * s["spec"]["consonants"]            # the rest are twins and marked forms of these
    assert {l["family"].split(":")[1] for l in letters} <= set(pen.ARCHETYPES)
    if kind:
        assert {st.get("k", "m") for l in letters for st in l["strokes"] if not st.get("stub")} - {"s", "m"} == set()
    assert generate(2, BY_ID[pid]["pins"])["letters"] == s["letters"]                    # deterministic


def test_description_words_choose_the_pen_hand():
    got = {(i["key"], i["value"]) for i in keywords("letters like Devanagari, a stem with arms hanging from a top bar")}
    assert ("stroke_hand", "pen") in got and ("pen_frame", "stem") in got and ("family", "stroke") in got
    got = {(i["key"], i["value"]) for i in keywords("like Tamil")}
    assert ("stroke_hand", "pen") in got and ("pen_frame", "free") in got
