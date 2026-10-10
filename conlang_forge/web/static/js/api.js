// Talking to the server: tokens, automatic refresh, errors.
const KEY = "cf.session";

export class ApiError extends Error {
  constructor(status, body) {
    super(body.message || body.error || `Request failed (${status})`);
    this.status = status; this.code = body.error; this.detail = body;
  }
}

// The app may be served from a sub-path (https://example.com/conlang/): every request goes to that same prefix.
// "" when it is served from the root.
export const BASE = new URL(".", document.baseURI).pathname.replace(/\/$/, "");

export const session = {
  get() { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } },
  set(s) { try { localStorage.setItem(KEY, JSON.stringify({ access_token: s.access_token, refresh_token: s.refresh_token })); } catch {} },
  clear() { try { localStorage.removeItem(KEY); } catch {} },
};

let refreshing = null;
async function refresh() {
  const s = session.get();
  if (!s) return false;
  refreshing = refreshing || fetch(BASE + "/api/auth/refresh", {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ refresh_token: s.refresh_token }),
  }).then(async (r) => {
    if (!r.ok) { session.clear(); return false; }
    session.set(await r.json()); return true;
  }).catch(() => false).finally(() => { refreshing = null; });
  return refreshing;
}

async function send(method, path, body, retry = true) {
  const s = session.get();
  const headers = {};
  if (body !== undefined) headers["content-type"] = "application/json";
  if (s) headers.authorization = "Bearer " + s.access_token;
  const r = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  if (r.status === 401 && retry && s && !path.startsWith("/api/auth/") && (await refresh())) return send(method, path, body, false);
  if (r.status === 401 && s && !path.startsWith("/api/auth/")) { session.clear(); window.dispatchEvent(new Event("cf:signedout")); }
  return r;
}

export async function api(method, path, body) {
  const r = await send(method, path, body);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, data);
  return data;
}
export async function text(path) {
  const r = await send("GET", path);
  if (!r.ok) throw new ApiError(r.status, await r.json().catch(() => ({})));
  return r.text();
}
export async function download(path, filename) {
  const r = await send("GET", path + (path.includes("?") ? "&" : "?") + "download=1");
  if (!r.ok) throw new ApiError(r.status, await r.json().catch(() => ({})));
  const url = URL.createObjectURL(await r.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
}
export const get = (p) => api("GET", p);
export const post = (p, b = {}) => api("POST", p, b);
export const patch = (p, b) => api("PATCH", p, b);
export const put = (p, b) => api("PUT", p, b);
export const del = (p) => api("DELETE", p);
