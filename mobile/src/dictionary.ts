// Dictionary ordering, searching and grouping (port of the website's dictionary tab). Pure data, tested with plain Node.
import type { DictEntry, Sounds } from "./types";

export const fold = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** The language's own alphabet order: letters (including two-letter ones like "sh") sorted by their base letter. */
export function alphabetOrder(sounds: Pick<Sounds, "consonants" | "vowels">) {
  const plain = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "");
  const letters = [...new Set([...sounds.consonants, ...sounds.vowels])];
  letters.sort((a, b) => {
    const pa = plain(a), pb = plain(b);
    return (pa[0] < pb[0] ? -1 : pa[0] > pb[0] ? 1 : 0) || Number(a.length > 1) - Number(b.length > 1) ||
      (pa < pb ? -1 : pa > pb ? 1 : 0) || Number(a !== pa) - Number(b !== pb);
  });
  const byLen = [...letters].sort((a, b) => b.length - a.length);
  const idx: Record<string, number> = Object.fromEntries(letters.map((l, i) => [l, i]));
  const tokens = (word: string) => {
    const out: string[] = [];
    const w = word.toLowerCase();
    for (let i = 0; i < w.length;) { const t = byLen.find((l) => w.startsWith(l, i)) || w[i]; out.push(t); i += t.length; }
    return out;
  };
  return { tokens, key: (w: string) => tokens(w).map((t) => idx[t] ?? 999), letters };
}

export type Indexed = DictEntry & { k: number[]; f: string; e: string };

export function buildIndex(entries: DictEntry[], sounds: Pick<Sounds, "consonants" | "vowels">) {
  const ab = alphabetOrder(sounds);
  const all: Indexed[] = entries.map((e) => ({ ...e, k: ab.key(e.form), f: fold(e.form), e: fold(e.en) }));
  const byForm = [...all].sort((a, b) => {
    for (let i = 0; i < Math.min(a.k.length, b.k.length); i++) if (a.k[i] !== b.k[i]) return a.k[i] - b.k[i];
    return a.k.length - b.k.length;
  });
  const posOptions = [...new Set(entries.map((e) => e.pos.split("/")[0]))].sort();
  return { ab, byEnglish: all, byForm, posOptions };   // the server already sorts entries by English
}

export type Direction = "en" | "con";
export type Section = { title: string; data: Indexed[] };

export function search(index: ReturnType<typeof buildIndex>, o: { dir: Direction; q: string; pos: string }) {
  const q = fold(o.q.trim());
  const src = o.dir === "en" ? index.byEnglish : index.byForm;
  const hits = src.filter((e) => (!o.pos || e.pos.startsWith(o.pos)) && (!q || e.f.includes(q) || e.e.includes(q)));
  if (q) return { hits, sections: [{ title: "", data: hits }] as Section[] };
  const sections: Section[] = [];
  for (const e of hits) {
    const head = o.dir === "en" ? (fold(e.en)[0] || "#").toUpperCase() : index.ab.tokens(e.form)[0] || "#";
    const last = sections[sections.length - 1];
    if (last && last.title === head) last.data.push(e); else sections.push({ title: head, data: [e] });
  }
  return { hits, sections };
}

/** One line of extra facts about a word: forms, tenses, agreement, relatives. */
export function details(e: DictEntry): string {
  const bits: string[] = [];
  if (e.gender) bits.push(e.gender);
  if (e.dual) bits.push("dual " + e.dual);
  if (e.plural) bits.push("plural " + e.plural);
  for (const [t, f] of Object.entries(e.tenses || {})) bits.push(t + " " + f);
  const ag = Object.entries(e.agreement || {});
  if (ag.length && new Set(ag.map(([, v]) => v)).size > 1)
    bits.push("agrees: " + ag.slice(0, 3).map(([k, v]) => `${k} ${v}`).join(" / ") + (ag.length > 3 ? ` (+${ag.length - 3} more)` : ""));
  if (e.built) bits.push("built from " + e.built);
  if (e.related?.length) bits.push("related: " + e.related.slice(0, 3).map((r) => `${r.form} (${r.en})`).join(", "));
  return bits.join(" · ");
}
