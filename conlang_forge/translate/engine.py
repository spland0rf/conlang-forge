"""One language's translator: everything that needs no model. Cheap to rebuild, so cached per conlang by the service."""
from __future__ import annotations

from ..spec import LanguageSpec
from .assemble import Assembler
from .lex import EnglishVocab
from .parser import parse
from .printer import Printer
from .realize import Realizer
from .validate import autorepair, validate


class LanguageTranslator:
    def __init__(self, lang: dict):
        self.spec = LanguageSpec.from_dict(lang["spec"])
        self.state = {"table": lang["table"], "stems": lang["stems"], "entries": lang["lexicon"], "plan": lang.get("plan")}
        self.V = EnglishVocab(self.state["entries"])
        self.realizer = Realizer(self.spec, self.state, None)
        self.assembler = Assembler(self.spec, self.state, self.V, self.realizer.g)
        self.printer = Printer(self.V)

    # ------------------------------------------------------------------ English -> language (no model)
    def parse(self, re_text: str):
        doc, issues = parse(self.V, re_text)
        issues += validate(doc, self.V, self.realizer.g)
        return doc, issues

    def to_language(self, re_text: str) -> dict:
        """Restricted English (as written by the Reducer or edited by the user) -> the language. Never raises: whatever
        cannot be read is reported in `issues` and replaced by the nearest reasonable thing."""
        doc, issues = self.parse(re_text)
        fixed, notes = autorepair(doc, self.V, self.realizer.g)
        sentences, rissues = self.realizer.document(fixed)
        all_issues = [i for i in issues if i["code"] != "unknown_word"] + notes + rissues
        return {"re_text": self.printer.document(fixed), "sentences": sentences,
                "text": " ".join(s["text"] for s in sentences), "issues": all_issues, "doc": fixed,
                "unknown": [i["word"] for i in issues if i["code"] == "unknown_word" and i.get("word")]}

    # ------------------------------------------------------------------ language -> English (no model)
    def from_language(self, text: str) -> dict:
        doc, inter = self.assembler.read(text)
        issues = []
        for si, sent in enumerate(inter):
            for tok in sent:
                if not tok["known"]:
                    issues.append({"level": "warn", "code": "unknown_word", "sentence": si, "word": tok["text"],
                                   "message": f"'{tok['text']}' is not a word of this language; it is shown as a name."})
        return {"re_text": self.printer.document(doc), "interlinear": inter, "issues": issues, "doc": doc}
