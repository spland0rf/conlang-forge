"""Allowances: plans (defaults) and per-user overrides.

A limit of None means unlimited. In a per-user override, NULL means "use the plan" and -1 means "unlimited".
The seeded plan values are placeholders for the owner to tune in the admin area.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationFailed
from .permissions import Actor, require

FIELDS = ("tokens_per_day", "tokens_per_month", "requests_per_minute", "max_conlangs", "max_output_tokens")


@dataclass(frozen=True)
class Limits:
    tokens_per_day: int | None = None
    tokens_per_month: int | None = None
    requests_per_minute: int | None = None
    max_conlangs: int | None = None
    max_output_tokens: int | None = None

    def to_dict(self):
        return asdict(self)


SEED_PLANS = {
    "free": ("New accounts", Limits(50_000, 500_000, 6, 5, 2_000)),
    "standard": ("Regular users", Limits(400_000, 6_000_000, 20, 50, 4_000)),
    "staff": ("Owner and staff: no practical limits", Limits(None, None, 60, None, 8_000)),
}


class LimitsService:
    def __init__(self, db, clock, audit):
        self.db, self.clock, self.audit = db, clock, audit
        self._seed()

    def _seed(self):
        with self.db.tx() as t:
            for name, (desc, lim) in SEED_PLANS.items():
                if t.one("SELECT name FROM plans WHERE name = ?", (name,)) is None:
                    t.execute("INSERT INTO plans (name, description, tokens_per_day, tokens_per_month, "
                              "requests_per_minute, max_conlangs, max_output_tokens) VALUES (?,?,?,?,?,?,?)",
                              (name, desc, *[getattr(lim, f) for f in FIELDS]))

    # ---- reading
    def plan(self, name: str) -> Limits:
        with self.db.read() as t:
            row = t.one("SELECT * FROM plans WHERE name = ?", (name,))
        if row is None:
            raise NotFound(f"no plan {name}")
        return Limits(**{f: row[f] for f in FIELDS})

    def plans(self) -> list:
        with self.db.read() as t:
            return t.all("SELECT * FROM plans ORDER BY name")

    def overrides(self, user_id: str) -> dict:
        with self.db.read() as t:
            row = t.one("SELECT * FROM user_limits WHERE user_id = ?", (user_id,))
        return {f: row[f] for f in FIELDS} if row else {f: None for f in FIELDS}

    def resolve(self, user: dict) -> Limits:
        """Effective limits for a user row: plan values, then per-user overrides."""
        base = self.plan(user["plan"]).to_dict()
        for f, v in self.overrides(user["id"]).items():
            if v is not None:
                base[f] = None if v == -1 else v
        return Limits(**base)

    # ---- writing (admin)
    def set_plan_limits(self, actor: Actor, name: str, **values) -> None:
        require(actor, "limits.manage")
        self._check(values)
        self.plan(name)
        values = {f: (None if v == -1 else v) for f, v in values.items()}     # -1 or None: unlimited
        with self.db.tx() as t:
            for f, v in values.items():
                t.execute(f"UPDATE plans SET {f} = ? WHERE name = ?", (v, name))
            self.audit.record(t, actor.id, "plan.limits", "plan", name, **values)

    def set_user_overrides(self, actor: Actor, user_id: str, **values) -> None:
        """Pass a number to override, -1 for unlimited, None to go back to the plan."""
        require(actor, "limits.manage")
        self._check(values, allow_none=True)
        with self.db.tx() as t:
            if t.one("SELECT id FROM users WHERE id = ?", (user_id,)) is None:
                raise NotFound("no such user")
            cur = self.overrides(user_id)
            cur.update(values)
            t.execute("DELETE FROM user_limits WHERE user_id = ?", (user_id,))
            t.execute("INSERT INTO user_limits (user_id, tokens_per_day, tokens_per_month, requests_per_minute, "
                      "max_conlangs, max_output_tokens, updated_by, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                      (user_id, *[cur[f] for f in FIELDS], actor.id, self.clock.now_ms()))
            self.audit.record(t, actor.id, "user.limits", "user", user_id, **values)

    @staticmethod
    def _check(values, allow_none=False):
        for f, v in values.items():
            if f not in FIELDS:
                raise ValidationFailed(f"unknown limit {f}")
            if v is None and allow_none:
                continue
            if v is not None and (not isinstance(v, int) or v < -1):
                raise ValidationFailed(f"{f} must be a whole number (or -1 for unlimited)")
