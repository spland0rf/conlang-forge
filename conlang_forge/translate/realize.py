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
    def _np(self, d):
        if not d:
            return d
        d = {k: v for k, v in d.items() if v is not None and k != "unknown"}
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
            pred = self._np(pred)
        args = dict(subject=self._np(c.get("subject")), verb=c.get("verb"), object=self._np(c.get("object")),
                    predicate=pred, pps=[(p, self._np(n)) for p, n in c.get("pps", [])], adverbs=list(c.get("adverbs", [])),
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
                if g.has(link):
                    toks += g.free_word(link)
            toks += self.clause(c, issues, idx)
        forms, glosses = g.interlinear(toks)
        text = " ".join(forms)
        text = text[:1].upper() + text[1:] + s.get("mark", ".")
        return {"text": text, "forms": forms, "glosses": glosses, "gloss": " ".join(glosses)}

    def document(self, doc):
        issues, out = [], []
        for i, s in enumerate(doc["sentences"]):
            out.append(self.sentence(s, i, issues))
        return out, issues
