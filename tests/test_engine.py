import copy
import json
from pathlib import Path

import pytest

from conlang_forge.lexicon import build_lexicon, extend_lexicon
from conlang_forge.spec import LanguageSpec, sample_spec, validate_spec
from conlang_forge.vocab import build_vocab, diff_vocab

ROOT = Path(__file__).resolve().parents[1]
VOCAB = build_vocab(ROOT / "data/source/words_v1.0.csv", ROOT / "data/vocab/v1.0.manifest.json")
IDS = {e["concept_id"] for e in VOCAB["entries"]}
SEEDS = range(1, 21)


def test_vocab_cleanup():
    assert len(VOCAB["entries"]) == 2000
    for w in ("duke", "explanation", "failure", "success", "true", "false", "sorcerer", "seek", "tavern", "orc", "goblin"):
        assert w in IDS, w
    for bad in ("est", "sorceror", "fals e", "tru e", "seek(ing)"):
        assert bad not in IDS
    assert {"case#court", "case#medical"} <= IDS
    assert not any("\u200b" in c for c in IDS)
    assert VOCAB["report"]["needs_review"] == []


def test_spec_valid_and_roundtrips():
    for seed in SEEDS:
        spec = sample_spec(seed)
        assert validate_spec(spec) == []
        assert LanguageSpec.from_dict(json.loads(json.dumps(spec.to_dict()))) == spec


def test_deterministic():
    a, b = sample_spec(7), sample_spec(7)
    assert a == b
    assert build_lexicon(a, VOCAB) == build_lexicon(b, VOCAB)


def test_pinning_does_not_reshuffle_other_fields():
    base = sample_spec(11)
    pinned = sample_spec(11, {"syntax.word_order": "VSO"})
    assert pinned.syntax.word_order == "VSO" and pinned.provenance["syntax.word_order"] == "pinned"
    assert pinned.phonology == base.phonology and pinned.morphology == base.morphology
    with pytest.raises(ValueError):
        sample_spec(11, {"syntax.word_order": "XYZ"})
    with pytest.raises(ValueError):
        sample_spec(11, {"not.a.key": 1})


def test_unique_forms_and_phonotactics():
    for seed in SEEDS:
        spec = sample_spec(seed)
        lex = build_lexicon(spec, VOCAB)
        assert len(lex) == 2000
        assert len({e["form"] for e in lex}) == 2000
        ph = spec.phonology
        vowels, cons = set(ph.vowels), set(ph.consonants)
        for e in lex:
            flat = [p for s in e["syllables"] for p in s]
            assert set(flat) <= vowels | cons
            assert all(any(p in vowels for p in s) for s in e["syllables"])


def test_function_words_shorter_on_average():
    spec = sample_spec(5)
    lex = build_lexicon(spec, VOCAB)
    f = [len(e["syllables"]) for e in lex if e["is_function"]]
    c = [len(e["syllables"]) for e in lex if not e["is_function"]]
    assert sum(f) / len(f) < sum(c) / len(c)


def test_pinned_inventory_is_respected():
    pins = {"phonology.consonants": ["p", "t", "k", "m", "n", "s", "l"], "phonology.vowels": ["a", "i", "u"]}
    spec = sample_spec(3, pins)
    assert validate_spec(spec) == []
    lex = build_lexicon(spec, VOCAB)
    used = {p for e in lex for s in e["syllables"] for p in s}
    assert used <= set(pins["phonology.consonants"]) | set(pins["phonology.vowels"])


def _subset(vocab, drop):
    v = copy.deepcopy(vocab)
    v["version"] = "0.9"
    v["entries"] = [e for e in v["entries"] if e["concept_id"] not in drop]
    return v


def test_upgrade_never_changes_existing_words():
    old_drop = {"tavern", "orc", "goblin", "duke"} | {e["concept_id"] for e in VOCAB["entries"][::40]}
    old = _subset(VOCAB, old_drop)
    for seed in (1, 2, 3):
        spec = sample_spec(seed)
        lex_old = build_lexicon(spec, old)
        lex_new, rep = extend_lexicon(spec, lex_old, VOCAB)
        assert set(rep["added"]) == old_drop and not rep["retired"]
        by_id = {e["concept_id"]: e for e in lex_new}
        for e in lex_old:
            assert by_id[e["concept_id"]] == e
        assert len({e["form"] for e in lex_new}) == len(lex_new) == 2000


def test_upgrade_retires_removed_words_without_deleting():
    spec = sample_spec(2)
    lex = build_lexicon(spec, VOCAB)
    smaller = _subset(VOCAB, {"duke", "success"})
    lex2, rep = extend_lexicon(spec, lex, smaller)
    assert sorted(rep["retired"]) == ["duke", "success"] and len(lex2) == 2000
    assert {e["concept_id"] for e in lex2 if e["retired"]} == {"duke", "success"}
    lex3, rep3 = extend_lexicon(spec, lex2, VOCAB)  # bringing them back un-retires, same words
    assert sorted(rep3["unretired"]) == ["duke", "success"] and rep3["added"] == []
    assert lex3 == lex


def test_alias_rename_keeps_word():
    spec = sample_spec(4)
    lex = build_lexicon(spec, VOCAB)
    renamed = copy.deepcopy(VOCAB)
    renamed["version"] = "1.1"
    renamed["aliases"] = {"sorcerer": "sorceress"}
    for e in renamed["entries"]:
        if e["concept_id"] == "sorcerer":
            e.update(concept_id="sorceress", lemma="sorceress", gloss="sorceress")
    old_form = next(e["form"] for e in lex if e["concept_id"] == "sorcerer")
    lex2, rep = extend_lexicon(spec, lex, renamed)
    assert rep["added"] == [] and rep["retired"] == []
    assert next(e["form"] for e in lex2 if e["concept_id"] == "sorceress") == old_form


def test_diff_vocab():
    d = diff_vocab(_subset(VOCAB, set()), _subset(VOCAB, {"duke"}))
    assert d["removed"] == ["duke"] and d["added"] == []


