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


DEPENDENT = [
    "I am afraid that my grandmother needs a bath.", "We left because the king came.", "When the king came, we left.",
    "If the king sleeps, we wait.", "The old queen thinks that the king saw the dog, and the dog sleeps.",
    "Do you know that the king is old?", "The man who sleeps is old.", "I see the dog that bit the king.",
    "The dog that the queen sees sleeps.", "We wait until the king comes.", "I think that the dragon that sleeps will wake.",
    "Please take my grandmother around the back so she won't have to smell it.", "I want to see the dragon.",
    "The king told the old queen to sleep.", "We are going to see the dragon because the king is going to wake.",
    "I will wait as the king sleeps.", "Once the king came, we left.", "We left as soon as the king came.",
    "I know what the king saw.", "I know who saw the dog.", "I wonder why the king sleeps.", "I know who the king is.",
    "I asked whether the king sleeps or the queen sleeps.", "I see the man whose dog bit the king.",
    "This is the place where the king sleeps.", "We eat after sleeping.", "We left without seeing the king.",
    "After eating, we slept.", "I came to see the king.", "I came in order to see the king.", "I am afraid to go.",
    "He sleeps like the king sleeps.", "He acts as if the king sleeps.", "Now that the king came, we wait.",
    "Whoever sees the dog wins.", "What the king saw is old.", "I think the king saw the dog.", "We wait in case the king comes.",
]


def test_dependent_clauses_are_read_as_clauses():
    V = tr(1).V
    s = parse(V, "I am afraid that my grandmother needs a bath.")[0]["sentences"][0]
    assert len(s["clauses"]) == 2 and s["links"] == [""] and s["clauses"][1]["intro"] == "that"
    assert s["clauses"][0]["predicate"] == {"adjective": "afraid"} and s["clauses"][1]["verb"] == "need"
    assert s["clauses"][1]["subject"]["possessor"] == "i" and s["clauses"][1]["subject"]["head"] == "grandmother"
    for text, intro, first in [("We left because the king came.", "because", 1), ("When the king came, we left.", "when", 0),
                               ("If the king sleeps we wait.", "if", 0)]:           # also without the comma
        d, issues = parse(V, text)
        s = d["sentences"][0]
        assert [c.get("intro") for c in s["clauses"]].index(intro) == first and len(s["clauses"]) == 2, text
        assert not [i for i in issues if i["code"] == "ignored_words"], (text, issues)
    s = parse(V, "The old queen thinks that the king saw the dog, and the dog sleeps.")[0]["sentences"][0]
    assert [c.get("intro") for c in s["clauses"]] == [None, "that", None] and s["links"] == ["", "and"]
    # 'that' and 'after' are still ordinary words where no clause follows them
    s = parse(V, "I see that dog.")[0]["sentences"][0]
    assert len(s["clauses"]) == 1 and s["clauses"][0]["object"]["demonstrative"] == "that"
    s = parse(V, "We sleep after the war.")[0]["sentences"][0]
    assert len(s["clauses"]) == 1 and s["clauses"][0]["pps"][0][0] == "after"
    # a question about a dependent statement keeps the question on the main clause
    s = parse(V, "Do you know that the king is old?")[0]["sentences"][0]
    assert s["clauses"][0]["question"] == "yes-no" and s["clauses"][1]["intro"] == "that"


def test_please_and_to_verb_are_understood():
    V = tr(1).V
    text = "Please take my grandmother around the back so she won't have to smell it."
    d, issues = parse(V, text)
    s = d["sentences"][0]
    assert not [i for i in issues if i["code"] in ("ignored_words", "loose_fragment")], issues
    assert [c.get("intro") for c in s["clauses"]] == [None, "so", "that"]
    a, b, c = s["clauses"]
    assert a["mood"] == "imperative" and a["polite"] and a["verb"] == "take" and a["pps"][0][0] == "around"
    assert b["verb"] == "need" and b["negated"] and b["tense"] == "future" and b["subject"]["head"] == "she"
    assert c["verb"] == "smell" and c["subject"] == b["subject"] and c["object"]["head"] == "it"
    s = parse(V, "I want her to go.")[0]["sentences"][0]["clauses"]            # object control: she is the one going
    assert s[0]["object"] is None and s[1]["subject"]["head"] == "she" and s[1]["verb"] == "go"
    s = parse(V, "She must wait.")[0]["sentences"][0]["clauses"]               # no modals: 'must' becomes 'need to'
    assert s[0]["verb"] == "need" and s[1]["verb"] == "wait"
    s = parse(V, "We must go so that she sleeps.")[0]["sentences"][0]["clauses"]
    assert [c.get("intro") for c in s] == [None, "that", "so"]
    # ordinary words are not swallowed
    assert parse(V, "Please the king.")[0]["sentences"][0]["clauses"][0]["object"]["head"] == "king"
    assert len(parse(V, "I go to the gate.")[0]["sentences"][0]["clauses"]) == 1


