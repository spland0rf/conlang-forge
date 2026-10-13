"""Sign in with Google from the phone app: browser hand-off with PKCE (Google itself is faked)."""
import json
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).parent))
import jwt  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402

from asgi_client import Client  # noqa: E402
from conlang_forge.backend.api import create_app  # noqa: E402
from conlang_forge.backend.app import Backend, Config  # noqa: E402
from conlang_forge.backend.clock import FakeClock  # noqa: E402
from conlang_forge.backend.google_app import pkce_challenge  # noqa: E402
from conlang_forge.backend.llm.providers import FakeProvider  # noqa: E402

REDIRECT = "conlangforge://auth"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
JWK = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key()))
JWK.update(kid="k1", alg="RS256")


def make(secret="shh", public="https://example.org/conlang", email_verified=True):
    clock = FakeClock()
    seen = {}

    def exchange(code, client_id, client_secret, redirect_uri):
        seen.update(code=code, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
        if code == "bad":
            raise RuntimeError("google said no")
        now = clock.now_ms() // 1000
        return {"id_token": jwt.encode({"sub": "42", "email": "gg@gmail.com", "email_verified": email_verified, "aud": "cid",
                                        "iss": "accounts.google.com", "iat": now, "exp": now + 600, "name": "Gee",
                                        "nonce": seen["nonce"]}, KEY, algorithm="RS256", headers={"kid": "k1"})}
    be = Backend(Config(database=":memory:", signing_secret="s" * 40, scrypt_n=2 ** 10, google_client_id="cid",
                        google_client_secret=secret, public_url=public),
                 provider=FakeProvider(), clock=clock, google_jwks=lambda url: {"keys": [JWK]}, google_exchange=exchange)
    return be, Client(create_app(be)), seen


def start(c, seen, verifier=None, redirect=REDIRECT):
    verifier = verifier or secrets.token_urlsafe(32)
    r = c.request("GET", f"/api/auth/google/app/start?redirect_uri={redirect}&challenge={pkce_challenge(verifier)}", token=None)
    assert r.status_code == 302, r.text
    q = parse_qs(urlsplit(r.headers["location"]).query)
    seen["nonce"] = q["nonce"][0]
    return verifier, r.headers["location"], q


def test_full_flow_signs_in_and_creates_account():
    be, c, seen = make()
    assert c.get("/api/config", token=None).json()["google_app_enabled"] is True
    verifier, loc, q = start(c, seen)
    assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert q["client_id"] == ["cid"] and q["redirect_uri"] == ["https://example.org/conlang/api/auth/google/app/callback"]
    assert q["scope"] == ["openid email profile"] and q["response_type"] == ["code"]
    cb = c.request("GET", "/api/auth/google/app/callback?code=abc&state=" + q["state"][0], token=None)
    assert cb.status_code == 302 and cb.headers["location"].startswith("conlangforge://auth?grant=")
    assert seen["code"] == "abc" and seen["client_secret"] == "shh"
    grant = parse_qs(urlsplit(cb.headers["location"]).query)["grant"][0]
    r = c.post("/api/auth/google/app/exchange", {"grant": grant, "verifier": verifier}, token=None)
    assert r.status_code == 200 and r.json()["user"]["email"] == "gg@gmail.com"
    c.token = r.json()["access_token"]
    assert c.get("/api/me").json()["providers"] == ["google"]


def test_grant_is_useless_without_the_verifier():
    be, c, seen = make()
    verifier, _, q = start(c, seen)
    cb = c.request("GET", "/api/auth/google/app/callback?code=abc&state=" + q["state"][0], token=None)
    grant = parse_qs(urlsplit(cb.headers["location"]).query)["grant"][0]
    assert c.post("/api/auth/google/app/exchange", {"grant": grant, "verifier": "wrong"}, token=None).status_code == 401


def test_expiry():
    be, c, seen = make()
    verifier, _, q = start(c, seen)
    cb = c.request("GET", "/api/auth/google/app/callback?code=abc&state=" + q["state"][0], token=None)
    grant = parse_qs(urlsplit(cb.headers["location"]).query)["grant"][0]
    be.clock.advance(121_000)
    assert c.post("/api/auth/google/app/exchange", {"grant": grant, "verifier": verifier}, token=None).status_code == 401


def test_redirect_must_be_the_app():
    be, c, seen = make()
    ch = pkce_challenge("v")
    for bad in ("https://evil.example/x", "javascript:alert(1)", "http://a", ""):
        r = c.request("GET", f"/api/auth/google/app/start?redirect_uri={bad}&challenge={ch}", token=None)
        assert r.status_code == 422, bad
    ok = c.request("GET", f"/api/auth/google/app/start?redirect_uri=exp://192.168.1.5:8081/--/auth&challenge={ch}", token=None)
    assert ok.status_code == 302
    assert c.request("GET", "/api/auth/google/app/start?redirect_uri=conlangforge://auth&challenge=short", token=None).status_code == 422


def test_cancel_and_failure_go_back_to_the_app_with_an_error():
    be, c, seen = make()
    _, _, q = start(c, seen)
    r = c.request("GET", "/api/auth/google/app/callback?error=access_denied&state=" + q["state"][0], token=None)
    assert r.status_code == 302 and "error=Google+sign-in+was+cancelled" in r.headers["location"]
    r = c.request("GET", "/api/auth/google/app/callback?code=bad&state=" + q["state"][0], token=None)
    assert r.status_code == 302 and "error=" in r.headers["location"] and "grant=" not in r.headers["location"]
    assert c.request("GET", "/api/auth/google/app/callback?code=x&state=garbage", token=None).status_code == 400


def test_unverified_google_email_is_refused():
    be, c, seen = make(email_verified=False)
    _, _, q = start(c, seen)
    r = c.request("GET", "/api/auth/google/app/callback?code=abc&state=" + q["state"][0], token=None)
    assert "grant=" not in r.headers["location"]


def test_not_configured_without_secret_or_public_url():
    for kw in ({"secret": ""}, {"public": ""}):
        be, c, seen = make(**kw)
        assert c.get("/api/config", token=None).json()["google_app_enabled"] is False
        r = c.request("GET", f"/api/auth/google/app/start?redirect_uri={REDIRECT}&challenge={pkce_challenge('v')}", token=None)
        assert r.status_code == 422
        assert c.post("/api/auth/google/app/exchange", {"grant": "x", "verifier": "y"}, token=None).status_code == 422
