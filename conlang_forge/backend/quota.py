"""Token quotas, request-rate limits and the global spending cap.

How a model call is paid for:

1. `reserve` sets aside an estimate (prompt estimate + the output cap) in one database transaction. The checks
   and the counter updates are single conditional UPDATE statements, so two simultaneous calls from the same
   user can never both squeeze into the last of the allowance.
2. When the provider answers, `settle` replaces the estimate with the real token count.
3. If the call fails, `release` gives the estimate back.

A reservation row is stored for each open reservation, so one left behind by a crash can be released by `reap`.
Counters: per user per day, per user per month, per user per minute (requests), and a global row per day.
"""
from __future__ import annotations

from dataclasses import dataclass

from .clock import MINUTE_MS, Clock, day_key, month_key, new_id, next_day_start, next_month_start
from .errors import QuotaExceeded, RateLimited
from .limits import Limits

GLOBAL = "*"


@dataclass(frozen=True)
class Reservation:
    id: str
    user_id: str
    amount: int
    day_key: str
    month_key: str


class QuotaService:
    def __init__(self, db, clock: Clock):
        self.db, self.clock = db, clock

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ensure(t, user_id, kind, key):
        t.execute("INSERT INTO quota_counters (user_id, period_kind, period_key) VALUES (?,?,?) "
                  "ON CONFLICT (user_id, period_kind, period_key) DO NOTHING", (user_id, kind, key))

    @staticmethod
    def _claim(t, user_id, kind, key, amount, limit, must_fit):
        """Add `amount` to reserved if used + reserved + must_fit stays within the limit. True if it did."""
        if limit is None:
            t.execute("UPDATE quota_counters SET reserved = reserved + ? WHERE user_id = ? AND period_kind = ? "
                      "AND period_key = ?", (amount, user_id, kind, key))
            return True
        cur = t.execute("UPDATE quota_counters SET reserved = reserved + ? WHERE user_id = ? AND period_kind = ? "
                        "AND period_key = ? AND used + reserved + ? <= ?", (amount, user_id, kind, key, must_fit, limit))
        return cur.rowcount == 1

    def _counter(self, t, user_id, kind, key) -> dict:
        return t.one("SELECT used, reserved, requests FROM quota_counters WHERE user_id = ? AND period_kind = ? "
                     "AND period_key = ?", (user_id, kind, key)) or {"used": 0, "reserved": 0, "requests": 0}

    # ------------------------------------------------------------------ the three steps
    def reserve(self, user_id: str, amount: int, limits: Limits, *, must_fit: int | None = None,
                global_daily_cap: int | None = None) -> Reservation:
        """`amount` is the estimate to hold; `must_fit` (default: amount) is the least that has to be available."""
        must_fit = amount if must_fit is None else min(must_fit, amount)
        now = self.clock.now_ms()
        d, m, minute = day_key(now), month_key(now), str(now // MINUTE_MS)
        problem = None
        with self.db.tx() as t:
            for uid, kind, key in ((user_id, "day", d), (user_id, "month", m), (user_id, "minute", minute),
                                   (GLOBAL, "day", d)):
                self._ensure(t, uid, kind, key)
            if limits.requests_per_minute is not None:
                cur = t.execute("UPDATE quota_counters SET requests = requests + 1 WHERE user_id = ? AND "
                                "period_kind = 'minute' AND period_key = ? AND requests < ?",
                                (user_id, minute, limits.requests_per_minute))
                if cur.rowcount != 1:
                    problem = RateLimited(f"too many requests: at most {limits.requests_per_minute} per minute",
                                          limit=limits.requests_per_minute, resets_at=(now // MINUTE_MS + 1) * MINUTE_MS)
            if problem is None:
                for scope, uid, kind, key, limit, reset in (
                        ("user_day", user_id, "day", d, limits.tokens_per_day, next_day_start(now)),
                        ("user_month", user_id, "month", m, limits.tokens_per_month, next_month_start(now)),
                        ("global_day", GLOBAL, "day", d, global_daily_cap, next_day_start(now))):
                    if not self._claim(t, uid, kind, key, amount, limit, must_fit):
                        c = self._counter(t, uid, kind, key)
                        problem = QuotaExceeded(
                            {"user_day": "daily token allowance used up", "user_month": "monthly token allowance used up",
                             "global_day": "the service is at its daily capacity; please try again later"}[scope],
                            scope=scope, limit=limit, used=c["used"], resets_at=reset)
                        break
            if problem is not None:
                raise problem            # leaving the transaction by an exception undoes every claim made above
            rid = new_id()
            t.execute("INSERT INTO quota_reservations (id, user_id, amount, day_key, month_key, created_at) "
                      "VALUES (?,?,?,?,?,?)", (rid, user_id, amount, d, m, now))
            return Reservation(rid, user_id, amount, d, m)

    def _finish(self, res: Reservation, actual: int) -> None:
        with self.db.tx() as t:
            gone = t.execute("DELETE FROM quota_reservations WHERE id = ?", (res.id,)).rowcount
            if gone != 1:        # already settled or reaped: do not count twice
                return
            for uid, kind, key in ((res.user_id, "day", res.day_key), (res.user_id, "month", res.month_key),
                                   (GLOBAL, "day", res.day_key)):
                t.execute("UPDATE quota_counters SET reserved = reserved - ?, used = used + ? WHERE user_id = ? "
                          "AND period_kind = ? AND period_key = ?", (res.amount, actual, uid, kind, key))

    def settle(self, res: Reservation, actual_tokens: int) -> None:
        self._finish(res, max(0, int(actual_tokens)))

    def release(self, res: Reservation) -> None:
        self._finish(res, 0)

    def reap(self, max_age_ms: int = 10 * MINUTE_MS) -> int:
        """Release reservations whose call never finished (a crashed worker). Returns how many."""
        cutoff = self.clock.now_ms() - max_age_ms
        with self.db.read() as t:
            stale = t.all("SELECT * FROM quota_reservations WHERE created_at < ?", (cutoff,))
        for r in stale:
            self.release(Reservation(r["id"], r["user_id"], r["amount"], r["day_key"], r["month_key"]))
        return len(stale)

    # ------------------------------------------------------------------ reading
    def snapshot(self, user_id: str, limits: Limits) -> dict:
        now = self.clock.now_ms()
        with self.db.read() as t:
            day = self._counter(t, user_id, "day", day_key(now))
            month = self._counter(t, user_id, "month", month_key(now))
            minute = self._counter(t, user_id, "minute", str(now // MINUTE_MS))

        def part(c, limit, reset):
            used = c["used"] + c["reserved"]
            return {"used": used, "limit": limit, "remaining": None if limit is None else max(0, limit - used),
                    "resets_at": reset}
        return {"day": part(day, limits.tokens_per_day, next_day_start(now)),
                "month": part(month, limits.tokens_per_month, next_month_start(now)),
                "requests_this_minute": {"used": minute["requests"], "limit": limits.requests_per_minute}}

    def global_used_today(self) -> int:
        with self.db.read() as t:
            c = self._counter(t, GLOBAL, "day", day_key(self.clock.now_ms()))
        return c["used"] + c["reserved"]
