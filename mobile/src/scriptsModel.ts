// The editor's state for one writing system: its name, seed, language and kept ("pinned") settings. Plain TypeScript,
// no React, so it is unit-tested with Node. It mirrors the logic of the website's scripts.js.
import type { Proposal, ScriptCatalog, ScriptDial, ScriptRecord } from "./types";

/** Set by the language's own sounds when a system is designed for one, so they cannot be edited then. */
export const SOUND_DIALS = new Set(["consonants", "vowels"]);

export const randomSeed = (rnd: () => number = Math.random) => Math.floor(rnd() * 2 ** 31);

export class ScriptDraft {
  seed: number; name: string; conlang: string; pins: Record<string, string | number>; dirty: boolean; rec: ScriptRecord | null;

  constructor(rec: ScriptRecord | null, presetLanguage = "", rnd: () => number = Math.random) {
    this.rec = rec;
    this.name = rec ? rec.name : "";
    this.conlang = rec ? rec.conlang_id || "" : presetLanguage;
    this.pins = rec ? { ...rec.pins } : {};
    this.seed = rec ? rec.seed : randomSeed(rnd);
    this.dirty = !rec;
  }

  /** A dial the language's own sounds decide. */
  fixed(key: string): boolean { return !!this.conlang && SOUND_DIALS.has(key); }
  pinned(key: string): boolean { return key in this.pins && !this.fixed(key); }

  setSeed(v: number) { this.seed = Math.min(2 ** 31 - 1, Math.max(0, Math.floor(Number(v) || 0))); this.dirty = true; }
  setName(v: string) { this.name = v; this.dirty = true; }
  setLanguage(id: string) { this.conlang = id; this.dirty = true; }
  /** Choosing a value keeps that setting. */
  setPin(key: string, value: string | number) { this.pins[key] = value; this.dirty = true; }
  /** The checkbox beside a dial: keep it at what it is now, or let the seed choose again. */
  toggleKeep(key: string, current: string | number) {
    if (key in this.pins) delete this.pins[key]; else this.pins[key] = current;
    this.dirty = true;
  }
  keepAll(cat: ScriptCatalog, spec: Record<string, any>) {
    for (const d of cat.dials) if (!this.fixed(d.key) && d.key in spec) this.pins[d.key] = spec[d.key];
    this.dirty = true;
  }
  releaseAll() { this.pins = {}; this.dirty = true; }
  randomize(rnd: () => number = Math.random) { this.seed = randomSeed(rnd); this.dirty = true; }

  /** What Save sends. */
  body() { return { name: this.name.trim(), seed: this.seed, pins: this.pins, conlang_id: this.conlang || null }; }
  /** What a redraw (preview) sends. */
  previewBody() { return { seed: this.seed, pins: this.pins, conlang_id: this.conlang || null }; }
  markSaved(rec: ScriptRecord) { this.rec = rec; this.name = rec.name; this.dirty = false; }

  status(): string { return !this.rec ? "Not saved yet" : this.dirty ? "Unsaved changes" : "Saved"; }
  isPrimaryHere(): boolean { return !!(this.rec && this.rec.primary && this.rec.conlang_id === this.conlang); }
}

export const fmtDial = (d: ScriptDial, v: unknown) => (d.step && d.step < 1 ? Number(v).toFixed(2) : String(v));
export const dialLabel = (cat: ScriptCatalog, key: string) => (cat.dials.find((d) => d.key === key) || { label: key }).label;
export const dialsOf = (cat: ScriptCatalog, group: string) => cat.dials.filter((d) => d.group === group);

/** The suggested settings the user left ticked become kept settings. Returns how many were applied. */
export function applyProposals(draft: ScriptDraft, proposals: Proposal[], ticked: Set<string>): number {
  let n = 0;
  for (const p of proposals) if (ticked.has(p.key)) { draft.setPin(p.key, p.value); n++; }
  return n;
}

/** Stepper steps for a number dial: whole numbers for counts, a twentieth of the range otherwise. */
export function stepFor(d: ScriptDial): number {
  if (d.step && d.step >= 1) return d.step;
  const span = (d.max ?? 1) - (d.min ?? 0);
  return span <= 1 ? 0.05 : span / 20;
}

// ---- the "Writing system:" chooser under a translation
export type WritingOption = { value: string; label: string };
export function writingOptions(scripts: { id: string; name: string }[], primaryId: string | null): WritingOption[] {
  const primary = scripts.find((s) => s.id === primaryId);
  return [
    ...(primary ? [{ value: primary.id, label: "Primary: " + primary.name }] : []),
    { value: "none", label: "None (disabled)" },
    ...scripts.filter((s) => s !== primary).map((s) => ({ value: s.id, label: s.name })),
  ];
}
/** The choice to show: the one made before if it still exists, else the primary system, else none. */
export function defaultWriting(options: WritingOption[], previous: string | null, primaryId: string | null): string {
  if (previous && options.some((o) => o.value === previous)) return previous;
  return primaryId && options.some((o) => o.value === primaryId) ? primaryId : "none";
}
export const approxNote = (language: string, n: number) =>
  `Not designed for ${language}: ${n} sound${n > 1 ? "s are" : " is"} written with the closest letter this script has.`;

// ---- checkpoints
export const kb = (n: number) => (n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(n < 10240 ? 1 : 0)} KB` : `${(n / 1048576).toFixed(1)} MB`);
export const versionBase = (kind: "lang" | "script", id: string) => (kind === "lang" ? `/api/conlangs/${id}` : `/api/scripts/${id}`);
