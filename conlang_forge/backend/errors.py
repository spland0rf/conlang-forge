"""Errors raised by the backend services.

Every error has a stable machine-readable `code` and the HTTP status the API layer should answer with, so the
web and mobile clients can react to a quota problem differently from a permission problem.
"""
from __future__ import annotations


class BackendError(Exception):
    code = "error"
    status = 400

    def __init__(self, message: str = "", **detail):
        super().__init__(message or self.code)
        self.message = message or self.code
        self.detail = detail

    def to_dict(self) -> dict:
        return {"error": self.code, "message": self.message, **self.detail}


class AuthError(BackendError):
    code, status = "auth_failed", 401


class AccountLocked(AuthError):
    code, status = "account_locked", 429


class AccountDisabled(BackendError):
    code, status = "account_disabled", 403


class PermissionDenied(BackendError):
    code, status = "permission_denied", 403


class NotFound(BackendError):
    code, status = "not_found", 404


class Conflict(BackendError):
    code, status = "conflict", 409


class ValidationFailed(BackendError):
    code, status = "invalid", 422


class QuotaExceeded(BackendError):
    """A token or conlang allowance is used up. `scope` says which one; `resets_at` is epoch ms (or None)."""
    code, status = "quota_exceeded", 429


class RateLimited(BackendError):
    code, status = "rate_limited", 429


class LLMDisabled(BackendError):
    code, status = "llm_disabled", 503


class ProviderError(BackendError):
    """The language-model provider failed. `retryable` tells the wrapper whether trying again can help."""
    code, status = "provider_error", 502

    def __init__(self, message: str = "", *, retryable: bool = False, http_status: int | None = None,
                 retry_after: float | None = None, **detail):
        super().__init__(message, retryable=retryable, http_status=http_status, **detail)
        self.retryable, self.http_status, self.retry_after = retryable, http_status, retry_after
