"""Structured clauses -> the language, using the grammar engine. Pure code: no model, no tokens, deterministic."""
from __future__ import annotations

from .. import curriculum
from ..grammar import Grammar, GrammarError
from .parser import Issue

TENSE_PREF = {"past": ["past", "recent past"], "future": ["future"], "present": ["present"]}
ASPECT_PREF = {"perfect": ["perfective", "completive", "perfect"],
               "progressive": ["progressive", "imperfective", "continuative"]}
WH = ("where", "when", "why", "how")


class Realizer:
    def __init__(self, spec, state, vocab):
        self.spec = spec
        self.g = Grammar(spec, state, vocab)
        self.g.set_semantics(curriculum.semantics())

    # ------------------------------------------------------------------ feature mapping
    def tense_for(self, tense, issues, idx):
        tenses = self.spec.morphology.tenses
        for cand in TENSE_PREF.get(tense or "present", []):
            if cand in tenses:
                return cand
        if tense in ("past", "future") and tense not in tenses:
            if not tenses:
                issues.append(Issue("info", "tense_unmarked", f"This language does not mark {tense} time on the verb.", sentence=idx))
            elif tense == "future" and "non-past" in tenses or tense == "past" and "non-future" in tenses:
                pass
        return None

    def aspect_for(self, aspect, issues, idx):
        if not aspect:
            return None
        for cand in ASPECT_PREF.get(aspect, []):
            if cand in self.spec.morphology.aspects:
                return cand
        issues.append(Issue("info", "aspect_unmarked", f"This language has no {aspect} aspect, so it was left unmarked.", sentence=idx))
        return None

    # ------------------------------------------------------------------ noun phrases
    def _relative_tokens(self, rel, issues, idx):
        """'who sleeps' / 'that the king saw' as tokens, to follow the noun they describe."""
        g = self.g
        word = rel.get("cid") or ("that" if rel.get("gap") == "possessor" else rel.get("word"))
        toks = g.free_word(word) if word and g.has(word) else []
        try:
            args = self._clause_args(rel["clause"], issues, idx)
            args.update(mood="indicative", question=None)
            return toks + g.clause(**args)
        except (GrammarError, KeyError) as e:
            issues.append(Issue("error", "cannot_realise", f"Could not build a describing clause (missing word {e}).", sentence=idx))
            return []

    def _np(self, d, issues=None, idx=0):
        if not d:
            return d
        rel = d.get("relative")
        d = {k: v for k, v in d.items() if v is not None and k not in ("unknown", "relative")}
        if rel and issues is not None:
            d["rel_tokens"] = self._relative_tokens(rel, issues, idx)
        h = d.get("head")
        if h and str(h).startswith("#"):
            d["head"] = self.g.name_for(h[1:])
        if d.get("possessor") and str(d["possessor"]).startswith("#"):
            d["possessor"] = self.g.name_for(d["possessor"][1:])
        d.setdefault("number", "singular")
        if "adjectives" in d:
            d["adjectives"] = list(d["adjectives"])
        return d

    def _clause_args(self, c, issues, idx):
        pred = c.get("predicate")
        if pred and "head" in pred:
            pred = self._np(pred, issues, idx)
        args = dict(subject=self._np(c.get("subject"), issues, idx), verb=c.get("verb"), object=self._np(c.get("object"), issues, idx),
                    predicate=pred, pps=[(p, self._np(n, issues, idx)) for p, n in c.get("pps", [])], adverbs=list(c.get("adverbs", [])),
                    tense=self.tense_for(c.get("tense"), issues, idx), aspect=self.aspect_for(c.get("aspect"), issues, idx),
                    mood=c.get("mood") or "indicative", negated=bool(c.get("negated")), question=c.get("question"))
        if args["mood"] == "imperative" and "imperative" not in self.spec.morphology.moods:
            issues.append(Issue("info", "mood_unmarked", "This language has no imperative ending; the plain verb is used.", sentence=idx))
        return args

    # ------------------------------------------------------------------ output
    def clause(self, c, issues, idx):
        g = self.g
        if c.get("kind") == "fragment":
            toks = []
            for w in c["words"]:
                if str(w).startswith("#"):
                    w = g.name_for(w[1:])
                if g.has(w):
                    toks += g.free_word(w)
                else:
                    issues.append(Issue("error", "unknown_word", f"'{w}' is not in this language.", sentence=idx, word=w))
            return toks
        try:
            return g.clause(**self._clause_args(c, issues, idx))
        except (GrammarError, KeyError) as e:
            issues.append(Issue("error", "cannot_realise", f"Could not build this clause (missing word {e}).", sentence=idx))
            return []

    def sentence(self, s, idx, issues):
        g = self.g
        toks = []
        for i, c in enumerate(s["clauses"]):
            if i:
                link = s["links"][i - 1] if i - 1 < len(s["links"]) else "and"
                if link and g.has(link):
                    toks += g.free_word(link)
            intro = c.get("intro")
            if intro:
                if g.has(intro):
                    toks += g.free_word(intro)
                else:
                    issues.append(Issue("info", "no_word_for_conjunction", f"This language has no word for '{intro}', so the clauses are simply placed side by side.", sentence=idx))
            toks += self.clause(c, issues, idx)
        forms, glosses = g.interlinear(toks)
        text = " ".join(forms)
        text = text[:1].upper() + text[1:] + s.get("mark", ".")
        if s.get("quote"):
            text = "\u201c" + text + "\u201d"
        return {"text": text, "forms": forms, "glosses": glosses, "gloss": " ".join(glosses)}

    def document(self, doc):
        issues, out = [], []
        for i, s in enumerate(doc["sentences"]):
            out.append(self.sentence(s, i, issues))
        return out, issues
