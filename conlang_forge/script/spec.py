"""The writing-system spec: every dial the generator reads, with a prior for each. A spec is resolved from a seed plus
optional pins (same pattern as the language spec): pinned dials are kept, the rest are drawn from the priors, so one
seed always gives the same script and pinning one dial changes only what depends on it."""
from __future__ import annotations

from ..wordgen import rng_for
from . import kana
from .forms import SHAPE_DIALS, SHAPE_NAMES

KINDS = ("alphabet", "abjad", "abugida")
DEFAULT_CONSONANTS = ("p t k b d g m n s h l r f v z j w ʃ tʃ ŋ x dʒ θ ð ɲ q ʔ ts ɣ ʒ kʰ pʰ tʰ").split()
DEFAULT_VOWELS = ("a i u e o ə ɔ ɛ ɪ y ø ɑ æ ʊ").split()

STROKE_BIASES = ("balanced", "vertical", "horizontal", "diagonal", "round", "vertical+diagonal", "horizontal+vertical")
MARK_SHAPES = ("any", "dots", "circles", "ticks", "snorkels", "voicing", "pen")
SIGN_SLOTS = ("mixed", "above", "below", "right", "left")

# dial -> (allowed values or (lo, hi) range, description)
DIALS = {
    "kind": (KINDS, "alphabet: every sound a letter; abjad: consonant letters only; abugida: consonant letters with vowel signs"),
    "direction": (("ltr", "rtl"), "writing direction"),
    "consonants": ((6, 34), "number of consonant letters"),
    "vowels": ((3, 12), "number of vowels (letters in an alphabet, signs in an abugida)"),
    "density": ((0.0, 1.0), "how many strokes and junctions a letter body carries"),
    "loops": ((0.0, 1.0), "how often letters contain closed loops"),
    "corner_style": (("mixed", "smooth", "sharp", "blocky"), "mixed: each letter is sharp (V A), smooth (O S), blocky (E H) or hybrid (D P), never smooth and sharp together; or force one style for every letter"),
    "roundness": ((0.0, 1.0), "how round the rounded corners are (1 = full curves; 0 turns every corner crisp)"),
    "width": ((0.5, 1.5), "mean letter width relative to x-height"),
    "ascender_share": ((0.0, 0.4), "share of letters that rise above the x-height (alphabets without a topline)"),
    "descender_share": ((0.0, 0.4), "share of letters that drop below the baseline"),
    "topline": (("none", "bar"), "a bar along the top of every letter (the bar joins letters into words)"),
    "topline_share": ((0.0, 1.0), "with a top bar: the share of letters that carry it; the others are drawn a little shorter, without the bar (as in Bengali), and the bar between letters only joins letters that have one; 1 is a bar on every letter"),
    "joining": (("none", "baseline", "partial"), "letters in a word connect along a join line: all of them (baseline), some of them (partial, like Arabic's non-joining letters), or none"),
    "mirror_share": ((0.0, 0.5), "share of letters that are mirror twins of another letter (related sounds)"),
    "mark_share": ((0.0, 0.4), "share of letters that carry a diacritic mark (alphabets and abjads)"),
    "sign_frames": ((0.0, 1.0), "abugida: share of vowel signs that wrap the letter on two sides"),
    "frame_tolerance": ((0.05, 0.6), "how far a letter's centre of gravity may sit from the middle of the standard letter frame (smaller = more uniform letters)"),
    "motif_count": ((0, 6), "characteristic shapes (ring, X, triangle...) reused across related letters; 0 for none"),
    "motif_share": ((0.0, 1.0), "share of letters in a motif class that are built from the class's shape"),
    "word_separator": (("space", "dot", "none"), "what divides words"),
    "family": (("spikey", "curvy", "bubbly", "boxy", "classic", "stroke"), "main style family of the letters: spikey (peaks, triangles, diamonds), curvy (arcs and waves), bubbly (circles and bowls), boxy (rectangles and steps), classic (letter-like figures of the Phoenician, Greek and Latin kind) or stroke (letters of a few separate short strokes, like the Japanese kana)"),
    "family2": (("none", "spikey", "curvy", "bubbly", "boxy", "classic", "stroke"), "an optional second family blended in (vowels and one consonant manner draw from it; with stroke, the vowels and the approximants are drawn as kana-like stroke letters)"),
    "stroke_hand": (("auto", "angular", "flowing", "bowed", "pen", "cuneiform"), "how stroke letters are drawn: angular (straight strokes and sharp corners, like katakana), flowing (curved strokes, hooks and small loops, like hiragana), bowed (a stem with one or two round bows, curls and rings, like Elvish), pen (letters drawn as a path of strokes that start from the end or middle of one another, like Devanagari, Bengali and Tamil), or auto; only used when the stroke family is in use"),
    "pen_frame": (("auto", "stem", "free"), "for the pen hand: stem (a long vertical stroke the other strokes hang from, as in Devanagari and Bengali), free (loops, curls and hooks chained end to end with no stem, as in Tamil), or auto (stem when the script has a top bar); the corner style decides whether the parts are curvy, spiky or mixed"),
    "stroke_bias": (STROKE_BIASES, "which lines the base letters are built from: vertical, horizontal, diagonal, round (curves and loops), a mix of two, or balanced (no preference)"),
    "vowel_shape": (("auto",) + SHAPE_NAMES, "the characteristic letter shape of vowels (every vowel is this figure plus a small variant); auto lets the generator choose"),
    "plosive_shape": (("auto",) + SHAPE_NAMES, "the characteristic letter shape of plosives (every plosive is this figure plus a small variant); auto lets the generator choose"),
    "fricative_shape": (("auto",) + SHAPE_NAMES, "the characteristic letter shape of fricatives (every fricative is this figure plus a small variant); auto lets the generator choose"),
    "nasal_shape": (("auto",) + SHAPE_NAMES, "the characteristic letter shape of nasals (every nasal is this figure plus a small variant); auto lets the generator choose"),
    "approximant_shape": (("auto",) + SHAPE_NAMES, "the characteristic letter shape of approximants (every approximant is this figure plus a small variant); auto lets the generator choose"),
    "mark_shape": (MARK_SHAPES, "what the diacritics, vowel signs and virama are made of: dots, small circles, short ticks, snorkels (a short stem with a bend), or any of them; pen draws small pen strokes (a stem, a curl, a slash, a hook) in the style of Devanagari vowel signs; voicing draws the voiced-sound mark as two short ticks above the letter and the next feature as a small ring (the kana way), with the other marks as ticks"),
    "vowel_sign_slot": (SIGN_SLOTS, "where abugida vowel signs sit: mixed (any side of the letter, the script chooses), or always above, below, right or left"),
    "stroke_share": ((0.0, 1.0), "share of letters drawn as stroke letters (kana-like, in the stroke hand): 1 for a pure stroke script; a second stroke style fills this share, vowels first; any other script may add some stroke letters too"),
    "stroke_ticks": ((0.0, 1.0), "stroke family: how often a letter gets a small detached tick (as in katakana ツ and hiragana こ)"),
    "stroke_crossings": ((0.0, 1.0), "stroke family: how often a short stroke crosses another stroke of the letter"),
    "stroke_joins": ((0.0, 1.0), "stroke family: how often one stroke is drawn on to another, making a T-junction"),
    "complexity": ((0.0, 1.0), "0 = ornate, pictorial letters with several strokes and small details; 1 = minimal, bold letters of at most three strokes"),
    "min_distance": ((0.1, 0.5), "least visual distance allowed between two letters"),
}


