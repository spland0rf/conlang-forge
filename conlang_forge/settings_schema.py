"""Every adjustable setting of a language, described for the settings editor (and for exemplar proposals).

A language is its seed plus *pins* (settings the user fixed) plus *tuning* (odds, rates and tendencies that steer the
settings left random). This module knows, for every setting: its label, help, kind, allowed values, current value,
whether it is pinned, and the odds it would be drawn with. It also validates and normalises edits so that a pile of
changes always forms a coherent spec, and it explains in plain words what changed.

Kinds: enum, bool, number, multi (subset), weights (a share for each item), clusters (pairs of consonants),
text, odds (only the odds of a random choice can be changed).
"""
from __future__ import annotations

import json

from .backend.errors import ValidationFailed
from .inventory import BASE_CONSONANTS, CONSONANTS, SAY_LIKE, UNIT_DATA, UNITS, VOWEL_SPELLINGS, VOWELS, manner
from .spec import (CASE_EXTRA, KNOWN_KEYS, TEMPLATE_LEVELS, TYPOLOGIES, WORD_ORDERS, LanguageSpec, option_label,
                   sample_spec, validate_spec)

TEMPLATES = ["CV", "CVC", "V", "VC", "CCV", "CCVC", "CVCC", "CCVCC"]
CORE_CASES = {"nominative-accusative": ["nominative", "accusative"], "ergative-absolutive": ["ergative", "absolutive"]}
ALL_CASES = ["nominative", "accusative", "ergative", "absolutive"] + CASE_EXTRA
NOT_EDITABLE = {"orthography.style"}

GROUPS = [
    ("identity", "Name", "What the language is called."),
    ("sounds", "Sounds", "Which consonants and vowels exist, and how often each is used."),
    ("shapes", "Word shapes", "How syllables are put together and how long words tend to be."),
    ("building", "How words are built", "Whether grammar lives in endings, in little words, or both."),
    ("nouns", "Nouns", "Number, case, gender and articles."),
    ("verbs", "Verbs", "Tense, aspect, mood, agreement and negation."),
    ("sentences", "Sentences", "Word order and how questions, copulas and pronouns work."),
    ("tendencies", "Small grammar habits", "Little choices the grammar makes (each language settles them once)."),
    ("generator", "Word-making tendencies", "How the generator balances short, common, related and independent words."),
]

TYPE_LABELS = {"isolating": "Isolating: short words with almost no endings",
               "agglutinative": "Agglutinative: endings stack on words, one meaning each",
               "fusional": "Fusional: endings blend several meanings together",
               "polysynthetic": "Polysynthetic: long words that carry a whole sentence"}
ORDER_LABELS = {"SOV": "SOV: subject, object, verb (Japanese)", "SVO": "SVO: subject, verb, object (English)",
                "VSO": "VSO: verb, subject, object (Welsh)", "VOS": "VOS: verb, object, subject (Malagasy)",
                "OVS": "OVS: object, verb, subject (Hixkaryana)", "OSV": "OSV: object, subject, verb (rare)"}


def _opts(pairs):
    return [{"value": v, "label": l} for v, l in pairs]


def _list_label(v):
    return "none" if not v else ", ".join(v)


def _presets(values):
    return [{"value": v, "label": _list_label(v)} for v in values]


def consonant_info():
    return {c: {"label": CONSONANTS[c][0], "manner": CONSONANTS[c][2], "say": SAY_LIKE.get(c, "")} for c in CONSONANTS}


def vowel_info():
    return {v: {"label": VOWEL_SPELLINGS[v][0], "say": SAY_LIKE.get(v, "")} for v in VOWELS}


