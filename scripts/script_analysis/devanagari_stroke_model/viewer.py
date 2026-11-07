"""Builds viewer.html: real Devanagari letters (Unicode glyph, romanisation, stroke form with colours and junction marks), then a
generated set from Generator v2's corpus. usage: python3 viewer.py [out.html] [n_generated] [seed]"""
import json, random, sys
sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from conlang_forge.script import stroke_graph as G

out = sys.argv[1] if len(sys.argv) > 1 else "viewer.html"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 60
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7

def pack(ss, js):
    return {"s": [[t.get("role", "body"), [[round(x, 3), round(y, 3)] for x, y in t["p"]]] for t in ss], "j": [[t, round(x, 3), round(y, 3)] for t, x, y in js]}

real = []
for l in G.real_letters():
    d = pack(G.real_strokes(l["glyph"], l["variant"], keep_bar=True), G.real_junctions(l["glyph"], l["variant"]))
    d.update(g=l["glyph"], n=l["iast"] + (" · " + l["variant"] if l["variant"] else ""))
    real.append(d)
r, sts, gen, seen = random.Random(seed), G.corpus(), [], set()
while len(gen) < N:
    st = r.choice(sts); L = r.choice(st["letters"])
    if L["key"] in seen: continue
    seen.add(L["key"])
    items = [tuple(i) for i in L["s"] if not G.is_bar(i[0], i[1])]
    bar = None if G.no_bar(L["key"]) else G.own_bar(items)
    d = pack(G.strokes_of(items + ([("struct", bar)] if bar else []), keep_bar=True), G.junctions(L))
    d.update(g="", n=f"G{len(gen) + 1} · style {st['id']}", k=L["key"].replace("|-|", "|").strip("|"))
    gen.append(d)
html = open(__file__.replace("viewer.py", "viewer_template.html"), encoding="utf-8").read()
html = html.replace("/*REAL*/[]", json.dumps(real, ensure_ascii=False, separators=(",", ":"))).replace("/*GEN*/[]", json.dumps(gen, ensure_ascii=False, separators=(",", ":")))
open(out, "w", encoding="utf-8").write(html)
print(out, len(real), len(gen))
