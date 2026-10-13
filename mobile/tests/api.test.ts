// Run with: npx tsx tests/api.test.ts   (plain Node; no React Native needed)
import assert from "node:assert/strict";
import { ApiError, createApi, memoryStore, normalizeBaseUrl, type FetchLike } from "../src/api";
import { errorText, fmtTokens, tokenCount } from "../src/format";
import { checkEmail, checkNewPassword } from "../src/validate";

type Call = { url: string; method: string; auth?: string; body?: any };
function server(handler: (c: Call) => { status: number; body?: any }) {
  const calls: Call[] = [];
  const f: FetchLike = async (url, init) => {
    const c: Call = { url, method: init.method, auth: init.headers?.authorization, body: init.body ? JSON.parse(init.body) : undefined };
    calls.push(c);
    const r = handler(c);
    return { ok: r.status < 400, status: r.status, json: async () => r.body ?? {}, text: async () => JSON.stringify(r.body ?? {}) };
  };
  return { f, calls };
}
const tests: [string, () => Promise<void>][] = [];
const test = (n: string, fn: () => Promise<void>) => tests.push([n, fn]);

test("normalizeBaseUrl", async () => {
  assert.equal(normalizeBaseUrl(" www.x.com/conlang/ "), "https://www.x.com/conlang");
  assert.equal(normalizeBaseUrl("http://10.0.0.5:8000/"), "http://10.0.0.5:8000");
});

test("sends the bearer token and JSON body", async () => {
  const s = server(() => ({ status: 200, body: { ok: 1 } }));
  const api = createApi({ baseUrl: "https://h/conlang", store: memoryStore({ access_token: "A", refresh_token: "R" }), fetch: s.f });
  assert.deepEqual(await api.post("/api/x", { a: 1 }), { ok: 1 });
  assert.equal(s.calls[0].url, "https://h/conlang/api/x");
  assert.equal(s.calls[0].auth, "Bearer A");
  assert.deepEqual(s.calls[0].body, { a: 1 });
});

test("401 refreshes once and retries with the new token", async () => {
  const store = memoryStore({ access_token: "old", refresh_token: "R1" });
  const s = server((c) => {
    if (c.url.endsWith("/api/auth/refresh")) return { status: 200, body: { access_token: "new", refresh_token: "R2" } };
    return c.auth === "Bearer new" ? { status: 200, body: { id: "u" } } : { status: 401, body: { error: "unauthorized" } };
  });
  const api = createApi({ baseUrl: "https://h", store, fetch: s.f });
  assert.deepEqual(await api.get("/api/me"), { id: "u" });
  assert.deepEqual(await store.load(), { access_token: "new", refresh_token: "R2" });
  assert.equal(s.calls.filter((c) => c.url.endsWith("/refresh")).length, 1);
});

test("concurrent 401s share one refresh", async () => {
  const store = memoryStore({ access_token: "old", refresh_token: "R1" });
  const s = server((c) => {
    if (c.url.endsWith("/api/auth/refresh")) return { status: 200, body: { access_token: "new", refresh_token: "R2" } };
    return c.auth === "Bearer new" ? { status: 200, body: {} } : { status: 401, body: {} };
  });
  const api = createApi({ baseUrl: "https://h", store, fetch: s.f });
  await Promise.all([api.get("/api/a"), api.get("/api/b"), api.get("/api/c")]);
  assert.equal(s.calls.filter((c) => c.url.endsWith("/refresh")).length, 1);
});

test("failed refresh clears the session and signals sign-out", async () => {
  const store = memoryStore({ access_token: "old", refresh_token: "R1" });
  let out = 0;
  const s = server((c) => (c.url.endsWith("/refresh") ? { status: 401, body: {} } : { status: 401, body: { error: "unauthorized" } }));
  const api = createApi({ baseUrl: "https://h", store, fetch: s.f, onSignedOut: () => out++ });
  await assert.rejects(api.get("/api/me"), (e: any) => e instanceof ApiError && e.status === 401);
  assert.equal(await store.load(), null);
  assert.equal(out, 1);
});

test("auth calls never trigger refresh or sign-out (wrong password stays a plain error)", async () => {
  const store = memoryStore({ access_token: "a", refresh_token: "r" });
  let out = 0;
  const s = server(() => ({ status: 401, body: { error: "invalid_credentials", message: "Wrong email or password." } }));
  const api = createApi({ baseUrl: "https://h", store, fetch: s.f, onSignedOut: () => out++ });
  await assert.rejects(api.post("/api/auth/login", {}), (e: any) => e.message === "Wrong email or password." && e.code === "invalid_credentials");
  assert.equal(s.calls.length, 1); assert.equal(out, 0); assert.notEqual(await store.load(), null);
});

test("offline during refresh keeps the session", async () => {
  const store = memoryStore({ access_token: "old", refresh_token: "R" });
  let n = 0;
  const f: FetchLike = async (url) => {
    if (url.endsWith("/refresh")) throw new TypeError("Network request failed");
    n++; return { ok: false, status: 401, json: async () => ({}), text: async () => "" };
  };
  const api = createApi({ baseUrl: "https://h", store, fetch: f });
  await assert.rejects(api.get("/api/me"));
  assert.notEqual(await store.load(), null);
});

test("unverified email arrives as a coded error", async () => {
  const s = server(() => ({ status: 403, body: { error: "email_not_verified", message: "Confirm your email address before signing in." } }));
  const api = createApi({ baseUrl: "https://h", store: memoryStore(), fetch: s.f });
  await assert.rejects(api.post("/api/auth/login", {}), (e: any) => e.code === "email_not_verified" && e.status === 403);
});

test("errorText", async () => {
  assert.equal(errorText(new TypeError("x")), "Could not reach the server. Check your connection and the server address.");
  assert.equal(errorText(new ApiError(400, { message: "bad" })), "bad");
  const t = errorText(new ApiError(429, { message: "Daily limit reached.", resets_at: Date.now() + 5 * 60000 }));
  assert.match(t, /Try again in about 5 minutes/);
});

test("tokens + validation", async () => {
  assert.equal(tokenCount({ input: 100, output: 50, cache_read: 100 }), 160);
  assert.equal(fmtTokens(1500), "1.5k"); assert.equal(fmtTokens(20000), "20k"); assert.equal(fmtTokens(12), "12");
  assert.equal(checkEmail("a@b.co"), null); assert.notEqual(checkEmail("nope"), null);
  assert.equal(checkNewPassword("1234567890"), null); assert.notEqual(checkNewPassword("short"), null);
});

(async () => {
  let failed = 0;
  for (const [n, fn] of tests) {
    try { await fn(); console.log("ok  ", n); } catch (e) { failed++; console.log("FAIL", n, "\n", e); }
  }
  console.log(failed ? `${failed} failed` : `all ${tests.length} passed`);
  process.exit(failed ? 1 : 0);
})();