def test_small_inventories_do_not_get_heavy_clusters():
    for seed in range(1, 60):
        spec = sample_spec(seed, {"phonology.consonants": ["p", "t", "k", "m", "n", "s", "l", "r"]})
        assert spec.phonology.syllable_complexity <= 3


# ---------------- root map ----------------
from conlang_forge.roots import FAMILY_MAX, FAMILY_TARGET, RootMapError, parse_roots  # noqa: E402

ROOTS_TXT = (ROOT / "data/roots/v1.0.roots.txt").read_text(encoding="utf-8")


def test_rootmap_valid_and_capped():
    rm = parse_roots(ROOTS_TXT, VOCAB)
    assert FAMILY_TARGET == 5 and FAMILY_MAX == 6
    assert rm["stats"]["largest_family"] <= 6
    assert all(len(v) <= 6 for v in rm["families"].values())
    assert all(len(rm["families"][f]) == 6 for f in rm["stats"]["families_of_max"])   # any 6-root family is flagged for review
    assert len(rm["stats"]["families_of_max"]) <= 5
    assert 600 <= rm["stats"]["root_groups"] <= 1200
    for w in ("environmental", "everybody", "everyone", "queen", "woman"):
        assert w in rm["recipes"]


def test_cap_applies_only_to_families():
    rm = parse_roots(ROOTS_TXT, VOCAB)
    assert rm["stats"]["derived"] > 10 and rm["stats"]["compounds"] > 10  # uncapped kinds exist in bulk
    big = ROOTS_TXT + "\nfamily toobig: " + " ".join(["dog", "cat", "pig", "cow", "hen", "fox", "bear"]) + "\n"   # 7 roots
    with pytest.raises(RootMapError):
        parse_roots(big, VOCAB)


def test_sibling_groups_reference_real_families():
    rm = parse_roots(ROOTS_TXT, VOCAB)
    assert len(rm["sibling_groups"]) >= 50
    for fams in rm["sibling_groups"].values():
        assert len(fams) >= 2 and all(f in rm["families"] for f in fams)
    with pytest.raises(RootMapError):
        parse_roots(ROOTS_TXT + "\nsiblings bogus: nosuch1 nosuch2\n", VOCAB)


def test_owner_examples_for_splitting_families():
    rm = parse_roots(ROOTS_TXT, VOCAB)
    F, RF, SG = rm["families"], rm["root_family"], rm["sibling_groups"]
    together = lambda *ws: len({RF.get(w, w) for w in ws}) == 1
    apart = lambda a, b: RF.get(a, a) != RF.get(b, b)
    sibs = lambda a, b: any(RF[a] in g and RF[b] in g for g in SG.values())
    # 1) dwellings: single-family homes vs larger buildings; tent and barn are outliers
    assert together("house", "home", "cottage", "hut", "apartment") and together("manor", "hotel", "inn")
    assert apart("house", "manor") and sibs("house", "manor") and "tent" not in RF and "barn" not in RF
    # 2) officials: sole rulers vs professional representatives
    assert together("president", "mayor", "chief", "dictator") and together("minister", "ambassador", "delegate", "judge", "jury")
    assert sibs("mayor", "judge")
    # 3) limbs: hand parts, foot parts, joints, limbs
    assert together("hand", "finger", "thumb", "palm") and together("foot", "toe") and together("shoulder", "knee")
    assert together("arm", "leg") and apart("arm", "hand") and sibs("hand", "foot") and sibs("arm", "knee")
    # 4) wing joins the limbs; lizard / spider / insect leave the birds
    assert together("bird", "feather", "hen", "chicken", "duck") and together("lizard", "spider", "insect")
    assert together("wing", "arm") and apart("bird", "lizard") and sibs("bird", "lizard")
    # 5) overland terrain vs holes in the ground
    assert together("mountain", "hill", "valley", "canyon") and together("chasm", "abyss", "pit")
    assert together("cave", "tunnel", "hole") and apart("hill", "cave") and sibs("hill", "cave") and sibs("cave", "pit")


def test_owner_corrections_round():
    rm = parse_roots(ROOTS_TXT, VOCAB)
    F, RF = rm["families"], rm["root_family"]
    assert RF["white"] == "color" and RF["empire"] == "realm" and "empire" not in F["regalia"]
    assert [RF[w] for w in ("winter", "south", "west")] == ["season", "compass", "compass"]
    for w in ("white", "winter", "south", "west"):
        assert w not in rm["recipes"]               # parallel terms, not derived opposites
    assert set(rm["pending"]) == {"purple", "wrist", "ankle", "elbow", "hip", "halfling", "fairy"}
    assert RF["purple"] == "cool" and RF["wrist"] == "hand" and RF["ankle"] == "foot"
    assert RF["elbow"] == RF["hip"] == "joint" and RF["halfling"] == RF["fairy"] == "humanoid"
    for w, base in (("sister", "brother"), ("aunt", "uncle"), ("wife", "husband"), ("daughter", "son")):
        assert rm["recipes"][w]["rel"] == "FEMALE" and RF[base] in ("relative", "offspring")
    with pytest.raises(RootMapError):                # a typo in a normal member is still an error
        parse_roots(ROOTS_TXT + "\nfamily oops: dog purpel\n", VOCAB)


def test_planned_words_join_their_family_when_the_vocabulary_grows():
    spec, state, _ = _lang(1)
    assert not any(e["concept_id"] in ("purple", "wrist", "fairy") for e in state["entries"])   # not in vocab: no entry
    bigger = copy.deepcopy(VOCAB)
    bigger["version"] = "1.1"
    for w in ("purple", "wrist", "ankle", "elbow", "hip", "halfling", "fairy"):
        bigger["entries"].append({"concept_id": w, "lemma": w, "sense": None, "gloss": w, "is_function": False, "tags": []})
    new_state, rep = extend(spec, bigger, RM, state, FREQ)
    assert set(rep["added"]) == {"purple", "wrist", "ankle", "elbow", "hip", "halfling", "fairy"} and not rep["retired"]
    old = {e["concept_id"]: e for e in state["entries"]}
    new = {e["concept_id"]: e for e in new_state["entries"]}
    assert all(new[c] == e for c, e in old.items())                       # nothing existing changed
    for w, fam in (("purple", "cool"), ("wrist", "hand"), ("ankle", "foot"), ("elbow", "joint"), ("fairy", "humanoid")):
        if fam in new_state["stems"]:
            assert new[w]["family"] == fam
    assert pdist(new["wrist"]["phonemes"], new["hand"]["phonemes"]) >= MIN_DIST
    assert verify(spec, RM, new_state)["duplicate_forms"] == 0


