"""Small English morphology for the restricted English the translator reads and writes.

Only what the shallow parser and printer need: regular and irregular verb forms, plurals, and the reverse (a surface
word back to its possible lemmas). Words that are not in the vocabulary never get here: the lexicon decides what is a word.
"""
from __future__ import annotations

# lemma: (past, past participle)
IRREGULAR_VERBS = {
    "be": ("was", "been"), "bear": ("bore", "borne"), "beat": ("beat", "beaten"), "become": ("became", "become"),
    "begin": ("began", "begun"), "bend": ("bent", "bent"), "bind": ("bound", "bound"), "bite": ("bit", "bitten"),
    "bleed": ("bled", "bled"), "blow": ("blew", "blown"), "break": ("broke", "broken"), "bring": ("brought", "brought"),
    "build": ("built", "built"), "burn": ("burned", "burned"), "burst": ("burst", "burst"), "buy": ("bought", "bought"),
    "catch": ("caught", "caught"), "choose": ("chose", "chosen"), "come": ("came", "come"), "cost": ("cost", "cost"),
    "cut": ("cut", "cut"), "deal": ("dealt", "dealt"), "dig": ("dug", "dug"), "do": ("did", "done"),
    "draw": ("drew", "drawn"), "dream": ("dreamed", "dreamed"), "drink": ("drank", "drunk"), "drive": ("drove", "driven"),
    "eat": ("ate", "eaten"), "fall": ("fell", "fallen"), "feed": ("fed", "fed"), "feel": ("felt", "felt"),
    "fight": ("fought", "fought"), "find": ("found", "found"), "flee": ("fled", "fled"), "fly": ("flew", "flown"),
    "forget": ("forgot", "forgotten"), "forgive": ("forgave", "forgiven"), "freeze": ("froze", "frozen"),
    "get": ("got", "got"), "give": ("gave", "given"), "go": ("went", "gone"), "grind": ("ground", "ground"),
    "grow": ("grew", "grown"), "hang": ("hung", "hung"), "have": ("had", "had"), "hear": ("heard", "heard"),
    "hide": ("hid", "hidden"), "hit": ("hit", "hit"), "hold": ("held", "held"), "hurt": ("hurt", "hurt"),
    "keep": ("kept", "kept"), "know": ("knew", "known"), "lay": ("laid", "laid"), "lead": ("led", "led"),
    "lean": ("leaned", "leaned"), "leave": ("left", "left"), "lend": ("lent", "lent"), "let": ("let", "let"),
    "lie": ("lay", "lain"), "lose": ("lost", "lost"), "make": ("made", "made"), "mean": ("meant", "meant"),
    "meet": ("met", "met"), "pay": ("paid", "paid"), "put": ("put", "put"), "read": ("read", "read"),
    "ride": ("rode", "ridden"), "ring": ("rang", "rung"), "rise": ("rose", "risen"), "run": ("ran", "run"),
    "say": ("said", "said"), "see": ("saw", "seen"), "seek": ("sought", "sought"), "sell": ("sold", "sold"),
    "send": ("sent", "sent"), "set": ("set", "set"), "shake": ("shook", "shaken"), "shine": ("shone", "shone"),
    "shoot": ("shot", "shot"), "show": ("showed", "shown"), "shrink": ("shrank", "shrunk"), "shut": ("shut", "shut"),
    "sing": ("sang", "sung"), "sink": ("sank", "sunk"), "sit": ("sat", "sat"), "sleep": ("slept", "slept"),
    "slide": ("slid", "slid"), "smell": ("smelled", "smelled"), "speak": ("spoke", "spoken"), "spell": ("spelled", "spelled"),
    "spend": ("spent", "spent"), "spill": ("spilled", "spilled"), "spin": ("spun", "spun"), "split": ("split", "split"),
    "spread": ("spread", "spread"), "spring": ("sprang", "sprung"), "stand": ("stood", "stood"), "steal": ("stole", "stolen"),
    "sting": ("stung", "stung"), "strike": ("struck", "struck"), "swear": ("swore", "sworn"), "swim": ("swam", "swum"),
    "swing": ("swung", "swung"), "take": ("took", "taken"), "teach": ("taught", "taught"), "tear": ("tore", "torn"),
    "tell": ("told", "told"), "think": ("thought", "thought"), "throw": ("threw", "thrown"), "understand": ("understood", "understood"),
    "wake": ("woke", "woken"), "wear": ("wore", "worn"), "win": ("won", "won"), "withdraw": ("withdrew", "withdrawn"),
    "write": ("wrote", "written"), "lie_": ("lied", "lied"),
}
IRREGULAR_PLURALS = {"man": "men", "woman": "women", "child": "children", "foot": "feet", "tooth": "teeth",
                     "mouse": "mice", "person": "people", "wife": "wives", "knife": "knives", "life": "lives",
                     "leaf": "leaves", "shelf": "shelves", "half": "halves", "wolf": "wolves", "elf": "elves",
                     "dwarf": "dwarves", "werewolf": "werewolves", "fish": "fish", "sheep": "sheep", "dice": "dice",
                     "human": "humans", "halfling": "halflings", "ox": "oxen", "goose": "geese"}
