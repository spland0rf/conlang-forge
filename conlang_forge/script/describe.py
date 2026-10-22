"""Design by description: turn a user's words about how a writing system should look into dial settings.

The model (or, without one, a keyword reader) only ever proposes values for dials in the catalogue; every value is
validated here, so nothing it says can set an unknown dial or an out-of-range value. Proposals carry a short piece of
evidence so the user can see why each was suggested and untick what they disagree with."""
from __future__ import annotations

import json
import math
import re

from .forms import SHAPE_DIALS, SHAPE_NAMES
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
"bubbly, circles" -> family bubbly; "blocky, boxy, square" -> family boxy; "like Latin or Greek letters" -> family classic; "like katakana" -> family stroke with stroke_hand angular; "like hiragana" \
-> family stroke with stroke_hand flowing; "like Elvish" or "stems with round bows" -> family stroke with stroke_hand bowed. \
"circles/dots/ticks/hooks as diacritics or modifying marks" -> mark_shape; "dakuten", "voicing marks" or "two ticks above" -> mark_shape voicing. "rises from a solid baseline, connected along the \
bottom" -> joining baseline; "hangs from a top bar" -> topline bar. "vowel signs around consonants" -> kind abugida. \
"vowels are rings / circles" -> vowel_shape ring (likewise plosive_shape for stops, fricative_shape, nasal_shape, \
approximant_shape; set one per sound class the user names, and for "consonants" set the four consonant dials); "triangles" -> \
triangle, "boxes/squares" -> box, "zigzags" -> zigzag. Only use shape names from the list. \
"simple, bold, minimal" -> complexity near 0.85; "ornate, intricate" -> near 0.15."""


def menu() -> str:
    lines = []
    for k in SETTABLE:
        rule, desc = DIALS[k]
        if k in SHAPE_DIALS.values():
            lines.append(f"- {k} (auto or a shape name from the list below): {desc}")
            continue
        vals = f"number {rule[0]} to {rule[1]}" if all(isinstance(x, (int, float)) for x in rule) and len(rule) == 2 else "one of " + ", ".join(rule)
        lines.append(f"- {k} ({vals}): {desc}")
    lines.append("Shape names: " + ", ".join(SHAPE_NAMES))
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


_SHAPE_WORDS = [("double ring", r"double[- ]rings?|two rings|concentric"), ("ring with cross", r"rings? with (?:a )?cross"),
                ("ring", r"rings?|circles?|circular|loops?|round"), ("inverted triangle", r"inverted triangles?|upside-down triangles?"),
                ("triangle", r"triangles?|triangular|pyramids?"), ("diamond", r"diamonds?|lozenges?"), ("zigzag", r"zig-?zags?|lightning"),
                ("double box", r"double (?:boxes|squares)"), ("box", r"boxes|box|squares?|rectang\w+"), ("plus", r"plus(?:es)?(?: signs?)?|crosses|cross"),
                ("comb", r"combs?|rakes?|forks?"), ("trident", r"tridents?"), ("wave", r"waves?|wavy"), ("arch", r"arch(?:es)?"),
                ("cup", r"cups?|bowls?"), ("curl", r"curls?|spirals?|swirls?"), ("arc", r"arcs?|crescents?"), ("S curve", r"s-?curves?|snakes?")]
_SHAPE_GROUPS = [("vowel", r"vowels?"), ("plosive", r"plosives?|stops?"), ("fricative", r"fricatives?|sibilants?"), ("nasal", r"nasals?"),
                 ("approximant", r"approximants?|liquids?|glides?"), ("consonant", r"consonants?")]


def _shapes(t):
    """(sound class, shape name, evidence) for phrases like "vowels are rings" or "triangular stops"."""
    found = []
    for shp, sp in _SHAPE_WORDS:
        for grp, gp in _SHAPE_GROUPS:
            m = re.search(rf"\b(?:{gp})\b[^.;,]{{0,24}}?\b(?:are|as|made (?:of|from)|use|using|with|from|like|shaped like|based on|built (?:on|from))\s+(?:an? |the |all |simple )?(?:{sp})\b", t) \
                or re.search(rf"\b(?:{sp})(?:[- ](?:shaped|based|like))?\s+(?:{gp})\b", t)
            if m:
                found.append((m.start(), grp, shp, m.group(0).strip()))
    found.sort()
    out, taken = [], set()
    for _, grp, shp, ev in found:        # the earliest phrase wins when two shapes compete for one class
        if grp not in taken:
            taken.add(grp)
            out.append((grp, shp, ev))
    return out


def keywords(text: str) -> list:
    """A plain keyword reader: covers the common phrases, so the feature still works with no model connected."""
    t = " " + clean(text).lower() + " "
    out, seen = [], set()

    def add(key, value, ev):
        if key not in seen and ev:
            seen.add(key)
            out.append(_item(key, value, ev, "keywords"))

    shapes = _shapes(t)
    for _, _, ev in shapes:               # words spent on a class's shape do not also set the style of the whole script
        t = t.replace(ev, " ")
    for pat, val in ((r"abugida|vowel signs?|signs? around", "abugida"), (r"abjad|consonants? only|no vowels", "abjad"),
                     (r"\balphabet", "alphabet")):
        add("kind", val, _has(t, pat))
    kat, hira = _has(t, r"katakana|angular kana"), _has(t, r"hiragana|cursive kana|flowing kana")
    elf = _has(t, r"elvish|elven|stems? with (?:round )?bows?|round bows?")
    kana_ev = kat or hira or elf or _has(t, r"\bkana\b|few short strokes|short separate strokes|brush[- ]?strokes? letters?")
    if kana_ev:
        add("family", "stroke", kana_ev)
        add("stroke_hand", "angular" if kat else "flowing" if hira else "bowed" if elf else "auto", kat or hira or elf)
    add("mark_shape", "voicing", _has(t, r"dakuten|voicing marks?|voiced[- ]sound marks?|two ticks? (?:above|over)"))
    fam = [("spikey", r"spik[ey]+|spiky|\bangular|pointy|sharp|jagged"), ("curvy", r"curvy|flowing|cursive|swoop|wavy"),
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
    for grp, shp, ev in shapes:
        for dial in (SHAPE_DIALS[g] for g in (["plosive", "fricative", "nasal", "approximant"] if grp == "consonant" else [grp])):
            add(dial, shp, ev)
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


# ---------------------------------------------------------------------------------------------- from a picture
IMAGE_TYPES = {"image/png": b"\x89PNG", "image/jpeg": b"\xff\xd8", "image/webp": b"RIFF"}
MAX_IMAGE_B64 = 2_800_000            # about 2 MB of picture; the browser shrinks pictures well below this first
IMAGE_SYSTEM = """You help design an invented writing system from a picture of sample letters the user likes. Describe the \
STYLE the picture suggests (what the strokes are like, how marks are made, whether letters sit on a line, how ornate or \
plain it is) and choose settings from the allowed list. Do not transcribe the letters, name a real script or font, or try \
to reproduce particular letterforms: only choose settings. Measurements computed from the picture's pixels are given; \
trust them over your impression for line directions. Answer with JSON only:
{"settings":[{"key":"...","value":<an allowed value>,"evidence":"what in the picture led to it, a few words"}],\
"notes":"one short sentence on anything you could not express"}
Only set a dial the picture gives evidence for; use only the listed keys and values."""


def clean_measures(raw) -> dict:
    """The numbers the browser measured from the picture, checked. Raises ValueError for anything out of shape."""
    if not isinstance(raw, dict):
        raise ValueError("measures must be an object")
    o = raw.get("orientation")
    if not (isinstance(o, list) and len(o) == 12 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and 0 <= x <= 1 for x in o)):
        raise ValueError("orientation must be 12 numbers from 0 to 1")
    out = {"orientation": [float(x) for x in o]}
    for k, hi in (("ink", 1.0), ("holes", 50.0), ("baseline", 1.0), ("topline", 1.0), ("components", 100000)):
        v = raw.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= hi:
            raise ValueError(f"{k} must be a number from 0 to {hi:g}")
        out[k] = float(v)
    return out


def _pct(x):
    return f"{round(100 * x)}%"


def measure_proposals(m: dict) -> list:
    """What the pixel measurements alone say (works with no model): line directions, a baseline or top bar, how much ink."""
    o = m["orientation"]
    tot = sum(o) or 1.0
    o = [x / tot for x in o]
    v, h = o[5] + o[6], o[0] + o[11]          # bins are 15 degrees wide, 0 = horizontal strokes
    d = 1.0 - v - h
    out = []

    def add(key, value, ev):
        out.append(_item(key, value, ev, "image"))

    off = [o[i] for i in (1, 2, 3, 4, 7, 8, 9, 10)]       # directions that are neither vertical nor horizontal
    t = sum(off)
    spread = (-sum(x / t * math.log(x / t) for x in off if x > 0) / math.log(8)) if t > 0 else 0.0   # 1 = every direction equally
    if t >= 0.3 and spread >= 0.9:                         # curves and loops use every direction about equally; straight diagonals do not
        add("stroke_bias", "round", "line directions are spread evenly, as in curves and loops")
    elif v + d >= 0.75 and v >= 0.2 and d >= 0.2:
        add("stroke_bias", "vertical+diagonal", f"{_pct(v)} of the ink runs vertically and {_pct(d)} diagonally")
    elif h + v >= 0.75 and h >= 0.25 and v >= 0.25:
        add("stroke_bias", "horizontal+vertical", f"{_pct(v)} vertical and {_pct(h)} horizontal ink")
        add("family", "boxy", "mostly horizontal and vertical lines")
    elif d >= 0.5:
        add("stroke_bias", "diagonal", f"{_pct(d)} of the ink runs diagonally")
        add("family", "spikey", "mostly diagonal lines")
    elif v >= 0.45:
        add("stroke_bias", "vertical", f"{_pct(v)} of the ink runs vertically")
    elif h >= 0.4:
        add("stroke_bias", "horizontal", f"{_pct(h)} of the ink runs horizontally")
    if m["baseline"] >= 0.3:
        add("joining", "baseline", "a long line runs along the bottom")
    elif m["topline"] >= 0.3:
        add("topline", "bar", "a long line runs along the top")
    if m["components"] >= 1 and m["holes"] >= 0.8:
        add("loops", 0.8, "most shapes enclose a loop")
    elif m["components"] >= 1 and m["holes"] < 0.15:
        add("loops", 0.15, "few shapes enclose a loop")
    return out


def image_prompt(m: dict) -> str:
    o = [round(x, 3) for x in m["orientation"]]
    return ("Allowed settings:\n" + menu() + "\n\nMeasurements from the picture's pixels:\n"
            f"- share of ink by stroke direction in 15 degree steps from horizontal (0) to just under 180: {o}\n"
            f"- ink covers {_pct(m['ink'])} of the picture; {int(m['components'])} separate shapes; "
            f"{m['holes']:.2f} enclosed loops per shape\n"
            f"- a long line along the bottom: {_pct(m['baseline'])}; along the top: {_pct(m['topline'])}\n\n"
            "The picture of sample letters is attached.")


def check_image(image) -> tuple[str, str]:
    """(media type, base64 data) of an uploaded picture, after cheap checks. Raises ValueError."""
    import base64
    import binascii
    if not isinstance(image, dict):
        raise ValueError("image must be an object with media_type and data")
    mt, data = image.get("media_type"), image.get("data")
    if mt not in IMAGE_TYPES:
        raise ValueError("the picture must be a PNG, JPEG or WebP image")
    if not isinstance(data, str) or not data or len(data) > MAX_IMAGE_B64:
        raise ValueError("the picture is missing or too large (2 MB at most)")
    try:
        head = base64.b64decode(data[:64] + "=" * (-len(data[:64]) % 4))
    except (binascii.Error, ValueError):
        raise ValueError("the picture data is not valid") from None
    if not head.startswith(IMAGE_TYPES[mt]):
        raise ValueError("the file does not look like the image type it claims to be")
    return mt, data
