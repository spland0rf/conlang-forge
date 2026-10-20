"""Choosing the characteristic shape of a sound class ("vowels are rings", "stops are triangles")."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from conlang_forge.script import describe as D  # noqa: E402
from conlang_forge.script.forms import SHAPE_DIALS, SHAPE_NAMES, builder, chosen, key  # noqa: E402
from conlang_forge.script.generate import generate  # noqa: E402
from conlang_forge.script.shapes import GROUP_OF  # noqa: E402
from conlang_forge.script.spec import DIALS, resolve  # noqa: E402


def _wearing(script, group, shape):
    return sum(1 for l in script["letters"] if GROUP_OF.get(l["id"]) == group and l.get("motif") == key(shape))


def test_vocabulary_builds_every_shape():
    assert len(SHAPE_NAMES) == len(set(SHAPE_NAMES)) >= 30
    for n in SHAPE_NAMES:
        assert builder(n)(), n
    assert set(SHAPE_DIALS.values()) <= set(DIALS)


def test_defaults_are_auto_and_change_nothing():
    spec = resolve(5, {})
    assert all(spec[d] == "auto" for d in SHAPE_DIALS.values()) and chosen(spec) == {}
    a = generate(5, {"kind": "alphabet"})
    b = generate(5, {"kind": "alphabet", "vowel_shape": "auto", "nasal_shape": "auto"})
    assert [(l["id"], l["strokes"]) for l in a["letters"]] == [(l["id"], l["strokes"]) for l in b["letters"]]
    assert "shape_report" not in a


def test_chosen_shapes_are_worn_by_their_class():
    pins = {"kind": "alphabet", "vowel_shape": "ring", "plosive_shape": "triangle", "motif_share": 1.0}
    for seed, corners in ((7, "mixed"), (11, "smooth")):
        s = generate(seed, dict(pins))
        assert s["spec"]["corner_style"] == corners
        rep = s["shape_report"]
        assert rep["vowel"]["wearing"] >= rep["vowel"]["letters"] // 2 >= 2
        assert rep["plosive"]["wearing"] >= 3
        assert _wearing(s, "vowel", "ring") == rep["vowel"]["wearing"]
    s = generate(5, dict(pins))                       # the same pins and seed give the same script
    assert json.dumps(s["letters"]) == json.dumps(generate(5, dict(pins))["letters"])


def test_shape_dials_reject_unknown_names():
    try:
        resolve(1, {"vowel_shape": "dragon"})
    except ValueError:
        return
    raise AssertionError("unknown shape accepted")


def test_reader_finds_shapes_for_classes():
    def read(t):
        return {x["key"]: x["value"] for x in D.keywords(t)}
    assert read("Vowels are rings and the stops are triangles.") == {"vowel_shape": "ring", "plosive_shape": "triangle"}
    r = read("triangular fricatives, nasals made of waves, and circular vowels")
    assert (r["fricative_shape"], r["nasal_shape"], r["vowel_shape"]) == ("triangle", "wave", "ring") and "family" not in r
    r = read("consonants are boxes, vowels are circles")
    assert [r[d] for d in ("plosive_shape", "fricative_shape", "nasal_shape", "approximant_shape")] == ["box"] * 4
    assert r["vowel_shape"] == "ring"
    assert "vowel_shape" not in read("simple bold letters")


def test_menu_lists_shape_names_once_and_model_values_are_checked():
    m = D.menu()
    assert m.count("Shape names:") == 1 and "vowel_shape" in m
    reply = json.dumps({"settings": [{"key": "nasal_shape", "value": "comb", "evidence": "like combs"},
                                     {"key": "vowel_shape", "value": "dragon", "evidence": "x"}]})
    items, _ = D.parse(reply)
    assert [(i["key"], i["value"]) for i in items] == [("nasal_shape", "comb")]


def test_word_separator_dot_sits_in_the_middle_of_its_gap():
    from conlang_forge.script.layout import separator_box
    for d in ("ltr", "rtl"):
        s = generate(3, {"word_separator": "dot", "direction": d, "kind": "alphabet"})
        dot_w, pad, total = separator_box(s["punct"]["separator"])
        assert 0.05 < dot_w < 0.3 and pad >= 0.1 and abs(pad - (total - dot_w - pad)) < 1e-9
