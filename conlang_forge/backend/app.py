"""Wiring: one Backend object holds every service. The API layer, the command line and the tests all start here."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .accounts import AccountService
from .audit import Audit
from .clock import Clock
from .conlangs import ConlangService
from .db import Database
from .limits import LimitsService
from .llm.metered import MeteredLLM
from .quota import QuotaService
from .security import TokenSigner
from .settings import Settings
from .usage import UsageReports


@dataclass
class Config:
    database: str = "conlang_forge.db"           # a SQLite path (a Postgres DSN is used when it starts with postgres)
    signing_secret: str = field(default_factory=lambda: os.environ.get("CONLANG_FORGE_SECRET", ""))
    access_ttl_seconds: int = 900
    data_dir: str = ""
    scrypt_n: int = 2 ** 15
    model_overrides: dict = field(default_factory=dict)
    google_client_id: str = field(default_factory=lambda: os.environ.get("GOOGLE_CLIENT_ID", ""))
    public_url: str = field(default_factory=lambda: os.environ.get("PUBLIC_URL", ""))     # base of links in emails
    google_client_secret: str = field(default_factory=lambda: os.environ.get("GOOGLE_CLIENT_SECRET", ""))   # phone-app sign-in only


class Backend:
    def __init__(self, config: Config, *, provider=None, clock: Clock | None = None, generator=None, google_jwks=None, mailer=None, google_exchange=None):
        self.config, self.clock = config, clock or Clock()
        if config.database.startswith("postgres"):         # pragma: no cover
            self.db = Database.postgres(config.database)
        else:
            self.db = Database.sqlite(config.database)
        self.audit = Audit(self.db, self.clock)
        self.settings = Settings(self.db, self.clock, self.audit)
        self.limits = LimitsService(self.db, self.clock, self.audit)
        self.signer = TokenSigner(config.signing_secret, config.access_ttl_seconds)
        if mailer is None:
            from .mail import mailer_from_env
            mailer = mailer_from_env()
        self.mailer = mailer
        self.accounts = AccountService(self.db, self.clock, self.signer, self.audit, self.settings,
                                       scrypt_n=config.scrypt_n, mailer=mailer, public_url=config.public_url)
        self.quota = QuotaService(self.db, self.clock)
        if provider is None and os.environ.get("ANTHROPIC_API_KEY"):
            from .llm.providers import AnthropicProvider
            provider = AnthropicProvider()
        self.provider = provider
        if generator is None and config.data_dir:
            from .conlangs import engine_generator
            generator = engine_generator(config.data_dir)
        self.conlangs = ConlangService(self.db, self.clock, self.accounts, self.limits, self.audit, generator)
        self.llm = MeteredLLM(self.db, self.clock, self.accounts, self.limits, self.quota, self.settings,
                              provider, model_overrides=config.model_overrides) if provider else None
        from .translation import TranslationService
        self.translation = TranslationService(self.conlangs, self.llm)
        from .scripts import ScriptService
        self.scripts = ScriptService(self.db, self.clock, self.conlangs, self.translation, self.audit, self.llm)
        from .exemplars import ExemplarService
        self.exemplars = ExemplarService(self.conlangs, self.llm, self.db, self.clock)
        self.google = None
        if config.google_client_id:
            from .oidc import GOOGLE_JWKS_URL, GoogleVerifier, JwksCache
            cache = JwksCache(GOOGLE_JWKS_URL, google_jwks) if google_jwks else None     # google_jwks: url -> keys (tests)
            self.google = GoogleVerifier(config.google_client_id, cache)
        self.google_app = None
        if self.google is not None:
            from .google_app import GoogleAppFlow, exchange_code
            self.google_app = GoogleAppFlow(secret=config.signing_secret, verifier=self.google, client_id=config.google_client_id,
                                            client_secret=config.google_client_secret, public_url=config.public_url, clock=self.clock,
                                            exchange=google_exchange or exchange_code)
        self.usage = UsageReports(self.db, self.clock, self.limits, self.quota, self.accounts)

    def login_with_google_app(self, grant: str, verifier: str, user_agent: str = "") -> dict:
        from .errors import ValidationFailed
        if self.google_app is None or not self.google_app.enabled:
            raise ValidationFailed("Google sign-in for the app is not configured on this server")
        return self.accounts.login_with_identity(self.google_app.identity_for(grant, verifier), user_agent)

    def login_with_google(self, id_token: str, user_agent: str = "", nonce: str | None = None) -> dict:
        from .errors import ValidationFailed
        if self.google is None:
            raise ValidationFailed("Google sign-in is not configured on this server")
        ident = self.google.verify(id_token, self.clock.now_ms(), nonce)
        return self.accounts.login_with_identity(ident, user_agent)
