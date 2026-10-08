"""Sign in with an identity provider (Google now; Facebook and Apple later).

Google flow: the browser (Google Identity Services) or the phone app obtains a Google *ID token* — a JWT signed by
Google — and sends it to us. We never see the user's Google password. We check, with Google's published public
keys, that the token's signature is valid, that it was issued by Google for OUR client id, that it has not
expired, and that Google vouches for the email address. Then `AccountService.login_with_identity` finds or creates
the matching user.

Apple's "Sign in with Apple" also hands out an ID token signed with published keys, so it can reuse this class
with Apple's issuer and keys. Facebook issues an access token instead and needs a call to its Graph API; that is
a separate small verifier.

The key fetcher is injectable so tests (and offline development) can supply keys without a network.
"""
from __future__ import annotations

import json
import threading
import urllib.request
from dataclasses import dataclass

import jwt

from .errors import AuthError, ValidationFailed

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


@dataclass(frozen=True)
class Identity:
    provider: str
    subject: str            # the provider's stable id for the person (Google "sub")
    email: str
    email_verified: bool
    name: str = ""


def fetch_jwks(url: str, timeout: float = 10.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:      # pragma: no cover - network
        return json.loads(r.read())


class JwksCache:
    """Provider signing keys, refreshed at most once per `ttl` seconds (and when an unknown key id shows up)."""

    def __init__(self, url: str, fetcher=fetch_jwks, ttl: float = 3600.0, now=None):
        import time
        self.url, self.fetcher, self.ttl = url, fetcher, ttl
        self._now = now or time.time
        self._keys, self._at, self._lock = {}, -1e18, threading.Lock()

    def key(self, kid: str):
        with self._lock:
            if kid not in self._keys or self._now() - self._at > self.ttl:
                try:
                    data = self.fetcher(self.url)
                except Exception as e:
                    if kid in self._keys:        # keep serving the keys we have if the refresh fails
                        return self._keys[kid]
                    raise AuthError("could not fetch the provider's signing keys") from e
                self._keys = {k["kid"]: jwt.PyJWK(k).key for k in data.get("keys", [])}
                self._at = self._now()
            if kid not in self._keys:
                raise AuthError("unknown signing key")
            return self._keys[kid]


class GoogleVerifier:
    provider = "google"

    def __init__(self, client_id: str, jwks: JwksCache | None = None):
        if not client_id:
            raise ValueError("a Google client id is required")
        self.client_id = client_id
        self.jwks = jwks or JwksCache(GOOGLE_JWKS_URL)

    def verify(self, id_token: str, now_ms: int, nonce: str | None = None) -> Identity:
        try:
            header = jwt.get_unverified_header(id_token)
            key = self.jwks.key(header.get("kid", ""))
            claims = jwt.decode(id_token, key, algorithms=["RS256"], audience=self.client_id,
                                options={"verify_exp": False, "require": ["exp", "iat", "sub", "aud", "iss"]})
        except AuthError:
            raise
        except jwt.PyJWTError as e:
            raise AuthError("invalid Google sign-in") from e
        if claims["iss"] not in GOOGLE_ISSUERS:
            raise AuthError("invalid Google sign-in")
        if claims["exp"] <= now_ms // 1000:                       # our clock, so tests can control it
            raise AuthError("Google sign-in expired; try again")
        if nonce is not None and claims.get("nonce") != nonce:
            raise AuthError("invalid Google sign-in")
        email = (claims.get("email") or "").lower()
        if not email:
            raise ValidationFailed("Google did not share an email address")
        if not claims.get("email_verified"):
            raise AuthError("Google has not verified this email address")
        return Identity("google", str(claims["sub"]), email, True, claims.get("name", ""))
