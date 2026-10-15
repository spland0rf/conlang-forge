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


# ------------------------------------------------------------------------------------------ from a picture
import base64  # noqa: E402

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 40).decode()
SPIKY = [0.07, 0.01, 0.04, 0.1, 0.19, 0.05, 0.16, 0.21, 0.06, 0.09, 0.01, 0.01]
ROUND = [0.06, 0.05, 0.04, 0.09, 0.11, 0.06, 0.32, 0.11, 0.03, 0.06, 0.05, 0.02]
BOXY = [0.24, 0.01, 0.0, 0.01, 0.01, 0.01, 0.67, 0.01, 0.0, 0.01, 0.01, 0.01]


def meas(o, **kw):
    return {"orientation": o, "ink": 0.04, "components": 15, "holes": 0.5, "baseline": 0.05, "topline": 0.01, **kw}


def test_measurements_become_settings():
    got = lambda o, **kw: {p["key"]: p["value"] for p in D.measure_proposals(D.clean_measures(meas(o, **kw)))}  # noqa: E731
    assert got(SPIKY)["stroke_bias"] == "vertical+diagonal"
    assert got(ROUND)["stroke_bias"] == "round"
    b = got(BOXY)
    assert b["stroke_bias"] == "horizontal+vertical" and b["family"] == "boxy"
    assert got(ROUND, baseline=0.5)["joining"] == "baseline" and got(ROUND, topline=0.5)["topline"] == "bar"
    assert got(ROUND, holes=1.2)["loops"] == 0.8
    assert all(D.valid(k, v) == v for k, v in got(SPIKY, baseline=0.5, holes=1.2).items())


def test_bad_measurements_and_pictures_are_refused():
    import pytest
    for bad in (None, {}, meas([0.5] * 11), meas([2] + [0] * 11), meas(SPIKY, ink=-1), meas(SPIKY, holes="x")):
        with pytest.raises(ValueError):
            D.clean_measures(bad)
    assert D.check_image({"media_type": "image/png", "data": PNG}) == ("image/png", PNG)
    for bad in ({"media_type": "image/gif", "data": PNG}, {"media_type": "image/jpeg", "data": PNG}, {"media_type": "image/png", "data": ""},
                {"media_type": "image/png", "data": "A" * (D.MAX_IMAGE_B64 + 1)}, {"media_type": "image/png", "data": "!!!"}, "x"):
        with pytest.raises(ValueError):
            D.check_image(bad)


def test_image_endpoint_shows_the_model_the_picture_and_merges_measurements():
    be, c = _app(lambda req: json.dumps({"settings": [{"key": "mark_shape", "value": "ticks", "evidence": "short bars"},
                                                      {"key": "stroke_bias", "value": "diagonal", "evidence": "slanted"}]}))
    body = {"image": {"media_type": "image/png", "data": PNG}, "measures": meas(BOXY)}
    r = c.post("/api/scripts/interpret-image", body)
    assert r.status_code == 200, r.text
    out = r.json()
    by = {p["key"]: p for p in out["proposals"]}
    assert by["mark_shape"]["source"] == "model" and by["stroke_bias"]["value"] == "diagonal"          # the model's word wins
    assert by["family"]["source"] == "image"                                                          # measurements fill the gaps
    assert out["usage"]["input"] > 1000                                                               # a picture is metered like ~1,500 tokens
    sent = be.provider.calls[-1].messages[-1]
    assert sent.images == (("image/png", PNG),) and "Measurements" in sent.content
    assert "copied" in " ".join(out["notes"])
    # the picture is not kept anywhere the call log looks
    with be.db.read() as t:
        rows = t.all("SELECT purpose, preview_json FROM llm_calls WHERE purpose = 'script.describe_image'")
    assert rows and all(PNG not in (r["preview_json"] or "") for r in rows)
    # no model needed, nothing spent; bad input is refused
    out2 = c.post("/api/scripts/interpret-image", {**body, "use_model": False}).json()
    assert out2["usage"] is None and {p["key"] for p in out2["proposals"]} >= {"stroke_bias", "family"}
    assert c.post("/api/scripts/interpret-image", {**body, "image": {"media_type": "image/png", "data": "xx"}}).status_code == 422
    assert c.post("/api/scripts/interpret-image", {**body, "measures": {"ink": 1}}).status_code == 422


def test_provider_sends_pictures_as_image_blocks():
    from conlang_forge.backend.llm.providers import AnthropicProvider
    from conlang_forge.backend.llm.types import LLMRequest, Message
    seen = {}

    def transport(url, headers, body, timeout):
        seen["body"] = json.loads(body)
        return 200, {}, json.dumps({"content": [{"type": "text", "text": "{}"}], "usage": {"input_tokens": 5, "output_tokens": 1}, "model": "m"}).encode()
    AnthropicProvider("k", transport=transport).complete(LLMRequest("m", (Message("user", "hi", (("image/png", PNG),)), Message("user", "plain"))))
    first, second = seen["body"]["messages"]
    assert first["content"][0] == {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": PNG}}
    assert first["content"][1] == {"type": "text", "text": "hi"} and second["content"] == "plain"
