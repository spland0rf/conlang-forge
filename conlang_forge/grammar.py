"""Inflection and clause realisation: turns "the old wizard sees the dragon" into the language's words, in the
language's word order, with every ending the spec calls for, plus a word-by-word gloss.

The morphemes themselves are drawn in morph.build_table (table["infl"]); this module only decides where they go.
It reads the finished lexicon, so every root is the real dictionary word. Nothing here is random except gender
assignment and a few small per-language choices, and those are pure functions of (seed, word / property), so the
same language always produces the same sentences.

Vocabulary in sentences is referred to by English concept id ("wizard", "see", "i").
"""
from __future__ import annotations

from .infl_inventory import abbr, zero_tense
from .morph import SPACE, build_table, is_analytic, join, render_flat
from .wordgen import rng_for

PRONOUN = {"i": (1, "sg"), "you": (2, "sg"), "he": (3, "sg"), "she": (3, "sg"), "it": (3, "sg"),
           "we": (1, "pl"), "they": (3, "pl")}
POSSESSIVE = {"i": "my", "you": "your", "he": "his", "she": "her", "it": "its", "we": "our", "they": "their"}
CASE_FOR = {  # which case replaces an English preposition, best match first
    "in": ["locative", "inessive"], "at": ["locative"], "on": ["locative"], "to": ["allative", "dative"],
    "from": ["ablative", "elative"], "with": ["comitative", "instrumental"], "of": ["genitive"],
    "for": ["benefactive", "dative"], "by": ["instrumental"]}
WH_WORDS = ["who", "what", "which", "where", "when", "why", "how"]


class GrammarError(KeyError):
    pass


def _tok(flat, gloss):
    return {"flat": list(flat), "gloss": gloss}


