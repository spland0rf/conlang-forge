"""Accounts, permissions, quotas, the metered LLM wrapper and usage reports (no network, no real model)."""
import json
import tempfile
import threading
from pathlib import Path

import pytest

from conlang_forge.backend.app import Backend, Config
from conlang_forge.backend.clock import DAY_MS, FakeClock
from conlang_forge.backend.errors import (AccountDisabled, AccountLocked, AuthError, Conflict, LLMDisabled,
                                          NotFound, PermissionDenied, ProviderError, QuotaExceeded, RateLimited,
                                          ValidationFailed)
from conlang_forge.backend.llm.providers import AnthropicProvider, FakeProvider
from conlang_forge.backend.llm.types import Message

PW = "Correct-Horse-9"


def make(provider=None, path=":memory:", **kw):
    clock = FakeClock()
    be = Backend(Config(database=path, signing_secret="s" * 40, scrypt_n=2 ** 10),
                 provider=provider if provider is not None else FakeProvider(), clock=clock,
                 generator=kw.get("generator", lambda seed, pins: ({"seed": seed}, {"vocab_version": "t", "seed": seed})))
    return be, clock


def user(be, email="u@x.org", **kw):
    u = be.accounts.register(email, PW, **kw)
    return u, be.accounts.actor_of(be.accounts.get(u["id"]))


def admin(be, email="boss@x.org"):
    u = be.accounts.bootstrap_admin(email, PW)
    return u, be.accounts.actor_of(be.accounts.get(u["id"]))


# ------------------------------------------------------------------ accounts
def test_register_login_refresh_rotation_and_reuse_detection():
    be, clock = make()
    be.accounts.register("A@X.org", PW, "Ann")
    s1 = be.accounts.login("a@x.org", PW)
    assert be.accounts.authenticate(s1["access_token"]).email == "a@x.org"
    s2 = be.accounts.refresh(s1["refresh_token"])
    assert s2["refresh_token"] != s1["refresh_token"]
    with pytest.raises(AuthError):                       # the old token is stolen and replayed ...
        be.accounts.refresh(s1["refresh_token"])
    with pytest.raises(AuthError):                       # ... so the whole family is dead, including the new one
        be.accounts.refresh(s2["refresh_token"])
    s3 = be.accounts.login("a@x.org", PW)
    be.accounts.logout(s3["refresh_token"])
    with pytest.raises(AuthError):
        be.accounts.refresh(s3["refresh_token"])


def test_access_token_expires_and_rejects_forgery():
    be, clock = make()
    be.accounts.register("a@x.org", PW)
    tok = be.accounts.login("a@x.org", PW)["access_token"]
    clock.advance(901_000)
    with pytest.raises(AuthError):
        be.accounts.authenticate(tok)
    with pytest.raises(AuthError):
        be.accounts.authenticate(tok[:-3] + "abc")


def test_password_rules_duplicates_and_lockout():
    be, clock = make()
    with pytest.raises(ValidationFailed):
        be.accounts.register("a@x.org", "short1A")
    with pytest.raises(ValidationFailed):
        be.accounts.register("not-an-email", PW)
    be.accounts.register("a@x.org", PW)
    with pytest.raises(Conflict):
        be.accounts.register("A@x.org", PW)
    for _ in range(5):
        with pytest.raises(AuthError):
            be.accounts.login("a@x.org", "wrong-Password1")
    with pytest.raises(AccountLocked):                   # locked even for the right password
        be.accounts.login("a@x.org", PW)
    clock.advance(16 * 60_000)
    assert be.accounts.login("a@x.org", PW)["access_token"]
    with pytest.raises(AuthError) as e:                  # unknown email looks the same as a wrong password
        be.accounts.login("nobody@x.org", PW)
    assert "wrong email or password" in str(e.value)


def test_no_self_service_privilege_and_registration_switch():
    be, _ = make()
    with pytest.raises(PermissionDenied):
        be.accounts.register("a@x.org", PW, role="admin")
    _, adm = admin(be)
    be.settings.set(adm, "registration.open", False)
    with pytest.raises(PermissionDenied):
        be.accounts.register("b@x.org", PW)


