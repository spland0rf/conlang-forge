// Talking to the server: bearer tokens, one automatic refresh on 401, readable errors.
// Port of the website's api.js. Nothing here depends on React Native, so it is unit-tested with plain Node.
import type { Session } from "./types";

export class ApiError extends Error {
  status: number; code?: string; detail: Record<string, any>;
  constructor(status: number, body: Record<string, any>) {
    super(body.message || body.error || `Request failed (${status})`);
    this.name = "ApiError"; this.status = status; this.code = body.error; this.detail = body;
  }
}

/** Where the session is kept. The app passes secure storage; tests pass an in-memory one. */
export interface SessionStore {
  load(): Promise<Session | null>;
  save(s: Session): Promise<void>;
  clear(): Promise<void>;
}

export function memoryStore(initial: Session | null = null): SessionStore {
  let cur = initial;
  return { load: async () => cur, save: async (s) => { cur = { access_token: s.access_token, refresh_token: s.refresh_token }; }, clear: async () => { cur = null; } };
}

type Resp = { ok: boolean; status: number; json(): Promise<any>; text(): Promise<string> };
export type FetchLike = (url: string, init?: any) => Promise<Resp>;

export interface ApiOptions {
  baseUrl: string;
  store: SessionStore;
  fetch?: FetchLike;
  /** Called when the server says the session is over and a refresh did not help. */
  onSignedOut?: () => void;
}

export function normalizeBaseUrl(raw: string): string {
  let u = raw.trim().replace(/\/+$/, "");
  if (u && !/^https?:\/\//i.test(u)) u = "https://" + u;
  return u;
}

export function createApi(opts: ApiOptions) {
  const doFetch: FetchLike = opts.fetch || ((url, init) => fetch(url, init) as any);
  let baseUrl = normalizeBaseUrl(opts.baseUrl);
  let refreshing: Promise<"ok" | "rejected" | "offline"> | null = null;

  async function refresh(): Promise<"ok" | "rejected" | "offline"> {
    const s = await opts.store.load();
    if (!s) return "rejected";
    refreshing = refreshing || (async () => {
      try {
        const r = await doFetch(baseUrl + "/api/auth/refresh", {
          method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ refresh_token: s.refresh_token }),
        });
        if (!r.ok) { await opts.store.clear(); return "rejected"; }
        await opts.store.save(await r.json());
        return "ok";
      } catch { return "offline"; }          // offline: keep the session, the caller sees the failed request
      finally { refreshing = null; }
    })();
    return refreshing;
  }

  async function send(method: string, path: string, body?: unknown, retry = true): Promise<Resp> {
    const s = await opts.store.load();
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["content-type"] = "application/json";
    if (s) headers.authorization = "Bearer " + s.access_token;
    const r = await doFetch(baseUrl + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    const isAuthCall = path.startsWith("/api/auth/");
    if (r.status === 401 && retry && s && !isAuthCall) {
      const outcome = await refresh();
      if (outcome === "ok") return send(method, path, body, false);
      if (outcome === "rejected") { await opts.store.clear(); opts.onSignedOut?.(); }
      return r;                                    // offline: keep the session, report the failed request
    }
    if (r.status === 401 && s && !isAuthCall) { await opts.store.clear(); opts.onSignedOut?.(); }
    return r;
  }

  async function api<T = any>(method: string, path: string, body?: unknown): Promise<T> {
    const r = await send(method, path, body);
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new ApiError(r.status, data || {});
    return data as T;
  }

  return {
    get baseUrl() { return baseUrl; },
    setBaseUrl(u: string) { baseUrl = normalizeBaseUrl(u); },
    api,
    get: <T = any>(p: string) => api<T>("GET", p),
    post: <T = any>(p: string, b: unknown = {}) => api<T>("POST", p, b),
    patch: <T = any>(p: string, b: unknown) => api<T>("PATCH", p, b),
    put: <T = any>(p: string, b: unknown) => api<T>("PUT", p, b),
    del: <T = any>(p: string) => api<T>("DELETE", p),
    async text(path: string): Promise<string> {
      const r = await send("GET", path);
      if (!r.ok) throw new ApiError(r.status, await r.json().catch(() => ({})));
      return r.text();
    },
  };
}
export type Api = ReturnType<typeof createApi>;