def test_going_to_is_future_only_before_a_verb():
    V = tr(1).V
    one = lambda t: (lambda d, i: (d["sentences"][0]["clauses"], i))(*parse(V, t))
    for text, verb in [("I am going to see the dog.", "see"), ("They are going to sleep.", "sleep"), ("I'm gonna go.", "go")]:
        c, issues = one(text)
        assert len(c) == 1 and c[0]["verb"] == verb and c[0]["tense"] == "future" and not issues, (text, c, issues)
    c, _ = one("Are you going to see the dog?")
    assert c[0]["question"] == "yes-no" and c[0]["tense"] == "future" and c[0]["subject"]["head"] == "you"
    c, _ = one("What are you going to see?")
    assert c[0]["question"] == "wh" and c[0]["object"]["head"] == "what" and c[0]["tense"] == "future"
    c, _ = one("She is not going to wait.")
    assert c[0]["negated"] and c[0]["tense"] == "future" and c[0]["verb"] == "wait"
    # a trip stays a trip
    for text, verb in [("I am going to the gate.", "go"), ("She is traveling to the city.", "travel"), ("We are going to town.", "go")]:
        c, issues = one(text)
        assert c[0]["verb"] == verb and c[0]["pps"][0][0] == "to" and c[0]["tense"] == "present" and c[0]["aspect"] == "progressive", text
    assert one("We shall see the dog.")[0][0]["tense"] == "future"


def test_more_linking_words_map_onto_the_ones_languages_have():
    V = tr(1).V
    intros = lambda t: [c.get("intro") for c in parse(V, t)[0]["sentences"][0]["clauses"]]
    for text, expect in [("I will wait as the king sleeps.", [None, "while"]), ("We left as soon as the king came.", [None, "when"]),
                         ("Once the king came, we left.", ["when", None]), ("We left whenever the king came.", [None, "when"]),
                         ("We wait in case the king comes.", [None, "if"]), ("We left even though the king came.", [None, "though"]),
                         ("Now that the king came, we wait.", ["because", None]), ("He acts as if the king sleeps.", [None, "like"]),
                         ("I wait where the king sleeps.", [None, "where"]), ("I wonder why the king sleeps.", [None, "why"]),
                         ("I know how the king sleeps.", [None, "how"]), ("We came so that she sleeps.", [None, "so"]),
                         ("I think the king saw the dog.", [None, "that"])]:
        assert intros(text) == expect, (text, intros(text))
    # ordinary uses of the same words are untouched
    assert len(parse(V, "I see the king as a friend.")[0]["sentences"][0]["clauses"]) == 1
    assert len(parse(V, "I like the dog.")[0]["sentences"][0]["clauses"]) == 1


def test_embedded_questions_keep_the_question_word_inside():
    V = tr(1).V
    c = parse(V, "I know what the king saw.")[0]["sentences"][0]["clauses"]
    assert len(c) == 2 and c[1]["object"]["head"] == "what" and c[1]["question"] == "wh" and c[1]["embedded"] and c[1]["tense"] == "past"
    c = parse(V, "I know who saw the dog.")[0]["sentences"][0]["clauses"]
    assert c[1]["subject"]["head"] == "who" and c[1]["object"]["head"] == "dog" and c[1]["embedded"]
    c = parse(V, "I know who the king is.")[0]["sentences"][0]["clauses"]
    assert c[1]["predicate"]["head"] == "who" and c[1]["verb"] is None
    c = parse(V, "I asked whether the king sleeps or the queen sleeps.")[0]["sentences"][0]
    assert [x.get("intro") for x in c["clauses"]] == [None, "whether", None] and c["links"] == ["", "or"]
    # who/what after a noun still describe it
    assert len(parse(V, "I see the man who sleeps.")[0]["sentences"][0]["clauses"]) == 1
    c = parse(V, "Whoever sees the dog wins.")[0]["sentences"][0]["clauses"]
    assert len(c) == 1 and c[0]["subject"]["head"] == "person" and c[0]["subject"]["relative"]["word"] == "who"
    c = parse(V, "What the king saw is old.")[0]["sentences"][0]["clauses"]
    assert c[0]["subject"]["head"] == "thing" and c[0]["subject"]["relative"]["gap"] == "object"
    assert parse(V, "What did the king see?")[0]["sentences"][0]["clauses"][0].get("embedded") is None


