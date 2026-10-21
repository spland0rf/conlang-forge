// Run with: npx tsx tests/scripts.test.ts
import assert from "node:assert/strict";
import type { ScriptPreset } from "../src/types";
import { ScriptDraft, applyProposals, createScriptBody, defaultWriting, HOW_OPTIONS, kb, stepFor, tweakDials, versionBase, writingOptions } from "../src/scriptsModel";
import type { ScriptCatalog, ScriptRecord } from "../src/types";

const cat: ScriptCatalog = { groups: ["Style", "Size"], dials: [
  { key: "family", label: "Main style", group: "Style", description: "", type: "choice", values: ["spikey", "curvy"] },
  { key: "roundness", label: "Roundness", group: "Style", description: "", type: "number", min: 0, max: 1, step: 0.01 },
  { key: "consonants", label: "Consonants", group: "Size", description: "", type: "number", min: 8, max: 40, step: 1 },
] };
const rec = (o: Partial<ScriptRecord> = {}): ScriptRecord => ({ id: "s1", name: "Plain", seed: 11, pins: { family: "curvy" }, conlang_id: null, primary: false, ...o });
const tests: [string, () => void][] = [];
const test = (n: string, f: () => void) => tests.push([n, f]);

test("a new draft is unsaved with a random seed; a saved one starts clean", () => {
  const d = new ScriptDraft(null, "L1", () => 0.5);
  assert.equal(d.seed, 2 ** 30); assert.equal(d.conlang, "L1"); assert.equal(d.status(), "Not saved yet");
  const s = new ScriptDraft(rec());
  assert.equal(s.dirty, false); assert.equal(s.status(), "Saved"); assert.deepEqual(s.pins, { family: "curvy" });
  s.setName("Other"); assert.equal(s.status(), "Unsaved changes");
});
test("choosing a value keeps it; the checkbox keeps or releases", () => {
  const d = new ScriptDraft(rec({ pins: {} }));
  d.setPin("family", "spikey"); assert.ok(d.pinned("family"));
  d.toggleKeep("roundness", 0.7); assert.equal(d.pins.roundness, 0.7);
  d.toggleKeep("roundness", 0.7); assert.ok(!("roundness" in d.pins));
});
test("sound dials are decided by the language", () => {
  const d = new ScriptDraft(rec({ pins: { consonants: 20 } }));
  assert.ok(d.pinned("consonants"));
  d.setLanguage("L1");
  assert.ok(d.fixed("consonants") && !d.pinned("consonants") && !d.fixed("family"));
  d.keepAll(cat, { family: "curvy", roundness: 0.4, consonants: 22 });
  assert.equal(d.pins.family, "curvy"); assert.equal(d.pins.roundness, 0.4);
  d.releaseAll(); assert.deepEqual(d.pins, {});
});
test("the saved and preview bodies are what the API expects", () => {
  const d = new ScriptDraft(rec());
  d.setName("  Bubbly  "); d.setSeed(-5.7);
  assert.deepEqual(d.body(), { name: "Bubbly", seed: 0, pins: { family: "curvy" }, conlang_id: null });
  d.setSeed(2 ** 40); assert.equal(d.seed, 2 ** 31 - 1);
  assert.deepEqual(d.previewBody(), { seed: 2 ** 31 - 1, pins: { family: "curvy" }, conlang_id: null });
  d.markSaved(rec({ name: "Bubbly" })); assert.equal(d.status(), "Saved");
});
test("only ticked suggestions are applied", () => {
  const d = new ScriptDraft(rec({ pins: {} }));
  const n = applyProposals(d, [{ key: "family", value: "spikey" }, { key: "roundness", value: 0.2 }], new Set(["family"]));
  assert.equal(n, 1); assert.deepEqual(d.pins, { family: "spikey" });
});
test("steps suit the dial", () => {
  assert.equal(stepFor(cat.dials[2]), 1); assert.equal(stepFor(cat.dials[1]), 0.05);
});
test("the writing chooser lists primary first, then none, then the rest", () => {
  const all = [{ id: "a", name: "Alpha" }, { id: "b", name: "Beta" }, { id: "c", name: "Gamma" }];
  const o = writingOptions(all, "b");
  assert.deepEqual(o.map((x) => x.label), ["Primary: Beta", "None (disabled)", "Alpha", "Gamma"]);
  assert.equal(defaultWriting(o, null, "b"), "b");
  assert.equal(defaultWriting(o, "c", "b"), "c");
  assert.equal(defaultWriting(o, "gone", "b"), "b");
  const none = writingOptions(all, null);
  assert.deepEqual(none.map((x) => x.label), ["None (disabled)", "Alpha", "Beta", "Gamma"]);
  assert.equal(defaultWriting(none, null, null), "none");
});
test("checkpoint helpers", () => {
  assert.equal(kb(900), "900 B"); assert.equal(kb(3600), "3.5 KB"); assert.equal(kb(80000), "78 KB"); assert.equal(kb(5 * 1048576), "5.0 MB");
  assert.equal(versionBase("lang", "x"), "/api/conlangs/x"); assert.equal(versionBase("script", "y"), "/api/scripts/y");
});
test("the create form: chosen settings win, suggestions fill the rest, a blank seed is random", () => {
  const r = createScriptBody({ name: "  Runes ", seed: "", language: "", tweaks: { family: "curvy" },
    proposals: [{ key: "family", value: "spikey" }, { key: "roundness", value: 0.2, evidence: "round" }], rnd: () => 0.5 });
  assert.deepEqual(r.body, { name: "Runes", seed: 2 ** 30, pins: { family: "curvy", roundness: 0.2 }, conlang_id: null });
  assert.deepEqual(r.applied.map((p) => p.key), ["roundness"]);
  assert.equal(createScriptBody({ name: "", seed: "42", language: "l1", tweaks: {} }).body?.conlang_id, "l1");
  assert.equal(createScriptBody({ name: "", seed: "42", language: "l1", tweaks: {} }).body?.seed, 42);
  assert.match(createScriptBody({ name: "", seed: "4x", language: "", tweaks: {} }).error || "", /whole number/);
  assert.ok(createScriptBody({ name: "", seed: "99999999999", language: "", tweaks: {} }).error);
  assert.deepEqual(HOW_OPTIONS.map((o) => o[0]), ["random", "words", "picture"]);
  assert.deepEqual(tweakDials(cat).map((d) => d.key), ["family", "roundness"]);        // the Style group only
});

let failed = 0;
for (const [n, f] of tests) { try { f(); console.log("ok  ", n); } catch (e) { failed++; console.log("FAIL", n, "\n    ", (e as Error).message.split("\n").slice(0, 4).join("\n     ")); } }
if (failed) { console.log(failed + " failed"); process.exit(1); }
console.log(tests.length + " passed");

test("Create like...: tweaks win over the preset, the preset wins over a description, sounds are left to the language", () => {
  const preset: ScriptPreset = { id: "x", label: "X", note: "", pins: { family: "boxy", direction: "rtl", consonants: 22, roundness: 0.2 } };
  const r = createScriptBody({ name: "", seed: "1", language: "", tweaks: { family: "curvy" }, preset,
    proposals: [{ key: "roundness", value: 1, evidence: "round" }, { key: "loops", value: 0.5, evidence: "loops" }] as any });
  assert.deepEqual(r.body?.pins, { family: "curvy", direction: "rtl", consonants: 22, roundness: 0.2, loops: 0.5 });
  const l = createScriptBody({ name: "", seed: "1", language: "l1", tweaks: {}, preset });
  assert.equal("consonants" in (l.body?.pins ?? {}), false);
});
