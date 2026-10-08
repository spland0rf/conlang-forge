"""MeteredLLM: every model call in the system goes through `complete`.

For one call it: re-reads the user (so a disabled account stops at once), checks the permission for the purpose
and ownership of the conlang, checks the kill switch, reserves tokens against the user's quotas and the global
cap, calls the provider (retrying temporary failures), settles the real token count, prices the call and writes
one row to the call log. Refused calls are logged too, with status "denied", so the admin can see who is hitting
limits. Nothing is charged for a failed call.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..clock import Clock, day_key, new_id
from ..errors import BackendError, LLMDisabled, NotFound, PermissionDenied, ProviderError, ValidationFailed
from ..permissions import Actor, can, require
from .pricing import Pricing
from .purposes import PURPOSES
from .types import LLMRequest, Message, Usage

MAX_ATTEMPTS = 3
BACKOFF_S = (1.0, 3.0)
MAX_INPUT_CHARS = 60_000


@dataclass(frozen=True)
class LLMResult:
    text: str
    usage: Usage
    model: str
    call_id: str
    cost_micro_usd: int
    attempts: int


class MeteredLLM:
    def __init__(self, db, clock: Clock, accounts, limits, quota, settings, provider, *, model_overrides=None):
        self.db, self.clock, self.accounts, self.limits = db, clock, accounts, limits
        self.quota, self.settings, self.provider = quota, settings, provider
        self.model_overrides = dict(model_overrides or {})        # purpose -> model

    # ------------------------------------------------------------------ public
    def complete(self, actor: Actor, purpose: str, *, prompt: str | None = None, messages=None, system: str = "",
                 conlang_id: str | None = None, job_id: str | None = None, max_tokens: int | None = None,
                 model: str | None = None, cache_system: bool = False) -> LLMResult:
        p = PURPOSES.get(purpose)
        if p is None:
            raise ValidationFailed(f"unknown purpose {purpose}")
        msgs = tuple(messages) if messages else (Message("user", prompt or ""),)
        chars = len(system) + sum(len(m.content) for m in msgs)
        started = self.clock.now_ms()
        call = {"id": new_id(), "user_id": actor.id, "conlang_id": conlang_id, "job_id": job_id, "purpose": purpose,
                "model": None, "request_chars": chars}
        reservation = None
        try:
            user = self.accounts.get(actor.id)                    # fresh status, role and plan
            live = self.accounts.actor_of(user)
            owner = self._owner(conlang_id, live)
            require(live, p.permission, owner)
            if model is not None and not live.is_admin:
                raise PermissionDenied("only administrators can choose the model")
            if not self.settings.get("llm.enabled"):
                raise LLMDisabled("model calls are switched off")
            if chars > MAX_INPUT_CHARS or not chars:
                raise ValidationFailed(f"input must be 1-{MAX_INPUT_CHARS} characters")
            lim = self.limits.resolve(user)
            out_cap = min(max_tokens or p.max_output_tokens, p.max_output_tokens,
                          lim.max_output_tokens or p.max_output_tokens)
            use_model = model or self.model_overrides.get(purpose) or p.model
            call["model"] = use_model
            in_est = (chars + 2) // 3 + 20
            reservation = self.quota.reserve(user["id"], in_est + out_cap, lim, must_fit=in_est + 1,
                                             global_daily_cap=self.settings.get("llm.global_tokens_per_day"))
            req = LLMRequest(use_model, msgs, system, out_cap, p.temperature, cache_system)
            resp, attempts = self._call(req)
        except BackendError as e:
            if reservation is not None:
                self.quota.release(reservation)
            call.update(status="denied" if not isinstance(e, ProviderError) else "error", error_code=e.code,
                        attempts=getattr(e, "attempts", 0))
            self._log(call, started, None, 0)
            raise
        except BaseException:
            if reservation is not None:
                self.quota.release(reservation)
            raise
        self.quota.settle(reservation, resp.usage.quota_tokens)
        prices = Pricing(self.settings.get("llm.prices"))
        cost = prices.cost_micro_usd(resp.model or use_model, resp.usage)
        call.update(status="ok", error_code=None if prices.known(resp.model or use_model) else "unpriced_model",
                    attempts=attempts, model=resp.model or use_model)
        self._log(call, started, resp, cost, req=req)
        return LLMResult(resp.text, resp.usage, call["model"], call["id"], cost, attempts)

    # ------------------------------------------------------------------ internals
    def _owner(self, conlang_id, actor):
        """Owner of the resource the permission is checked against: the conlang's owner, else the actor."""
        if not conlang_id:
            return actor.id
        with self.db.read() as t:
            row = t.one("SELECT owner_id, status FROM conlangs WHERE id = ?", (conlang_id,))
        if row is None or row["status"] != "active":
            raise NotFound("no such conlang")
        if row["owner_id"] != actor.id:       # an administrator may read others' conlangs but never spend on them
            raise PermissionDenied("this conlang belongs to another user")
        return row["owner_id"]

    def _call(self, req):
        last = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return self.provider.complete(req), attempt
            except ProviderError as e:
                last = e
                last.attempts = attempt
                if not e.retryable or attempt == MAX_ATTEMPTS:
                    raise
                delay = e.retry_after if e.retry_after is not None else BACKOFF_S[min(attempt - 1, len(BACKOFF_S) - 1)]
                self.clock.sleep(min(delay, 20.0))
        raise last        # pragma: no cover

    def _log(self, call, started, resp, cost, req=None):
        now = self.clock.now_ms()
        u = resp.usage if resp else Usage()
        preview = None
        if resp is not None and self.settings.get("llm.store_previews") and req is not None:
            preview = json.dumps({"prompt": req.messages[-1].content[:500], "response": resp.text[:500]})
        with self.db.tx() as t:
            t.execute(
                "INSERT INTO llm_calls (id, user_id, conlang_id, job_id, purpose, provider, model, status, error_code, "
                "input_tokens, output_tokens, cache_write_tokens, cache_read_tokens, quota_tokens, cost_micro_usd, "
                "latency_ms, attempts, request_chars, response_chars, preview_json, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (call["id"], call["user_id"], call["conlang_id"], call["job_id"], call["purpose"],
                 getattr(self.provider, "name", "?"), call["model"], call["status"], call.get("error_code"),
                 u.input_tokens, u.output_tokens, u.cache_write_tokens, u.cache_read_tokens, u.quota_tokens, cost,
                 now - started, call.get("attempts", 0), call["request_chars"], len(resp.text) if resp else 0,
                 preview, now))
