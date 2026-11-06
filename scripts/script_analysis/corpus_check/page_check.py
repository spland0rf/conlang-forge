"""Run the structural-signature, size tests and repair on the 26 letters the Generator v2 page draws (seed 7)."""
import corpus_load as CL, collections
import sig as SG, compound_gen as C
from repair_corpus import fix
from corpus_sheet import sheet
R = C.R; P = CL.page_records(); real = SG.known_signatures(); seen = {}; rows = []
for r in P:
    sg = SG.sig(SG.letter_strokes(r)); dup = seen.get(sg); seen.setdefault(sg, r["key"])
    wf, pr = C.white_fraction(r), C.primary_size(r); mv = C.max_void(r) if r["sk"]["kind"] in ("stem", "desc") else 0
    fail = [n for n, b in (("primary", pr < R["PRIMARY_MIN"]), ("white", wf > R["WHITE_MAX"]), ("void", mv > R["MAX_VOID"])) if b]
    N = how = None
    if fail and not dup: N, how = fix(r, sg)
    rows.append((r, sg in real, dup, wf, pr, mv, fail, N, how))
    print(r["key"], r["sk"]["kind"], "real-copy" if sg in real else "", ("dup of " + dup) if dup else "", "w%.2f p%.2f v%.0f" % (wf, pr, mv), fail, ("repaired " + str(how)) if N else (how or ""))
print(collections.Counter("dup" if x[2] else "real" if x[1] else "pass" if not x[6] else "repaired" if x[7] else "stuck" for x in rows))
items = []
for r, rl, dup, wf, pr, mv, fail, N, how in rows:
    if dup: continue
    items.append((r, "%s w%.2f p%.2f" % (r["key"], wf, pr), "#a33" if fail and not N else "#1f4e9c" if not fail else "#999999"))
    if N: items.append((N, "%s fixed x%.2f y%.2f" % (r["key"], how[0], how[1]), "#1f4e9c"))
sheet(items, "page_seed7.png")
