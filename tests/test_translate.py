"""Translation pipeline: English morphology, the shallow parser and printer, validation and repair, English -> language ->
English round trips across very different generated languages, the Reducer's repair loop and the translate endpoint.
No network and no real model: the model is a scripted FakeProvider."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pytest  # noqa: E402

from conlang_forge.backend.conlangs import engine_generator  # noqa: E402
from conlang_forge.translate import english as en  # noqa: E402
from conlang_forge.translate.engine import LanguageTranslator  # noqa: E402
from conlang_forge.translate.parser import parse  # noqa: E402
from conlang_forge.translate.validate import autorepair, unknown_words, validate  # noqa: E402

DATA = str(Path(__file__).resolve().parents[1] / "data")
_GEN = engine_generator(DATA)
_LANGS = {}
LANG_SPECS = [(1, None), (5, None), (11, {"morphology.typology": "agglutinative"}), (12, {"morphology.typology": "isolating"}),
              (7, None), (3, None)]


def lang(seed, pins=None):
    key = (seed, repr(sorted((pins or {}).items())))
    if key not in _LANGS:
        _LANGS[key] = _GEN(seed, pins or {})
    return _LANGS[key]


def tr(seed, pins=None):
    key = ("tr", seed, repr(sorted((pins or {}).items())))
    if key not in _LANGS:
        _LANGS[key] = LanguageTranslator(lang(seed, pins)[1])
    return _LANGS[key]


# ---------------------------------------------------------------- English forms
def test_english_forms():
    assert en.third("go") == "goes" and en.third("carry") == "carries" and en.third("have") == "has"
    assert en.past("see") == "saw" and en.past("walk") == "walked" and en.past("stop") == "stopped" and en.past("love") == "loved"
    assert en.participle("see") == "seen" and en.participle("eat") == "eaten" and en.ing("make") == "making"
    assert en.ing("run") == "running" and en.ing("visit") == "visiting" and en.ing("die") == "dying"
    assert en.plural("wolf") == "wolves" and en.plural("city") == "cities" and en.plural("box") == "boxes"
    assert en.plural("man") == "men" and en.plural("fish") == "fish"
    assert ("see", "past") in en.verb_candidates("saw") and ("walk", "past") in en.verb_candidates("walked")
    assert ("make", "ing") in en.verb_candidates("making") and ("run", "ing") in en.verb_candidates("running")
    assert ("city", "plural") in en.noun_candidates("cities") and ("man", "plural") in en.noun_candidates("men")


# ---------------------------------------------------------------- parser and printer
SENTENCES = [
    "The old wizard saw the dragon in the dark cave.", "Does the king see the dog?", "Who sees the dragon?",
    "What did you see?", "Where is the king?", "I do not have a sword.", "The guards watch the gate, and the king sleeps.",
    "The king's sword is big.", "Hello.", "Aldric kills the dragons with three swords.", "I will not go.",
    "She has seen the dragon.", "We are walking home.", "Where did you go?", "Is the king old?", "They had eaten the bread.",
    "An old man sees a big dog.", "Do not touch the sword.", "Who is the king?", "The women eat the bread.",
]


def test_parser_reads_structure():
    V = tr(1)[0] if False else tr(1).V
    d, issues = parse(V, "The old wizard saw the dragon in the dark cave.")
    c = d["sentences"][0]["clauses"][0]
    assert c["subject"] == {"definite": True, "adjectives": ["old"], "head": "wizard"} and c["verb"] == "see"
    assert c["tense"] == "past" and c["object"]["head"] == "dragon" and c["pps"][0][0] == "in" and not issues
    c = parse(V, "I do not have a sword.")[0]["sentences"][0]["clauses"][0]
    assert c["negated"] and c["subject"]["head"] == "i" and c["verb"] == "have" and c["object"]["definite"] is False
    c = parse(V, "Does the king see the dog?")[0]["sentences"][0]["clauses"][0]
    assert c["question"] == "yes-no" and c["subject"]["head"] == "king"
    c = parse(V, "What did you see?")[0]["sentences"][0]["clauses"][0]
    assert c["question"] == "wh" and c["object"]["head"] == "what" and c["subject"]["head"] == "you" and c["tense"] == "past"
    c = parse(V, "Aldric kills the dragons with three swords.")[0]["sentences"][0]["clauses"][0]
    assert c["subject"]["head"] == "#Aldric" and c["object"]["number"] == "plural" and c["pps"][0][1]["numeral"] == 3
    c = parse(V, "The king's sword is big.")[0]["sentences"][0]["clauses"][0]
    assert c["subject"]["possessor"] == "king" and c["predicate"] == {"adjective": "big"}
    d = parse(V, "The king sleeps, and the queen sings.")[0]["sentences"][0]
    assert len(d["clauses"]) == 2 and d["links"] == ["and"]


def test_printer_roundtrips_the_parser():
    t = tr(1)
    from conlang_forge.translate.printer import Printer
    P = Printer(t.V)
    for s in SENTENCES:
        d, _ = parse(t.V, s)
        again, _ = parse(t.V, P.document(d))
        assert again == d, (s, P.document(d))


def test_parser_never_fails_and_flags_unknown_words():
    t = tr(1)
    for junk in ["", "   ", "!!!", "asdf qwer zxcv", "The the the.", "dog dog dog dog", "1234567 swords", "and and and",
                 "Who who who?", "of the of the", "Don't you ever, ever, stop?", "She said: \"go!\""]:
        res = t.to_language(junk)
        assert isinstance(res["text"], str)
    res = t.to_language("The zorp eats the blorf.")
    assert res["text"] and set(res["unknown"]) == {"zorp", "blorf"}
    assert any(i["code"] == "kept_as_name" for i in res["issues"])
    d, issues = t.parse("The wizzard sees the dragon.")
    bad = [i for i in issues if i["code"] == "unknown_word"]
    assert bad and "wizard" in bad[0]["suggestions"]


def test_repair_replaces_unknown_words_instead_of_failing():
    t = tr(1)
    d, issues = t.parse("The glorbulous king flarbs the dragon with a zing.")
    fixed, notes = autorepair(d, t.V, t.realizer.g)
    assert not validate(fixed, t.V, t.realizer.g)
    assert {n["code"] for n in notes} <= {"kept_as_name", "word_dropped", "word_replaced"}
    out = t.to_language("The glorbulous king flarbs the dragon with a zing.")
    assert out["sentences"] and out["text"]


# ---------------------------------------------------------------- English -> language -> English
CORE = ["The king sees the dog.", "The old wizard saw the dragon in the dark cave.", "I do not have a sword.",
        "Does the king see the dog?", "Who sees the dragon?", "The women eat the bread.", "We will go to the house.",
        "The dog is big.", "Where is the king?", "The king sleeps, and the queen sings.", "Three men walk.",
        "Do not touch the sword.", "They eat bread.", "You have a big house."]
PRON = {"he": "he", "she": "he", "it": "he"}


def _core(doc):
    out = []
    for s in doc["sentences"]:
        for c in s["clauses"]:
            if c.get("kind") != "clause":
                out.append(("fragment",))
                continue

            def h(n):
                return PRON.get(n["head"], n["head"]) if n else None
            pr = c.get("predicate") or {}
            out.append((h(c.get("subject")), c.get("verb"), h(c.get("object")), bool(c.get("negated")),
                        c.get("question"), pr.get("adjective") or pr.get("adverb") or (pr.get("head") if pr else None),
                        tuple(sorted(p for p, _ in c.get("pps", [])))))
    return out


def test_every_language_translates_and_reads_back():
    total = ok = 0
    per_language = {}
    for seed, pins in LANG_SPECS:
        t = tr(seed, pins)
        good = 0
        for s in CORE:
            res = t.to_language(s)
            assert res["text"] and not [i for i in res["issues"] if i["level"] == "error"], (seed, s, res["issues"])
            assert t.to_language(s)["text"] == res["text"]                      # deterministic
            back = t.from_language(res["text"])
            want, got = _core(res["doc"]), _core(back["doc"])
            total += 1
            good += want == got
        per_language[seed] = good / len(CORE)
        ok += good
    assert ok / total >= 0.7, (ok / total, per_language)
    assert min(per_language.values()) >= 0.5, per_language


def test_commands_are_addressed_to_you():
    for seed, pins in LANG_SPECS[:4]:
        t = tr(seed, pins)
        res = t.to_language("Do not touch the sword.")
        back = t.from_language(res["text"])["doc"]["sentences"][0]["clauses"][0]
        assert back["verb"] == "touch" and back["negated"]
        if back["subject"]:
            assert back["subject"]["head"] in ("you", "sword")      # no imperative ending: read as a statement to "you"


# ---------------------------------------------------------------- the Reducer (scripted model) and the endpoint
def _backend(script=None):
    from conlang_forge.backend.app import Backend, Config
    from conlang_forge.backend.clock import FakeClock
    from conlang_forge.backend.llm.providers import FakeProvider
    spec, language = lang(11, {"morphology.typology": "agglutinative"})
    be = Backend(Config(database=":memory:", signing_secret="s" * 40, scrypt_n=2 ** 10, data_dir=DATA),
                 provider=FakeProvider(script), clock=FakeClock(), generator=lambda seed, pins: (spec, language))
    u = be.accounts.register("t@x.org", "Correct-Horse-9")
    actor = be.accounts.actor_of(be.accounts.get(u["id"]))
    c = be.conlangs.create(actor, "Test", seed=11)
    return be, actor, c["id"]


def test_reducer_repairs_unknown_words_then_translates():
    be, actor, cid = _backend(["The wizzard sees the dragon.", "The wizard sees the dragon."])
    out = be.translation.to_language(actor, cid, "The sorcerer is looking at the dragon.")
    assert out["repair_rounds"] == 1 and out["reduced"] == "The wizard sees the dragon."
    assert out["text"] and not [i for i in out["issues"] if i["level"] == "error"]
    calls = be.llm.provider.calls
    assert len(calls) == 2 and calls[0].cache_system and "Vocabulary" in calls[0].system and "wizard" in calls[0].system
    assert "wizzard" in calls[1].messages[-1].content and "wizard" in calls[1].messages[-1].content       # suggestion offered
    assert be.usage.my_usage(actor)["day"]["used"] > 0                  # both calls were metered to the user
    res = be.translation.from_language(actor, cid, out["text"])
    assert res["literal"] == ["Wizard sees dragon."] and res["natural"] is None       # this language has no articles


def test_reducer_gives_up_politely_and_never_fails():
    be, actor, cid = _backend(["The zorp eats the blorf.", "The zorp eats the blorf.", "The zorp eats the blorf."])
    out = be.translation.to_language(actor, cid, "Zorps eat blorfs")
    assert out["repair_rounds"] == 2 and out["text"]
    assert {i["code"] for i in out["issues"]} >= {"kept_as_name"}


def test_restricted_mode_is_free_and_smoothing_is_metered():
    be, actor, cid = _backend(["The king saw the old dog."])
    out = be.translation.to_language(actor, cid, "The king sees the old dog.", mode="restricted")
    assert out["usage"] is None and be.usage.my_usage(actor)["day"]["used"] == 0 and not be.llm.provider.calls
    res = be.translation.from_language(actor, cid, out["text"], smooth=True)
    assert res["natural"] == ["The king saw the old dog."] and res["usage"]["input"] > 0
    assert be.llm.provider.calls[0].system.startswith("You turn a machine")
    assert be.usage.my_usage(actor)["day"]["used"] > 0


def test_translation_is_permissioned_and_validated():
    from conlang_forge.backend.errors import PermissionDenied, ValidationFailed
    be, actor, cid = _backend()
    other = be.accounts.actor_of(be.accounts.get(be.accounts.register("o@x.org", "Correct-Horse-9")["id"]))
    with pytest.raises(PermissionDenied):
        be.translation.to_language(other, cid, "The king sees the dog.", mode="restricted")
    with pytest.raises(ValidationFailed):
        be.translation.to_language(actor, cid, "   ")
    with pytest.raises(ValidationFailed):
        be.translation.to_language(actor, cid, "x" * 5000)
    boss = be.accounts.actor_of(be.accounts.get(be.accounts.bootstrap_admin("boss@x.org", "Correct-Horse-9")["id"]))
    assert be.translation.from_language(boss, cid, "hello")["literal"]          # admins may read, but not spend:
    with pytest.raises(PermissionDenied):
        be.translation.to_language(boss, cid, "The king sees the dog.", mode="english")


def test_translate_endpoint():
    from asgi_client import Client
    from conlang_forge.backend.api import create_app
    be, actor, cid = _backend(["The king sees the dog."])
    c = Client(create_app(be))
    c.token = be.accounts.login("t@x.org", "Correct-Horse-9")["access_token"]
    r = c.post(f"/api/conlangs/{cid}/translate", {"direction": "to", "text": "The king looks at the dog."})
    assert r.status_code == 200 and r.json()["text"] and r.json()["reduced"] == "The king sees the dog."
    r2 = c.post(f"/api/conlangs/{cid}/translate", {"direction": "from", "text": r.json()["text"]})
    assert r2.status_code == 200 and r2.json()["literal"] == ["King sees dog."]
    assert c.post(f"/api/conlangs/{cid}/translate", {"direction": "sideways", "text": "x"}).status_code == 422
    assert c.post(f"/api/conlangs/{cid}/translate", {"direction": "to"}).status_code == 422


def test_names_keep_their_endings_and_come_back_as_names():
    for seed, pins in LANG_SPECS[:3]:
        t = tr(seed, pins)
        res = t.to_language("Aldric sees the dragon.")
        back = t.from_language(res["text"])
        subj = back["doc"]["sentences"][0]["clauses"][0]["subject"]
        assert subj and str(subj["head"]).startswith("#"), (seed, res["text"], back["interlinear"])
        assert any(not tok["known"] for tok in back["interlinear"][0])