def test_disabling_takes_effect_immediately_and_last_admin_is_protected():
    be, _ = make()
    u, ua = user(be)
    a, adm = admin(be)
    sess = be.accounts.login("u@x.org", PW)
    be.accounts.disable(adm, u["id"], "abuse")
    with pytest.raises(AccountDisabled):
        be.accounts.authenticate(sess["access_token"])
    with pytest.raises(AccountDisabled):
        be.accounts.refresh(sess["refresh_token"])
    with pytest.raises(AccountDisabled):
        be.accounts.login("u@x.org", PW)
    with pytest.raises(Conflict):
        be.accounts.disable(adm, a["id"])
    with pytest.raises(Conflict):
        be.accounts.set_role(adm, a["id"], "user")
    be.accounts.enable(adm, u["id"])
    assert be.accounts.login("u@x.org", PW)
    b, _ = admin(be, "second@x.org")
    be.accounts.set_role(adm, a["id"], "user")           # fine now: there is another administrator
    with pytest.raises(PermissionDenied):                # and the demoted one has lost the power
        be.accounts.list_users(be.accounts.actor_of(be.accounts.get(a["id"])))
    actions = [r["action"] for r in be.audit.list(limit=50)]
    assert "user.disable" in actions and "user.role" in actions


def test_permission_matrix():
    be, _ = make()
    (u1, a1), (u2, a2), (_, adm) = user(be, "1@x.org"), user(be, "2@x.org"), admin(be)
    c = be.conlangs.create(a1, "Mine", seed=1)
    assert be.conlangs.get_language(adm, c["id"])["seed"] == 1       # admin can read any conlang
    with pytest.raises(PermissionDenied):
        be.conlangs.get_language(a2, c["id"])                       # other users cannot
    with pytest.raises(PermissionDenied):
        be.conlangs.rename(adm, c["id"], "Hijack")                  # not even admins edit others' conlangs
    with pytest.raises(PermissionDenied):
        be.conlangs.delete(a2, c["id"])
    with pytest.raises(PermissionDenied):
        be.accounts.list_users(a1)
    with pytest.raises(PermissionDenied):
        be.settings.set(a1, "llm.enabled", False)
    with pytest.raises(PermissionDenied):
        be.limits.set_user_overrides(a1, u1["id"], tokens_per_day=10**9)    # cannot raise your own limits
    assert be.accounts.list_users(adm)["total"] == 3
    assert [x["id"] for x in be.conlangs.list_own(a2)] == []
    assert len(be.conlangs.list_all(adm)) == 1
    be.conlangs.delete(a1, c["id"])
    with pytest.raises(NotFound):
        be.conlangs.summary(a1, c["id"])


def test_conlang_count_limit_follows_plan_and_override():
    be, _ = make()
    u, a = user(be)
    _, adm = admin(be)
    be.limits.set_plan_limits(adm, "free", max_conlangs=2)
    be.conlangs.create(a, "One", seed=1)
    be.conlangs.create(a, "Two", seed=2)
    with pytest.raises(QuotaExceeded):
        be.conlangs.create(a, "Three", seed=3)
    be.limits.set_user_overrides(adm, u["id"], max_conlangs=3)
    be.conlangs.create(a, "Three", seed=3)
    be.limits.set_user_overrides(adm, u["id"], max_conlangs=-1)    # unlimited
    be.conlangs.create(a, "Four", seed=4)
    be.limits.set_user_overrides(adm, u["id"], max_conlangs=None)  # back to the plan
    assert be.limits.resolve(be.accounts.get(u["id"])).max_conlangs == 2


# ------------------------------------------------------------------ metered LLM
def setup_llm(provider=None, **plan):
    be, clock = make(provider)
    u, a = user(be)
    _, adm = admin(be)
    if plan:
        be.limits.set_plan_limits(adm, "free", **plan)
    return be, clock, u, a, adm


def test_call_is_logged_priced_and_counted():
    be, clock, u, a, adm = setup_llm()
    r = be.llm.complete(a, "translate.reduce", prompt="the old wizard went home")
    assert r.text.startswith("[claude-haiku") and r.usage.input_tokens > 0 and r.cost_micro_usd > 0
    rows = be.usage.recent_calls(adm)
    assert len(rows) == 1 and rows[0]["status"] == "ok" and rows[0]["user_id"] == u["id"]
    assert rows[0]["purpose"] == "translate.reduce" and rows[0]["quota_tokens"] == r.usage.quota_tokens
    mine = be.usage.my_usage(a)
    assert mine["day"]["used"] == r.usage.quota_tokens == mine["month"]["used"]
    assert mine["day"]["limit"] == 50_000 and mine["requests_this_minute"]["used"] == 1


