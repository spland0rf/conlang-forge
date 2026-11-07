import sys, json, time, collections
from corpus_load import records
import sig as SG, compound_gen as C
R = C.R
recs = records(); real = SG.known_signatures(); t = time.time()
rows = []
for r in recs:
    try:
        sg = SG.sig(SG.letter_strokes(r))
        pr = C.primary_size(r); wf = C.white_fraction(r); mv = C.max_void(r) if r["sk"]["kind"] in ("stem", "desc") else None
    except Exception as e:
        rows.append({"r": r, "err": repr(e)}); continue
    rows.append({"r": r, "sig": sg, "real": sg in real, "primary": pr, "white": wf, "void": mv,
                 "fail": [n for n, bad in (("primary", pr < R["PRIMARY_MIN"]), ("white", wf > R["WHITE_MAX"]), ("void", mv is not None and mv > R["MAX_VOID"])) if bad]})
print("time", round(time.time() - t, 1), "errors", sum("err" in x for x in rows))
ok = [x for x in rows if "err" not in x]
cnt = collections.Counter(x["sig"] for x in ok)
print("letters", len(ok), "| distinct structures", len(cnt), "| copies of a real letter", sum(x["real"] for x in ok))
print("fail size tests:", sum(bool(x["fail"]) for x in ok), collections.Counter(f for x in ok for f in x["fail"]))
# distinct, non-real structures
firsts = {}
for x in ok:
    if not x["real"]: firsts.setdefault(x["sig"], x)
print("distinct non-real structures:", len(firsts), "| of which pass size tests:", sum(not x["fail"] for x in firsts.values()), "| fail:", sum(bool(x["fail"]) for x in firsts.values()))
print("failures by kind among distinct:", collections.Counter(tuple(x["fail"]) for x in firsts.values() if x["fail"]))
print("by skeleton:", collections.Counter(x["r"]["sk"]["kind"] for x in firsts.values()))
json.dump([{"style": x["r"]["style"], "idx": x["r"]["idx"], "fail": x["fail"], "primary": round(x["primary"], 2), "white": round(x["white"], 2), "void": x["void"] and round(x["void"], 1)} for x in firsts.values()], open("distinct.json", "w"))
