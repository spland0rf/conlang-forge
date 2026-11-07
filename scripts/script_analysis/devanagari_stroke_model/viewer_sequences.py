"""Builds viewer_sequences.html: each real letter as a row of frames, one per step, the newest stroke red (like the hand-drawn sheets).
usage: python3 viewer_sequences.py [out.html]"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "../../..")))
from conlang_forge.script import stroke_graph as G
L = {(l["glyph"], l["variant"]): l for l in json.load(open(os.path.join(HERE, "model/letters.json")))}
rows = []
for q in json.load(open(os.path.join(HERE, "sequences.json"))):
    key = next(k for k in L if k[0] == q["glyph"] and ((k[1] or "") and q["name"].endswith(k[1]) or (not k[1] and " " not in q["name"] or (not k[1] and q["name"].split(" ")[0] == L[k]["iast"] and False))))
    l = L[key]
    S = {s["id"]: [[round(x, 3), round(y, 3)] for x, y in G.to_unit(G.polyline(s["d"]))] for s in l["strokes"]}
    rows.append({"g": q["glyph"], "n": q["name"], "st": q["status"], "steps": q["steps"], "units": q["units"], "S": S})
tpl = open(os.path.join(HERE, "viewer_sequences_template.html"), encoding="utf-8").read()
open(sys.argv[1] if len(sys.argv) > 1 else "viewer_sequences.html", "w", encoding="utf-8").write(tpl.replace("/*ROWS*/[]", json.dumps(rows, ensure_ascii=False, separators=(",", ":"))))
print(len(rows))