INVARIANT_PLURAL = {"fish", "sheep", "dice", "police", "clothes", "news", "pants", "scissors", "troops", "arms", "goods",
                    "stairs", "wages", "tears", "crops", "chemicals", "barracks", "stables", "fireworks", "politics"}
IRREGULAR_BY_FORM = {}
for _l, (_p, _pp) in IRREGULAR_VERBS.items():
    _l = _l.rstrip("_")
    IRREGULAR_BY_FORM.setdefault(_p, []).append((_l, "past"))
    if _pp != _p:
        IRREGULAR_BY_FORM.setdefault(_pp, []).append((_l, "pp"))
REVERSE_PLURAL = {}
for _s, _p in IRREGULAR_PLURALS.items():
    REVERSE_PLURAL.setdefault(_p, _s)
VOWELS = "aeiou"


def _double(w):
    """Consonant doubling for short words ending consonant-vowel-consonant: stop -> stopped."""
    return len(w) >= 3 and w[-1] not in VOWELS + "wxy" and w[-2] in VOWELS and w[-3] not in VOWELS and \
        (len(w) <= 4 or w in {"admit", "begin", "occur", "prefer", "permit", "refer", "regret", "control", "equip"}) and \
        w not in {"open", "visit", "enter", "offer", "listen", "gather", "answer", "travel", "bother", "suffer", "order", "limit",
                  "edit", "target", "happen", "ruin", "wonder", "murder", "honor", "harbor"}


def third(v):
    if v == "be":
        return "is"
    if v == "have":
        return "has"
    if v.endswith(("s", "x", "z", "ch", "sh", "o")):
        return v + "es"
    if v.endswith("y") and v[-2:-1] not in VOWELS:
        return v[:-1] + "ies"
    return v + "s"


def past(v):
    if v == "be":
        return "was"
    if v in IRREGULAR_VERBS:
        return IRREGULAR_VERBS[v][0]
    return _regular(v, "ed")


def participle(v):
    if v in IRREGULAR_VERBS:
        return IRREGULAR_VERBS[v][1]
    return _regular(v, "ed")


def ing(v):
    if v.endswith("ie"):
        return v[:-2] + "ying"
    if v.endswith("e") and not v.endswith(("ee", "oe", "ye")):
        return v[:-1] + "ing"
    return (v + v[-1] if _double(v) else v) + "ing"


def _regular(v, end):
    if v.endswith("e"):
        return v + "d"
    if v.endswith("y") and v[-2:-1] not in VOWELS:
        return v[:-1] + "ied"
    return (v + v[-1] if _double(v) else v) + "ed"


def plural(n):
    if n in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[n]
    if n in INVARIANT_PLURAL:
        return n
    if n.endswith(("s", "x", "z", "ch", "sh")):
        return n + "es"
    if n.endswith("y") and n[-2:-1] not in VOWELS:
        return n[:-1] + "ies"
    if n.endswith("o") and n in {"hero", "potato", "tomato", "echo", "veto"}:
        return n + "es"
    return n + "s"


def verb_candidates(word):
    """(lemma, feature) readings of a surface word as a verb form; feature in base, third, past, pp, ing."""
    w = word.lower()
    out = [(w, "base")]
    for lem, f in IRREGULAR_BY_FORM.get(w, []):
        out.append((lem, f))
    if w in ("is", "are", "am"):
        out.append(("be", "base"))
    if w == "has":
        out.append(("have", "third"))
    if w.endswith("ies"):
        out.append((w[:-3] + "y", "third"))
    if w.endswith("es"):
        out.append((w[:-2], "third"))
    if w.endswith("s") and not w.endswith("ss"):
        out.append((w[:-1], "third"))
    for suf, f in (("ied", "past"), ("ed", "past"), ("d", "past")):
        if w.endswith(suf):
            stem = w[:-len(suf)] + ("y" if suf == "ied" else "")
            out.append((stem, f))
            out.append((stem, "pp"))
            if suf == "ed" and len(stem) > 2 and stem[-1] == stem[-2]:
                out.append((stem[:-1], f))
                out.append((stem[:-1], "pp"))
            if suf == "ed":
                out.append((stem + "e", f))
                out.append((stem + "e", "pp"))
    if w.endswith("ing"):
        stem = w[:-3]
        out.append((stem, "ing"))
        out.append((stem + "e", "ing"))
        if len(stem) > 2 and stem[-1] == stem[-2]:
            out.append((stem[:-1], "ing"))
        if w.endswith("ying"):
            out.append((w[:-4] + "ie", "ing"))
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


def noun_candidates(word):
    """(lemma, 'singular'|'plural') readings of a surface word as a noun."""
    w = word.lower()
    out = [(w, "singular")]
    if w in REVERSE_PLURAL:
        out.append((REVERSE_PLURAL[w], "plural"))
    if w in INVARIANT_PLURAL:
        out.append((w, "plural"))
    if w.endswith("ies"):
        out.append((w[:-3] + "y", "plural"))
    if w.endswith("ves"):
        out += [(w[:-3] + "f", "plural"), (w[:-3] + "fe", "plural")]
    if w.endswith("es"):
        out.append((w[:-2], "plural"))
    if w.endswith("s") and not w.endswith("ss"):
        out.append((w[:-1], "plural"))
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res
