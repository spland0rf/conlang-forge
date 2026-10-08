"""Plain-letter spelling, the settings editor, tuning, the spelling view, and sample-text shaping."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pytest  # noqa: E402

from conlang_forge import exemplar as X  # noqa: E402
from conlang_forge import settings_schema as S  # noqa: E402
from conlang_forge.plain import fold, respell, with_script  # noqa: E402
from conlang_forge.spec import sample_spec  # noqa: E402
from test_api import make, signed_in  # noqa: E402

HAWAIIAN = ["Aloha kakahiaka, e ka hoa. Mahalo nui loa no ka wahine kanaka.",
            "Hale lani kai honu pua lei hula nene kapu ohana aina wai wiki malama.",
            "Kamaaina keiki waiwai mahina akua kupuna pono mele lahui moku"]


def _new(c, seed=5):
    r = c.post("/api/conlangs", {"name": "", "seed": seed, "pins": {}})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_every_spelling_is_plain_letters_and_unique():
    for seed in range(60):
        rom = sample_spec(seed).orthography.romanization
        assert all(v.isascii() and v.isalpha() for v in rom.values()), (seed, rom)
        assert len(set(rom.values())) == len(rom)


def test_typed_special_letters_fold_to_plain():
    assert fold("Šöre ñandú") == "Soere nandu" and fold("kaŋ þa") == "kang tha"


def test_old_accented_languages_are_respelled_without_changing_sounds():
    from conlang_forge.backend.conlangs import engine_generator
    gen = engine_generator(str(Path(__file__).resolve().parents[1] / "data"))
    _, lang = gen(5, {"phonology.vowels": ["a", "e", "i", "o", "u", "ø"], "phonology.consonants": list("ptkmnsl") + ["ʃ", "ŋ"]})
    phon = [e["phonemes"] for e in lang["lexicon"]]
    plain_forms = [e["form"] for e in lang["lexicon"]]
    old = {p: {"ø": "ö", "ʃ": "š", "ŋ": "ŋ"}.get(p, s) for p, s in lang["spec"]["orthography"]["romanization"].items()}
    lang["spec"]["orthography"]["romanization"] = old
    for e in lang["lexicon"]:
        e["form"] = "".join(old[p] for p in e["phonemes"])
    assert respell(lang) is True
    assert [e["form"] for e in lang["lexicon"]] == plain_forms and [e["phonemes"] for e in lang["lexicon"]] == phon
    assert respell(lang) is False


def test_special_letters_are_only_a_view():
    from conlang_forge.backend.conlangs import engine_generator
    gen = engine_generator(str(Path(__file__).resolve().parents[1] / "data"))
    _, lang = gen(5, {"phonology.vowels": ["a", "e", "i", "o", "u", "ø"]})
    sp = with_script(lang, "special")
    assert sp is not lang and [e["phonemes"] for e in sp["lexicon"]] == [e["phonemes"] for e in lang["lexicon"]]
    assert any(not e["form"].isascii() for e in sp["lexicon"]) and all(e["form"].isascii() for e in lang["lexicon"])
    assert with_script(lang, "plain") is lang


def test_default_odds_leave_languages_unchanged_and_tuning_changes_them():
    base = sample_spec(11, {}).to_dict()
    assert sample_spec(11, {}, {}).to_dict() == base
    t = {"odds": {"syntax.word_order": {"SOV": 0, "SVO": 0, "VSO": 1, "VOS": 0, "OVS": 0, "OSV": 0}}, "rates": {"syntax.pro_drop": 1.0}}
    sp = sample_spec(11, {}, t)
    assert sp.syntax.word_order == "VSO" and sp.syntax.pro_drop is True and sp.tuning == t


def test_pins_round_trip_from_a_spec():
    sp = sample_spec(3, {"morphology.typology": "isolating", "phonology.max_cluster": 3})
    pins = S.pins_of(sp)
    assert pins["morphology.typology"] == "isolating" and pins["phonology.max_cluster"] == 3
    assert sample_spec(3, pins).to_dict() == sp.to_dict()


def test_schema_describes_every_setting_with_odds():
    d = S.describe(sample_spec(5))
    keys = {s["key"] for s in d["settings"]}
    assert {"phonology.consonants", "phonology.vowel_weights", "syntax.word_order", "gen.tiny_word_leak"} <= keys
    wo = next(s for s in d["settings"] if s["key"] == "syntax.word_order")
    assert len(wo["odds"]) == 6 and all(o["weight"] > 0 for o in wo["odds"]) and wo["pinned"] is False
    assert next(s for s in d["settings"] if s["key"] == "syntax.pro_drop")["chance"]["default"] in (.5, .8)


def test_bad_edits_get_friendly_errors():
    sp = sample_spec(5)
    for pins in ({"phonology.consonants": ["p", "t"]}, {"morphology.typology": "banana"}, {"nope": 1},
                 {"phonology.consonants": ["p", "t", "k", "m", "n", "s"], "phonology.vowels": ["a", "i"], "phonology.syllable_complexity": 1}):
        with pytest.raises(Exception) as e:
            S.build_spec(5, S.normalize(pins, sp), {})
        assert "message" in dir(e.value) or str(e.value)
    with pytest.raises(Exception):
        S.clean_tuning({"gen": {"max_root_syllables": 99}})
    with pytest.raises(Exception):
        S.clean_tuning({"rates": {"syntax.word_order": .5}})


def test_normalize_repairs_dependent_settings():
    sp = sample_spec(5)
    n = S.normalize({"phonology.consonants": list("ptkmnsl"), "phonology.consonant_weights": {"p": 1, "t": 1, "z": 5},
                     "morphology.case_alignment": "ergative-absolutive", "morphology.cases": ["nominative", "accusative", "genitive"]}, sp)
    assert set(n["phonology.consonant_weights"]) == set("ptkmnsl") and abs(sum(n["phonology.consonant_weights"].values()) - 1) < 1e-3
    assert n["morphology.cases"] == ["ergative", "absolutive", "genitive"]


def test_apply_with_no_changes_is_the_same_language_and_edits_rebuild():
    be, c = make()
    signed_in(c, be)
    cid = _new(c)
    before = c.get(f"/api/conlangs/{cid}").json()["profile"]
    assert c.post(f"/api/conlangs/{cid}/settings/preview", {"set": {}}).json()["same"] is True
    assert c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {}}).status_code == 200
    assert c.get(f"/api/conlangs/{cid}").json()["profile"] == before
    pre = c.post(f"/api/conlangs/{cid}/settings/preview", {"set": {"syntax.word_order": "VSO"}}).json()
    assert any(ch["key"] == "syntax.word_order" and ch["after"].startswith("VSO") for ch in pre["changes"])
    r = c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"syntax.word_order": "VSO"}, "tuning": {"gen": {"tiny_word_leak": .2}}})
    assert r.status_code == 200 and r.json()["profile"]["grammar"]["word_order"] == "VSO"
    s = c.get(f"/api/conlangs/{cid}/settings").json()
    wo = next(x for x in s["settings"] if x["key"] == "syntax.word_order")
    assert wo["pinned"] is True and wo["value"] == "VSO" and s["tuning"]["gen"]["tiny_word_leak"] == .2
    # unpin goes back to random (the seed's own choice)
    r = c.post(f"/api/conlangs/{cid}/settings/apply", {"unpin": ["syntax.word_order"]})
    assert r.status_code == 200
    assert next(x for x in c.get(f"/api/conlangs/{cid}/settings").json()["settings"] if x["key"] == "syntax.word_order")["pinned"] is False


def test_copy_keeps_the_original_and_errors_are_422():
    be, c = make()
    signed_in(c, be)
    cid = _new(c)
    r = c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"syntax.word_order": "OSV"}, "mode": "copy"})
    assert r.status_code == 200 and r.json()["id"] != cid and r.json()["profile"]["grammar"]["word_order"] == "OSV"
    assert c.get(f"/api/conlangs/{cid}").json()["profile"]["grammar"]["word_order"] != "OSV"
    bad = c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"phonology.consonants": ["p", "t", "k", "m", "n", "s"],
                 "phonology.vowels": ["a", "i"], "phonology.syllable_complexity": 1}})
    assert bad.status_code == 422 and "vowels" in bad.json()["message"]
    assert c.get(f"/api/conlangs/{cid}").status_code == 200           # still intact


def test_other_users_cannot_edit_settings():
    be, c = make()
    signed_in(c, be)
    cid = _new(c)
    be2, _ = None, None
    from asgi_client import Client
    c2 = Client(c.app)
    c2.token = c2.post("/api/auth/register", {"email": "o@x.org", "password": "Correct-Horse-9"}, token=None).json()["access_token"]
    assert c2.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"syntax.word_order": "VSO"}}).status_code in (403, 404)
    assert c2.get(f"/api/conlangs/{cid}/settings").status_code in (403, 404)


def test_script_view_over_http():
    be, c = make()
    signed_in(c, be)
    cid = _new(c)
    assert c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"phonology.vowels": ["a", "e", "i", "o", "u", "ø"],
                  "phonology.vowel_weights": {"a": .3, "e": .2, "i": .2, "o": .1, "u": .1, "ø": .1}}}).status_code == 200
    plain = c.post(f"/api/conlangs/{cid}/translate", {"direction": "to", "text": "the man sees the dog", "mode": "restricted"}).json()["text"]
    special = c.post(f"/api/conlangs/{cid}/translate", {"direction": "to", "text": "the man sees the dog", "mode": "restricted", "script": "special"}).json()["text"]
    assert plain.isascii() and special != plain and special.replace("ö", "oeh").replace("š", "sh").lower() == plain.lower()
    back = c.post(f"/api/conlangs/{cid}/translate", {"direction": "from", "text": special}).json()
    assert back["re_text"] == "Man sees dog."          # typed special letters are understood
    assert c.get(f"/api/conlangs/{cid}?script=bogus").status_code == 422


# ---------------------------------------------------------------------------------------------------- sample text
def test_sounds_are_read_back_from_spelling():
    assert X.to_phonemes("chasha") == ["tʃ", "a", "ʃ", "a"] and X.to_phonemes("kang") == ["k", "a", "ŋ"]
    assert X.to_phonemes("Šöre") == ["ʃ", "ø", "r", "e"] and X.to_phonemes("caesar")[0] == "k"
    sy = X.syllabify(X.to_phonemes("pantra"))
    assert [X.template_of(s) for s in sy] == ["CVC", "CCV"]


def test_sample_proposals_match_the_sample_and_flag_fixed_settings():
    sp = sample_spec(5, {"phonology.max_cluster": 3, "phonology.allow_hiatus": False})
    rep = X.PhonologyReport(HAWAIIAN)
    props = {p["key"]: p for p in X.phonology_proposals(sp, rep)}
    assert props["phonology.vowels"]["proposed"] == ["a", "e", "i", "o", "u"]
    assert props["phonology.max_cluster"]["kind"] == "conflict" and props["phonology.max_cluster"]["proposed"] == 1
    assert props["phonology.allow_hiatus"]["proposed"] is True
    top = max(props["phonology.consonant_weights"]["proposed"].items(), key=lambda kv: kv[1])[0]
    assert top == "k"
    assert X.phonology_proposals(sp, X.PhonologyReport(["ka"])) == []          # too little text to judge


def test_grammar_reader_output_is_validated():
    sp = sample_spec(5, {"syntax.word_order": "SVO"})
    good = '{"settings":[{"key":"syntax.word_order","value":"SOV","confidence":"high","evidence":"verbs come last"},' \
           '{"key":"syntax.word_order","value":"XYZ"},{"key":"phonology.consonants","value":["p"]},{"key":"syntax.adposition","value":"nonsense"}]}'
    out = X.parse_grammar("Here: " + good, sp)
    assert [(p["key"], p["proposed"], p["kind"]) for p in out] == [("syntax.word_order", "SOV", "conflict")]
    assert X.parse_grammar("no json", sp) == []


def test_analyze_endpoint_and_applying_proposals_shapes_the_language():
    be, c = make()
    signed_in(c, be)
    cid = _new(c)
    r = c.post(f"/api/conlangs/{cid}/exemplars/analyze", {"texts": HAWAIIAN, "use_model": False})
    assert r.status_code == 200
    props = r.json()["proposals"]
    assert props and r.json()["summary"]["words"] > 30
    assert c.post(f"/api/conlangs/{cid}/exemplars/analyze", {"texts": []}).status_code == 422
    chosen = {p["key"]: p["proposed"] for p in props}
    assert c.put(f"/api/conlangs/{cid}/exemplars", {"texts": HAWAIIAN}).status_code == 200
    assert c.post(f"/api/conlangs/{cid}/settings/apply", {"set": chosen}).status_code == 200
    again = c.post(f"/api/conlangs/{cid}/exemplars/analyze", {"texts": HAWAIIAN, "use_model": False}).json()["proposals"]
    assert [p["key"] for p in again if p["key"] in ("phonology.vowels", "phonology.max_cluster", "phonology.syllable_templates")] == []
    s = c.get(f"/api/conlangs/{cid}/settings").json()
    assert s["exemplars"][0].startswith("Aloha")
    voc = next(x for x in s["settings"] if x["key"] == "phonology.vowels")["value"]
    assert voc == ["a", "e", "i", "o", "u"]


def test_analyze_uses_the_model_for_grammar_when_available():
    be, c = make()
    signed_in(c, be)
    cid = _new(c)
    reply = '{"settings":[{"key":"syntax.word_order","value":"VSO","confidence":"medium","evidence":"verb comes first"}]}'
    be.provider.reply = lambda req: reply
    r = c.post(f"/api/conlangs/{cid}/exemplars/analyze", {"texts": HAWAIIAN})
    assert r.status_code == 200 and r.json()["usage"] is not None
    assert any(p["key"] == "syntax.word_order" and p["proposed"] == "VSO" and p["source"] == "model" for p in r.json()["proposals"]) \
        or sample_spec(5).syntax.word_order == "VSO"


def test_new_language_from_sample_keeps_user_settings_and_infers_the_rest():
    be, c = make()
    signed_in(c, be)
    r = c.post("/api/conlangs/from-sample", {"texts": HAWAIIAN, "use_model": False, "seed": 7,
                                             "pins": {"phonology.stress": "final", "morphology.typology": "agglutinative"}})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["shaped"]["applied"] and d["shaped"]["summary"]["words"] > 30
    s = c.get(f"/api/conlangs/{d['id']}/settings").json()
    val = {x["key"]: x for x in s["settings"]}
    assert val["phonology.vowels"]["value"] == ["a", "e", "i", "o", "u"] and val["phonology.vowels"]["pinned"]
    assert set(val["phonology.consonants"]["value"]) >= set("kmnhlwp") and val["phonology.max_cluster"]["value"] == 1
    assert val["phonology.stress"]["value"] == "final" and val["morphology.typology"]["value"] == "agglutinative"
    assert val["syntax.word_order"]["pinned"] is False          # nothing in the sample implied it: left to chance
    assert s["exemplars"][0].startswith("Aloha")
    # same seed without a sample gives the same random choices for everything the sample did not decide
    plain = c.post("/api/conlangs", {"name": "", "seed": 7, "pins": {}}).json()["id"]
    p = {x["key"]: x for x in c.get(f"/api/conlangs/{plain}/settings").json()["settings"]}
    assert p["syntax.word_order"]["value"] == val["syntax.word_order"]["value"]


def test_from_sample_conflicts_with_user_settings_are_reported_not_applied():
    be, c = make()
    signed_in(c, be)
    r = c.post("/api/conlangs/from-sample", {"texts": HAWAIIAN, "use_model": False, "seed": 3, "pins": {"morphology.numeral_base": 12}})
    assert r.status_code == 200
    assert c.post("/api/conlangs/from-sample", {"texts": [], "use_model": False}).status_code == 422
    r2 = c.post("/api/conlangs/from-sample", {"texts": ["ka"], "use_model": False, "seed": 3})      # too little to judge: all random
    assert r2.status_code == 200 and r2.json()["shaped"]["applied"] == []


# ---------------------------------------------------------------------------------------------------- counts and complex consonants
def test_counts_are_exact_and_separate_from_complex_consonants():
    sp = sample_spec(5, {"phonology.consonant_count": 11, "phonology.vowel_count": 4, "phonology.complex_count": 3})
    ph = sp.phonology
    assert len([c for c in ph.consonants if c not in ph.complex_consonants]) == 11 and len(ph.vowels) == 4 and len(ph.complex_consonants) == 3
    assert S.spec_value(sp, "phonology.consonant_count") == 11 and S.spec_value(sp, "phonology.complex_count") == 3
    # all sounds that make a unit are still ordinary sounds on their own, with their own letter for the unit
    rom = sp.orthography.romanization
    assert all(u in rom and len(rom[u]) >= 2 for u in ph.complex_consonants)
    assert sample_spec(5, S.pins_of(sp)).to_dict() == sp.to_dict()


def test_complex_consonants_default_to_random_and_old_languages_have_none():
    counts = [len(sample_spec(s).phonology.complex_consonants) for s in range(60)]
    assert 0 < sum(1 for n in counts if n) < 40 and max(counts) <= 8
    old = sample_spec(9, {"phonology.complex_count": 0}).to_dict()
    old["phonology"].pop("complex_consonants"); old["provenance"].pop("phonology.complex_consonants")
    from conlang_forge.spec import LanguageSpec
    spec = LanguageSpec.from_dict(old)
    assert S.pins_of(spec)["phonology.complex_consonants"] == [] and spec.phonology.complex_consonants == []
    assert sample_spec(9, S.pins_of(spec)).phonology.consonants == spec.phonology.consonants


def test_minimum_inventory_is_computed_from_the_other_settings():
    cv = {"CV": 1.0}
    rich = {"CV": .5, "CVC": .3, "V": .1, "VC": .1}
    assert S.min_consonants(3, cv) > S.min_consonants(3, rich) >= 4
    assert S.min_vowels(9, cv) == S.MIN_VOWELS and S.min_vowels(4, cv) > S.MIN_VOWELS
    assert S.min_consonants(3, cv, units=2) < S.min_consonants(3, cv)
    sp = sample_spec(5, {"phonology.syllable_complexity": 1})
    m = S.describe(sp)["minimums"]
    assert m["consonants"]["5"] == S.min_consonants(5, sp.phonology.syllable_templates, len(sp.phonology.complex_consonants))
    with pytest.raises(Exception) as e:
        S.build_spec(5, S.normalize({"phonology.consonant_count": 4, "phonology.vowel_count": 3, "phonology.syllable_complexity": 1,
                                     "phonology.complex_count": 0}), {})
    assert "at least" in str(getattr(e.value, "message", e.value))


def test_count_edits_free_the_exact_lists_and_lists_override_counts():
    be, c = make()
    signed_in(c, be)
    cid = _new(c)
    r = c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"phonology.consonants": list("ptkmnslr"), "phonology.vowels": ["a", "e", "i", "o", "u"]}})
    assert r.status_code == 200
    r = c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"phonology.consonant_count": 12, "phonology.complex_count": 2}})
    assert r.status_code == 200, r.text
    v = {x["key"]: x for x in c.get(f"/api/conlangs/{cid}/settings").json()["settings"]}
    assert len(v["phonology.consonants"]["value"]) == 12 and len(v["phonology.complex_consonants"]["value"]) == 2
    assert v["phonology.vowels"]["value"] == ["a", "e", "i", "o", "u"]               # untouched
    assert v["phonology.consonant_count"]["pinned"] and not v["phonology.consonants"]["pinned"]
    r = c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"phonology.complex_consonants": ["ts", "kp"]}})
    assert r.status_code == 200
    v = {x["key"]: x for x in c.get(f"/api/conlangs/{cid}/settings").json()["settings"]}
    assert v["phonology.complex_consonants"]["value"] == ["ts", "kp"] and v["phonology.complex_count"]["value"] == 2


def test_a_language_with_complex_consonants_builds_and_translates():
    be, c = make()
    signed_in(c, be)
    cid = _new(c)
    r = c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"phonology.complex_consonants": ["ts", "tɬ", "kp"], "phonology.consonant_count": 14}})
    assert r.status_code == 200, r.text
    d = c.get(f"/api/conlangs/{cid}/dictionary.json").json()
    assert any("ts" in e["form"] or "tl" in e["form"] or "kp" in e["form"] for e in d["entries"])
    assert c.get(f"/api/conlangs/{cid}/dictionary.md").status_code == 200 and c.get(f"/api/conlangs/{cid}/grammar-book.md").status_code == 200
    out = c.post(f"/api/conlangs/{cid}/translate", {"direction": "to", "text": "the man sees the dog", "mode": "restricted"}).json()
    back = c.post(f"/api/conlangs/{cid}/translate", {"direction": "from", "text": out["text"]}).json()
    assert back["re_text"].lower().replace("the ", "").startswith("man sees dog")


def test_sample_text_units_are_read_as_one_consonant():
    assert X.to_phonemes("tsatsa") == ["ts", "a", "ts", "a"] and X.to_phonemes("tzar")[0] == "ts"
    assert X.to_phonemes("tlatoa")[0] == "tɬ" and "tɬ" not in X.to_phonemes("atlas")      # tl only starts a unit at a word start
    assert X.to_phonemes("kpako")[0] == "kp" and X.to_phonemes("rzhava")[0] == "rʒ"
    rep = X.PhonologyReport(["tsatsa tsiko katsu tlatoa tlaco matsi pfala kpaka tsana tsuma", "tlali tlapa tsetse"])
    sp = sample_spec(5, {"phonology.complex_count": 0})
    props = {p["key"]: p for p in X.phonology_proposals(sp, rep, fresh=True)}
    assert {"ts", "tɬ"} <= set(props["phonology.complex_consonants"]["proposed"])
    assert not set(props["phonology.consonants"]["proposed"]) & {"ts", "tɬ"}


def test_tb_tbl_zl_are_units_at_both_ends_of_a_word():
    from conlang_forge.inventory import UNITS, romanization_map
    assert {"tb", "tbl", "zl"} <= set(UNITS)
    assert X.to_phonemes("tbalo")[:2] == ["tb", "a"] and X.to_phonemes("tblaki")[:2] == ["tbl", "a"]   # longest match wins
    assert X.to_phonemes("zlato")[0] == "zl" and X.to_phonemes("katb")[-1] == "tb" and X.to_phonemes("kotbl")[-1] == "tbl"
    assert X.to_phonemes("kazl")[-1] == "zl" and X.to_phonemes("nd")[0] == "nd" and X.to_phonemes("kand")[-1] == "nd"
    assert X.to_phonemes("kanda") == ["k", "a", "n", "d", "a"]            # mid-word legal pair stays a cluster
    assert X.to_phonemes("katbo") == ["k", "a", "tb", "o"]                # mid-word, not a legal cluster: a unit
    rom = romanization_map("plain", ["t", "b", "l", "z", "tb", "tbl", "zl"], ["a"])
    assert rom["tb"] in ("tb", "tbh") and rom["tbl"] in ("tbl", "tbhl") and rom["zl"] in ("zl", "zlh")
    sp = sample_spec(5, {"phonology.complex_consonants": ["tb", "tbl", "zl"], "phonology.consonant_count": 15})
    assert sp.phonology.complex_consonants == ["tb", "tbl", "zl"]