def test_every_old_family_member_is_still_placed():
    """Splitting must not lose roots: everything the 10-cap map had in a family is still in one,
    except the owner-chosen outliers, which are free roots."""
    rm = parse_roots(ROOTS_TXT, VOCAB)
    for w in ("tent", "barn", "parade"):
        assert w not in rm["root_family"] and w not in rm["recipes"]
    assert rm["stats"]["roots_in_families"] >= 670


def test_rootmap_rejects_bad_input():
    for bad in ("\nzzz = king +FEMALE\n", "\nqueen = king +NOPE\n", "\ntree = tree +ADJ\n"):
        with pytest.raises(RootMapError):
            parse_roots(ROOTS_TXT + bad, VOCAB)


# ---------------- root-based generation ----------------
from conlang_forge.morph import apply_relation  # noqa: E402
from conlang_forge.phonetics import MIN_DIST, NearIndex, pdist, sub_cost  # noqa: E402
from conlang_forge.inventory import CONSONANTS as _CONS, VOWELS as _VOWS  # noqa: E402
from conlang_forge.rootgen import build_language, extend, verify  # noqa: E402
from conlang_forge.roots import adapt_rootmap, parse_roots as _parse  # noqa: E402

RM = _parse(ROOTS_TXT, VOCAB)
from conlang_forge.frequency import build_freq, commonness  # noqa: E402
from conlang_forge.plan import apply_plan, make_plan  # noqa: E402
FREQ = build_freq(ROOT / "data/source/ngsl_1.2_stats.csv", VOCAB,
                  [ROOT / f"data/source/{n}.csv" for n in ("top_100_english_nouns", "top_100_english_verbs", "top_100_ngsl_adjectives")])
_CACHE = {}


def _realised(spec, state):
    """The root map as this language realises it (gender view + stored plan)."""
    return apply_plan(adapt_rootmap(RM, spec.morphology.gender_base), state["plan"])


def _lang(seed, pins=None):
    key = (seed, json.dumps(pins, sort_keys=True))
    if key not in _CACHE:
        spec = sample_spec(seed, pins)
        _CACHE[key] = (spec, *build_language(spec, VOCAB, RM, FREQ))
    return _CACHE[key]


def test_phonetics_tables_cover_inventory():
    from conlang_forge.phonetics import _CONS as PC, _VOW as PV
    assert set(_CONS) <= set(PC) and set(_VOWS) <= set(PV)
    assert sub_cost("p", "b") < MIN_DIST and sub_cost("e", "i") < MIN_DIST   # too alike to rely on
    assert sub_cost("p", "t") >= MIN_DIST and sub_cost("a", "i") >= MIN_DIST
    assert pdist("kat", "kat") == 0 and pdist("kat", "kata") == 1.0
    idx = NearIndex()
    idx.add(["p", "a"])
    assert idx.near(["b", "a"]) and not idx.near(["t", "a"]) and not idx.near(["p", "a", "t"])


def test_rootgen_quality_all_typologies():
    cases = [(1, None), (3, None), (11, {"morphology.typology": "isolating"}),
             (11, {"morphology.typology": "agglutinative"}), (12, {"morphology.typology": "polysynthetic"})]
    for seed, pins in cases:
        spec, state, rep = _lang(seed, pins)
        q = verify(spec, RM, state)
        assert q["duplicate_forms"] == 0
        assert q["near_root_pairs"] == 0
        assert q["family_pairs_below_min"] == 0
        assert q["false_parses"] <= 0.01 * q["entries"], (seed, q["false_parses"])
        assert q["relaxed_roots"] == 0
        live = {e["concept_id"] for e in state["entries"] if not e["retired"]} - {"@quake", "@grand", "@inter", "@polit"}
        assert live == IDS


def test_deterministic_root_language():
    spec = sample_spec(1)
    a, _ = build_language(spec, VOCAB, RM, FREQ)
    assert a == _lang(1)[1]


def test_derived_words_follow_the_affix_rules():
    spec, state, _ = _lang(1)
    E = {e["concept_id"]: e for e in state["entries"]}
    RMa = _realised(spec, state)
    checked = 0
    for cid, node in RMa["recipes"].items():
        if node["op"] == "derive" and isinstance(node["base"], str):
            e, base = E[cid], E[node["base"]]
            ok = [apply_relation(spec, state["table"], base["phonemes"], node["rel"], k) for k in ("affix", "affix_noelide")]
            assert e["phonemes"] in ok, cid
            checked += 1
    assert checked > 250
    # the same relation always uses the same affix
    adj = [E[c]["phonemes"] for c, n in RMa["recipes"].items() if n["op"] == "derive" and n["rel"] == "ADJ"]
    assert len(adj) > 30


def test_families_share_stems_and_heads_are_bare():
    spec, state, _ = _lang(1)
    E = {e["concept_id"]: e for e in state["entries"]}
    for fam, roots in _realised(spec, state)["families"].items():
        st = state["stems"][fam]["phonemes"]
        assert E[roots[0]]["phonemes"] == st and E[roots[0]]["kind"] == "head"
    fam_entries = [e for e in state["entries"] if e["kind"] == "family"]
    kept = sum(1 for e in fam_entries if e["intact"]) / len(fam_entries)
    assert kept > 0.4  # whole stem usually survives inside the other members of its family


