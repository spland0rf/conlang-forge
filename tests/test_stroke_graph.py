"""The stroke-graph forms (traced Devanagari letters and Generator v2's corpus) load, convert and stay connected."""
import random

from conlang_forge.script import stroke_graph as G
from conlang_forge.script.generate import analyse, generate
from conlang_forge.script.geometry import stroke
from conlang_forge.script.presets import BY_ID


def _barred(ss):
    xs = [x for s in ss for x, _ in s["p"]]
    return ss + [stroke([(min(xs), 1.0), (max(xs), 1.0)])]


def test_real_letters_are_one_connected_shape_and_sit_in_the_box():
    letters = G.real_letters()
    assert len(letters) == 49
    for l in letters:
        ss = G.real_strokes(l["glyph"], l["variant"])
        assert analyse(_barred(ss))["parts"] == 1, l["glyph"]
        assert all(-0.2 <= y <= 1.3 for s in ss for _, y in s["p"])


def test_corpus_letters_are_connected_and_not_copies():
    n = 0
    for st in G.corpus():
        for l in st["letters"]:
            n += 1
            assert analyse(_barred(G.strokes_of(l["s"])))["parts"] == 1
    assert n > 500


def test_headline_bar_is_not_duplicated_and_descenders_reach_it():
    ss = G.real_strokes("इ")
    assert not any(len(set(round(y, 3) for _, y in s["p"])) == 1 and round(s["p"][0][1], 3) == 1.0 for s in ss)
    assert max(y for s in ss for _, y in s["p"]) >= 0.999


def test_devanagari_preset_draws_from_the_corpus_deterministically():
    s = generate(2, BY_ID["devanagari"]["pins"])
    assert any(l["family"] == "stroke:dg_corpus" for l in s["letters"])
    assert generate(2, BY_ID["devanagari"]["pins"])["letters"] == s["letters"]
