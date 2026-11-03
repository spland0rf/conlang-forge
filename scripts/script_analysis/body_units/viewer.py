"""Builds viewer.html: the real bodies cut into units, then newly generated bodies in context. usage: python3 viewer.py [out.html]"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
real = [{"n": f"{b['letter']} · {b['stroke']}", "g": b["glyph"], "a": b["attach"], "pts": b["pts"], "u": [[u["kind"], u["i0"], u["i1"], round(u["len"]), round(u["turn"]), 1 if u["cusp_before"] else 0] for u in b["units"]]} for b in json.load(open(os.path.join(HERE, "units.json")))]
gen = json.load(open(os.path.join(HERE, "bodies.json")))
tpl = open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8").read()
open(sys.argv[1] if len(sys.argv) > 1 else "viewer.html", "w", encoding="utf-8").write(tpl.replace("/*REAL*/[]", json.dumps(real, ensure_ascii=False, separators=(",", ":"))).replace("/*GEN*/[]", json.dumps(gen, separators=(",", ":"))))
print(len(real), len(gen))
