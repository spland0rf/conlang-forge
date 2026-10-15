// What the administrator's screens compute: limits typed as text, usage buckets for the charts, and nice axis numbers.
// Plain TypeScript with no React Native, so it is unit-tested with Node. Mirrors the website's admin.js and charts.js.

export const DAY = 86400000;
export const PURPOSES = ["exemplar.analyze", "book.polish", "translate.reduce", "translate.smooth", "admin.test", "script.describe"];
/** Describing a script in words or by picture is one series in the charts. */
export const GROUP: Record<string, string> = { "script.describe_image": "script.describe" };
export const PURPOSE_LABEL: Record<string, string> = {
  "exemplar.analyze": "Analyse example text", "book.polish": "Polish grammar book", "translate.reduce": "Translate: simplify",
  "translate.smooth": "Translate: smooth", "admin.test": "Admin test", "script.describe": "Describe a script", "script.describe_image": "Script from picture",
};
export const LIMITS: [string, string][] = [["tokens_per_day", "Tokens per day"], ["tokens_per_month", "Tokens per month"],
  ["requests_per_minute", "Requests per minute"], ["max_conlangs", "Languages"], ["max_output_tokens", "Max reply length (tokens)"]];
/** The fixed colour order of the website's charts (light mode). Colour follows the purpose, never its rank. */
export const SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7a5fd6"];
export const purposeColor = (p: string) => SERIES_COLORS[Math.max(0, PURPOSES.indexOf(p)) % SERIES_COLORS.length];

/** A user's limit overrides, typed as text: blank uses the plan, a whole number overrides, "unlimited" removes the limit. */
export function parseUserLimits(texts: Record<string, string>): Record<string, number | null> {
  const out: Record<string, number | null> = {};
  for (const [k] of LIMITS) {
    const v = (texts[k] ?? "").trim().toLowerCase();
    const n = v === "" ? null : v === "unlimited" ? -1 : Number(v);
    if (n !== null && !Number.isInteger(n)) throw new Error("Limits must be whole numbers, or the word unlimited.");
    out[k] = n;
  }
  return out;
}
/** A plan's limits: blank means no limit. */
export function parsePlanLimits(texts: Record<string, string>): Record<string, number | null> {
  const out: Record<string, number | null> = {};
  for (const [k] of LIMITS) {
    const t = (texts[k] ?? "").trim();
    const n = t === "" ? null : Number(t);
    if (n !== null && !Number.isInteger(n)) throw new Error("Use whole numbers, or leave blank for no limit.");
    out[k] = n;
  }
  return out;
}
export const limitText = (v: number | null | undefined) => (v == null ? "" : String(v));
/** The spending cap: blank means none. */
export function parseCap(text: string): number | null {
  const t = text.trim();
  if (t && !/^\d+$/.test(t)) throw new Error("Use a whole number.");
  return t ? Number(t) : null;
}
export function parsePrices(text: string): Record<string, unknown> {
  try { const v = JSON.parse(text || "{}"); if (v && typeof v === "object" && !Array.isArray(v)) return v; } catch { /* fall through */ }
  throw new Error("That is not valid JSON.");
}

// ---- usage charts
export type SeriesRow = { bucket_start: number; grp: string; quota_tokens: number; cost_micro_usd: number };
export type Bucket = { t: number; label: string; parts: Record<string, number>; cost: number };
/** The period asked for: whole UTC days ending now. */
export function usageRange(days: number, now = Date.now()) {
  const end = now + 1;
  return { start: Math.floor((end - days * DAY) / DAY) * DAY, end };
}
export function makeBuckets(rows: SeriesRow[], start: number, end: number): Bucket[] {
  const out: Bucket[] = [];
  for (let t = start; t < end; t += DAY) out.push({ t, label: new Date(t).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" }), parts: {}, cost: 0 });
  const idx = Object.fromEntries(out.map((b) => [b.t, b]));
  for (const r of rows) { const b = idx[r.bucket_start], g = GROUP[r.grp] || r.grp; if (b) { b.parts[g] = (b.parts[g] || 0) + r.quota_tokens; b.cost += r.cost_micro_usd; } }
  return out;
}
export const bucketTotal = (b: Bucket, keys: string[]) => keys.reduce((s, k) => s + (b.parts[k] || 0), 0);
/** The purposes that appear in the period, in their fixed order. */
export const usedPurposes = (buckets: Bucket[]) => PURPOSES.filter((p) => buckets.some((b) => b.parts[p]));

export function niceMax(v: number): number {
  if (v <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(v)), n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
}
export function compact(n: number): string {
  return n >= 1e6 ? (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M" : n >= 1e3 ? (n / 1e3).toFixed(n >= 1e4 ? 0 : 1).replace(/\.0$/, "") + "k" : String(Math.round(n));
}
/** Which columns get a date label so they do not crowd each other. */
export const labelEvery = (columns: number, fit = 7) => Math.max(1, Math.ceil(columns / fit));

export function auditDetail(detail: Record<string, unknown> | undefined): string {
  return Object.entries(detail || {}).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(", ");
}