def test_relative_clauses_with_whose_where_when_why():
    V = tr(1).V
    o = parse(V, "I see the man whose dog bit the king.")[0]["sentences"][0]["clauses"][0]["object"]
    rel = o["relative"]
    assert rel["word"] == "whose" and rel["gap"] == "possessor" and rel["clause"]["subject"]["possessor"] == "man" and rel["cid"] == "that"
    for text, word, head in [("This is the place where the king sleeps.", "where", "place"), ("I see the day when the king came.", "when", "day"),
                             ("I know the reason why the king sleeps.", "why", "reason")]:
        c = parse(V, text)[0]["sentences"][0]["clauses"]
        np = (c[0].get("object") or c[0].get("predicate"))
        assert len(c) == 1 and np["head"] == head and np["relative"]["word"] == word and np["relative"]["gap"] == "adjunct", text
    # 'where' after an ordinary noun is a separate clause, not a description of it
    assert len(parse(V, "I see the king where he sleeps.")[0]["sentences"][0]["clauses"]) == 2


def test_clauses_without_their_own_subject_borrow_one():
    V = tr(1).V
    cl = lambda t: parse(V, t)[0]["sentences"][0]["clauses"]
    c = cl("We eat after sleeping.")
    assert [x.get("intro") for x in c] == [None, "after"] and c[1]["subject"]["head"] == "we" and c[1]["verb"] == "sleep"
    c = cl("After eating, we slept.")
    assert c[0]["intro"] == "after" and c[0]["subject"]["head"] == "we" and c[0]["tense"] == "past" and c[0]["verb"] == "eat"
    s = parse(V, "We left without seeing the king.")[0]["sentences"][0]
    assert s["links"] == ["and"] and s["clauses"][1]["negated"] and s["clauses"][1]["subject"]["head"] == "we" and s["clauses"][1]["tense"] == "past"
    c = cl("I came to see the king.")
    assert c[1]["intro"] == "so" and c[1]["subject"]["head"] == "i" and c[1]["verb"] == "see"
    assert cl("I came in order to see the king.") == c
    c = cl("I am afraid to go.")
    assert c[1]["intro"] == "that" and c[1]["subject"]["head"] == "i"
    assert cl("Eat before leaving.")[1]["subject"]["head"] == "you"
    # a trip to a place, and a noun that looks like a verb, are still not purposes
    assert len(cl("I go to the gate.")) == 1 and len(cl("I go to sleep.")) == 1


def test_quoted_speech_is_translated_as_its_own_sentence():
    from conlang_forge.translate.parser import split_sentences
    V = tr(1).V
    d = parse(V, 'He said, "The king sleeps."')[0]["sentences"]
    assert len(d) == 2 and not d[0].get("quote") and d[1].get("quote") and d[1]["clauses"][0]["subject"]["head"] == "king"
    d = parse(V, '"Where is the king?" he asked.')[0]["sentences"]
    assert d[0].get("quote") and d[0]["mark"] == "?" and d[1]["clauses"][0]["verb"] == "ask"
    assert len(split_sentences("No quotes here.")) == 1
    t = tr(1)
    res = t.to_language('He said, "The king sleeps."')
    assert res["sentences"][1]["text"].startswith("\u201c") and res["sentences"][1]["text"].endswith("\u201d")
    from conlang_forge.translate.printer import Printer
    P = Printer(V)
    d = parse(V, 'He said, "The king sleeps."')[0]
    assert parse(V, P.document(d))[0] == d


