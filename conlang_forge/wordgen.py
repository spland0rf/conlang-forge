"""Deterministic word generation from a spec.

Each word is derived from hash(seed, concept_id, attempt), never from a running
random stream. Adding, removing or reordering vocabulary therefore cannot change
any other word, which is what makes dictionary upgrades safe.
"""
from __future__ import annotations

import hashlib
import random


def rng_for(seed: int, *parts) -> random.Random:
    h = hashlib.blake2b("|".join(map(str, (seed,) + parts)).encode(), digest_size=8).digest()
    return random.Random(int.from_bytes(h, "big"))


def _pick(r, items, weights):
    return r.choices(items, weights)[0]


def _poisson(r, lam: float) -> int:
    limit, k, p = pow(2.718281828459045, -lam), 0, 1.0
    while True:
        p *= r.random()
        if p <= limit:
            return k
        k += 1


def _syllable(spec, r, first: bool, force_cv: bool = False) -> list:
    ph = spec.phonology
    templates = {"CV": 1.0} if force_cv else ph.syllable_templates
    names, ws = list(templates), list(templates.values())
    t = _pick(r, names, ws)
    for _ in range(25):
        if first or ph.allow_hiatus or not t.startswith("V"):
            break
        t = _pick(r, names, ws)
    else:
        t = next(x for x in names if x.startswith("C"))
    onset_len = len(t) - len(t.lstrip("C"))
    coda_len = len(t) - len(t.rstrip("C"))
    cons, cw = ph.consonants, [ph.consonant_weights[c] for c in ph.consonants]
    out = []
    if onset_len == 1:
        out.append(_pick(r, cons, cw))
    elif onset_len == 2:
        out += _pick(r, ph.onset_clusters, [ph.consonant_weights[a] * ph.consonant_weights[b]
                                           for a, b in ph.onset_clusters])
    out.append(_pick(r, ph.vowels, [ph.vowel_weights[v] for v in ph.vowels]))
    if coda_len == 1:
        cc = ph.coda_consonants
        out.append(_pick(r, cc, [ph.consonant_weights[c] for c in cc]))
    elif coda_len == 2:
        out += _pick(r, ph.coda_clusters, [ph.consonant_weights[a] * ph.consonant_weights[b]
                                          for a, b in ph.coda_clusters])
    return out


def _max_run(spec, syllables) -> int:
    vowels, run, best = set(spec.phonology.vowels), 0, 0
    for p in (p for s in syllables for p in s):
        run = 0 if p in vowels else run + 1
        best = max(best, run)
    return best


def make_word(spec, r, n_syll: int) -> list:
    """Return a list of syllables (each a list of IPA phonemes) obeying max_cluster."""
    for _ in range(40):
        sy = [_syllable(spec, r, i == 0) for i in range(n_syll)]
        if _max_run(spec, sy) <= spec.phonology.max_cluster:
            return sy
    return [_syllable(spec, r, i == 0, force_cv=True) for i in range(n_syll)]


def render(spec, syllables) -> tuple[str, str]:
    """Return (romanized form, IPA string with syllable dots and stress mark)."""
    rom = spec.orthography.romanization
    form = "".join(rom[p] for s in syllables for p in s)
    n = len(syllables)
    mark = {"initial": 0, "final": n - 1, "penultimate": max(n - 2, 0), "none": None}[spec.phonology.stress]
    parts = [("ˈ" if i == mark and n > 1 else "") + "".join(s) for i, s in enumerate(syllables)]
    return form, "/" + ".".join(parts) + "/"


def syllable_count(spec, r, concept: dict, attempt: int) -> int:
    mean = spec.phonology.mean_root_syllables
    if concept["is_function"]:
        mean = max(1.0, mean * .6)
    elif len(concept["lemma"]) >= 9:
        mean += .3
    n = 1 + _poisson(r, max(mean - 1, .05))
    return min(n, 5) + attempt // 4  # lengthen on repeated collisions so uniqueness always terminates


def make_name(spec) -> str:
    r = rng_for(spec.seed, "language-name")
    form, _ = render(spec, make_word(spec, r, r.choice([2, 2, 3])))
    return form[:1].upper() + form[1:]
