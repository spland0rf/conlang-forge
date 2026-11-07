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


def test_library_letters_are_connected_inside_the_box_and_skip_duplicates():
    allv = G._load("devanagari_library.json")["letters"]
    lib = G.library()
    assert len(allv) == 54 and len(lib) == 51
    assert all(l.get("duplicate_of") for l in allv if l not in lib)
    assert {l["family"] for l in lib} == {"stem", "hang", "descender", "half-bar"}
    for l in lib:
        ss = G.strokes_of([tuple(i) for i in l["s"]], keep_bar=True)
        assert analyse(ss)["parts"] == 1, l["id"]
        assert all(-0.25 <= y <= 1.35 and -0.02 <= x <= 1.02 for s in ss for x, y in s["p"]), l["id"]


def test_library_letter_is_deterministic_and_brings_its_own_headline():
    a, b = G.library_letter(random.Random(3)), G.library_letter(random.Random(3))
    assert a == b and all(s["nobar"] for s in a)


def test_devanagari_preset_can_draw_library_letters():
    from conlang_forge.script import pen_vocab as V
    assert "dg_library" in V.FAMILIES["headline"] and V.LIKE["dg_library"] > 0
    s = generate(40, BY_ID["devanagari"]["pins"])
    assert any(l["family"] == "stroke:dg_library" for l in s["letters"])
