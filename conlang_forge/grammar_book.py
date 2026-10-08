"""The grammar book: an introductory "Language 101" course for one generated language, as Markdown.

Everything in it is read from the language itself (spec, lexicon, inflection table) and every example sentence is
produced by conlang_forge.grammar, so the rules in the text and the sentences below them cannot disagree. Lessons
for features the language does not have (cases, genders, tenses ...) are replaced by a one-line note, so the book
teaches exactly the grammar this language has. The prose is template text; an LLM pass can polish it later without
being able to change a single word or ending.
"""
from __future__ import annotations

from . import curriculum as C
from .grammar import Grammar, GrammarError, PRONOUN, POSSESSIVE, WH_WORDS
from .infl_inventory import abbr
from .morph import render_flat
from .relations import GLOSS

from .inventory import SAY_LIKE as IPA_HINT
CASE_USE = {
    "nominative": "the subject of a sentence (unmarked)", "accusative": "the direct object: what the action is done to",
    "ergative": "the doer of an action on something (the subject of a transitive verb)",
    "absolutive": "the subject of 'sleeps' and the object of 'sees' (unmarked)", "genitive": "the owner: 'of', 's",
    "dative": "the recipient: 'to', 'for'", "locative": "place: 'in', 'at', 'on'", "ablative": "source: 'from', 'away from'",
    "instrumental": "the tool or means: 'with, by means of'", "comitative": "company: 'together with'",
    "allative": "direction: 'to, toward'", "vocative": "calling someone: 'O dragon!'", "benefactive": "'for the sake of'",
    "partitive": "part of a whole: 'some of'", "essive": "'as' (being something)", "translative": "'becoming' something",
    "inessive": "'inside'", "elative": "'out of'",
}
TENSE_HINT = {"past": ("I went", "he ate"), "present": ("I go", "he eats"), "future": ("I will go", "he will eat"),
              "non-past": ("I go / I will go", None), "non-future": ("I went / I go", None),
              "remote past": ("I went long ago", None), "recent past": ("I went a moment ago", None)}
ASPECT_HINT = {"perfective": "he ate (the whole thing, done)", "imperfective": "he was eating / used to eat",
               "progressive": "he is eating (right now)", "habitual": "he eats (as a habit)",
               "completive": "he has finished eating", "continuative": "he keeps on eating"}
MOOD_HINT = {"imperative": "Eat!", "subjunctive": "(I wish) that he eat", "conditional": "he would eat",
             "optative": "may he eat!"}
PERSONS = [("I", 1, "sg"), ("you", 2, "sg"), ("he / she / it", 3, "sg"), ("we", 1, "pl"), ("you (all)", 2, "pl"),
           ("they", 3, "pl")]


def _table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out + [""]


