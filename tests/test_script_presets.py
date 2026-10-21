"""The "Create like..." presets: every one is a valid set of pins and makes a script."""
import pytest

from conlang_forge.script.generate import generate
from conlang_forge.script.presets import PRESETS
from conlang_forge.script.service import describe_dials
from conlang_forge.script.spec import resolve


def test_catalogue_lists_every_preset_with_a_note():
    ids = [p["id"] for p in describe_dials()["presets"]]
    assert ids == [p["id"] for p in PRESETS] and len(set(ids)) == len(ids) >= 13
    assert all(p["label"] and p["note"] for p in PRESETS)


@pytest.mark.parametrize("preset", PRESETS, ids=lambda p: p["id"])
def test_preset_pins_are_valid_and_kept(preset):
    spec = resolve(7, preset["pins"])
    for k, v in preset["pins"].items():
        if k in ("ascender_share",) and preset["pins"].get("topline") == "bar":
            continue
        if k in ("consonants",) and spec["corner_style"] == "blocky":
            continue
        assert spec[k] == v, (preset["id"], k, spec[k], v)


@pytest.mark.parametrize("pid", ["latin", "hebrew", "arabic", "devanagari", "thai", "katakana", "hiragana"])
def test_a_script_can_be_made_from_a_preset(pid):
    pins = next(p for p in PRESETS if p["id"] == pid)["pins"]
    sc = generate(11, pins)
    assert len(sc["letters"]) >= 20
    assert sc["spec"]["direction"] == pins["direction"]
