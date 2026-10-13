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
    "roundness": ((0.0, 1.0), "corner rounding when drawn: 1 = smooth curves, 0 = sharp angles (a deliberate angular style)"),
    "width": ((0.5, 1.1), "mean letter width relative to x-height"),
    "ascender_share": ((0.0, 0.4), "share of letters that rise above the x-height (alphabets without a topline)"),
    "descender_share": ((0.0, 0.4), "share of letters that drop below the baseline"),
    "topline": (("none", "bar"), "a bar along the top of every letter (the bar joins letters into words)"),
    "joining": (("none", "baseline"), "letters in a word connect along a join line"),
    "mirror_share": ((0.0, 0.5), "share of letters that are mirror twins of another letter (related sounds)"),
    "mark_share": ((0.0, 0.4), "share of letters that carry a diacritic mark (alphabets and abjads)"),
    "sign_frames": ((0.0, 1.0), "abugida: share of vowel signs that wrap the letter on two sides"),
    "word_separator": (("space", "dot", "none"), "what divides words"),
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
        "roundness": round(rng.choice([0.0] + [0.7, 0.85, 1.0, 1.0, 1.0] * 2), 2),
        "width": round(rng.uniform(0.62, 0.95), 2),
        "ascender_share": 0.0 if topline == "bar" else round(rng.uniform(0.05, 0.3), 2),
        "descender_share": round(rng.uniform(0.04, 0.3), 2),
        "topline": topline,
        "joining": joined,
        "mirror_share": round(rng.uniform(0.0, 0.3), 2),
        "mark_share": 0.0 if kind == "abugida" else round(rng.uniform(0.0, 0.3), 2),
        "sign_frames": round(rng.uniform(0.0, 0.7), 2),
        "word_separator": "dot" if rng.random() < 0.12 else ("none" if rng.random() < 0.05 else "space"),
        "min_distance": 0.22,
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
    spec["layout"] = "satellite" if kind == "abugida" else "linear"
    spec["seed"] = int(seed)
    spec["pins"] = sorted(pins)
    return spec
