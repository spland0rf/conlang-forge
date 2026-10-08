"""Which inflectional morphemes a language needs, read off its spec. No sounds are chosen here (morph.build_table
draws them), so this module has no dependencies and can be imported by both morph.py and grammar.py.

Categories: number, case, gender (agreement), def (definiteness affix), tense, aspect, mood, evid, agr (verb agreement),
q (question marker), cop (copula particle). Zero-marked values (singular, nominative, present, indicative, the first
listed aspect, ...) have no morpheme. Several morphemes reuse a derivational affix so that, for example, "me = I +OBJ"
and the accusative ending are the same sound: plural -> PLURAL, accusative -> OBJ, genitive -> POSS.
"""
from __future__ import annotations

ZERO_TENSES = ["present", "non-past", "non-future"]
REUSE = {"number:plural": "PLURAL", "case:accusative": "OBJ", "case:genitive": "POSS"}

ABBR = {
    "plural": "PL", "dual": "DU", "paucal": "PAUC", "singular": "SG",
    "nominative": "NOM", "accusative": "ACC", "ergative": "ERG", "absolutive": "ABS", "genitive": "GEN", "dative": "DAT",
    "locative": "LOC", "ablative": "ABL", "instrumental": "INS", "comitative": "COM", "allative": "ALL",
    "vocative": "VOC", "benefactive": "BEN", "partitive": "PART", "essive": "ESS", "translative": "TRANS",
    "inessive": "INESS", "elative": "ELAT",
    "masculine": "M", "feminine": "F", "neuter": "N", "animate": "ANIM", "inanimate": "INAN",
    "past": "PST", "present": "PRS", "future": "FUT", "non-past": "NPST", "non-future": "NFUT",
    "remote past": "RPST", "recent past": "RCPST",
    "perfective": "PFV", "imperfective": "IPFV", "progressive": "PROG", "habitual": "HAB", "completive": "COMPL",
    "continuative": "CONT",
    "indicative": "IND", "imperative": "IMP", "subjunctive": "SBJV", "conditional": "COND", "optative": "OPT",
    "reported": "REP", "inferred": "INFR", "witnessed": "WIT", "definite": "DEF",
}


def abbr(value: str) -> str:
    if value.startswith("class "):
        return "CL" + value[6:]
    return ABBR.get(value, value.upper())


def zero_tense(spec):
    for z in ZERO_TENSES:
        if z in spec.morphology.tenses:
            return z
    return None


def inventory(spec) -> list:
    """Ordered list of {key, category, value, gloss, reuse} for every overt inflectional morpheme."""
    m, syn = spec.morphology, spec.syntax
    items = []

    def add(key, cat, value, gloss):
        items.append({"key": key, "category": cat, "value": value, "gloss": gloss, "reuse": REUSE.get(key)})

    for n in m.noun_number:
        if n != "singular":
            add(f"number:{n}", "number", n, abbr(n))
    for c in m.cases:
        if c not in ("nominative", "absolutive"):
            add(f"case:{c}", "case", c, abbr(c))
    for g in m.genders:
        add(f"gender:{g}", "gender", g, abbr(g))
    if m.definiteness == "definiteness affix":
        add("def:definite", "def", "definite", "DEF")
    tz = zero_tense(spec)
    for t in m.tenses:
        if t != tz:
            add(f"tense:{t}", "tense", t, abbr(t))
    for a in m.aspects[1:]:
        add(f"aspect:{a}", "aspect", a, abbr(a))
    for md in m.moods:
        if md != "indicative":
            add(f"mood:{md}", "mood", md, abbr(md))
    if m.evidentiality:
        for e in ("reported", "inferred"):
            add(f"evid:{e}", "evid", e, abbr(e))
    if m.verb_agreement != "none":
        roles = ["subj"] if m.verb_agreement == "subject" else ["subj", "obj"]
        for role in roles:
            for p in (1, 2, 3):
                for n in ("sg", "pl"):
                    add(f"agr:{role}:{p}{n}", "agr", f"{role}:{p}{n}", f"{p}{n.upper()}" if role == "subj" else f"{p}{n.upper()}.O")
    if syn.question_strategy == "particle":
        add("q:particle", "q", "particle", "Q")
    elif syn.question_strategy == "verbal affix":
        add("q:affix", "q", "affix", "Q")
    if syn.has_copula and syn.copula_form == "particle":
        add("cop", "cop", "particle", "COP")
    return items


def position(spec, category: str) -> str:
    """'prefix' or 'suffix'. In analytic languages these mean "particle before / after the word"."""
    ap = spec.morphology.affix_position
    if ap == "prefixing":
        return "prefix"
    if ap == "suffixing":
        return "suffix"
    if ap == "mixed":
        return {"gender": "prefix", "agr": "prefix", "def": "prefix"}.get(category, "suffix")
    return {"number": "suffix", "case": "suffix", "q": "suffix", "cop": "suffix"}.get(category, "prefix")