def test_sibling_stems_are_related_but_distinct():
    spec, state, _ = _lang(1)
    sg = _realised(spec, state)["sibling_groups"]
    assert len(sg) >= 40
    for fams in sg.values():
        base = state["stems"][fams[0]]["phonemes"]
        for f in fams[1:]:
            other = state["stems"][f]["phonemes"]
            assert other != base and pdist(base, other) >= MIN_DIST


def test_sound_classes_keep_grammar_and_lexicon_apart():
    for seed, pins in [(1, None), (3, None)]:
        spec, state, _ = _lang(seed, pins)
        t = state["table"]
        sc = t["sound_classes"]
        G = set(sc["grammatical"]["consonants"]) | set(sc["grammatical"]["vowels"])
        L = set(sc["lexical"]["consonants"]) | set(sc["lexical"]["vowels"])
        if sc["disjoint_consonants"] and sc["disjoint_vowels"]:
            assert not (G & L)
        for a in t["affixes"].values():
            assert set(a["phonemes"]) <= G
        for f in t["formatives"]:
            assert set(f) <= L
        for e in state["entries"]:  # changes inside a root only introduce lexical sounds
            if e["kind"] == "family":
                assert set(e["phonemes"]) - set(state["stems"][e["family"]]["phonemes"]) <= L
        assert t["link_consonant"] not in {p for a in t["affixes"].values() for p in a["phonemes"]}


def test_common_relations_get_short_affixes():
    spec, state, _ = _lang(1)
    A = state["table"]["affixes"]
    short = sum(len(A[r]["phonemes"]) for r in ("PLURAL", "ADJ", "ADV", "NEG", "AGENT"))
    rare = sum(len(A[r]["phonemes"]) for r in ("INDEP", "REVERSE", "MALE", "YOUNG", "AUGMENT"))
    assert short <= rare


def test_stem_length_follows_capacity_and_frequency():
    rich, st_rich, _ = _lang(1)
    poor, st_poor, _ = _lang(11, {"morphology.typology": "agglutinative"})
    content = lambda st: {f: s for f, s in st["stems"].items() if not s.get("small")}   # not the short-word families
    n1 = lambda st: sum(1 for s in content(st).values() if s["syllables"] == 1)
    assert n1(st_rich) >= 0.8 * len(content(st_rich)) and n1(st_poor) < 0.3 * len(content(st_poor))  # few syllables -> more multi-syllable stems
    assert any(s["syllables"] > 1 for s in st_poor["stems"].values())
    short_tiers = [s["group_tier"] for s in st_poor["stems"].values() if s["syllables"] == 1]
    assert not short_tiers or max(short_tiers) == 1                # any scarce short stems go to the most common (a CV-only language has none: its CV forms belong to the short common words)
    by_tier = verify(poor, RM, st_poor)["mean_syllables_by_tier"]
    assert by_tier[1] < by_tier[3]


def test_upgrade_adds_roots_without_changing_existing_words():
    dropped = {"abbey", "zoo", "zero", "orc", "goblin", "duke"}
    old = _subset(VOCAB, dropped)
    spec = sample_spec(1)
    s_old, _ = build_language(spec, old, RM)
    s_new, rep = extend(spec, VOCAB, RM, s_old)
    assert set(rep["added"]) == dropped and not rep["retired"]
    new = {e["concept_id"]: e for e in s_new["entries"]}
    for e in s_old["entries"]:
        assert new[e["concept_id"]] == e
    assert verify(spec, RM, s_new)["duplicate_forms"] == 0
    stem = s_new["stems"]["monster"]["phonemes"]
    assert new["goblin"]["family"] == "monster" and new["goblin"]["phonemes"] != stem
    gone = _subset(VOCAB, {"zoo"})
    s_gone, rep2 = extend(spec, gone, RM, s_new)
    assert rep2["retired"] == ["zoo"] and {e["concept_id"]: e for e in s_gone["entries"]}["zoo"]["form"] == new["zoo"]["form"]


# ---------------- feedback round: core words, gender base, fantasy families ----------------
def _fmap(rm=RM):
    from conlang_forge.frequency import f_of
    ents = {e["concept_id"]: e for e in VOCAB["entries"]}
    return {c: f_of(ents.get(c), FREQ) for c in set(rm["recipes"]) | set(rm["root_family"])}


def test_commonness_is_smooth_and_monotone():
    vals = [commonness(r) for r in (1, 10, 50, 100, 500, 1000, 2000, 2809)]
    assert vals == sorted(vals, reverse=True) and vals[0] > .95 and abs(vals[4] - .5) < 1e-9 and vals[-1] < .15
    R = FREQ["ranks"]
    assert R["be"] == 2 and R["work"] == 67 and R["time"] == 49           # overall ranks from the NGSL list
    assert R["case"] == R["case#court"] == R["case#medical"] == 168       # a lemma ranks all its senses
    assert R["i"] == 20 and R["true"] == 478                              # "I" and Excel's "TRUE" are normalised
    assert len(R) > 1500 and "dragon" not in R and "goblin" not in R      # fantasy words are not in the list
    assert FREQ["report"]["taken_from_extra_lists"] == ["others", "best"] or set(FREQ["report"]["taken_from_extra_lists"]) == {"others", "best"}


def test_frequent_words_are_more_often_independent_but_it_is_only_a_tendency():
    """Across many languages: the more frequent a derived word, the more often it gets its own root;
    but even frequent derived words keep their derivation sometimes and rare ones are rarely detached."""
    f = _fmap()
    derived = [c for c, n in RM["recipes"].items() if n["op"] != "same"]
    common = [c for c in derived if f[c] >= .4]
    rare = [c for c in derived if f[c] < .15]
    assert len(common) >= 15 and len(rare) >= 60
    rate = lambda cs: sum(c in make_plan(RM, f, sd)["independent"] for sd in range(1, 41) for c in cs) / (40 * len(cs))
    r_common, r_rare = rate(common), rate(rare)
    assert r_common > 3 * r_rare and 0.2 < r_common < 0.95 and r_rare < 0.1


