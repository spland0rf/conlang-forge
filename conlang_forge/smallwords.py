"""The short common words list.

Pronouns, articles and determiners, conjunctions, negation, interrogatives, prepositions, auxiliaries and
a few adverbs. In real languages these are used so often that they are under heavy pressure to be cheap to
say: mostly one syllable, and they take most of the one- and two-letter words a language has.

Each word has a probability of being "efficient" in a given language (a one-syllable form, preferring the
lightest shapes). The most basic words (and, of, in, not, the, I, you ...) are almost always efficient;
longer or rarer ones (beneath, between, although) only sometimes. The roll for each word is a hash of
(seed, word), so it never depends on what else is in the vocabulary, and upgrades cannot change it.

Only words that exist in the vocabulary version being built are used. Words that are derived from another
word in the root map (me, my, him, she, these ...) are not listed: they inherit their shortness from the
base word plus an affix.
"""
from __future__ import annotations

from .wordgen import rng_for

CLASSES = {
    "pronoun": {"i": .96, "you": .96, "he": .95, "we": .95, "they": .93, "it": .95},
    "article / determiner": {"a": .96, "the": .96, "this": .93, "that": .93, "no": .95, "some": .85, "any": .85,
                             "all": .85, "each": .8, "both": .75, "other": .75, "few": .75, "such": .7,
                             "same": .7, "own": .7},
    "conjunction": {"and": .97, "or": .95, "but": .95, "if": .95, "so": .93, "as": .92, "than": .9, "yet": .75,
                    "while": .6, "since": .55, "until": .6, "because": .5, "unless": .45},
    "negation / answer": {"not": .97, "yes": .9},
    "interrogative": {"who": .93, "what": .93, "how": .9, "which": .85, "when": .85, "where": .85, "why": .85},
    "preposition": {"of": .97, "in": .97, "to": .97, "on": .95, "at": .95, "for": .95, "with": .93, "by": .93,
                    "from": .9, "up": .85, "like": .8, "over": .8, "near": .75, "under": .75, "about": .7,
                    "after": .7, "before": .7, "past": .7, "through": .65, "above": .6, "along": .6,
                    "around": .6, "behind": .55, "below": .55, "toward": .55, "across": .5, "among": .5,
                    "between": .5, "during": .5, "except": .5, "against": .5, "beyond": .4, "beneath": .35},
    "auxiliary / copula": {"be": .93, "have": .93, "is": .9, "do": .9, "can": .9, "will": .88, "am": .85,
                           "are": .85, "may": .8, "must": .7, "might": .65, "could": .65, "would": .65,
                           "should": .6},
    "adverb / particle": {"here": .9, "now": .9, "then": .88, "too": .85, "very": .8, "just": .8, "much": .8,
                          "ever": .75, "again": .7, "even": .7, "else": .65, "still": .6},
}

SHORT = {w: (cls, p) for cls, ws in CLASSES.items() for w, p in ws.items()}

LEAK = .05   # chance that an ordinary (non-list) word or family stem may use a one- or two-letter form
TINY = 2     # "one- and two-letter words"


def is_short_word(cid: str) -> bool:
    return cid in SHORT


def is_efficient(seed: int, cid: str, scale: float = 1.0) -> bool:
    """Does this language give the word an efficient (one-syllable, light) form?"""
    if cid not in SHORT:
        return False
    return rng_for(seed, "smallroll", cid).random() < min(1.0, SHORT[cid][1] * scale)


def tiny_leak(seed: int, key: str, rate: float = LEAK) -> bool:
    """Rare permission for an ordinary word or family stem to use a one- or two-letter form."""
    return rng_for(seed, "tinyleak", key).random() < rate
