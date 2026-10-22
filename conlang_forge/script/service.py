"""What the web and mobile clients call: the dial catalogue and a one-shot "build this writing system" that returns the
script, a specimen sheet and a line of sample text. Deterministic for a (seed, pins) pair, so results are cached."""
from __future__ import annotations

import json
from functools import lru_cache

from .generate import generate
from .render import sheet_svg, text_svg
from .layout import sample_words
from .spec import DIALS, resolve

GROUPS = [
    ("Style", ["kind", "family", "family2", "stroke_hand", "corner_style", "complexity", "roundness", "direction"]),
    ("Size", ["consonants", "vowels", "width"]),
    ("Shape mix", ["motif_count", "motif_share", "vowel_shape", "plosive_shape", "fricative_shape", "nasal_shape", "approximant_shape", "density", "loops", "frame_tolerance", "min_distance"]),
    ("Letters", ["stroke_bias", "ascender_share", "descender_share", "mirror_share", "mark_share", "sign_frames", "mark_shape"]),
    ("Joining", ["topline", "joining", "word_separator"]),
]
_LABELS = {
    "kind": "Kind of writing", "family": "Main style", "family2": "Second style", "stroke_hand": "Stroke hand", "corner_style": "Corners", "complexity": "Complexity",
    "roundness": "Roundness", "direction": "Direction", "consonants": "Consonants", "vowels": "Vowels", "width": "Letter width",
    "motif_count": "Characteristic shapes", "motif_share": "Shape reuse", "density": "Strokes per letter", "loops": "Loops",
    "frame_tolerance": "Frame looseness", "min_distance": "Least difference", "ascender_share": "Tall letters",
    "descender_share": "Letters that drop", "mirror_share": "Mirror and turned twins", "mark_share": "Marked letters",
    "vowel_shape": "Vowel shape", "plosive_shape": "Stop shape", "fricative_shape": "Fricative shape", "nasal_shape": "Nasal shape", "approximant_shape": "Approximant shape",
    "sign_frames": "Wrapping vowel signs", "stroke_bias": "Main strokes", "mark_shape": "Marks are made of", "topline": "Top bar", "joining": "Joining", "word_separator": "Word separator",
}
_INTEGER = {"consonants", "vowels", "motif_count"}


def describe_dials() -> dict:
    out = []
    for group, keys in GROUPS:
        for k in keys:
            rule, desc = DIALS[k]
            item = {"key": k, "label": _LABELS.get(k, k), "group": group, "description": desc}
            if len(rule) == 2 and all(isinstance(x, (int, float)) for x in rule):
                item.update(type="number", min=rule[0], max=rule[1], step=1 if k in _INTEGER else 0.01)
            else:
                item.update(type="choice", values=list(rule))
            out.append(item)
    from .presets import PRESETS
    return {"groups": [g for g, _ in GROUPS], "dials": out, "presets": PRESETS}


def _public(script: dict) -> dict:
    return {"spec": script["spec"], "metrics": script.get("metrics"), "script": script}


@lru_cache(maxsize=24)
def generated(seed: int, pins_json: str, phonemes_json: str = "null") -> dict:
    """The generated script (treat as read-only). `phonemes` fixes the sounds it has letters for."""
    return generate(seed, json.loads(pins_json), json.loads(phonemes_json))


@lru_cache(maxsize=64)
def _build(seed: int, pins_json: str, phonemes_json: str = "null") -> str:
    script = generated(seed, pins_json, phonemes_json)
    payload = _public(script)
    payload["specimen"] = sheet_svg(script)
    payload["sample"] = text_svg(script, sample_words(script, 5, "preview"))
    return json.dumps(payload, ensure_ascii=False)


def clean_phonemes(phonemes: dict | None) -> str:
    """Canonical JSON for a {consonants, vowels} inventory (or "null" for the default one)."""
    if not phonemes:
        return "null"
    return json.dumps({"consonants": list(phonemes.get("consonants") or []), "vowels": list(phonemes.get("vowels") or [])},
                      ensure_ascii=False)


def check(seed, pins) -> dict:
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2 ** 31:
        raise ValueError("seed must be a whole number from 0 to 2147483647")
    pins = dict(pins or {})
    resolve(seed, pins)                              # validates the pins before the expensive part
    return pins


def build(seed: int, pins: dict | None, phonemes: dict | None = None) -> dict:
    """Raises ValueError for a bad seed or pin. The returned dict is a fresh copy."""
    pins = check(seed, pins)
    return json.loads(_build(seed, json.dumps(pins, sort_keys=True), clean_phonemes(phonemes)))