def _prior(rng, kind):
    jt = rng.random()
    topline = "bar" if (kind == "abugida" and jt < 0.45) or (kind != "abugida" and jt < 0.12) else "none"
    joined = "baseline" if topline == "none" and rng.random() < (0.2 if kind == "abjad" else 0.08) else "none"
    return {
        "direction": "rtl" if kind == "abjad" and rng.random() < 0.7 else ("rtl" if rng.random() < 0.07 else "ltr"),
        "consonants": {"alphabet": rng.randint(14, 24), "abjad": rng.randint(18, 28), "abugida": rng.randint(18, 34)}[kind],
        "vowels": {"alphabet": rng.randint(4, 8), "abjad": 0, "abugida": rng.randint(5, 10)}[kind],
        "density": round(rng.uniform(0.15, 0.85), 2),
        "loops": round(rng.uniform(0.0, 1.0), 2),
        "corner_style": rng.choices(["mixed", "smooth", "sharp", "blocky"], [0.4, 0.38, 0.12, 0.1])[0],
        "roundness": round(rng.choice([0.7, 0.85, 1.0, 1.0, 1.0]), 2),
        "width": round(rng.uniform(0.62, 0.95), 2),
        "ascender_share": 0.0 if topline == "bar" else round(rng.uniform(0.0, 0.12), 2),
        "descender_share": round(rng.uniform(0.0, 0.12), 2),
        "topline": topline,
        "joining": joined,
        "mirror_share": round(rng.uniform(0.0, 0.3), 2),
        "mark_share": 0.0 if kind == "abugida" else round(rng.uniform(0.0, 0.3), 2),
        "sign_frames": round(rng.uniform(0.0, 0.7), 2),
        "frame_tolerance": round(rng.uniform(0.15, 0.25), 2),
        "motif_count": rng.choice([4, 4, 5, 5, 6]),
        "motif_share": round(rng.uniform(0.75, 0.95), 2),
        "word_separator": "dot" if rng.random() < 0.12 else ("none" if rng.random() < 0.05 else "space"),
        "min_distance": 0.28,
        "complexity": round(rng.uniform(0.1, 0.95), 2),
        "stroke_bias": "balanced",                       # fixed defaults, no random draw: scripts made before these dials exist are unchanged
        "mark_shape": "any",
        "stroke_hand": "auto",
        "pen_frame": "auto",
        "topline_share": 1.0,
        "vowel_sign_slot": "mixed",
        "stroke_share": 0.0,
        "stroke_ticks": 0.25,
        "stroke_crossings": 0.4,
        "stroke_joins": 0.3,
        "vowel_shape": "auto",
        "plosive_shape": "auto",
        "fricative_shape": "auto",
        "nasal_shape": "auto",
        "approximant_shape": "auto",
    }