COMPARISONS = [
    "He is older than the king.", "The king is bigger than the dog.", "She is more beautiful than the queen.",
    "He is as old as the king.", "He is not as old as the king.", "He runs faster than the dog.", "He runs as fast as the dog.",
    "He is the biggest man.", "She is the most beautiful woman.", "He is less old than the king.", "He is the least old man.",
    "The old wizard is happier than I am.", "He is as old as I am.", "I see the oldest dog.", "He runs more quickly than the dog.",
]


def test_comparisons_are_read_as_degrees():
    V = tr(1).V
    cl = lambda t: parse(V, t)[0]["sentences"][0]["clauses"]
    iss = lambda t: [i for i in parse(V, t)[1] if i["level"] != "info"]
    c = cl("He is older than the king.")[0]
    assert c["predicate"] == {"adjective": "old", "degree": "comparative"} and c["pps"][0][0] == "than" and c["pps"][0][1]["head"] == "king"
    assert cl("He is more old than the king.") == cl("He is older than the king.")             # both spellings, one meaning
    assert cl("She is more beautiful than the queen.")[0]["predicate"]["degree"] == "comparative"
    assert cl("The king is bigger than the dog.")[0]["predicate"]["adjective"] == "big"           # spelling: bigg-er -> big
    c = cl("He is as old as the king.")[0]
    assert c["predicate"] == {"adjective": "old", "degree": "equative"} and c["pps"] == [["like", {"definite": True, "head": "king"}]] and c["equative"]
    assert cl("He is not as old as the king.")[0]["negated"]
    assert cl("He is the biggest man.")[0]["predicate"]["degrees"] == ["superlative"]
    assert cl("She is the most beautiful woman.")[0]["predicate"]["degrees"] == ["superlative"]
    assert cl("I see the oldest dog.")[0]["object"]["degrees"] == ["superlative"] and cl("I see the oldest dog.")[0]["object"]["adjectives"] == ["old"]
    assert cl("He is less old than the king.")[0]["predicate"]["degree"] == "less"
    assert cl("He is the least old man.")[0]["predicate"]["degrees"] == ["least"]
    c = cl("He runs faster than the dog.")[0]
    assert c["adverbs"] == ["more", "fast"] and c["pps"][0][0] == "than"
    assert cl("He runs more quickly than the dog.")[0]["adverbs"] == ["more", "quick" + "ly"] or cl("He runs more quickly than the dog.")[0]["adverbs"][0] == "more"
    # the repeated verb of the standard is left out
    assert cl("I am older than he is.")[0]["pps"][0][1]["head"] == "he" and not iss("I am older than he is.")
    assert cl("He is as old as I am.")[0]["pps"][0][1]["head"] == "i" and len(cl("He is as old as I am.")) == 1
    # words that merely look like comparatives, and words that are in the dictionary, are left alone
    assert cl("The better man sees the water.")[0]["subject"]["adjectives"] == ["better"] and "degrees" not in cl("The better man sees the water.")[0]["subject"]
    assert not iss("The wizard sees the number of the water.")
    assert cl("We have more bread.")[0]["object"]["head"] == "bread"


def test_comparisons_print_and_reparse_identically():
    t = tr(1)
    from conlang_forge.translate.printer import Printer
    P = Printer(t.V)
    for s in COMPARISONS:
        d, _ = parse(t.V, s)
        again, _ = parse(t.V, P.document(d))
        assert again == d, (s, P.document(d))
    assert P.document(parse(t.V, "He is more old than the king.")[0]) == "He is older than the king."
    assert P.document(parse(t.V, "She is more beautiful than the queen.")[0]) == "She is more beautiful than the queen."
    assert P.document(parse(t.V, "He is the happiest man.")[0]) == "He is the happiest man."
    assert P.document(parse(t.V, "He is as old as the king.")[0]) == "He is as old as the king."


def test_every_language_translates_comparisons_with_its_own_endings():
    for seed, pins in LANG_SPECS:
        t = tr(seed, pins)
        for s in COMPARISONS:
            res = t.to_language(s)
            bad = [i for i in res["issues"] if i["level"] in ("error", "warn")]
            assert res["text"] and not bad, (seed, s, bad)
        g = lambda s: res_gloss(t.to_language(s))
        assert "COMPAR" in g("He is older than the king.") and "than" in g("He is older than the king.")
        assert "SUPERL" in g("He is the biggest man.")
        assert "like" in g("He is as old as the king.") and "COMPAR" not in g("He is as old as the king.")
        assert "least" in g("He is the least old man.") and "less" in g("He is less old than the king.")
        assert "COMPAR" in g("He runs faster than the dog.") or "more" in g("He runs faster than the dog.")


