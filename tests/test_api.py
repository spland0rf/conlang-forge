"""The HTTP API, driven through the ASGI interface (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pytest  # noqa: E402

from asgi_client import Client  # noqa: E402
from conlang_forge.backend.api import create_app  # noqa: E402
from conlang_forge.backend.app import Backend, Config  # noqa: E402
from conlang_forge.backend.clock import FakeClock  # noqa: E402
from conlang_forge.backend.llm.providers import FakeProvider  # noqa: E402

DATA = str(Path(__file__).resolve().parents[1] / "data")
PW = "Correct-Horse-9"
_SHARED = {}


def make(**kw):
    be = Backend(Config(database=":memory:", signing_secret="s" * 40, scrypt_n=2 ** 10, data_dir=DATA,
                        google_client_id=kw.pop("google_client_id", "")),
                 provider=FakeProvider(), clock=FakeClock(), **kw)
    return be, Client(create_app(be))


def signed_in(c, be, email="u@x.org"):
    r = c.post("/api/auth/register", {"email": email, "password": PW}, token=None)
    assert r.status_code == 200, r.text
    c.token = r.json()["access_token"]
    return r.json()


def admin_client(be, app_client):
    be.accounts.bootstrap_admin("boss@x.org", PW)
    a = Client(app_client.app)
    a.token = a.post("/api/auth/login", {"email": "boss@x.org", "password": PW}, token=None).json()["access_token"]
    return a


def test_public_config_and_auth_required():
    be, c = make()
    cfg = c.get("/api/config").json()
    assert cfg["registration_open"] is True and cfg["google_client_id"] is None and "morphology.typology" in cfg["dials"]
    assert c.get("/api/health").json()["ok"] is True
    r = c.get("/api/me")
    assert r.status_code == 401 and r.json()["error"] == "auth_failed"
    assert c.get("/api/me", token="garbage").status_code == 401
    assert c.get("/api/nope").status_code == 404
    assert c.post("/api/auth/login", {"email": "a@b.co"}, token=None).status_code == 422


def test_register_login_refresh_logout_over_http():
    be, c = make()
    s = signed_in(c, be)
    me = c.get("/api/me").json()
    assert me["email"] == "u@x.org" and me["usage"]["day"]["limit"] == 50_000 and me["role"] == "user"
    s2 = c.post("/api/auth/refresh", {"refresh_token": s["refresh_token"]}, token=None)
    assert s2.status_code == 200
    assert c.post("/api/auth/refresh", {"refresh_token": s["refresh_token"]}, token=None).status_code == 401
    assert c.post("/api/auth/logout", {"refresh_token": s2.json()["refresh_token"]}, token=None).status_code == 200
    assert c.post("/api/auth/login", {"email": "u@x.org", "password": "wrong-Pass-1"}, token=None).status_code == 401
    assert c.post("/api/auth/register", {"email": "u@x.org", "password": PW}, token=None).status_code == 409
    assert c.post("/api/auth/register", {"email": "z@x.org", "password": "weak"}, token=None).status_code == 422
    assert c.post("/api/me/password", {"old_password": PW, "new_password": "Another-Pass-77"}).status_code == 200


def test_create_view_download_and_delete_a_conlang():
    be, c = make()
    signed_in(c, be)
    r = c.post("/api/conlangs", {"name": "Zurö", "seed": 5})
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    one = c.get(f"/api/conlangs/{cid}").json()
    assert one["profile"]["words"] >= 2000 and one["profile"]["grammar"]["type"] and one["profile"]["quick_words"]
    d = c.get(f"/api/conlangs/{cid}/dictionary.json").json()
    assert d["count"] >= 2000 and {"en", "form", "ipa", "pos"} <= set(d["entries"][0])
    md = c.get(f"/api/conlangs/{cid}/dictionary.md")
    assert md.status_code == 200 and md.text.startswith("# ") and "text/markdown" in md.headers["content-type"]
    assert c.get(f"/api/conlangs/{cid}/dictionary.csv?download=1").headers["content-disposition"].startswith("attachment")
    assert "Lesson 1" in c.get(f"/api/conlangs/{cid}/grammar-book.md").text
    assert [x["id"] for x in c.get("/api/conlangs").json()["conlangs"]] == [cid]
    assert c.patch(f"/api/conlangs/{cid}", {"name": "Renamed"}).json()["name"] == "Renamed"
    # another user cannot see it
    other = Client(c.app)
    signed_in(other, be, "o@x.org")
    assert other.get(f"/api/conlangs/{cid}").status_code == 403
    assert other.get(f"/api/conlangs/{cid}/dictionary.json").status_code == 403
    assert other.delete(f"/api/conlangs/{cid}").status_code == 403
    assert c.delete(f"/api/conlangs/{cid}").status_code == 200
    assert c.get(f"/api/conlangs/{cid}").status_code == 404


def test_dials_are_whitelisted_and_pins_take_effect():
    be, c = make()
    signed_in(c, be)
    assert c.post("/api/conlangs", {"name": "X", "pins": {"phonology.consonants": ["p"]}}).status_code == 422
    assert c.post("/api/conlangs", {"name": "X", "pins": {"morphology.typology": "klingon"}}).status_code == 422
    assert c.post("/api/conlangs", {"name": "X", "seed": -4}).status_code == 422
    assert c.post("/api/conlangs", {"name": "x" * 90, "seed": 3}).status_code == 422
    r = c.post("/api/conlangs", {"name": "Pinned", "seed": 12, "pins": {"morphology.typology": "isolating",
                                                                        "syntax.word_order": "SOV", "name": "Setthi"}})
    assert r.status_code == 200, r.text
    g = c.get(f"/api/conlangs/{r.json()['id']}").json()["profile"]
    assert g["grammar"]["type"] == "isolating" and g["grammar"]["word_order"] == "SOV" and g["name"] == "Setthi"


def test_conlang_limit_returns_429_with_scope():
    be, c = make()
    signed_in(c, be)
    adm = admin_client(be, c)
    uid = c.get("/api/me").json()["id"]
    assert adm.patch(f"/api/admin/users/{uid}", {"limits": {"max_conlangs": 1}}).status_code == 200
    assert c.post("/api/conlangs", {"name": "A", "seed": 1}).status_code == 200
    r = c.post("/api/conlangs", {"name": "B", "seed": 2})
    assert r.status_code == 429 and r.json()["scope"] == "max_conlangs"


def test_admin_endpoints_need_the_admin_role():
    be, c = make()
    signed_in(c, be)
    for path in ("/api/admin/users", "/api/admin/plans", "/api/admin/audit", "/api/admin/settings",
                 "/api/admin/usage/totals", "/api/admin/usage/series", "/api/admin/usage/top-users",
                 "/api/admin/usage/calls", "/api/admin/conlangs"):
        assert c.get(path).status_code == 403, path
    assert c.put("/api/admin/settings", {"llm.enabled": False}).status_code == 403
    assert c.post("/api/admin/llm-test", {"prompt": "hi"}).status_code == 403
    uid = c.get("/api/me").json()["id"]
    assert c.patch(f"/api/admin/users/{uid}", {"role": "admin"}).status_code == 403          # no self-promotion
    assert c.patch(f"/api/admin/users/{uid}", {"limits": {"max_conlangs": 999}}).status_code == 403


def test_admin_manages_users_limits_settings_and_sees_usage():
    be, c = make()
    signed_in(c, be)
    uid = c.get("/api/me").json()["id"]
    adm = admin_client(be, c)
    users = adm.get("/api/admin/users?q=u@x").json()
    assert users["total"] == 1 and users["users"][0]["id"] == uid
    detail = adm.get(f"/api/admin/users/{uid}").json()
    assert detail["limits"]["effective"]["tokens_per_day"] == 50_000 and detail["usage"]["day"]["used"] == 0
    assert adm.patch(f"/api/admin/users/{uid}", {"plan": "standard"}).json()["plan"] == "standard"
    assert adm.patch(f"/api/admin/users/{uid}", {"limits": {"tokens_per_day": 123}}).status_code == 200
    assert adm.get(f"/api/admin/users/{uid}").json()["limits"]["effective"]["tokens_per_day"] == 123
    assert adm.get("/api/admin/plans").json()["plans"][0]["name"]
    assert adm.put("/api/admin/plans/free", {"max_conlangs": 7}).status_code == 200
    # a model call by the user shows up in the graphs
    be.llm.complete(be.accounts.actor_of(be.accounts.get(uid)), "translate.reduce", prompt="hello there")
    assert adm.get("/api/admin/usage/totals").json()["calls"] == 1
    series = adm.get("/api/admin/usage/series?bucket=hour&group_by=purpose").json()
    assert series["rows"][0]["grp"] == "translate.reduce"
    assert adm.get("/api/admin/usage/top-users").json()["users"][0]["email"] == "u@x.org"
    assert adm.get("/api/admin/usage/calls").json()["calls"][0]["status"] == "ok"
    assert adm.get("/api/admin/usage/series?bucket=bogus").status_code == 422
    # kill switch from the admin screen
    assert adm.put("/api/admin/settings", {"llm.enabled": False}).json()["llm.enabled"] is False
    assert adm.put("/api/admin/settings", {"nonsense": 1}).status_code == 422
    r = adm.post("/api/admin/llm-test", {"prompt": "ping"})
    assert r.status_code == 503
    adm.put("/api/admin/settings", {"llm.enabled": True})
    assert adm.post("/api/admin/llm-test", {"prompt": "ping"}).json()["text"].startswith("[")
    # disabling stops the user's existing token at once
    assert adm.patch(f"/api/admin/users/{uid}", {"status": "disabled", "reason": "test"}).status_code == 200
    assert c.get("/api/me").status_code == 403
    actions = [e["action"] for e in adm.get("/api/admin/audit").json()["entries"]]
    assert "user.disable" in actions and "user.plan" in actions and "settings.set" in actions
    assert adm.get("/api/admin/conlangs").status_code == 200


def test_google_endpoint():
    sys.path.insert(0, str(Path(__file__).parent))
    import json as _json

    import jwt as _jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _json.loads(_jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid="k1", alg="RS256")
    be, c = make(google_client_id="cid-1", google_jwks=lambda url: {"keys": [jwk]})
    assert c.get("/api/config").json()["google_client_id"] == "cid-1"
    now = be.clock.now_ms() // 1000
    tok = _jwt.encode({"sub": "1", "email": "gg@gmail.com", "email_verified": True, "aud": "cid-1",
                       "iss": "accounts.google.com", "iat": now, "exp": now + 600, "name": "Gee"}, key,
                      algorithm="RS256", headers={"kid": "k1"})
    r = c.post("/api/auth/google", {"credential": tok}, token=None)
    assert r.status_code == 200 and r.json()["user"]["email"] == "gg@gmail.com"
    c.token = r.json()["access_token"]
    me = c.get("/api/me").json()
    assert me["providers"] == ["google"] and me["password_set"] == 0
    assert c.post("/api/auth/google", {"credential": "x.y.z"}, token=None).status_code == 401
    bad, c2 = make()
    assert c2.post("/api/auth/google", {"credential": tok}, token=None).status_code == 422
