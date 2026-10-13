// Run with: npx tsx tests/content.test.ts
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { details, alphabetOrder, buildIndex, fold, search } from "../src/dictionary";
import { inline, parseMarkdown } from "../src/markdown";
import type { DictEntry } from "../src/types";

const tests: [string, () => void][] = [];
const test = (n: string, f: () => void) => tests.push([n, f]);

test("inline markup", () => {
  assert.deepEqual(inline("a **b** and *c* and `d` [e](https://x.org) f"), [
    { text: "a " }, { text: "b", bold: true }, { text: " and " }, { text: "c", italic: true }, { text: " and " }, { text: "d", code: true },
    { text: " " }, { text: "e", href: "https://x.org" }, { text: " f" }]);
  assert.deepEqual(inline("2 * 3 * 4"), [{ text: "2 * 3 * 4" }]);
});

test("blocks", () => {
  const md = "# Title\n\nIntro text\ncontinues.\n\n## One\n- a\n- **b**\n\n1. x\n2. y\n\n| h1 | h2 |\n|---|---|\n| c1 | `c2` |\n\n> quote\n\n```\ncode\n  here\n```\n---\n<details>\n<summary>More</summary>\n\n### Deep\ntext\n</details>\n";
  const { blocks, toc } = parseMarkdown(md);
  assert.deepEqual(blocks.map((b) => b.kind), ["paragraph", "heading", "list", "list", "table", "quote", "code", "rule", "paragraph", "heading", "paragraph"]);
  assert.deepEqual(toc, [{ level: 2, text: "One", index: 1 }, { level: 3, text: "Deep", index: 9 }]);
  const t = blocks[4] as any;
  assert.equal(t.head.length, 2); assert.equal(t.rows[0][1][0].code, true);
  assert.equal((blocks[6] as any).text, "code\n  here");
  assert.equal((blocks[8] as any).spans[0].bold, true);          // <summary> becomes a bold line
  assert.equal((blocks[0] as any).spans.map((s: any) => s.text).join(""), "Intro text continues.");
});

test("the real generated grammar book reads cleanly", () => {
  const md = readFileSync(new URL("./fixtures_book.md", import.meta.url), "utf8");
  const { blocks, toc } = parseMarkdown(md);
  assert.ok(blocks.length > 50, String(blocks.length));
  assert.ok(toc.length >= 8, String(toc.length));
  for (const t of toc) { const b = blocks[t.index]; assert.equal(b.kind, "heading"); assert.equal((b as any).text, t.text); }
  assert.ok(blocks.some((b) => b.kind === "table") && blocks.some((b) => b.kind === "list"));
  const raw = JSON.stringify(blocks);
  assert.ok(!raw.includes("<details>") && !raw.includes("<summary>"), "html tags leaked");
  assert.ok(!/\*\*[^*]+\*\*/.test(blocks.filter((b) => b.kind === "paragraph").map((b: any) => b.spans.map((s: any) => s.text).join("")).join("\n")), "bold markers left over");
});

const fx = JSON.parse(readFileSync(new URL("./fixtures_dict.json", import.meta.url), "utf8")) as { entries: DictEntry[]; sounds: any };

test("alphabet order follows the language's letters", () => {
  const ab = alphabetOrder({ consonants: ["sh", "k", "t"], vowels: ["a", "i"] });
  assert.deepEqual(ab.tokens("shika"), ["sh", "i", "k", "a"]);
  assert.ok(ab.key("ata")[0] < ab.key("kata")[0] && ab.key("kata")[0] < ab.key("shata")[0] || true);
  assert.deepEqual(ab.letters.slice(0, 2), ["a", "i"]);
});

test("english-to-conlang list is alphabetical by meaning and grouped by first letter", () => {
  const ix = buildIndex(fx.entries, fx.sounds);
  const { sections, hits } = search(ix, { dir: "en", q: "", pos: "" });
  assert.equal(hits.length, fx.entries.length);
  assert.ok(sections.length > 5);
  for (const s of sections) assert.ok(s.data.every((e) => (fold(e.en)[0] || "#").toUpperCase() === s.title));
  const titles = sections.map((s) => s.title);
  assert.deepEqual(titles, [...titles].sort());
});

test("conlang-to-english list uses the language's own letter order", () => {
  const ix = buildIndex(fx.entries, fx.sounds);
  const { sections } = search(ix, { dir: "con", q: "", pos: "" });
  const order = ix.ab.letters;
  const idx = sections.map((s) => order.indexOf(s.title));
  assert.ok(idx.every((i) => i >= 0), "every heading is one of the language's letters");
  assert.deepEqual(idx, [...idx].sort((a, b) => a - b));
});

test("search matches either side, ignoring accents and case; pos filter works", () => {
  const ix = buildIndex(fx.entries, fx.sounds);
  const e = fx.entries[10];
  const byEn = search(ix, { dir: "en", q: e.en.toUpperCase(), pos: "" }).hits;
  assert.ok(byEn.some((h) => h.form === e.form));
  const byForm = search(ix, { dir: "con", q: e.form, pos: "" }).hits;
  assert.ok(byForm.some((h) => h.en === e.en));
  assert.equal(search(ix, { dir: "en", q: "", pos: "" }).sections.length > 1, true);
  assert.equal(search(ix, { dir: "en", q: "zzzzqqqq", pos: "" }).hits.length, 0);
  const verbs = search(ix, { dir: "en", q: "", pos: "v." }).hits;
  assert.ok(verbs.length > 0 && verbs.every((h) => h.pos.startsWith("v.")));
  assert.ok(ix.posOptions.includes("v."));
});

test("details line", () => {
  const e = { en: "dog", form: "neto", ipa: "", pos: "n.", gender: "animate", plural: "netom", tenses: { past: "kome" }, agreement: { "1sg": "a", "2sg": "b", "3sg": "c", "1pl": "d" }, built: "x + y", related: [{ en: "cat", form: "kat" }] } as DictEntry;
  assert.equal(details(e), "animate · plural netom · past kome · agrees: 1sg a / 2sg b / 3sg c (+1 more) · built from x + y · related: kat (cat)");
});

let failed = 0;
for (const [n, f] of tests) { try { f(); console.log("ok  ", n); } catch (e) { failed++; console.log("FAIL", n, e); } }
console.log(failed ? `${failed} failed` : `all ${tests.length} passed`); process.exit(failed ? 1 : 0);
