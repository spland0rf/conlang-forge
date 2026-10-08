"""Model providers. A provider turns an LLMRequest into an LLMResponse, or raises ProviderError.

* AnthropicProvider talks to the Messages API over HTTPS (standard library only, so there is no SDK dependency).
  Its transport is injectable, which is how the tests run without a network.
* FakeProvider answers deterministically and can be scripted to fail: used by tests and the local demo.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..errors import ProviderError
from .types import LLMRequest, LLMResponse, Usage

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def urllib_transport(url, headers, body: bytes, timeout: float):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ProviderError(f"network error: {e}", retryable=True) from e


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str | None = None, *, transport=urllib_transport, timeout: float = 60.0,
                 url: str = API_URL):
        self._key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._key:
            raise ValueError("no Anthropic API key (set ANTHROPIC_API_KEY)")
        self.transport, self.timeout, self.url = transport, timeout, url

    def complete(self, req: LLMRequest) -> LLMResponse:
        body = {"model": req.model, "max_tokens": req.max_tokens, "temperature": req.temperature,
                "messages": [{"role": m.role, "content": m.content} for m in req.messages]}
        if req.system:
            body["system"] = ([{"type": "text", "text": req.system, "cache_control": {"type": "ephemeral"}}]
                              if req.cache_system else req.system)
        headers = {"content-type": "application/json", "x-api-key": self._key, "anthropic-version": API_VERSION}
        status, hdrs, raw = self.transport(self.url, headers, json.dumps(body).encode(), self.timeout)
        if status != 200:
            retry_after = None
            try:
                retry_after = float({k.lower(): v for k, v in hdrs.items()}.get("retry-after", ""))
            except ValueError:
                pass
            try:
                msg = json.loads(raw).get("error", {}).get("message", "")
            except Exception:
                msg = ""
            retryable = status in (408, 409, 429, 500, 502, 503, 504, 529)
            raise ProviderError(f"provider returned {status}: {msg}"[:300], retryable=retryable, http_status=status,
                                retry_after=retry_after)
        try:
            data = json.loads(raw)
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
            u = data.get("usage", {})
            usage = Usage(u.get("input_tokens", 0), u.get("output_tokens", 0),
                          u.get("cache_creation_input_tokens", 0) or 0, u.get("cache_read_input_tokens", 0) or 0)
        except (KeyError, ValueError, TypeError) as e:
            raise ProviderError("unreadable response from provider", retryable=False) from e
        return LLMResponse(text, usage, data.get("model", req.model), data.get("stop_reason", ""), data.get("id", ""))


class FakeProvider:
    """Deterministic stand-in. `script` is a list of exceptions or strings consumed one per call (then the default
    echo answer). Token counts follow the text length, so quota behaviour is realistic."""
    name = "fake"

    def __init__(self, script=None, *, reply=None):
        self.script, self.reply, self.calls = list(script or []), reply, []

    def complete(self, req: LLMRequest) -> LLMResponse:
        self.calls.append(req)
        if self.script:
            step = self.script.pop(0)
            if isinstance(step, Exception):
                raise step
            text = step
        else:
            last = req.messages[-1].content if req.messages else ""
            text = self.reply(req) if self.reply else f"[{req.model}] " + last[:200]
        inp = max(1, (req.chars + 2) // 3)
        out = min(req.max_tokens, max(1, (len(text) + 2) // 3))
        return LLMResponse(text, Usage(inp, out), req.model, "end_turn", f"fake-{len(self.calls)}")


class DemoProvider(FakeProvider):
    """Offline stand-in used by `serve --demo`: no model is called. It "simplifies" English by returning it unchanged (the
    shallow parser then does its best) and "smooths" by returning the literal reading, so the whole flow can be tried."""
    name = "demo"

    def __init__(self):
        super().__init__(reply=self._reply)

    @staticmethod
    def _reply(req: LLMRequest) -> str:
        msgs = [m.content for m in req.messages]
        if req.system.startswith("You rewrite English"):
            if len(msgs) >= 3:                       # a repair round: keep the previous answer
                return msgs[-2]
            return msgs[-1]
        if req.system.startswith("You turn a machine"):
            lits = [l.split("literal:", 1)[1].strip() for l in msgs[-1].split("\n") if "literal:" in l]
            return "\n".join(lits)
        return "[demo] " + (msgs[-1][:200] if msgs else "")
