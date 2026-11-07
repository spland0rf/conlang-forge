"""Corpus (gen_corpus.js output) -> conlang_forge/script/forms/devanagari_corpus.json. usage: python3 export_corpus.py corpus_full.json"""
import json, sys, os
d = json.load(open(sys.argv[1]))
out = {"version": 1, "source": d["source"], "box": d["box"], "styles": [{"id": s["id"], "mutated": s["mutated"], "letters": [
    {"s": [[x["role"], x["d"]] for x in l["s"]], "j": [[j["t"], j["x"], j["y"]] for j in l["j"]], "key": l["key"], "acc": l["acc"]} for l in s["letters"]]} for s in d["styles"]]}
dst = os.path.join(os.path.dirname(__file__), "../../../../conlang_forge/script/forms/devanagari_corpus.json")
json.dump(out, open(dst, "w"), separators=(",", ":"))
print(len(out["styles"]), sum(len(s["letters"]) for s in out["styles"]))
