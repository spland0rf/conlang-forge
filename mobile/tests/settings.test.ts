// Run with: npx tsx tests/settings.test.ts
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SettingsDraft, type SettingsPayload } from "../src/settingsModel";

const S = JSON.parse(readFileSync(new URL("./fixtures_settings.json", import.meta.url), "utf8")) as SettingsPayload;
const fresh = () => new SettingsDraft(JSON.parse(JSON.stringify(S)));
const tests: [string, () => void][] = [];
const test = (n: string, f: () => void) => tests.push([n, f]);
const firstOf = (kind: string, pred: (s: any) => boolean = () => true) => S.settings.find((s) => s.kind === kind && pred(s))!;

test("a fresh draft has no changes and an empty payload", () => {
  const d = fresh();
  assert.equal(d.changeCount(), 0);
  assert.deepEqual(d.payload(), { set: {}, unpin: [], tuning: undefined });
});

test("changing an enum counts once, is fixed, and can be discarded", () => {
  const d = fresh();
  const s = firstOf("enum", (x) => x.editable && x.key === "syntax.word_order");
  const other = s.options!.find((o) => o.value !== s.value)!;
  d.setVal(s.key, other.value);
  assert.equal(d.changeCount(), 1); assert.ok(d.touched(s.key)); assert.ok(d.pinned(s.key));
  assert.deepEqual(d.payload().set, { [s.key]: other.value });
  d.setVal(s.key, s.value);                                           // back to the saved value
  assert.equal(d.changeCount(), 0, "setting the same value again is not a change");
  d.setVal(s.key, other.value); d.discard();
  assert.equal(d.changeCount(), 0); assert.deepEqual(d.payload().set, {});
});

test("Fixed <-> Random", () => {
  const d = fresh();
  const pinned = S.settings.find((s) => s.editable && s.pinned)!, loose = S.settings.find((s) => s.editable && !s.pinned);
  d.lock(pinned.key);                                                 // fixed -> random
  assert.ok(!d.pinned(pinned.key)); assert.deepEqual(d.payload().unpin, [pinned.key]); assert.equal(d.changeCount(), 1);
  d.lock(pinned.key);                                                 // and back
  assert.ok(d.pinned(pinned.key)); assert.equal(d.changeCount(), 0);
  if (loose) { d.lock(loose.key); assert.ok(d.pinned(loose.key)); assert.deepEqual(d.payload().set[loose.key], loose.value); }
});

test("a count and its list override each other", () => {
  const d = fresh();
  d.setVal("phonology.consonants", ["p", "t", "k", "m", "n", "s", "l", "d"]);
  assert.equal(d.cur("phonology.consonant_count"), 8);
  d.setVal("phonology.consonant_count", 10);                          // choosing a count releases the exact list
  assert.ok(!("phonology.consonants" in d.set));
  if (S.settings.find((s) => s.key === "phonology.consonants")!.pinned) assert.ok(d.payload().unpin.includes("phonology.consonants"));
  assert.equal(d.cur("phonology.consonant_count"), 10);
  d.setVal("phonology.consonants", ["p", "t", "k", "m", "n", "s", "l", "d"]);
  assert.ok(!("phonology.consonant_count" in d.set), "choosing the list releases the count");
  assert.ok(!("phonology.consonant_weights" in d.set), "and the shares, which no longer fit");
});

test("number minimums depend on the other count", () => {
  const d = fresh();
  const s = S.settings.find((x) => x.key === "phonology.consonant_count")!;
  assert.ok(d.numberMin(s) >= (s.min ?? 0));
  const vowelCount = d.cur("phonology.vowel_count");
  assert.equal(d.numberMin(s), Math.max(s.min!, S.minimums.consonants[String(vowelCount)] || 0));
});

