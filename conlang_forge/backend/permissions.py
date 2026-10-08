"""Roles, permissions and the one place that decides "may this person do this?".

A permission is `resource.action:scope` where scope is `own` (resources they own) or `any`.
Roles only collect permissions; they never appear in business code.
"""
from __future__ import annotations

from dataclasses import dataclass

from .errors import AccountDisabled, PermissionDenied

USER_PERMS = {
    "conlang.create:own", "conlang.read:own", "conlang.edit:own", "conlang.delete:own",
    "conlang.translate:own",          # translation uses the language model
    "conlang.analyze:own",            # exemplar analysis uses the language model
    "conlang.polish:own",             # grammar-book prose polish uses the language model
    "usage.read:own",
    "account.edit:own",
}
ADMIN_PERMS = USER_PERMS | {
    "conlang.read:any",               # browse any user's conlangs (read only)
    "users.read:any", "users.manage:any",
    "limits.manage:any", "usage.read:any",
    "audit.read:any", "settings.manage:any",
    "llm.test:any",                   # try a model call from the admin area
}
ROLES = {"user": USER_PERMS, "admin": ADMIN_PERMS}


@dataclass(frozen=True)
class Actor:
    """Who is acting. Built from the database row on every request."""
    id: str
    role: str
    status: str
    email: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def can(actor: Actor, permission: str, owner_id: str | None = None) -> bool:
    """`permission` is "resource.action" (no scope). Allowed with the :any scope, or the :own scope on one's own resource."""
    if actor.status != "active":
        return False
    perms = ROLES.get(actor.role, set())
    if f"{permission}:any" in perms:
        return True
    return f"{permission}:own" in perms and owner_id is not None and owner_id == actor.id


def require(actor: Actor, permission: str, owner_id: str | None = None) -> None:
    if actor.status != "active":
        raise AccountDisabled("this account is disabled")
    if not can(actor, permission, owner_id):
        raise PermissionDenied(f"not allowed: {permission}", permission=permission)
