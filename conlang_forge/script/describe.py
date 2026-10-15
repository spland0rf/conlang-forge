"""Design by description: turn a user's words about how a writing system should look into dial settings.

The model (or, without one, a keyword reader) only ever proposes values for dials in the catalogue; every value is
validated here, so nothing it says can set an unknown dial or an out-of-range value. Proposals carry a short piece of
evidence so the user can see why each was suggested and untick what they disagree with."""
from __future__ import annotations

import json
import re

from .spec import DIALS

# dials a description can set. consonants and vowels come from the language; the two tolerances are technical.
SETTABLE = [k for k in DIALS if k not in ("consonants", "vowels", "min_distance", "frame_tolerance")]
MAX_CHARS = 1500

SYSTEM = """You help design an invented writing system. The user describes how they would like it to look. Choose settings \
from the allowed list that match their words. Answer with JSON only:
{"settings":[{"key":"...","value":<an allowed value>,"evidence":"the user's own words that led to it, a few words"}],\
"notes":"one short sentence on anything you could not express"}
Rules: only set a dial the description gives evidence for; never invent evidence; use only the listed keys and values; \
numbers must stay inside the listed range.
Guide: "vertical/upright lines" -> stroke_bias vertical; "diagonals, slashes" -> diagonal; "vertical and diagonal" -> \
vertical+diagonal; "curves, loops, round" -> round; "angular, spiky, sharp" -> family spikey; "flowing, curvy" -> family curvy; \
"bubbly, circles" -> family bubbly; "blocky, boxy, square" -> family boxy; "like Latin or Greek letters" -> family classic. \
"circles/dots/ticks/hooks as diacritics or modifying marks" -> mark_shape. "rises from a solid baseline, connected along the \
bottom" -> joining baseline; "hangs from a top bar" -> topline bar. "vowel signs around consonants" -> kind abugida. \
"simple, bold, minimal" -> complexity near 0.85; "ornate, intricate" -> near 0.15."""


def menu() -> str:
    lines = []
    for k in SETTABLE:
        rule, desc = DIALS[k]
        vals = f"number {rule[0]} to {rule[1]}" if all(isinstance(x, (int, float)) for x in rule) and len(rule) == 2 else "one of " + ", ".join(rule)
        lines.append(f"- {k} ({vals}): {desc}")
    return "\n".join(lines)


def prompt(text: str) -> str:
    return "Allowed settings:\n" + menu() + "\n\nDescription:\n" + clean(text)


def clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:MAX_CHARS]


def valid(key, value):
    """The value if it is allowed for this dial (numbers are rounded to two places), else raise ValueError."""
    if key not in SETTABLE:
        raise ValueError("unknown dial")
    rule = DIALS[key][0]
    if len(rule) == 2 and all(isinstance(x, (int, float)) for x in rule):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not rule[0] <= value <= rule[1]:
            raise ValueError("out of range")
        return int(value) if key in ("motif_count",) else round(float(value), 2)
    if value not in rule:
        raise ValueError("not an allowed value")
    return value


def _item(key, value, evidence, source):
    return {"key": key, "value": value, "evidence": str(evidence)[:160], "source": source}


def parse(reply: str) -> tuple[list, str]:
    """(proposals, note) from a model reply. Anything invalid is dropped; the first proposal for a dial wins."""
    m = re.search(r"\{.*\}", reply or "", flags=re.S)
    if not m:
        return [], ""
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return [], ""
    out, seen = [], set()
    for it in data.get("settings", []) if isinstance(data, dict) else []:
        if not isinstance(it, dict) or it.get("key") in seen:
            continue
        try:
            out.append(_item(it["key"], valid(it["key"], it.get("value")), it.get("evidence", ""), "model"))
        except (ValueError, KeyError, TypeError):
            continue
        seen.add(it["key"])
    return out, str(data.get("notes", ""))[:240] if isinstance(data, dict) else ""


