"""Plain-letter spelling: every language is written with the 26 English letters only.

* `fold` turns typed text with accents or special letters into plain approximations, so a visitor who pastes
  "ö" or "š" (or whose phone auto-corrects) still gets a sensible reading.
* `respell` upgrades a language saved before plain spelling existed (diacritic letters) to the plain spelling.
  Only the written form changes; the phonemes, and therefore every word, stay the same.
"""
from __future__ import annotations

import unicodedata

FOLD = {"ä": "ae", "æ": "ae", "ö": "oe", "ø": "oe", "ü": "ue", "ë": "uh", "ə": "uh", "ï": "i", "ß": "ss",
        "š": "sh", "ž": "zh", "č": "ch", "ǧ": "j", "ŋ": "ng", "þ": "th", "ð": "th", "ʔ": "q",
        "ħ": "h", "ɣ": "g", "ł": "l", "đ": "d"}


def own_fold(romanization: dict) -> dict:
    """Special letter -> how this language spells that sound in plain letters (so 'ö' becomes its own 'oe' or 'eu')."""
    return {SPECIAL[p]: s for p, s in romanization.items() if p in SPECIAL and SPECIAL[p] != s}


def fold(text: str, own: dict | None = None) -> str:
    out = []
    for ch in text:
        if own and ch in own:
            out.append(own[ch])
        elif ch in FOLD:
            out.append(FOLD[ch])
        elif ord(ch) < 128:
            out.append(ch)
        else:
            d = unicodedata.normalize("NFD", ch)
            base = "".join(c for c in d if ord(c) < 128)
            out.append(base or ch)
    return "".join(out)


def is_plain(s: str) -> bool:
    return all(c.isascii() for c in s)


def respell(lang: dict) -> bool:
    """Rewrite spellings in a loaded language dict in place. Returns True if anything changed."""
    from .inventory import romanization_map
    from .morph import render_flat
    from .spec import LanguageSpec
    rom = lang.get("spec", {}).get("orthography", {}).get("romanization", {})
    if all(is_plain(v) for v in rom.values()):
        return False
    spec = LanguageSpec.from_dict(lang["spec"])
    ph = spec.phonology
    new = romanization_map("plain", ph.consonants, ph.vowels)
    lang["spec"]["orthography"]["romanization"] = new
    lang["spec"]["orthography"]["style"] = "plain"
    spec = LanguageSpec.from_dict(lang["spec"])
    for e in lang.get("lexicon", []):
        if e.get("phonemes"):
            e["form"], e["ipa"], e["syllables"] = render_flat(spec, e["phonemes"])
    return True


# ---------------------------------------------------------------------------------------------------- display script
# The language itself is stored as sounds (phonemes). Its spelling is only a view: plain English letters by default,
# or "special" letters (š, ŋ, þ, ö ...) on request. Switching never changes the language, only how forms are drawn.
SPECIAL = {"ʔ": "ʼ", "ŋ": "ŋ", "θ": "þ", "ʃ": "š", "ʒ": "ž", "tʃ": "č", "dʒ": "ǧ", "æ": "ä", "ø": "ö", "y": "ü", "ə": "ë"}
SCRIPTS = ("plain", "special")


def with_script(lang: dict, script: str) -> dict:
    """A copy of a loaded language whose spellings are drawn in the requested script ("plain" returns it unchanged)."""
    if script in (None, "", "plain"):
        return lang
    if script not in SCRIPTS:
        raise ValueError("script must be plain or special")
    import copy
    from .morph import render_flat
    from .spec import LanguageSpec
    out = copy.deepcopy(lang)
    rom = out["spec"]["orthography"]["romanization"]
    out["spec"]["orthography"]["romanization"] = {p: SPECIAL.get(p, s) for p, s in rom.items()}
    out["spec"]["orthography"]["style"] = "special"
    spec = LanguageSpec.from_dict(out["spec"])
    for e in out.get("lexicon", []):
        if e.get("phonemes"):
            e["form"], e["ipa"], e["syllables"] = render_flat(spec, e["phonemes"])
    return out
