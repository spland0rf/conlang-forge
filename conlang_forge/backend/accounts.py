"""User accounts: registration, login, token refresh, and administration of users.

Security choices:
* passwords are scrypt-hashed; a failed-login counter locks an account for a while after repeated failures;
* the same message is returned for an unknown email and a wrong password;
* refresh tokens are random, stored only as hashes, and rotated on every use. Presenting an already-used token
  is treated as theft: the whole token family is revoked;
* access tokens carry only the user id. Status and role are read from the database on every request, so a
  disabled account stops working at once;
* the last active admin can neither be disabled nor demoted.
"""
from __future__ import annotations

import re

from .clock import DAY_MS, MINUTE_MS, Clock, new_id
from .errors import (AccountDisabled, AccountLocked, AuthError, Conflict, NotFound, PermissionDenied,
                     ValidationFailed)
from .permissions import ROLES, Actor, require
from .security import TokenSigner, hash_password, hash_token, new_refresh_token, verify_password

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_FAILED = 5
LOCK_MS = 15 * MINUTE_MS
REFRESH_TTL_MS = 30 * DAY_MS
PUBLIC_FIELDS = ("id", "email", "display_name", "role", "status", "plan", "disabled_reason", "email_verified",
                 "password_set", "created_at", "last_login_at")


def public(user: dict | None) -> dict | None:
    return None if user is None else {k: user[k] for k in PUBLIC_FIELDS}


