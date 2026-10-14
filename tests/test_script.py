"""The writing-system generator: determinism, pins, connectivity, distinctness, abugida signs, layout, SVG."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pytest  # noqa: E402

from conlang_forge.script import compose, generate, sample_words, set_text, sheet_svg, text_svg  # noqa: E402
from conlang_forge.script.geometry import bbox  # noqa: E402
from conlang_forge.script.graph import analyse, distance, points  # noqa: E402
from conlang_forge.script.spec import resolve  # noqa: E402
import importlib  # noqa: E402
norm_points = importlib.import_module("conlang_forge.script.generate").norm_points


def test_same_seed_same_script_and_pins_change_only_what_they_touch():
    a, b = generate(5), generate(5)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert generate(5)["letters"] != generate(6)["letters"]
    pinned = generate(5, {"kind": "alphabet", "roundness": 0.3})
    assert pinned["spec"]["kind"] == "alphabet" and pinned["spec"]["roundness"] == 0.3
    # roundness is style only: the same seed with another roundness has identical strokes
    other = generate(5, {"kind": "alphabet", "roundness": 1.0})
    plain = lambda sc: [l["strokes"] for l in sc["letters"] if not l["from"]]
    assert plain(other) == plain(pinned)


def test_bad_pins_are_refused():
    for pins in ({"nope": 1}, {"kind": "runic"}, {"roundness": 3}, {"consonants": "many"}):
        with pytest.raises(ValueError):
            resolve(1, pins)


def test_every_plain_letter_is_one_connected_piece_and_letters_are_distinct():
    for seed in range(6):
        for kind in ("alphabet", "abjad", "abugida"):
            s = generate(seed, {"kind": kind})
            ids = [l["id"] for l in s["letters"]]
            assert len(ids) == len(set(ids))
            related = {frozenset((l["id"], l["from"])) for l in s["letters"] if l["from"]}
            pts = {l["id"]: norm_points(l, 0.05) for l in s["letters"]}     # width differences do not make letters distinct
            for l in s["letters"]:
                assert analyse(l["strokes"])["parts"] == 1 or l["mark"], (seed, kind, l["id"])
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    if frozenset((a, b)) not in related and not (s["letters"][i]["mark"] or s["letters"][ids.index(b)]["mark"]):
                        assert distance(pts[a], pts[b]) > 0.04, (seed, kind, a, b)


def test_abugida_has_signs_with_long_short_rule_and_virama():
    s = generate(3, {"kind": "abugida", "vowels": 9})
    signs = {x["id"]: x for x in s["signs"]}
    assert len(signs) == 9 and s["virama"]["parts"]
    longs = [x for x in s["signs"] if x["long_of"]]
    assert longs and all(x["long_of"] in signs for x in longs)
    base = s["letters"][0]["id"]
    plain, _ = compose(s, base)
    for x in s["signs"]:
        strokes, w = compose(s, base, x["id"])
        assert len(strokes) > len(plain) and w >= s["letters"][0]["width"]
    # a sign that touches its letter keeps the syllable in one piece
    touching = [x for x in s["signs"] if all(p["touch"] for p in x["parts"].values())]
    for x in touching:
        assert analyse(compose(s, base, x["id"])[0])["parts"] == 1


def test_topline_and_joined_scripts_carry_the_device():
    s = generate(4, {"kind": "alphabet", "topline": "bar", "joining": "none"})
    for l in s["letters"]:
        assert any(len(st["p"]) == 2 and st["p"][0][1] == 1.0 == st["p"][1][1] for st in l["strokes"])
    j = generate(4, {"kind": "alphabet", "joining": "baseline", "topline": "none"})
    for l in j["letters"]:
        assert analyse(l["strokes"])["parts"] == 1


def test_right_to_left_text_places_first_letter_at_the_right_without_mirroring():
    s = generate(7, {"kind": "alphabet", "direction": "rtl", "topline": "none"})
    first = s["letters"][0]["id"]
    ltr = generate(7, {"kind": "alphabet", "direction": "ltr", "topline": "none"})
    words = [[("letter", first), ("letter", s["letters"][1]["id"])]]
    r, w = set_text(s, words, None)
    l, w2 = set_text(ltr, words, None)
    assert abs(w - w2) < 1e-6 and bbox(r)[2] > w - 0.5 and bbox(l)[0] < 0.5
    assert sample_words(s, 3) == sample_words(s, 3)


def test_svg_output_is_well_formed():
    s = generate(2)
    ET.fromstring(sheet_svg(s))
    ET.fromstring(text_svg(s))
    json.dumps(s)


def test_user_supplied_phoneme_inventory_is_used():
    s = generate(9, {"kind": "alphabet"}, {"consonants": ["p", "t", "k", "s", "m", "n"], "vowels": ["a", "i", "u"]})
    assert [l["id"] for l in s["letters"]] == ["p", "t", "k", "s", "m", "n", "a", "i", "u"]


def test_default_scripts_are_drawn_with_smooth_corners():
    from conlang_forge.script.geometry import flatten, stroke
    from conlang_forge.script.render import strokes_svg
    corner = stroke([(0, 0), (0, 1), (1, 1)])
    assert len(flatten(corner, 0.0)) == 3 and len(flatten(corner, 1.0)) > 8
    assert "Q" in strokes_svg([corner], 1.0) and "Q" not in strokes_svg([corner], 0.0)
    smooth = sum(1 for sd in range(40) if generate(sd)["spec"]["roundness"] >= 0.7)
    assert smooth >= 30


def test_each_stroke_is_sharp_smooth_blocky_or_hybrid_never_a_mix():
    from conlang_forge.script.motifs import classify
    seen = set()
    for seed in range(8):
        s = generate(seed, {"kind": "alphabet", "corner_style": "mixed", "topline": "none", "joining": "none"})
        for l in s["letters"]:
            for st in l["strokes"]:
                if st.get("dot") or len(st["p"]) < 2:
                    continue
                k = st.get("k")
                assert k in ("s", "m", "b", "h"), (seed, l["id"], k)
                seen.add(k)
                if k == "b":                       # blocky strokes have right angles only
                    c = classify([st])
                    assert c["angular"] == 0 and c["gentle"] == 0
    assert {"s", "m"} <= seen                       # a mixed script really uses several treatments
    for style, want in (("smooth", {"m"}), ("sharp", {"s"}), ("blocky", {"b"})):
        s = generate(3, {"kind": "alphabet", "corner_style": style, "topline": "none", "joining": "none"})
        assert {st["k"] for l in s["letters"] for st in l["strokes"] if "k" in st} == want


def test_characteristic_shapes_recur_across_related_letters():
    s = generate(3, {"kind": "alphabet", "motif_count": 4, "motif_share": 1.0, "topline": "none", "joining": "none"})
    assert 1 <= len(s["motifs"]) <= 6
    built = [l for l in s["letters"] if l["motif"]]
    assert len(built) >= 6
    from collections import Counter
    by_shape = Counter(l["motif"] for l in built)
    assert max(by_shape.values()) >= 3                       # a shape really recurs
    groups = {g: m["shape"] for m in s["motifs"] for g in m["classes"]}
    from conlang_forge.script.shapes import GROUP_OF
    for l in built:
        assert groups[GROUP_OF[l["id"]]] == l["motif"]        # a letter uses its sound group's shape
    vowel_shape = groups["vowel"]
    assert all(l["motif"] != vowel_shape for l in built if GROUP_OF[l["id"]] != "vowel")   # rule D
    for shape in set(by_shape):
        variants = [l["variant"] for l in built if l["motif"] == shape]
        assert len(variants) == len(set(variants))            # variants of one shape are all different
    off = generate(3, {"kind": "alphabet", "motif_count": 0})
    assert not off["motifs"] and not any(l["motif"] for l in off["letters"])
    assert generate(3, {"motif_count": 4}) == generate(3, {"motif_count": 4})


def test_most_letters_share_one_frame_with_their_weight_near_the_middle():
    from conlang_forge.script.generate import _balance
    tall = balanced = total = 0
    for seed in range(6):
        s = generate(seed, {"kind": "alphabet", "topline": "none", "joining": "none"})
        tol = s["spec"]["frame_tolerance"]
        for l in s["letters"]:
            if l["from"] or l["motif"]:
                continue
            total += 1
            tall += l["band"] != "x"
            y0, y1 = {"x": (0, 1), "asc": (0, 1.55), "desc": (-0.5, 1.0)}[l["band"]]
            core = [st for st in l["strokes"]]
            balanced += _balance(core, l["width"], y0, y1) <= tol * 1.7
    assert tall / total < 0.3 and balanced / total > 0.75, (tall, balanced, total)


def test_partial_joining_breaks_the_chain_at_non_joining_letters():
    s = generate(7, {"kind": "alphabet", "joining": "partial", "topline": "none", "direction": "ltr"})
    kinds = {l["joins"] for l in s["letters"]}
    assert kinds == {"both", "prev", "none"}
    for l in s["letters"]:
        stubs = {st["stub"] for st in l["strokes"] if "stub" in st}
        assert (l["joins"] == "none") <= (not stubs)
        assert (l["joins"] == "both") <= (stubs <= {"L", "R"})
        if l["joins"] == "prev":
            assert "R" not in stubs                        # left-to-right: only the side facing the previous letter
    full = generate(7, {"kind": "alphabet", "joining": "baseline", "topline": "none"})
    assert all(l["joins"] == "both" for l in full["letters"])
    assert all(l["joins"] == "none" for l in generate(7, {"kind": "alphabet", "joining": "none"})["letters"])


def test_bodies_sit_in_the_main_frame_and_ascenders_reach_the_lines():
    """Rules A and B: a letter's body is inside the main frame; an ascender or descender is a stroke that reaches the
    ascender or descender line, not a stretched body."""
    for seed in range(8):
        for kind in ("alphabet", "abjad"):
            s = generate(seed, {"kind": kind})
            for l in s["letters"]:
                if l["mark"]:
                    continue
                ys = [p[1] for p in points([x for x in l["strokes"] if "stub" not in x], step=0.04)]
                band = l["band"]
                lo, hi = min(ys), max(ys)
                assert (hi <= 1.1) or "asc" in band, (seed, l["id"], band, hi)
                assert (lo >= -0.1) or "desc" in band, (seed, l["id"], band, lo)
                if "asc" in band:
                    assert abs(hi - 1.55) < 0.03, (seed, l["id"], band, hi)
                if "desc" in band:
                    assert abs(lo + 0.5) < 0.03, (seed, l["id"], band, lo)


def test_similar_sounds_get_similar_shapes():
    """Rule D: a consonant's most similar letter is usually another consonant of its own manner, well above chance."""
    rows = [generate(seed, {"kind": "alphabet"})["metrics"]["sound_coherence"] for seed in range(1, 9)]
    rows = [r for r in rows if r["nearest_same_manner"] is not None]
    assert sum(r["nearest_same_manner"] for r in rows) / len(rows) > 0.38
    assert sum(r["nearest_same_kind"] for r in rows) / len(rows) > 0.7
    assert sum(r["manner_within"] < r["manner_across"] for r in rows) >= len(rows) * 0.5