def test_permissions_and_ownership_on_model_calls():
    be, clock, u, a, adm = setup_llm()
    _, b = user(be, "b@x.org")
    c = be.conlangs.create(a, "Mine", seed=1)
    with pytest.raises(PermissionDenied):
        be.llm.complete(b, "translate.reduce", prompt="hi", conlang_id=c["id"])
    with pytest.raises(PermissionDenied):                # administrators cannot spend a user's allowance either
        be.llm.complete(adm, "translate.reduce", prompt="hi", conlang_id=c["id"])
    with pytest.raises(PermissionDenied):
        be.llm.complete(a, "admin.test", prompt="hi")
    with pytest.raises(PermissionDenied):
        be.llm.complete(a, "translate.reduce", prompt="hi", model="claude-opus-5-5")
    assert be.llm.complete(adm, "admin.test", prompt="ping", model="claude-sonnet-5-5").model == "claude-sonnet-5-5"
    assert be.llm.complete(a, "translate.reduce", prompt="hi", conlang_id=c["id"]).text
    denied = be.usage.recent_calls(adm, status="denied")
    assert len(denied) == 4 and all(d["quota_tokens"] == 0 for d in denied)
    with pytest.raises(ValidationFailed):
        be.llm.complete(a, "no.such.purpose", prompt="x")
    with pytest.raises(ValidationFailed):
        be.llm.complete(a, "translate.reduce", prompt="")


def test_disabled_user_and_kill_switch_cannot_call():
    be, clock, u, a, adm = setup_llm()
    be.settings.set(adm, "llm.enabled", False)
    with pytest.raises(LLMDisabled):
        be.llm.complete(a, "translate.reduce", prompt="hi")
    be.settings.set(adm, "llm.enabled", True)
    be.accounts.disable(adm, u["id"])
    with pytest.raises(AccountDisabled):                  # the old Actor object is stale; the wrapper re-reads the user
        be.llm.complete(a, "translate.reduce", prompt="hi")
    assert be.provider.calls == []


def test_daily_and_monthly_quota_with_reset():
    be, clock, u, a, adm = setup_llm(requests_per_minute=None)
    big = "x" * 300
    go = lambda: be.llm.complete(a, "translate.reduce", prompt=big, max_tokens=50)
    one = go().usage.quota_tokens                   # measure one call, then set limits in units of it
    be.limits.set_user_overrides(adm, u["id"], tokens_per_day=2 * one + 5, tokens_per_month=3 * one + 5)
    go()                                            # day 1, second call: fits
    with pytest.raises(QuotaExceeded) as e:         # day 1, third: daily allowance gone
        go()
    assert e.value.detail["scope"] == "user_day" and e.value.detail["resets_at"] > clock.now_ms()
    clock.advance(DAY_MS)
    go()                                            # a new day: allowed again (month total is now 3 calls)
    with pytest.raises(QuotaExceeded) as e:
        go()
    assert e.value.detail["scope"] == "user_month"
    clock.advance(40 * DAY_MS)                      # a new month
    go()
    snap = be.usage.my_usage(a)
    assert snap["day"]["used"] == one and snap["month"]["used"] == one      # the refused calls used nothing


def test_per_user_override_beats_plan_and_rate_limit():
    be, clock, u, a, adm = setup_llm(tokens_per_day=100, requests_per_minute=2)
    with pytest.raises(QuotaExceeded):
        be.llm.complete(a, "translate.reduce", prompt="y" * 600)
    be.limits.set_user_overrides(adm, u["id"], tokens_per_day=100_000)
    be.llm.complete(a, "translate.reduce", prompt="hello")
    be.llm.complete(a, "translate.reduce", prompt="hello")
    with pytest.raises(RateLimited):
        be.llm.complete(a, "translate.reduce", prompt="hello")
    clock.advance(61_000)
    be.llm.complete(a, "translate.reduce", prompt="hello")


def test_global_cap_and_failed_calls_cost_nothing():
    prov = FakeProvider([ProviderError("down", retryable=False, http_status=400)])
    be, clock, u, a, adm = setup_llm(prov)
    with pytest.raises(ProviderError):
        be.llm.complete(a, "translate.reduce", prompt="hello")
    snap = be.my = be.usage.my_usage(a)
    assert snap["day"]["used"] == 0                       # the reservation was released
    row = be.usage.recent_calls(adm)[0]
    assert row["status"] == "error" and row["error_code"] == "provider_error" and row["quota_tokens"] == 0
    be.settings.set(adm, "llm.global_tokens_per_day", 50)
    with pytest.raises(QuotaExceeded) as e:
        be.llm.complete(a, "translate.reduce", prompt="z" * 400)
    assert e.value.detail["scope"] == "global_day"


