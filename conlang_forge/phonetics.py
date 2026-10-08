"""Phonetic distance, used to keep words (and morphemes) distinguishable.

sub_cost(a, b) is a feature-based substitution cost in [0.3, 1.0] (0 for identical phonemes).
Insertions and deletions cost 1.0. pdist() is the weighted edit distance between two phoneme
sequences. MIN_DIST is the smallest distance two distinct words may have.

Because the cheapest substitution costs 0.3 and MIN_DIST is 0.5, "too close" means exactly:
same length and differing in ONE position with a substitution cost below MIN_DIST. NearIndex
exploits this to answer "is any existing word too close?" with a few dictionary lookups.
"""
from __future__ import annotations

from collections import defaultdict

MIN_DIST = 0.5
MIN_SUB = 0.3
assert MIN_DIST <= 2 * MIN_SUB, "NearIndex is only exact while two substitutions always reach MIN_DIST"

# ipa: (manner, fine place, coarse place, voiced)
_CONS = {
    "p": ("stop", 0, "lab", 0), "b": ("stop", 0, "lab", 1),
    "t": ("stop", 3, "cor", 0), "d": ("stop", 3, "cor", 1),
    "k": ("stop", 6, "dor", 0), "g": ("stop", 6, "dor", 1), "ʔ": ("stop", 7, "glo", 0),
    "m": ("nasal", 0, "lab", 1), "n": ("nasal", 3, "cor", 1), "ŋ": ("nasal", 6, "dor", 1),
    "f": ("fric", 1, "lab", 0), "v": ("fric", 1, "lab", 1), "θ": ("fric", 2, "cor", 0),
    "s": ("fric", 3, "cor", 0), "z": ("fric", 3, "cor", 1), "ʃ": ("fric", 4, "cor", 0),
    "ʒ": ("fric", 4, "cor", 1), "x": ("fric", 6, "dor", 0), "h": ("fric", 7, "glo", 0),
    "tʃ": ("aff", 4, "cor", 0), "dʒ": ("aff", 4, "cor", 1),
    "l": ("lat", 3, "cor", 1), "r": ("rho", 3, "cor", 1),
    "w": ("glide", 0, "lab", 1), "j": ("glide", 5, "dor", 1),
    # complex consonants (see inventory.UNIT_DATA)
    "ts": ("aff", 3, "cor", 0), "dz": ("aff", 3, "cor", 1), "tɬ": ("aff", 3.5, "cor", 0), "pf": ("aff", 1, "lab", 0),
    "kx": ("aff", 6, "dor", 0), "rʒ": ("rho", 4, "cor", 1), "kp": ("stop", .5, "lab", 0), "gb": ("stop", .5, "lab", 1),
    "mb": ("stop", .2, "lab", 1), "nd": ("stop", 3.2, "cor", 1), "tθ": ("aff", 2, "cor", 0),
    "tb": ("stop", 2.5, "cor", 1), "tbl": ("aff", 2.8, "cor", 1), "zl": ("aff", 3.2, "cor", 1),
}
# ipa: (height 0 low..2 high, backness 0 front..2 back, rounded)
_VOW = {
    "a": (0, 1, 0), "e": (1, 0, 0), "i": (2, 0, 0), "o": (1, 2, 1), "u": (2, 2, 1),
    "æ": (0, 0, 0), "ø": (1, 0, 1), "y": (2, 0, 1), "ə": (1, 1, 0),
}


def sub_cost(a: str, b: str) -> float:
    if a == b:
        return 0.0
    ca, cb = _CONS.get(a), _CONS.get(b)
    if ca and cb:
        c = 0.5 * (ca[0] != cb[0])
        c += 0.5 if ca[2] != cb[2] else (0.3 if ca[1] != cb[1] else 0.0)
        c += 0.35 * (ca[3] != cb[3])
        return min(1.0, max(MIN_SUB, c))
    va, vb = _VOW.get(a), _VOW.get(b)
    if va and vb:
        c = 0.3 * abs(va[0] - vb[0]) + 0.25 * abs(va[1] - vb[1]) + 0.2 * abs(va[2] - vb[2])
        return min(1.0, max(MIN_SUB, c))
    return 1.0


def pdist(a, b) -> float:
    a, b = list(a), list(b)
    n, m = len(a), len(b)
    prev = [float(j) for j in range(m + 1)]
    for i in range(1, n + 1):
        cur = [float(i)] + [0.0] * m
        for j in range(1, m + 1):
            cur[j] = min(prev[j] + 1.0, cur[j - 1] + 1.0, prev[j - 1] + sub_cost(a[i - 1], b[j - 1]))
        prev = cur
    return prev[m]


class NearIndex:
    """Set of phoneme sequences supporting exact and 'too close' lookups."""

    def __init__(self):
        self.exact: set = set()
        self.masks: dict = defaultdict(list)

    def add(self, w) -> None:
        w = tuple(w)
        if w in self.exact:
            return
        self.exact.add(w)
        for i in range(len(w)):
            self.masks[(w[:i], w[i + 1:])].append(w[i])

    def has(self, w) -> bool:
        return tuple(w) in self.exact

    def near(self, w) -> bool:
        """True if some indexed word differs from w in exactly one position, cheaply."""
        w = tuple(w)
        for i in range(len(w)):
            for p in self.masks.get((w[:i], w[i + 1:]), ()):
                if p != w[i] and sub_cost(p, w[i]) < MIN_DIST:
                    return True
        return False

    def near_count(self, w) -> int:
        """Number of indexed words (other than w itself) that are too close to w."""
        w = tuple(w)
        n = 0
        for i in range(len(w)):
            for p in self.masks.get((w[:i], w[i + 1:]), ()):
                if p != w[i] and sub_cost(p, w[i]) < MIN_DIST:
                    n += 1
        return n