def test_plan_is_deterministic_and_never_revisits_a_decision():
    f = _fmap()
    p1, p2 = make_plan(RM, f, 5), make_plan(RM, f, 5)
    assert p1 == p2
    flipped = {c: 1.0 - v for c, v in f.items()}                  # even wildly different frequency data ...
    p3 = make_plan(RM, flipped, 5, prior=p1)
    assert p3 == p1                                               # ... does not change decisions already made
    assert make_plan(RM, flipped, 5) != p1                        # but is used for undecided concepts


def test_plan_keeps_the_root_map_valid():
    f = _fmap()
    for sd in range(1, 21):
        rm = apply_plan(RM, make_plan(RM, f, sd))
        assert all(len(v) >= 2 and len(v) <= 10 for v in rm["families"].values())
        assert all(rm["root_family"][r] == fam for fam, v in rm["families"].items() for r in v)
        assert all(r not in rm["recipes"] for r in rm["root_family"])
        assert all(len(m) >= 2 for m in rm["sibling_groups"].values())
        assert all(m in rm["families"] for ms in rm["sibling_groups"].values() for m in ms)
    assert "detached" not in RM and "small" in RM["recipes"]      # the shared root map itself is never modified


def test_families_heads_follow_frequency():
    f = _fmap()
    heads = [make_plan(RM, f, sd)["heads"] for sd in range(1, 41)]
    # `old` (rank 10 adjective) rarely heads nothing odd; `water`, a frequent noun, usually heads its family
    fam = RM["root_family"]["water"]
    share = sum(h[fam] == "water" for h in heads) / len(heads)
    assert share > .4
    other = {x for h in heads for x in [h[fam]]}
    assert len(other) >= 1


def test_frequent_words_are_shorter_in_a_generated_language():
    spec, state, _ = _lang(1)
    E = [e for e in state["entries"] if e["kind"] in ("free", "head") and not e["is_function"]]
    common = [len(e["syllables"]) for e in E if e["f"] >= .5]
    rare = [len(e["syllables"]) for e in E if e["f"] < .1]
    assert common and rare and sum(common) / len(common) < sum(rare) / len(rare)
    st = state["plan"]
    assert st["independent"] and st["heads"]          # the plan is stored with the language
    # a stored plan is what verify() and upgrades use
    assert verify(spec, RM, state)["duplicate_forms"] == 0


def test_gender_base_is_a_language_setting():
    male, st_m, _ = _lang(1, {"morphology.gender_base": "male"})
    fem, st_f, _ = _lang(1, {"morphology.gender_base": "female"})
    assert male.provenance["morphology.gender_base"] == "pinned"
    assert male.phonology == fem.phonology and male.syntax == fem.syntax     # nothing else reshuffles
    st_m_plan, st_f_plan = st_m["plan"], st_f["plan"]
    Em = {e["concept_id"]: e for e in st_m["entries"]}
    Ef = {e["concept_id"]: e for e in st_f["entries"]}
    for fe, ma in [("queen", "king"), ("woman", "man"), ("mother", "father"), ("sister", "brother"),
                   ("wife", "husband"), ("she", "he"), ("lady", "lord"), ("girl", "boy")]:
        # a very frequent pair member may have been given its own root by the frequency plan (a tendency)
        assert (Em[fe]["kind"] == "derived" and Em[fe]["recipe"] == f"{ma} +FEMALE") or fe in st_m_plan["independent"], fe
        assert Em[ma]["kind"] in ("head", "family", "free")
        assert (Ef[ma]["kind"] == "derived" and Ef[ma]["recipe"] == f"{fe} +MALE") or ma in st_f_plan["independent"], ma
        assert Ef[fe]["kind"] in ("head", "family", "free")
    assert Em["grandmother"]["recipe"] == "@grand | father +FEMALE" or "grandmother" in st_m_plan["independent"]
    assert Ef["grandmother"]["recipe"] == "@grand | mother" or "grandmother" in st_f_plan["independent"]
    assert Ef["grandfather"]["recipe"] == "grandmother +MALE" or "grandfather" in st_f_plan["independent"]
    # in a female-base language the female term takes the male term's place in its family
    assert state_family(st_f, "queen") == state_family(st_m, "king") == "royalty"
    for st, spec in ((st_m, male), (st_f, fem)):
        q = verify(spec, RM, st)
        assert q["duplicate_forms"] == 0 and q["near_root_pairs"] == 0 and q["family_pairs_below_min"] == 0


def state_family(state, cid):
    return next(e["family"] for e in state["entries"] if e["concept_id"] == cid)


def test_gender_base_defaults_for_old_specs_and_adapt_is_idempotent_for_male():
    d = sample_spec(2).to_dict()
    d["morphology"].pop("gender_base")
    assert LanguageSpec.from_dict(d).morphology.gender_base == "male"
    assert adapt_rootmap(RM, "male") is RM
    a = adapt_rootmap(RM, "female")
    assert RM["recipes"]["queen"]["rel"] == "FEMALE"             # the original is not modified
    assert a["recipes"]["king"] == {"op": "derive", "base": "queen", "rel": "MALE"}
    assert len(a["gender_pairs_swapped"]) == 12


def test_friendly_humanoids_and_monsters_are_separate_families():
    assert RM["families"]["humanoid"] == ["elf", "dwarf", "halfling", "fairy"]   # the last two are planned words
    assert RM["families"]["monster"][:3] == ["monster", "orc", "goblin"]
    assert RM["root_family"]["elf"] != RM["root_family"]["orc"]
    spec, state, _ = _lang(1)
    st = state["stems"]
    assert pdist(st["humanoid"]["phonemes"], st["monster"]["phonemes"]) >= MIN_DIST
    E = {e["concept_id"]: e for e in state["entries"]}
    assert E["elf"]["family"] == "humanoid" and E["goblin"]["family"] == "monster"


