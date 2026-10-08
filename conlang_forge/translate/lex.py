"""The restricted English vocabulary of one language, with the word classes the parser needs."""
from __future__ import annotations

import difflib

from ..grammar import POSSESSIVE, PRONOUN, WH_WORDS
from ..pos import ADJ, ADV, CONJ, DET, INTERJ, NOUN, NUM, PREP, PRON, VERB, pos_of

OBJECT_PRONOUN = {"me": "i", "him": "he", "her": "she", "us": "we", "them": "they"}
POSSESSIVE_WORDS = {v: k for k, v in POSSESSIVE.items()}               # my -> i
DETERMINERS = {"the": "the", "a": "a", "an": "a", "this": "this", "that": "that", "these": "these", "those": "those"}
NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100}
# words the parser reads as sentence machinery, never as content
AUX = {"am", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did", "will", "would", "shall", "have",
       "has", "had", "can", "could", "must", "may", "might", "should"}


class EnglishVocab:
    """Built from a language's lexicon entries (concept_id, lemma, retired)."""

    def __init__(self, entries):
        self.by_lemma, self.pos, self.lemmas, self.lemma_of = {}, {}, set(), {}
        for e in entries:
            if e.get("retired"):
                continue
            cid, lem = e["concept_id"], e["lemma"].lower()
            self.by_lemma.setdefault(lem, cid)
            self.lemmas.add(lem)
            self.pos[cid] = pos_of(cid, e["lemma"])
            self.lemma_of[cid] = lem
        self.concepts = set(self.pos)

    def has(self, word: str) -> bool:
        return word.lower() in self.by_lemma

    def cid(self, word: str):
        return self.by_lemma.get(word.lower())

    def is_pos(self, word: str, *kinds) -> bool:
        c = self.cid(word)
        return bool(c) and any(k in self.pos.get(c, ()) for k in kinds)

    def main_pos(self, word: str):
        c = self.cid(word)
        return (self.pos.get(c) or [None])[0] if c else None

    def suggest(self, word: str, kind: str | None = None, n: int = 4) -> list:
        pool = [l for l in self.lemmas if kind is None or kind in self.pos[self.by_lemma[l]]]
        return difflib.get_close_matches(word.lower(), pool, n=n, cutoff=0.6)

    def words_by_class(self) -> dict:
        """For the Reducer's prompt: vocabulary grouped by part of speech, compact."""
        groups = {NOUN: [], VERB: [], ADJ: [], ADV: [], PREP: [], "other": []}
        for lem in sorted(self.lemmas):
            kinds = self.pos[self.by_lemma[lem]]
            k = kinds[0] if kinds else NOUN
            groups.get(k, groups["other"]).append(lem)
        return groups


__all__ = ["EnglishVocab", "OBJECT_PRONOUN", "POSSESSIVE_WORDS", "DETERMINERS", "NUMBER_WORDS", "AUX", "PRONOUN",
           "WH_WORDS", "NOUN", "VERB", "ADJ", "ADV", "PREP", "CONJ", "DET", "INTERJ", "NUM", "PRON"]
