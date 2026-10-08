"""Sample-text shaping: reads the user's strings and proposes settings (see conlang_forge/exemplar.py)."""
from __future__ import annotations

import json

from .. import exemplar as X
from .errors import LLMDisabled, ValidationFailed
from .permissions import Actor, require


class ExemplarService:
    def __init__(self, conlangs, llm, db, clock):
        self.conlangs, self.llm, self.db, self.clock = conlangs, llm, db, clock

    def analyze(self, actor: Actor, conlang_id: str, raw_texts, *, use_model: bool = True) -> dict:
        texts = X.clean_texts(raw_texts)
        spec = self.conlangs.current_spec(actor, conlang_id)           # checks read permission
        return self._read(actor, spec, texts, use_model, conlang_id)

    def _read(self, actor, spec, texts, use_model, conlang_id=None, fresh=False) -> dict:
        sounds = [t.split("|")[0].strip() for t in texts]
        rep = X.PhonologyReport(sounds)
        proposals = X.phonology_proposals(spec, rep, fresh)
        notes = []
        if rep.n_words < 3:
            notes.append("There is too little text to judge the sounds. Add a few more words.")
        elif rep.size() == "low":
            notes.append("This is a short sample, so sounds you leave out are kept rather than removed.")
        if rep.skipped_clusters:
            notes.append(f"{rep.skipped_clusters} consonant cluster(s) in the sample are outside what the generator can build and were ignored.")
        usage = None
        if use_model:
            if self.llm is None:
                notes.append("No language model is connected, so only the sounds were analysed, not the grammar.")
            else:
                r = self.llm.complete(actor, "exemplar.analyze", prompt=X.grammar_prompt(texts), system=X.SYSTEM,
                                      conlang_id=conlang_id, max_tokens=1500)
                proposals += X.parse_grammar(r.text, spec)
                usage = {"input": r.usage.input_tokens, "output": r.usage.output_tokens}
        order = {"conflict": 0, "drift": 1}
        proposals.sort(key=lambda p: (order[p["kind"]], p["group"] != "sounds", p["key"]))
        return {"proposals": proposals, "summary": X.summary_of(rep), "notes": notes, "usage": usage}

    def create_from_sample(self, actor: Actor, raw_texts, *, name: str | None = None, seed: int, pins: dict | None = None,
                           use_model: bool = True) -> dict:
        """Make a new language shaped by sample text. Settings the user fixed (`pins`) always win; settings the sample
        implies are fixed to what it implies; everything else is chosen at random from the seed, as usual."""
        from .. import settings_schema as S
        from ..spec import sample_spec
        texts = X.clean_texts(raw_texts)
        pins = dict(pins or {})
        self.conlangs.precheck_create(actor)                          # before any paid model call
        base = sample_spec(seed, pins)
        res = self._read(actor, base, texts, use_model, fresh=True)
        inferred = [p for p in res["proposals"] if p["key"] not in pins]
        kept = [p for p in res["proposals"] if p["key"] in pins]       # the sample disagrees with a setting the user fixed
        notes = list(res["notes"])
        stages = [inferred, [p for p in inferred if p["source"] == "model"], []]    # if sounds cannot be built, fall back
        created, applied = None, []
        for n, chosen in enumerate(stages):
            try:
                merged = S.normalize({**{p["key"]: p["proposed"] for p in chosen}, **pins}, base)
                S.build_spec(seed, merged, {})
                created = self.conlangs.create(actor, name, seed=seed, pins=merged, extra={"exemplars": texts})
                applied = chosen
                break
            except ValidationFailed as e:
                if n == len(stages) - 1:
                    raise
                notes.append("Some sounds from the sample could not be combined into a full language (" + str(e)[:140] +
                             ") so they were left to chance.")
        return {**created, "shaped": {"applied": applied, "kept": kept, "notes": notes, "summary": res["summary"],
                                      "usage": res["usage"]}}

    def save(self, actor: Actor, conlang_id: str, raw_texts) -> list:
        """Remember the sample strings with the language (they survive rebuilds)."""
        texts = X.clean_texts(raw_texts) if raw_texts else []
        with self.db.read() as t:
            r = self.conlangs._row(t, conlang_id)
        require(actor, "conlang.edit", r["owner_id"])
        lang = json.loads(r["language_json"])
        lang["exemplars"] = texts
        with self.db.tx() as t:
            t.execute("UPDATE conlangs SET language_json = ? WHERE id = ?", (json.dumps(lang, ensure_ascii=False), conlang_id))
        return texts
