"""Checkpoints of a language or a writing system.

Nothing is saved automatically. The owner presses "Create checkpoint" and the item's current state is stored, read only,
as the next numbered version; the item itself stays as the editable working version (one number higher). Older
versions are never edited: "New version from this one" makes a separate, editable copy that starts identical to it.

A checkpoint is a snapshot, not a recipe. The generators are deterministic for one release of the code, but rules
change between releases, so a recipe could redraw differently years later. Snapshots are compressed (lzma) and kept as
base85 text so the same table works on SQLite and PostgreSQL: about 3.5 KB for a writing system and 80 KB for a language.
"""
from __future__ import annotations

import base64
import hashlib
import json
import lzma

from .clock import new_id
from .errors import Conflict, NotFound, ValidationFailed
from .permissions import require

MAX_PER_ITEM = 50
MAX_BYTES_PER_USER = 100 * 1024 * 1024


def pack(obj) -> tuple:
    """(digest of the canonical JSON, its size, compressed text)."""
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), len(raw), base64.b85encode(lzma.compress(raw, preset=6)).decode("ascii")


def unpack(text: str):
    return json.loads(lzma.decompress(base64.b85decode(text.encode("ascii"))).decode("utf-8"))


class VersionService:
    def __init__(self, db, clock, conlangs, scripts, audit):
        self.db, self.clock, self.conlangs, self.scripts, self.audit = db, clock, conlangs, scripts, audit

    # ------------------------------------------------------------------ the two kinds of item
    def _subject(self, actor, kind, sid, write=False):
        """The item's row, after the permission check."""
        if kind == "conlang":
            return self.conlangs._load(actor, sid, "conlang.edit" if write else "conlang.read")
        return self.scripts._own(actor, sid)

    def _capture(self, actor, kind, sid) -> dict:
        if kind == "conlang":
            return self.conlangs.snapshot(actor, sid)
        r = self.scripts._own(actor, sid)
        live = self.scripts._live(actor, r["conlang_id"])
        phon = self.scripts._phonemes(actor, live) if live else None
        pins = json.loads(r["pins_json"])
        script = self.scripts._generate(actor, r["seed"], pins, live)
        return {"name": r["name"], "seed": r["seed"], "pins": pins, "conlang_id": live, "phonemes": phon, "script": script}

    # ------------------------------------------------------------------ list / create / delete
    def _rows(self, t, kind, sid):
        return t.all("SELECT id, n, label, digest, raw_bytes, LENGTH(packed) AS stored, created_at FROM versions "
                     "WHERE kind = ? AND subject_id = ? ORDER BY n DESC", (kind, sid))

    def list(self, actor, kind, sid) -> dict:
        r = self._subject(actor, kind, sid)
        with self.db.read() as t:
            rows = self._rows(t, kind, sid)
        top = rows[0]["n"] if rows else 0
        origin = None
        try:
            origin = json.loads(r["branched_from"]) if r.get("branched_from") else None
        except ValueError:
            pass
        return {"working": top + 1, "has_checkpoints": bool(rows), "branched_from": origin,
                "versions": [{"id": x["id"], "n": x["n"], "label": x["label"], "created_at": x["created_at"],
                              "stored_bytes": x["stored"], "raw_bytes": x["raw_bytes"]} for x in rows],
                "max_per_item": MAX_PER_ITEM}

    def create(self, actor, kind, sid, label: str = "") -> dict:
        """Store the current state as the next read-only version. Only ever called because the user asked for it."""
        r = self._subject(actor, kind, sid, write=True)
        label = (label or "").strip()
        if len(label) > 80:
            raise ValidationFailed("a checkpoint note can be at most 80 characters")
        snap = self._capture(actor, kind, sid)
        digest, raw_bytes, packed = pack(snap)                    # CPU work, outside any transaction
        with self.db.tx() as t:
            rows = self._rows(t, kind, sid)
            if rows and rows[0]["digest"] == digest:
                raise Conflict(f"Nothing has changed since version {rows[0]['n']}, so there is nothing new to keep.")
            if len(rows) >= MAX_PER_ITEM:
                raise ValidationFailed(f"you can keep up to {MAX_PER_ITEM} checkpoints of one item; delete an old one first")
            used = t.scalar("SELECT COALESCE(SUM(LENGTH(packed)), 0) FROM versions WHERE owner_id = ?", (actor.id,), 0)
            if used + len(packed) > MAX_BYTES_PER_USER:
                raise ValidationFailed("your saved checkpoints take up the most space allowed; delete some you no longer need")
            n = (rows[0]["n"] if rows else 0) + 1
            vid = new_id()
            t.execute("INSERT INTO versions (id, kind, subject_id, owner_id, n, label, digest, raw_bytes, packed, created_at) "
                      "VALUES (?,?,?,?,?,?,?,?,?,?)", (vid, kind, sid, r["owner_id"], n, label, digest, raw_bytes, packed, self.clock.now_ms()))
            self.audit.record(t, actor.id, f"{kind}.checkpoint", kind, sid, n=n)
        return self.list(actor, kind, sid)

    def _load(self, actor, kind, sid, n, write=False):
        self._subject(actor, kind, sid, write=write)
        with self.db.read() as t:
            v = t.one("SELECT * FROM versions WHERE kind = ? AND subject_id = ? AND n = ?", (kind, sid, int(n)))
        if v is None:
            raise NotFound("no such version")
        return v

    def delete(self, actor, kind, sid, n) -> dict:
        v = self._load(actor, kind, sid, n, write=True)
        with self.db.tx() as t:
            t.execute("DELETE FROM versions WHERE id = ?", (v["id"],))
            self.audit.record(t, actor.id, f"{kind}.checkpoint_delete", kind, sid, n=v["n"])
        return self.list(actor, kind, sid)

    # ------------------------------------------------------------------ reading an old version
    def detail(self, actor, kind, sid, n) -> dict:
        v = self._load(actor, kind, sid, n)
        snap = unpack(v["packed"])
        head = {"n": v["n"], "label": v["label"], "created_at": v["created_at"], "read_only": True, "kind": kind}
        if kind == "conlang":
            return {**head, **self._language_detail(actor, sid, snap)}
        return {**head, **self._script_detail(actor, sid, snap)}

    def _language_detail(self, actor, sid, snap) -> dict:
        from .. import settings_schema as S
        from ..spec import LanguageSpec
        lang = snap["language"]
        old = LanguageSpec.from_dict(lang["spec"])
        try:
            changes = S.diff(old, self.conlangs.current_spec(actor, sid))      # what the working version changed since
        except Exception:
            changes = []
        ph = lang["spec"].get("phonology", {})
        lex = lang.get("lexicon") or []
        return {"name": snap["name"], "seed": snap["seed"], "vocab_version": snap["vocab_version"], "words": len(lex),
                "consonants": list(ph.get("consonants", [])), "vowels": list(ph.get("vowels", [])),
                "typology": lang["spec"].get("morphology", {}).get("typology"),
                "word_order": lang["spec"].get("syntax", {}).get("word_order"),
                "changes_since": [{"label": c["label"], "then": c["before"], "now": c["after"]} for c in changes]}

    def _script_detail(self, actor, sid, snap) -> dict:
        from ..script import service as SS
        from ..script.layout import sample_words
        from ..script.render import sheet_svg, text_svg
        script = snap["script"]
        labels = {d["key"]: d["label"] for d in SS.describe_dials()["dials"]}
        now = self.scripts._own(actor, sid)
        now_pins = json.loads(now["pins_json"])
        changes = []
        if snap["seed"] != now["seed"]:
            changes.append({"label": "Seed", "then": snap["seed"], "now": now["seed"]})
        for k in sorted(set(snap["pins"]) | set(now_pins)):
            if snap["pins"].get(k) != now_pins.get(k):
                changes.append({"label": labels.get(k, k), "then": snap["pins"].get(k, "random"), "now": now_pins.get(k, "random")})
        if snap["name"] != now["name"]:
            changes.append({"label": "Name", "then": snap["name"], "now": now["name"]})
        sentences = []
        if snap.get("conlang_id"):
            try:
                if self.scripts._live(actor, snap["conlang_id"]):
                    sentences = self.scripts.sample_sentences(actor, snap["conlang_id"], script)
            except Exception:
                sentences = []
        return {"name": snap["name"], "seed": snap["seed"], "pins": snap["pins"], "conlang_id": snap.get("conlang_id"),
                "spec": script["spec"], "metrics": script.get("metrics"),
                "specimen": sheet_svg(script), "sample": text_svg(script, sample_words(script, 5, "preview")),
                "sentences": sentences, "changes_since": changes}

    # ------------------------------------------------------------------ a new editable item from an old version
    def branch(self, actor, kind, sid, n, name: str = "") -> dict:
        v = self._load(actor, kind, sid, n)
        snap = unpack(v["packed"])
        name = (name or "").strip()[:80] or f"{snap['name']} (from v{v['n']})"[:80]
        origin = {"kind": kind, "id": sid, "name": snap["name"], "n": v["n"]}
        if kind == "conlang":
            return {"kind": "conlang", "item": self.conlangs.create_from_snapshot(actor, snap, name, origin)}
        live = self.scripts._live(actor, snap.get("conlang_id"))
        item = self.scripts.create(actor, name=name, seed=snap["seed"], pins=snap["pins"], conlang_id=live)
        # The recipe is redrawn by today's generator; say so when that no longer matches the stored drawing.
        script_now = self.scripts._generate(actor, snap["seed"], snap["pins"], live)
        exact = pack(script_now)[0] == pack(snap["script"])[0]
        with self.db.tx() as t:
            t.execute("UPDATE writing_systems SET branched_from = ? WHERE id = ?", (json.dumps(origin), item["script_record"]["id"]))
        return {"kind": "script", "item": item, "exact": exact}
