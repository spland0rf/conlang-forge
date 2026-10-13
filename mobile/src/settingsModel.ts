// The settings editor's brain: what is fixed, what is random, what has changed, what to send to the server.
// A port of the website's settings.js without any screen code, so it can be tested with plain Node.
export type Option = { value: any; label: string; hint?: string; group?: string };
export type Setting = {
  key: string; group: string; label: string; help: string; kind: string;
  value?: any; pinned?: boolean; editable?: boolean;
  options?: Option[]; min?: number; max?: number; step?: number; integer?: boolean; dynamic_min?: string; of?: string; items?: Option[];
  yes?: string; no?: string; maxlen?: number; position?: string; unused?: string;
  odds?: { key: string; label: string; default: number }[]; default?: number; chance?: { value: number; default: number };
};
export type SettingsPayload = {
  groups: { id: string; label: string; help: string }[]; settings: Setting[];
  consonants: Record<string, { label: string; manner: string; say: string }>; vowels: Record<string, { label: string }>;
  cluster_rules: Record<string, { first: string[]; second: string[]; never_first?: string[]; first_extra?: string[]; never_second?: string[]; s_plus_stop?: boolean }>;
  tuning: Record<string, any>; seed: number; minimums: { consonants: Record<string, number>; vowels: Record<string, number> };
};

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x ?? null));
export const pct = (x: number) => Math.round(x * 1000) / 10;

// a count (how many) and its list (which ones) are two ways to set the same thing; the last one chosen wins
const LIST_OF: Record<string, string> = { "phonology.consonant_count": "phonology.consonants", "phonology.vowel_count": "phonology.vowels", "phonology.complex_count": "phonology.complex_consonants" };
const FREES: Record<string, string[]> = { "phonology.consonants": ["phonology.consonant_weights"], "phonology.vowels": ["phonology.vowel_weights"], "phonology.complex_consonants": ["phonology.consonant_weights"] };

export class SettingsDraft {
  S: SettingsPayload;
  by: Record<string, Setting>;
  original: { tuning: Record<string, any> };
  set: Record<string, any> = {};
  unpin = new Set<string>();
  tuning: Record<string, any>;
  private order: string[];

  constructor(S: SettingsPayload) {
    this.S = S;
    this.by = Object.fromEntries(S.settings.map((s) => [s.key, s]));
    this.original = { tuning: clone(S.tuning || {}) };
    this.tuning = clone(S.tuning || {});
    this.order = Object.keys(S.consonants);
  }

  // ---- reading
  cur(k: string): any {
    if (k in this.set) return this.set[k];
    const l = LIST_OF[k];
    if (l && l in this.set) return this.set[l].length;
    return this.by[k].value;
  }
  pinned(k: string) { return k in this.set || (!!this.by[k].pinned && !this.unpin.has(k)); }
  touched(k: string) {
    const b = this.by[k];
    return (k in this.set && (!b.pinned || !same(this.set[k], b.value))) || (!!b.pinned && this.unpin.has(k));
  }
  tuningChanged() { return !same(this.tuning, this.original.tuning); }
  changeCount() { return Object.keys(this.by).filter((k) => "editable" in this.by[k] && this.touched(k)).length + (this.tuningChanged() ? 1 : 0); }
  labelOf(c: string) { return this.S.consonants[c] ? this.S.consonants[c].label : this.S.vowels[c] ? this.S.vowels[c].label : c; }
  ofList(of: string): string[] {
    return of.split("+").flatMap((x) => (x === "complex" ? this.cur("phonology.complex_consonants") : this.cur(x)) as string[])
      .sort((a, b) => this.order.indexOf(a) - this.order.indexOf(b));
  }

  // ---- changing
  setVal(k: string, v: any) {
    this.set[k] = v; this.unpin.delete(k);
    const l = LIST_OF[k];
    if (l) {
      delete this.set[l]; if (this.by[l].pinned) this.unpin.add(l);
      (FREES[l] || []).forEach((w) => { delete this.set[w]; if (this.by[w].pinned) this.unpin.add(w); });
    }
    const cnt = Object.keys(LIST_OF).find((c) => LIST_OF[c] === k);
    if (cnt) { delete this.set[cnt]; if (this.by[cnt].pinned) this.unpin.add(cnt); }
  }
  /** Fixed <-> Random. */
  lock(k: string) {
    if (this.pinned(k)) { delete this.set[k]; this.unpin.add(k); }
    else { this.set[k] = clone(this.by[k].value); this.unpin.delete(k); }
  }
  tune(kind: string, key: string, v: any) {
    (this.tuning[kind] ||= {});
    if (v == null) delete this.tuning[kind][key]; else this.tuning[kind][key] = v;
    if (!Object.keys(this.tuning[kind]).length) delete this.tuning[kind];
  }
  discard() { this.set = {}; this.unpin = new Set(); this.tuning = clone(this.original.tuning); }
  /** Stage changes proposed by analysing a sample text. */
  stage(changes: { key: string; proposed: any }[]) { for (const c of changes) { this.set[c.key] = c.proposed; this.unpin.delete(c.key); } }

  payload() {
    return { set: this.set, unpin: [...this.unpin], tuning: this.tuningChanged() ? this.tuning : undefined };
  }

  // ---- per-kind helpers
  /** Lowest allowed value for a number setting (some depend on another setting). */
  numberMin(s: Setting): number {
    let min = s.min ?? 0;
    if (s.dynamic_min) {
      const other = this.cur(s.dynamic_min === "consonants" ? "phonology.vowel_count" : "phonology.consonant_count");
      const t = this.S.minimums[s.dynamic_min as "consonants" | "vowels"]?.[String(other)];
      if (t) min = Math.max(min, t);
    }
    return min;
  }