# ---------------- vocabulary v1.1: upgrade of existing languages ----------------
def _v11():
    v = build_vocab(ROOT / "data/source/words_v1.1.csv", ROOT / "data/vocab/v1.1.manifest.json")
    rm = parse_roots((ROOT / "data/roots/v1.1.roots.txt").read_text(encoding="utf-8"), v)
    fr = build_freq(ROOT / "data/source/ngsl_1.2_stats.csv", v,
                    [ROOT / f"data/source/{n}.csv" for n in ("top_100_english_nouns", "top_100_english_verbs", "top_100_ngsl_adjectives")])
    return v, rm, fr


NEW_V11 = {"ankle", "ant", "bee", "commercial", "elbow", "fairy", "giant", "gnome", "halfling", "hip", "hobgoblin",
           "modern", "particular", "priest", "purple", "require", "warrior", "western", "wrist"}


def test_vocab_v1_1_only_adds_words():
    v11, rm11, _ = _v11()
    d = diff_vocab(VOCAB, v11)
    assert set(d["added"]) == NEW_V11 and d["removed"] == []          # room and understand were restored
    assert {"room", "understand", "duke"} <= {e["concept_id"] for e in v11["entries"]}
    assert rm11["pending"] == {} and rm11["stats"]["largest_family"] <= 5
    assert rm11["root_family"]["wrist"] == "hand" and rm11["root_family"]["gnome"] == "humanoid"
    assert rm11["root_family"]["hobgoblin"] == "brute" and ["monster", "brute"] in rm11["sibling_groups"].values()
    assert rm11["recipes"]["western"] == {"op": "derive", "base": "west", "rel": "ADJ"}


def test_upgrade_1_0_language_to_1_1_adds_exactly_the_new_words():
    v11, rm11, fr11 = _v11()
    for seed, pins in [(1, None), (11, {"morphology.typology": "agglutinative"})]:
        spec, state, _ = _lang(seed, pins)
        new_state, rep = extend(spec, v11, rm11, state, fr11)
        assert set(rep["added"]) == NEW_V11 and rep["retired"] == [] and rep["unretired"] == []
        old = {e["concept_id"]: e for e in state["entries"]}
        new = {e["concept_id"]: e for e in new_state["entries"]}
        assert all(new[c] == e for c, e in old.items())                 # nothing existing changed, not even by a letter
        q = verify(spec, rm11, new_state)
        assert q["duplicate_forms"] == 0 and q["near_root_pairs"] == 0 and q["family_pairs_below_min"] == 0
        if new[ "wrist"]["kind"] == "family":
            assert new["wrist"]["family"] == "hand" and new["fairy"]["family"] == "humanoid"


# ---------------- vocabulary v1.2: troll, ogre, werewolf ----------------
def _v12():
    v = build_vocab(ROOT / "data/source/words_v1.2.csv", ROOT / "data/vocab/v1.2.manifest.json")
    rm = parse_roots((ROOT / "data/roots/v1.2.roots.txt").read_text(encoding="utf-8"), v)
    fr = build_freq(ROOT / "data/source/ngsl_1.2_stats.csv", v,
                    [ROOT / f"data/source/{n}.csv" for n in ("top_100_english_nouns", "top_100_english_verbs", "top_100_ngsl_adjectives")])
    return v, rm, fr


def test_vocab_v1_2_adds_three_monsters_in_the_brute_family():
    v11, _, _ = _v11()
    v12, rm12, _ = _v12()
    assert set(diff_vocab(v11, v12)["added"]) == {"troll", "ogre", "werewolf"} and diff_vocab(v11, v12)["removed"] == []
    F = rm12["families"]
    assert F["monster"] == ["monster", "demon", "dragon"]                           # the generic word + non-humanoid horrors
    assert F["orcish"] == ["orc", "goblin", "hobgoblin", "werewolf"]                # humanoid monsters, human size
    assert F["brute"] == ["giant", "troll", "ogre"]                                 # big, hulking monsters
    assert ["monster", "orcish", "brute"] in rm12["sibling_groups"].values()
    assert F["humanoid"] == ["elf", "dwarf", "halfling", "fairy", "gnome"]          # friendly humanoids stay apart from monsters
    assert rm12["root_family"]["werewolf"] != rm12["root_family"]["vampire"]      # a lycanthrope is not undead
    assert rm12["families"]["undead"] == ["ghost", "vampire"] and rm12["stats"]["largest_family"] <= 5


def test_upgrade_1_1_language_to_1_2_adds_exactly_three_words():
    v11, rm11, fr11 = _v11()
    v12, rm12, fr12 = _v12()
    spec = sample_spec(1)
    s11, _ = build_language(spec, v11, rm11, fr11)
    s12, rep = extend(spec, v12, rm12, s11, fr12)
    assert set(rep["added"]) == {"troll", "ogre", "werewolf"} and not rep["retired"]
    old = {e["concept_id"]: e for e in s11["entries"]}
    new = {e["concept_id"]: e for e in s12["entries"]}
    assert all(new[c] == e for c, e in old.items())
    assert all(new[w]["family"] == "brute" for w in ("troll", "ogre")) and new["werewolf"]["family"] == "orcish"
    # orc, goblin and hobgoblin were built before the orcish family existed and stay exactly as they were
    assert all(new[w] == old[w] for w in ("orc", "goblin", "hobgoblin"))
    q = verify(spec, rm12, s12)
    assert q["duplicate_forms"] == 0 and q["near_root_pairs"] == 0 and q["family_pairs_below_min"] == 0


# ---------------------------------------------------------------- short common words
def _live(state):
    return [e for e in state["entries"] if not e["retired"] and e["kind"] not in ("alias", "bound")]


def test_short_list_is_made_of_real_vocabulary_base_words():
    from conlang_forge.smallwords import SHORT, CLASSES
    ids = {e["concept_id"] for e in VOCAB["entries"]}
    assert set(SHORT) <= ids and len(SHORT) >= 100
    assert all(0 < p <= 1 for _, p in SHORT.values())
    assert set(RM["recipes"]).isdisjoint(SHORT)      # derived words (me, my, him ...) inherit shortness from their base
    assert len(CLASSES) >= 8