# ---------------------------------------------------------------------------------------------------- definitions
def definitions() -> list:
    d = []

    def add(key, group, label, help, kind, **kw):
        d.append(dict(key=key, group=group, label=label, help=help, kind=kind, **kw))

    add("name", "identity", "Language name", "Leave it on Random to keep the invented name.", "text", maxlen=40)

    add("phonology.consonant_count", "sounds", "Consonants: fewer or more",
        "How many ordinary consonants the language has. Fewer gives a plainer, softer sound; more gives a richer one. The "
        "lowest allowed is the least that still lets the language make a unique, consistent vocabulary with your other "
        "settings. The generator picks which consonants. Complex consonants (below) are counted separately.", "number",
        min=4, max=len(BASE_CONSONANTS), step=1, integer=True, dynamic_min="consonants")
    add("phonology.consonants", "sounds", "Which consonants",
        "Choose the exact consonant sounds instead of just how many. Setting this overrides the count above.", "multi", min=4,
        options=[{"value": c, "label": CONSONANTS[c][0], "hint": SAY_LIKE.get(c, ""), "group": manner(c)} for c in BASE_CONSONANTS])
    add("phonology.complex_count", "sounds", "Complex consonants: how many",
        "Some languages treat a sequence such as ts, tl, kp or the Czech rzh as ONE consonant, separate from its parts. Pick none, "
        "one, a few or many. The generator chooses which ones; fix the exact list below if you want.", "enum",
        options=_opts([(0, "None"), (1, "One"), (2, "Two"), (3, "A few (three)"), (4, "Four"), (5, "Five"), (6, "Many (six)"),
                       (7, "Seven"), (8, "Eight")]))
    add("phonology.complex_consonants", "sounds", "Which complex consonants",
        "Each acts as a single consonant in syllables, has its own letter in the alphabet and its own share below, and never "
        "joins a consonant pair.", "multi", min=0,
        options=[{"value": u, "label": CONSONANTS[u][0], "hint": SAY_LIKE.get(u, "")} for u in UNITS])
    add("phonology.consonant_weights", "sounds", "How often each consonant is used",
        "Higher shares make a consonant turn up more in words.", "weights", of="phonology.consonants+complex")
    add("phonology.consonant_size", "sounds", "Consonant count when random",
        "How likely a small, medium or large consonant set is, when the count is left on Random.", "odds",
        labels={"small": "Small (8 to 12)", "medium": "Medium (13 to 19)", "large": "Large (20 to 25)"})
    add("phonology.vowel_count", "sounds", "Vowels: fewer or more",
        "How many vowels the language has. The lowest allowed is the least that still gives a unique, consistent vocabulary "
        "with your other settings.", "number", min=3, max=len(VOWELS), step=1, integer=True, dynamic_min="vowels")
    add("phonology.vowels", "sounds", "Which vowels", "Choose the exact vowels instead of just how many. The five plain vowels "
        "(a e i o u) are easy to read; extra vowels are written with letter pairs. Overrides the count above.", "multi", min=3,
        options=[{"value": v, "label": VOWEL_SPELLINGS[v][0], "hint": SAY_LIKE.get(v, "")} for v in VOWELS])
    add("phonology.vowel_weights", "sounds", "How often each vowel is used", "Higher shares make a vowel more common.",
        "weights", of="phonology.vowels")
    add("phonology.vowel_count_odds", "sounds", "Vowel count when random", "How likely each vowel count is, when the "
        "count is left on Random.", "odds", labels={str(n): f"{n} vowels" for n in range(3, 10)})
    add("phonology.stress", "sounds", "Stress", "Which syllable of a word is said louder.", "enum",
        options=_opts([("initial", "First syllable"), ("penultimate", "Second to last syllable"),
                       ("final", "Last syllable"), ("none", "Even, no stress")]))
    add("phonology.allow_hiatus", "sounds", "Vowels side by side",
        "Whether two vowels may stand next to each other in one word (like the 'oe' in 'poet').", "bool",
        yes="Allowed", no="Not allowed")

    add("phonology.syllable_complexity", "shapes", "Syllable complexity",
        "A starting point for syllable shapes: 1 is simple (ma-ni), 5 allows heavy clusters (strants).", "enum",
        options=_opts([(1, "1: only consonant + vowel"), (2, "2: simple, some closed syllables"),
                       (3, "3: moderate"), (4, "4: complex, clusters allowed"), (5, "5: heavy clusters")]))
    add("phonology.syllable_templates", "shapes", "Syllable shapes and how common each is",
        "C is a consonant and V a vowel. CV is 'ma', CVC is 'man', CCV is 'pla'. Set a share to 0 to forbid a shape.",
        "weights", of=None, items=[{"value": t, "label": t} for t in TEMPLATES])
    add("phonology.onset_clusters", "shapes", "Consonant pairs that may start a syllable",
        "Pairs like 'pl' or 'st' at the start of a syllable. Only used by shapes that start with CC.", "clusters",
        position="onset")
    add("phonology.coda_consonants", "shapes", "Consonants that may end a syllable",
        "Only used by shapes that end in a consonant (CVC).", "multi", of="phonology.consonants+complex", min=0,
        options=[{"value": c, "label": CONSONANTS[c][0], "hint": SAY_LIKE.get(c, ""), "group": manner(c)} for c in CONSONANTS])
    add("phonology.coda_clusters", "shapes", "Consonant pairs that may end a syllable",
        "Pairs like 'nt' or 'lk' at the end of a syllable. Only used by shapes ending in CC.", "clusters",
        position="coda")
    add("phonology.max_cluster", "shapes", "Longest run of consonants", "No word will have more consonants in a row "
        "than this.", "number", min=1, max=4, step=1, integer=True)
    add("phonology.mean_root_syllables", "shapes", "Typical root length (syllables)",
        "Average number of syllables in an ordinary word. Common words come out shorter, rare ones longer.", "number",
        min=1.0, max=4.0, step=.05)

    add("morphology.typology", "building", "Kind of language", "The overall style of the grammar. It also sets the "
        "defaults of many other settings that you leave on Random.", "enum", options=_opts([(t, TYPE_LABELS[t]) for t in TYPOLOGIES]))
    add("morphology.synthesis_index", "building", "Endings per word", "Average number of meaningful pieces in a word. "
        "1 is one piece (no endings); 5 is very long words.", "number", min=1.0, max=6.0, step=.05)
    add("morphology.affix_position", "building", "Where endings go", "Before the word, after it, or both.", "enum",
        options=_opts([("none", "None: no affixes"), ("suffixing", "After the word (suffixes)"),
                       ("prefixing", "Before the word (prefixes)"), ("mixed", "Both before and after")]))

    add("morphology.noun_number", "nouns", "Number", "How many forms a noun has for counting.", "enum",
        options=_presets([[], ["singular", "plural"], ["singular", "dual", "plural"], ["singular", "paucal", "plural"]]))
    add("morphology.case_alignment", "nouns", "Who is the doer", "How subjects and objects are marked. English-like "
        "languages mark the object; ergative languages mark the doer of an action on an object.", "enum",
        options=_opts([("nominative-accusative", "Nominative-accusative (like English)"),
                       ("ergative-absolutive", "Ergative-absolutive (like Basque)")]))
    add("morphology.cases", "nouns", "Cases", "Endings (or small words) that show a noun's job. The two basic cases "
        "for the chosen alignment are always kept.", "multi", min=0, options=[{"value": c, "label": c} for c in ALL_CASES])
    add("morphology.genders", "nouns", "Genders", "Noun classes that adjectives and verbs may agree with.", "enum",
        options=_presets([[], ["masculine", "feminine"], ["masculine", "feminine", "neuter"], ["animate", "inanimate"]]
                         + [[f"class {i}" for i in range(1, n + 1)] for n in range(4, 9)]))
    add("morphology.gender_base", "nouns", "Plain form of paired words", "For pairs like king/queen, which one is the "
        "plain root and which is built from it.", "enum", options=_opts([("male", "The male word is the root"), ("female", "The female word is the root")]))
    add("morphology.definiteness", "nouns", "Articles", "Words or endings like 'the' and 'a'.", "enum",
        options=_opts([("none", "None"), ("definite article", "'the' only"),
                       ("definite+indefinite articles", "'the' and 'a'"), ("definiteness affix", "An ending for 'the'")]))
    add("morphology.numeral_base", "nouns", "Counting base", "How numbers above the first few are built.", "enum",
        options=_opts([(10, "10 (like English)"), (20, "20 (scores)"), (5, "5 (one hand)"), (12, "12 (dozens)"), (8, "8")]))

    add("morphology.tenses", "verbs", "Tenses", "Ways to place an action in time.", "enum",
        options=_presets([[], ["past", "non-past"], ["past", "present", "future"], ["future", "non-future"],
                          ["remote past", "recent past", "present", "future"]]))
    add("morphology.aspects", "verbs", "Aspects", "Whether an action is finished, ongoing, repeated, and so on.", "enum",
        options=_presets([[], ["perfective", "imperfective"], ["perfective", "imperfective", "progressive", "habitual"],
                          ["completive", "continuative"]]))
    add("morphology.moods", "verbs", "Moods", "Statements, commands, wishes, conditions.", "enum",
        options=_presets([["indicative"], ["indicative", "imperative"], ["indicative", "imperative", "subjunctive"],
                          ["indicative", "imperative", "subjunctive", "conditional", "optative"]]))
    add("morphology.verb_agreement", "verbs", "Verb agreement", "Whether the verb changes to match who does it (and "
        "to whom).", "enum", options=_opts([("none", "None"), ("subject", "With the subject"),
                                            ("subject+object", "With subject and object"), ("polypersonal", "With everyone involved")]))
    add("morphology.evidentiality", "verbs", "Evidentials", "Verb endings that say how the speaker knows (saw it, "
        "heard it, guessed it).", "bool", yes="Yes", no="No")
    add("morphology.negation", "verbs", "Negation", "How 'not' is said.", "enum",
        options=_opts([("particle before verb", "A small word before the verb"), ("particle after verb", "A small word after the verb"),
                       ("verbal affix", "An ending on the verb"), ("auxiliary verb", "A helping verb"),
                       ("double negation particle", "A small word on each side of the verb")]))

    add("syntax.word_order", "sentences", "Sentence order", "The usual order of subject (S), verb (V) and object (O).",
        "enum", options=_opts([(w, ORDER_LABELS[w]) for w in WORD_ORDERS]))
    add("syntax.adposition", "sentences", "Little place words", "Whether words like 'in' and 'to' come before or after "
        "the noun.", "enum", options=_opts([("preposition", "Before the noun (prepositions)"), ("postposition", "After the noun (postpositions)")]))
    add("syntax.adjective_order", "sentences", "Adjectives", "Where 'big' goes in 'big house'.", "enum",
        options=_opts([("adjective-noun", "Before the noun"), ("noun-adjective", "After the noun")]))
    add("syntax.genitive_order", "sentences", "Possession", "Where 'the king's' goes in 'the king's sword'.", "enum",
        options=_opts([("genitive-noun", "Owner first"), ("noun-genitive", "Thing first")]))
    add("syntax.relative_clause", "sentences", "Relative clauses", "Where 'who sleeps' goes in 'the man who sleeps'.",
        "enum", options=_opts([("prenominal", "Before the noun"), ("postnominal", "After the noun")]))
    add("syntax.has_copula", "sentences", "A word for 'to be'", "Whether the language has a dedicated 'is'.", "bool",
        yes="Yes", no="No")
    add("syntax.copula_form", "sentences", "What the 'is' looks like", "A full verb, a small particle, or nothing at all.",
        "enum", options=_opts([("verb", "A verb"), ("particle", "A small word"), ("zero", "Nothing (just put the words side by side)")]))
    add("syntax.question_strategy", "sentences", "Yes/no questions", "How a question is signalled.", "enum",
        options=_opts([("particle", "A question word"), ("intonation", "Only the tone of voice"),
                       ("verb inversion", "Swap verb and subject"), ("verbal affix", "An ending on the verb")]))
    add("syntax.pro_drop", "sentences", "Dropping 'I', 'you'...", "Whether pronouns are left out when the verb already "
        "shows who.", "bool", yes="Often dropped", no="Always said")

    add("grammar.wh_fronting", "tendencies", "Question words go first", "Chance that who/what/where move to the front "
        "(only languages with verb-medial or verb-initial order).", "rate", default=.5)
    add("grammar.plural_after_numeral", "tendencies", "Plural after a number", "Chance that 'three dogs' keeps the plural "
        "ending (otherwise 'three dog').", "rate", default=.55)
    add("grammar.number_order", "tendencies", "Order of big numbers", "Chance of twenty-three over three-and-twenty.",
        "rate", default=.85)

    def gen(name, label, help, lo, hi, step, default, integer=False):
        add("gen." + name, "generator", label, help, "tune", min=lo, max=hi, step=step, default=default, integer=integer)

    gen("small_inventory_min", "Smallest small consonant set", "When a small consonant set is drawn, at least this many.", 6, 12, 1, 8, True)
    gen("small_inventory_max", "Largest small consonant set", "...and at most this many.", 6, 14, 1, 12, True)
    gen("letter_unevenness_min", "Letter unevenness (low end)", "How lopsided the letter frequencies are: 0.3 is nearly even, 1.5 is very uneven.", .2, 2.0, .05, .5)
    gen("letter_unevenness_max", "Letter unevenness (high end)", "Upper end of the same range.", .2, 2.0, .05, 1.1)
    gen("onset_clusters_min", "Fewest starting pairs", "When starting pairs are random, at least this many.", 0, 20, 1, 3, True)
    gen("onset_clusters_max", "Most starting pairs", "...and at most this many.", 0, 40, 1, 12, True)
    gen("coda_consonants_min", "Fewest ending consonants", "When ending consonants are random, at least this many.", 0, 10, 1, 2, True)
    gen("coda_consonants_max", "Most ending consonants", "...and at most this many.", 1, 15, 1, 7, True)
    gen("commonness_shortening", "Common words are short", "How much shorter everyday words are than rare ones. 0 makes all words "
        "about equally long; 2 makes everyday words very short.", 0, 2.5, .05, 1.35)
    gen("function_word_shortening", "Small words are short", "How much shorter little grammar words (the, of, and) are. "
        "1 means no shortening; 0.5 makes them very short.", .4, 1.0, .05, .8)
    gen("max_root_syllables", "Longest ordinary root", "No ordinary word starts out longer than this many syllables.", 2, 8, 1, 5, True)
    gen("short_word_efficiency", "Very short everyday words", "Multiplier on how many of the commonest English words get a "
        "one-syllable form. 0 turns it off.", 0, 1.5, .05, 1.0)
    gen("tiny_word_leak", "One- and two-letter words", "Chance an ordinary word may be a tiny one-or-two-letter word.", 0, .5, .01, .05)
    gen("frequency_exponent", "Common words get their own roots", "Higher values make only the very commonest words "
        "independent roots; lower values give more rare words their own root too.", .5, 3.0, .05, 1.5)
    gen("compound_independence", "Compounds become roots", "Chance that a word that could be a compound (like "
        "'sunrise') becomes a simple root instead.", 0, 1.5, .05, .7)
    gen("derivation_independence", "Derived words become roots", "Multiplier on the chance that a word that could be "
        "built from another (like 'singer' from 'sing') becomes its own root.", 0, 2.0, .05, 1.0)
    gen("family_leaving", "Families break up", "Chance that a related word leaves its word family and gets its own root.", 0, 1.5, .05, .8)
    return d