test("weights: changing one share keeps the others", () => {
  const d = fresh();
  const s = S.settings.find((x) => x.key === "phonology.consonant_weights")!;
  const before = d.weightRows(s);
  assert.ok(before.length >= 4);
  d.setWeight(s, before[0].value, 50);
  const after = d.weightRows(s);
  assert.equal(after[0].pct, 50);
  assert.deepEqual(after.slice(1).map((r) => r.pct), before.slice(1).map((r) => r.pct));
  assert.equal(d.changeCount(), 1);
});

test("odds and rates and tuning are changes, and reset cleanly", () => {
  const d = fresh();
  const e = S.settings.find((s) => s.kind === "enum" && s.odds && s.odds.some((o) => o.default > 0))!;
  const rows = d.oddsRows(e);
  d.setOdd(e, rows[0].key, rows[0].default + 5);
  assert.ok(d.oddsChanged(e.key)); assert.equal(d.changeCount(), 1);
  assert.ok(Math.abs(d.oddsRows(e).reduce((a, r) => a + r.share, 0) - 100) < 0.5);
  d.setOdd(e, rows[0].key, rows[0].default);                          // back to the usual odds
  assert.ok(!d.oddsChanged(e.key)); assert.equal(d.changeCount(), 0);
  const rate = S.settings.find((s) => s.kind === "rate")!;
  d.setRate(rate.key, rate.default!, 80);
  assert.equal(d.rateValue(rate.key, rate.default!).value, 0.8); assert.equal(d.changeCount(), 1);
  d.setRate(rate.key, rate.default!, rate.default! * 100);
  assert.equal(d.changeCount(), 0);
  const t = S.settings.find((s) => s.kind === "tune")!;
  d.setTune(t, t.default! + t.step!); assert.ok(d.tuneValue(t).custom); assert.deepEqual(Object.keys(d.payload().tuning!), ["gen"]);
  d.setTune(t, t.default!); assert.equal(d.changeCount(), 0); assert.equal(d.payload().tuning, undefined);
});

test("cluster candidates follow the consonants and the language's rules", () => {
  const d = fresh();
  const cons = d.cur("phonology.consonants") as string[];
  for (const [a, b] of d.candidates("onset")) {
    assert.ok(cons.includes(a) && cons.includes(b) && a !== b);
    assert.ok(S.cluster_rules.onset.first.includes(S.consonants[a].manner) || a === "s");
  }
  const coda = d.candidates("coda");
  for (const [a, b] of coda) assert.equal(S.consonants[b].manner, "stop");
  const med = d.candidates("medial");
  const codas = d.cur("phonology.coda_consonants") as string[];
  assert.ok(med.every(([a]) => codas.includes(a)));
  const c = S.settings.find((s) => s.kind === "clusters")!;
  const { sel, options } = d.clusterOptions(c);
  assert.ok(sel.every((id) => options.some((o) => o.value === id)));
  assert.ok(options.every((o) => o.value.includes("+") && o.label && o.hint));
});

test("cases: the core cases are locked on when any case is used", () => {
  const d = fresh();
  const cs = S.settings.find((s) => s.key === "morphology.cases")!;
  d.setVal(cs.key, ["genitive"]);
  const m = d.multi(cs);
  assert.ok(m.locked.length === 2 && m.selected.includes("genitive") && m.locked.every((c) => m.selected.includes(c)));
  d.setVal(cs.key, []);
  assert.deepEqual(d.multi(cs).locked, []);
});

test("staged sample proposals become fixed settings", () => {
  const d = fresh();
  d.stage([{ key: "phonology.stress", proposed: "initial" }]);
  assert.equal(d.cur("phonology.stress"), "initial"); assert.ok(d.pinned("phonology.stress"));
});

let failed = 0;
for (const [n, f] of tests) { try { f(); console.log("ok  ", n); } catch (e) { failed++; console.log("FAIL", n, e); } }
console.log(failed ? `${failed} failed` : `all ${tests.length} passed`); process.exit(failed ? 1 : 0);
