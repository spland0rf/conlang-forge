"""Catalogue of how real Devanagari body strokes connect (patterns.json -> HTML). usage: python3 viewer.py out.html"""
import json, os, sys
from collections import defaultdict
from mine import G, mine, orient
HERE = os.path.dirname(os.path.abspath(__file__))
def cls(desc):
    if desc == "free": return "free"
    t, rest = desc.split(":", 1); role, rest = rest.split(" ", 1); ori, where = rest.split("@")
    if role == "struct" and ori == "bar": return "top bar"
    if role == "struct" and ori == "vert": return "descender"
    if role == "body": return "another body (%s)" % ("crossing" if t == "cross" else "joined")
    return role
def key(p):
    mids = sorted({cls(m[1]) for m in p["mid"]})
    return (cls(p["start"]), cls(p["end"]), tuple(mids), p["self_cross"] > 0)
P = mine(); groups = defaultdict(list)
for p in P: groups[key(p)].append(p)
byg = {(l["glyph"], l["variant"]): l for l in G}
cards = []
for k, ps in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    ex = []
    for p in ps[:4]:
        l = byg[(p["glyph"], p["variant"])]
        sid = p["stroke"]
        ex.append({"g": l["glyph"], "i": l["iast"], "sid": sid, "strokes": l["strokes"],
                   "j": [[j["t"], j["x"], j["y"]] for j in l["junctions"]]})
    cards.append({"start": k[0], "end": k[1], "mids": list(k[2]), "loop": k[3], "n": len(ps), "ex": ex})
tpl = open(os.path.join(HERE, "viewer_template.html")).read()
open(sys.argv[1], "w").write(tpl.replace("/*DATA*/null", json.dumps(cards, ensure_ascii=False)))
print(len(cards), "patterns;", sum(c["n"] for c in cards), "body strokes")