DEFS = definitions()
BY_KEY = {s["key"]: s for s in DEFS}
TUNE_NAMES = {s["key"][4:] for s in DEFS if s["kind"] == "tune"}
RATE_KEYS = {s["key"] for s in DEFS if s["kind"] == "rate"} | {
    "phonology.allow_hiatus", "morphology.evidentiality", "syntax.has_copula", "syntax.pro_drop"}
ODDS_KEYS = {s["key"] for s in DEFS if s["kind"] in ("enum", "odds")}
SPEC_KEYS = {s["key"] for s in DEFS if "." in s["key"] and not s["key"].startswith(("gen.", "grammar.")) and s["kind"] not in ("odds", "tune", "rate")} | {"name"}
assert SPEC_KEYS - {"name"} <= KNOWN_KEYS, SPEC_KEYS - KNOWN_KEYS


# ---------------------------------------------------------------------------------------------------- reading a spec
def spec_value(spec: LanguageSpec, key: str):
    if key == "name":
        return spec.name
    if key == "phonology.consonants":                       # ordinary consonants only; complex ones are their own setting
        return [c for c in spec.phonology.consonants if c not in UNIT_DATA]
    if key == "phonology.consonant_count":
        return len([c for c in spec.phonology.consonants if c not in UNIT_DATA])
    if key == "phonology.vowel_count":
        return len(spec.phonology.vowels)
    if key == "phonology.complex_count":
        return len(spec.phonology.complex_consonants)
    sec, attr = key.split(".")
    return getattr(getattr(spec, sec), attr)


