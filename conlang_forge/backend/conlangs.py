"""A user's conlangs: ownership, per-plan limits, and the bridge to the generator engine."""
from __future__ import annotations

import json

from .clock import Clock, new_id
from .errors import Conflict, NotFound, QuotaExceeded, ValidationFailed
from .permissions import Actor, require

LIST_FIELDS = "id, owner_id, name, seed, vocab_version, status, created_at, updated_at"
LIST_SQL = LIST_FIELDS + ", spec_json"


def engine_generator(data_dir, vocab_version: str = "1.2"):
    """Returns generate(seed, pins) -> (spec_dict, language_dict) using the deterministic engine."""
    from pathlib import Path

    from ..frequency import load_freq
    from ..rootgen import build_language, verify
    from ..roots import load_rootmap
    from ..spec import sample_spec
    from ..vocab import load_vocab
    root = Path(data_dir)
    cache = {}

    def load():
        if not cache:
            cache.update(vocab=load_vocab(root / f"vocab/v{vocab_version}.json"),
                         rm=load_rootmap(root / f"roots/v{vocab_version}.rootmap.json"),
                         freq=load_freq(root / f"vocab/v{vocab_version}.freq.json"))
        return cache

    def generate(seed: int, pins: dict, tuning: dict | None = None, spec=None):
        c = load()
        spec = spec or sample_spec(seed, pins or {}, tuning or None)
        state, rep = build_language(spec, c["vocab"], c["rm"], c["freq"])
        lang = {"format": "conlang-forge-language/2", "vocab_version": c["vocab"]["version"], "spec": spec.to_dict(),
                "table": state["table"], "stems": state["stems"], "stem_budget": state["stem_budget"],
                "lexicon": state["entries"], "plan": state["plan"], "quality": verify(spec, c["rm"], state),
                "history": [{"vocab_version": c["vocab"]["version"], "added": len(rep["added"]), "retired": 0}]}
        return spec.to_dict(), lang
    return generate


