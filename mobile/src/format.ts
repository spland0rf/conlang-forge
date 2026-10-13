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