def res_gloss(res):
    return " ".join(x["gloss"] for x in res["sentences"])


def test_a_language_built_before_least_says_so_instead_of_guessing():
    from conlang_forge.backend.conlangs import engine_generator as eg
    old = eg(DATA, "1.2")(1, {})
    t = LanguageTranslator(old[1])
    res = t.to_language("He is the least old man.")
    assert any(i["code"] in ("degree_unavailable", "word_dropped", "word_replaced", "kept_as_name") for i in res["issues"]), res["issues"]
    assert "COMPAR" in res_gloss(t.to_language("He is older than the king."))


def test_relative_clauses_describe_the_noun():
    V = tr(1).V
    c = parse(V, "The man who sleeps is old.")[0]["sentences"][0]["clauses"]
    assert len(c) == 1 and c[0]["predicate"] == {"adjective": "old"}
    rel = c[0]["subject"]["relative"]
    assert c[0]["subject"]["head"] == "man" and rel["gap"] == "subject" and rel["clause"]["verb"] == "sleep" and rel["clause"]["subject"] is None
    assert rel["clause"]["mood"] == "indicative"                      # not mistaken for a command
    rel = parse(V, "I see the dog that bit the king.")[0]["sentences"][0]["clauses"][0]["object"]["relative"]
    assert rel["gap"] == "subject" and rel["clause"]["tense"] == "past" and rel["clause"]["object"]["head"] == "king"
    rel = parse(V, "The dog that the queen sees sleeps.")[0]["sentences"][0]["clauses"][0]["subject"]["relative"]
    assert rel["gap"] == "object" and rel["clause"]["subject"]["head"] == "queen" and rel["clause"]["verb"] == "see"


def test_dependent_clauses_print_and_reparse_identically():
    t = tr(1)
    from conlang_forge.translate.printer import Printer
    P = Printer(t.V)
    for s in DEPENDENT:
        d, _ = parse(t.V, s)
        again, _ = parse(t.V, P.document(d))
        assert again == d, (s, P.document(d))
    assert P.document(parse(t.V, "When the king came, we left.")[0]) == "When the king came, we left."
    assert P.document(parse(t.V, "We left because the king came.")[0]) == "We left because the king came."


def test_every_language_translates_dependent_clauses():
    for seed, pins in LANG_SPECS:
        t = tr(seed, pins)
        for s in DEPENDENT:
            res = t.to_language(s)
            bad = [i for i in res["issues"] if i["level"] in ("error", "warn")]
            assert res["text"] and not bad, (seed, s, bad)
            glosses = res["sentences"][0]["glosses"]
            assert len(glosses) >= 3, (seed, s, glosses)
        one = t.to_language("I am afraid that my grandmother needs a bath.")["sentences"][0]
        stems = {part for g in one["glosses"] for part in g.split("-")}
        assert "that" in stems and "grandmother" in stems and "bath" in stems and "need" in stems, (seed, one["gloss"])


def test_dependent_clauses_read_back_in_the_other_direction():
    for seed, pins in LANG_SPECS[:4]:
        t = tr(seed, pins)
        for s, intro in [("I am afraid that my grandmother needs a bath.", "that"), ("We left because the king came.", "because")]:
            back = t.from_language(t.to_language(s)["text"])["doc"]["sentences"][0]
            assert [c.get("intro") for c in back["clauses"]] == [None, intro], (seed, s, back)


def test_unknown_words_inside_dependent_clauses_are_repaired_not_fatal():
    t = tr(1)
    res = t.to_language("The wizard who flurbs sleeps, and I fear that the glorbulous king sleeps.")
    assert res["text"] and not [i for i in res["issues"] if i["level"] == "error"]
    assert any(i["code"] in ("word_dropped", "kept_as_name", "word_replaced") for i in res["issues"])


def test_long_sentences_parse_quickly():
    import time
    t = tr(1)
    s = ("The old king who sleeps in the castle thinks that the young queen saw the big dog that bit the wizard, "
         "and the guards say that the dragon sleeps because the night is dark.")
    t0 = time.time()
    res = t.to_language(s)
    assert time.time() - t0 < 5 and res["text"]


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
