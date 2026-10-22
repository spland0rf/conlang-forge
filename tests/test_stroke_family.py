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
            _, st = kana.make(random.Random(k), hand, name, mirror_ok=False, extra=0, cross=0, join=0)
            assert len([s for s in st if not s.get("dot")]) <= 5
            fh, fw = kana.FILL.get(hand, (0.7, 0.45))
            good += kana.reads_as_one(st) and kana.fills(st, fh, fw)
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
    assert multi >= (0 if hand in ("bowed", "pen") else 2)       # separate strokes are the point of the kana hands; bowed and pen letters are one piece


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


def test_kana_voicing_is_two_ticks_above_the_letter():
    from conlang_forge.script.generate import generate
    from conlang_forge.script.presets import BY_ID
    s = generate(2, BY_ID["katakana"]["pins"])
    kinds = {m["kind"]: m for m in s["marks"]}
    assert "dakuten" in kinds and len(kinds["dakuten"]["strokes"]) == 2 and kinds["dakuten"]["slot"] == "above"
    voiced = [l for l in s["letters"] if l.get("feature") == "voiced"]
    assert voiced and all(l["mark"] == kinds["dakuten"]["id"] for l in voiced)


def test_basic_katakana_are_mostly_one_piece():
    from conlang_forge.script.generate import generate
    from conlang_forge.script.graph import analyse
    from conlang_forge.script.presets import BY_ID
    s = generate(3, BY_ID["katakana"]["pins"])
    base = [l for l in s["letters"] if not l.get("relation")]
    one = [l for l in base if analyse([x for x in l["strokes"] if not x.get("stub")])["parts"] == 1]
    assert len(one) >= 0.6 * len(base)


def test_bowed_hand_is_elvish_like():
    from conlang_forge.script.presets import BY_ID
    sc = generate(4, BY_ID["elvish"]["pins"])
    assert sc["spec"]["stroke_hand"] == "bowed" and sc["spec"]["kind"] == "abugida"
    assert all(analyse([s for s in l["strokes"] if not s.get("stub")])["parts"] == 1 for l in sc["letters"])      # every letter is one piece
    bands = {l["band"] for l in sc["letters"]}
    assert "desc" in bands or "asc" in bands or "asc+desc" in bands                                         # stems reach beyond the x-height band
    assert all(s["slots"] == ["above"] for s in sc["signs"])                                                 # vowel marks sit above the letter
    assert describe.keywords("a script like Elvish, stems with round bows")


def test_voicing_marks_and_sign_slot_work_in_any_family():
    sc = generate(5, {"family": "curvy", "kind": "alphabet", "mark_shape": "voicing", "mark_share": 0.4, "consonants": 22})
    kinds = {m["kind"] for m in sc["marks"]}
    assert "dakuten" in kinds
    ab = generate(5, {"family": "boxy", "kind": "abugida", "vowel_sign_slot": "below"})
    assert ab["signs"] and all(s["slots"] == ["below"] for s in ab["signs"])
    assert describe.keywords("with dakuten style voicing marks")


def test_stroke_extras_are_dials_for_every_hand():
    import random
    from conlang_forge.script.generate import generate as g
    plain = g(7, {"family": "stroke", "stroke_hand": "flowing", "stroke_ticks": 0.0, "stroke_crossings": 0.0, "stroke_joins": 0.0})
    busy = g(7, {"family": "stroke", "stroke_hand": "flowing", "stroke_ticks": 1.0, "stroke_crossings": 1.0, "stroke_joins": 0.0})
    n = lambda sc: sum(len([s for s in l["strokes"] if not s.get("stub")]) for l in sc["letters"])
    assert n(busy) > n(plain)
    bowed = g(7, {"family": "stroke", "stroke_hand": "bowed", "stroke_ticks": 1.0})        # a bowed script may now have ticks too
    assert bowed["spec"]["stroke_ticks"] == 1.0 and bowed["spec"]["vowel_sign_slot"] == "above"


def _share(sc):
    return sum(str(l.get("family", "")).startswith("stroke:") for l in sc["letters"]) / len(sc["letters"])


def test_stroke_share_sets_how_many_letters_are_stroke_letters():
    base = {"family": "curvy", "family2": "stroke", "stroke_hand": "flowing", "kind": "alphabet", "consonants": 20, "vowels": 5}
    none, some, most = (generate(11, dict(base, stroke_share=x)) for x in (0.0, 0.3, 0.8))
    assert _share(none) == 0 and 0.2 <= _share(some) <= 0.4 and _share(most) >= 0.7      # derived letters copy their parent, so not exact
    assert resolve(11, {"family": "stroke"})["stroke_share"] == 1.0
    assert resolve(11, {"family": "curvy", "family2": "stroke"})["stroke_share"] == 0.35


def test_any_script_can_take_some_stroke_letters():
    sc = generate(12, {"family": "classic", "kind": "alphabet", "stroke_share": 0.25, "stroke_hand": "bowed", "consonants": 20, "vowels": 5})
    assert sc["spec"]["stroke_hand"] == "bowed" and 0.1 <= _share(sc) <= 0.4
    off = generate(12, {"family": "classic", "kind": "alphabet", "consonants": 20, "vowels": 5})
    assert _share(off) == 0 and off["spec"]["stroke_hand"] == "auto"
