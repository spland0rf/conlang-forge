import { ApiError } from "./api";
import type { Usage } from "./types";

/** A sentence a person can read, from whatever went wrong. */
export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    const resets = e.detail?.resets_at;
    if (resets && e.status === 429) {
      const mins = Math.max(1, Math.round((resets - Date.now()) / 60000));
      return `${e.message} Try again in about ${mins < 90 ? mins + " minutes" : Math.round(mins / 60) + " hours"}.`;
    }
    return e.message;
  }
  if (e instanceof TypeError) return "Could not reach the server. Check your connection and the server address.";
  return (e as Error)?.message || "Something went wrong.";
}

export function tokenCount(u: Usage): number {
  return u ? (u.input || 0) + (u.output || 0) + (u.cache_write || 0) + Math.round((u.cache_read || 0) / 10) : 0;
}
export function fmtTokens(n: number): string {
  return n >= 10000 ? Math.round(n / 1000) + "k" : n >= 1000 ? (n / 1000).toFixed(1) + "k" : String(n);
}

export const TYPES: Record<string, string> = {
  isolating: "Isolating", agglutinative: "Agglutinative", fusional: "Fusional", polysynthetic: "Polysynthetic",
};

export const nf = (n: number) => Math.round(n).toLocaleString();
/** Dollars from millionths of a dollar, as the website shows them. */
export function fmtUsd(micro: number): string { const d = micro / 1e6; return d < 0.01 && micro > 0 ? "<$0.01" : "$" + d.toFixed(d < 10 ? 2 : 0); }
export function ago(ms: number | null | undefined, now = Date.now()): string {
  if (!ms) return "never";
  const s = (now - ms) / 1000;
  if (s < 90) return "just now"; if (s < 5400) return Math.round(s / 60) + " min ago";
  if (s < 129600) return Math.round(s / 3600) + " h ago"; if (s < 86400 * 40) return Math.round(s / 86400) + " days ago";
  return new Date(ms).toLocaleDateString();
}
export const when = (ms: number | null | undefined) => (ms ? new Date(ms).toLocaleString() : "never");
/** Tokens as the admin pages show them (null means no limit). */
export const fmtLimitTokens = (n: number | null | undefined) => (n == null ? "no limit" : n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M" : n >= 1e4 ? Math.round(n / 1e3) + "k" : nf(n));
