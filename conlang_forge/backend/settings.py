"""System settings stored in the database (admin-editable, audited)."""
from __future__ import annotations

import json

from .permissions import Actor, require

DEFAULTS = {
    "registration.open": True,
    "llm.enabled": True,                      # kill switch for every model call
    "llm.global_tokens_per_day": None,        # None = no global cap
    "llm.store_previews": False,              # keep short prompt/response previews in the call log
    "llm.prices": {},                         # model -> {"in": usd per M tokens, "out": ..., "cache_write": ..., "cache_read": ...}
}


class Settings:
    def __init__(self, db, clock, audit):
        self.db, self.clock, self.audit = db, clock, audit

    def get(self, key, default=None):
        with self.db.read() as t:
            row = t.one("SELECT value_json FROM settings WHERE key = ?", (key,))
        if row is None:
            return DEFAULTS.get(key, default)
        return json.loads(row["value_json"])

    def set(self, actor: Actor, key: str, value) -> None:
        require(actor, "settings.manage")
        if key not in DEFAULTS:
            from .errors import ValidationFailed
            raise ValidationFailed(f"unknown setting {key}")
        with self.db.tx() as t:
            t.execute("INSERT INTO settings (key, value_json, updated_by, updated_at) VALUES (?,?,?,?) "
                      "ON CONFLICT (key) DO UPDATE SET value_json = excluded.value_json, "
                      "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
                      (key, json.dumps(value), actor.id, self.clock.now_ms()))
            self.audit.record(t, actor.id, "settings.set", "setting", key, value=value)

    def all(self) -> dict:
        out = dict(DEFAULTS)
        with self.db.read() as t:
            for r in t.all("SELECT key, value_json FROM settings"):
                out[r["key"]] = json.loads(r["value_json"])
        return out
