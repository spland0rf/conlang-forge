// Run with: npx tsx tests/admin.test.ts
import assert from "node:assert/strict";
import { DAY, auditDetail, bucketTotal, compact, labelEvery, makeBuckets, niceMax, parseCap, parsePlanLimits, parsePrices, parseUserLimits, purposeColor, usageRange, usedPurposes, PURPOSES } from "../src/adminModel";
import { ago, fmtLimitTokens, fmtUsd } from "../src/format";

const tests: [string, () => void][] = [];
const test = (n: string, f: () => void) => tests.push([n, f]);

test("user limits: blank uses the plan, a number overrides, unlimited is -1", () => {
  const r = parseUserLimits({ tokens_per_day: " 5000 ", tokens_per_month: "Unlimited", requests_per_minute: "", max_conlangs: "3" });
  assert.deepEqual(r, { tokens_per_day: 5000, tokens_per_month: -1, requests_per_minute: null, max_conlangs: 3, max_output_tokens: null });
  assert.throws(() => parseUserLimits({ tokens_per_day: "1.5" }), /whole numbers/);
  assert.throws(() => parseUserLimits({ max_conlangs: "lots" }), /whole numbers/);
});
test("plan limits: blank is no limit", () => {
  assert.equal(parsePlanLimits({ tokens_per_day: "" }).tokens_per_day, null);
  assert.equal(parsePlanLimits({ tokens_per_day: "100000" }).tokens_per_day, 100000);
  assert.throws(() => parsePlanLimits({ tokens_per_day: "-1.2" }));
});
test("cap and prices", () => {
  assert.equal(parseCap(""), null); assert.equal(parseCap(" 250000 "), 250000);
  assert.throws(() => parseCap("12k"), /whole number/);
  assert.deepEqual(parsePrices('{"m": {"in": 3}}'), { m: { in: 3 } });
  assert.deepEqual(parsePrices(""), {});
  assert.throws(() => parsePrices("{oops"), /valid JSON/); assert.throws(() => parsePrices("[1]"), /valid JSON/);
});
test("usage buckets fill every day and add up", () => {
  const now = Date.UTC(2026, 9, 15, 13, 0);
  const { start, end } = usageRange(3, now);
  assert.equal(start, Date.UTC(2026, 9, 12)); assert.ok(end > now);
  const b = makeBuckets([{ bucket_start: start, grp: "translate.reduce", quota_tokens: 100, cost_micro_usd: 5 }, { bucket_start: start, grp: "translate.reduce", quota_tokens: 50, cost_micro_usd: 2 },
    { bucket_start: start + 2 * DAY, grp: "book.polish", quota_tokens: 7, cost_micro_usd: 1 }, { bucket_start: start + DAY, grp: "script.describe", quota_tokens: 20, cost_micro_usd: 1 }, { bucket_start: start + DAY, grp: "script.describe_image", quota_tokens: 30, cost_micro_usd: 1 }, { bucket_start: start - DAY, grp: "x", quota_tokens: 9, cost_micro_usd: 9 }], start, end);
  assert.equal(b.length, 4);
  assert.deepEqual(b[0].parts, { "translate.reduce": 150 }); assert.equal(b[0].cost, 7); assert.equal(bucketTotal(b[2], PURPOSES), 7);
  assert.deepEqual(b[1].parts, { "script.describe": 50 });          // words and picture are one series
  assert.deepEqual(usedPurposes(b), ["book.polish", "translate.reduce", "script.describe"]);
});
test("colour follows the purpose, not its rank", () => {
  assert.equal(purposeColor("exemplar.analyze"), "#2a78d6"); assert.equal(purposeColor("translate.reduce"), purposeColor("translate.reduce"));
  assert.notEqual(purposeColor("book.polish"), purposeColor("translate.smooth"));
});
test("axis numbers", () => {
  assert.equal(niceMax(0), 1); assert.equal(niceMax(1), 1); assert.equal(niceMax(130), 200); assert.equal(niceMax(4100), 5000); assert.equal(niceMax(6000), 10000);
  assert.equal(compact(950), "950"); assert.equal(compact(1500), "1.5k"); assert.equal(compact(12000), "12k"); assert.equal(compact(2500000), "2.5M");
  assert.equal(labelEvery(14), 2); assert.equal(labelEvery(7), 1); assert.equal(labelEvery(60), 9);
});
test("money, time and tokens read like the website", () => {
  assert.equal(fmtUsd(0), "$0.00"); assert.equal(fmtUsd(5000), "<$0.01"); assert.equal(fmtUsd(2_500_000), "$2.50"); assert.equal(fmtUsd(25_000_000), "$25");
  const now = 1_000_000_000_000;
  assert.equal(ago(null), "never"); assert.equal(ago(now - 30_000, now), "just now"); assert.equal(ago(now - 600_000, now), "10 min ago");
  assert.equal(ago(now - 3 * 3600_000, now), "3 h ago"); assert.equal(ago(now - 3 * 86400_000, now), "3 days ago");
  assert.equal(fmtLimitTokens(null), "no limit"); assert.equal(fmtLimitTokens(12_345), "12k"); assert.equal(fmtLimitTokens(2_500_000), "2.5M");
});
test("audit details are one readable line", () => {
  assert.equal(auditDetail({ seed: 5, n: 2, x: { a: 1 } }), 'seed: 5, n: 2, x: {"a":1}'); assert.equal(auditDetail(undefined), "");
});

let failed = 0;
for (const [n, f] of tests) { try { f(); console.log("ok  ", n); } catch (e) { failed++; console.log("FAIL", n, "\n    ", (e as Error).message.split("\n").slice(0, 4).join("\n     ")); } }
if (failed) { console.log(failed + " failed"); process.exit(1); }
console.log(tests.length + " passed");
