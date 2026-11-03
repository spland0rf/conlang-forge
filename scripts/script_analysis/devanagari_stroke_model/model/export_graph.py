"""letters.json -> conlang_forge/script/forms/devanagari_graph.json (the real-letter graph the engine loads)."""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(H, "letters.json")))
out = {"box": {"w": 100, "h": 100, "top": 20, "base": 88}, "letters": [{"glyph": l["glyph"], "iast": l["iast"], "variant": l["variant"],
       "strokes": [[s["role"], s["d"], s["id"]] for s in l["strokes"]], "junctions": [{"t": j["t"], "x": j["x"], "y": j["y"], "members": j["members"]} for j in l["junctions"]]} for l in L]}
dst = os.path.join(H, "../../../../conlang_forge/script/forms/devanagari_graph.json")
json.dump(out, open(dst, "w"), separators=(",", ":"), ensure_ascii=False)
print(len(L))
