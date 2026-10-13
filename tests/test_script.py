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
            pts = {l["id"]: points(l["strokes"], step=0.08) for l in s["letters"]}
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
