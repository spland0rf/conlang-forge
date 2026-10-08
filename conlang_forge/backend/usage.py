"""Usage reports for the admin graphs and for each user's own meter.

All queries read the llm_calls log. Group-by and bucket choices are checked against fixed lists, never pasted
into SQL from user input. Buckets are integer divisions of the timestamp, which both SQLite and PostgreSQL do.
"""
from __future__ import annotations

from .clock import DAY_MS, HOUR_MS, MINUTE_MS, Clock
from .errors import ValidationFailed
from .permissions import Actor, require

BUCKETS = {"hour": HOUR_MS, "day": DAY_MS, "week": 7 * DAY_MS, "15min": 15 * MINUTE_MS}
GROUPS = {"purpose": "purpose", "model": "model", "user": "user_id", "status": "status", "none": "'all'"}
METRICS = ("calls", "errors", "denied", "input_tokens", "output_tokens", "quota_tokens", "cost_micro_usd")
SUMS = ("COUNT(*) AS calls, "
        "SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS errors, "
        "SUM(CASE WHEN status = 'denied' THEN 1 ELSE 0 END) AS denied, "
        "COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens, "
        "COALESCE(SUM(quota_tokens),0) AS quota_tokens, COALESCE(SUM(cost_micro_usd),0) AS cost_micro_usd")


class UsageReports:
    def __init__(self, db, clock: Clock, limits, quota, accounts):
        self.db, self.clock, self.limits, self.quota, self.accounts = db, clock, limits, quota, accounts

    # ---- a user's own meter
    def my_usage(self, actor: Actor) -> dict:
        require(actor, "usage.read", actor.id)
        user = self.accounts.get(actor.id)
        lim = self.limits.resolve(user)
        snap = self.quota.snapshot(actor.id, lim)
        snap["limits"] = lim.to_dict()
        return snap

    # ---- admin: graphs
    def timeseries(self, actor: Actor, *, start_ms: int, end_ms: int, bucket: str = "day", group_by: str = "none",
                   user_id: str | None = None, purpose: str | None = None, include_denied: bool = False) -> dict:
        """Rows of {bucket_start, group, calls, errors, ..., cost_micro_usd}, oldest first. Missing buckets are absent
        (the chart fills zeros)."""
        self._admin(actor, user_id)
        if bucket not in BUCKETS or group_by not in GROUPS:
            raise ValidationFailed("bad bucket or group_by")
        if end_ms <= start_ms or (end_ms - start_ms) // BUCKETS[bucket] > 2000:
            raise ValidationFailed("time range is empty or has too many buckets")
        size, g = BUCKETS[bucket], GROUPS[group_by]
        q = (f"SELECT (created_at / {size}) * {size} AS bucket_start, {g} AS grp, {SUMS} FROM llm_calls "
             "WHERE created_at >= ? AND created_at < ?")
        p = [start_ms, end_ms]
        if not include_denied:
            q += " AND status <> 'denied'"
        for col, v in (("user_id", user_id), ("purpose", purpose)):
            if v:
                q += f" AND {col} = ?"
                p.append(v)
        q += " GROUP BY bucket_start, grp ORDER BY bucket_start, grp"
        with self.db.read() as t:
            rows = t.all(q, p)
        return {"bucket": bucket, "bucket_ms": size, "start_ms": start_ms, "end_ms": end_ms, "group_by": group_by,
                "rows": rows}

    def totals(self, actor: Actor, *, start_ms: int, end_ms: int, user_id: str | None = None) -> dict:
        self._admin(actor, user_id)
        q, p = f"SELECT {SUMS} FROM llm_calls WHERE created_at >= ? AND created_at < ?", [start_ms, end_ms]
        if user_id:
            q += " AND user_id = ?"
            p.append(user_id)
        with self.db.read() as t:
            return t.one(q, p)

    def top_users(self, actor: Actor, *, start_ms: int, end_ms: int, metric: str = "quota_tokens", limit: int = 10):
        self._admin(actor, None)
        if metric not in METRICS:
            raise ValidationFailed("bad metric")
        with self.db.read() as t:
            rows = t.all(f"SELECT x.*, u.email, u.display_name, u.plan FROM "
                         f"(SELECT user_id, {SUMS} FROM llm_calls WHERE created_at >= ? AND created_at < ? "
                         f"GROUP BY user_id) x LEFT JOIN users u ON u.id = x.user_id "
                         f"ORDER BY x.{metric} DESC, x.user_id LIMIT ?", (start_ms, end_ms, min(limit, 100)))
        return rows

    def recent_calls(self, actor: Actor, *, user_id: str | None = None, status: str | None = None,
                     purpose: str | None = None, before_ms: int | None = None, limit: int = 50) -> list:
        self._admin(actor, user_id)
        q, p = "SELECT * FROM llm_calls WHERE 1=1", []
        for col, v in (("user_id", user_id), ("status", status), ("purpose", purpose)):
            if v:
                q += f" AND {col} = ?"
                p.append(v)
        if before_ms:
            q += " AND created_at < ?"
            p.append(before_ms)
        q += " ORDER BY created_at DESC, id LIMIT ?"
        p.append(min(limit, 200))
        with self.db.read() as t:
            return t.all(q, p)

    def _admin(self, actor, user_id):
        # an administrator sees everything; a normal user may only ask about themselves
        if user_id is not None and user_id == actor.id:
            require(actor, "usage.read", actor.id)
        else:
            require(actor, "usage.read")
