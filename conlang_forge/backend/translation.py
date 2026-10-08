"""Translation service: English <-> a user's language. Glue between the conlang store, the translator and the model.

English -> language uses the Reducer (a model call, metered) unless the caller supplies restricted English, which is free.
Language -> English is code only (word analysis and a literal reading); the Smoother (a model call) is optional.
"""
from __future__ import annotations

import threading
from collections import OrderedDict

from ..translate.engine import LanguageTranslator
from ..translate.reducer import Reducer, Smoother
from .errors import LLMDisabled, ValidationFailed
from .permissions import Actor

MAX_CHARS = 4000
MAX_SENTENCES = 60


class TranslationService:
    def __init__(self, conlangs, llm, max_cached: int = 12):
        self.conlangs, self.llm = conlangs, llm
        self._cache, self._max, self._lock = OrderedDict(), max_cached, threading.Lock()

    # ------------------------------------------------------------------ translators
    def translator(self, actor: Actor, conlang_id: str, script: str = "plain") -> LanguageTranslator:
        summary = self.conlangs.summary(actor, conlang_id)               # checks read permission
        key = (conlang_id, summary["updated_at"], script)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        tr = LanguageTranslator(self.conlangs.get_language(actor, conlang_id, script))
        with self._lock:
            self._cache[key] = tr
            while len(self._cache) > self._max:
                self._cache.popitem(last=False)
        return tr

    @staticmethod
    def _check(text) -> str:
        if not isinstance(text, str) or not text.strip():
            raise ValidationFailed("enter some text to translate")
        text = text.strip()
        if len(text) > MAX_CHARS:
            raise ValidationFailed(f"text is too long ({len(text)} characters; the limit is {MAX_CHARS})")
        return text

    @staticmethod
    def _issues(issues):
        out, seen = [], set()
        for i in issues:
            key = (i.get("code"), i.get("word"), i.get("sentence"), i.get("message"))
            if key in seen:
                continue
            seen.add(key)
            out.append({k: v for k, v in i.items() if k in ("level", "code", "message", "word", "sentence", "suggestions")})
        return out

    # ------------------------------------------------------------------ English -> language
    def to_language(self, actor: Actor, conlang_id: str, text: str, *, mode: str = "english", script: str = "plain") -> dict:
        text = self._check(text)
        if mode not in ("english", "restricted"):
            raise ValidationFailed("mode must be 'english' or 'restricted'")
        tr = self.translator(actor, conlang_id, script)
        reduced, usage, rounds = None, None, 0
        if mode == "english":
            if self.llm is None:
                raise LLMDisabled("no model is configured on this server; use restricted English instead")
            red = Reducer(self.llm).reduce(actor, conlang_id, tr, text)
            re_text, usage, rounds = red["re_text"], red["usage"], red["rounds"]
            reduced = re_text
        else:
            re_text = text
        res = tr.to_language(re_text)
        if len(res["sentences"]) > MAX_SENTENCES:
            raise ValidationFailed(f"too many sentences (limit {MAX_SENTENCES})")
        return {"mode": mode, "input": text, "reduced": reduced, "re_text": res["re_text"], "text": res["text"],
                "sentences": res["sentences"], "issues": self._issues(res["issues"]), "usage": usage, "repair_rounds": rounds}

    # ------------------------------------------------------------------ language -> English
    def from_language(self, actor: Actor, conlang_id: str, text: str, *, smooth: bool = False) -> dict:
        text = self._check(text)
        tr = self.translator(actor, conlang_id)
        res = tr.from_language(text)
        doc, inter = res["doc"], res["interlinear"]
        literal, items = [], []
        for i, s in enumerate(doc["sentences"]):
            lit = tr.printer.sentence(s)
            literal.append(lit)
            toks = inter[i] if i < len(inter) else []
            gloss = " ".join(t["gloss"] + (("/" + "/".join(t["alts"])) if t.get("alts") else "") for t in toks)
            items.append({"text": " ".join(t["text"] for t in toks), "gloss": gloss, "literal": lit})
        out = {"input": text, "literal": literal, "re_text": res["re_text"], "interlinear": inter,
               "issues": self._issues(res["issues"]), "natural": None, "usage": None}
        if smooth:
            if self.llm is None:
                raise LLMDisabled("no model is configured on this server")
            sm = Smoother(self.llm).smooth(actor, conlang_id, items)
            lines = sm["lines"]
            if len(lines) != len(items):                       # the model merged or split lines: fall back to one block
                lines = [" ".join(lines)] if lines else literal
            out["natural"], out["usage"] = lines, sm["usage"]
        return out
