"""The HTTP API (Starlette). A thin layer: parse the request, call a service, return JSON.

All business rules live in the services, so the website, the phone apps and the tests behave the same.
Every endpoint except /api/config and /api/auth/* needs `Authorization: Bearer <access token>`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from ..spec import TYPOLOGIES, WORD_ORDERS
from .errors import AuthError, BackendError, NotFound, ValidationFailed
from .permissions import Actor, require
from .views import LanguageViews

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# The dials the website may pin when creating a language: key -> allowed values (None = free text)
DIALS = {
    "name": None,
    "morphology.typology": TYPOLOGIES,
    "syntax.word_order": WORD_ORDERS,
    "syntax.adjective_order": ["adjective-noun", "noun-adjective"],
    "phonology.stress": ["initial", "penultimate", "final", "none"],
    "morphology.numeral_base": [5, 8, 10, 12, 20],
}


def clean_pins(raw) -> dict:
    if raw in (None, ""):
        return {}
    if not isinstance(raw, dict):
        raise ValidationFailed("pins must be an object")
    out = {}
    for k, v in raw.items():
        if v in (None, ""):
            continue
        if k not in DIALS:
            raise ValidationFailed(f"unknown setting {k}")
        allowed = DIALS[k]
        if allowed is None:
            if not isinstance(v, str) or len(v.strip()) > 40 or not v.strip():
                raise ValidationFailed("name must be 1-40 characters")
            out[k] = v.strip()
        else:
            if v not in allowed:
                raise ValidationFailed(f"{k} must be one of {allowed}")
            out[k] = v
    return out


def script_of(request) -> str:
    """Spelling script asked for: plain English letters (default) or special letters. Only a view, never stored."""
    return request.query_params.get("script") or "plain"


def create_app(be, *, views: LanguageViews | None = None, serve_web: bool = True) -> Starlette:
    views = views or (LanguageViews(be.config.data_dir) if be.config.data_dir else None)

    # ---------------------------------------------------------------- plumbing
    def bearer(request: Request) -> str:
        h = request.headers.get("authorization", "")
        if not h.lower().startswith("bearer "):
            raise AuthError("sign in required")
        return h[7:].strip()

    async def body(request: Request) -> dict:
        if not (await request.body()):
            return {}
        try:
            data = await request.json()
        except ValueError:
            raise ValidationFailed("request body must be JSON")
        if not isinstance(data, dict):
            raise ValidationFailed("request body must be a JSON object")
        return data

    def api(fn, *, auth=True, raw=False):
        """Wrap a handler fn(actor, request, data) into an endpoint; services run in a worker thread."""
        async def endpoint(request: Request):
            try:
                data = await body(request) if request.method in ("POST", "PUT", "PATCH") else {}
                actor = await run_in_threadpool(lambda: be.accounts.authenticate(bearer(request))) if auth else None
                result = await run_in_threadpool(fn, actor, request, data)
                if isinstance(result, Response):
                    return result
                return JSONResponse(result if result is not None else {"ok": True})
            except BackendError as e:
                headers = {}
                if e.detail.get("resets_at"):
                    headers["retry-after"] = str(max(1, (int(e.detail["resets_at"]) - be.clock.now_ms()) // 1000))
                return JSONResponse(e.to_dict(), status_code=e.status, headers=headers)
        return endpoint

    def qint(request, name, default, lo=0, hi=10**16):
        try:
            return max(lo, min(hi, int(request.query_params.get(name, default))))
        except ValueError:
            raise ValidationFailed(f"{name} must be a number")

    def need(data, *keys):
        for k in keys:
            if k not in data or data[k] is None:
                raise ValidationFailed(f"missing {k}")
        return [data[k] for k in keys]

    def lang_and_key(actor, cid, script="plain"):
        summary = be.conlangs.summary(actor, cid)
        return summary, (cid, summary["updated_at"], script)

    # ---------------------------------------------------------------- public / auth
    def config(actor, request, data):
        return {"app": "Conlang Forge", "google_client_id": be.config.google_client_id or None,
                "registration_open": bool(be.settings.get("registration.open")),
                "model_available": be.llm is not None, "dials": DIALS}

    def register(actor, request, data):
        email, password = need(data, "email", "password")
        be.accounts.register(email, password, str(data.get("display_name", "")))
        return be.accounts.login(email, password, request.headers.get("user-agent", ""))

    def login(actor, request, data):
        email, password = need(data, "email", "password")
        return be.accounts.login(email, password, request.headers.get("user-agent", ""))

    def google(actor, request, data):
        (token,) = need(data, "credential")
        return be.login_with_google(token, request.headers.get("user-agent", ""), data.get("nonce"))

    def refresh(actor, request, data):
        (tok,) = need(data, "refresh_token")
        return be.accounts.refresh(tok, request.headers.get("user-agent", ""))

    def logout(actor, request, data):
        be.accounts.logout(str(data.get("refresh_token", "")))

    # ---------------------------------------------------------------- me
    def me(actor, request, data):
        u = be.accounts.get(actor.id)
        from .accounts import public
        out = public(u)
        out["providers"] = be.accounts.linked_providers(actor)
        out["usage"] = be.usage.my_usage(actor)
        out["conlang_count"] = len(be.conlangs.list_own(actor, limit=200))
        return out

    def update_me(actor, request, data):
        (name,) = need(data, "display_name")
        return be.accounts.update_profile(actor, str(name))

    def password(actor, request, data):
        be.accounts.change_password(actor, str(data.get("old_password", "")), str(data.get("new_password", "")))

    # ---------------------------------------------------------------- conlangs
    def list_conlangs(actor, request, data):
        return {"conlangs": be.conlangs.list_own(actor)}

    def create_conlang(actor, request, data):
        name = data.get("name")
        pins = clean_pins(data.get("pins"))
        if isinstance(name, str) and name.strip() and "name" not in pins:
            pins["name"] = clean_pins({"name": name})["name"]      # the language's own name is the one typed
        seed = data.get("seed")
        if seed in (None, ""):
            import secrets
            seed = secrets.randbelow(2 ** 31)
        if not isinstance(seed, int) or isinstance(seed, bool) or not (0 <= seed < 2 ** 31):
            raise ValidationFailed("seed must be a whole number from 0 to 2147483647")
        return be.conlangs.create(actor, str(name), seed=seed, pins=pins)

    def create_from_sample(actor, request, data):
        (texts,) = need(data, "texts")
        pins = clean_pins(data.get("pins"))
        name = data.get("name")
        if isinstance(name, str) and name.strip() and "name" not in pins:
            pins["name"] = clean_pins({"name": name})["name"]
        seed = data.get("seed")
        if seed in (None, ""):
            import secrets
            seed = secrets.randbelow(2 ** 31)
        if not isinstance(seed, int) or isinstance(seed, bool) or not (0 <= seed < 2 ** 31):
            raise ValidationFailed("seed must be a whole number from 0 to 2147483647")
        out = be.exemplars.create_from_sample(actor, texts, name=str(name or ""), seed=seed, pins=pins, use_model=bool(data.get("use_model", True)))
        return out

    def get_conlang(actor, request, data):
        cid = request.path_params["cid"]
        summary, key = lang_and_key(actor, cid, script_of(request))
        return {**summary, "profile": views.profile(be.conlangs.get_language(actor, cid, script_of(request)))}

    def rename_conlang(actor, request, data):
        (name,) = need(data, "name")
        return be.conlangs.rename(actor, request.path_params["cid"], str(name))

    def delete_conlang(actor, request, data):
        be.conlangs.delete(actor, request.path_params["cid"])

    def dictionary_json(actor, request, data):
        cid = request.path_params["cid"]
        summary, key = lang_and_key(actor, cid, script_of(request))
        return views.dictionary_json(key, be.conlangs.get_language(actor, cid, script_of(request)))

    def translate(actor, request, data):
        cid = request.path_params["cid"]
        (text,) = need(data, "text")
        direction = data.get("direction", "to")
        if direction == "to":
            return be.translation.to_language(actor, cid, text, mode=str(data.get("mode", "english")), script=str(data.get("script") or "plain"))
        if direction == "from":
            return be.translation.from_language(actor, cid, text, smooth=bool(data.get("smooth")))
        raise ValidationFailed("direction must be 'to' or 'from'")

    def get_settings(actor, request, data):
        return be.conlangs.settings(actor, request.path_params["cid"])

    def _edit_args(data):
        if not isinstance(data.get("set", {}), dict) or not isinstance(data.get("unpin", []), list):
            raise ValidationFailed("set must be an object and unpin a list")
        return dict(set=data.get("set") or {}, unpin=data.get("unpin") or [], tuning=data.get("tuning"))

    def preview_settings(actor, request, data):
        return be.conlangs.preview_settings(actor, request.path_params["cid"], **_edit_args(data))

    def apply_settings(actor, request, data):
        cid = request.path_params["cid"]
        mode = str(data.get("mode", "replace"))
        summary = be.conlangs.apply_settings(actor, cid, mode=mode, **_edit_args(data))
        return {**summary, "profile": views.profile(be.conlangs.get_language(actor, summary["id"]))}

    def exemplar_analyze(actor, request, data):
        (texts,) = need(data, "texts")
        return be.exemplars.analyze(actor, request.path_params["cid"], texts, use_model=bool(data.get("use_model", True)))

    def exemplar_save(actor, request, data):
        return {"texts": be.exemplars.save(actor, request.path_params["cid"], data.get("texts") or [])}

    def download(kind):
        def handler(actor, request, data):
            cid = request.path_params["cid"]
            summary, key = lang_and_key(actor, cid, script_of(request))
            lang = be.conlangs.get_language(actor, cid, script_of(request))
            import unicodedata
            ascii_name = unicodedata.normalize("NFKD", summary["name"]).encode("ascii", "ignore").decode()
            safe = "".join(c if c.isalnum() else "_" for c in ascii_name).strip("_") or "language"
            text, ctype, fname = {
                "dictionary.md": (views.dictionary_md, "text/markdown", f"{safe}_dictionary.md"),
                "dictionary.csv": (views.dictionary_csv, "text/csv", f"{safe}_dictionary.csv"),
                "grammar-book.md": (views.grammar_book, "text/markdown", f"{safe}_grammar_book.md"),
            }[kind]
            content = text(key, lang)
            disp = "attachment" if request.query_params.get("download") else "inline"
            return PlainTextResponse(content, media_type=f"{ctype}; charset=utf-8",
                                     headers={"content-disposition": f'{disp}; filename="{fname}"'})
        return handler

    # ---------------------------------------------------------------- admin
    def admin_users(actor, request, data):
        p = request.query_params
        return be.accounts.list_users(actor, search=p.get("q", ""), status=p.get("status") or None,
                                      role=p.get("role") or None, limit=qint(request, "limit", 50, 1, 200),
                                      offset=qint(request, "offset", 0))

    def admin_user(actor, request, data):
        uid = request.path_params["uid"]
        u = be.accounts.get_user(actor, uid)
        row = be.accounts.get(uid)
        require(actor, "limits.manage")
        return {**u, "limits": {"effective": be.limits.resolve(row).to_dict(), "overrides": be.limits.overrides(uid),
                                "plan": be.limits.plan(row["plan"]).to_dict()},
                "usage": be.quota.snapshot(uid, be.limits.resolve(row)),
                "conlangs": be.conlangs.list_all(actor, owner_id=uid)}

    def admin_user_patch(actor, request, data):
        uid = request.path_params["uid"]
        out = None
        if "status" in data:
            if data["status"] == "disabled":
                out = be.accounts.disable(actor, uid, str(data.get("reason", "")))
            elif data["status"] == "active":
                out = be.accounts.enable(actor, uid)
            else:
                raise ValidationFailed("status must be active or disabled")
        if "role" in data:
            out = be.accounts.set_role(actor, uid, str(data["role"]))
        if "plan" in data:
            out = be.accounts.set_plan(actor, uid, str(data["plan"]))
        if "new_password" in data:
            out = be.accounts.reset_password(actor, uid, str(data["new_password"]))
        if "limits" in data:
            if not isinstance(data["limits"], dict):
                raise ValidationFailed("limits must be an object")
            be.limits.set_user_overrides(actor, uid, **data["limits"])
        return out or be.accounts.get_user(actor, uid)

    def admin_plans(actor, request, data):
        require(actor, "limits.manage")
        return {"plans": be.limits.plans()}

    def admin_plan_put(actor, request, data):
        be.limits.set_plan_limits(actor, request.path_params["name"], **data)

    def window(request):
        end = qint(request, "end", be.clock.now_ms() + 1)
        start = qint(request, "start", end - 14 * 86_400_000)
        return start, end

    def usage_series(actor, request, data):
        start, end = window(request)
        p = request.query_params
        return be.usage.timeseries(actor, start_ms=start, end_ms=end, bucket=p.get("bucket", "day"),
                                   group_by=p.get("group_by", "none"), user_id=p.get("user_id") or None,
                                   purpose=p.get("purpose") or None)

    def usage_totals(actor, request, data):
        start, end = window(request)
        return be.usage.totals(actor, start_ms=start, end_ms=end, user_id=request.query_params.get("user_id") or None)

    def usage_top(actor, request, data):
        start, end = window(request)
        return {"users": be.usage.top_users(actor, start_ms=start, end_ms=end,
                                            metric=request.query_params.get("metric", "quota_tokens"),
                                            limit=qint(request, "limit", 10, 1, 100))}

    def usage_calls(actor, request, data):
        p = request.query_params
        return {"calls": be.usage.recent_calls(actor, user_id=p.get("user_id") or None, status=p.get("status") or None,
                                               purpose=p.get("purpose") or None,
                                               before_ms=qint(request, "before", 0) or None,
                                               limit=qint(request, "limit", 50, 1, 200))}

    def admin_audit(actor, request, data):
        require(actor, "audit.read")
        p = request.query_params
        return {"entries": be.audit.list(action=p.get("action") or None, target_id=p.get("target_id") or None,
                                          before=qint(request, "before", 0) or None, limit=qint(request, "limit", 100, 1, 500))}

    def admin_settings(actor, request, data):
        require(actor, "settings.manage")
        return be.settings.all()

    def admin_settings_put(actor, request, data):
        for k, v in data.items():
            be.settings.set(actor, k, v)
        return be.settings.all()

    def admin_conlangs(actor, request, data):
        return {"conlangs": be.conlangs.list_all(actor, owner_id=request.query_params.get("owner_id") or None,
                                                 limit=qint(request, "limit", 100, 1, 200))}

    def admin_conlang_view(actor, request, data):
        cid = request.path_params["cid"]
        summary, key = lang_and_key(actor, cid)
        return {**summary, "profile": views.profile(be.conlangs.get_language(actor, cid))}

    def llm_test(actor, request, data):
        require(actor, "llm.test")
        if be.llm is None:
            from .errors import LLMDisabled
            raise LLMDisabled("no model provider is configured (set ANTHROPIC_API_KEY)")
        (prompt,) = need(data, "prompt")
        r = be.llm.complete(actor, "admin.test", prompt=str(prompt), model=data.get("model") or None)
        return {"text": r.text, "model": r.model, "input_tokens": r.usage.input_tokens,
                "output_tokens": r.usage.output_tokens, "cost_micro_usd": r.cost_micro_usd}

    def health(actor, request, data):
        return {"ok": True, "time": be.clock.now_ms()}

    A = lambda fn, **kw: api(fn, **kw)
    routes = [
        Route("/api/health", A(health, auth=False)),
        Route("/api/config", A(config, auth=False)),
        Route("/api/auth/register", A(register, auth=False), methods=["POST"]),
        Route("/api/auth/login", A(login, auth=False), methods=["POST"]),
        Route("/api/auth/google", A(google, auth=False), methods=["POST"]),
        Route("/api/auth/refresh", A(refresh, auth=False), methods=["POST"]),
        Route("/api/auth/logout", A(logout, auth=False), methods=["POST"]),
        Route("/api/me", A(me), methods=["GET"]),
        Route("/api/me", A(update_me), methods=["PATCH"]),
        Route("/api/me/password", A(password), methods=["POST"]),
        Route("/api/conlangs", A(list_conlangs), methods=["GET"]),
        Route("/api/conlangs", A(create_conlang), methods=["POST"]),
        Route("/api/conlangs/{cid}", A(get_conlang), methods=["GET"]),
        Route("/api/conlangs/{cid}", A(rename_conlang), methods=["PATCH"]),
        Route("/api/conlangs/{cid}", A(delete_conlang), methods=["DELETE"]),
        Route("/api/conlangs/{cid}/translate", A(translate), methods=["POST"]),
        Route("/api/conlangs/from-sample", A(create_from_sample), methods=["POST"]),
        Route("/api/conlangs/{cid}/exemplars/analyze", A(exemplar_analyze), methods=["POST"]),
        Route("/api/conlangs/{cid}/exemplars", A(exemplar_save), methods=["PUT"]),
        Route("/api/conlangs/{cid}/settings", A(get_settings), methods=["GET"]),
        Route("/api/conlangs/{cid}/settings/preview", A(preview_settings), methods=["POST"]),
        Route("/api/conlangs/{cid}/settings/apply", A(apply_settings), methods=["POST"]),
        Route("/api/conlangs/{cid}/dictionary.json", A(dictionary_json)),
        Route("/api/conlangs/{cid}/dictionary.md", A(download("dictionary.md"))),
        Route("/api/conlangs/{cid}/dictionary.csv", A(download("dictionary.csv"))),
        Route("/api/conlangs/{cid}/grammar-book.md", A(download("grammar-book.md"))),
        Route("/api/admin/users", A(admin_users)),
        Route("/api/admin/users/{uid}", A(admin_user), methods=["GET"]),
        Route("/api/admin/users/{uid}", A(admin_user_patch), methods=["PATCH"]),
        Route("/api/admin/plans", A(admin_plans)),
        Route("/api/admin/plans/{name}", A(admin_plan_put), methods=["PUT"]),
        Route("/api/admin/usage/series", A(usage_series)),
        Route("/api/admin/usage/totals", A(usage_totals)),
        Route("/api/admin/usage/top-users", A(usage_top)),
        Route("/api/admin/usage/calls", A(usage_calls)),
        Route("/api/admin/audit", A(admin_audit)),
        Route("/api/admin/settings", A(admin_settings), methods=["GET"]),
        Route("/api/admin/settings", A(admin_settings_put), methods=["PUT"]),
        Route("/api/admin/conlangs", A(admin_conlangs)),
        Route("/api/admin/conlangs/{cid}", A(admin_conlang_view)),
        Route("/api/admin/llm-test", A(llm_test), methods=["POST"]),
    ]

    async def not_found(request):
        return JSONResponse({"error": "not_found", "message": "no such endpoint"}, status_code=404)

    routes.append(Route("/api/{rest:path}", not_found))
    if serve_web and WEB_DIR.exists():
        async def index(request):
            return FileResponse(WEB_DIR / "index.html", headers={"cache-control": "no-cache"})
        routes += [Mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static"),
                   Route("/{path:path}", index)]

    async def security_headers(request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("x-content-type-options", "nosniff")
        resp.headers.setdefault("referrer-policy", "same-origin")
        resp.headers.setdefault("x-frame-options", "DENY")
        if request.url.path.startswith("/api/"):
            resp.headers.setdefault("cache-control", "no-store")
        return resp

    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    app = Starlette(routes=routes, middleware=[Middleware(BaseHTTPMiddleware, dispatch=security_headers)])
    app.state.backend = be
    return app