def pins_of(spec: LanguageSpec) -> dict:
    """The settings that were fixed (not random) when this spec was made, with their current values."""
    out = {}
    for k, how in (spec.provenance or {}).items():
        if how == "pinned" and k in SPEC_KEYS:
            out[k] = spec_value(spec, k)
    if "phonology.complex_consonants" not in (spec.provenance or {}):
        out["phonology.complex_consonants"] = []             # a language made before complex consonants existed has none
    return out


def cluster_id(pair) -> str:
    return "+".join(pair)


def _clusters_to_ids(v):
    return [cluster_id(p) for p in v]


def _value_for_client(s, v):
    if s["kind"] == "clusters":
        return _clusters_to_ids(v)
    return v


def _label_of(odds_key, option):
    s = BY_KEY.get(odds_key)
    if s and s.get("options"):
        for o in s["options"]:
            if o["value"] == option:
                return o["label"]
    if s and s.get("labels"):
        return s["labels"].get(str(option), str(option))
    if isinstance(option, bool):
        return "Yes" if option else "No"
    return option if isinstance(option, str) else _list_label(option) if isinstance(option, list) else str(option)


def describe(spec: LanguageSpec) -> dict:
    """Everything the editor shows: the setting definitions plus this language's value, pin state and odds."""
    pins = pins_of(spec)
    rec: dict = {}
    sample_spec(spec.seed, pins, spec.tuning, recorder=rec)
    tuning = spec.tuning or {}
    settings = []
    for s in DEFS:
        k = s["key"]
        item = {kk: vv for kk, vv in s.items()}
        if k in SPEC_KEYS:
            item["value"] = _value_for_client(s, spec_value(spec, k))
            item["pinned"] = k in pins
            item["editable"] = True
        if s["kind"] == "tune":
            v = (tuning.get("gen") or {}).get(k[4:])
            item["value"] = s["default"] if v is None else v
            item["custom"] = v is not None
        if s["kind"] == "rate":
            v = (tuning.get("rates") or {}).get(k)
            item["value"] = s["default"] if v is None else v
            item["custom"] = v is not None
        if k in rec:
            r = rec[k]
            if s["kind"] == "bool" or k in RATE_KEYS and s["kind"] == "bool":
                custom = k in (tuning.get("rates") or {})
                item["chance"] = {"value": round(r["weights"][0], 4), "default": round(r["default"][0], 4), "custom": custom}
            else:
                over = (tuning.get("odds") or {}).get(k) or {}
                item["odds"] = [{"option": o, "key": option_label(o), "label": _label_of(k, o), "weight": w, "default": dw,
                                 "custom": option_label(o) in over}
                                for o, w, dw in zip(r["options"], r["weights"], r["default"])]
        settings.append(item)
    return {"groups": [{"id": g, "label": l, "help": h} for g, l, h in GROUPS], "settings": settings,
            "consonants": consonant_info(), "vowels": vowel_info(),
            "cluster_rules": {"onset": {"first": ["stop", "fricative"], "second": ["liquid", "glide"], "never_first": ["ʔ", "h"],
                                        "s_plus_stop": True},
                              "coda": {"first": ["nasal", "liquid"], "first_extra": ["s"], "second": ["stop"], "never_second": ["ʔ"]}},
            "tuning": tuning, "seed": spec.seed, "minimums": minimums(spec)}


