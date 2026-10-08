"""Run the website and API locally:  python -m conlang_forge serve

First run: creates the database, a signing secret (saved beside it, owner-read-only) and, if there are no users,
an administrator. Set CONLANG_FORGE_ADMIN_EMAIL / CONLANG_FORGE_ADMIN_PASSWORD to choose them; otherwise a random
password is printed once.
Optional: ANTHROPIC_API_KEY (model calls), GOOGLE_CLIENT_ID (Sign in with Google).
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path


def is_dsn(db: str) -> bool:
    return str(db).startswith(("postgres://", "postgresql://"))


def load_secret(db_path: Path) -> str:
    env = os.environ.get("CONLANG_FORGE_SECRET")
    if env:
        return env
    if is_dsn(str(db_path)):
        raise SystemExit("With a PostgreSQL database, set CONLANG_FORGE_SECRET (a long random string used to sign "
                         "sign-in tokens). Make one with: python -c \"import secrets; print(secrets.token_hex(32))\"")
    f = db_path.with_suffix(".secret")
    if not f.exists():
        f.write_text(secrets.token_hex(32))
        f.chmod(0o600)
    return f.read_text().strip()


def seed_demo(be):
    """DEMO ONLY: a few sample users and 30 days of invented model usage, so the admin charts have something to show.
    The calls are fake rows written straight into the log; no model was called."""
    import random

    from .clock import DAY_MS, new_id
    rnd = random.Random(7)
    with be.db.read() as t:
        if t.scalar("SELECT COUNT(*) FROM users", default=0) > 1:
            return
    people = [("rin@example.test", "Rin Okafor"), ("bram@example.test", "Bram Eliasson"), ("sol@example.test", "Sol Marchetti"),
              ("wren@example.test", "Wren Adeyemi")]
    ids = [be.accounts.register(e, "Demo-Password-1", n)["id"] for e, n in people]
    now = be.clock.now_ms()
    purposes = [("translate.reduce", "claude-haiku-4-5-20251001", 900), ("translate.smooth", "claude-haiku-4-5-20251001", 700),
                ("book.polish", "claude-sonnet-5-5", 2600), ("exemplar.analyze", "claude-sonnet-5-5", 3400)]
    with be.db.tx() as t:
        for d in range(30, -1, -1):
            for uid, weight in zip(ids, (1.0, 0.6, 0.3, 0.1)):
                for _ in range(int(rnd.random() * 9 * weight * (1 + (30 - d) / 25))):
                    purpose, model, size = rnd.choice(purposes)
                    inp, out = int(size * rnd.uniform(.6, 1.3)), int(size * rnd.uniform(.2, .6))
                    price = (1.0, 5.0) if "haiku" in model else (3.0, 15.0)
                    ts = now - d * DAY_MS - rnd.randrange(0, DAY_MS // 2)
                    t.execute("INSERT INTO llm_calls (id, user_id, purpose, provider, model, status, input_tokens, output_tokens, "
                              "quota_tokens, cost_micro_usd, latency_ms, attempts, request_chars, response_chars, created_at) "
                              "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (new_id(), uid, purpose, "demo", model, "ok" if rnd.random() > .03 else "error", inp, out, inp + out,
                               round(inp * price[0] + out * price[1]), rnd.randrange(600, 4000), 1, inp * 3, out * 3, ts))


def build_backend(db: str, data_dir: str, demo: bool = False):
    from .app import Backend, Config
    secret = load_secret(db if is_dsn(db) else Path(db))
    provider = None
    if demo:
        from .llm.providers import DemoProvider
        provider = DemoProvider()
    be = Backend(Config(database=db, signing_secret=secret, data_dir=data_dir), provider=provider)
    with be.db.read() as t:
        has_admin = t.scalar("SELECT COUNT(*) FROM users WHERE role = 'admin'", default=0)
    if not has_admin:
        email = os.environ.get("CONLANG_FORGE_ADMIN_EMAIL", "admin@localhost.test")
        pw = os.environ.get("CONLANG_FORGE_ADMIN_PASSWORD")
        shown = False
        if not pw:
            pw, shown = "Admin-" + secrets.token_urlsafe(9) + "7a", True
        be.accounts.bootstrap_admin(email, pw, "Admin")
        print(f"\n  Created the administrator account:\n    email:    {email}\n"
              f"    password: {pw if shown else '(from CONLANG_FORGE_ADMIN_PASSWORD)'}\n")
    if demo:
        seed_demo(be)
    return be


def run(db="conlang_forge.db", data_dir=None, host="127.0.0.1", port=8000, demo=False):
    import uvicorn

    from .api import create_app
    data_dir = data_dir or str(Path(__file__).resolve().parents[2] / "data")
    be = build_backend(db, data_dir, demo)
    if demo:
        print('  DEMO MODE: sample users and invented usage numbers; the model is a stand-in: it passes English through unchanged instead of simplifying it.')
    print(f"  Conlang Forge is running at http://{host}:{port}")
    print(f"  Model calls: {'on' if be.llm else 'off (set ANTHROPIC_API_KEY to enable)'}; "
          f"Google sign-in: {'on' if be.google else 'off (set GOOGLE_CLIENT_ID to enable)'}\n")
    uvicorn.run(create_app(be), host=host, port=port, log_level="warning")
