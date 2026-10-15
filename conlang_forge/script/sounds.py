"""Matching sounds to a writing system: the closest-fit rule behind transliteration.

A script is designed for one set of sounds. When a language with other sounds is written in it, every sound the
script lacks is written with the closest sound it has, the way names are carried between human writing systems
(imperfectly, but readably). Closeness is a small phonetic distance: place, manner and voicing for consonants;
height, backness and rounding for vowels. A complex consonant the script lacks (ts, kp, tl ...) is written as its
parts; a glide (j, w) the script lacks is written with the vowel it resembles (i, u)."""
from __future__ import annotations

from ..inventory import UNIT_DATA

# place: 0 lips, 1 lips+teeth, 2 teeth, 3 ridge, 4 behind the ridge, 5 palate, 6 soft palate, 7 uvula, 8 throat
# (place, manner, voiced, aspirated)
CONS = {
    "p": (0, "stop", 0, 0), "b": (0, "stop", 1, 0), "t": (3, "stop", 0, 0), "d": (3, "stop", 1, 0),
    "k": (6, "stop", 0, 0), "g": (6, "stop", 1, 0), "q": (7, "stop", 0, 0), "ʔ": (8, "stop", 0, 0),
    "pʰ": (0, "stop", 0, 1), "tʰ": (3, "stop", 0, 1), "kʰ": (6, "stop", 0, 1),
    "m": (0, "nasal", 1, 0), "n": (3, "nasal", 1, 0), "ɲ": (5, "nasal", 1, 0), "ŋ": (6, "nasal", 1, 0),
    "f": (1, "fricative", 0, 0), "v": (1, "fricative", 1, 0), "θ": (2, "fricative", 0, 0), "ð": (2, "fricative", 1, 0),
    "s": (3, "fricative", 0, 0), "z": (3, "fricative", 1, 0), "ʃ": (4, "fricative", 0, 0), "ʒ": (4, "fricative", 1, 0),
    "x": (6, "fricative", 0, 0), "ɣ": (6, "fricative", 1, 0), "h": (8, "fricative", 0, 0),
    "tʃ": (4, "affricate", 0, 0), "dʒ": (4, "affricate", 1, 0), "ts": (3, "affricate", 0, 0), "dz": (3, "affricate", 1, 0),
    "l": (3, "lateral", 1, 0), "r": (3, "trill", 1, 0), "w": (0, "glide", 1, 0), "j": (5, "glide", 1, 0),
}
# manner closeness (symmetric); anything not listed is far apart
_MANNER = {
    ("stop", "affricate"): 1.0, ("affricate", "fricative"): 1.0, ("stop", "fricative"): 2.0, ("stop", "nasal"): 1.6,
    ("affricate", "nasal"): 2.6, ("fricative", "nasal"): 2.8, ("lateral", "trill"): 0.7, ("nasal", "lateral"): 2.0,
    ("nasal", "trill"): 2.2, ("fricative", "lateral"): 2.4, ("fricative", "trill"): 2.4, ("glide", "lateral"): 1.6,
    ("glide", "trill"): 1.8, ("glide", "fricative"): 1.8, ("glide", "nasal"): 2.6, ("stop", "lateral"): 3.0,
    ("stop", "trill"): 3.0, ("affricate", "lateral"): 3.0, ("affricate", "trill"): 3.0, ("stop", "glide"): 3.2,
    ("affricate", "glide"): 3.2,
}
# vowels: (height 0 close .. 3 open, backness 0 front .. 2 back, rounded)
VOW = {
    "i": (0, 0, 0), "y": (0, 0, 1), "u": (0, 2, 1), "ɪ": (0.5, 0.3, 0), "ʊ": (0.5, 1.7, 1), "e": (1, 0, 0),
    "ø": (1, 0, 1), "o": (1, 2, 1), "ə": (1.5, 1, 0), "ɛ": (2, 0, 0), "ɔ": (2, 2, 1), "æ": (2.5, 0, 0),
    "a": (3, 1, 0), "ɑ": (3, 2, 0),
}
_GLIDE_VOWEL = {"j": "i", "w": "u"}


def is_consonant(p: str) -> bool:
    return p in CONS or p in UNIT_DATA


def is_vowel(p: str) -> bool:
    return p in VOW


def cdist(a: str, b: str) -> float:
    """Phonetic distance between two single consonants (0 = same)."""
    if a == b:
        return 0.0
    pa, ma, va, aa = CONS[a]
    pb, mb, vb, ab = CONS[b]
    place = abs(pa - pb) * 0.55
    manner = 0.0 if ma == mb else _MANNER.get((ma, mb), _MANNER.get((mb, ma), 3.5))
    return place + manner + (0.8 if va != vb else 0.0) + (0.3 if aa != ab else 0.0)


def vdist(a: str, b: str) -> float:
    if a == b:
        return 0.0
    (ha, ba, ra), (hb, bb, rb) = VOW[a], VOW[b]
    return ((ha - hb) ** 2 * 1.2 + (ba - bb) ** 2 * 0.9) ** 0.5 + (0.7 if ra != rb else 0.0)


def closest(phoneme: str, consonants, vowels) -> dict:
    """How to write one sound with a script that has `consonants` and `vowels` (ipa lists).

    Returns {"to": [ipa, ...], "exact": bool, "cost": float, "how": short explanation}. `to` is empty when the sound is
    simply left out (a throat stop in a script with nothing near it)."""
    cons, vows = list(consonants), list(vowels)
    if phoneme in cons or phoneme in vows:
        return {"to": [phoneme], "exact": True, "cost": 0.0, "how": "same sound"}
    if phoneme in UNIT_DATA:                                         # a complex consonant: write its parts
        parts = UNIT_DATA[phoneme][2]
        subs = [closest(p, cons, vows) for p in parts]
        return {"to": [t for s in subs for t in s["to"]], "exact": False, "cost": sum(s["cost"] for s in subs),
                "how": "written as " + " + ".join(parts)}
    if phoneme in CONS:
        options = [(cdist(phoneme, c), [c], "closest consonant") for c in cons if c in CONS]
        if phoneme in _GLIDE_VOWEL:                                  # j and w are close cousins of i and u
            v = _GLIDE_VOWEL[phoneme]
            if v in vows:
                options.append((1.4, [v], f"written with the vowel {v}"))
        if not options:
            return {"to": [], "exact": False, "cost": 9.0, "how": "left out"}
        cost, to, how = min(options, key=lambda o: o[0])
        if phoneme == "ʔ" and cost > 2.5:
            return {"to": [], "exact": False, "cost": 0.5, "how": "left out (no letter near it)"}
        return {"to": to, "exact": False, "cost": round(cost, 2), "how": how}
    if phoneme in VOW and vows:
        cost, v = min((vdist(phoneme, x), x) for x in vows if x in VOW)
        return {"to": [v], "exact": False, "cost": round(cost, 2), "how": "closest vowel"}
    return {"to": [], "exact": False, "cost": 9.0, "how": "not a known sound"}
