"""Phoneme pool and romanization tables.

CONSONANTS: ipa -> (digraph romanization, diacritic romanization, manner, base_freq)
base_freq is a rough cross-linguistic commonness (0..1) used to bias sampling.
"""
CONSONANTS = {
    "p": ("p", "p", "stop", .90), "b": ("b", "b", "stop", .60),
    "t": ("t", "t", "stop", .95), "d": ("d", "d", "stop", .65),
    "k": ("k", "k", "stop", .95), "g": ("g", "g", "stop", .60),
    "ʔ": ("q", "ʼ", "stop", .30),
    "m": ("m", "m", "nasal", .95), "n": ("n", "n", "nasal", .95),
    "ŋ": ("ng", "ŋ", "nasal", .35),
    "f": ("f", "f", "fricative", .40), "v": ("v", "v", "fricative", .35),
    "θ": ("th", "þ", "fricative", .10), "s": ("s", "s", "fricative", .85),
    "z": ("z", "z", "fricative", .40), "ʃ": ("sh", "š", "fricative", .45),
    "ʒ": ("zh", "ž", "fricative", .15), "x": ("kh", "x", "fricative", .20),
    "h": ("h", "h", "fricative", .50),
    "tʃ": ("ch", "č", "affricate", .40), "dʒ": ("j", "ǧ", "affricate", .30),
    "l": ("l", "l", "liquid", .90), "r": ("r", "r", "liquid", .80),
    "w": ("w", "w", "glide", .60), "j": ("y", "y", "glide", .60),
}

# "Complex consonants": two or more sounds that this language treats as ONE consonant, separate from their parts
# (like ts in Russian, tl in Nahuatl, kp in Yoruba, rzh as in Czech). ipa -> (spelling, manner, parts, base_freq).
# They fill one consonant slot in a syllable, count once toward consonant runs, and get their own letter and share.
UNIT_DATA = {
    "ts": ("ts", "affricate", ("t", "s"), .14), "dz": ("dz", "affricate", ("d", "z"), .08),
    "tɬ": ("tl", "affricate", ("t", "l"), .07), "pf": ("pf", "affricate", ("p", "f"), .05),
    "kx": ("kx", "affricate", ("k", "x"), .05), "rʒ": ("rzh", "affricate", ("r", "ʒ"), .03),
    "kp": ("kp", "stop", ("k", "p"), .06), "gb": ("gb", "stop", ("g", "b"), .06),
    "mb": ("mb", "stop", ("m", "b"), .10), "nd": ("nd", "stop", ("n", "d"), .10),
    "tθ": ("tth", "affricate", ("t", "θ"), .03),
    "tb": ("tb", "stop", ("t", "b"), .03), "tbl": ("tbl", "affricate", ("t", "b", "l"), .02),
    "zl": ("zl", "affricate", ("z", "l"), .04),
}
UNIT_SPELLINGS = {"ts": ["ts", "tz"], "tɬ": ["tl", "tlh"], "rʒ": ["rzh", "rj"],
                  "tb": ["tb", "tbh"], "tbl": ["tbl", "tbhl"], "zl": ["zl", "zlh"]}
UNITS = list(UNIT_DATA)
UNIT_PAIRS = {parts: u for u, (_, _, parts, _) in UNIT_DATA.items()}     # parts tuple (2 or 3 sounds) -> unit
UNIT_MAX = max(len(p) for p in UNIT_PAIRS)
for _u, (_sp, _m, _parts, _f) in UNIT_DATA.items():
    CONSONANTS[_u] = (_sp, _sp, "affricate", _f)       # units never join clusters: they behave like one consonant
BASE_CONSONANTS = [c for c in CONSONANTS if c not in UNIT_DATA]

# ipa -> (romanization, base_freq)
VOWELS = {
    "a": ("a", .99), "e": ("e", .90), "i": ("i", .95), "o": ("o", .90), "u": ("u", .90),
    "æ": ("ae", .15), "ø": ("oe", .12), "y": ("ue", .10), "ə": ("uh", .20),
}

