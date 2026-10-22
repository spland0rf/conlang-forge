"""The cuneiform hand of the stroke family: signs made of filled wedges (Akkadian-like)."""
import random

import pytest

from conlang_forge.script import cuneiform, kana
from conlang_forge.script.describe import keywords
from conlang_forge.script.generate import generate
from conlang_forge.script.presets import BY_ID
from conlang_forge.script.render import strokes_svg
from conlang_forge.script.spec import resolve


def test_every_archetype_is_filled_wedges_inside_the_box():
    for name, build in cuneiform.ARCHETYPES.items():
        for seed in range(30):
            sts = build(random.Random(seed))
            assert sts, name
            for st in sts:
                assert st["fill"] and st["closed"] and len(st["p"]) == 3 and st["k"] == "s"
                assert all(-0.1 <= x <= 1.1 and -0.1 <= y <= 1.1 for x, y in st["p"]), (name, st["p"])


def test_wedges_are_never_mirrored():
    """A horizontal wedge keeps its head on the left: the generic kana mirroring is off for this hand."""
    for seed in range(60):
        _, sts = kana.make(random.Random(seed), "cuneiform", "hrows")
        for st in sts:
            (x0, _), (x1, _), (tx, _) = st["p"]
            assert tx > max(x0, x1)


def test_the_preset_makes_cuneiform_signs():
    s = generate(2, BY_ID["cuneiform"]["pins"])
    assert s["spec"]["stroke_hand"] == "cuneiform"
    letters = [l for l in s["letters"] if l["family"].startswith("stroke:")]
    assert len(letters) >= 0.6 * len(s["letters"])
    assert {l["family"].split(":")[1] for l in letters} <= set(cuneiform.ARCHETYPES)
    assert all(st.get("fill") for l in letters for st in l["strokes"] if not st.get("stub") and not st.get("dot"))
    assert generate(2, BY_ID["cuneiform"]["pins"])["letters"] == s["letters"]          # deterministic


def test_filled_wedges_are_drawn_filled():
    svg = strokes_svg([cuneiform.wedge(.2, .8, -90, .8)], 0.0)
    assert 'fill="#1b1b1b"' in svg and 'fill="none"' not in svg


def test_dials_and_description():
    assert resolve(1, {"family": "stroke", "stroke_hand": "cuneiform"})["stroke_hand"] == "cuneiform"
    assert resolve(1, {"width": 1.5})["width"] == 1.5
    with pytest.raises(ValueError):
        resolve(1, {"width": 1.6})
    got = {(i["key"], i["value"]) for i in keywords("a script like Akkadian cuneiform, wedges pressed in clay")}
    assert ("family", "stroke") in got and ("stroke_hand", "cuneiform") in got