class ConlangService:
    def __init__(self, db, clock: Clock, accounts, limits, audit, generator=None):
        self.db, self.clock, self.accounts, self.limits, self.audit = db, clock, accounts, limits, audit
        self.generator = generator

    def _row(self, t, conlang_id):
        r = t.one("SELECT * FROM conlangs WHERE id = ? AND status <> 'deleted'", (conlang_id,))
        if r is None:
            raise NotFound("no such conlang")
        return r

    def create(self, actor: Actor, name: str | None, *, seed: int, pins: dict | None = None, tuning: dict | None = None,
               extra: dict | None = None) -> dict:
        """`name` may be blank: the language then keeps the name the generator invented for it."""
        name = (name or "").strip()
        if len(name) > 80:
            raise ValidationFailed("name must be at most 80 characters")
        self.precheck_create(actor)
        if tuning:
            spec, lang = self.generator(seed, pins or {}, tuning)
        else:
            spec, lang = self.generator(seed, pins or {})   # CPU work, outside any database transaction
        if extra:
            lang.update(extra)
        name = name or spec.get("name") or f"Language {seed}"
        cid, now = new_id(), self.clock.now_ms()
        with self.db.tx() as t:
            t.execute("INSERT INTO conlangs (id, owner_id, name, seed, vocab_version, status, spec_json, language_json, "
                      "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (cid, actor.id, name, seed, lang["vocab_version"], "active", json.dumps(spec),
                       json.dumps(lang, ensure_ascii=False), now, now))
            self.audit.record(t, actor.id, "conlang.create", "conlang", cid, seed=seed)
        return self.summary(actor, cid)

    def precheck_create(self, actor: Actor) -> None:
        """Permission, generator and plan limit. Called before any paid work (such as reading a sample with the model)."""
        require(actor, "conlang.create", actor.id)
        if self.generator is None:
            raise ValidationFailed("no generator configured")
        user = self.accounts.get(actor.id)
        cap = self.limits.resolve(user).max_conlangs
        with self.db.read() as t:
            have = t.scalar("SELECT COUNT(*) FROM conlangs WHERE owner_id = ? AND status = 'active'", (actor.id,), 0)
        if cap is not None and have >= cap:
            raise QuotaExceeded(f"your plan allows {cap} conlangs; delete one or ask for more",
                                scope="max_conlangs", limit=cap, used=have)

    def summary(self, actor: Actor, conlang_id: str) -> dict:
        with self.db.read() as t:
            r = self._row(t, conlang_id)
        require(actor, "conlang.read", r["owner_id"])
        return {k: r[k] for k in LIST_FIELDS.split(", ")}

    def get_language(self, actor: Actor, conlang_id: str, script: str = "plain") -> dict:
        with self.db.read() as t:
            r = self._row(t, conlang_id)
        require(actor, "conlang.read", r["owner_id"])
        lang = json.loads(r["language_json"])
        from ..plain import respell
        respell(lang)                      # languages saved with accented letters are shown in plain letters
        if script not in (None, "", "plain"):
            from ..plain import with_script
            try:
                lang = with_script(lang, script)
            except ValueError as e:
                raise ValidationFailed(str(e)) from e
        return lang

    def list_own(self, actor: Actor, *, limit: int = 50, offset: int = 0) -> list:
        require(actor, "conlang.read", actor.id)
        with self.db.read() as t:
            rows = t.all(f"SELECT {LIST_SQL} FROM conlangs WHERE owner_id = ? AND status = 'active' "
                         "ORDER BY updated_at DESC, id LIMIT ? OFFSET ?", (actor.id, min(limit, 200), offset))
        for r in rows:
            try:
                spec = json.loads(r.pop("spec_json") or "{}")
                r["typology"] = spec.get("morphology", {}).get("typology")
                r["word_order"] = spec.get("syntax", {}).get("word_order")
            except ValueError:
                r["typology"] = r["word_order"] = None
        return rows

    def list_all(self, actor: Actor, *, owner_id: str | None = None, limit: int = 50, offset: int = 0) -> list:
        """Administrators browse any user's conlangs (read only)."""
        require(actor, "conlang.read")
        q, p = f"SELECT c.id, c.owner_id, u.email AS owner_email, c.name, c.seed, c.status, c.created_at, c.updated_at " \
               "FROM conlangs c JOIN users u ON u.id = c.owner_id WHERE c.status = 'active'", []
        if owner_id:
            q += " AND c.owner_id = ?"
            p.append(owner_id)
        with self.db.read() as t:
            return t.all(q + " ORDER BY c.updated_at DESC, c.id LIMIT ? OFFSET ?", p + [min(limit, 200), offset])

    def rename(self, actor: Actor, conlang_id: str, name: str) -> dict:
        with self.db.read() as t:
            r = self._row(t, conlang_id)
        require(actor, "conlang.edit", r["owner_id"])
        if not name.strip() or len(name) > 80:
            raise ValidationFailed("name must be 1-80 characters")
        with self.db.tx() as t:
            t.execute("UPDATE conlangs SET name = ?, updated_at = ? WHERE id = ?", (name.strip(), self.clock.now_ms(), conlang_id))
        return self.summary(actor, conlang_id)

    def delete(self, actor: Actor, conlang_id: str) -> None:
        with self.db.read() as t:
            r = self._row(t, conlang_id)
        require(actor, "conlang.delete", r["owner_id"])
        with self.db.tx() as t:
            t.execute("UPDATE conlangs SET status = 'deleted', updated_at = ? WHERE id = ?", (self.clock.now_ms(), conlang_id))
            self.audit.record(t, actor.id, "conlang.delete", "conlang", conlang_id)

    # ------------------------------------------------------------------ settings editor
    def _load(self, actor, conlang_id, perm="conlang.read"):
        with self.db.read() as t:
            r = self._row(t, conlang_id)
        require(actor, perm, r["owner_id"])
        return r

    def current_spec(self, actor: Actor, conlang_id: str):
        from ..spec import LanguageSpec
        lang = self.get_language(actor, conlang_id)
        return LanguageSpec.from_dict(lang["spec"])

    def settings(self, actor: Actor, conlang_id: str) -> dict:
        from .. import settings_schema as S
        d = S.describe(self.current_spec(actor, conlang_id))
        d["exemplars"] = self.get_language(actor, conlang_id).get("exemplars", [])
        return d

    def _edited(self, spec, set_, unpin, tuning):
        """(new pins, new tuning, new spec) after applying an edit to the language's current settings."""
        from .. import settings_schema as S
        pins = S.pins_of(spec)
        for k in unpin or []:
            if k not in S.SPEC_KEYS:
                raise ValidationFailed(f"unknown setting {k}")
            pins.pop(k, None)
        chosen = set_ or {}
        # asking for a count (instead of an exact list) frees the list and its shares; the generator picks again
        for cnt, lst, extra in (("phonology.consonant_count", "phonology.consonants", ["phonology.consonant_weights"]),
                                ("phonology.vowel_count", "phonology.vowels", ["phonology.vowel_weights"]),
                                ("phonology.complex_count", "phonology.complex_consonants", ["phonology.consonant_weights"])):
            if cnt in chosen and lst not in chosen:
                for k in [lst] + [e for e in extra if e not in chosen]:
                    pins.pop(k, None)
        pins.update(S.normalize(chosen, spec))
        # a pinned inventory with leftover shares/clusters from before: bring them in line
        pins = S.normalize(pins, spec)
        new_tuning = S.clean_tuning(tuning) if tuning is not None else (spec.tuning or {})
        return pins, new_tuning, S.build_spec(spec.seed, pins, new_tuning)

    def preview_settings(self, actor: Actor, conlang_id: str, *, set=None, unpin=None, tuning=None) -> dict:
        """What an edit would change, without building the vocabulary (cheap)."""
        from .. import settings_schema as S
        spec = self.current_spec(actor, conlang_id)
        _, _, new = self._edited(spec, set, unpin, tuning)
        return {"changes": S.diff(spec, new), "same": spec.to_dict() == new.to_dict()}

    def apply_settings(self, actor: Actor, conlang_id: str, *, set=None, unpin=None, tuning=None, mode: str = "replace") -> dict:
        """Rebuild the language from edited settings, in place or as a new copy. Words are regenerated by the rules;
        no word is edited by hand here."""
        from .. import settings_schema as S
        r = self._load(actor, conlang_id, "conlang.edit")
        old = json.loads(r["language_json"])
        from ..plain import respell
        respell(old)
        from ..spec import LanguageSpec
        spec = LanguageSpec.from_dict(old["spec"])
        pins, new_tuning, new = self._edited(spec, set, unpin, tuning)
        keep = {k: old[k] for k in ("exemplars",) if k in old}
        if mode == "copy":
            name = (set or {}).get("name") or f"{r['name']} (copy)"
            pins = {k: v for k, v in pins.items() if k != "name"}
            return self.create(actor, name[:80], seed=spec.seed, pins=pins, tuning=new_tuning, extra=keep)
        if mode != "replace":
            raise ValidationFailed("mode must be replace or copy")
        try:
            spec_d, lang = self.generator(spec.seed, pins, new_tuning, new)
        except Exception as e:          # the generator could not make enough distinct words from these settings
            raise ValidationFailed("The generator could not build a full vocabulary from these settings "
                                   f"({str(e)[:160]}). Try allowing more sounds or syllable shapes.") from e
        lang.update(keep)
        now = self.clock.now_ms()
        new_name = spec_d.get("name") or r["name"]
        with self.db.tx() as t:
            t.execute("UPDATE conlangs SET name = ?, spec_json = ?, language_json = ?, vocab_version = ?, updated_at = ? "
                      "WHERE id = ?", (new_name[:80], json.dumps(spec_d), json.dumps(lang, ensure_ascii=False),
                                       lang["vocab_version"], now, conlang_id))
            self.audit.record(t, actor.id, "conlang.settings", "conlang", conlang_id)
        return self.summary(actor, conlang_id)