def resolve(seed: int, pins: dict | None = None) -> dict:
    """Return the full spec for a seed. Unknown pins and out-of-range values raise ValueError."""
    pins = dict(pins or {})
    for k, v in pins.items():
        if k not in DIALS:
            raise ValueError(f"unknown script dial {k!r}; known: {', '.join(sorted(DIALS))}")
        rule = DIALS[k][0]
        if len(rule) == 2 and all(isinstance(x, (int, float)) for x in rule):
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not rule[0] <= v <= rule[1]:
                raise ValueError(f"{k} must be a number from {rule[0]} to {rule[1]}")
        elif v not in rule:
            raise ValueError(f"{k} must be one of {', '.join(rule)}")
    rng = rng_for(seed, "script", "spec")
    kind = pins.get("kind") or rng.choice(["alphabet"] * 4 + ["abjad"] * 2 + ["abugida"] * 4)
    spec = _prior(rng_for(seed, "script", "prior", kind), kind)
    spec.update(pins)
    spec["kind"] = kind
    if kind == "abjad":
        spec["vowels"] = 0 if "vowels" not in pins else spec["vowels"]
    if spec["topline"] == "bar":
        spec["ascender_share"] = 0.0 if "ascender_share" not in pins else spec["ascender_share"]
    if spec["joining"] == "baseline" and spec["topline"] == "bar" and "joining" not in pins:
        spec["joining"] = "none"
    if spec["corner_style"] == "blocky" and "consonants" not in pins:      # right-angle shapes run out of distinct forms
        spec["consonants"] = min(spec["consonants"], 22)
    _families(spec, pins, seed)
    _stroke_letters(spec, pins, seed)
    spec["layout"] = "satellite" if kind == "abugida" else "linear"
    spec["seed"] = int(seed)
    spec["pins"] = sorted(pins)
    return spec


