"""Passwords, access tokens (JWT) and refresh tokens. Standard library plus PyJWT."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

import jwt

from .errors import AuthError

# scrypt parameters (OWASP-recommended class); stored in the hash so they can be raised later
_N, _R, _P = 2 ** 15, 8, 1


def hash_password(password: str, *, n: int = _N) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=n, r=_R, p=_P, dklen=32, maxmem=128 * 1024 * 1024)
    return f"scrypt${n}${_R}${_P}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, dk = stored.split("$")
        calc = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                              dklen=32, maxmem=128 * 1024 * 1024)
        return hmac.compare_digest(calc, base64.b64decode(dk))
    except Exception:
        return False


def new_refresh_token() -> tuple:
    """(token to give the client, hash to store). Only the hash is kept."""
    tok = secrets.token_urlsafe(48)
    return tok, hash_token(tok)


def hash_token(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()


class TokenSigner:
    """Short-lived signed access tokens. The token carries only the user id; role and status are read from the
    database on every request, so disabling an account or changing a role takes effect at once."""
    ALG = "HS256"

    def __init__(self, secret: str, ttl_seconds: int = 900, issuer: str = "conlang-forge"):
        if len(secret) < 32:
            raise ValueError("signing secret must be at least 32 characters")
        self.secret, self.ttl, self.issuer = secret, ttl_seconds, issuer

    def issue(self, user_id: str, now_ms: int) -> str:
        now = now_ms // 1000
        return jwt.encode({"sub": user_id, "iat": now, "exp": now + self.ttl, "iss": self.issuer},
                          self.secret, algorithm=self.ALG)

    def verify(self, token: str, now_ms: int) -> str:
        try:
            claims = jwt.decode(token, self.secret, algorithms=[self.ALG], issuer=self.issuer,
                                options={"verify_exp": False})
        except jwt.PyJWTError as e:
            raise AuthError("invalid token") from e
        if claims["exp"] <= now_ms // 1000:      # compare against our clock, not the system clock
            raise AuthError("token expired", expired=True)
        return claims["sub"]
