"""Language Spec: the single JSON-serializable description of a language.

Every creation mode (random / settings / exemplar / hybrid) produces a spec.
Everything downstream reads only the spec.

Sampling uses a separate RNG per field (seeded from seed+key), so pinning one
setting never reshuffles the others. `provenance` records whether each field
was "random" or "pinned" (pins are how settings and exemplar analysis plug in).
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass, field

from .inventory import BASE_CONSONANTS, CONSONANTS, OBSTRUENT_MANNERS, UNIT_DATA, UNITS, VOWELS, manner, romanization_map

SCHEMA_VERSION = 1
TYPOLOGIES = ["isolating", "agglutinative", "fusional", "polysynthetic"]
WORD_ORDERS = ["SOV", "SVO", "VSO", "VOS", "OVS", "OSV"]

TEMPLATE_LEVELS = {
    1: {"CV": 1.0},
    2: {"CV": .70, "CVC": .20, "V": .10},
    3: {"CV": .50, "CVC": .30, "V": .10, "VC": .10},
    4: {"CV": .35, "CVC": .30, "CCV": .10, "CCVC": .10, "CVCC": .05, "V": .05, "VC": .05},
    5: {"CV": .20, "CVC": .25, "CCV": .10, "CCVC": .15, "CVCC": .10, "CCVCC": .08, "V": .04, "VC": .04},
}
MAX_CLUSTER = {1: 1, 2: 2, 3: 2, 4: 3, 5: 4}


@dataclass
class Phonology:
    consonants: list
    consonant_weights: dict
    vowels: list
    vowel_weights: dict
    syllable_complexity: int
    syllable_templates: dict
    onset_clusters: list
    coda_consonants: list
    coda_clusters: list
    max_cluster: int
    allow_hiatus: bool
    stress: str
    mean_root_syllables: float
    complex_consonants: list = field(default_factory=list)   # members of `consonants` that act as ONE consonant (ts, tl, kp ...)


@dataclass
class Morphology:
    typology: str
    synthesis_index: float
    affix_position: str
    noun_number: list
    case_alignment: str
    cases: list
    genders: list
    definiteness: str
    tenses: list
    aspects: list
    moods: list
    verb_agreement: str
    evidentiality: bool
    negation: str
    numeral_base: int
    gender_base: str = "male"  # which member of a gender pair is the unmarked root: "male" or "female"


@dataclass
class Syntax:
    word_order: str
    adposition: str
    adjective_order: str
    genitive_order: str
    relative_clause: str
    has_copula: bool
    copula_form: str
    question_strategy: str
    pro_drop: bool


@dataclass
class Orthography:
    style: str
    romanization: dict


@dataclass
class LanguageSpec:
    schema_version: int
    seed: int
    name: str
    phonology: Phonology
    morphology: Morphology
    syntax: Syntax
    orthography: Orthography
    provenance: dict = field(default_factory=dict)
    tuning: dict = field(default_factory=dict)    # odds / rates / generator tendencies; empty = built-in defaults

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "LanguageSpec":
        return LanguageSpec(
            schema_version=d["schema_version"], seed=d["seed"], name=d["name"],
            phonology=Phonology(**d["phonology"]), morphology=Morphology(**d["morphology"]),
            syntax=Syntax(**d["syntax"]), orthography=Orthography(**d["orthography"]),
            provenance=d.get("provenance", {}), tuning=d.get("tuning") or {})


def option_label(o) -> str:
    """Stable text key for an option, used to address its odds in `tuning`."""
    return o if isinstance(o, str) else json.dumps(o, ensure_ascii=False)


class Sampler:
    def __init__(self, seed: int, pins: dict | None, tuning: dict | None = None):
        self.seed, self.pins, self.prov = seed, dict(pins or {}), {}
        self.tuning, self.rec = tuning or {}, {}      # rec: what every random choice could have been (for the settings editor)
        unknown = [k for k in self.pins if k not in KNOWN_KEYS]
        if unknown:
            raise ValueError(f"Unknown pin keys: {unknown}. Known: {sorted(KNOWN_KEYS)}")

    def r(self, key: str) -> random.Random:
        h = hashlib.blake2b(f"{self.seed}|{key}".encode(), digest_size=8).digest()
        return random.Random(int.from_bytes(h, "big"))

    def get(self, key, fn, options=None):
        if key in self.pins:
            v = self.pins[key]
            if options is not None and v not in options:
                raise ValueError(f"Pin {key}={v!r} not in {options}")
            self.prov[key] = "pinned"
            return v
        self.prov[key] = "random"
        return fn()

    def weights(self, key, options, default=None) -> list:
        """The odds in force for a random choice: the built-in ones unless `tuning["odds"]` overrides them."""
        base = list(default) if default is not None else [1.0] * len(options)
        w = list(base)
        over = (self.tuning.get("odds") or {}).get(key)
        if over:
            w = [max(float(over.get(option_label(o), b)), 0.0) for o, b in zip(options, base)]
            if sum(w) <= 0:
                w = list(base)
        self.rec[key] = {"options": options, "weights": w, "default": base}
        return w

    def choice(self, key, options, weights=None):
        w = self.weights(key, options, weights)
        return self.get(key, lambda: self.r(key).choices(options, w)[0], options)

    def tune(self, name, default):
        """A generator tendency (see settings_schema.TUNING); `default` when the language does not override it."""
        v = (self.tuning.get("gen") or {}).get(name)
        return default if v is None else v

    def flag(self, key, default_p, draw=None):
        """A yes/no setting that is random with probability p (overridable in tuning["rates"])."""
        p = (self.tuning.get("rates") or {}).get(key)
        p = default_p if p is None else float(p)
        self.rec[key] = {"options": [True, False], "weights": [p, 1 - p], "default": [default_p, 1 - default_p]}
        return self.get(key, lambda: (draw() if draw else self.r(key).random()) < p, [True, False])


KNOWN_KEYS = {
    "morphology.typology", "morphology.synthesis_index", "morphology.affix_position",
    "morphology.noun_number", "morphology.case_alignment", "morphology.cases",
    "morphology.genders", "morphology.definiteness", "morphology.tenses",
    "morphology.aspects", "morphology.moods", "morphology.verb_agreement",
    "morphology.evidentiality", "morphology.negation", "morphology.numeral_base", "morphology.gender_base",
    "phonology.consonants", "phonology.consonant_weights", "phonology.vowels",
    "phonology.vowel_weights", "phonology.syllable_complexity", "phonology.syllable_templates",
    "phonology.stress", "phonology.mean_root_syllables", "phonology.allow_hiatus",
    "syntax.word_order", "syntax.adposition", "syntax.adjective_order",
    "syntax.genitive_order", "syntax.relative_clause", "syntax.has_copula",
    "syntax.copula_form", "syntax.question_strategy", "syntax.pro_drop",
    "orthography.style", "name",
    "phonology.onset_clusters", "phonology.coda_consonants", "phonology.coda_clusters", "phonology.max_cluster",
    "phonology.consonant_count", "phonology.vowel_count", "phonology.complex_consonants", "phonology.complex_count",
}


def int_range(pair):
    lo, hi = int(pair[0]), int(pair[1])
    return (lo, max(lo, hi))


def _wsample(r, items, weight_of, n):
    """Weighted sampling without replacement (Efraimidis-Spirakis)."""
    keyed = sorted(items, key=lambda x: r.random() ** (1.0 / max(weight_of(x), 1e-9)), reverse=True)
    return keyed[:n]


def _zipf_weights(r, items, noisy, lo=.5, hi=1.1):
    order = sorted(items, key=lambda p: noisy(p) * r.uniform(.7, 1.3), reverse=True)
    a = r.uniform(lo, hi)
    w = {p: 1.0 / (i + 2) ** a for i, p in enumerate(order)}
    total = sum(w.values())
    return {p: round(v / total, 5) for p, v in w.items()}


def _sample_consonants(s: Sampler) -> list:
    """The ordinary (single-sound) consonants. Complex consonants such as ts or tl are chosen separately."""
    r = s.r("phonology.consonants")
    sizes = {"small": (s.tune("small_inventory_min", 8), s.tune("small_inventory_max", 12)),
             "medium": (13, 19), "large": (20, 25)}
    counts = {k: r.randint(*int_range(v)) for k, v in sizes.items()}     # (all three are drawn: keeps older languages stable)
    pick = r.choices(["small", "medium", "large"], s.weights("phonology.consonant_size", ["small", "medium", "large"],
                                                             [.25, .5, .25]))[0]
    n = counts[pick]
    noisy = {p: CONSONANTS[p][3] ** 1.5 * r.uniform(.5, 1.5) for p in BASE_CONSONANTS}
    needs = [(("stop",), 2), (("nasal",), 1), (("liquid", "glide"), 1)]
    forced = s.pins.get("phonology.consonant_count")
    if forced is not None:                                    # the user asked for exactly this many
        n = max(4, min(len(BASE_CONSONANTS), int(forced)))
        chosen = []
        for manners, k in needs + ([(("fricative",), 1)] if n >= 10 else []):
            cand = sorted((c for c in BASE_CONSONANTS if manner(c) in manners and c not in chosen), key=lambda c: -noisy[c])
            chosen += cand[:max(0, k - sum(manner(c) in manners for c in chosen))]
        rest = _wsample(r, [c for c in BASE_CONSONANTS if c not in chosen], lambda p: noisy[p], max(0, n - len(chosen)))
        return sorted(chosen + rest, key=list(CONSONANTS).index)
    chosen = _wsample(r, list(BASE_CONSONANTS), lambda p: noisy[p], n)
    if n >= 10:
        needs.append((("fricative",), 1))
    for manners, k in needs:
        while sum(manner(c) in manners for c in chosen) < k:
            cand = [c for c in BASE_CONSONANTS if manner(c) in manners and c not in chosen]
            chosen.append(max(cand, key=lambda c: CONSONANTS[c][3]))
    return sorted(chosen, key=list(CONSONANTS).index)


COMPLEX_COUNTS = [0, 1, 2, 3, 4, 5, 6, 7, 8]
COMPLEX_ODDS = [.6, .2, .08, .05, .03, .02, .01, .005, .005]


def _sample_units(s: Sampler, base: list, count: int) -> list:
    if count <= 0:
        return []
    r = s.r("phonology.complex_units")
    weight = {u: UNIT_DATA[u][3] * (3 if all(p in base for p in UNIT_DATA[u][2]) else 1) for u in UNITS}
    return sorted(_wsample(r, list(UNITS), lambda u: weight[u], min(count, len(UNITS))), key=UNITS.index)


def _sample_vowels(s: Sampler) -> list:
    r = s.r("phonology.vowels")
    if (s.tuning.get("odds") or {}).get("phonology.vowel_count_odds"):
        n = r.choices([3, 4, 5, 6, 7, 8, 9], s.weights("phonology.vowel_count_odds", [3, 4, 5, 6, 7, 8, 9],
                                                        [1, 1, 3, 1, 1, 1, 1]))[0]
    else:
        s.weights("phonology.vowel_count_odds", [3, 4, 5, 6, 7, 8, 9], [1, 1, 3, 1, 1, 1, 1])
        n = r.choice([3, 4, 5, 5, 5, 6, 7, 8, 9])
    if s.pins.get("phonology.vowel_count") is not None:            # the user asked for exactly this many
        n = max(3, min(len(VOWELS), int(s.pins["phonology.vowel_count"])))
    chosen = _wsample(r, list(VOWELS), lambda v: VOWELS[v][1] ** 2 * r.uniform(.6, 1.4), n)
    return sorted(chosen, key=list(VOWELS).index)


def _clusters(consonants):
    onset = [[a, b] for a in consonants for b in consonants
             if a != b and manner(a) in ("stop", "fricative") and manner(b) in ("liquid", "glide")
             and not (a in ("ʔ", "h"))]
    if "s" in consonants:
        onset += [["s", b] for b in consonants if manner(b) == "stop" and b != "ʔ"]
    return onset


def _build_phonology(s: Sampler, typ: str) -> Phonology:
    base = s.get("phonology.consonants", lambda: _sample_consonants(s))
    if "phonology.consonants" in s.pins:
        s.prov.pop("phonology.consonant_count", None)           # the list decides the count
    else:
        s.prov["phonology.consonant_count"] = "pinned" if "phonology.consonant_count" in s.pins else "random"
    ccount = s.choice("phonology.complex_count", COMPLEX_COUNTS, COMPLEX_ODDS)
    units = s.get("phonology.complex_consonants", lambda: _sample_units(s, base, ccount))
    cons = sorted(list(base) + [u for u in units if u not in base], key=list(CONSONANTS).index)
    cw = s.get("phonology.consonant_weights",
               lambda: _zipf_weights(s.r("cw"), cons, lambda p: CONSONANTS[p][3],
                                                     s.tune("letter_unevenness_min", .5), s.tune("letter_unevenness_max", 1.1)))
    vows = s.get("phonology.vowels", lambda: _sample_vowels(s))
    if "phonology.vowels" in s.pins:
        s.prov.pop("phonology.vowel_count", None)
    else:
        s.prov["phonology.vowel_count"] = "pinned" if "phonology.vowel_count" in s.pins else "random"
    vw = s.get("phonology.vowel_weights",
               lambda: _zipf_weights(s.r("vw"), vows, lambda v: VOWELS[v][1],
                                                     s.tune("letter_unevenness_min", .5), s.tune("letter_unevenness_max", 1.1)))

    cw_by_typ = {"isolating": [.05, .10, .20, .30, .35], "agglutinative": [.25, .30, .20, .15, .10],
                 "fusional": [.20, .25, .25, .18, .12], "polysynthetic": [.20, .25, .25, .18, .12]}[typ]
    if len(cons) < 12:  # small inventories rarely allow heavy clusters (cf. Hawaiian, Japanese)
        cw_by_typ = [cw_by_typ[0] + cw_by_typ[4], cw_by_typ[1] + cw_by_typ[3], cw_by_typ[2], 0, 0]
    cw_by_typ = s.weights("phonology.syllable_complexity", [1, 2, 3, 4, 5], cw_by_typ)
    complexity = s.get("phonology.syllable_complexity",
                       lambda: s.r("phonology.syllable_complexity").choices([1, 2, 3, 4, 5], cw_by_typ)[0],
                       [1, 2, 3, 4, 5])
    templates = dict(TEMPLATE_LEVELS[complexity])

    onset_all = _clusters(cons)
    r = s.r("phonology.clusters")
    onset_default = (r.sample(onset_all, min(len(onset_all), r.randint(*int_range((s.tune("onset_clusters_min", 3), s.tune("onset_clusters_max", 12))))))
                     if onset_all else [])
    onset = s.get("phonology.onset_clusters", lambda: onset_default)

    cfac = {"nasal": 3, "liquid": 2.5, "fricative": 1.5, "stop": 1.5, "affricate": .3, "glide": .5}
    lo_c, hi_c = int_range((s.tune("coda_consonants_min", 2), s.tune("coda_consonants_max", 7)))
    coda_default = _wsample(r, cons, lambda c: cfac[manner(c)] * r.uniform(.5, 1.5),
                            r.randint(min(lo_c, len(cons)), min(hi_c, len(cons))))
    coda_cons = s.get("phonology.coda_consonants", lambda: coda_default)
    stops = [c for c in cons if manner(c) == "stop" and c != "ʔ"]
    coda_cl = s.get("phonology.coda_clusters", lambda: [[a, b] for a in coda_cons for b in stops
                    if a != b and (manner(a) in ("nasal", "liquid") or a == "s")])

    if not onset:
        templates = {t: w for t, w in templates.items() if not t.startswith("CC")}
    if not coda_cl:
        templates = {t: w for t, w in templates.items() if not t.endswith("CC")}
    templates = s.get("phonology.syllable_templates", lambda: templates)
    total = sum(templates.values())
    templates = {t: round(w / total, 4) for t, w in templates.items()}

    mean = s.get("phonology.mean_root_syllables", lambda: round(
        {"isolating": 1.3, "agglutinative": 2.1, "fusional": 1.9, "polysynthetic": 2.5}[typ]
        + s.r("phonology.mean_root_syllables").uniform(-.2, .2), 2))
    return Phonology(
        consonants=cons, consonant_weights=cw, vowels=vows, vowel_weights=vw,
        syllable_complexity=complexity, syllable_templates=templates,
        onset_clusters=onset, coda_consonants=sorted(coda_cons), coda_clusters=coda_cl,
        max_cluster=s.get("phonology.max_cluster", lambda: MAX_CLUSTER[complexity]),
        allow_hiatus=s.flag("phonology.allow_hiatus", .35),
        stress=s.choice("phonology.stress", ["initial", "penultimate", "final", "none"], [.35, .35, .15, .15]),
        mean_root_syllables=mean, complex_consonants=[u for u in units if u in cons])


CASE_EXTRA = ["genitive", "dative", "locative", "ablative", "instrumental", "comitative", "allative",
              "vocative", "benefactive", "partitive", "essive", "translative", "inessive", "elative"]


def _build_morphology(s: Sampler, typ: str) -> Morphology:
    idx = s.get("morphology.synthesis_index", lambda: round(s.r("morphology.synthesis_index").uniform(
        *{"isolating": (1.0, 1.6), "agglutinative": (2.2, 3.2), "fusional": (2.0, 3.0),
          "polysynthetic": (3.5, 5.0)}[typ]), 2))
    r = s.r("morphology.misc")
    pos_w = {"isolating": [1, 0, 0, 0], "agglutinative": [.6, .2, .2, 0], "fusional": [.6, .2, .2, 0],
             "polysynthetic": [.3, .3, .4, 0]}[typ]
    affix = s.choice("morphology.affix_position", ["none", "suffixing", "prefixing", "mixed"],
                     [1, 0, 0, 0] if typ == "isolating" else [0, .6, .2, .2])
    number = s.choice("morphology.noun_number", [[], ["singular", "plural"], ["singular", "dual", "plural"],
                      ["singular", "paucal", "plural"]], [.2, .55, .15, .1])
    align = s.choice("morphology.case_alignment", ["nominative-accusative", "ergative-absolutive"], [.8, .2])

    def mk_cases():
        n = {"isolating": 0, "fusional": r.randint(0, 7), "agglutinative": r.randint(2, 12),
             "polysynthetic": r.randint(0, 6)}[typ]
        if n == 0:
            return []
        core = ["nominative", "accusative"] if align.startswith("nom") else ["ergative", "absolutive"]
        return (core + r.sample(CASE_EXTRA, min(len(CASE_EXTRA), max(0, n - 2))))[:max(n, 2)]
    cases = s.get("morphology.cases", mk_cases)
    genders = s.choice("morphology.genders", [[], ["masculine", "feminine"], ["masculine", "feminine", "neuter"],
                       ["animate", "inanimate"], [f"class {i}" for i in range(1, r.randint(4, 8) + 1)]],
                       [.45, .2, .1, .15, .1])
    agree_w = {"isolating": [1, 0, 0, 0], "agglutinative": [.25, .3, .25, .2], "fusional": [.2, .4, .3, .1],
               "polysynthetic": [0, .05, .25, .7]}[typ]
    return Morphology(
        typology=typ, synthesis_index=idx, affix_position=affix, noun_number=number,
        case_alignment=align, cases=cases, genders=genders,
        definiteness=s.choice("morphology.definiteness", ["none", "definite article", "definite+indefinite articles",
                              "definiteness affix"], [.4, .2, .2, .2]),
        tenses=s.choice("morphology.tenses", [[], ["past", "non-past"], ["past", "present", "future"],
                        ["future", "non-future"], ["remote past", "recent past", "present", "future"]],
                        [.1, .35, .35, .1, .1]),
        aspects=s.choice("morphology.aspects", [[], ["perfective", "imperfective"],
                         ["perfective", "imperfective", "progressive", "habitual"], ["completive", "continuative"]],
                         [.2, .4, .25, .15]),
        moods=s.choice("morphology.moods", [["indicative"], ["indicative", "imperative"],
                       ["indicative", "imperative", "subjunctive"],
                       ["indicative", "imperative", "subjunctive", "conditional", "optative"]], [.15, .35, .3, .2]),
        verb_agreement=s.choice("morphology.verb_agreement", ["none", "subject", "subject+object", "polypersonal"],
                                agree_w),
        evidentiality=s.flag("morphology.evidentiality", .1, draw=r.random),
        negation=s.choice("morphology.negation", ["particle before verb", "particle after verb", "verbal affix",
                          "auxiliary verb", "double negation particle"],
                          [.4, .2, 0, 0, .4] if typ == "isolating" else [.25, .15, .35, .1, .15]),
        numeral_base=s.choice("morphology.numeral_base", [10, 20, 5, 12, 8], [.7, .12, .1, .05, .03]),
        gender_base=s.choice("morphology.gender_base", ["male", "female"], [.5, .5]))


def _build_syntax(s: Sampler, typ: str) -> Syntax:
    wo = s.choice("syntax.word_order", WORD_ORDERS, [45, 42, 9, 3, 1, .5])
    ov = wo.index("O") < wo.index("V")
    p_post = {"SOV": .9, "SVO": .3, "VSO": .08, "VOS": .15, "OVS": .85, "OSV": .9}[wo]
    return Syntax(
        word_order=wo,
        adposition=s.choice("syntax.adposition", ["postposition", "preposition"], [p_post, 1 - p_post]),
        adjective_order=s.choice("syntax.adjective_order", ["adjective-noun", "noun-adjective"],
                                 [.6, .4] if ov else [.35, .65]),
        genitive_order=s.choice("syntax.genitive_order", ["genitive-noun", "noun-genitive"],
                                [.7, .3] if ov else [.3, .7]),
        relative_clause=s.choice("syntax.relative_clause", ["prenominal", "postnominal"],
                                 [.5, .5] if ov else [.1, .9]),
        has_copula=s.flag("syntax.has_copula", .6),
        copula_form=s.choice("syntax.copula_form", ["verb", "particle", "zero"], [.4, .3, .3]),
        question_strategy=s.choice("syntax.question_strategy", ["particle", "intonation", "verb inversion",
                                   "verbal affix"], [.35, .3, .1, .25]),
        pro_drop=s.flag("syntax.pro_drop", .8 if typ == "polysynthetic" else .5))


def sample_spec(seed: int, pins: dict | None = None, tuning: dict | None = None, recorder: dict | None = None) -> LanguageSpec:
    """Sample a full language spec. `pins` maps dotted keys to fixed values; `tuning` overrides odds and rates.
    `recorder`, if given, is filled with every random choice and the odds it was made with."""
    s = Sampler(seed, pins, tuning)
    typ = s.choice("morphology.typology", TYPOLOGIES, [.2, .3, .35, .15])
    ph = _build_phonology(s, typ)
    morph = _build_morphology(s, typ)
    syn = _build_syntax(s, typ)
    style = s.choice("orthography.style", ["plain"], [1])
    ortho = Orthography(style=style, romanization=romanization_map(style, ph.consonants, ph.vowels))
    spec = LanguageSpec(SCHEMA_VERSION, seed, "", ph, morph, syn, ortho)
    from .wordgen import make_name  # local import: wordgen reads the spec
    spec.name = s.get("name", lambda: make_name(spec))
    spec.provenance = dict(sorted(s.prov.items()))
    spec.tuning = json.loads(json.dumps(tuning)) if tuning else {}
    if recorder is not None:
        recorder.update(s.rec)
    return spec


def validate_spec(spec: LanguageSpec) -> list[str]:
    """Return a list of problems (empty if the spec is internally consistent)."""
    ph, errs = spec.phonology, []
    if not set(ph.consonants) <= set(CONSONANTS):
        errs.append("unknown consonant in inventory")
    if not set(ph.vowels) <= set(VOWELS):
        errs.append("unknown vowel in inventory")
    if set(ph.consonant_weights) != set(ph.consonants):
        errs.append("consonant_weights keys differ from inventory")
    if set(ph.vowel_weights) != set(ph.vowels):
        errs.append("vowel_weights keys differ from inventory")
    if not any(t.startswith("C") for t in ph.syllable_templates):
        errs.append("need at least one consonant-initial syllable template")
    if len(ph.vowels) < 2:
        errs.append("need at least two vowels")
    return errs
