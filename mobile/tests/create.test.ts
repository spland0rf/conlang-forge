import assert from "node:assert/strict";
import { dialsFromConfig, forgeBody, latestOnly, meterFraction, meterText, parseSeed, pinsFrom, sampleBody, sampleLines, shapedLines, rollSeed, EMPTY_MEASURE } from "../src/createModel";

let n = 0;
const ok = (name: string, f: () => void) => { f(); n++; console.log("ok  ", name); };

const config = { "morphology.typology": ["isolating", "fusional"], "syntax.word_order": ["SOV", "SVO"], "syntax.adjective_order": ["adjective-noun", "noun-adjective"],
  "phonology.stress": ["initial", "none"], "morphology.numeral_base": [5, 8, 10, 12, 20], name: null };

ok("dials follow the server config, in website order, with friendly labels", () => {
  const d = dialsFromConfig(config as any);
  assert.deepEqual(d.map((x) => x.key), ["morphology.typology", "syntax.word_order", "syntax.adjective_order", "phonology.stress", "morphology.numeral_base"]);
  assert.equal(d[1].options[1].label, "SVO: Subject, verb, object (like English)");
  assert.equal(d[2].options[0].label, "Before the noun");
  assert.equal(d[3].options[1].label, "Even, no stress");
  assert.equal(d[4].options.find((o) => o.value === "12")?.label, "12 (dozens)");
  assert.deepEqual(dialsFromConfig(undefined), []);
  assert.equal(dialsFromConfig({ "phonology.stress": ["initial"] } as any).length, 1);
});

ok("seeds: blank is left to the server, digits parse, junk and huge values are refused", () => {
  assert.deepEqual(parseSeed("  "), {});
  assert.deepEqual(parseSeed(" 42 "), { seed: 42 });
  assert.deepEqual(parseSeed("0"), { seed: 0 });
  assert.ok(parseSeed("-1").error && parseSeed("1.5").error && parseSeed("abc").error);
  assert.ok(parseSeed("2147483648").error);
  assert.equal(parseSeed("2147483647").seed, 2147483647);
  assert.equal(rollSeed(() => 0.5), String(2 ** 30));
  assert.ok(Number(rollSeed(() => 0.999999999)) <= 2147483647);
});

ok("pins: empty choices dropped, numeric ones become numbers", () => {
  assert.deepEqual(pinsFrom({ "syntax.word_order": "SOV", "phonology.stress": "", "morphology.numeral_base": "12" }), { "syntax.word_order": "SOV", "morphology.numeral_base": 12 });
});

ok("forge body", () => {
  assert.deepEqual(forgeBody({ name: " Ekki ", seed: "", choices: {} }).body, { name: "Ekki", pins: {} });
  assert.deepEqual(forgeBody({ name: "", seed: "7", choices: { "syntax.word_order": "VSO" } }).body, { name: "", pins: { "syntax.word_order": "VSO" }, seed: 7 });
  assert.ok(forgeBody({ name: "", seed: "x", choices: {} }).error);
});

ok("sample body: lines trimmed, model only when available and asked for", () => {
  assert.deepEqual(sampleLines("  korash vael | the old road \n\n tume\n"), ["korash vael | the old road", "tume"]);
  const base = { name: "", seed: "", choices: {}, sample: "a b\n c d", readGrammar: true, modelAvailable: true };
  assert.deepEqual(sampleBody(base).body, { texts: ["a b", "c d"], pins: {}, name: "", use_model: true });
  assert.equal((sampleBody({ ...base, modelAvailable: false }).body as any).use_model, false);
  assert.equal((sampleBody({ ...base, readGrammar: false }).body as any).use_model, false);
  assert.equal(sampleBody({ ...base, sample: " \n " }).error, "Paste some sample text first.");
  assert.ok(sampleBody({ ...base, seed: "no" }).error);
  assert.equal((sampleBody({ ...base, seed: "5" }).body as any).seed, 5);
});

ok("meter wording and fill", () => {
  assert.match(meterText(EMPTY_MEASURE), /^Aim for about 40 syllables/);
  assert.match(meterText({ syllables: 3, words: 1, min: 8, target: 40, level: "none" }), /^3 of 40 syllables\. Too short/);
  assert.match(meterText({ syllables: 20, words: 8, min: 8, target: 40, level: "partial" }), /Enough to shape some settings/);
  assert.match(meterText({ syllables: 55, words: 20, min: 8, target: 40, level: "good" }), /^55 syllables, past the 40 target/);
  assert.equal(meterFraction({ syllables: 20, words: 1, min: 8, target: 40, level: "partial" }), 0.5);
  assert.equal(meterFraction({ syllables: 90, words: 1, min: 8, target: 40, level: "good" }), 1);
  assert.equal(meterFraction(EMPTY_MEASURE), 0);
});

ok("shaped summary", () => {
  const l = shapedLines({ applied: [{ label: "Stress", proposed_show: "initial", evidence: "most words start loud" }], kept: [{ label: "Sentence order", proposed_show: "SOV", current_show: "SVO" }], notes: ["n1"] });
  assert.equal(l.headline, "The sample decided 1 setting:");
  assert.deepEqual(l.applied, ["Stress: initial (most words start loud)"]);
  assert.deepEqual(l.kept, ["Sentence order: kept SVO (sample suggested SOV)"]);
  assert.match(shapedLines({ applied: [], kept: [], notes: [] }).headline, /made at random/);
  assert.match(shapedLines({ applied: [{ label: "a", proposed_show: "b" }, { label: "c", proposed_show: "d" }], kept: [], notes: [] }).headline, /2 settings/);
});

ok("only the newest slow answer is used", () => {
  const g = latestOnly<number>();
  const a = g.next(), b = g.next();
  assert.equal(g.isLatest(a), false);
  assert.equal(g.isLatest(b), true);
});

console.log(`all ${n} passed`);
