"""The writing-system spec: every dial the generator reads, with a prior for each. A spec is resolved from a seed plus
optional pins (same pattern as the language spec): pinned dials are kept, the rest are drawn from the priors, so one
seed always gives the same script and pinning one dial changes only what depends on it."""
from __future__ import annotations

from ..wordgen import rng_for

KINDS = ("alphabet", "abjad", "abugida")
DEFAULT_CONSONANTS = ("p t k b d g m n s h l r f v z j w ʃ tʃ ŋ x dʒ θ ð ɲ q ʔ ts ɣ ʒ kʰ pʰ tʰ").split()
DEFAULT_VOWELS = ("a i u e o ə ɔ ɛ ɪ y ø ɑ æ ʊ").split()

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
    "width": ((0.5, 1.1), "mean letter width relative to x-height"),
    "ascender_share": ((0.0, 0.4), "share of letters that rise above the x-height (alphabets without a topline)"),
    "descender_share": ((0.0, 0.4), "share of letters that drop below the baseline"),
    "topline": (("none", "bar"), "a bar along the top of every letter (the bar joins letters into words)"),
    "joining": (("none", "baseline", "partial"), "letters in a word connect along a join line: all of them (baseline), some of them (partial, like Arabic's non-joining letters), or none"),
    "mirror_share": ((0.0, 0.5), "share of letters that are mirror twins of another letter (related sounds)"),
    "mark_share": ((0.0, 0.4), "share of letters that carry a diacritic mark (alphabets and abjads)"),
    "sign_frames": ((0.0, 1.0), "abugida: share of vowel signs that wrap the letter on two sides"),
    "frame_tolerance": ((0.05, 0.6), "how far a letter's centre of gravity may sit from the middle of the standard letter frame (smaller = more uniform letters)"),
    "motif_count": ((0, 6), "characteristic shapes (ring, X, triangle...) reused across related letters; 0 for none"),
    "motif_share": ((0.0, 1.0), "share of letters in a motif class that are built from the class's shape"),
    "word_separator": (("space", "dot", "none"), "what divides words"),
    "family": (("spikey", "curvy", "bubbly", "boxy"), "main style family of the letters: spikey (peaks, triangles, diamonds), curvy (arcs and waves), bubbly (circles and bowls) or boxy (rectangles and steps)"),
    "family2": (("none", "spikey", "curvy", "bubbly", "boxy"), "an optional second family blended in (vowels and one consonant manner draw from it)"),
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
    spec["layout"] = "satellite" if kind == "abugida" else "linear"
    spec["seed"] = int(seed)
    spec["pins"] = sorted(pins)
    return spec


_NATIVE = {"spikey": "sharp", "curvy": "smooth", "bubbly": "smooth", "boxy": "blocky"}


def _families(spec, pins, seed):
    """Pick the style families (and keep corner_style consistent with them). A pinned corner style steers the choice of
    family; a pinned family steers the corner style."""
    frng = rng_for(seed, "script", "families")
    style = spec["corner_style"]
    if "family" in pins:
        f1 = pins["family"]
    else:
        f1 = {"smooth": frng.choice(["curvy", "bubbly"]), "sharp": "spikey", "blocky": "boxy"}.get(style) or frng.choice(["spikey", "curvy", "bubbly", "boxy"])
    if "family2" in pins:
        f2 = pins["family2"]
    elif style == "mixed" or ("family" in pins and "corner_style" not in pins):
        others = [f for f in ("spikey", "curvy", "bubbly", "boxy") if f != f1]
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