# ---------------------------------------------------------------------------------------------- without a model
def _has(text, pattern):
    m = re.search(pattern, text)
    return m.group(0) if m else None


def keywords(text: str) -> list:
    """A plain keyword reader: covers the common phrases, so the feature still works with no model connected."""
    t = " " + clean(text).lower() + " "
    out, seen = [], set()

    def add(key, value, ev):
        if key not in seen and ev:
            seen.add(key)
            out.append(_item(key, value, ev, "keywords"))

    for pat, val in ((r"abugida|vowel signs?|signs? around", "abugida"), (r"abjad|consonants? only|no vowels", "abjad"),
                     (r"\balphabet", "alphabet")):
        add("kind", val, _has(t, pat))
    fam = [("spikey", r"spik[ey]+|spiky|angular|pointy|sharp|jagged"), ("curvy", r"curvy|flowing|cursive|swoop|wavy"),
           ("bubbly", r"bubbl[ey]+|circular|circles? as (?:the )?(?:main|base)"), ("boxy", r"box[ey]+|block[ey]+|square|rectang"),
           ("classic", r"latin|greek|phoenician|classic|letter-?like")]
    for val, pat in fam:
        ev = _has(t, pat)
        if ev:
            add("family", val, ev)
            break
    v, h_, d, r = (_has(t, r"vertical|upright|tall lines|straight up"), _has(t, r"horizontal|flat lines|sideways bars"),
                   _has(t, r"diagonal|slash|slant"), _has(t, r"curves?|curved|loops?|round(?:ed)? (?:letters|shapes|forms)|swirl"))
    if v and d:
        add("stroke_bias", "vertical+diagonal", f"{v} and {d}")
    elif h_ and v:
        add("stroke_bias", "horizontal+vertical", f"{h_} and {v}")
    elif d:
        add("stroke_bias", "diagonal", d)
    elif v:
        add("stroke_bias", "vertical", v)
    elif h_:
        add("stroke_bias", "horizontal", h_)
    elif r and "family" not in seen:
        add("stroke_bias", "round", r)
    mk = re.search(r"(\bcircles?\b|\bdots?\b|\bticks?\b|\bsnorkels?\b|\bhooks?\b)[^.]{0,40}?(diacritic|modifier|modifying|mark|accent|vowel sign)|"
                   r"(diacritic\w*|modifier\w*|modifying elements?|marks|accents)[^.]{0,40}?(\bcircles?\b|\bdots?\b|\bticks?\b|\bsnorkels?\b|\bhooks?\b)", t)
    if mk:
        word = next(g for g in mk.groups() if g and re.match(r"circle|dot|tick|snorkel|hook", g))
        add("mark_shape", {"circle": "circles", "dot": "dots", "tick": "ticks", "snorkel": "snorkels", "hook": "snorkels"}[word.rstrip("s")], mk.group(0))
    ev = _has(t, r"(?:solid|continuous|connected|joined|unbroken)[^.]{0,20}baseline|baseline[^.]{0,20}(?:solid|connected|joined)|rise[s]? from (?:a )?(?:solid )?baseline")
    add("joining", "baseline", ev)
    add("topline", "bar", _has(t, r"top ?bar|top ?line|headline|hang[s]? from (?:a )?(?:top )?line"))
    ev = _has(t, r"simple|minimal|clean|bold|uncluttered")
    add("complexity", 0.85, ev)
    add("complexity", 0.15, _has(t, r"ornate|elaborate|intricate|decorative|detailed|fancy"))
    add("direction", "rtl", _has(t, r"right[- ]to[- ]left|\brtl\b|arabic-like|hebrew-like"))
    add("roundness", 0.0, _has(t, r"crisp corners|sharp corners"))
    add("word_separator", "dot", _has(t, r"dots? between words|dot[- ]separated words"))
    add("density", 0.8, _has(t, r"dense|busy|packed"))
    add("density", 0.2, _has(t, r"sparse|airy|spare|light strokes"))
    return out
