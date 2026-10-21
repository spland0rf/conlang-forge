"""The stroke family: kana-like letters made of a few short strokes that need not touch (angular = katakana-like, flowing = hiragana-like)."""
import pytest

from conlang_forge.script import describe, kana
from conlang_forge.script.generate import generate
from conlang_forge.script.graph import analyse
from conlang_forge.script.spec import resolve


@pytest.mark.parametrize("hand", kana.HANDS)
def test_every_archetype_fills_its_box_and_reads_as_one(hand):
    import random
    for name in kana.archetypes(hand):
        good = 0
        for k in range(12):
            _, st = kana.make(random.Random(k), hand, name, mirror_ok=False, extra=0, cross=0)
            assert len([s for s in st if not s.get("dot")]) <= 4
            good += kana.reads_as_one(st) and kana.fills(st, 0.7, 0.45)
        assert good >= 6, (hand, name, good)       # the generator filters the rest; most draws of an archetype must be usable


@pytest.mark.parametrize("hand", kana.HANDS)
def test_stroke_script_letters_are_kana_like(hand):
    sc = generate(3, {"family": "stroke", "stroke_hand": hand, "kind": "alphabet"})
    spec = sc["spec"]
    assert spec["family"] == "stroke" and spec["stroke_hand"] == hand
    assert spec["topline"] == "none" and spec["joining"] == "none"
    assert spec["corner_style"] == ("sharp" if hand == "angular" else "smooth")
    own = [l for l in sc["letters"] if str(l.get("family", "")).startswith("stroke:")]
    assert len(own) >= 0.8 * len(sc["letters"])
    multi = 0
    for l in sc["letters"]:
        a = analyse(l["strokes"])
        assert a["parts"] <= kana.MAX_PARTS + 1       # a mark piece may add one more
        multi += a["parts"] > 1
    assert multi >= 2                                   # separate strokes are the point of the family


def test_deterministic_and_pins_validate():
    pins = {"family": "stroke", "stroke_hand": "angular"}
    assert generate(8, pins)["letters"] == generate(8, pins)["letters"]
    with pytest.raises(ValueError):
        resolve(1, {"stroke_hand": "curly"})


def test_hand_auto_resolves_and_is_unused_without_the_family():
    assert resolve(4, {"family": "stroke"})["stroke_hand"] in kana.HANDS
    assert all(resolve(s)["family"] != "stroke" and resolve(s)["family2"] != "stroke" for s in range(1, 60))   # never drawn at random
    assert resolve(4, {"family": "boxy", "stroke_hand": "angular"})["stroke_hand"] == "auto"


def test_second_family_blends_kana_vowels():
    sc = generate(6, {"family": "boxy", "family2": "stroke", "stroke_hand": "flowing", "kind": "alphabet"})
    fams = {l["id"]: str(l.get("family", "")) for l in sc["letters"]}
    assert any(f.startswith("stroke:") for f in fams.values())
    assert any(not f.startswith("stroke:") for f in fams.values())


def test_description_reader_knows_kana():
    k = {i["key"]: i["value"] for i in describe.keywords("a script like katakana")}
    assert k["family"] == "stroke" and k["stroke_hand"] == "angular"
    h = {i["key"]: i["value"] for i in describe.keywords("soft hiragana-like letters")}
    assert h["family"] == "stroke" and h["stroke_hand"] == "flowing"


@pytest.mark.parametrize("hand", kana.HANDS)
def test_extra_ticks_and_crossings_keep_a_letter_readable(hand):
    import random
    for k in range(60):
        _, st = kana.make(random.Random(k), hand, extra=1.0, cross=1.0)
        assert len([s for s in st if not s.get("dot")]) <= 7