class Book:
    def __init__(self, spec, state, vocab, version=""):
        self.spec, self.state, self.vocab = spec, state, vocab
        self.m, self.s, self.ph = spec.morphology, spec.syntax, spec.phonology
        self.g = Grammar(spec, state, vocab)
        self.g.set_semantics(C.semantics())
        self.ids = {e["concept_id"] for e in vocab["entries"]}
        self.L: list = []
        self.used_gloss: set = set()
        self.used_gloss_full: set = set()
        self.bank: list = []        # (english, tokens) for the exercises
        self.lesson_no = 0

    # ------------------------------------------------------------------ small helpers
    def add(self, *lines):
        self.L.extend(lines)

    def w(self, cid, keys=(), extra=()):
        """The language's spelling of a word, with optional morphemes."""
        toks = self.g.word(cid, keys, extra)
        return " ".join(self.g.form(t["flat"]) for t in toks)

    def has(self, *cids):
        return all(c in self.g.E for c in cids)

    def form(self, tokens):
        return " ".join(self.g.form(t["flat"]) for t in tokens)

    def lesson(self, title, intro=None):
        self.lesson_no += 1
        self.add(f"## Lesson {self.lesson_no}: {title}", "")
        if intro:
            self.add(intro, "")

    def rule(self, text):
        self.add("> **Rule.** " + text, "")

    def note(self, text):
        self.add("> *" + text + "*", "")

    def time_ref(self, kind):
        m, g = self.m, self.g
        if kind == "present":
            return g.zero_tense if g.zero_tense else None, []
        if kind == "past":
            for t in ("past", "recent past", "remote past", "non-future"):
                if t in m.tenses:
                    return t, []
            return None, [a for a in ("yesterday",) if self.has(a)]
        for t in ("future", "non-past"):
            if t in m.tenses:
                return t, []
        return None, [a for a in ("tomorrow",) if self.has(a)]

    def example(self, en, *, kind="present", keep=False, **kw):
        """Add one glossed example sentence and return its tokens (None if the language lacks a needed word)."""
        tense, adv = self.time_ref(kind) if "tense" not in kw else (kw.pop("tense"), [])
        kw["adverbs"] = list(kw.get("adverbs", [])) + adv
        try:
            toks = self.g.clause(tense=tense, **kw)
        except (GrammarError, KeyError):
            return None
        self._block(en, toks)
        if keep:
            self.bank.append((en, toks))
        return toks

    def _block(self, en, toks):
        forms, glosses = self.g.interlinear(toks)
        for gl in glosses:
            for part in gl.split("-"):
                self.used_gloss_full.add(part)
        cols = [max(len(f), len(gl)) for f, gl in zip(forms, glosses)]
        l1 = "  ".join(f.ljust(c) for f, c in zip(forms, cols)).rstrip()
        l2 = "  ".join(gl.ljust(c) for gl, c in zip(glosses, cols)).rstrip()
        self.add("```", l1, l2, f"'{en}'", "```", "")

    # ------------------------------------------------------------------ front matter
    def title(self):
        sp, m, s = self.spec, self.m, self.s
        self.add(f"# {sp.name}: a beginner's course", "",
                 f"*Language 101 for {sp.name}. Seed {sp.seed}. Every word and ending in this book is read straight from the "
                 "language, so the examples always agree with the rules.*", "")
        self.add("## How to use this book", "",
                 "Each lesson gives the **rules** first, then **short examples** with a word-by-word translation. In the examples "
                 "the first line is the sentence in the language, the second line translates each word or ending in turn "
                 "(small capitals such as PST or PL are grammar labels, explained at the end of the book), and the third line "
                 "is natural English. Work through the lessons in order, then try the exercises and check yourself against "
                 "the answer key.", "")

    def at_a_glance(self):
        sp, m, s = self.spec, self.m, self.s
        typ = {"isolating": "isolating: words do not change shape; small separate words carry the grammar",
               "agglutinative": "agglutinative: endings are chained onto a word, each with one meaning",
               "fusional": "fusional: endings merge with the word where they meet, and one ending can carry several meanings",
               "polysynthetic": "polysynthetic: a verb can carry a whole sentence's worth of endings"}[m.typology]
        wo = {"SOV": "subject, object, verb", "SVO": "subject, verb, object", "VSO": "verb, subject, object",
              "VOS": "verb, object, subject", "OVS": "object, verb, subject", "OSV": "object, subject, verb"}[s.word_order]
        where = {"none": "no affixes at all (small separate words)", "suffixing": "suffixes (endings)",
                 "prefixing": "prefixes (beginnings)", "mixed": "both prefixes and suffixes"}[m.affix_position]
        self.add("## The language at a glance", "")
        rows = [("Type", typ), ("Basic word order", f"{s.word_order}: {wo}"),
                ("Grammar is added with", where),
                ("Adjectives", "come " + ("before" if s.adjective_order == "adjective-noun" else "after") + " the noun"),
                ("Owners", "come " + ("before" if s.genitive_order == "genitive-noun" else "after") + " the thing owned"),
                ("Little words like 'in'", "come " + ("after" if s.adposition == "postposition" else "before") + " the noun (" + s.adposition + "s)"),
                ("Number", ", ".join(m.noun_number) if m.noun_number else "not marked on nouns"),
                ("Cases", f"{len(m.cases)}: " + ", ".join(m.cases) if m.cases else "none (word order and little words do the work)"),
                ("Genders", ", ".join(m.genders) if m.genders else "none"),
                ("Articles", m.definiteness if m.definiteness != "none" else "none ('the' and 'a' are not said)"),
                ("Tenses", ", ".join(m.tenses) if m.tenses else "none (time words are used instead)"),
                ("Aspects", ", ".join(m.aspects) if m.aspects else "none"),
                ("Moods", ", ".join(m.moods)),
                ("Verbs agree with", {"none": "nothing", "subject": "the subject", "subject+object": "the subject and the object",
                                       "polypersonal": "the subject and the object"}[m.verb_agreement]),
                ("Alignment", "nominative-accusative" if m.case_alignment.startswith("nom") else "ergative-absolutive"),
                ("Counting base", str(m.numeral_base))]
        self.add(*_table(["", ""], rows))

    # ------------------------------------------------------------------ lesson 1: sounds
    def sounds(self):
        ph, rom = self.ph, self.spec.orthography.romanization
        self.lesson("Sounds and spelling")
        self.add("**Consonants**", "")
        self.add(*_table(["Letter", "Sound", "Say it like"], [(rom[c], f"/{c}/", IPA_HINT.get(c, "")) for c in ph.consonants]))
        self.add("**Vowels**", "")
        self.add(*_table(["Letter", "Sound", "Say it like"], [(rom[v], f"/{v}/", IPA_HINT.get(v, "")) for v in ph.vowels]))
        shapes = " ".join(ph.syllable_templates)
        self.rule(f"Syllables in {self.spec.name} have these shapes (C = consonant, V = vowel): **{shapes}**. "
                  f"The stress falls on the {'first syllable' if ph.stress == 'initial' else 'last syllable' if ph.stress == 'final' else 'next-to-last syllable' if ph.stress == 'penultimate' else 'syllable you find natural (there is no fixed stress)'}.")
        if ph.max_cluster > 1:
            self.add(f"Up to {ph.max_cluster} consonants can stand together.", "")
        samples = [c for c in ("water", "fire", "mother", "dragon", "house", "tree", "friend", "king") if self.has(c)][:6]
        if samples:
            self.add("**Practice words** (a dot separates syllables)", "")
            self.add(*_table(["English", "Spelling", "Pronunciation"],
                             [(c, self.g.form(self.g.flat(c)), render_flat(self.spec, self.g.flat(c))[1]) for c in samples]))

    # ------------------------------------------------------------------ lesson 2: greetings
    def greetings(self):
        g = self.g
        self.lesson("Greetings and polite phrases")
        rows = []
        for cid, en in [("hello", "Hello!"), ("goodbye", "Goodbye!"), ("please", "Please."), ("sorry", "Sorry."),
                        ("yes", "Yes."), ("no", "No.")]:
            if self.has(cid):
                rows.append((en, self.w(cid)))
        if self.has("thank"):
            toks = None
            try:
                toks = g.clause(subject={"head": "i"}, verb="thank", object={"head": "you"}, tense=self.time_ref("present")[0])
            except (GrammarError, KeyError):
                pass
            if toks:
                rows.append(("Thank you. (literally 'I thank you')", self.form(toks)))
        for en, kw in [("Good morning.", dict(noun="morning", adj="good")), ("Good night.", dict(noun="night", adj="good"))]:
            if self.has(kw["noun"], kw["adj"]):
                toks, _ = g.noun_phrase(kw["noun"], adjectives=[kw["adj"]])
                rows.append((en, self.form(toks)))
        self.add(*_table(["English", self.spec.name], rows))
        you = {"head": "you"}
        self.add("**Short conversations**", "")
        me = g.name_for("Tamo")
        self.example("What is your name?", predicate={"head": "name", "possessor": "you"}, subject={"head": "what"},
                     question="wh", keep=True) if self.has("name") else None
        self.example("How are you?", subject=you, predicate={"adverb": "how"}, question="wh", keep=True)
        self.example("I am well.", subject={"head": "i"}, predicate={"adjective": "good"}, keep=True)
        self.example("I am happy.", subject={"head": "i"}, predicate={"adjective": "happy"}, keep=True)
        self.example("I do not understand.", subject={"head": "i"}, verb="understand", negated=True, keep=True) if self.has("understand") else None
        self.example("I love you.", subject={"head": "i"}, verb="love", object=you, keep=True)
        if self.has("name"):
            self.example("My name is Tamo.", subject={"head": "name", "possessor": "i"}, predicate={"head": me}, keep=True)
            self.note("Names keep their own sound; they are not translated. A name takes the same endings as any noun.")

    # ------------------------------------------------------------------ lesson 3: pronouns
    def pronouns(self):
        g, m = self.g, self.m
        self.lesson("Pronouns and 'to be'")
        rows = []
        for p in C.PRONOUNS:
            if not self.has(p):
                continue
            obj = self.form(g.pronoun(p, "accusative"))
            pos = self.w(POSSESSIVE[p]) if self.has(POSSESSIVE[p]) else ""
            rows.append(("I" if p == "i" else p, self.w(p), obj, pos))
        self.add(*_table(["English", "Subject", "Object (me, him ...)", "Owner (my, his ...)"], rows))
        self.rule("The object form is the subject form plus the object ending, and the owner form is the subject form plus the "
                  "possessive ending. Learn the seven subject pronouns and you can build all of the rest.")
        if self.has("this", "that", "these", "those"):
            self.add("**This and that**", "")
            self.add(*_table(["English", self.spec.name], [(c, self.w(c)) for c in C.DEMONSTRATIVES]))
            self.note("The plural forms are the singular forms plus the plural ending.")
        if self.g.pro_drop:
            self.rule("This language **drops subject pronouns**: the verb ending already tells you who is acting, so 'I' is usually left out. "
                      "You may add it for emphasis.")
        elif self.s.pro_drop and not g.subject_agrees:
            self.rule("Subject pronouns are **always said**, because the verb does not show who is acting.")
        else:
            self.rule("Subject pronouns are **always said** in this language.")
        self.add("**To be**", "")
        if not self.s.has_copula or self.s.copula_form == "zero":
            self.rule("In the present tense there is **no word for 'is/am/are'**: you just put the two parts side by side "
                      f"(\"I teacher\"). {'In other tenses the verb ‘be’ is used.' if m.tenses else ''}")
        elif self.s.copula_form == "particle":
            self.rule("'Is/am/are' is a small word, the **copula particle**, that never changes. In other tenses or in negative "
                      "sentences the full verb 'be' is used.")
        else:
            self.rule("'To be' is an ordinary verb. It takes the same endings as any other verb (see Lesson 6).")
        i = {"head": "i"}
        self.example("I am a wizard.", subject=i, predicate={"head": "wizard", "definite": False}, keep=True)
        self.example("You are happy.", subject={"head": "you"}, predicate={"adjective": "happy"}, keep=True)
        self.example("The dog is big.", subject={"head": "dog", "definite": True}, predicate={"adjective": "big"}, keep=True)
        self.example("We are friends.", subject={"head": "we"}, predicate={"head": "friend", "number": "plural"}, keep=True)
        self.example("She is a queen.", subject={"head": "she"}, predicate={"head": "queen", "definite": False}, keep=True)
        if g.subject_agrees and self.s.has_copula and self.s.copula_form == "verb":
            self.add("**'Be' for each person**", "")
            rows = []
            for lab, p, n in PERSONS:
                b, v, a = g.verb_complex("be", tense=self.time_ref("present")[0], subj=(p, n))
                rows.append((lab, self.form(b + v + a)))
            self.add(*_table(["", "be"], rows))

    # ------------------------------------------------------------------ lesson 4: numbers and colors
    def numbers_colors(self):
        g, m = self.g, self.m
        self.lesson("Numbers and colors")
        rows = [(n, self.form(g.numeral(n))) for n in C.NUMBERS if all(self.has(x) for x in g.numeral_words(n))]
        self.add(*_table(["Number", self.spec.name], rows))
        base = m.numeral_base
        bw = {5: "five", 8: "eight", 10: "ten", 12: "dozen", 20: "twenty"}[base]
        if base == 12 and not self.has("dozen"):
            base, bw = 10, "ten"
        big = g.number_order == "big-first"
        self.rule(f"This language counts in **{base}s**. The numbers 1 to 10 have their own words. Above that, say the large part and "
                  f"then the rest, {'biggest part first' if big else 'smaller part first, joined with ‘and’'}. For example 23 is said "
                  f"'{self.form(g.numeral(23))}' ({' '.join(g.numeral_words(23))}).")
        ex = [n for n in (11, 12, 15, 20, 21, 35, 100, 234) if all(self.has(x) for x in g.numeral_words(n))]
        self.add(*_table(["Number", self.spec.name, "Built from"],
                         [(n, self.form(g.numeral(n)), " ".join(g.numeral_words(n))) for n in ex]))
        self.add("**Counting things**", "")
        if m.noun_number:
            if "plural" in m.noun_number:
                if g.plural_after_numeral:
                    self.rule("After a number above one the noun takes its **plural** form.")
                else:
                    self.rule("After a number the noun stays **singular**; the number already shows that there is more than one.")
        if self.analytic_classifier():
            self.rule("When you count, a **class word** follows the number. It depends on the noun's class (see Lesson 5).")
        for n, noun, en in [(1, "dog", "one dog"), (3, "horse", "three horses"), (5, "king", "five kings")]:
            if self.has(noun) and all(self.has(x) for x in g.numeral_words(n)):
                toks, _ = g.noun_phrase(noun, number="plural" if n > 1 else "singular", numeral=n)
                self.add(f"- {en}: **{self.form(toks)}**")
        self.add("")
        self.add("**Colors**", "")
        cols = [c for c in C.COLORS if self.has(c)]
        self.add(*_table(["English", self.spec.name], [(c, self.w(c)) for c in cols]))
        pos = "before" if self.s.adjective_order == "adjective-noun" else "after"
        self.rule(f"Colors are adjectives, so they come **{pos}** the noun and "
                  f"{'agree with it (Lesson 7)' if (m.genders or m.noun_number) and not self.analytic_all() else 'do not change'}.")
        for en, noun, col in [("a red sword", "sword", "red"), ("the blue river", "river", "blue"), ("white horses", "horse", "white")]:
            if self.has(noun, col):
                kw = {"head": noun, "adjectives": [col]}
                if "white horses" == en:
                    kw["number"] = "plural"
                else:
                    kw["definite"] = en.startswith("the")
                toks, _ = g.noun_phrase(**kw)
                self.add(f"- {en}: **{self.form(toks)}**")
        self.add("")

    def analytic_classifier(self):
        return self.g.analytic and bool(self.m.genders)

    def analytic_all(self):
        return self.g.analytic

    # ------------------------------------------------------------------ lesson 5: nouns
    def nouns(self):
        g, m = self.g, self.m
        self.lesson("Nouns: number, gender, articles and cases")
        for group, items in C.NOUNS.items():
            ws = [w for w in items if self.has(w)]
            if not ws:
                continue
            self.add(f"**{group.capitalize()}**", "")
            head = ["English", self.spec.name]
            if "plural" in m.noun_number:
                head.append("plural")
            if m.genders:
                head.append("gender")
            rows = []
            for w in ws:
                row = [w, self.w(w)]
                if "plural" in m.noun_number:
                    toks, _ = g.noun_phrase(w, number="plural", case="nominative")
                    row.append(self.form(toks))
                if m.genders:
                    row.append(abbr(g.gender_of(w)))
                rows.append(row)
            self.add(*_table(head, rows))
        # number
        if m.noun_number:
            others = [n for n in m.noun_number if n != "singular"]
            self.add("**Number**", "")
            self.rule("A noun is **singular** by default (no ending). " + ". ".join(
                f"The **{n}** (for {'two' if n == 'dual' else 'a few' if n == 'paucal' else 'more than one'}) adds {self._affix_text('number:' + n)}" for n in others) + ".")
        else:
            self.rule("Nouns **do not change** for number: the same word means 'dog' and 'dogs'. Context or a number word tells you which.")
        # gender
        if m.genders:
            self.add("**Gender**", "")
            sg = ", ".join(m.genders)
            if self.analytic_classifier():
                self.rule(f"Every noun belongs to one of these classes: {sg}. Nouns themselves do not change; the class shows up only in the **class word** said after a number or 'this/that'.")
            else:
                kind = "noun classes" if m.genders[0].startswith("class") else "genders"
                self.rule(f"Every noun belongs to one of these {kind}: **{sg}**. The noun itself does not change, but the words that go with it (adjectives, 'the', 'this') take the matching ending (see Lesson 7). "
                          + ("Words for men are masculine and words for women are feminine; for everything else the gender simply has to be learned with the word."
                             if "feminine" in m.genders else "Words for people and animals have their own groups; everything else must be learned with the word."))
            self.add(*_table(["Gender / class", "Class word" if self.analytic_classifier() else "Ending on adjectives", "Examples"], [
                (abbr(gd), self._affix_text("gender:" + gd), ", ".join([w for w in self._all_nouns() if g.gender_of(w) == gd][:9]))
                for gd in m.genders]))
        # articles
        self.add("**'The' and 'a'**", "")
        d = m.definiteness
        if d == "none":
            self.rule("There are **no articles**: 'the dragon' and 'a dragon' are both just 'dragon'.")
        elif d == "definite article":
            self.rule(f"'The' is a separate word, **{self.w('the')}**, said before the noun" + (" and agreeing with it" if m.genders and not self.g.analytic else "") + ". There is no word for 'a'.")
        elif d == "definite+indefinite articles":
            self.rule(f"'The' is **{self.w('the')}** and 'a' is **{self.w('a')}**, said before the noun" + (" and agreeing with it" if m.genders and not self.g.analytic else "") + ". They are used much as in English.")
        else:
            self.rule(f"'The' is not a word but an ending, **{self._affix_text('def:definite')}**, added to the noun. There is no word for 'a'.")
        self.example("the dragon", predicate=None, subject={"head": "dragon", "definite": True}, verb="sleep", keep=False) if False else None
        # cases
        if m.cases:
            self.add("**Cases**", "")
            self.rule("A **case** is an ending on a noun that shows its job in the sentence. This language has "
                      f"**{len(m.cases)}** ({', '.join(m.cases)}). The word order does the rest of the work.")
            rows = []
            for c in m.cases:
                end = self._affix_text("case:" + c) if f"case:{c}" in g.infl else "(no ending)"
                toks, _ = g.noun_phrase("house", case=c) if self.has("house") else ([], None)
                rows.append((c, abbr(c), end, CASE_USE.get(c, ""), self.form(toks) if toks else ""))
            self.add(*_table(["Case", "Label", "Ending", "Used for", "'house'"], rows))
            self.example("The wizard sees the dragon.", subject={"head": "wizard", "definite": True}, verb="see",
                         object={"head": "dragon", "definite": True}, keep=True)
            if not m.case_alignment.startswith("nom"):
                self.rule("This language marks the **doer of an action on something** with the ergative and leaves the object bare. "
                          "The subject of a verb with no object ('sleeps', 'goes') is bare too.")
        else:
            self.rule("This language has **no cases**: nouns never change for their job in a sentence. Word order and little words "
                      f"({self.s.adposition}s) show who does what to whom.")

    def _all_nouns(self):
        return [w for items in C.NOUNS.values() for w in items if self.has(w)]

    def _affix_text(self, key):
        info = self.g.infl.get(key)
        if not info:
            return "(none)"
        f = self.g.form(info["phonemes"])
        if self.g.analytic:
            target = "verb" if info["category"] in ("tense", "aspect", "mood", "evid", "agr") else \
                     "noun" if info["category"] in ("number", "case", "gender", "def") else "word"
            return f"the word **{f}** placed " + ("before" if info["position"] == "prefix" else "after") + f" the {target}"
        return f"**{f}-**" if info["position"] == "prefix" else f"**-{f}**"

    # ------------------------------------------------------------------ lesson 6: verbs
    def verbs(self):
        g, m = self.g, self.m
        self.lesson("Verbs and how to conjugate them")
        vs = [v for v in C.VERBS if self.has(v)]
        self.add(*_table(["English", self.spec.name, "takes an object?"], [(v, self.w(v), "yes" if C.VERBS[v] else "no") for v in vs]))
        self.rule("Look verbs up in the dictionary in this form, the **stem**. Every ending below attaches to the stem"
                  + ("" if not g.analytic else " (here, as small separate words in front of it)") + ".")
        z = g.zero_tense
        if g.subject_agrees:
            self.add("**Who is acting: agreement**", "")
            obj = m.verb_agreement != "subject"
            self.rule("The verb ending shows **who is acting**" + (" and **who it is done to**" if obj else "") + ". "
                      "Say the verb with the ending for the person: 1 = I/we, 2 = you, 3 = he/she/it/they.")
            rows = []
            for lab, p, n in PERSONS:
                b, v, a = g.verb_complex("see", tense=z, subj=(p, n), obj=(3, "sg") if obj else None)
                rows.append((lab, f"{p}{n.upper()}", self.form(b + v + a)))
            self.add(*_table(["Subject", "Label", "see" + (" (it)" if obj else "")], rows))
            if obj:
                rows = []
                for lab, p, n in PERSONS[:3] + PERSONS[3:4]:
                    b, v, a = g.verb_complex("see", tense=z, subj=(3, "sg"), obj=(p, n))
                    rows.append((lab, f"{p}{n.upper()}.O", self.form(b + v + a)))
                self.add("**...and who it is done to** (he/she sees ...)", "")
                self.add(*_table(["Object", "Label", "he sees ..."], rows))
        else:
            self.rule("Verbs **do not change** for person or number: 'sees' is the same word whoever sees.")
        # tense
        self.add("**Time: tense**", "")
        if m.tenses:
            rows = []
            for t in m.tenses:
                en = TENSE_HINT.get(t, (t, None))[0]
                toks = g.clause(subject={"head": "i"}, verb="go", tense=t, drop_subject=False)
                mark = "(no ending)" if f"tense:{t}" not in g.infl else self._affix_text("tense:" + t)
                rows.append((t, abbr(t), mark, en, self.form(toks)))
            self.add(*_table(["Tense", "Label", "Marker", "English", "'go'"], rows))
            if "non-past" in m.tenses:
                self.note("Non-past covers both the present and the future.")
            if "non-future" in m.tenses:
                self.note("Non-future covers both the past and the present.")
        else:
            self.rule("This language has **no tenses**. Verbs stay the same, and you say *when* with a time word (yesterday, today, tomorrow) or let the situation make it clear.")
            for en, kind in [("I go today.", "present"), ("I went yesterday.", "past"), ("I will go tomorrow.", "future")]:
                self.example(en, subject={"head": "i"}, verb="go", kind=kind, adverbs=["today"] if kind == "present" and self.has("today") else [], keep=False, drop_subject=False)
        # aspect
        if m.aspects:
            self.add("**How the action unfolds: aspect**", "")
            self.rule("Aspect shows whether an action is finished, ongoing or habitual. " + (
                f"**{m.aspects[0]}** is the plain form (no ending); the others add one." ))
            rows = []
            for a in m.aspects:
                toks = g.clause(subject={"head": "he"}, verb="eat", object={"head": "bread"}, aspect=a, tense=g.zero_tense, drop_subject=False)
                rows.append((a, abbr(a), "(no ending)" if f"aspect:{a}" not in g.infl else self._affix_text("aspect:" + a), ASPECT_HINT.get(a, ""), self.form(toks)))
            self.add(*_table(["Aspect", "Label", "Marker", "Meaning", "'he eats bread'"], rows))
        # mood
        extra = [x for x in m.moods if x != "indicative"]
        if extra:
            self.add("**Commands and wishes: mood**", "")
            self.rule("The plain form (**indicative**) states facts. " + " ".join(
                f"The **{x}** adds {self._affix_text('mood:' + x)}." for x in extra))
            rows = []
            for x in extra:
                toks = g.clause(subject={"head": "you" if x == "imperative" else "he"}, verb="eat", object={"head": "bread"}, mood=x, tense=g.zero_tense, drop_subject=x == "imperative" or None)
                rows.append((x, abbr(x), MOOD_HINT.get(x, ""), self.form(toks)))
            self.add(*_table(["Mood", "Label", "English", "'eat bread'"], rows))
        else:
            self.rule("There is no special command form: say the plain statement with 'you' ('You eat the bread') and a firm voice.")
        if m.evidentiality:
            self.add("**How do you know? Evidentiality**", "")
            self.rule("A verb ending also shows how the speaker knows. Unmarked means seen firsthand; "
                      f"**{self._affix_text('evid:reported')}** means 'they say'; **{self._affix_text('evid:inferred')}** means 'it seems'.")
            for ev, en in [("reported", "(They say) he eats bread."), ("inferred", "(It seems) he eats bread.")]:
                self.example(en, subject={"head": "he"}, verb="eat", object={"head": "bread"}, evid=ev, drop_subject=False)
        self.add("**Order of the endings**", "")
        self.rule(self.slot_template())
        # negation
        self.add("**Saying 'not'**", "")
        neg = {"particle before verb": "the word **{n}** goes **right before the verb**",
               "particle after verb": "the word **{n}** goes **right after the verb**",
               "verbal affix": "the ending **{a}** is added to the verb, next to the stem",
               "auxiliary verb": "the word **{n}** acts as a helper verb that carries the tense and person endings, and the main verb stays bare",
               "double negation particle": "the word **{n}** goes **both before and after the verb**"}[m.negation]
        self.rule("To negate, " + neg.format(n=self.w("not"), a=self._neg_text()) + ".")
        self.example("I do not go.", subject={"head": "i"}, verb="go", negated=True, keep=True, drop_subject=False)
        self.example("The dragon does not sleep.", subject={"head": "dragon", "definite": True}, verb="sleep", negated=True, keep=True)
        # word building
        self.add("**Building new words**", "")
        self.rule("Most new words are made from old ones with regular endings. The same ending works on any root.")
        rows = []
        for rel, base, en in [("AGENT", "teach", "teacher"), ("ABSTRACT", "free", "freedom"), ("ADJ", "danger", "dangerous"),
                              ("ADV", "quick", "quickly"), ("NEG", "happy", "unhappy"), ("AGAIN", "build", "rebuild"),
                              ("FEMALE", "king", "queen"), ("DIMIN", "house", "little house"), ("PLACE", "work", "workplace")]:
            if self.has(base):
                toks = g.word(base, [], [g._affix_part(rel, rel)])
                rows.append((GLOSS[rel].split(":")[0] if ":" in GLOSS[rel] else GLOSS[rel], f"{base} +{rel}", en, self.form(toks)))
        self.add(*_table(["Meaning", "Recipe", "English", self.spec.name], rows))

    def slot_template(self):
        """Where each ending goes on a verb, from the stem outward."""
        g, m = self.g, self.m
        chain = []
        if m.negation == "verbal affix":
            chain.append(("NEG", self.g.table["affixes"]["NEG"]["position"]))
        for cat, lab in (("aspect", "ASPECT"), ("tense", "TENSE"), ("mood", "MOOD"), ("evid", "EVIDENTIAL")):
            keys = [i for k, i in g.infl.items() if i["category"] == cat]
            if keys:
                chain.append((lab, keys[0]["position"]))
        for role, lab in (("subj", "SUBJECT-PERSON"), ("obj", "OBJECT-PERSON")):
            keys = [i for k, i in g.infl.items() if k.startswith(f"agr:{role}:")]
            if keys:
                chain.append((lab, keys[0]["position"]))
        if "q:affix" in g.infl:
            chain.append(("QUESTION", g.infl["q:affix"]["position"]))
        if not chain:
            return "A verb has **no endings**: it is just the stem."
        left, right = [], []
        for lab, pos in chain:
            (left.insert(0, lab) if pos == "prefix" else right.append(lab))
        sep = " + " if g.analytic else "-"
        parts = left + ["STEM"] + right
        allp = all(i["position"] == "prefix" for i in g.infl.values() if i["category"] in ("tense", "aspect", "mood", "agr", "evid"))
        what = ("separate small words, in this order" if g.analytic else "beginnings (prefixes), in this order" if allp and chain and all(p == "prefix" for _, p in chain)
                else "endings, in this order")
        tail = (" SUBJECT-PERSON shows who is acting" + ("; OBJECT-PERSON shows who it is done to." if any(l == "OBJECT-PERSON" for l, _ in chain) else "."))\
            if any(l.startswith("SUBJECT") for l, _ in chain) else ""
        near = "The one nearest the stem is added first. " if not g.analytic else "The order never changes. "
        return f"A verb is built from the stem plus these {what}: **" + sep.join(parts) + "**. Leave out any you do not need. " + near + tail.strip()

    def _neg_text(self):
        a = self.g.table["affixes"]["NEG"]
        f = self.g.form(a["phonemes"])
        return f + "-" if a["position"] == "prefix" else "-" + f

    # ------------------------------------------------------------------ lesson 7: adjectives
    def adjectives(self):
        g, m = self.g, self.m
        self.lesson("Adjectives and agreement")
        adjs = [a for a in C.ADJECTIVES if self.has(a)]
        self.add(*_table(["English", self.spec.name], [(a, self.w(a)) for a in adjs]))
        pos = "before" if self.s.adjective_order == "adjective-noun" else "after"
        self.rule(f"An adjective comes **{pos}** the noun it describes.")
        concord = bool(m.genders or m.noun_number) and not g.analytic
        if concord:
            what = []
            if m.genders:
                what.append("gender")
            if "plural" in m.noun_number or len(m.noun_number) > 1:
                what.append("number")
            if m.cases and m.typology == "fusional":
                what.append("case")
            self.rule("An adjective must **agree** with its noun in " + " and ".join(what) + ": it takes the ending of the noun's " + " and ".join(what) + ". "
                      "The same goes for 'the', 'this' and 'that'.")
            if m.genders:
                head = ["'big' agrees with a noun that is ..."] + [abbr(gd) for gd in m.genders]
                row_s = ["singular"] + [self.form(g.word("big", g._concord(gd, "singular", "nominative"))) for gd in m.genders]
                rows = [row_s]
                if "plural" in m.noun_number:
                    rows.append(["plural"] + [self.form(g.word("big", g._concord(gd, "plural", "nominative"))) for gd in m.genders])
                self.add(*_table(head, rows))
        else:
            self.rule("Adjectives **never change**: they have one form whatever the noun is." if not g.analytic else
                      "Adjectives are single words that never change.")
        w0 = self._noun_with_gender(0)
        w1 = self._noun_with_gender(1)
        for noun, en_s, en_p in [(w0, None, None), (w1, None, None)]:
            if noun:
                toks, _ = g.noun_phrase(noun, adjectives=["big"], definite=True)
                tp, _ = g.noun_phrase(noun, adjectives=["big"], number="plural") if "plural" in m.noun_number else (None, None)
                self.add(f"- the big {noun}: **{self.form(toks)}**" + (f"; big {noun}s: **{self.form(tp)}**" if tp else ""))
        self.add("")
        self.example("The old wizard sees the big dragon.", subject={"head": "wizard", "adjectives": ["old"], "definite": True}, verb="see",
                     object={"head": "dragon", "adjectives": ["big"], "definite": True}, keep=True)
        plural = "plural" in m.noun_number
        self.example("The horses are fast." if plural else "The horse is fast.", subject={"head": "horse", "number": "plural" if plural else "singular", "definite": True},
                     predicate={"adjective": "fast"}, keep=True)
        if self.has("more") or True:
            self.add("**More and most**", "")
            self.rule("To compare, add the comparative ending (**" + self._affix_text_rel("COMPAR") + "**: 'bigger') or the superlative ending (**"
                      + self._affix_text_rel("SUPERL") + "**: 'biggest') to the adjective. To make an adverb ('quickly') add **" + self._affix_text_rel("ADV") + "**.")
            rows = []
            for rel, en in [("COMPAR", "bigger"), ("SUPERL", "biggest")]:
                rows.append((en, f"big +{rel}", self.form(g.word("big", [], [g._affix_part(rel, rel)]))))
            if self.has("quick"):
                rows.append(("quickly", "quick +ADV", self.form(g.word("quick", [], [g._affix_part("ADV", "ADV")]))))
            self.add(*_table(["English", "Recipe", self.spec.name], rows))

    def _affix_text_rel(self, rel):
        a = self.g.table["affixes"][rel]
        f = self.g.form(a["phonemes"])
        if self.g.analytic:
            return f"the word {f} " + ("before" if a["position"] == "prefix" else "after") + " it"
        return f + "-" if a["position"] == "prefix" else "-" + f

    def _noun_with_gender(self, idx):
        if not self.m.genders:
            return "dog" if idx == 0 and self.has("dog") else ("horse" if idx == 1 and self.has("horse") else None)
        gd = self.m.genders[min(idx, len(self.m.genders) - 1)]
        for w in self._all_nouns():
            if self.g.gender_of(w) == gd:
                return w
        return None

    # ------------------------------------------------------------------ lesson 8: sentences
    def sentences(self):
        g, m, s = self.g, self.m, self.s
        self.lesson("Building sentences")
        self.rule(f"The basic word order is **{s.word_order}**" + (" (the verb comes last)." if s.word_order.endswith("V") else
                  " (the verb comes first)." if s.word_order.startswith("V") else " (the verb comes in the middle)."))
        W = {"head": "wizard", "definite": True}
        D = {"head": "dragon", "definite": True}
        self.add("**1. Subject and verb**", "")
        self.example("The wizard sleeps.", subject=W, verb="sleep", keep=True)
        self.add("**2. Adding an object**", "")
        self.example("The wizard sees the dragon.", subject=W, verb="see", object=D, keep=True)
        if m.cases:
            self.note("Notice the case ending on the object." if m.case_alignment.startswith("nom") else "Notice the ending on the doer.")
        self.add("**3. Describing with adjectives**", "")
        self.example("The old wizard sees the big dragon.", subject=dict(W, adjectives=["old"]), verb="see", object=dict(D, adjectives=["big"]), keep=True)
        self.add("**4. Saying whose it is**", "")
        pos_text = "before" if s.genitive_order == "genitive-noun" else "after"
        self.rule(f"The owner comes **{pos_text}** the thing owned" + (", marked with the possessive ending." if not m.cases or "genitive" not in m.cases else ", in the genitive case."))
        self.example("My dog eats the bread.", subject={"head": "dog", "possessor": "i"}, verb="eat", object={"head": "bread", "definite": True}, keep=True)
        self.example("The king's horse is fast.", subject={"head": "horse", "possessor": "king", "definite": True}, predicate={"adjective": "fast"}, keep=True)
        self.add("**5. Where, when and with what**", "")
        used_cases = [c for c in ("locative", "allative", "dative", "instrumental", "comitative", "ablative") if c in m.cases]
        if used_cases:
            self.rule("Places and directions are shown with **case endings** where the language has one for the meaning, and with " +
                      f"{s.adposition}s (little words {'after' if s.adposition == 'postposition' else 'before'} the noun) otherwise.")
        else:
            self.rule(f"Places and directions use **{s.adposition}s**: a little word like 'in' or 'to' placed {'after' if s.adposition == 'postposition' else 'before'} the noun.")
        F = {"head": "forest", "definite": True}
        self.example("The wizard walks in the forest.", subject=W, verb="walk", pps=[("in", F)], keep=True)
        self.example("The wizard gives the book to the king.", subject=W, verb="give", object={"head": "book", "definite": True},
                     pps=[("to", {"head": "king", "definite": True})], keep=True)
        self.example("I fight with a sword.", subject={"head": "i"}, verb="fight", pps=[("with", {"head": "sword", "definite": False})], drop_subject=False, keep=True)
        pp = "Little words" if not used_cases else "Cases and little words"
        self.add("**6. Past and future**", "")
        self.example("The wizard saw the dragon.", subject=W, verb="see", object=D, kind="past", keep=True)
        self.example("The wizard will see the dragon.", subject=W, verb="see", object=D, kind="future", keep=True)
        if not m.tenses:
            self.note("With no tenses, a time word carries the meaning.")
        elif "non-past" in m.tenses:
            self.note("There is no separate future here: the non-past form means both 'does' and 'will do'.")
        elif "non-future" in m.tenses:
            self.note("There is no separate past here: the non-future form means both 'did' and 'does'.")
        self.add("**7. Joining sentences**", "")
        if self.has("and", "but"):
            a = g.clause(subject=W, verb="sleep", tense=self.time_ref("present")[0])
            b = g.clause(subject=D, verb="sleep", tense=self.time_ref("present")[0])
            self.rule(f"Join two sentences with **{self.w('and')}** ('and') or **{self.w('but')}** ('but') between them.")
            self._block("The wizard sleeps and the dragon sleeps.", a + g.free_word("and") + b)
        self.add("**8. Having**", "")
        self.example("The king has a castle.", subject={"head": "king", "definite": True}, verb="have", object={"head": "castle", "definite": False}, keep=True)
        if not m.case_alignment.startswith("nom"):
            self.note("The doer of 'have' takes the ergative ending, because 'have' acts on an object.")

    # ------------------------------------------------------------------ lesson 9: questions
    def questions(self):
        g, m, s = self.g, self.m, self.s
        self.lesson("Questions, answers and 'not'")
        qs = s.question_strategy
        W = {"head": "wizard", "definite": True}
        D = {"head": "dragon", "definite": True}
        self.add("**Yes/no questions**", "")
        if qs == "particle":
            self.rule(f"Add the question word **{self.form(g.particle('q:particle'))}** at the **{'end' if g.question_final else 'start'}** of a statement.")
        elif qs == "verbal affix":
            self.rule(f"Add the question ending **{self._affix_text('q:affix')}** to the verb.")
        elif qs == "verb inversion":
            if s.word_order.startswith("V"):
                self.rule("A question has the same word order as a statement, since the verb is already first; the voice rises at the end.")
            else:
                self.rule("Put the **verb first**, before the subject.")
        else:
            self.rule("A question has **the same words as a statement**; only the voice rises at the end.")
        if qs in ("verb inversion", "verbal affix") and (not s.has_copula or s.copula_form == "zero"):
            self.note("A sentence with no verb (such as 'The dragon is big', where the language has no word for 'is') has nowhere to put "
                      "this marking, so only the voice rises at the end.")
        self.example("The wizard sees the dragon.", subject=W, verb="see", object=D, keep=False)
        q_same = qs == "intonation" or (qs == "verb inversion" and s.word_order.startswith("V"))
        self.example("Does the wizard see the dragon?" + (" (said with a rising voice)" if q_same else ""), subject=W, verb="see", object=D, question="yes-no", keep=True)
        self.example("Is the dragon big?", subject=D, predicate={"adjective": "big"}, question="yes-no", keep=True)
        self.add("**Answers**", "")
        if self.has("yes", "no"):
            self.add(f"- Yes: **{self.w('yes')}** / No: **{self.w('no')}**", "")
        self.rule("To answer, say yes or no, or repeat the sentence with the verb.")
        self.add("**Question words**", "")
        rows = [(q, self.w(q)) for q in C.QUESTION_WORDS if self.has(q)]
        self.add(*_table(["English", self.spec.name], rows))
        if g.wh_fronted:
            self.rule("A question word goes at the **start** of the sentence.")
        else:
            self.rule("A question word stays **where the answer would be** (no moving).")
        self.example("Who sees the dragon?", subject={"head": "who"}, verb="see", object=D, question="wh", keep=True)
        self.example("What does the wizard see?", subject=W, verb="see", object={"head": "what"}, question="wh", keep=True)
        self.example("Where does the wizard sleep?", subject=W, verb="sleep", adverbs=["where"], question="wh", keep=True)
        self.example("Why does the dragon sleep?", subject=D, verb="sleep", adverbs=["why"], question="wh", keep=True)
        self.example("How does the wizard walk?", subject=W, verb="walk", adverbs=["how"], question="wh", keep=False)
        self.add("**Saying 'not'** (review)", "")
        self.example("The wizard does not see the dragon.", subject=W, verb="see", object=D, negated=True, keep=True)
        self.example("I do not know.", subject={"head": "i"}, verb="know", negated=True, drop_subject=False, keep=True)
        self.example("Who does not sleep?", subject={"head": "who"}, verb="sleep", negated=True, question="wh", keep=False)

    # ------------------------------------------------------------------ lesson 10: dialogues
    def dialogues(self):
        g = self.g
        self.lesson("Putting it together: conversations")
        tamo, ira = g.name_for("Tamo"), g.name_for("Ira")
        you = {"head": "you"}
        I = {"head": "i"}
        sword = {"head": "sword", "definite": False}
        D = {"head": "dragon", "definite": True}
        self.add("Two travellers meet at an inn. Read each line aloud, then cover the English and translate it back.", "")

        def say(who, en, **kw):
            self.add(f"**{who}**", "")
            if "word" in kw:
                if self.has(kw["word"]):
                    self.add(f"```\n{self.w(kw['word'])}\n'{en}'\n```", "")
                return
            self.example(en, keep=kw.pop("keep", True), **kw)

        say("Tamo", "Hello!", word="hello")
        say("Ira", "Hello! What is your name?", subject={"head": "what"}, predicate={"head": "name", "possessor": "you"}, question="wh") if self.has("name") else None
        say("Tamo", "My name is Tamo.", subject={"head": "name", "possessor": "i"}, predicate={"head": tamo}) if self.has("name") else None
        say("Ira", "My name is Ira.", subject={"head": "name", "possessor": "i"}, predicate={"head": ira}, keep=False) if self.has("name") else None
        say("Ira", "I am a priest.", subject=I, predicate={"head": "priest", "definite": False}, drop_subject=False, keep=False)
        say("Tamo", "Do you have a sword?", subject=you, verb="have", object=sword, question="yes-no", drop_subject=False)
        say("Ira", "Yes, I have a sword.", subject=I, verb="have", object=sword, drop_subject=False, keep=False)
        say("Tamo", "Where is the dragon?", subject=D, predicate={"adverb": "where"}, question="wh")
        say("Ira", "The dragon sleeps in the mountain.", subject=D, verb="sleep", pps=[("in", {"head": "mountain", "definite": True})])
        say("Tamo", "I do not fear the dragon.", subject=I, verb="fear", object=D, negated=True, drop_subject=False, keep=False) if self.has("fear") else None
        say("Ira", "Goodbye!", word="goodbye")

    # ------------------------------------------------------------------ exercises
    def exercises(self):
        g, m = self.g, self.m
        self.lesson("Practice")
        seen, uniq = set(), []
        for en, toks in self.bank:
            if en not in seen:
                seen.add(en)
                uniq.append((en, toks))
        pick_a = uniq[0::3][:10]
        pick_b = uniq[1::3][:10]
        self.add("**A. Translate into English** (use the dictionary at the end)", "")
        for n, (en, toks) in enumerate(pick_a, 1):
            self.add(f"{n}. {self.form(toks)}")
        self.add("")
        self.add("**B. Translate into " + self.spec.name + "**", "")
        for n, (en, toks) in enumerate(pick_b, 1):
            self.add(f"{n}. {en}")
        self.add("")
        drills = self.drills()
        if drills:
            self.add("**C. Endings and agreement** (give the correct form)", "")
            for n, (q, a) in enumerate(drills, 1):
                self.add(f"{n}. {q}")
            self.add("")
        self.add("<details><summary>Answer key</summary>", "")
        self.add("**A.**", "")
        for n, (en, toks) in enumerate(pick_a, 1):
            self.add(f"{n}. {en}")
        self.add("")
        self.add("**B.**", "")
        for n, (en, toks) in enumerate(pick_b, 1):
            self.add(f"{n}. {self.form(toks)}")
        if drills:
            self.add("", "**C.**", "")
            for n, (q, a) in enumerate(drills, 1):
                self.add(f"{n}. {a}")
        self.add("", "</details>", "")

    def drills(self):
        """Small form-building questions, one for each agreement feature the language has."""
        g, m = self.g, self.m
        out = []
        if g.subject_agrees:
            for lab, p, n in (PERSONS[3], PERSONS[5], PERSONS[1]):
                b, v, a = g.verb_complex("go", tense=g.zero_tense, subj=(p, n))
                out.append((f"Put 'go' ({self.w('go')}) into the form for **{lab}**.", f"**{self.form(b + v + a)}**"))
        if m.genders and not g.analytic:
            for idx in range(min(2, len(m.genders))):
                noun = self._noun_with_gender(idx)
                if noun:
                    out.append((f"Make 'big' ({self.w('big')}) agree with **{noun}** ({self.w(noun)}), which is {m.genders[idx]}.",
                                f"**{self.form(g.word('big', g._concord(m.genders[idx], 'singular', 'nominative')))}**"))
        if m.cases:
            c = [x for x in m.cases if x not in ("nominative", "absolutive")][:2]
            for case in c:
                if self.has("house"):
                    toks, _ = g.noun_phrase("house", case=case)
                    out.append((f"Put 'house' ({self.w('house')}) into the **{case}** case.", f"**{self.form(toks)}**"))
        if "plural" in m.noun_number and self.has("dog"):
            toks, _ = g.noun_phrase("dog", number="plural")
            out.append((f"Make 'dog' ({self.w('dog')}) plural.", f"**{self.form(toks)}**"))
        if m.tenses:
            for t in [x for x in m.tenses if f"tense:{x}" in g.infl][:2]:
                toks = g.clause(subject={"head": "he"}, verb="sleep", tense=t, drop_subject=False)
                out.append((f"Say 'he sleeps' in the **{t}** tense.", f"**{self.form(toks)}**"))
        return out

    # ------------------------------------------------------------------ appendices
    def cheat_sheet(self):
        g = self.g
        self.add("## Appendix A: every ending on one page", "")
        rows = []
        for k, info in g.infl.items():
            f = g.form(info["phonemes"])
            if k in ("q:particle", "cop"):
                where = "separate word" + (" at the end of the sentence" if k == "q:particle" and g.question_final else
                                           " at the start of the sentence" if k == "q:particle" else " in the verb's place")
                shown = f
            elif g.analytic:
                where = "separate word " + ("before" if info["position"] == "prefix" else "after")
                shown = f
            else:
                where = "prefix" if info["position"] == "prefix" else "suffix"
                shown = f + "-" if where == "prefix" else "-" + f
            rows.append((info["category"], k.split(":", 1)[-1], info["gloss"], shown, where))
        if rows:
            self.add(*_table(["Kind", "Value", "Label", "Form", "Where"], rows))
        self.add("**Word-building endings**", "")
        rows = []
        for rel, a in g.table["affixes"].items():
            f = g.form(a["phonemes"])
            shown = f if g.analytic else (f + "-" if a["position"] == "prefix" else "-" + f)
            rows.append((rel, GLOSS[rel], shown))
        self.add(*_table(["Label", "Meaning", "Form"], rows))

    def glossary(self):
        g = self.g
        meaning = {}
        for k, info in g.infl.items():
            cat, val = info["category"], k.split(":", 1)[-1]
            if cat == "agr":
                role, pn = val.split(":")
                meaning[info["gloss"]] = f"person {pn[0]}, {'singular' if pn[1:] == 'sg' else 'plural'}, " + ("the one doing it" if role == "subj" else "the one it is done to")
            else:
                meaning[info["gloss"]] = f"{cat}: {val}"
        meaning.update({"ACC": "case: accusative (object ending, also on pronouns)", "NEG": "negation", "POSS": "possessive (of)",
                        "COMPAR": "comparative (more)", "SUPERL": "superlative (most)", "ADV": "adverb ending",
                        "Q": "question marker", "COP": "copula particle (is / am / are)"})
        used = sorted(x for x in {t for t in self.used_gloss_full} if x in meaning)
        self.add("## Appendix B: grammar labels", "")
        self.add(*_table(["Label", "Meaning"], [(u, meaning[u]) for u in used]))

    def dictionary(self):
        g = self.g
        words = set(C.PRONOUNS + C.DEMONSTRATIVES + C.QUESTION_WORDS + C.COLORS + C.GREETING_WORDS + C.ADJECTIVES + list(C.VERBS)
                    + C.SMALL_WORDS + C.PREPOSITIONS + C.TIME_WORDS + C.FAMILY_TERMS + ["the", "a", "not", "name", "dozen", "hundred"]
                    + [n for n in ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")])
        for grp in C.NOUNS.values():
            words |= set(grp)
        words = sorted(w for w in words if self.has(w))
        self.add("## Appendix C: mini-dictionary", "")
        self.add("**English to " + self.spec.name + "**", "")
        self.add(*_table(["English", self.spec.name], [(w, self.w(w)) for w in words]))
        self.add("**" + self.spec.name + " to English**", "")
        rev = sorted(((self.w(w), w) for w in words), key=lambda x: x[0])
        self.add(*_table([self.spec.name, "English"], rev))

    # ------------------------------------------------------------------ whole book
    def render(self) -> str:
        self.title()
        self.at_a_glance()
        self.sounds()
        self.greetings()
        self.pronouns()
        self.numbers_colors()
        self.nouns()
        self.verbs()
        self.adjectives()
        self.sentences()
        self.questions()
        self.dialogues()
        self.exercises()
        self.cheat_sheet()
        self.glossary()
        self.dictionary()
        return "\n".join(self.L) + "\n"


def abbr_values():
    from .infl_inventory import ABBR
    out = []
    for k, v in ABBR.items():
        out.append((v, k))
    out += [("ACC", "accusative (object ending)"), ("NEG", "negation"), ("Q", "question marker"), ("COP", "copula (is/am/are)"),
            ("1SG", "I"), ("2SG", "you"), ("3SG", "he/she/it"), ("1PL", "we"), ("2PL", "you (all)"), ("3PL", "they"),
            ("1SG.O", "me"), ("2SG.O", "you (object)"), ("3SG.O", "him/her/it (object)"), ("1PL.O", "us"), ("2PL.O", "you all (object)"), ("3PL.O", "them (object)"),
            ("POSS", "possessive (of)"), ("COMPAR", "comparative"), ("SUPERL", "superlative")]
    return out


def build_book(spec, state, vocab) -> str:
    return Book(spec, state, vocab).render()