def test_retries_temporary_failures_with_backoff_and_bills_once():
    prov = FakeProvider([ProviderError("busy", retryable=True, http_status=529),
                         ProviderError("slow", retryable=True, http_status=429, retry_after=7), "finally"])
    be, clock, u, a, adm = setup_llm(prov)
    r = be.llm.complete(a, "translate.reduce", prompt="hello")
    assert r.text == "finally" and r.attempts == 3 and len(prov.calls) == 3
    assert clock.slept == [1.0, 7]
    assert len(be.usage.recent_calls(adm)) == 1
    prov.script[:] = [ProviderError("busy", retryable=True)] * 3
    with pytest.raises(ProviderError):
        be.llm.complete(a, "translate.reduce", prompt="hello")
    assert be.usage.recent_calls(adm)[0]["attempts"] == 3


def test_real_usage_replaces_estimate_and_output_cap_is_enforced():
    be, clock, u, a, adm = setup_llm(max_output_tokens=40)
    r = be.llm.complete(a, "translate.reduce", prompt="hello", max_tokens=5000)
    assert be.provider.calls[-1].max_tokens == 40
    snap = be.usage.my_usage(a)
    assert snap["day"]["used"] == r.usage.quota_tokens          # not the larger estimate


def test_crashed_reservation_is_reaped():
    be, clock, u, a, adm = setup_llm()
    lim = be.limits.resolve(be.accounts.get(u["id"]))
    be.quota.reserve(u["id"], 1000, lim)
    assert be.usage.my_usage(a)["day"]["used"] == 1000
    clock.advance(11 * 60_000)
    assert be.quota.reap() == 1 and be.usage.my_usage(a)["day"]["used"] == 0