class Grammar:
    def __init__(self, spec, state, vocab=None):
        self.spec, self.m, self.s = spec, spec.morphology, spec.syntax
        self.table = state["table"]
        self.infl = self.table.get("infl") or build_table(spec)["infl"]
        self.E = {e["concept_id"]: e for e in state["entries"] if not e["retired"]}
        self.analytic = is_analytic(spec)
        self.seed = spec.seed
        self.extra = {}   # proper names: "#Name" -> phonemes (made by name_for)
        self.sem = {}  # concept id -> {"sex": "f"/"m"/None, "animate": bool, "kind": str}
        self.zero_tense = zero_tense(spec)

    # ------------------------------------------------------------------ language-level choices
    def prop(self, name, options, weights=None):
        p = ((getattr(self.spec, "tuning", None) or {}).get("rates") or {}).get("grammar." + name)
        if p is not None and len(options) == 2:                  # the language's own rate for this small choice
            weights = [float(p), 1 - float(p)]
        return rng_for(self.seed, "grammar", name).choices(options, weights)[0]

    @property
    def verb_final(self):
        return self.s.word_order.endswith("V")

    @property
    def wh_fronted(self):
        return False if self.verb_final else self.prop("wh_fronting", [True, False], [.5, .5])

    @property
    def plural_after_numeral(self):
        return self.prop("plural_after_numeral", [True, False], [.55, .45])

    @property
    def number_order(self):
        """'big-first': twenty-three; 'small-first': three-and-twenty."""
        return self.prop("number_order", ["big-first", "small-first"], [.85, .15])

    @property
    def question_final(self):
        return self.infl.get("q:particle", {}).get("position") == "suffix"

    @property
    def subject_agrees(self):
        return self.m.verb_agreement != "none"

    @property
    def pro_drop(self):
        """Pronoun subjects are dropped only where the verb still shows who is meant."""
        return bool(self.s.pro_drop and self.subject_agrees)

    def has(self, cid):
        return cid in self.E or cid in self.extra

    def name_for(self, label, kind="person"):
        """A personal name made with the language's own sounds, the same every time for the same label."""
        from .wordgen import make_word
        from .morph import valid_word
        key = "#" + label
        if key not in self.extra:
            for attempt in range(200):
                r = rng_for(self.seed, "personal-name", label, attempt)
                syl = make_word(self.spec, r, r.choice([2, 2, 3]))
                flat = [p for sy in syl for p in sy]
                if valid_word(self.spec, flat) and self.form(flat) not in self._forms():
                    break          # a name must never spell a dictionary word, or reading it back would be ambiguous
            self.extra[key] = flat
        return key

    def _forms(self):
        if not hasattr(self, "_form_set"):
            self._form_set = {e["form"] for e in self.E.values()}
        return self._form_set

    def flat(self, cid):
        if cid in self.extra:
            return list(self.extra[cid])
        if cid not in self.E:
            raise GrammarError(cid)
        return list(self.E[cid]["phonemes"])

    def form(self, flat):
        return render_flat(self.spec, flat)[0]

    def gloss_of(self, cid):
        if cid in self.extra:
            return cid[1:].upper()
        e = self.E[cid]
        return e["lemma"] if not e.get("gloss") else e["gloss"]

    # ------------------------------------------------------------------ building words
    def _word(self, stem_flat, stem_gloss, keys=(), extra_parts=()):
        """Stem plus morphemes. keys (and extra_parts: (key-like dict, gloss) pairs) go from the innermost
        (closest to the stem) to the outermost. Prefixes pile up to the left, suffixes to the right."""
        left, right = [], []
        parts = [self.infl[k] | {"gloss": self.infl[k]["gloss"]} for k in keys if k]
        parts += list(extra_parts)
        for p in parts:
            (left.insert(0, p) if p["position"] == "prefix" else right.append(p))
        seq = [(p["phonemes"], p["gloss"]) for p in left] + [(stem_flat, stem_gloss)] + [(p["phonemes"], p["gloss"]) for p in right]
        if self.analytic:
            return [_tok(f, g) for f, g in seq]
        flat = list(seq[0][0])
        for f, _ in seq[1:]:
            flat = join(self.spec, self.table, flat, f, "affix")
        return [_tok(flat, "-".join(g for _, g in seq))]

    def _affix_part(self, rel, gloss):
        a = self.table["affixes"][rel]
        return {"phonemes": a["phonemes"], "position": a["position"], "gloss": gloss}

    def word(self, cid, keys=(), extra_parts=()):
        return self._word(self.flat(cid), self.gloss_of(cid), keys, extra_parts)

    def free_word(self, cid):
        return [_tok(self.flat(cid), self.gloss_of(cid))]

    def particle(self, key):
        return [_tok(self.infl[key]["phonemes"], self.infl[key]["gloss"])]

    # ------------------------------------------------------------------ nouns and gender
    def set_semantics(self, sem):
        self.sem = dict(sem)

    def gender_of(self, cid):
        g = self.m.genders
        if not g:
            return None
        sem = self.sem.get(cid, {})
        sex, animate = sem.get("sex"), sem.get("animate", False)
        r = rng_for(self.seed, "gender", cid)
        if g == ["masculine", "feminine"]:
            return {"m": "masculine", "f": "feminine"}.get(sex) or r.choice(g)
        if g == ["masculine", "feminine", "neuter"]:
            if sex:
                return {"m": "masculine", "f": "feminine"}[sex]
            return r.choices(g, [.3, .3, .4] if not animate else [.5, .5, 0.0001])[0]
        if g == ["animate", "inanimate"]:
            return "animate" if animate or sex else "inanimate"
        kind = sem.get("kind")  # noun classes: people, animals and plants get their own classes
        base = {"person": 0, "animal": 1, "plant": 2}.get(kind)
        if base is not None and base < len(g):
            return g[base]
        return r.choice(g[min(3, len(g) - 1):])

    def _number_key(self, number):
        k = f"number:{number}"
        return k if k in self.infl else None

    def _concord(self, gender, number, case):
        keys = []
        if gender and not self.analytic and f"gender:{gender}" in self.infl:
            keys.append(f"gender:{gender}")
        nk = self._number_key(number) if number != "singular" else None
        if nk and not self.analytic:
            keys.append(nk)
        if case and self.m.typology == "fusional" and f"case:{case}" in self.infl:
            keys.append(f"case:{case}")
        return keys

    def _case_parts(self, case):
        """(keys, extra_parts) for a case on a noun. Cases that this language does not have add nothing."""
        if case and f"case:{case}" in self.infl:
            return [f"case:{case}"], []
        return [], []

    def pronoun(self, cid, case="nominative"):
        gloss = self.gloss_of(cid)
        keys, extra = [], []
        if case == "accusative":
            extra = [self._affix_part("OBJ", "ACC")]
        elif case == "genitive":
            return self.free_word(POSSESSIVE[cid])
        elif f"case:{case}" in self.infl:
            keys = [f"case:{case}"]
        return self.word(cid, keys, extra)

    def noun_phrase(self, head, *, number="singular", case="nominative", definite=None, adjectives=(), demonstrative=None,
                    numeral=None, possessor=None, plural_pronoun=False):
        """Returns (tokens, info). `head` is a noun, a pronoun, or a question word (who / what)."""
        info = {"head": head, "number": number, "person": 3, "gender": None}
        if head in PRONOUN:
            p, n = PRONOUN[head]
            info.update(person=p, number="plural" if n == "pl" else "singular")
            return self.pronoun(head, case), info
        if head in ("who", "what"):
            ck, cextra = self._case_parts(case)
            if case == "accusative" and not ck:
                cextra = [self._affix_part("OBJ", "ACC")]
            return self.word(head, ck, cextra), info
        gender = self.gender_of(head) if head[:1] != "#" else None
        info["gender"] = gender
        agree_number = number
        if numeral is not None and numeral != 1:
            number = "plural" if self.plural_after_numeral else "singular"
            agree_number = number
        before, after = [], []
        # determiners
        art_cid = None
        if demonstrative:
            art_cid = demonstrative if number == "singular" else {"this": "these", "that": "those"}[demonstrative]
        elif definite is True and self.m.definiteness in ("definite article", "definite+indefinite articles"):
            art_cid = "the"
        elif definite is False and self.m.definiteness == "definite+indefinite articles" and number == "singular":
            art_cid = "a"
        if art_cid and self.has(art_cid):
            conc = self._concord(gender, agree_number if art_cid in ("the", "a") else "singular", case)
            if art_cid in ("these", "those", "this", "that"):
                conc = self._concord(gender, "singular", case)
            before += self.word(art_cid, conc)
        if numeral is not None:
            before += self.numeral(numeral)
            if self.analytic and gender and f"gender:{gender}" in self.infl:  # classifier particle after a number
                before += self.particle(f"gender:{gender}")
        adj_toks = []
        for a in adjectives:
            adj_toks += self.word(a, self._concord(gender, agree_number, case))
        if possessor is not None:
            ptoks = self.possessor(possessor)
        else:
            ptoks = []
        noun_keys = []
        nk = self._number_key(number) if number != "singular" else None
        if nk:
            noun_keys.append(nk)
        ck, cextra = self._case_parts(case)
        if ck:
            noun_keys += ck
        if definite is True and self.m.definiteness == "definiteness affix":
            noun_keys.insert(0, "def:definite")
        noun = self.word(head, noun_keys, cextra)
        if self.s.adjective_order == "adjective-noun":
            core = before + adj_toks + noun
        else:
            core = before + noun + adj_toks
        if ptoks:
            core = (ptoks + core) if self.s.genitive_order == "genitive-noun" else (core + ptoks)
        info["number"] = number
        return core, info

    def possessor(self, who):
        if who in PRONOUN:
            return self.free_word(POSSESSIVE[who])
        toks, _ = self.noun_phrase(who, case="genitive")
        if f"case:genitive" not in self.infl:   # no genitive case: the possessive affix does the job
            gen = self.word(who, [], [self._affix_part("POSS", "POSS")])
            return gen
        return toks

    # ------------------------------------------------------------------ numerals
    def numeral(self, n):
        words = self.numeral_words(n)
        toks = []
        for w in words:
            toks += self.free_word(w)
        return toks

    def numeral_words(self, n):
        """Concept ids spelling out n (0 <= n < 1000). Everything up to ten has its own word; above that the
        language counts in its base (5, 8, 10, 12 or 20): "2 x base + rest", with 'hundred' for 100 in base 10 and
        the base word twice for base squared. The big part comes first unless the language counts small-first."""
        lex = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
        if n <= 10:
            return [lex[n]]
        base = self.m.numeral_base
        bw = {5: "five", 8: "eight", 10: "ten", 12: "dozen", 20: "twenty"}[base]
        if base == 12 and not self.has("dozen"):
            base, bw = 10, "ten"
        if base == 10 and n >= 100:
            q, r = divmod(n, 100)
            head = (self.numeral_words(q) if q > 1 else []) + ["hundred"]
        elif base != 10 and n >= base * base:
            q, r = divmod(n, base * base)
            head = (self.numeral_words(q) if q > 1 else []) + [bw, bw]
        elif n >= base:
            q, r = divmod(n, base)
            head = (self.numeral_words(q) if q > 1 else []) + [bw]
        else:                       # 11 .. base-1 (base 12 or 20): ten and the rest
            head, r = ["ten"], n - 10
        tail = self.numeral_words(r) if r else []
        if self.number_order == "big-first" or not tail or not self.has("and"):
            return head + tail
        return tail + ["and"] + head          # "three and twenty": the link keeps 12 (two-and-ten) apart from 20 (two ten)

    # ------------------------------------------------------------------ verbs
    def agreement_keys(self, subj, obj=None):
        keys = []
        if self.m.verb_agreement == "none":
            return keys
        p, n = subj
        keys.append(f"agr:subj:{p}{n}")
        if obj and self.m.verb_agreement != "subject":
            keys.append(f"agr:obj:{obj[0]}{obj[1]}")
        return keys

    def verb_complex(self, verb, *, tense=None, aspect=None, mood="indicative", evid=None, subj=(3, "sg"), obj=None,
                     negated=False, question=False, as_stem=None):
        """Tokens for the verb with tense/aspect/mood/agreement/negation. Returns (before, verb, after) where
        before/after are separate particles that sit next to the verb (negation, auxiliaries)."""
        chain = []
        extra = []
        neg = self.m.negation if negated else None
        if neg == "verbal affix":
            extra.append(self._affix_part("NEG", "NEG"))
        if aspect and f"aspect:{aspect}" in self.infl:
            chain.append(f"aspect:{aspect}")
        if tense and f"tense:{tense}" in self.infl:
            chain.append(f"tense:{tense}")
        if mood and f"mood:{mood}" in self.infl:
            chain.append(f"mood:{mood}")
        if evid and f"evid:{evid}" in self.infl:
            chain.append(f"evid:{evid}")
        chain += self.agreement_keys(subj, obj)
        if question and "q:affix" in self.infl:
            chain.append("q:affix")
        before, after = [], []
        if neg == "auxiliary verb":
            before = self.word("not", chain)          # the negative auxiliary carries the endings
            verb_toks = self.word(verb) if as_stem is None else as_stem
            return [], before + verb_toks, []
        if neg in ("particle before verb", "double negation particle"):
            before = self.free_word("not")
        if neg in ("particle after verb", "double negation particle"):
            after = self.free_word("not")
        # the extra (affix) parts sit closest to the stem, then the chain
        parts = [self.infl[k] for k in chain]
        verb_toks = self._word_mixed(self.flat(verb), self.gloss_of(verb), extra + parts) if as_stem is None else as_stem
        return before, verb_toks, after

    def _word_mixed(self, stem_flat, stem_gloss, parts):
        return self._word(stem_flat, stem_gloss, (), parts)

    # ------------------------------------------------------------------ clauses
    def case_for_role(self, role, transitive):
        """nominative-accusative or ergative-absolutive, as far as the language has the cases."""
        if self.m.case_alignment.startswith("nom"):
            return {"subj": "nominative", "obj": "accusative"}[role]
        return {"subj": "ergative" if transitive else "absolutive", "obj": "absolutive"}[role]

    def prep_phrase(self, prep, np_args):
        """'in the house': a case ending if the language has a fitting case, else an adposition."""
        for c in CASE_FOR.get(prep, []):
            if f"case:{c}" in self.infl:
                toks, info = self.noun_phrase(case=c, **np_args)
                return toks, c
        toks, info = self.noun_phrase(case="nominative", **np_args)
        adp = self.free_word(prep) if self.has(prep) else []
        return (adp + toks if self.s.adposition == "preposition" else toks + adp), None

    def clause(self, *, subject, verb=None, object=None, predicate=None, pps=(), adverbs=(), tense="present", aspect=None,
               mood="indicative", evid=None, negated=False, question=None, drop_subject=None):
        """Realise one clause. subject / object are dicts of noun_phrase arguments, e.g.
        {"head": "wizard", "adjectives": ["old"], "definite": True}; predicate is {"head": ..} for "X is a Y" or
        {"adjective": "old"} for "X is old"; pps is a list of (preposition, noun-phrase dict); question is None,
        "yes-no" or "wh" (put the question word in the subject / object / pps / adverbs slot)."""
        transitive = object is not None
        if subject is not None and subject.get("head") == "WH":
            subject = None
        S = O = None
        s_info = {"person": 3, "number": "singular"}
        s_dict = dict(subject) if subject else None
        if s_dict:
            s_toks, s_info = self.noun_phrase(case=self.case_for_role("subj", transitive), **s_dict)
        o_info = None
        if object:
            o_toks, o_info = self.noun_phrase(case=self.case_for_role("obj", True), **dict(object))
        else:
            o_toks = []
        if mood == "imperative" and not s_dict:       # a command is addressed to "you": the verb agrees with the listener
            s_info = {"person": 2, "number": "singular"}
        subj_pn = (s_info["person"], "pl" if s_info["number"] != "singular" else "sg")
        obj_pn = (o_info["person"], "pl" if o_info["number"] != "singular" else "sg") if o_info else None
        if mood == "imperative" and "mood:imperative" not in self.infl:
            mood = "indicative"
        imperative = mood == "imperative"
        drop = self.pro_drop if drop_subject is None else drop_subject
        if imperative:
            drop = True
        subject_is_pronoun = bool(s_dict) and s_dict.get("head") in PRONOUN
        if s_dict and subject_is_pronoun and drop:
            s_toks = []
        cop_tokens = None
        pred_toks = []
        is_yn = question == "yes-no"
        # ---- the verb complex
        if predicate is not None:
            pred_toks, cop_tokens = self._predicate(predicate, s_info, tense, negated, subj_pn, aspect, mood, evid, is_yn)
            before, vtoks, after = cop_tokens
        else:
            before, vtoks, after = self.verb_complex(verb, tense=tense, aspect=aspect, mood=mood, evid=evid, subj=subj_pn,
                                                     obj=obj_pn, negated=negated, question=is_yn)
        vgroup = before + vtoks + after
        arg_o = o_toks if predicate is None else pred_toks
        # ---- adjuncts
        adj_toks = []
        for prep, npd in pps:
            t, _ = self.prep_phrase(prep, npd)
            adj_toks += t
        for adv in adverbs:
            adj_toks += self.free_word(adv) if self.has(adv) else []
        # ---- question words: in place, or moved to the front of the clause
        wh_front = []
        wh_in = lambda d: bool(d) and d.get("head") in ("who", "what", "which", "where", "when", "why", "how")
        parts_S = s_toks if s_dict else []
        if question == "wh" and self.wh_fronted:
            if wh_in(s_dict):
                wh_front, parts_S = parts_S, []
            elif wh_in(object):
                wh_front, arg_o = arg_o, []
            elif predicate is not None and "adverb" in predicate and predicate["adverb"] in WH_WORDS:
                wh_front, arg_o = arg_o, []
            else:
                keep = []
                for a in adverbs:
                    if a in WH_WORDS and not wh_front:
                        wh_front = self.free_word(a)
                        adj_toks = self._remove(adj_toks, wh_front)
        # ---- word order
        order = self.s.word_order
        parts = {"S": parts_S, "V": vgroup, "O": arg_o}
        if is_yn and self.s.question_strategy == "verb inversion" and order[0] != "V":
            seq = ["V"] + [x for x in order if x != "V"]
        else:
            seq = list(order)
        out = []
        for x in seq:
            if x == "V" and adj_toks and self.verb_final:
                out += adj_toks
                adj_toks = []
            out += parts[x]
        out += adj_toks
        out = wh_front + out
        # ---- yes-no particle
        if is_yn and "q:particle" in self.infl:
            q = self.particle("q:particle")
            out = out + q if self.question_final else q + out
        return out

    @staticmethod
    def _remove(tokens, sub):
        n = len(sub)
        for i in range(len(tokens) - n + 1):
            if tokens[i:i + n] == sub:
                return tokens[:i] + tokens[i + n:]
        return tokens

    def _predicate(self, predicate, s_info, tense, negated, subj_pn, aspect, mood, evid, is_yn):
        """'X is a Y' / 'X is old'. Returns (predicate tokens, (before, verb, after))."""
        gender = s_info.get("gender")
        if "adverb" in predicate:
            ptoks = self.free_word(predicate["adverb"])
        elif "adjective" in predicate:
            ptoks = self.word(predicate["adjective"], self._concord(gender, s_info["number"], "nominative"))
        else:
            d = dict(predicate)
            ptoks, _ = self.noun_phrase(case="nominative", **d)
        present = tense in (None, "present", self.zero_tense) or (tense and tense not in self.m.tenses)
        zero = (not self.s.has_copula) or self.s.copula_form == "zero"
        if self.s.has_copula and self.s.copula_form == "particle" and "cop" in self.infl and present:
            cop = self.particle("cop")
            before, vtoks, after = [], cop, []
            if negated:
                before, vtoks, after = self.verb_complex("be", tense=tense, aspect=aspect, mood=mood, evid=evid,
                                                         subj=subj_pn, negated=True, as_stem=cop)
        elif zero and present and not negated and mood == "indicative":
            before, vtoks, after = [], [], []
        else:
            before, vtoks, after = self.verb_complex("be", tense=tense, aspect=aspect, mood=mood, evid=evid, subj=subj_pn,
                                                     negated=negated, question=is_yn)
        return ptoks, (before, vtoks, after)

    # ------------------------------------------------------------------ output
    def render(self, tokens):
        """(text, gloss) where text is the sentence in the language's own spelling and gloss is aligned word by word."""
        forms = [self.form(t["flat"]) for t in tokens]
        return " ".join(forms), tokens and " ".join(t["gloss"] for t in tokens) or ""

    def interlinear(self, tokens):
        forms = [self.form(t["flat"]) for t in tokens]
        glosses = [t["gloss"] for t in tokens]
        return forms, glosses