def test_short_words_are_mostly_one_syllable_in_typical_languages():
    for seed, pins in [(1, None), (5, None), (11, {"morphology.typology": "isolating"})]:
        spec, state, _ = _lang(seed, pins)
        from conlang_forge.smallwords import SHORT
        short = [e for e in _live(state) if e["concept_id"] in SHORT]
        mono = sum(1 for e in short if len(e["syllables"]) == 1)
        assert mono >= 0.65 * len(short), (seed, mono, len(short))


def test_one_and_two_letter_words_mostly_belong_to_the_short_list():
    from conlang_forge.smallwords import SHORT
    for seed, pins in [(1, None), (5, None), (3, None), (11, {"morphology.typology": "agglutinative"})]:
        spec, state, _ = _lang(seed, pins)
        tiny = [e for e in _live(state) if len(e["form"].replace(" ", "")) <= 2]
        mine = [e for e in tiny if e["concept_id"] in SHORT or e["is_function"]]
        assert tiny and len(mine) >= 0.75 * len(tiny), (seed, len(mine), len(tiny))


def test_short_word_roll_is_a_pure_function_of_seed_and_word():
    from conlang_forge.smallwords import is_efficient
    a = [is_efficient(7, w) for w in ("and", "beneath", "the", "between")]
    assert a == [is_efficient(7, w) for w in ("and", "beneath", "the", "between")]
    rolls = [is_efficient(s, "and") for s in range(200)]
    assert sum(rolls) > 180                              # very basic words are nearly always efficient
    assert 40 < sum(is_efficient(s, "beneath") for s in range(200)) < 110
    assert not is_efficient(1, "dragon")                 # only listed words


def test_short_words_upgrade_without_changing_existing_words():
    dropped = {"and", "the", "because", "unless"}
    old = _subset(VOCAB, dropped)
    spec = sample_spec(1)
    s_old, _ = build_language(spec, old, RM, FREQ)
    s_new, rep = extend(spec, VOCAB, RM, s_old, FREQ)
    assert set(rep["added"]) == dropped
    before = {e["concept_id"]: e for e in s_old["entries"]}
    after = {e["concept_id"]: e for e in s_new["entries"]}
    assert all(after[c] == e for c, e in before.items())


# ---------------------------------------------------------------- inflection and the grammar book
def _grammar(seed, pins=None):
    from conlang_forge.grammar import Grammar
    spec, state, _ = _lang(seed, pins)
    return spec, state, Grammar(spec, state, VOCAB)


def test_inflection_inventory_matches_the_spec():
    from conlang_forge.infl_inventory import inventory
    for seed, pins in [(1, None), (5, None), (11, {"morphology.typology": "agglutinative"}), (12, {"morphology.typology": "isolating"})]:
        spec, state, _ = _grammar(seed, pins)
        m = spec.morphology
        keys = {i["key"] for i in inventory(spec)}
        assert set(state["table"]["infl"]) == keys
        assert {f"case:{c}" for c in m.cases if c not in ("nominative", "absolutive")} <= keys
        assert {f"gender:{g}" for g in m.genders} <= keys
        assert ("tense:present" not in keys) and ("tense:non-past" not in keys)      # the zero-marked tense has no ending
        assert all(not k.startswith("agr:") for k in keys) == (m.verb_agreement == "none")


def test_no_dictionary_word_is_an_inflectional_ending():
    for seed, pins in [(1, None), (5, None), (11, {"morphology.typology": "agglutinative"})]:
        spec, state, _ = _grammar(seed, pins)
        ends = {tuple(i["phonemes"]) for i in state["table"]["infl"].values() if not i["reuse"] and i["category"] not in ("q", "cop")}
        words = {tuple(e["phonemes"]) for e in state["entries"] if e["kind"] in ("head", "family", "free")}
        assert not (ends & words)
        spellings = [e["form"] for e in state["entries"] if e["kind"] != "alias" and not e["retired"]]
        assert len(spellings) == len(set(spellings))          # also true of the written forms: n+g and ng must not both occur


def test_clause_follows_word_order_and_is_reproducible():
    for seed, pins in [(1, None), (5, None), (12, {"morphology.typology": "isolating"}), (11, {"morphology.typology": "agglutinative"})]:
        spec, state, g = _grammar(seed, pins)
        kw = dict(subject={"head": "king"}, verb="see", object={"head": "dog"}, tense=None, drop_subject=False)
        toks = g.clause(**kw)
        glosses = [t["gloss"] for t in toks]
        pos = {"S": next(i for i, x in enumerate(glosses) if x.endswith("king") or "king" in x.split("-")),
               "O": next(i for i, x in enumerate(glosses) if "dog" in x.split("-")),
               "V": next(i for i, x in enumerate(glosses) if "see" in x.split("-"))}
        order = "".join(sorted("SVO", key=lambda c: pos[c]))
        assert order == spec.syntax.word_order, (seed, order, spec.syntax.word_order, glosses)
        assert toks == g.clause(**kw)


def test_agreement_and_marking_appear_where_the_spec_asks_for_them():
    spec, state, g = _grammar(11, {"morphology.typology": "agglutinative"})
    m = spec.morphology
    toks = g.clause(subject={"head": "king", "adjectives": ["big"]}, verb="see", object={"head": "dog"}, tense=None)
    flat = " ".join(t["gloss"] for t in toks)
    if m.genders:
        gd = g.gender_of("king")
        assert f"big-{abbr_(gd)}" in flat
    if m.cases:
        assert "ACC" in flat
    if m.verb_agreement != "none":
        assert "3SG" in flat
    neg = g.clause(subject={"head": "king"}, verb="see", object={"head": "dog"}, negated=True, tense=None)
    assert "NEG" in " ".join(t["gloss"] for t in neg)
    spec, state, g = _grammar(12, {"morphology.typology": "isolating"})
    pl = g.clause(subject={"head": "dog", "number": "plural"}, verb="sleep", tense=None)
    assert any(t["gloss"] == "PL" for t in pl) or "plural" not in spec.morphology.noun_number