def test_complexity_dial_orders_stroke_counts_and_bans_dots_when_bold():
    def strokes(c):
        counts, dots = [], 0
        for seed in range(1, 6):
            s = generate(seed, {"kind": "alphabet", "complexity": c, "mark_share": 0.0})
            for l in s["letters"]:
                counts.append(len([x for x in l["strokes"] if "stub" not in x]))
                dots += sum(1 for x in l["strokes"] if x.get("dot"))
        return counts, dots
    ornate, bold = strokes(0.05), strokes(0.9)
    mean = lambda v: sum(v) / len(v)
    assert mean(ornate[0]) >= mean(bold[0]) + 1.0
    assert max(bold[0]) <= 4 and bold[1] == 0
    with pytest.raises(ValueError):
        resolve(1, {"complexity": 1.5})


def test_style_families_choose_the_figures_and_letters_can_be_turned_or_mirrored():
    for fam in ("spikey", "curvy", "bubbly", "boxy"):
        s = generate(2, {"kind": "alphabet", "family": fam, "family2": "none"})
        assert s["spec"]["family"] == fam
        made = [l["motif"] for l in s["letters"] if l["motif"]]
        assert made and all(m.startswith(fam + ".") for m in made)
    with pytest.raises(ValueError):
        resolve(1, {"family": "wobbly"})
    assert generate(5, {"corner_style": "blocky"})["spec"]["family"] == "boxy"
    seen = set()
    for seed in range(1, 7):
        s = generate(seed, {"kind": "alphabet", "mirror_share": 0.5, "topline": "none", "joining": "none"})
        seen |= {l["relation"] for l in s["letters"] if l["relation"]}
    assert len(seen & {"flip_x", "flip_y", "rot90", "rot270", "rot180"}) >= 3


def test_a_feature_gets_the_same_mark_on_every_letter_that_has_it():
    found = 0
    for seed in range(1, 9):
        s = generate(seed, {"kind": "alphabet", "mark_share": 0.4, "mirror_share": 0.1, "topline": "none", "joining": "none"})
        by_feature = {}
        for l in s["letters"]:
            if l["mark"] and l["feature"]:
                by_feature.setdefault(l["feature"], set()).add(l["mark"])
        for feat, marks in by_feature.items():
            assert len(marks) == 1, (seed, feat, marks)
            found += 1
    assert found >= 3
