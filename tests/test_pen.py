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
                    assert len(s["p"]) >= 2 or s.get("dot")             # a dot (the Bengali nukta) is a single point
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


@pytest.mark.parametrize("pid,frame,kind", [("devanagari", "headline", "m"), ("bengali", "bengali", "s"), ("tamil", "foot", None)])
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


def _bar_pins(share):
    return dict(BY_ID["bengali"]["pins"], topline_share=share)


def test_topline_share_dial():
    assert resolve(1, {})["topline_share"] == 1.0
    assert resolve(1, {"topline_share": 0.4})["topline_share"] == 0.4
    with pytest.raises(ValueError):
        resolve(1, {"topline_share": 1.5})


def test_headless_letters_are_shorter_and_the_share_follows_the_dial():
    from conlang_forge.script.layout import _has_bar

    def cons(share):
        s = generate(3, _bar_pins(share))
        return [l for l in s["letters"] if l["role"] == "consonant" and l["family"].startswith("stroke:")]

    full, half = cons(1.0), cons(0.5)
    assert all(_has_bar(l["strokes"]) for l in full)
    share = sum(_has_bar(l["strokes"]) for l in half) / len(half)
    assert 0.25 <= share <= 0.8
    for l in half:
        top = max(y for st in l["strokes"] if not st.get("dot") for _, y in st["p"])
        if not _has_bar(l["strokes"]):
            assert top < 0.93


def test_pen_headless_scales_the_top_down():
    sts = [stroke([(0, 1), (1, 1)]), stroke([(.5, 1), (.5, -.2)])]
    out = pen.headless(random.Random(1), sts)
    assert max(y for st in out for _, y in st["p"]) < 0.9
    assert min(y for st in out for _, y in st["p"]) == -.2          # parts below the line are kept


def test_pen_signs_by_slot():
    for slot in ("left", "right", "above", "below"):
        for style in STYLES:
            kind, sts = pen.sign_strokes(random.Random(5), slot, style)
            assert kind.startswith("pen_") and sts
            assert all(-0.01 <= x <= 1.01 and -0.01 <= y <= 1.01 for st in sts for x, y in st["p"])


def test_pen_marks_and_their_long_form():
    from conlang_forge.script import marks
    part = marks.make_part(random.Random(2), "right", style="mixed", shape="pen")
    assert part["kind"].startswith("pen_")
    long = marks.grow_part(random.Random(2), part, "right")
    assert long["kind"].endswith("+") and len(long["strokes"]) == len(part["strokes"]) + 1
    assert resolve(1, {"mark_shape": "pen"})["mark_shape"] == "pen"


# ---- pen v2: a fixed vocabulary, guide lines and one upright axis ----------------------------------------------------------
def test_stem_letters_have_exactly_upright_stems_that_start_on_the_top_line():
    for name in pen.STEM:
        for style in STYLES:
            for seed in range(10):
                sts = pen.ARCHETYPES[name](random.Random(seed), style)
                stems = [st for st in sts if st["p"][0][1] == pen.TOP and st["p"][0][0] == st["p"][1][0] and st["p"][1][1] < pen.TOP]
                assert stems, (name, style)                         # a stem leaves the top line exactly upright (it may end in a hook)


def test_pen_values_come_from_the_vocabulary():
    """Arm lengths, radii and guide heights are a few fixed values, so two letters never differ by a hair."""
    ys = set()
    for name in pen.STEM:
        for seed in range(20):
            for st in pen.ARCHETYPES[name](random.Random(seed), "sharp"):
                ys.update(round(y, 2) for _, y in st["p"])
    assert min(ys) >= -0.12 and max(ys) <= 1.02             # nothing leaves the box vertically
    assert len({round(y / 0.05) for y in ys}) <= 34         # the guide lines plus what a few fixed sizes add to them
    assert {pen.TOP, pen.BASE} <= ys


def test_tamil_atoms_are_in_the_free_frame():
    assert {"a", "bell", "v_bell", "h_bell"} <= set(pen.FREE)
    sts = pen.ARCHETYPES["a"](random.Random(1), "smooth")
    assert any(len(st["p"]) == 2 and st["p"][0][0] == st["p"][1][0] for st in sts)          # the full-height vertical


def test_bowed_stems_are_upright_in_two_columns():
    from conlang_forge.script import kana
    cols = set()
    for name in ("single", "double", "left", "left_double", "raised", "raised_double", "raised_left", "short", "tall"):
        for seed in range(8):
            stem = kana.BOWED[name](random.Random(seed))[0]
            assert stem["p"][0][0] == stem["p"][1][0]
            cols.add(stem["p"][0][0])
    assert cols <= {kana.STEM_L, kana.STEM_R}


def test_slant_is_a_drawing_style_applied_when_drawn():
    from conlang_forge.script.render import strokes_svg
    st = [stroke([(0.5, 0), (0.5, 1)])]
    flat, lean = strokes_svg(st, 0.0), strokes_svg(st, 0.0, slant=20)
    assert flat != lean and "M50.0 0.0" in flat
    assert strokes_svg(st, 0.0, slant=0) == flat
    assert resolve(1, {"slant": 12})["slant"] == 12 and resolve(1, {})["slant"] == 0
    with pytest.raises(ValueError):
        resolve(1, {"slant": 40})
    base = generate(2, BY_ID["elvish"]["pins"])
    assert generate(2, dict(BY_ID["elvish"]["pins"], slant=10))["letters"] == base["letters"]          # the letters themselves do not change
