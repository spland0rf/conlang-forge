"""A tiny synchronous test client for ASGI apps (Starlette's own TestClient needs httpx, which may be missing)."""
import asyncio
import json
from urllib.parse import urlencode, urlsplit


class Response:
    def __init__(self, status, headers, body):
        self.status_code, self.headers, self.content = status, headers, body

    @property
    def text(self):
        return self.content.decode("utf-8")

    def json(self):
        return json.loads(self.content)


class Client:
    def __init__(self, app):
        self.app = app
        self.token = None

    def request(self, method, url, json_body=None, headers=None, token="auto"):
        parts = urlsplit(url)
        hdrs = {"host": "testserver", **(headers or {})}
        tok = self.token if token == "auto" else token
        if tok:
            hdrs["authorization"] = f"Bearer {tok}"
        body = b""
        if json_body is not None:
            body = json.dumps(json_body).encode()
            hdrs["content-type"] = "application/json"
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
                 "scheme": "http", "path": parts.path, "raw_path": parts.path.encode(),
                 "query_string": parts.query.encode(), "root_path": "", "client": ("127.0.0.1", 1),
                 "server": ("testserver", 80),
                 "headers": [(k.lower().encode(), v.encode()) for k, v in hdrs.items()]}
        out = {"status": 0, "headers": {}, "body": b""}

        async def run():
            sent = False

            async def receive():
                nonlocal sent
                if not sent:
                    sent = True
                    return {"type": "http.request", "body": body, "more_body": False}
                await asyncio.sleep(3600)

            async def send(msg):
                if msg["type"] == "http.response.start":
                    out["status"] = msg["status"]
                    out["headers"] = {k.decode(): v.decode() for k, v in msg["headers"]}
                elif msg["type"] == "http.response.body":
                    out["body"] += msg.get("body", b"")
            await self.app(scope, receive, send)
        asyncio.run(run())
        return Response(out["status"], out["headers"], out["body"])

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, json=None, **kw):
        return self.request("POST", url, json_body=json, **kw)

    def patch(self, url, json=None, **kw):
        return self.request("PATCH", url, json_body=json, **kw)

    def put(self, url, json=None, **kw):
        return self.request("PUT", url, json_body=json, **kw)

    def delete(self, url, **kw):
        return self.request("DELETE", url, **kw)
