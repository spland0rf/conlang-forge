// Sign in with Google from the app: open the server's /api/auth/google/app/start page in the phone's browser,
// get a short-lived grant back through the app link, and trade it (plus our secret PKCE verifier) for a session.
// Pure logic with injected phone pieces, so it is tested with plain Node.
import type { Api } from "./api";
import type { Session } from "./types";

export type AuthBrowserResult = { type: string; url?: string };
export interface GoogleDeps {
  api: Api;
  redirectUri: string;                                           // where the browser sends us back (the app link)
  openAuth(startUrl: string, redirectUri: string): Promise<AuthBrowserResult>;
  randomVerifier(): Promise<string>;
  sha256Base64Url(text: string): Promise<string>;
}

export function buildStartUrl(baseUrl: string, redirectUri: string, challenge: string): string {
  return `${baseUrl}/api/auth/google/app/start?redirect_uri=${encodeURIComponent(redirectUri)}&challenge=${encodeURIComponent(challenge)}`;
}

/** Reads ?grant= or ?error= from the app link the browser returned. */
export function parseResult(url: string): { grant?: string; error?: string } {
  const q = url.split("#")[0].split("?")[1] || "";
  const out: Record<string, string> = {};
  for (const part of q.split("&")) {
    if (!part) continue;
    const [k, v = ""] = part.split("=");
    out[decodeURIComponent(k)] = decodeURIComponent(v.replace(/\+/g, " "));
  }
  return { grant: out.grant, error: out.error };
}

/** Returns a session, or null when the person closed the browser. Throws an Error with a readable message on failure. */
export async function googleSignIn(d: GoogleDeps): Promise<Session | null> {
  const verifier = await d.randomVerifier();
  const challenge = await d.sha256Base64Url(verifier);
  const res = await d.openAuth(buildStartUrl(d.api.baseUrl, d.redirectUri, challenge), d.redirectUri);
  if (res.type !== "success" || !res.url) return null;
  const { grant, error } = parseResult(res.url);
  if (error) throw new Error(error);
  if (!grant) throw new Error("Google sign-in did not finish. Try again.");
  return d.api.post<Session>("/api/auth/google/app/exchange", { grant, verifier });
}