class AccountService:
    def __init__(self, db, clock: Clock, signer: TokenSigner, audit, settings, *, scrypt_n: int = 2 ** 15):
        self.db, self.clock, self.signer, self.audit, self.settings = db, clock, signer, audit, settings
        self.scrypt_n = scrypt_n
        self._dummy = hash_password("dummy-password-Z9", n=scrypt_n)    # same cost for unknown emails

    # ------------------------------------------------------------------ helpers
    def _user(self, t, user_id=None, email=None):
        if user_id is not None:
            return t.one("SELECT * FROM users WHERE id = ?", (user_id,))
        return t.one("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))

    def get(self, user_id: str) -> dict:
        with self.db.read() as t:
            u = self._user(t, user_id)
        if u is None:
            raise NotFound("no such user")
        return u

    @staticmethod
    def actor_of(u: dict) -> Actor:
        return Actor(u["id"], u["role"], u["status"], u["email"])

    @staticmethod
    def _check_password(pw: str):
        if len(pw) < 10:
            raise ValidationFailed("password must be at least 10 characters")
        if pw.lower() == pw or not any(c.isdigit() for c in pw):
            raise ValidationFailed("password must mix upper and lower case and include a digit")

    def _active_admins(self, t) -> int:
        return t.scalar("SELECT COUNT(*) FROM users WHERE role = 'admin' AND status = 'active'", default=0)

    # ------------------------------------------------------------------ registration and login
    def register(self, email: str, password: str, display_name: str = "", *, role: str = "user",
                 plan: str = "free", _internal: bool = False) -> dict:
        if not _internal and not self.settings.get("registration.open"):
            raise PermissionDenied("registration is closed")
        email = email.strip().lower()
        if not EMAIL_RE.match(email):
            raise ValidationFailed("that does not look like an email address")
        self._check_password(password)
        if role not in ROLES:
            raise ValidationFailed(f"unknown role {role}")
        if role != "user" and not _internal:
            raise PermissionDenied("only an administrator can create privileged accounts")
        pw = hash_password(password, n=self.scrypt_n)
        uid, now = new_id(), self.clock.now_ms()
        with self.db.tx() as t:
            if self._user(t, email=email):
                raise Conflict("an account with that email already exists")
            if t.one("SELECT name FROM plans WHERE name = ?", (plan,)) is None:
                raise ValidationFailed(f"unknown plan {plan}")
            t.execute("INSERT INTO users (id, email, display_name, password_hash, role, status, plan, created_at) "
                      "VALUES (?,?,?,?,?,?,?,?)",
                      (uid, email, display_name.strip() or email.split("@")[0], pw, role, "active", plan, now))
            self.audit.record(t, uid, "user.register", "user", uid, role=role, plan=plan)
            return public(self._user(t, uid))

    def bootstrap_admin(self, email: str, password: str, display_name: str = "Admin") -> dict:
        """Create the first administrator (command line / deployment only; there is no API route for this)."""
        return self.register(email, password, display_name, role="admin", plan="staff", _internal=True)

    def login(self, email: str, password: str, user_agent: str = "") -> dict:
        now = self.clock.now_ms()
        error = None
        with self.db.tx() as t:          # the counters must be saved even when the login fails
            u = self._user(t, email=email)
            if u is None:
                verify_password(password, self._dummy)
                error = AuthError("wrong email or password")
            elif u["locked_until"] > now:
                error = AccountLocked("too many failed attempts; try again later", retry_at=u["locked_until"])
            elif not verify_password(password, u["password_hash"]):
                fails = u["failed_logins"] + 1
                lock = now + LOCK_MS if fails >= MAX_FAILED else 0
                t.execute("UPDATE users SET failed_logins = ?, locked_until = ? WHERE id = ?",
                          (0 if lock else fails, lock, u["id"]))
                if lock:
                    self.audit.record(t, u["id"], "user.locked", "user", u["id"])
                error = AuthError("wrong email or password")
            elif u["status"] != "active":
                error = AccountDisabled("this account is disabled", reason=u["disabled_reason"])
            else:
                t.execute("UPDATE users SET failed_logins = 0, locked_until = 0, last_login_at = ? WHERE id = ?",
                          (now, u["id"]))
                out = self._issue(t, u, new_id(), user_agent)
                out.pop("_rid")
                return out
        raise error

    def login_with_identity(self, ident, user_agent: str = "") -> dict:
        """Sign in (or sign up) with a verified identity from a provider such as Google.

        1. a known (provider, subject) signs in to its user;
        2. otherwise, if a user with the same verified email exists, the identity is linked to that user (the provider
           has proved the person controls the address);
        3. otherwise a new user is created, if registration is open. Such an account has no password until the
           person sets one."""
        if not ident.email_verified:
            raise AuthError("the email address is not verified")
        now = self.clock.now_ms()
        error = None
        with self.db.tx() as t:
            link = t.one("SELECT * FROM identities WHERE provider = ? AND subject = ?", (ident.provider, ident.subject))
            if link:
                u = self._user(t, link["user_id"])
            else:
                u = self._user(t, email=ident.email)
                if u is None:
                    if not self.settings.get("registration.open"):
                        raise PermissionDenied("registration is closed")
                    uid = new_id()
                    t.execute("INSERT INTO users (id, email, display_name, password_hash, password_set, role, status, "
                              "plan, email_verified, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                              (uid, ident.email, (ident.name or ident.email.split("@")[0])[:80], "!", 0, "user",
                               "active", "free", 1, now))
                    self.audit.record(t, uid, "user.register", "user", uid, provider=ident.provider)
                    u = self._user(t, uid)
                else:
                    self.audit.record(t, u["id"], "identity.link", "user", u["id"], provider=ident.provider)
                t.execute("INSERT INTO identities (provider, subject, user_id, email, created_at) VALUES (?,?,?,?,?)",
                          (ident.provider, ident.subject, u["id"], ident.email, now))
            if u["status"] != "active":
                error = AccountDisabled("this account is disabled", reason=u["disabled_reason"])
            else:
                t.execute("UPDATE identities SET last_login_at = ? WHERE provider = ? AND subject = ?",
                          (now, ident.provider, ident.subject))
                t.execute("UPDATE users SET last_login_at = ?, email_verified = 1 WHERE id = ?", (now, u["id"]))
                out = self._issue(t, u, new_id(), user_agent)
                out.pop("_rid")
                return out
        raise error

    def _issue(self, t, u, family_id, user_agent="") -> dict:
        now = self.clock.now_ms()
        raw, h = new_refresh_token()
        rid = new_id()
        t.execute("INSERT INTO refresh_tokens (id, user_id, family_id, token_hash, created_at, expires_at, user_agent) "
                  "VALUES (?,?,?,?,?,?,?)", (rid, u["id"], family_id, h, now, now + REFRESH_TTL_MS, user_agent[:200]))
        return {"access_token": self.signer.issue(u["id"], now), "refresh_token": raw,
                "expires_in": self.signer.ttl, "user": public(u), "_rid": rid}

    def refresh(self, refresh_token: str, user_agent: str = "") -> dict:
        now, h = self.clock.now_ms(), hash_token(refresh_token)
        error = None
        with self.db.tx() as t:          # one transaction: two racing refreshes cannot both succeed
            row = t.one("SELECT * FROM refresh_tokens WHERE token_hash = ?", (h,))
            u = self._user(t, row["user_id"]) if row else None
            if row is None:
                error = AuthError("invalid refresh token")
            elif u is None or u["status"] != "active":
                error = AccountDisabled("this account is disabled")
            elif row["revoked_at"] is not None and row["replaced_by"] is None:
                error = AuthError("this session has ended; please sign in again")     # logout, password change
            elif row["revoked_at"] is not None:
                # a token that was already exchanged came back: assume it leaked and end the whole family
                t.execute("UPDATE refresh_tokens SET revoked_at = ? WHERE family_id = ? AND revoked_at IS NULL",
                          (now, row["family_id"]))
                self.audit.record(t, row["user_id"], "token.reuse", "user", row["user_id"])
                error = AuthError("refresh token already used; please sign in again")
            elif row["expires_at"] <= now:
                error = AuthError("refresh token expired")
            else:
                out = self._issue(t, u, row["family_id"], user_agent)
                t.execute("UPDATE refresh_tokens SET revoked_at = ?, replaced_by = ? WHERE id = ?",
                          (now, out.pop("_rid"), row["id"]))
                return out
        raise error

    def logout(self, refresh_token: str) -> None:
        with self.db.tx() as t:
            row = t.one("SELECT family_id FROM refresh_tokens WHERE token_hash = ?", (hash_token(refresh_token),))
            if row:
                t.execute("UPDATE refresh_tokens SET revoked_at = ? WHERE family_id = ? AND revoked_at IS NULL",
                          (self.clock.now_ms(), row["family_id"]))

    def authenticate(self, access_token: str) -> Actor:
        """Access token -> Actor, with the user's current role and status."""
        uid = self.signer.verify(access_token, self.clock.now_ms())
        u = self.get(uid)
        if u["status"] != "active":
            raise AccountDisabled("this account is disabled", reason=u["disabled_reason"])
        return self.actor_of(u)

    # ------------------------------------------------------------------ own account
    def change_password(self, actor: Actor, old: str, new: str) -> None:
        require(actor, "account.edit", actor.id)
        self._check_password(new)
        with self.db.tx() as t:
            u = self._user(t, actor.id)
            if u["password_set"] and not verify_password(old, u["password_hash"]):
                raise AuthError("wrong password")
            t.execute("UPDATE users SET password_hash = ?, password_set = 1 WHERE id = ?",
                      (hash_password(new, n=self.scrypt_n), actor.id))
            t.execute("UPDATE refresh_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                      (self.clock.now_ms(), actor.id))
            self.audit.record(t, actor.id, "user.password", "user", actor.id)

    def linked_providers(self, actor: Actor) -> list:
        with self.db.read() as t:
            return [r["provider"] for r in t.all("SELECT provider FROM identities WHERE user_id = ? ORDER BY provider",
                                                 (actor.id,))]

    def update_profile(self, actor: Actor, display_name: str) -> dict:
        require(actor, "account.edit", actor.id)
        if not display_name.strip() or len(display_name) > 80:
            raise ValidationFailed("display name must be 1-80 characters")
        with self.db.tx() as t:
            t.execute("UPDATE users SET display_name = ? WHERE id = ?", (display_name.strip(), actor.id))
            return public(self._user(t, actor.id))

    # ------------------------------------------------------------------ administration
    def list_users(self, actor: Actor, *, search: str = "", status: str | None = None, role: str | None = None,
                   limit: int = 50, offset: int = 0) -> dict:
        require(actor, "users.read")
        q, p = " FROM users WHERE 1=1", []
        if search:
            q += " AND (LOWER(email) LIKE ? OR LOWER(display_name) LIKE ?)"      # case-insensitive on SQLite and PostgreSQL
            p += [f"%{search.lower()}%", f"%{search.lower()}%"]
        for col, v in (("status", status), ("role", role)):
            if v:
                q += f" AND {col} = ?"
                p.append(v)
        with self.db.read() as t:
            total = t.scalar("SELECT COUNT(*)" + q, p, default=0)
            rows = t.all("SELECT *" + q + " ORDER BY created_at DESC, id LIMIT ? OFFSET ?",
                         p + [min(limit, 200), offset])
        return {"total": total, "users": [public(r) for r in rows]}

    def get_user(self, actor: Actor, user_id: str) -> dict:
        require(actor, "users.read")
        return public(self.get(user_id))

    def _admin_change(self, actor, user_id, action, fn, **detail):
        require(actor, "users.manage")
        with self.db.tx() as t:
            u = self._user(t, user_id)
            if u is None:
                raise NotFound("no such user")
            fn(t, u)
            self.audit.record(t, actor.id, action, "user", user_id, **detail)
            return public(self._user(t, user_id))

    def disable(self, actor: Actor, user_id: str, reason: str = "") -> dict:
        def fn(t, u):
            if u["role"] == "admin" and u["status"] == "active" and self._active_admins(t) <= 1:
                raise Conflict("cannot disable the last active administrator")
            t.execute("UPDATE users SET status = 'disabled', disabled_reason = ? WHERE id = ?", (reason or None, u["id"]))
            t.execute("UPDATE refresh_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                      (self.clock.now_ms(), u["id"]))
        return self._admin_change(actor, user_id, "user.disable", fn, reason=reason)

    def enable(self, actor: Actor, user_id: str) -> dict:
        return self._admin_change(actor, user_id, "user.enable", lambda t, u: t.execute(
            "UPDATE users SET status = 'active', disabled_reason = NULL, failed_logins = 0, locked_until = 0 "
            "WHERE id = ?", (u["id"],)))

    def set_role(self, actor: Actor, user_id: str, role: str) -> dict:
        if role not in ROLES:
            raise ValidationFailed(f"unknown role {role}")

        def fn(t, u):
            if u["role"] == "admin" and role != "admin" and u["status"] == "active" and self._active_admins(t) <= 1:
                raise Conflict("cannot demote the last active administrator")
            t.execute("UPDATE users SET role = ? WHERE id = ?", (role, u["id"]))
        return self._admin_change(actor, user_id, "user.role", fn, role=role)

    def set_plan(self, actor: Actor, user_id: str, plan: str) -> dict:
        def fn(t, u):
            if t.one("SELECT name FROM plans WHERE name = ?", (plan,)) is None:
                raise ValidationFailed(f"unknown plan {plan}")
            t.execute("UPDATE users SET plan = ? WHERE id = ?", (plan, u["id"]))
        return self._admin_change(actor, user_id, "user.plan", fn, plan=plan)

    def reset_password(self, actor: Actor, user_id: str, new_password: str) -> dict:
        self._check_password(new_password)

        def fn(t, u):
            t.execute("UPDATE users SET password_hash = ?, failed_logins = 0, locked_until = 0 WHERE id = ?",
                      (hash_password(new_password, n=self.scrypt_n), u["id"]))
            t.execute("UPDATE refresh_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                      (self.clock.now_ms(), u["id"]))
        return self._admin_change(actor, user_id, "user.password_reset", fn)