  weightRows(s: Setting): { value: string; label: string; pct: number }[] {
    const items = s.of ? this.ofList(s.of).map((c) => ({ value: c, label: this.labelOf(c) })) : (s.items || []);
    const base: Record<string, number> = this.cur(s.key) || {};
    const floor = s.of ? Math.min(...Object.values(base).filter((x) => x > 0), 0.05) : 0;
    return items.map((it) => ({ value: it.value, label: it.label, pct: Math.round((it.value in base ? base[it.value] : floor) * 100) }));
  }
  setWeight(s: Setting, value: string, pctValue: number) {
    const out: Record<string, number> = {};
    for (const r of this.weightRows(s)) out[r.value] = (r.value === value ? pctValue : r.pct) / 100;
    this.setVal(s.key, out);
  }

  oddsRows(s: Setting): { key: string; label: string; default: number; w: number; share: number }[] {
    const over = (this.tuning.odds || {})[s.key] || {};
    const rows = (s.odds || []).map((o) => ({ ...o, w: o.key in over ? over[o.key] : o.default }));
    const total = rows.reduce((a, r) => a + r.w, 0) || 1;
    return rows.map((r) => ({ ...r, share: pct(r.w / total) }));
  }
  setOdd(s: Setting, key: string, w: number) {
    const rows = this.oddsRows(s);
    const o: Record<string, number> = {};
    for (const r of rows) o[r.key] = r.key === key ? Math.max(0, w) : r.w;
    this.tune("odds", s.key, rows.every((r) => Math.abs(o[r.key] - r.default) < 1e-9) ? null : o);
  }
  resetOdds(s: Setting) { this.tune("odds", s.key, null); }
  oddsChanged(k: string) { return k in (this.tuning.odds || {}); }
  /** Enum settings that have odds when random (shown in a collapsible box). */
  hasOddsBox(s: Setting) { return !!s.odds && s.kind === "enum" && !s.odds.every((o) => o.default === 0); }

  tuneValue(s: Setting) {
    const name = s.key.slice(4), v = (this.tuning.gen || {})[name];
    return { value: v ?? s.default ?? 0, custom: v != null };
  }
  setTune(s: Setting, x: number) {
    const name = s.key.slice(4);
    this.tune("gen", name, Math.abs(x - (s.default ?? 0)) < 1e-9 ? null : s.integer ? Math.round(x) : x);
  }
  rateValue(key: string, dflt: number) { const v = (this.tuning.rates || {})[key]; return { value: v ?? dflt, custom: v != null }; }
  setRate(key: string, dflt: number, percent: number) { this.tune("rates", key, Math.abs(percent / 100 - dflt) < 1e-9 ? null : percent / 100); }

  /** Possible two-consonant clusters for a position, from the current consonants. */
  candidates(position: string): string[][] {
    const cons: string[] = this.cur("phonology.consonants"), man = (c: string) => this.S.consonants[c].manner;
    const R = this.S.cluster_rules[position] || ({} as any);
    const out: string[][] = [];
    if (position === "medial") {
      const all = [...cons, ...this.cur("phonology.complex_consonants")];
      const codas = (this.cur("phonology.coda_consonants") as string[]).filter((c) => all.includes(c));
      for (const a of codas) for (const b of all) out.push([a, b]);
    } else if (position === "onset") {
      for (const a of cons) for (const b of cons) if (a !== b && R.first.includes(man(a)) && R.second.includes(man(b)) && !(R.never_first || []).includes(a)) out.push([a, b]);
      if (cons.includes("s")) for (const b of cons) if (man(b) === "stop" && b !== "ʔ" && !out.some((p) => p[0] === "s" && p[1] === b)) out.push(["s", b]);
    } else {
      const complex: string[] = this.cur("phonology.complex_consonants");
      const codas = (this.cur("phonology.coda_consonants") as string[]).filter((c) => cons.includes(c) || complex.includes(c));
      for (const a of codas) for (const b of cons) if (a !== b && man(b) === "stop" && b !== "ʔ" && (R.first.includes(man(a)) || (R.first_extra || []).includes(a))) out.push([a, b]);
    }
    return out;
  }
  clusterOptions(s: Setting): { sel: string[]; options: Option[] } {
    const cand = this.candidates(s.position || "onset");
    const sel = ((this.cur(s.key) as string[]) || []).filter((id) => cand.some((p) => p.join("+") === id));
    return { sel, options: cand.map((p) => ({ value: p.join("+"), label: p.map((c) => this.labelOf(c)).join(""), hint: p.map((c) => this.S.consonants[c].say).join(" + ") })) };
  }

  /** The options a multi-choice setting offers right now, and which are selected. */
  multi(s: Setting): { options: Option[]; selected: string[]; locked: string[] } {
    let opts = s.options || [];
    if (s.of) { const allowed = this.ofList(s.of); opts = opts.filter((o) => allowed.includes(o.value)); }
    const v = this.cur(s.key) as string[];
    if (s.key === "morphology.cases") {
      const core = ({ "nominative-accusative": ["nominative", "accusative"], "ergative-absolutive": ["ergative", "absolutive"] } as Record<string, string[]>)[this.cur("morphology.case_alignment")] || [];
      const other = ["nominative", "accusative", "ergative", "absolutive"].filter((c) => !core.includes(c));
      opts = opts.filter((o) => !other.includes(o.value));
      return { options: opts, selected: [...new Set([...(v.length ? core : []), ...v])], locked: v.length ? core : [] };
    }
    return { options: opts, selected: v.filter((x) => opts.some((o) => o.value === x)), locked: [] };
  }
}
