"""Derivational relations: the closed set of regular word-formation operations.

Every language gets one affix (or particle) per relation, applied the same way
to every root. SAME is special: it makes an exact alias (spelling variants etc.).
"""
RELATIONS = [
    "ADJ", "ADV", "ABSTRACT", "ACTION", "RESULT", "AGENT", "TOOL", "PLACE", "VERBALIZE",
    "NEG", "OPPOSITE", "REVERSE", "AGAIN", "CAUSE", "FEMALE", "MALE", "YOUNG", "AUGMENT",
    "DIMIN", "COLLECTIVE", "FULL", "WITHOUT", "ABLE", "COMPAR", "SUPERL", "ORD", "PLURAL",
    "POSS", "OBJ", "SELF", "INDEP",
]
SAME = "SAME"

GLOSS = {
    "ADJ": "adjective: 'of, relating to X'", "ADV": "adverb: 'in an X way'",
    "ABSTRACT": "abstract noun: 'the quality or state of X'", "ACTION": "'the act or process of X-ing'",
    "RESULT": "'the product or result of X'", "AGENT": "'one who does X / is concerned with X'",
    "TOOL": "'a thing used for X'", "PLACE": "'a place for X'", "VERBALIZE": "verb: 'to do or become X'",
    "NEG": "'not X'", "OPPOSITE": "'the opposite of X'", "REVERSE": "'to undo X'", "AGAIN": "'to X again'",
    "CAUSE": "'to cause X'", "FEMALE": "'female X'", "MALE": "'male X'", "YOUNG": "'young X'",
    "AUGMENT": "'greater or stronger X'", "DIMIN": "'lesser or weaker X'", "COLLECTIVE": "'a group of X'",
    "FULL": "'full of X'", "WITHOUT": "'without X'", "ABLE": "'able to be X-ed'",
    "COMPAR": "comparative: 'more X'", "SUPERL": "superlative: 'most X'", "ORD": "ordinal: 'X-th'",
    "PLURAL": "plural: 'several X'", "POSS": "possessive: 'of X'", "OBJ": "object form of X",
    "SELF": "reflexive: 'X-self'", "INDEP": "independent possessive: 'the one(s) of X'",
}

# In mixed-affixing languages these tend to be prefixes; everything else is a suffix.
PREFIX_LEANING = {"NEG", "OPPOSITE", "REVERSE", "AGAIN", "CAUSE", "WITHOUT", "COMPAR", "SUPERL"}

# Most frequently used relations first: they claim the shortest affixes when a language draws its pool.
FREQUENCY_ORDER = [
    "PLURAL", "ADJ", "ADV", "NEG", "AGENT", "POSS", "OBJ", "VERBALIZE", "ABSTRACT", "COMPAR", "SUPERL",
    "CAUSE", "FEMALE", "AGAIN", "SELF", "ACTION", "RESULT", "PLACE", "ORD", "COLLECTIVE", "OPPOSITE", "TOOL",
    "FULL", "WITHOUT", "ABLE", "DIMIN", "AUGMENT", "YOUNG", "MALE", "REVERSE", "INDEP",
]
assert sorted(FREQUENCY_ORDER) == sorted(RELATIONS)

# How readily a frequent word breaks away from its base word and gets a root of its own. Used by plan.py as
# a multiplier on the commonness-based probability: opposites and size alterations of frequent words are
# very often unrelated words in natural languages (hot/cold, big/small); gender pairs and grammatical
# relations much less so.
INDEPENDENCE = {"OPPOSITE": 1.0, "NEG": 1.0, "REVERSE": 1.0, "AUGMENT": 1.0, "DIMIN": 1.0,
                "ACTION": .7, "RESULT": .7, "ABSTRACT": .7, "AGENT": .6, "TOOL": .6, "PLACE": .6, "CAUSE": .6,
                "VERBALIZE": .5, "ADJ": .5, "ADV": .4, "COLLECTIVE": .6, "FULL": .6, "WITHOUT": .6, "ABLE": .5,
                "AGAIN": .5, "FEMALE": .35, "MALE": .35, "YOUNG": .5, "ORD": .3, "COMPAR": .2, "SUPERL": .2,
                "PLURAL": .2, "POSS": .2, "OBJ": .2, "SELF": .3, "INDEP": 1.0}
DEFAULT_INDEPENDENCE = .6
