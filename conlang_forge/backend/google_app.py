"""Sign in with Google for the phone apps, through the system browser.

A phone app cannot use the website's Google button, and native Google SDKs need separate client ids and a custom
build. Instead the app opens this server in the phone's browser, and the server does the standard Google
"authorization code" flow with the same web client the website uses:

  app -> GET  /api/auth/google/app/start?redirect_uri=..&challenge=..      (browser) -> Google
  Google -> GET /api/auth/google/app/callback?code=..&state=..              server trades the code, verifies the ID token
  server -> 302 <app redirect>?grant=..                                     back into the app
  app -> POST /api/auth/google/app/exchange {grant, verifier}               gets a normal session

Nothing needs to be stored. `state` and `grant` are short-lived signed tokens. The app invents a random
`verifier` and sends only its SHA-256 `challenge` at the start (PKCE), so a grant that leaks from the redirect is
useless without the verifier, which never leaves the phone.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import urllib.parse
import urllib.request

import jwt

from .errors import AuthError, ValidationFailed
from .oidc import Identity

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
APP_SCHEMES = ("conlangforge", "exp", "exps")          # the installed app, and Expo Go while testing
STATE_TTL, GRANT_TTL = 600, 120
CALLBACK_PATH = "/api/auth/google/app/callback"


def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str, timeout: float = 15.0) -> dict:
    data = urllib.parse.urlencode({"code": code, "client_id": client_id, "client_secret": client_secret,
                                   "redirect_uri": redirect_uri, "grant_type": "authorization_code"}).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, headers={"content-type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as r:        # pragma: no cover - network
        return json.loads(r.read())


def pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def with_params(url: str, **params) -> str:
    sep = "&" if "?" in url else "?"
    return url + sep + urllib.parse.urlencode(params)


class GoogleAppFlow:
    def __init__(self, *, secret: str, verifier, client_id: str, client_secret: str, public_url: str, clock, exchange=exchange_code):
        self.secret, self.verifier, self.client_id, self.client_secret = secret, verifier, client_id, client_secret
        self.public_url, self.clock, self.exchange = public_url.rstrip("/"), clock, exchange

    @property
    def enabled(self) -> bool:
        return bool(self.verifier and self.client_id and self.client_secret and self.public_url)

    @property
    def callback_uri(self) -> str:
        return self.public_url + CALLBACK_PATH

    # ---- signed blobs
    def _sign(self, aud: str, ttl: int, **claims) -> str:
        now = self.clock.now_ms() // 1000
        return jwt.encode({**claims, "aud": aud, "iss": "conlang-forge-google-app", "iat": now, "exp": now + ttl}, self.secret, algorithm="HS256")

    def _open(self, token: str, aud: str) -> dict:
        try:
            claims = jwt.decode(token, self.secret, algorithms=["HS256"], audience=aud, issuer="conlang-forge-google-app", options={"verify_exp": False})
        except jwt.PyJWTError as e:
            raise AuthError("invalid or expired sign-in; start again") from e
        if claims["exp"] <= self.clock.now_ms() // 1000:
            raise AuthError("invalid or expired sign-in; start again")
        return claims

    # ---- steps
    @staticmethod
    def check_redirect(uri: str) -> str:
        parts = urllib.parse.urlsplit(uri or "")
        if parts.scheme not in APP_SCHEMES or not (parts.netloc or parts.path) or parts.fragment:
            raise ValidationFailed("redirect_uri must point back to the app")
        return uri

    def start(self, redirect_uri: str, challenge: str) -> str:
        if not self.enabled:
            raise ValidationFailed("Google sign-in for the app is not configured on this server")
        self.check_redirect(redirect_uri)
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", challenge or ""):
            raise ValidationFailed("challenge must be a base64url SHA-256")
        nonce = secrets.token_urlsafe(16)
        state = self._sign("state", STATE_TTL, redirect=redirect_uri, challenge=challenge, nonce=nonce)
        return with_params(AUTH_URL, client_id=self.client_id, redirect_uri=self.callback_uri, response_type="code",
                           scope="openid email profile", state=state, nonce=nonce, prompt="select_account")

    def callback(self, code: str | None, state: str | None, error: str | None) -> str:
        """Returns the URL to send the browser to (always back into the app when the state is valid)."""
        st = self._open(state or "", "state")                 # a bad state is shown as an error page, not redirected
        redirect = st["redirect"]
        if error or not code:
            return with_params(redirect, error="Google sign-in was cancelled." if error == "access_denied" else "Google sign-in failed.")
        try:
            tok = self.exchange(code, self.client_id, self.client_secret, self.callback_uri)
            ident = self.verifier.verify(tok["id_token"], self.clock.now_ms(), st["nonce"])
        except Exception:
            return with_params(redirect, error="Google sign-in failed. Try again.")
        grant = self._sign("grant", GRANT_TTL, sub=ident.subject, email=ident.email, name=ident.name, challenge=st["challenge"])
        return with_params(redirect, grant=grant)

    def identity_for(self, grant: str, verifier: str) -> Identity:
        g = self._open(grant, "grant")
        if not hmac.compare_digest(pkce_challenge(verifier or ""), g["challenge"]):
            raise AuthError("invalid or expired sign-in; start again")
        return Identity("google", g["sub"], g["email"], True, g.get("name", ""))