OBSTRUENT_MANNERS = {"stop", "fricative", "affricate"}
SONORANT_MANNERS = {"nasal", "liquid", "glide"}


def manner(ipa: str) -> str:
    return CONSONANTS[ipa][2]


# Spelling uses only the 26 plain English letters, so every word can be read aloud and typed on any keyboard.
# Each unusual vowel has a list of spellings, best first; the first one that cannot be mistaken for two other letters
# of the same language written side by side is used ("ae" is skipped in a language that has both a and e).
VOWEL_SPELLINGS = {
    "a": ["a"], "e": ["e"], "i": ["i"], "o": ["o"], "u": ["u"],
    "æ": ["ae", "aa", "aeh"], "ø": ["oe", "eu", "oeh"], "y": ["ue", "ui", "ueh"], "ə": ["uh", "ey", "uuh"],
}
# ipa -> how an English speaker would say it (shown in the grammar book and on the language page)
SAY_LIKE = {
    "p": "p in spin", "b": "b in bat", "t": "t in star", "d": "d in dog", "k": "k in sky", "g": "g in go",
    "ʔ": "the catch in uh-oh", "m": "m in man", "n": "n in not", "ŋ": "ng in sing", "f": "f in fan", "v": "v in van",
    "θ": "th in thin", "s": "s in sun", "z": "z in zoo", "ʃ": "sh in ship", "ʒ": "s in measure",
    "x": "ch in Scottish loch", "h": "h in hat", "tʃ": "ch in chip", "dʒ": "j in jam", "l": "l in lip",
    "r": "a tapped or rolled r", "w": "w in wet", "j": "y in yes",
    "a": "a in father", "e": "e in bed", "i": "ee in see", "o": "o in more", "u": "oo in food", "æ": "a in cat",
    "ø": "ur in fur, without the r sound", "y": "ew in few", "ə": "a in about",
    "ts": "ts in cats, as one sound", "dz": "ds in kids, as one sound", "tɬ": "tl in Atlantic, as one sound",
    "pf": "pf in Pfizer, as one sound", "kx": "k and the ch of loch together", "rʒ": "a rolled r and zh together (Czech ř)",
    "kp": "k and p said at the same moment (Yoruba)", "gb": "g and b said at the same moment (Yoruba)",
    "mb": "mb in number, as one sound", "nd": "nd in wonder, as one sound", "tθ": "t and th (thin) together",
    "tb": "t and b said as one quick sound", "tbl": "t, b and l run together as one sound",
    "zl": "z and l said as one sound",
}


def romanization_map(style: str, consonants: list[str], vowels: list[str]) -> dict[str, str]:
    """ipa -> spelling, using plain a-z only. `style` is kept for older specs ("diacritic" now spells the same way)."""
    out = {}
    for c in consonants:
        if c in UNIT_DATA:
            used = set(out.values()) | {CONSONANTS[x][0] for x in consonants if x not in UNIT_DATA}
            out[c] = next((sp for sp in UNIT_SPELLINGS.get(c, [CONSONANTS[c][0]]) if sp not in used), UNIT_SPELLINGS.get(c, [CONSONANTS[c][0]])[-1])
        else:
            out[c] = CONSONANTS[c][0]
    plain_vowels = {v: VOWEL_SPELLINGS[v][0] for v in vowels if len(VOWEL_SPELLINGS[v]) == 1}
    letters = list(out.values()) + list(plain_vowels.values())
    pairs = {a + b for a in letters for b in letters}
    for v in vowels:
        if v in plain_vowels:
            out[v] = plain_vowels[v]
            continue
        cands = VOWEL_SPELLINGS[v]
        out[v] = next((c for c in cands if c not in pairs), cands[-1])
        pairs |= {out[v] + x for x in letters} | {x + out[v] for x in letters}
        letters.append(out[v])
    return out