def abbr_(x):
    from conlang_forge.infl_inventory import abbr
    return abbr(x)


def test_numerals_are_distinct_and_follow_the_counting_base():
    for seed, pins in [(1, None), (5, None), (11, {"morphology.typology": "agglutinative"})]:
        spec, state, g = _grammar(seed, pins)
        seen = {}
        for n in range(1, 100):
            w = tuple(g.numeral_words(n))
            assert w not in seen, (n, seen[w])
            seen[w] = n
        assert g.numeral_words(7) == ["seven"]
        if spec.morphology.numeral_base == 10:
            assert set(g.numeral_words(20)) == {"two", "ten"} and "hundred" in g.numeral_words(100)


def test_grammar_book_teaches_exactly_the_features_of_the_language():
    from conlang_forge.grammar_book import build_book
    for seed, pins in [(1, None), (5, None), (12, {"morphology.typology": "isolating"}), (11, {"morphology.typology": "agglutinative"})]:
        spec, state, _ = _lang(seed, pins)
        md = build_book(spec, state, VOCAB)
        assert md == build_book(spec, state, VOCAB)                       # reproducible
        for head in ("Lesson 1: Sounds and spelling", "Lesson 2: Greetings", "Lesson 3: Pronouns", "Lesson 4: Numbers and colors",
                     "Lesson 5: Nouns", "Lesson 6: Verbs", "Lesson 7: Adjectives", "Lesson 8: Building sentences",
                     "Lesson 9: Questions", "Lesson 10:", "Lesson 11: Practice", "Appendix A", "Appendix C"):
            assert head in md, head
        assert "None" not in md and "{" not in md
        assert md.count("```") // 2 >= 30
        m = spec.morphology
        assert (f"has **{len(m.cases)}**" in md) == bool(m.cases) or ("This language has **" in md) == bool(m.cases)
        assert ("no cases" in md) == (not m.cases)
        assert ("no tenses" in md) == (not m.tenses)
        assert ("**Gender**" in md) == bool(m.genders) and ("**Cases**" in md) == bool(m.cases)
        # every example line is written only with the language's own letters
        rom = set("".join(spec.orthography.romanization.values())) | {" ", "'"}
        for block in md.split("```")[1::2]:
            first = block.strip("\n").split("\n")[0]
            assert set(first) <= rom | set("?!."), (seed, first)


def test_cli_writes_the_book_with_the_language(tmp_path=None):
    import tempfile, subprocess, sys, pathlib
    out = pathlib.Path(tempfile.mkdtemp()) / "lang"
    root = pathlib.Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, "-m", "conlang_forge", "generate", "--seed", "3", "--vocab", str(root / "data/vocab/v1.2.json"),
                    "--rootmap", str(root / "data/roots/v1.2.rootmap.json"), "--freq", str(root / "data/vocab/v1.2.freq.json"),
                    "--out", str(out)], check=True, cwd=root, capture_output=True)
    assert (out / "grammar_book.md").read_text(encoding="utf-8").startswith("# ")


# ---------------------------------------------------------------- the two-way dictionary
def test_dictionary_has_both_halves_with_every_word_in_each():
    from conlang_forge.dictionary import build_rows, dictionary_markdown_full
    spec, state, _ = _lang(5)
    rows = build_rows(spec, state, VOCAB)
    live = [r for r in rows if not r["retired"]]
    assert len(live) >= 2000 and all(r["pos"] for r in rows)
    md = dictionary_markdown_full(spec, state, VOCAB, VOCAB["version"], rows)
    assert md == dictionary_markdown_full(spec, state, VOCAB, VOCAB["version"])        # reproducible
    eng, con = md.split(f"## English → {spec.name}")[1].split(f"## {spec.name} → English")
    assert eng.count("\n- **") == len(rows) == con.count("\n- **")
    for r in rows[:50]:
        assert f"**{r['form']}**" in eng and f"**{r['form']}**" in con


def test_dictionary_alphabet_treats_digraphs_as_letters():
    from conlang_forge.dictionary import Sorter, alphabet
    spec = sample_spec(5, {})
    letters = alphabet(spec)
    assert letters.index("sh") == letters.index("s") + 1 
    st = Sorter(spec)
    assert st.tokens("shaz") == ["sh", "a", "z"]
    assert st.key("sa") < st.key("sh") < st.key("sz") if "sz" in letters else st.key("sa") < st.key("sh")


def test_dictionary_forms_are_the_grammar_engines_forms():
    from conlang_forge.dictionary import build_rows
    from conlang_forge.grammar import Grammar
    for seed, pins in [(5, None), (12, {"morphology.typology": "isolating"})]:
        spec, state, _ = _lang(seed, pins)
        g = Grammar(spec, state, VOCAB)
        rows = {r["concept_id"]: r for r in build_rows(spec, state, VOCAB)}
        nouns = [r for r in rows.values() if r["plural"]]
        assert nouns
        r = nouns[0]
        assert r["plural"] == g.render(g.word(r["concept_id"], ["number:plural"]))[0]
        assert rows["go"]["pos"][0] == "v." and rows["big"]["pos"] == ["adj."] and rows["the"]["pos"] == ["det."]


def test_cli_writes_the_full_dictionary():
    import tempfile, subprocess, sys, pathlib
    out = pathlib.Path(tempfile.mkdtemp()) / "lang"
    root = pathlib.Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, "-m", "conlang_forge", "generate", "--seed", "3", "--vocab", str(root / "data/vocab/v1.2.json"),
                    "--rootmap", str(root / "data/roots/v1.2.rootmap.json"), "--freq", str(root / "data/vocab/v1.2.freq.json"),
                    "--out", str(out)], check=True, cwd=root, capture_output=True)
    assert "## How to use this dictionary" in (out / "dictionary.md").read_text(encoding="utf-8")
    assert (out / "dictionary.csv").read_text(encoding="utf-8").startswith("english,conlang,ipa,pos,gender")
