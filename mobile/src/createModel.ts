// Pure logic for creating languages (random "forge" and "from a sample"); no React, tested under Node.
import type { LanguageSummary } from "./types";

export type DialOptions = Record<string, (string | number)[] | null>;
export type Dial = { key: string; label: string; options: { value: string; label: string }[] };

const TYPES: Record<string, string> = {
  isolating: "Isolating: short words, little endings", agglutinative: "Agglutinative: endings stack on words",
  fusional: "Fusional: endings blend and carry several meanings", polysynthetic: "Polysynthetic: long words carry whole sentences",
};
const ORDERS: Record<string, string> = {
  SOV: "Subject, object, verb (like Japanese)", SVO: "Subject, verb, object (like English)", VSO: "Verb, subject, object (like Welsh)",
  VOS: "Verb, object, subject", OVS: "Object, verb, subject", OSV: "Object, subject, verb",
};
const BASES: Record<string, string> = { "10": "10 (like English)", "12": "12 (dozens)", "20": "20 (scores)", "5": "5 (one hand)", "8": "8" };

const DIAL_DEFS: { key: string; label: string; fmt: (o: string) => string }[] = [
  { key: "morphology.typology", label: "How words are built", fmt: (o) => TYPES[o] || o },
  { key: "syntax.word_order", label: "Sentence order", fmt: (o) => `${o}: ${ORDERS[o] ?? ""}` },
  { key: "syntax.adjective_order", label: "Adjectives", fmt: (o) => (o === "adjective-noun" ? "Before the noun" : "After the noun") },
  { key: "phonology.stress", label: "Stress", fmt: (o) => (o === "none" ? "Even, no stress" : `On the ${o} syllable`) },
  { key: "morphology.numeral_base", label: "Counting base", fmt: (o) => BASES[o] || o },
];

/** The shaping dials the server offers (from /api/config), in the website's order. A dial the server does not list is skipped. */
export function dialsFromConfig(dials: DialOptions | undefined | null): Dial[] {
  const out: Dial[] = [];
  for (const d of DIAL_DEFS) {
    const opts = dials?.[d.key];
    if (!opts || !opts.length) continue;
    out.push({ key: d.key, label: d.label, options: opts.map((o) => ({ value: String(o), label: d.fmt(String(o)) })) });
  }
  return out;
}

export const MAX_SEED = 2 ** 31 - 1;

/** "" -> undefined (the server picks one); digits -> number; anything else -> error text. */
export function parseSeed(text: string): { seed?: number; error?: string } {
  const t = text.trim();
  if (!t) return {};
  if (!/^\d{1,10}$/.test(t) || Number(t) > MAX_SEED) return { error: "The seed must be a whole number from 0 to 2147483647." };
  return { seed: Number(t) };
}

export const rollSeed = (rand: () => number = Math.random): string => String(Math.floor(rand() * 2 ** 31));

/** Chosen dials -> pins. Empty choice ("Surprise me") is left out; numbers stay numbers. */
export function pinsFrom(choices: Record<string, string>): Record<string, string | number> {
  const pins: Record<string, string | number> = {};
  for (const [k, v] of Object.entries(choices)) if (v) pins[k] = /^\d+$/.test(v) ? Number(v) : v;
  return pins;
}

export type ForgeInput = { name: string; seed: string; choices: Record<string, string> };
export function forgeBody(i: ForgeInput): { body?: Record<string, unknown>; error?: string } {
  const s = parseSeed(i.seed);
  if (s.error) return { error: s.error };
  const body: Record<string, unknown> = { name: i.name.trim(), pins: pinsFrom(i.choices) };
  if (s.seed !== undefined) body.seed = s.seed;
  return { body };
}

/** One sample line per entry, blank lines dropped. */
export const sampleLines = (text: string): string[] => text.split("\n").map((t) => t.trim()).filter(Boolean);

export type SampleInput = ForgeInput & { sample: string; readGrammar: boolean; modelAvailable: boolean };
export function sampleBody(i: SampleInput): { body?: Record<string, unknown>; error?: string } {
  const texts = sampleLines(i.sample);
  if (!texts.length) return { error: "Paste some sample text first." };
  const s = parseSeed(i.seed);
  if (s.error) return { error: s.error };
  const body: Record<string, unknown> = { texts, pins: pinsFrom(i.choices), name: i.name.trim(), use_model: i.readGrammar && i.modelAvailable };
  if (s.seed !== undefined) body.seed = s.seed;
  return { body };
}

export type Measure = { syllables: number; words: number; min: number; target: number; level: "none" | "partial" | "good" };
export const EMPTY_MEASURE: Measure = { syllables: 0, words: 0, min: 8, target: 40, level: "none" };

/** The sentence under the length meter (same wording as the website). */
export function meterText(m: Measure): string {
  const n = `${m.syllables} of ${m.target} syllables`;
  if (m.syllables === 0) return `Aim for about ${m.target} syllables (roughly 25 words). The more text, the more reliably the language will match the sounds and syllable shapes in your example.`;
  if (m.level === "none") return `${n}. Too short to shape the language yet. Add more, or the language will be made at random.`;
  if (m.level === "partial") return `${n}. Enough to shape some settings. With about ${m.target} or more, the sounds and syllable shapes match your example more reliably.`;
  return `${m.syllables} syllables, past the ${m.target} target. Enough to match your example's sounds and syllable shapes reliably. More text still helps a little.`;
}
export const meterFraction = (m: Measure): number => (m.target > 0 ? Math.max(0, Math.min(1, m.syllables / m.target)) : 0);

export type ShapedProposal = { label: string; proposed_show: string; current_show?: string; evidence?: string };
export type Shaped = { applied: ShapedProposal[]; kept: ShapedProposal[]; notes: string[] };
export type FromSampleResult = LanguageSummary & { shaped: Shaped };

/** The "your language is ready" summary, as plain lines for the screen. */
export function shapedLines(sh: Shaped): { applied: string[]; kept: string[]; notes: string[]; headline: string } {
  const n = sh.applied.length;
  return {
    headline: n ? `The sample decided ${n} setting${n === 1 ? "" : "s"}:` : "The sample was too short to decide anything, so the language was made at random.",
    applied: sh.applied.map((p) => `${p.label}: ${p.proposed_show}${p.evidence ? ` (${p.evidence})` : ""}`),
    kept: sh.kept.map((p) => `${p.label}: kept ${p.current_show} (sample suggested ${p.proposed_show})`),
    notes: sh.notes,
  };
}

/** Keeps only the newest answer when several slow requests overlap (the length meter). */
export function latestOnly<T>() {
  let seq = 0;
  return { next: () => ++seq, isLatest: (n: number) => n === seq };
}
