"""Top-down alphabet sampler. Reads spec.json (the mix of letter families and sub-types), turns the shares into exact counts, and fills each
bucket with its own constructive builder -- so the mix is decided first and randomness only fills in the unspecified details. Fixed rules live
in compound_gen/rules.py. usage: python3 sampler.py [spec.json] -> alphabet.json"""
import json, math, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "compound_gen"))
import compound_gen as C, compound_half as H
from rules import R
BG = C.BG; C.RAW_MODE["ct"] = True
sys.path.insert(0, os.path.join(HERE, ".."))
import sig as SG
sys.path.insert(0, os.path.join(HERE, "..", "compound_gen"))
import repair as RP     # repair step for letters that fail only the size / whitespace rules
REPAIRS = [0]       # structural duplicate test (same strokes, same joins, attachment slides ignored)

def allocate(shares, n):
    """Largest-remainder rounding of shares to whole counts summing to n."""
    tot = sum(shares.values()); raw = {k: v / tot * n for k, v in shares.items()}
    out = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[: n - sum(out.values())]: out[k] += 1
    return out

def pick(rng, weights): return rng.choices(list(weights), list(weights.values()))[0]

def rejected_ink():
    ink = []
    for f, idx in (("letters_v5.json", C.REJECTED_V5), ("letters_v6.json", C.REJECTED_V6), ("letters_v7.json", C.REJECTED_V7)):
        p = os.path.join(HERE, "..", "compound_gen", f)
        if os.path.exists(p):
            v = json.load(open(p))
            for i in idx: ink.append([q for P in v[i - 1]["strokes"] for q in C.thin2(P)])
    return ink

def checkpoint_ink():
    out = []
    for f in ("letters.json", "letters_half.json"):
        p = os.path.join(HERE, "..", "compound_gen", f)
        if os.path.exists(p):
            for v in json.load(open(p)): out.append([q for P in v["strokes"] for q in C.thin2(P)])
    return out

def main(spec_path):
    spec = json.load(open(spec_path)); rng = random.Random(spec["seed"]); n = spec["size"]
    counts = allocate(spec["skeleton_share"], n); budget = spec["per_bucket_try_budget"]
    ink = rejected_ink() + (checkpoint_ink() if spec.get("avoid_checkpoint") else []); fams = []; out = []; stats = {}
    seen_sig = SG.known_signatures()
    max_fam = spec.get("max_per_family", 1)
    for bucket, need in counts.items():
        t0 = time.time(); tries = built = 0; got = 0
        three_left = round(need * spec["half"]["three_share"]) if bucket == "half" else 0
        joins = allocate(spec["half"]["join_at"], need) if bucket == "half" else {}
        while got < need and tries < budget * max(1, need) // 2:
            tries += 1
            if bucket == "half":
                three = three_left > 0 and (need - got) <= three_left or (three_left > 0 and rng.random() < .6)
                jn = next((k for k, v in joins.items() if v > 0), None)
                L = H.build(rng, three, join_at=jn, right_variant=pick(rng, spec["half"]["right_form"]))
                if not L: continue
                fam = None
            else:
                recipe = pick(rng, spec["skeleton_recipes"]); L = C.build(rng, recipe, "bar" if bucket == "hang" else bucket)
                if not L: continue
                if not C.valid(L):
                    # too small / too sparse but otherwise sound: repair it (scale and slide the body group, same topology) instead of discarding it
                    if not C.valid(L, size_rules=False): continue
                    s_pre = SG.sig(SG.letter_strokes(L))
                    if s_pre in seen_sig: continue          # same strokes and joins as a letter we already have: not worth repairing
                    L, _ = RP.repair_fast(L, s_pre)
                    if L is None: continue
                    REPAIRS[0] += 1
                fam = C.family(L)
                if sum(1 for g in fams if C.same_family(fam, g)) >= max_fam: continue
            built += 1
            pts = [p for P in L["strokes"] for p in C.thin2(P)] + ([p for P in L.get("struct", []) for p in C.thin2(P)] if bucket == "half" else [])
            if any(BG.chamfer(pts, q) < R["INK_MIN_DIST"] for q in ink): continue
            sg = SG.sig(SG.letter_strokes(L))
            if sg in seen_sig: continue
            seen_sig.add(sg)
            ink.append(pts); got += 1
            if fam: fams.append(fam)
            if bucket == "half":
                if L["recipe"].endswith("-3"): three_left -= 1
                joins[L["join"]] = joins.get(L["join"], 0) - 1
            if "bar" not in L or L.get("bar") is None and bucket != "half":
                sk = L["sk"]; x0, x1 = C.bar_span(L, min(p[0] for P in L["strokes"] for p in P)); L["bar"] = [round(x0, 1), round(x1, 1)]
            rec = {"skel": L["skel"], "recipe": L["recipe"], "sk": L["sk"], "bar": L.get("bar"), "struct": L.get("struct"), "descs": [],
                   "J": [[j[0], round(j[1], 1), round(j[2], 1)] for j in L["J"]], "seqs": L["seqs"], "bucket": bucket,
                   "strokes": [[[round(p[0], 1), round(p[1], 1)] for p in P] for P in L["strokes"]]}
            if L.get("join"): rec["join"] = L["join"]
            out.append(rec)
        stats[bucket] = {"wanted": need, "got": got, "tries": tries, "built": built, "sec": round(time.time() - t0, 1)}
    json.dump({"spec": spec, "stats": stats, "letters": out}, open(os.path.join(HERE, "alphabet.json"), "w"), separators=(",", ":"))
    print(json.dumps(stats))
    print(len(out), "letters;", "yield per try:", {k: round(v["got"] / max(1, v["tries"]), 4) for k, v in stats.items()})
    print("repaired candidates used:", REPAIRS[0])

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "spec.json"))
