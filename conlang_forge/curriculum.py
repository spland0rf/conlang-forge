"""The beginner course word lists (concept ids from the reduced English vocabulary) and their meaning tags.

Words that a vocabulary version does not contain are skipped, so the same lists work for every vocab version.
Tags drive gender assignment: sex ("m" / "f") for words about people and animals that have a sex, and kind
("person" / "animal" / "plant" / "thing") for animacy and noun-class systems.
"""
from __future__ import annotations

PRONOUNS = ["i", "you", "he", "she", "it", "we", "they"]
OBJECT_PRONOUNS_NOTE = "formed with the object ending"
DEMONSTRATIVES = ["this", "that", "these", "those"]
QUESTION_WORDS = ["who", "what", "which", "where", "when", "why", "how"]
SMALL_WORDS = ["and", "or", "but", "because", "if", "not", "also", "very", "too", "here", "there", "now", "then"]
PREPOSITIONS = ["in", "on", "at", "to", "from", "with", "for", "of", "by", "about", "under", "over"]
NUMBERS = list(range(0, 11))
COLORS = ["red", "orange", "yellow", "green", "blue", "purple", "white", "black", "brown", "pink", "gold", "silver"]
TIME_WORDS = ["today", "tomorrow", "yesterday", "now", "morning", "night", "day"]
GREETING_WORDS = ["hello", "goodbye", "please", "thank", "sorry", "yes", "no"]

# noun: (sex, kind)
NOUNS = {
    "people": {"man": ("m", "person"), "woman": ("f", "person"), "boy": ("m", "person"), "girl": ("f", "person"),
               "child": (None, "person"), "mother": ("f", "person"), "father": ("m", "person"),
               "brother": ("m", "person"), "sister": ("f", "person"), "friend": (None, "person"),
               "king": ("m", "person"), "queen": ("f", "person"), "wizard": (None, "person"),
               "knight": (None, "person"), "priest": (None, "person"), "enemy": (None, "person")},
    "animals": {"dog": (None, "animal"), "cat": (None, "animal"), "horse": (None, "animal"), "bird": (None, "animal"),
                "fish": (None, "animal"), "bear": (None, "animal"), "fox": (None, "animal"), "dragon": (None, "animal")},
    "home and food": {"house": (None, "thing"), "door": (None, "thing"), "table": (None, "thing"), "bed": (None, "thing"),
                      "water": (None, "thing"), "bread": (None, "thing"), "meat": (None, "thing"),
                      "milk": (None, "thing"), "apple": (None, "plant"), "book": (None, "thing"),
                      "sword": (None, "thing"), "gold": (None, "thing")},
    "nature and places": {"sun": (None, "thing"), "moon": (None, "thing"), "star": (None, "thing"),
                          "fire": (None, "thing"), "river": (None, "thing"), "mountain": (None, "thing"),
                          "forest": (None, "plant"), "tree": (None, "plant"), "flower": (None, "plant"),
                          "stone": (None, "thing"), "road": (None, "thing"), "village": (None, "thing"),
                          "city": (None, "thing"), "castle": (None, "thing")},
}
# verb: transitive?
VERBS = {"be": False, "have": True, "go": False, "come": False, "see": True, "hear": True, "eat": True, "drink": True,
         "sleep": False, "love": True, "fight": False, "die": False, "give": True, "say": True, "take": True,
         "make": True, "know": True, "want": True, "need": True, "like": True, "live": False, "work": False,
         "help": True, "ask": True, "tell": True, "think": False, "speak": False, "read": True, "write": True,
         "walk": False, "run": False, "buy": True, "find": True}
ADJECTIVES = ["big", "small", "old", "new", "young", "long", "short", "tall", "hot", "cold", "dark", "strong", "weak",
              "fast", "slow", "happy", "sad", "rich", "poor", "beautiful", "dangerous", "brave", "clean", "good", "bad"]
FAMILY_TERMS = ["mother", "father", "brother", "sister", "son", "daughter", "husband", "wife", "uncle", "aunt"]


def semantics() -> dict:
    out = {}
    for group in NOUNS.values():
        for w, (sex, kind) in group.items():
            out[w] = {"sex": sex, "animate": kind in ("person", "animal"), "kind": kind}
    for w, sex in (("son", "m"), ("daughter", "f"), ("husband", "m"), ("wife", "f"), ("uncle", "m"), ("aunt", "f")):
        out[w] = {"sex": sex, "animate": True, "kind": "person"}
    return out


def available(words, vocab_ids) -> list:
    return [w for w in words if w in vocab_ids]