# ---------------------------------------------------------------------------------------------------- editing
def candidate_clusters(position: str, consonants: list, coda_consonants: list | None = None) -> list:
    if position == "onset":
        out = [[a, b] for a in consonants for b in consonants
               if a != b and manner(a) in ("stop", "fricative") and manner(b) in ("liquid", "glide") and a not in ("ʔ", "h")]
        if "s" in consonants:
            out += [["s", b] for b in consonants if manner(b) == "stop" and b != "ʔ"]
        return out
    stops = [c for c in consonants if manner(c) == "stop" and c != "ʔ"]
    return [[a, b] for a in (coda_consonants if coda_consonants is not None else consonants) for b in stops
            if a != b and (manner(a) in ("nasal", "liquid") or a == "s")]


def _bad(msg):
    raise ValidationFailed(msg)


def _num(v, lo, hi, what, integer=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        _bad(f"{what} must be a number")
    if v < lo or v > hi:
        _bad(f"{what} must be between {lo} and {hi}")
    return int(round(v)) if integer else round(float(v), 4)


def clean_value(key: str, v, context: dict):
    """Check one pinned value against its definition and convert it to the spec's own form."""
    s = BY_KEY.get(key)
    if s is None or key not in SPEC_KEYS:
        _bad(f"unknown setting {key}")
    kind, label = s["kind"], s["label"]
    if kind == "text":
        if not isinstance(v, str) or not v.strip() or len(v.strip()) > s["maxlen"]:
            _bad(f"{label} must be 1 to {s['maxlen']} characters")
        return v.strip()
    if kind == "bool":
        if not isinstance(v, bool):
            _bad(f"{label} must be yes or no")
        return v
    if kind == "enum":
        for o in s["options"]:
            if o["value"] == v:
                return o["value"]
        _bad(f"{label}: that choice is not available")
    if kind == "number":
        return _num(v, s["min"], s["max"], label, s.get("integer", False))
    if kind == "multi":
        if not isinstance(v, list) or any(not isinstance(x, str) for x in v):
            _bad(f"{label} must be a list")
        allowed = [o["value"] for o in s["options"]]
        if any(x not in allowed for x in v):
            _bad(f"{label}: unknown item")
        out = [x for x in allowed if x in set(v)]
        if len(out) < s.get("min", 0):
            _bad(f"{label}: choose at least {s['min']}")
        return out
    if kind == "weights":
        if not isinstance(v, dict):
            _bad(f"{label} must be a set of shares")
        out = {}
        for k2, w in v.items():
            if isinstance(w, bool) or not isinstance(w, (int, float)) or w < 0:
                _bad(f"{label}: shares must be zero or more")
            out[k2] = float(w)
        if not any(w > 0 for w in out.values()):
            _bad(f"{label}: at least one share must be above zero")
        total = sum(out.values())
        return {k2: round(w / total, 5) for k2, w in out.items()}
    if kind == "clusters":
        if not isinstance(v, list):
            _bad(f"{label} must be a list")
        pairs = []
        for x in v:
            if isinstance(x, str):
                x = x.split("+")
            if not (isinstance(x, list) and len(x) == 2 and all(isinstance(c, str) and c in CONSONANTS for c in x)):
                _bad(f"{label}: bad pair {x!r}")
            pairs.append(list(x))
        return pairs
    _bad(f"cannot set {key}")


def normalize(pins: dict, base_spec: LanguageSpec | None = None) -> dict:
    """Validate raw pins and make them mutually consistent (inventories vs shares, cases vs alignment, clusters vs
    consonants). Raises ValidationFailed with a plain message when an edit cannot be made to work."""
    if not isinstance(pins, dict):
        _bad("settings must be an object")
    out = {}
    for k, v in pins.items():
        if k in NOT_EDITABLE:
            continue
        out[k] = clean_value(k, v, out)
    base_c = out.get("phonology.consonants") or (spec_value(base_spec, "phonology.consonants") if base_spec else None)
    units = out["phonology.complex_consonants"] if "phonology.complex_consonants" in out else (
        base_spec.phonology.complex_consonants if base_spec else [])
    cons = sorted(list(base_c) + [u for u in units if u not in base_c], key=list(CONSONANTS).index) if base_c else None
    vows = out.get("phonology.vowels") or (base_spec.phonology.vowels if base_spec else None)
    # a list overrides the matching count (the list decides how many)
    for lst, cnt in (("phonology.consonants", "phonology.consonant_count"), ("phonology.vowels", "phonology.vowel_count"),
                     ("phonology.complex_consonants", "phonology.complex_count")):
        if lst in out:
            out.pop(cnt, None)
    if "phonology.consonants" in out and "phonology.consonant_weights" not in out and base_spec is not None:
        pass   # shares are then random for the new inventory (the sampler derives them)
    for inv, wk, items in (("phonology.consonants", "phonology.consonant_weights", cons), ("phonology.vowels", "phonology.vowel_weights", vows)):
        if wk in out and items:
            w = out[wk]
            extra = [x for x in w if x not in items]
            for x in extra:
                del w[x]
            if not w:
                _bad(f"{BY_KEY[wk]['label']}: give at least one of the chosen sounds a share")
            missing = [x for x in items if x not in w]
            if missing:
                floor = min(w.values()) if w else .05
                for x in missing:
                    w[x] = floor
            tot = sum(w.values())
            out[wk] = {x: round(w[x] / tot, 5) for x in items}
    if "phonology.consonant_weights" in out and "phonology.consonants" not in out and base_spec is not None:
        pass
    if "phonology.syllable_templates" in out:
        t = out["phonology.syllable_templates"]
        bad = [x for x in t if x not in TEMPLATES]
        if bad:
            _bad(f"unknown syllable shape {bad[0]}")
        out["phonology.syllable_templates"] = {x: w for x, w in t.items() if w > 0}
    if "morphology.cases" in out or "morphology.case_alignment" in out:
        align = out.get("morphology.case_alignment") or (base_spec.morphology.case_alignment if base_spec else "nominative-accusative")
        if "morphology.cases" in out and out["morphology.cases"]:
            core = CORE_CASES[align]
            cs = [c for c in ALL_CASES if c in set(out["morphology.cases"])]
            drop = [c for c in cs if c in {"nominative", "accusative", "ergative", "absolutive"} and c not in core]
            cs = [c for c in cs if c not in drop]
            out["morphology.cases"] = core + [c for c in cs if c not in core]
    if cons:
        on = candidate_clusters("onset", cons)
        if "phonology.onset_clusters" in out:
            ok = {cluster_id(p) for p in on}
            out["phonology.onset_clusters"] = [p for p in out["phonology.onset_clusters"] if cluster_id(p) in ok]
        if "phonology.coda_consonants" in out:
            out["phonology.coda_consonants"] = [c for c in out["phonology.coda_consonants"] if c in cons]
        if "phonology.coda_clusters" in out:
            cc = out.get("phonology.coda_consonants") or (base_spec.phonology.coda_consonants if base_spec else cons)
            ok = {cluster_id(p) for p in candidate_clusters("coda", cons, cc)}
            out["phonology.coda_clusters"] = [p for p in out["phonology.coda_clusters"] if cluster_id(p) in ok]
    return out


def clean_tuning(t) -> dict:
    """Validate a complete tuning object. Returns it in canonical form (empty parts removed)."""
    if t in (None, ""):
        return {}
    if not isinstance(t, dict) or set(t) - {"odds", "rates", "gen"}:
        _bad("tuning must contain only odds, rates and gen")
    out = {}
    odds = {}
    for k, o in (t.get("odds") or {}).items():
        if k not in ODDS_KEYS or not isinstance(o, dict):
            _bad(f"unknown odds for {k}")
        row = {}
        for lab, w in o.items():
            if isinstance(w, bool) or not isinstance(w, (int, float)) or w < 0 or w > 1000:
                _bad(f"odds for {BY_KEY[k]['label']} must be numbers from 0 up")
            row[str(lab)] = float(w)
        if row:
            odds[k] = row
    if odds:
        out["odds"] = odds
    rates = {}
    for k, p in (t.get("rates") or {}).items():
        if k not in RATE_KEYS:
            _bad(f"unknown rate {k}")
        if isinstance(p, bool) or not isinstance(p, (int, float)) or p < 0 or p > 1:
            _bad(f"{BY_KEY[k]['label']}: the chance must be between 0 and 1")
        rates[k] = round(float(p), 4)
    if rates:
        out["rates"] = rates
    gen = {}
    for k, v in (t.get("gen") or {}).items():
        s = BY_KEY.get("gen." + k)
        if s is None or s["kind"] != "tune":
            _bad(f"unknown tendency {k}")
        gen[k] = _num(v, s["min"], s["max"], s["label"], s.get("integer", False))
    if gen:
        out["gen"] = gen
    return out


# ---------------------------------------------------------------------------------------------------- explaining
def show(key: str, v) -> str:
    s = BY_KEY.get(key)
    if v is None:
        return "-"
    if s is None:
        return str(v)
    k = s["kind"]
    if k == "enum":
        for o in s["options"]:
            if o["value"] == v:
                return o["label"].split(":")[0] if k == "enum" and key in ("morphology.typology", "syntax.word_order") else o["label"]
    if k == "bool":
        return s["yes"] if v else s["no"]
    if k == "multi":
        lab = {o["value"]: o["label"] for o in s["options"]}
        return ", ".join(lab.get(x, x) for x in v) or "none"
    if k == "clusters":
        return ", ".join("".join(CONSONANTS[c][0] for c in p) for p in v) or "none"
    if k == "weights":
        lab = {o["value"]: o["label"] for o in (s.get("items") or [])}
        top = sorted(v.items(), key=lambda kv: -kv[1])
        return ", ".join(f"{lab.get(x) or (CONSONANTS.get(x) or ('',))[0] or VOWEL_SPELLINGS.get(x, [x])[0]} {round(w * 100)}%" for x, w in top[:8]) + (" ..." if len(top) > 8 else "")
    return str(v)


def diff(old: LanguageSpec, new: LanguageSpec) -> list:
    """Settings whose value differs between two specs, with plain-language before/after."""
    out = []
    for s in DEFS:
        k = s["key"]
        if k not in SPEC_KEYS or k == "name" or k in ("phonology.consonant_count", "phonology.vowel_count", "phonology.complex_count"):
            continue
        a, b = spec_value(old, k), spec_value(new, k)
        if a != b:
            if s["kind"] == "weights" or s["kind"] == "clusters":
                sa, sb = show(k, a), show(k, b)
                if sa == sb:
                    sa, sb = "(earlier mix)", "(new mix)"
            else:
                sa, sb = show(k, a), show(k, b)
            out.append({"key": k, "label": s["label"], "group": s["group"], "before": sa, "after": sb})
    if old.name != new.name:
        out.append({"key": "name", "label": "Language name", "group": "identity", "before": old.name, "after": new.name})
    return out


def build_spec(seed: int, pins: dict, tuning: dict) -> LanguageSpec:
    """Sample a spec from settings and make sure the result can make words. Raises ValidationFailed with advice."""
    try:
        spec = sample_spec(seed, pins, tuning)
    except ValueError as e:
        _bad(str(e))
    errs = validate_spec(spec)
    ph = spec.phonology
    if len(ph.vowels) < MIN_VOWELS:
        _bad(f"A language needs at least {MIN_VOWELS} vowels to build a unique vocabulary (it has {len(ph.vowels)}).")
    templates = ph.syllable_templates
    if not templates:
        errs.append("allow at least one syllable shape")
    if any(t.startswith("CC") for t in templates) and not ph.onset_clusters and all(t.startswith("CC") for t in templates):
        errs.append("every syllable shape starts with two consonants but no starting pairs are allowed")
    if errs:
        _bad("These settings do not fit together: " + "; ".join(errs))
    capacity = capacity_of(len(ph.consonants), len(ph.vowels), templates)
    if not feasible(len(ph.consonants), len(ph.vowels), templates):
        units = len(ph.complex_consonants)
        base = len(ph.consonants) - units
        need_c, need_v = min_consonants(len(ph.vowels), templates, units), min_vowels(len(ph.consonants), templates)
        tips = []
        if need_c <= len(BASE_CONSONANTS):
            tips.append(f"with {len(ph.vowels)} vowels you need at least {need_c} consonants (you have {base})")
        if need_v <= len(VOWELS):
            tips.append(f"with {base} consonants you need at least {need_v} vowels (you have {len(ph.vowels)})")
        _bad(f"These sounds and syllable shapes can only make about {capacity:,} different words of up to three syllables, too few "
             "for a unique 2,000-word vocabulary. " + ("; ".join(tips).capitalize() + ". " if tips else "") +
             "You can also allow more syllable shapes or add complex consonants.")
    return spec


MIN_VOWELS = 3        # tested: with two vowels the generator could not find enough distinct short endings in about half the trials
VOCAB_NEED = 8000     # distinct words of up to three syllables: about four times the 2,000-word vocabulary, so every word can be unique and
#                       far enough from the others (the build itself makes the final check)


def capacity_of(c_total: int, v: int, templates: dict) -> int:
    """Distinct words of up to three syllables that `c_total` consonants (complex ones count once each) and `v` vowels allow."""
    total = 0
    for t, w in templates.items():
        if w <= 0:
            continue
        n = 1
        for ch in t:
            n *= v if ch == "V" else c_total
        total += n
    return total + total ** 2 + total ** 3


def min_consonants(v: int, templates: dict, units: int = 0) -> int:
    """Fewest ordinary consonants that still give a unique, consistent vocabulary with `v` vowels."""
    for b in range(4, len(BASE_CONSONANTS) + 1):
        if capacity_of(b + units, v, templates) >= VOCAB_NEED:
            return b
    return len(BASE_CONSONANTS) + 1            # not reachable with these syllable shapes


def min_vowels(c_total: int, templates: dict) -> int:
    for v in range(MIN_VOWELS, len(VOWELS) + 1):
        if capacity_of(c_total, v, templates) >= VOCAB_NEED:
            return v
    return len(VOWELS) + 1


def feasible(c_total: int, v: int, templates: dict) -> bool:
    return v >= MIN_VOWELS and capacity_of(c_total, v, templates) >= VOCAB_NEED


def minimums(spec: LanguageSpec) -> dict:
    t, units = spec.phonology.syllable_templates, len(spec.phonology.complex_consonants)
    return {"consonants": {str(v): min_consonants(v, t, units) for v in range(MIN_VOWELS, len(VOWELS) + 1)},
            "vowels": {str(b): min_vowels(b + units, t) for b in range(4, len(BASE_CONSONANTS) + 1)},
            "need": VOCAB_NEED}
