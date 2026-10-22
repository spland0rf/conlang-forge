"""Writing systems owned by a user, and their link to conlangs.

A writing system is stored as its recipe (seed + pinned dials), never as drawings: the generator is deterministic, so
the letters are rebuilt on demand. A system may be *designed for* a conlang: its letters then cover exactly that
language's consonants and vowels (and follow the language when its sounds change). Each conlang has one *primary*
system. Any of the owner's systems can write any of the owner's languages; sounds the system lacks use the closest
sound it has (see script/sounds.py)."""
from __future__ import annotations

import hashlib
import json
import secrets
import threading

from ..script import service as S
from ..script import text as T
from .clock import new_id
from .errors import NotFound, ValidationFailed
from .permissions import require

MAX_SCRIPTS = 60
SAMPLE_ENGLISH = ["The old man sees a big dog.", "We will go to the house.", "Where is the water?",
                  "The king has two sons.", "I do not like the night."]
FIELDS = "id, owner_id, conlang_id, name, seed, pins_json, created_at, updated_at, branched_from, preview_svg, preview_key"


class ScriptService:
    def __init__(self, db, clock, conlangs, translation, audit, llm=None):
        self.db, self.clock, self.conlangs, self.translation, self.audit = db, clock, conlangs, translation, audit
        self.llm = llm
        self._samples, self._lock = {}, threading.Lock()

    # ------------------------------------------------------------------ rows
    def _row(self, t, sid):
        r = t.one(f"SELECT {FIELDS} FROM writing_systems WHERE id = ? AND status = 'active'", (sid,))
        if r is None:
            raise NotFound("no such writing system")
        return r

    def _own(self, actor, sid, perm="script.manage"):
        with self.db.read() as t:
            r = self._row(t, sid)
        require(actor, perm, r["owner_id"])
        return r

    def _primary_of(self, t, cid):
        return t.scalar("SELECT primary_script_id FROM conlangs WHERE id = ?", (cid,))

    @staticmethod
    def _public_row(r, primary_ids=(), key=None):
        """`preview` is the stored line of sample text when it was drawn for this very recipe, else None (the client then asks for it)."""
        fresh = key is not None and r.get("preview_key") == key
        return {"id": r["id"], "name": r["name"], "seed": r["seed"], "pins": json.loads(r["pins_json"]),
                "conlang_id": r["conlang_id"], "conlang_name": r.get("conlang_name"),
                "primary": r["id"] in primary_ids, "updated_at": r["updated_at"], "preview": r.get("preview_svg") if fresh else None}

    @staticmethod
    def _recipe_key(seed, pins, phonemes) -> str:
        raw = json.dumps([seed, pins, S.clean_phonemes(phonemes)], sort_keys=True, ensure_ascii=False)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def _remember_line(self, sid, key, script):
        svg = S.preview_line(script)                       # drawn before the transaction opens, so it never holds the database
        with self.db.tx() as t:
            t.execute("UPDATE writing_systems SET preview_svg = ?, preview_key = ? WHERE id = ?", (svg, key, sid))
        return svg

    # ------------------------------------------------------------------ sounds of a language
    def sounds_of(self, actor, cid) -> dict:
        lang = self.conlangs.get_language(actor, cid)
        ph = lang["spec"]["phonology"]
        return {"consonants": list(ph["consonants"]), "vowels": list(ph["vowels"]),
                "romanization": lang["spec"]["orthography"]["romanization"], "name": lang["spec"].get("name")}

    def _live(self, actor, conlang_id):
        """The language a system was designed for, or None when it has since been deleted (the system then stands alone)."""
        if not conlang_id:
            return None
        try:
            self.conlangs.summary(actor, conlang_id)
        except NotFound:
            return None
        return conlang_id

    def _phonemes(self, actor, conlang_id):
        if not self._live(actor, conlang_id):
            return None
        s = self.sounds_of(actor, conlang_id)
        return {"consonants": s["consonants"], "vowels": s["vowels"]}

    # ------------------------------------------------------------------ list / create / edit / delete
    def list_own(self, actor) -> list:
        require(actor, "script.manage", actor.id)
        with self.db.read() as t:
            rows = t.all(f"SELECT {FIELDS} FROM writing_systems WHERE owner_id = ? AND status = 'active' "
                         "ORDER BY updated_at DESC, id", (actor.id,))
            langs = {r["id"]: r for r in t.all("SELECT id, name, primary_script_id FROM conlangs WHERE owner_id = ? "
                                               "AND status = 'active'", (actor.id,))}
        primary = {l["primary_script_id"] for l in langs.values() if l["primary_script_id"]}
        out = []
        for r in rows:
            r["conlang_name"] = langs.get(r["conlang_id"], {}).get("name")
            key = self._recipe_key(r["seed"], json.loads(r["pins_json"]), self._phonemes(actor, r["conlang_id"]))
            out.append(self._public_row(r, primary, key))
        return out

    def _validate(self, actor, name, seed, pins, conlang_id):
        if seed in (None, ""):
            seed = secrets.randbelow(2 ** 31)
        if not isinstance(pins or {}, dict):
            raise ValidationFailed("pins must be an object")
        try:
            pins = S.check(seed, pins)
        except ValueError as e:
            raise ValidationFailed(str(e)) from e
        if conlang_id:
            self.conlangs.summary(actor, conlang_id)                     # must exist and be readable
        name = (name or "").strip()
        if len(name) > 80:
            raise ValidationFailed("name must be at most 80 characters")
        return name, int(seed), pins

    def create(self, actor, *, name=None, seed=None, pins=None, conlang_id=None, primary=False) -> dict:
        require(actor, "script.manage", actor.id)
        name, seed, pins = self._validate(actor, name, seed, pins, conlang_id)
        with self.db.read() as t:
            have = t.scalar("SELECT COUNT(*) FROM writing_systems WHERE owner_id = ? AND status = 'active'", (actor.id,), 0)
        if have >= MAX_SCRIPTS:
            raise ValidationFailed(f"you can keep up to {MAX_SCRIPTS} writing systems; delete one first")
        name = name or (f"{self.sounds_of(actor, conlang_id)['name'] or 'Language'} script" if conlang_id else f"Writing system {have + 1}")
        sid, now = new_id(), self.clock.now_ms()
        with self.db.tx() as t:
            t.execute("INSERT INTO writing_systems (id, owner_id, conlang_id, name, seed, pins_json, status, created_at, updated_at) "
                      "VALUES (?,?,?,?,?,?,?,?,?)", (sid, actor.id, conlang_id, name, seed, json.dumps(pins, sort_keys=True), "active", now, now))
            if primary and conlang_id:
                t.execute("UPDATE conlangs SET primary_script_id = ? WHERE id = ?", (sid, conlang_id))
            self.audit.record(t, actor.id, "script.create", "writing_system", sid, seed=seed)
        return self.detail(actor, sid)

    def update(self, actor, sid, data: dict) -> dict:
        r = self._own(actor, sid)
        conlang_id = data["conlang_id"] if "conlang_id" in data else r["conlang_id"]
        name, seed, pins = self._validate(actor, data.get("name", r["name"]) or r["name"], data.get("seed", r["seed"]),
                                          data["pins"] if "pins" in data else json.loads(r["pins_json"]), conlang_id)
        with self.db.tx() as t:
            t.execute("UPDATE writing_systems SET name = ?, seed = ?, pins_json = ?, conlang_id = ?, updated_at = ? WHERE id = ?",
                      (name, seed, json.dumps(pins, sort_keys=True), conlang_id, self.clock.now_ms(), sid))
            if conlang_id != r["conlang_id"] and r["conlang_id"]:           # no longer designed for it: not its primary either
                t.execute("UPDATE conlangs SET primary_script_id = NULL WHERE id = ? AND primary_script_id = ?", (r["conlang_id"], sid))
            self.audit.record(t, actor.id, "script.edit", "writing_system", sid)
        return self.detail(actor, sid)

    def delete(self, actor, sid) -> None:
        self._own(actor, sid)
        with self.db.tx() as t:
            t.execute("UPDATE writing_systems SET status = 'deleted', updated_at = ? WHERE id = ?", (self.clock.now_ms(), sid))
            t.execute("UPDATE conlangs SET primary_script_id = NULL WHERE primary_script_id = ?", (sid,))
            t.execute("DELETE FROM versions WHERE kind = 'script' AND subject_id = ?", (sid,))
            self.audit.record(t, actor.id, "script.delete", "writing_system", sid)

    # ------------------------------------------------------------------ building
    def _generate(self, actor, seed, pins, conlang_id) -> dict:
        try:
            return S.generated(seed, json.dumps(pins, sort_keys=True), S.clean_phonemes(self._phonemes(actor, conlang_id)))
        except ValueError as e:
            raise ValidationFailed(str(e)) from e
        except Exception as e:      # a rare inventory the generator cannot draw distinct letters for
            raise ValidationFailed(f"could not draw a writing system from these settings ({str(e)[:140]}). Try another seed.") from e

    def _payload(self, actor, seed, pins, conlang_id, with_samples=True) -> dict:
        try:
            out = S.build(seed, pins, self._phonemes(actor, conlang_id))
        except ValueError as e:
            raise ValidationFailed(str(e)) from e
        except Exception as e:
            raise ValidationFailed(f"could not draw a writing system from these settings ({str(e)[:140]}). Try another seed.") from e
        if self._live(actor, conlang_id):
            snd = self.sounds_of(actor, conlang_id)
            out["language"] = {"id": conlang_id, "name": snd["name"], "exact": True}
            if with_samples:
                out["sentences"] = self.sample_sentences(actor, conlang_id, S.generated(
                    seed, json.dumps(pins, sort_keys=True), S.clean_phonemes(self._phonemes(actor, conlang_id))))
        return out

    def detail(self, actor, sid) -> dict:
        r = self._own(actor, sid)
        pins = json.loads(r["pins_json"])
        with self.db.read() as t:
            name = t.scalar("SELECT name FROM conlangs WHERE id = ?", (r["conlang_id"],)) if r["conlang_id"] else None
            primary = bool(r["conlang_id"]) and self._primary_of(t, r["conlang_id"]) == sid
        r = dict(r, conlang_name=name)
        live = self._live(actor, r["conlang_id"])
        out = self._payload(actor, r["seed"], pins, live)
        key = self._recipe_key(r["seed"], pins, self._phonemes(actor, live))
        if r.get("preview_key") != key:                       # drawn once per recipe, while the script is already generated
            r["preview_svg"], r["preview_key"] = self._remember_line(sid, key, self._generate(actor, r["seed"], pins, live)), key
        out["script_record"] = self._public_row(r, {sid} if primary else set(), key)
        return out

    def preview_line(self, actor, sid) -> dict:
        """The list's line of sample text for one system (drawn and stored when missing or out of date)."""
        r = self._own(actor, sid)
        pins = json.loads(r["pins_json"])
        live = self._live(actor, r["conlang_id"])
        key = self._recipe_key(r["seed"], pins, self._phonemes(actor, live))
        svg = r.get("preview_svg") if r.get("preview_key") == key else self._remember_line(sid, key, self._generate(actor, r["seed"], pins, live))
        return {"id": sid, "preview": svg}

    def preview(self, actor, seed=None, pins=None, conlang_id=None) -> dict:
        """Regenerate without saving: what the editor shows while the dials are being changed."""
        require(actor, "script.manage", actor.id)
        _, seed, pins = self._validate(actor, "", seed, pins, conlang_id)
        out = self._payload(actor, seed, pins, conlang_id)
        out["seed"] = seed
        return out

    # ------------------------------------------------------------------ design by description
    def interpret(self, actor, text, use_model: bool = True) -> dict:
        """Settings suggested by a description of the look ("lots of vertical lines, circles as marks ..."). Nothing is saved:
        the caller shows the proposals and the user applies the ones they want as pinned dials."""
        from ..script import describe as D
        require(actor, "script.manage", actor.id)
        text = D.clean(text)
        if len(text) < 3:
            raise ValidationFailed("describe how you would like the writing system to look")
        proposals, notes, usage = [], [], None
        if use_model and self.llm is not None:
            r = self.llm.complete(actor, "script.describe", prompt=D.prompt(text), system=D.SYSTEM, max_tokens=900)
            proposals, note = D.parse(r.text)
            usage = {"input": r.usage.input_tokens, "output": r.usage.output_tokens}
            if note:
                notes.append(note)
        if not proposals:
            proposals = D.keywords(text)
            notes.append("No language model is connected, so only common phrases were recognised." if self.llm is None else
                         "The model gave no usable settings, so common phrases were read instead." if use_model else
                         "Read by keywords (no model used).")
        if not proposals:
            notes.append("Nothing in the description matched a setting. Try naming lines (vertical, diagonal, round), "
                         "marks (dots, circles, ticks) or a style (spiky, curvy, bubbly, boxy).")
        return {"proposals": proposals, "notes": notes, "usage": usage}

    def interpret_image(self, actor, image, measures, use_model: bool = True) -> dict:
        """Settings suggested by a picture of letters the user likes. The browser sends a shrunken copy of the picture and
        numbers it measured from the pixels; the picture is shown to the model once and never stored or logged."""
        from ..script import describe as D
        from .llm.types import Message
        require(actor, "script.manage", actor.id)
        try:
            mt, data = D.check_image(image)
            m = D.clean_measures(measures)
        except ValueError as e:
            raise ValidationFailed(str(e)) from e
        notes, usage, proposals = [], None, []
        if use_model and self.llm is not None:
            r = self.llm.complete(actor, "script.describe_image", messages=[Message("user", D.image_prompt(m), ((mt, data),))],
                                  system=D.IMAGE_SYSTEM, max_tokens=900)
            proposals, note = D.parse(r.text)
            usage = {"input": r.usage.input_tokens, "output": r.usage.output_tokens}
            if note:
                notes.append(note)
        elif use_model:
            notes.append("No language model is connected, so only the measurements of the picture were used.")
        have = {p["key"] for p in proposals}
        proposals += [p for p in D.measure_proposals(m) if p["key"] not in have]
        if use_model and self.llm is not None and not have:
            notes.append("The model gave no usable settings, so the measurements of the picture were used.")
        if not proposals:
            notes.append("Nothing clear came out of this picture. A cleaner sample of several letters on a plain background works best.")
        notes.append("The letters themselves are not copied: the picture only steers the style settings.")
        return {"proposals": proposals, "notes": notes, "usage": usage}

    # ------------------------------------------------------------------ language side
    def scripts_for(self, actor, cid) -> dict:
        self.conlangs.summary(actor, cid)
        with self.db.read() as t:
            pid = self._primary_of(t, cid)
        return {"primary_id": pid, "scripts": self.list_own(actor)}

    def ensure_primary(self, actor, cid) -> dict:
        """The conlang's primary writing system: made from the language's own seed the first time it is asked for."""
        summary = self.conlangs.summary(actor, cid)
        with self.db.read() as t:
            pid = self._primary_of(t, cid)
            ok = pid and t.one("SELECT id FROM writing_systems WHERE id = ? AND status = 'active'", (pid,))
            mine = t.one("SELECT id FROM writing_systems WHERE conlang_id = ? AND owner_id = ? AND status = 'active' "
                         "ORDER BY created_at LIMIT 1", (cid, actor.id))
        if ok:
            return self.detail(actor, pid)
        if mine:
            self.set_primary(actor, cid, mine["id"])
            return self.detail(actor, mine["id"])
        return self.create(actor, name=f"{summary['name']} script", seed=summary["seed"] or None, conlang_id=cid, primary=True)

    def set_primary(self, actor, cid, sid) -> dict:
        require(actor, "conlang.edit", self.conlangs.summary(actor, cid)["owner_id"])
        r = self._own(actor, sid)
        if r["conlang_id"] != cid:
            raise ValidationFailed("the primary writing system must be one designed for this language; "
                                   "edit it and choose this language under 'Designed for' first")
        with self.db.tx() as t:
            t.execute("UPDATE conlangs SET primary_script_id = ? WHERE id = ?", (sid, cid))
            self.audit.record(t, actor.id, "script.primary", "conlang", cid, script=sid)
        return self.detail(actor, sid)

    def sample_sentences(self, actor, cid, script) -> list:
        """A few plain sentences in the language, written in `script` (free: the restricted-English translator, no model)."""
        summary = self.conlangs.summary(actor, cid)
        key = (cid, summary["updated_at"])
        with self._lock:
            lines = self._samples.get(key)
        if lines is None:
            lines = []
            for en in SAMPLE_ENGLISH:
                try:
                    res = self.translation.to_language(actor, cid, en, mode="restricted")
                except Exception:
                    continue
                if res["text"].strip():
                    lines.append({"english": en, "text": res["text"]})
            with self._lock:
                if len(self._samples) > 64:
                    self._samples.clear()
                self._samples[key] = lines
        snd = self.sounds_of(actor, cid)
        out = []
        from ..plain import own_fold
        for ln in lines:
            r = T.render_text(script, ln["text"], snd["romanization"], own_fold(snd["romanization"]))
            out.append({**ln, "svg": r["sentences"][0]["svg"] if r["sentences"] else ""})
        return out

    def render(self, actor, cid, text, script_id=None) -> dict:
        """Write `text` (in the language's own spelling) in a writing system: the primary one unless another is chosen."""
        if not isinstance(text, str) or not text.strip():
            raise ValidationFailed("enter some text to write")
        if len(text) > 4000:
            raise ValidationFailed("text is too long (4,000 characters at most)")
        summary = self.conlangs.summary(actor, cid)
        if script_id is None:
            with self.db.read() as t:
                script_id = self._primary_of(t, cid)
            if not script_id:
                script_id = self.ensure_primary(actor, cid)["script_record"]["id"]
        r = self._own(actor, script_id)
        pins = json.loads(r["pins_json"])
        script = self._generate(actor, r["seed"], pins, self._live(actor, r["conlang_id"]))
        snd = self.sounds_of(actor, cid)
        from ..plain import own_fold
        res = T.render_text(script, text, snd["romanization"], own_fold(snd["romanization"]))
        with self.db.read() as t:
            primary = self._primary_of(t, cid) == script_id
        return {"script_id": script_id, "script_name": r["name"], "primary": primary, "language": summary["name"],
                "designed_for_this": r["conlang_id"] == cid, **res,
                "coverage": T.coverage(script, snd["consonants"], snd["vowels"])}
