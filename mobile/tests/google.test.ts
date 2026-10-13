// Run with: npx tsx tests/google.test.ts
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createApi, memoryStore, type FetchLike } from "../src/api";
import { buildStartUrl, googleSignIn, parseResult } from "../src/googleAuth";

const sha = async (t: string) => createHash("sha256").update(t).digest("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const tests: [string, () => Promise<void>][] = [];
const test = (n: string, f: () => Promise<void>) => tests.push([n, f]);

function apiWith(handler: (url: string, body: any) => { status: number; body: any }) {
  const calls: { url: string; body: any }[] = [];
  const f: FetchLike = async (url, init) => {
    const body = init.body ? JSON.parse(init.body) : undefined; calls.push({ url, body });
    const r = handler(url, body);
    return { ok: r.status < 400, status: r.status, json: async () => r.body, text: async () => "" };
  };
  return { api: createApi({ baseUrl: "https://h/conlang", store: memoryStore(), fetch: f }), calls };
}

test("same challenge as the server computes (value taken from the Python implementation)", async () => {
  assert.equal(await sha("abc"), "ungWv48Bz-pBQUDeXa4iI7ADYaOWF3qctBD_YfIAFa0");
});

test("start url and result parsing", async () => {
  assert.equal(buildStartUrl("https://h/conlang", "exp://1.2.3.4:8081/--/auth", "CH"),
    "https://h/conlang/api/auth/google/app/start?redirect_uri=exp%3A%2F%2F1.2.3.4%3A8081%2F--%2Fauth&challenge=CH");
  assert.deepEqual(parseResult("conlangforge://auth?grant=a.b.c"), { grant: "a.b.c", error: undefined });
  assert.deepEqual(parseResult("exp://h/--/auth?error=Google+sign-in+was+cancelled.#x"), { grant: undefined, error: "Google sign-in was cancelled." });
});

test("happy path sends the grant with the verifier whose hash was in the start url", async () => {
  const { api, calls } = apiWith(() => ({ status: 200, body: { access_token: "A", refresh_token: "R" } }));
  let started = "";
  const s = await googleSignIn({ api, redirectUri: "conlangforge://auth", randomVerifier: async () => "VERIFIER", sha256Base64Url: sha,
    openAuth: async (url) => { started = url; return { type: "success", url: "conlangforge://auth?grant=G1" }; } });
  assert.deepEqual(s, { access_token: "A", refresh_token: "R" });
  assert.ok(started.includes("challenge=" + (await sha("VERIFIER"))));
  assert.deepEqual(calls[0], { url: "https://h/conlang/api/auth/google/app/exchange", body: { grant: "G1", verifier: "VERIFIER" } });
});

test("closing the browser returns null; an error in the link throws its message", async () => {
  const { api, calls } = apiWith(() => ({ status: 200, body: {} }));
  const base = { api, redirectUri: "r://x", randomVerifier: async () => "v", sha256Base64Url: sha };
  assert.equal(await googleSignIn({ ...base, openAuth: async () => ({ type: "cancel" }) }), null);
  await assert.rejects(googleSignIn({ ...base, openAuth: async () => ({ type: "success", url: "r://x?error=Google+sign-in+failed." }) }), /Google sign-in failed\./);
  await assert.rejects(googleSignIn({ ...base, openAuth: async () => ({ type: "success", url: "r://x" }) }), /did not finish/);
  assert.equal(calls.length, 0);
});

(async () => {
  let failed = 0;
  for (const [n, f] of tests) { try { await f(); console.log("ok  ", n); } catch (e) { failed++; console.log("FAIL", n, e); } }
  console.log(failed ? `${failed} failed` : `all ${tests.length} passed`); process.exit(failed ? 1 : 0);
})();