_NATIVE = {"spikey": "sharp", "curvy": "smooth", "bubbly": "smooth", "boxy": "blocky", "classic": "mixed", "stroke": "mixed"}


def _stroke_letters(spec, pins, seed):
    """Stroke-family letters: settle the hand and, unless pinned, the dials that suit it (how often a letter gets a tick, a
    crossing stroke or a joined stroke). When the stroke family is the main style, also: no top bar, no joining, no ascenders
    or descenders, few mirror twins, and the marks that suit the hand (voicing marks for the kana hands; vowel signs above for
    the bowed one). Nothing is drawn unless the stroke family is in use."""
    if spec["family"] == "stroke":
        spec["stroke_share"] = 1.0                      # every letter is a stroke letter
    elif spec["family2"] == "stroke" and "stroke_share" not in pins:
        spec["stroke_share"] = 0.35                     # a blend: roughly the vowels and approximants
    if "stroke" not in (spec["family"], spec["family2"]) and spec["stroke_share"] <= 0:
        spec["stroke_hand"] = "auto"
        return
    hand = spec["stroke_hand"]
    if hand == "auto":
        hand = rng_for(seed, "script", "hand").choice(["angular", "flowing"])
    spec["stroke_hand"] = hand
    if hand == "pen" and spec["pen_frame"] == "auto":
        spec["pen_frame"] = "stem" if spec["topline"] == "bar" else rng_for(seed, "script", "penframe").choice(["stem", "free"])
    for k, v in (("stroke_ticks", kana.EXTRA_TICK[hand]), ("stroke_crossings", kana.CROSS[hand]), ("stroke_joins", kana.JOIN[hand])):
        if k not in pins:
            spec[k] = v
    if spec["family"] != "stroke":                      # a blend: the other family keeps the script's frame
        return
    if "corner_style" not in pins:
        spec["corner_style"] = "sharp" if hand in ("angular", "cuneiform") else "smooth"
    marks = ((("mark_share", 0.0), ("mark_shape", "any"), ("vowel_sign_slot", "above")) if hand == "bowed" else
             (("mark_share", 0.0), ("mark_shape", "any")) if hand in ("pen", "cuneiform") else (("mark_share", 0.25), ("mark_shape", "voicing")))
    for k, v in (("topline", "none"), ("joining", "none"), ("ascender_share", 0.0), ("descender_share", 0.0), ("mirror_share", 0.0)) + marks:
        if k not in pins:
            spec[k] = v


def _families(spec, pins, seed):
    """Pick the style families (and keep corner_style consistent with them). A pinned corner style steers the choice of
    family; a pinned family steers the corner style."""
    frng = rng_for(seed, "script", "families")
    style = spec["corner_style"]
    if "family" in pins:
        f1 = pins["family"]
    else:
        f1 = {"smooth": frng.choice(["curvy", "bubbly"]), "sharp": "spikey", "blocky": "boxy"}.get(style) or frng.choice(["spikey", "curvy", "bubbly", "boxy", "classic"])
    if "family2" in pins:
        f2 = pins["family2"]
    elif style == "mixed" or ("family" in pins and "corner_style" not in pins):
        others = [f for f in ("spikey", "curvy", "bubbly", "boxy", "classic") if f != f1]
        f2 = frng.choice(others) if frng.random() < 0.55 else "none"
    elif style == "smooth" and f1 in ("curvy", "bubbly") and frng.random() < 0.4:
        f2 = "bubbly" if f1 == "curvy" else "curvy"
    else:
        f2 = "none"
    if f2 == f1:
        f2 = "none"
    if "corner_style" not in pins and "family" in pins:
        native = {_NATIVE[f1]} | ({_NATIVE[f2]} if f2 != "none" else set())
        spec["corner_style"] = native.pop() if len(native) == 1 else "mixed"
    spec["family"], spec["family2"] = f1, f2