def test_concurrent_calls_cannot_overspend_the_allowance():
    path = str(Path(tempfile.mkdtemp()) / "t.db")
    be, clock, u, a, adm = setup_llm(None, tokens_per_day=1000, requests_per_minute=None) if False else (None,) * 5
    be, clock = make(FakeProvider(), path)
    u, a = user(be)
    _, adm = admin(be)
    be.limits.set_plan_limits(adm, "free", tokens_per_day=1000, requests_per_minute=None)
    lim = be.limits.resolve(be.accounts.get(u["id"]))
    ok, no = [], []

    def go():
        try:
            be.quota.reserve(u["id"], 300, lim)
            ok.append(1)
        except QuotaExceeded:
            no.append(1)
    ts = [threading.Thread(target=go) for _ in range(12)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(ok) == 3 and len(no) == 9            # 3 x 300 fit in 1000; the 4th does not


# ------------------------------------------------------------------ usage reports
def test_usage_reports_group_by_user_purpose_and_bucket():
    be, clock, u, a, adm = setup_llm(tokens_per_day=10**7, requests_per_minute=None)
    ub, b = user(be, "b@x.org")
    t0 = clock.now_ms()
    for i in range(3):
        be.llm.complete(a, "translate.reduce", prompt="one two three")
    be.llm.complete(b, "translate.smooth", prompt="four five")
    clock.advance(DAY_MS)
    be.llm.complete(a, "book.polish", prompt="six")
    end = clock.now_ms() + 1000
    ts = be.usage.timeseries(adm, start_ms=t0 // DAY_MS * DAY_MS, end_ms=end, bucket="day", group_by="purpose")
    by = {(r["bucket_start"], r["grp"]): r["calls"] for r in ts["rows"]}
    assert sorted(by.values()) == [1, 1, 3] and len({k[0] for k in by}) == 2
    tot = be.usage.totals(adm, start_ms=t0 - 1, end_ms=end)
    assert tot["calls"] == 5 and tot["cost_micro_usd"] > 0
    top = be.usage.top_users(adm, start_ms=t0 - 1, end_ms=end)
    assert top[0]["email"] == "u@x.org" and top[0]["calls"] == 4
    with pytest.raises(PermissionDenied):
        be.usage.timeseries(a, start_ms=t0, end_ms=end)            # users cannot see system-wide graphs
    assert be.usage.timeseries(a, start_ms=t0 - 1, end_ms=end, user_id=u["id"])["rows"]   # but can see their own
    with pytest.raises(PermissionDenied):
        be.usage.timeseries(a, start_ms=t0 - 1, end_ms=end, user_id=ub["id"])
    with pytest.raises(ValidationFailed):
        be.usage.timeseries(adm, start_ms=t0, end_ms=end, group_by="email; DROP TABLE users")


def test_unknown_model_price_is_flagged_and_prices_are_overridable():
    be, clock, u, a, adm = setup_llm()
    be.llm.complete(adm, "admin.test", prompt="x", model="mystery-model")
    row = be.usage.recent_calls(adm)[0]
    assert row["error_code"] == "unpriced_model" and row["cost_micro_usd"] == 0
    be.settings.set(adm, "llm.prices", {"mystery-model": {"in": 2.0, "out": 4.0}})
    r = be.llm.complete(adm, "admin.test", prompt="x", model="mystery-model")
    assert r.cost_micro_usd == round(r.usage.input_tokens * 2 + r.usage.output_tokens * 4)


def test_previews_are_off_by_default_and_optional():
    be, clock, u, a, adm = setup_llm()
    be.llm.complete(a, "translate.reduce", prompt="secret words")
    assert be.usage.recent_calls(adm)[0]["preview_json"] is None
    be.settings.set(adm, "llm.store_previews", True)
    clock.advance(5)
    be.llm.complete(a, "translate.reduce", prompt="secret words")
    assert "secret words" in be.usage.recent_calls(adm)[0]["preview_json"]


# ------------------------------------------------------------------ the Anthropic provider (stub transport)
def test_anthropic_provider_parses_and_classifies_errors():
    seen = {}

    def ok(url, headers, body, timeout):
        seen.update(json.loads(body), headers=headers)
        return 200, {}, json.dumps({"id": "msg_1", "model": "claude-haiku-4-5-20251001", "stop_reason": "end_turn",
                                    "content": [{"type": "text", "text": "hel"}, {"type": "text", "text": "lo"}],
                                    "usage": {"input_tokens": 11, "output_tokens": 3, "cache_read_input_tokens": 50}}).encode()
    p = AnthropicProvider("k", transport=ok)
    from conlang_forge.backend.llm.types import LLMRequest
    r = p.complete(LLMRequest("claude-haiku-4-5-20251001", (Message("user", "hi"),), "be brief", 100, 0.0))
    assert r.text == "hello" and r.usage.input_tokens == 11 and r.usage.quota_tokens == 11 + 3 + 5
    assert seen["system"] == "be brief" and seen["headers"]["x-api-key"] == "k" and seen["max_tokens"] == 100

    def err(status, **h):
        return lambda *a: (status, h, json.dumps({"error": {"message": "nope"}}).encode())
    for status, retryable in ((429, True), (529, True), (500, True), (400, False), (401, False)):
        with pytest.raises(ProviderError) as e:
            AnthropicProvider("k", transport=err(status, **{"retry-after": "4"})).complete(
                LLMRequest("m", (Message("user", "hi"),)))
        assert e.value.retryable is retryable
    assert e.value.retry_after == 4.0
    with pytest.raises(ValueError):
        AnthropicProvider(None) if not __import__("os").environ.get("ANTHROPIC_API_KEY") else (_ for _ in ()).throw(ValueError)


def test_models_that_reject_temperature_are_retried_without_it_and_remembered():
    from conlang_forge.backend.llm.types import LLMRequest
    sent = []

    def transport(url, headers, raw, timeout):
        body = json.loads(raw)
        sent.append(body)
        if "temperature" in body:
            return 400, {}, json.dumps({"error": {"message": "`temperature` is deprecated for this model."}}).encode()
        return 200, {}, json.dumps({"id": "m", "model": body["model"], "stop_reason": "end_turn", "content": [{"type": "text", "text": "ok"}],
                                    "usage": {"input_tokens": 1, "output_tokens": 1}}).encode()
    p = AnthropicProvider("k", transport=transport)
    req = LLMRequest("claude-new", (Message("user", "hi"),), "", 50, 0.0)
    assert p.complete(req).text == "ok" and ["temperature" in b for b in sent] == [True, False]
    assert p.complete(req).text == "ok" and ["temperature" in b for b in sent] == [True, False, False]   # remembered
    # an unrelated 400 is still an error
    bad = AnthropicProvider("k", transport=lambda *a: (400, {}, json.dumps({"error": {"message": "max_tokens too large"}}).encode()))
    with pytest.raises(ProviderError):
        bad.complete(req)


# ------------------------------------------------------------------ sign in with Google
def _google(client_id="client-123"):
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt as _jwt
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(_jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid="k1", alg="RS256", use="sig")
    clock = FakeClock()
    be = Backend(Config(database=":memory:", signing_secret="s" * 40, scrypt_n=2 ** 10, google_client_id=client_id),
                 provider=FakeProvider(), clock=clock, google_jwks=lambda url: {"keys": [jwk]})

    def token(sub="g-1", email="g@gmail.com", verified=True, aud=client_id, iss="https://accounts.google.com",
              ttl=3600, kid="k1", signing_key=key, **extra):
        now = clock.now_ms() // 1000
        claims = {"sub": sub, "email": email, "email_verified": verified, "aud": aud, "iss": iss, "iat": now,
                  "exp": now + ttl, "name": "Gina G", **extra}
        return _jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid": kid})
    return be, clock, token, key


def test_google_sign_in_creates_then_reuses_the_account():
    be, clock, token, _ = _google()
    s1 = be.login_with_google(token())
    assert s1["user"]["email"] == "g@gmail.com" and s1["user"]["password_set"] == 0 and s1["user"]["email_verified"] == 1
    s2 = be.login_with_google(token(email="changed@gmail.com"))          # same Google account, new email: same user
    assert s2["user"]["id"] == s1["user"]["id"]
    assert be.accounts.authenticate(s2["access_token"]).email == "g@gmail.com"
    with pytest.raises(AuthError):                                         # no password exists to guess
        be.accounts.login("g@gmail.com", "anything-Goes-1")
    assert be.accounts.linked_providers(be.accounts.authenticate(s2["access_token"])) == ["google"]


def test_google_links_to_existing_password_account_with_same_verified_email():
    be, clock, token, _ = _google()
    u = be.accounts.register("same@gmail.com", PW)
    s = be.login_with_google(token(sub="g-9", email="same@gmail.com"))
    assert s["user"]["id"] == u["id"]
    assert be.accounts.login("same@gmail.com", PW)["user"]["id"] == u["id"]      # the password still works
    actions = [r["action"] for r in be.audit.list(limit=20)]
    assert "identity.link" in actions


def test_google_token_checks():
    from cryptography.hazmat.primitives.asymmetric import rsa
    be, clock, token, key = _google()
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for bad in (token(aud="someone-elses-app"), token(iss="https://evil.example"), token(ttl=-10),
                token(signing_key=other), token(kid="unknown")):
        with pytest.raises(AuthError):
            be.login_with_google(bad)
    with pytest.raises(AuthError):
        be.login_with_google(token(verified=False))
    with pytest.raises(AuthError):
        be.login_with_google("not.a.jwt")
    with pytest.raises(AuthError):                                         # a replayed token for another nonce
        be.login_with_google(token(nonce="a"), nonce="b")
    assert be.login_with_google(token(nonce="a"), nonce="a")["access_token"]
    plain, _ = make()
    with pytest.raises(ValidationFailed):
        plain.login_with_google(token())                                    # not configured


def test_google_respects_disabled_accounts_and_closed_registration():
    be, clock, token, _ = _google()
    s = be.login_with_google(token())
    adm = be.accounts.actor_of(be.accounts.get(be.accounts.bootstrap_admin("boss@x.org", PW)["id"]))
    be.accounts.disable(adm, s["user"]["id"], "spam")
    with pytest.raises(AccountDisabled):
        be.login_with_google(token())
    be.settings.set(adm, "registration.open", False)
    with pytest.raises(PermissionDenied):
        be.login_with_google(token(sub="new-person", email="new@gmail.com"))
    be.accounts.enable(adm, s["user"]["id"])
    assert be.login_with_google(token())["access_token"]                    # existing users still sign in


def test_first_password_can_be_set_without_old_one():
    be, clock, token, _ = _google()
    s = be.login_with_google(token())
    me = be.accounts.authenticate(s["access_token"])
    be.accounts.change_password(me, "", "Brand-New-Pass9")
    assert be.accounts.login("g@gmail.com", "Brand-New-Pass9")["user"]["id"] == s["user"]["id"]
    with pytest.raises(AuthError):
        be.accounts.change_password(me, "wrong-old-Pass1", "Another-Pass-9")
