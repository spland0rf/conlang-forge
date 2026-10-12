"""Email verification and password recovery (no network: mail goes to an in-memory sender)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pytest  # noqa: E402

from asgi_client import Client  # noqa: E402
from conlang_forge.backend import mail as mailmod  # noqa: E402
from conlang_forge.backend.api import create_app  # noqa: E402
from conlang_forge.backend.app import Backend, Config  # noqa: E402
from conlang_forge.backend.clock import FakeClock, HOUR_MS, MINUTE_MS  # noqa: E402
from conlang_forge.backend.errors import AuthError, EmailNotVerified, RateLimited, ValidationFailed  # noqa: E402
from conlang_forge.backend.llm.providers import FakeProvider  # noqa: E402
from conlang_forge.backend.mail import FakeMailer, MailError  # noqa: E402

PW = "Correct-Horse-9"
NEW = "Brand-New-Pass-42"


def make():
    clock, mailer = FakeClock(), FakeMailer()
    be = Backend(Config(database=":memory:", signing_secret="s" * 40, scrypt_n=2 ** 10,
                        public_url="https://example.org/conlang/"),
                 provider=FakeProvider(), clock=clock, mailer=mailer,
                 generator=lambda seed, pins: ({"seed": seed}, {"vocab_version": "t", "seed": seed}))
    return be, clock, mailer


def token_in(mail):
    m = re.search(r"/#/(verify|reset)/([\w-]+)", mail.text)
    assert m, mail.text
    return m.group(2)


def test_registration_sends_a_confirmation_link_that_verifies_once():
    be, clock, mailer = make()
    u = be.accounts.register("a@x.org", PW, "Ann")
    assert u["email_verified"] == 0 and len(mailer.sent) == 1
    mail = mailer.sent[0]
    assert mail.to == "a@x.org" and "https://example.org/conlang/#/verify/" in mail.text and "//#" not in mail.text
    tok = token_in(mail)
    assert be.accounts.verify_email(tok)["email"] == "a@x.org"
    assert be.accounts.get(u["id"])["email_verified"] == 1
    with pytest.raises(ValidationFailed):                    # single use
        be.accounts.verify_email(tok)
    with pytest.raises(ValidationFailed):
        be.accounts.verify_email("not-a-token")


def test_confirmation_link_expires_and_resend_is_throttled_and_replaces_old_link():
    be, clock, mailer = make()
    u = be.accounts.register("a@x.org", PW)
    actor = be.accounts.actor_of(be.accounts.get(u["id"]))
    first = token_in(mailer.sent[0])
    with pytest.raises(RateLimited):
        be.accounts.resend_verification(actor)
    clock.advance(2 * MINUTE_MS)
    assert be.accounts.resend_verification(actor) == {"sent": True}
    second = token_in(mailer.sent[1])
    assert first != second
    with pytest.raises(ValidationFailed):                    # the older link stopped working
        be.accounts.verify_email(first)
    clock.advance(49 * HOUR_MS)
    with pytest.raises(ValidationFailed):
        be.accounts.verify_email(second)
    clock.advance(MINUTE_MS)
    be.accounts.resend_verification(actor)
    be.accounts.verify_email(token_in(mailer.sent[2]))
    assert be.accounts.resend_verification(actor) == {"already_verified": True}


def test_operator_made_and_google_accounts_are_already_verified():
    be, clock, mailer = make()
    a = be.accounts.bootstrap_admin("boss@x.org", PW)
    assert a["email_verified"] == 1 and mailer.sent == []


def test_delivery_failure_does_not_break_registration():
    be, clock, mailer = make()
    mailer.fail = True
    u = be.accounts.register("a@x.org", PW)
    assert u["email_verified"] == 0
    mailer.fail = False
    clock.advance(2 * MINUTE_MS)
    be.accounts.resend_verification(be.accounts.actor_of(be.accounts.get(u["id"])))
    assert len(mailer.sent) == 1


def test_password_reset_flow_ends_sessions_and_unlocks_and_confirms_email():
    be, clock, mailer = make()
    be.accounts.register("a@x.org", PW)
    mailer.sent.clear()
    old = be.accounts.login("a@x.org", PW)
    for _ in range(5):
        with pytest.raises(AuthError):
            be.accounts.login("a@x.org", "wrong-Password-1")                 # locks the account
    be.accounts.request_password_reset("A@X.org")
    assert len(mailer.sent) == 1 and "https://example.org/conlang/#/reset/" in mailer.sent[0].text
    tok = token_in(mailer.sent[0])
    with pytest.raises(ValidationFailed):
        be.accounts.complete_password_reset(tok, "weak")                      # bad password does not burn the link
    be.accounts.complete_password_reset(tok, NEW)
    with pytest.raises(AuthError):                                            # old sessions are gone
        be.accounts.refresh(old["refresh_token"])
    s = be.accounts.login("a@x.org", NEW)                                     # lock cleared, new password works
    assert s["user"]["email_verified"] == 1
    with pytest.raises(AuthError):
        be.accounts.login("a@x.org", PW)
    with pytest.raises(ValidationFailed):                                     # single use
        be.accounts.complete_password_reset(tok, "Another-Pass-77")


def test_reset_request_never_reveals_whether_an_account_exists_and_expires():
    be, clock, mailer = make()
    be.accounts.request_password_reset("nobody@x.org")
    be.accounts.request_password_reset("not an email")
    assert mailer.sent == []
    be.accounts.register("a@x.org", PW)
    mailer.sent.clear()
    be.accounts.request_password_reset("a@x.org")
    be.accounts.request_password_reset("a@x.org")                             # inside the minute: quietly ignored
    assert len(mailer.sent) == 1
    clock.advance(HOUR_MS + MINUTE_MS)
    with pytest.raises(ValidationFailed):
        be.accounts.complete_password_reset(token_in(mailer.sent[0]), NEW)
    adm = be.accounts.actor_of(be.accounts.get(be.accounts.bootstrap_admin("boss@x.org", PW)["id"]))
    be.accounts.disable(adm, be.accounts.login("a@x.org", PW)["user"]["id"])
    mailer.sent.clear()
    clock.advance(2 * MINUTE_MS)
    be.accounts.request_password_reset("a@x.org")                             # disabled accounts get nothing
    assert mailer.sent == []


def test_a_google_only_account_can_set_a_password_by_email():
    be, clock, mailer = make()
    from conlang_forge.backend.oidc import Identity
    ident = Identity("google", "sub1", "g@x.org", True, "Gee")
    be.accounts.login_with_identity(ident)
    be.accounts.request_password_reset("g@x.org")
    be.accounts.complete_password_reset(token_in(mailer.sent[-1]), NEW)
    assert be.accounts.login("g@x.org", NEW)["user"]["password_set"] == 1


def test_setting_can_require_a_confirmed_email_for_model_calls():
    be, clock, mailer = make()
    u = be.accounts.register("a@x.org", PW)
    actor = be.accounts.actor_of(be.accounts.get(u["id"]))
    adm = be.accounts.actor_of(be.accounts.get(be.accounts.bootstrap_admin("boss@x.org", PW)["id"]))
    assert be.llm.complete(actor, "translate.reduce", prompt="hello").text            # off by default: works unverified
    be.settings.set(adm, "llm.require_verified_email", True)
    with pytest.raises(EmailNotVerified):
        be.llm.complete(actor, "translate.reduce", prompt="hello")
    assert be.llm.complete(adm, "translate.reduce", prompt="hello").text               # staff are never blocked
    be.accounts.verify_email(token_in(mailer.sent[0]))
    assert be.llm.complete(actor, "translate.reduce", prompt="hello").text


def test_api_routes_and_uniform_forgot_answer():
    be, clock, mailer = make()
    c = Client(create_app(be))
    r = c.post("/api/auth/register", {"email": "a@x.org", "password": PW}, token=None)
    assert r.status_code == 200 and r.json()["user"]["email_verified"] == 0
    c.token = r.json()["access_token"]
    assert c.post("/api/me/verify/resend", {}).status_code == 429
    assert c.post("/api/auth/verify", {"token": token_in(mailer.sent[0])}, token=None).json()["verified"] is True
    assert c.get("/api/me").json()["email_verified"] == 1
    a = c.post("/api/auth/forgot", {"email": "a@x.org"}, token=None)
    b = c.post("/api/auth/forgot", {"email": "ghost@x.org"}, token=None)
    assert a.status_code == b.status_code == 200 and a.json() == b.json()
    assert c.post("/api/auth/reset", {"token": token_in(mailer.sent[-1]), "new_password": NEW}, token=None).status_code == 200
    assert c.post("/api/auth/login", {"email": "a@x.org", "password": NEW}, token=None).status_code == 200
    assert c.post("/api/auth/reset", {"token": "bad", "new_password": NEW}, token=None).status_code == 422
    cfg = c.get("/api/config").json()
    assert cfg["email_enabled"] is True and cfg["verified_email_required"] is False


def test_mailer_selection_and_resend_request(monkeypatch=None):
    assert mailmod.mailer_from_env({}).name == "console"
    assert mailmod.mailer_from_env({"MAIL_PROVIDER": "smtp", "SMTP_HOST": "h", "MAIL_FROM": "X <x@y.z>"}).port == 587
    assert mailmod.mailer_from_env({"MAIL_PROVIDER": "smtp", "SMTP_HOST": "h", "SMTP_SECURITY": "ssl"}).port == 465
    with pytest.raises(ValueError):
        mailmod.mailer_from_env({"MAIL_PROVIDER": "resend"})                  # key missing
    with pytest.raises(ValueError):
        mailmod.mailer_from_env({"MAIL_PROVIDER": "carrier-pigeon"})
    sent = {}

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    def fake_open(req, timeout=0):
        sent.update(url=req.full_url, auth=req.get_header("Authorization"), body=req.data)
        return Resp()
    real = mailmod.urllib.request.urlopen
    mailmod.urllib.request.urlopen = fake_open
    try:
        m = mailmod.mailer_from_env({"MAIL_PROVIDER": "resend", "RESEND_API_KEY": "re_test", "MAIL_FROM": "CF <noreply@x.org>"})
        m.send(mailmod.Mail("a@b.co", "Hi", "Body"))
    finally:
        mailmod.urllib.request.urlopen = real
    assert sent["url"] == "https://api.resend.com/emails" and sent["auth"] == "Bearer re_test"
    assert b'"to": ["a@b.co"]' in sent["body"] and b"noreply@x.org" in sent["body"]
