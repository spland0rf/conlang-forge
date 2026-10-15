"""Design by description: new dials (stroke bias, mark shape) and turning words into validated settings."""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_api import DATA, PW, make, signed_in  # noqa: E402

from conlang_forge.backend.api import create_app  # noqa: E402
from conlang_forge.backend.app import Backend, Config  # noqa: E402
from conlang_forge.backend.clock import FakeClock  # noqa: E402
from conlang_forge.backend.llm.providers import FakeProvider  # noqa: E402
from conlang_forge.script import describe as D  # noqa: E402
from conlang_forge.script.bias import profile  # noqa: E402
from conlang_forge.script.generate import generate  # noqa: E402
from conlang_forge.script.marks import make_part  # noqa: E402
from conlang_forge.script.spec import DIALS, resolve  # noqa: E402

EXAMPLE = ("I would like this writing system to be based on lots of vertical and diagonal lines and slashes, with circles as "
           "modifying elements or diacritical marks. It should rise from a solid baseline.")


def test_new_dials_default_to_no_change():
    assert {"stroke_bias", "mark_shape"} <= set(DIALS)
    spec = resolve(5, {})
    assert spec["stroke_bias"] == "balanced" and spec["mark_shape"] == "any"
    a = generate(5, {"kind": "alphabet"})
    b = generate(5, {"kind": "alphabet", "stroke_bias": "balanced", "mark_shape": "any"})
    assert [(l["id"], l["strokes"]) for l in a["letters"]] == [(l["id"], l["strokes"]) for l in b["letters"]]


def test_stroke_bias_shifts_the_ink_of_the_letters():
    def mean(bias, key):
        vals = []
        for seed in (3, 8):
            sc = generate(seed, {"kind": "alphabet", "family": "classic", "family2": "spikey", "complexity": 0.6, "stroke_bias": bias})
            vals += [profile(l["strokes"])[key] for l in sc["letters"]]
        return sum(vals) / len(vals)
    assert mean("diagonal", "d") > mean("balanced", "d") + 0.1
    assert mean("round", "r") > mean("balanced", "r") + 0.1


def test_mark_shape_decides_what_marks_are_made_of():
    rng = random.Random(1)
    for slot in ("above", "below", "left", "right"):
        assert all(make_part(rng, slot, shape="dots")["kind"].startswith("dots") for _ in range(12))
        assert all(make_part(rng, slot, shape="snorkels")["kind"] == "snorkel" for _ in range(12))
        assert all(make_part(rng, slot, shape="circles")["kind"] == "ring" for _ in range(12))
        assert {make_part(rng, slot, shape="ticks")["kind"] for _ in range(12)} <= {"stem", "diag"}
    sc = generate(4, {"kind": "abugida", "mark_shape": "circles"})
    kinds = {p["kind"].rstrip("+") for s in sc["signs"] for p in s["parts"].values()}     # a long sign adds one stroke
    assert kinds == {"ring"}


def test_replies_are_validated_before_anything_is_proposed():
    reply = json.dumps({"settings": [
        {"key": "family", "value": "spikey", "evidence": "sharp"}, {"key": "complexity", "value": 3},
        {"key": "complexity", "value": 0.8, "evidence": "simple"}, {"key": "nope", "value": 1},
        {"key": "consonants", "value": 9}, {"key": "stroke_bias", "value": "sideways"}, {"key": "family", "value": "boxy"}],
        "notes": "ok"})
    got, note = D.parse("Here you go: " + reply)
    assert [(p["key"], p["value"]) for p in got] == [("family", "spikey"), ("complexity", 0.8)] and note == "ok"
    assert D.parse("not json") == ([], "")
    assert D.parse('{"settings": "x"}') == ([], "")


def test_keywords_read_the_example_description():
    got = {p["key"]: p["value"] for p in D.keywords(EXAMPLE)}
    assert got["stroke_bias"] == "vertical+diagonal" and got["mark_shape"] == "circles" and got["joining"] == "baseline"
    assert all(D.valid(k, v) == v for k, v in got.items())


def _app(reply):
    be = Backend(Config(database=":memory:", signing_secret="s" * 40, scrypt_n=2 ** 10, data_dir=DATA),
                 provider=FakeProvider(reply=reply), clock=FakeClock())
    from asgi_client import Client
    c = Client(create_app(be))
    signed_in(c, be)
    return be, c


def test_interpret_endpoint_uses_the_model_and_falls_back_to_keywords():
    be, c = _app(lambda req: json.dumps({"settings": [
        {"key": "family", "value": "spikey", "evidence": "lines and slashes"},
        {"key": "stroke_bias", "value": "vertical+diagonal", "evidence": "vertical and diagonal lines"},
        {"key": "bogus", "value": 1}], "notes": "no way to say 'rise'"}))
    r = c.post("/api/scripts/interpret", {"text": EXAMPLE})
    assert r.status_code == 200, r.text
    out = r.json()
    assert [(p["key"], p["value"], p["source"]) for p in out["proposals"]] == [("family", "spikey", "model"), ("stroke_bias", "vertical+diagonal", "model")]
    assert out["usage"]["input"] > 0 and out["notes"] == ["no way to say 'rise'"]
    # the settings it proposes are accepted as pins
    pins = {p["key"]: p["value"] for p in out["proposals"]}
    assert c.post("/api/scripts/preview", {"seed": 3, "pins": pins}).status_code == 200
    # a model that answers with nonsense: the keyword reader steps in
    be2, c2 = _app(lambda req: "I cannot help with that")
    out2 = c2.post("/api/scripts/interpret", {"text": EXAMPLE}).json()
    assert {p["key"] for p in out2["proposals"]} >= {"stroke_bias", "mark_shape", "joining"} and all(p["source"] == "keywords" for p in out2["proposals"])
    # without the model at all (use_model false), nothing is spent
    out3 = c.post("/api/scripts/interpret", {"text": EXAMPLE, "use_model": False}).json()
    assert out3["usage"] is None and out3["proposals"]
    assert c.post("/api/scripts/interpret", {"text": "  "}).status_code == 422
