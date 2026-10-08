"""Turns a stored language into what the website shows: a profile, dictionary rows, and the downloadable
Markdown/CSV (dictionary and grammar book). Rendering is deterministic, so results are cached per conlang version."""
from __future__ import annotations

import threading
from collections import OrderedDict
from pathlib import Path

from ..dictionary import build_rows, dictionary_csv_full, dictionary_markdown_full
from ..grammar_book import build_book
from ..spec import LanguageSpec
from ..vocab import load_vocab

QUICK_WORDS = ["hello", "goodbye", "yes", "no", "please", "thank", "water", "fire", "king", "queen", "dragon", "sword",
               "friend", "love", "night", "day"]


class LanguageViews:
    def __init__(self, data_dir, max_cached: int = 24):
        self.data_dir = Path(data_dir)
        self._vocabs, self._cache, self._max = {}, OrderedDict(), max_cached
        self._lock = threading.Lock()

    def _vocab(self, version: str):
        if version not in self._vocabs:
            self._vocabs[version] = load_vocab(self.data_dir / f"vocab/v{version}.json")
        return self._vocabs[version]

    def _parts(self, lang: dict):
        spec = LanguageSpec.from_dict(lang["spec"])
        state = {"table": lang["table"], "stems": lang["stems"], "entries": lang["lexicon"], "plan": lang.get("plan")}
        return spec, state, self._vocab(lang["vocab_version"])

    def _cached(self, key, make):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        value = make()                       # slow part outside the lock
        with self._lock:
            self._cache[key] = value
            while len(self._cache) > self._max:
                self._cache.popitem(last=False)
        return value

    # ---- outputs (key = (conlang id, updated_at) so edits invalidate)
    def rows(self, key, lang):
        def make():
            spec, state, vocab = self._parts(lang)
            return build_rows(spec, state, vocab)
        return self._cached((key, "rows"), make)

    def dictionary_md(self, key, lang):
        def make():
            spec, state, vocab = self._parts(lang)
            return dictionary_markdown_full(spec, state, vocab, lang["vocab_version"], self.rows(key, lang))
        return self._cached((key, "dict.md"), make)

    def dictionary_csv(self, key, lang):
        return self._cached((key, "dict.csv"), lambda: dictionary_csv_full(self.rows(key, lang)))

    def grammar_book(self, key, lang):
        def make():
            spec, state, vocab = self._parts(lang)
            return build_book(spec, state, vocab)
        return self._cached((key, "book.md"), make)

    def dictionary_json(self, key, lang) -> dict:
        """Compact rows for client-side search."""
        rows = self.rows(key, lang)
        out = []
        for r in rows:
            if r["retired"]:
                continue
            out.append({"en": r["gloss"], "form": r["form"], "ipa": r["ipa"], "pos": "/".join(r["pos"][:2]),
                        "gender": r["gender"], "plural": r["plural"], "dual": r["dual"], "tenses": r["tenses"],
                        "agreement": r["agreement"], "built": r["derivation"],
                        "related": [{"en": g, "form": f} for g, f in r["related"][:4]]})
        out.sort(key=lambda r: r["en"].lower())
        return {"count": len(out), "entries": out}

    # ---- profile for the overview page
    def profile(self, lang: dict) -> dict:
        spec = LanguageSpec.from_dict(lang["spec"])
        ph, m, sy, rom = spec.phonology, spec.morphology, spec.syntax, spec.orthography.romanization
        ents = {e["concept_id"]: e for e in lang["lexicon"] if not e["retired"]}
        quick = [{"en": ents[w]["gloss"], "form": ents[w]["form"], "ipa": ents[w]["ipa"]} for w in QUICK_WORDS if w in ents]
        live = [e for e in ents.values() if e["kind"] != "bound"]
        one = sum(1 for e in live if len(e["syllables"]) == 1)
        return {
            "name": spec.name, "seed": spec.seed, "words": len(live),
            "one_syllable_share": round(one / max(1, len(live)), 2),
            "sounds": {"consonants": [rom[c] for c in ph.consonants], "vowels": [rom[v] for v in ph.vowels],
                       "syllables": sorted(ph.syllable_templates, key=lambda k: -ph.syllable_templates[k]) if isinstance(ph.syllable_templates, dict) else list(ph.syllable_templates), "stress": ph.stress, "spelling": spec.orthography.style},
            "grammar": {
                "type": m.typology, "word_order": sy.word_order, "adjectives": "adjective before noun" if sy.adjective_order == "adjective-noun" else "adjective after noun",
                "adposition": sy.adposition, "affixes": m.affix_position, "number": [n for n in m.noun_number if n != "singular"],
                "cases": m.cases, "genders": m.genders, "definiteness": m.definiteness, "tenses": m.tenses,
                "aspects": m.aspects, "moods": m.moods, "agreement": m.verb_agreement, "negation": m.negation,
                "questions": sy.question_strategy, "numeral_base": m.numeral_base, "alignment": m.case_alignment,
                "pro_drop": sy.pro_drop},
            "quick_words": quick,
            "vocab_version": lang["vocab_version"],
        }
