"""Audit log of administrative and security-relevant actions."""
from __future__ import annotations

import json

from .clock import Clock, new_id


class Audit:
    def __init__(self, db, clock: Clock):
        self.db, self.clock = db, clock

    def record(self, t, actor_id, action, target_type=None, target_id=None, **detail):
        """Write inside the caller's transaction `t`, so the log and the change commit together."""
        t.execute("INSERT INTO audit_log (id, actor_id, action, target_type, target_id, detail_json, created_at) "
                  "VALUES (?,?,?,?,?,?,?)",
                  (new_id(), actor_id, action, target_type, target_id, json.dumps(detail, default=str),
                   self.clock.now_ms()))

    def list(self, *, action=None, target_id=None, actor_id=None, before=None, limit=100):
        q, p = "SELECT * FROM audit_log WHERE 1=1", []
        for col, v in (("action", action), ("target_id", target_id), ("actor_id", actor_id)):
            if v:
                q += f" AND {col} = ?"
                p.append(v)
        if before:
            q += " AND created_at < ?"
            p.append(before)
        q += " ORDER BY created_at DESC, id LIMIT ?"
        p.append(min(int(limit), 500))
        with self.db.read() as t:
            rows = t.all(q, p)
        for r in rows:
            r["detail"] = json.loads(r.pop("detail_json") or "{}")
        return rows
