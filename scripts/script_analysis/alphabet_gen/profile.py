"""Shape profile of the real Devanagari letters (the 49 records of the stroke graph): how letters divide into skeleton types, how many
body strokes they have, which connection patterns occur. This is the target distribution the alphabet sampler is aligned to.
usage: python3 profile.py -> profile.json"""
import json, os, re, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "../../../conlang_forge/script/forms/devanagari_graph.json")))["letters"]
V = re.compile(r"M\s*([\d.]+)\s+([\d.]+)\s*V\s*([\d.]+)")
H = re.compile(r"M\s*([\d.]+)\s+([\d.]+)\s*H\s*([\d.]+)")

def classify(l):
    S = l["strokes"]; f = {}
    f["bar"] = any(s[0] == "struct" and H.fullmatch(s[1].strip()) and abs(float(H.fullmatch(s[1].strip()).group(2)) - 20) < .5 and abs(float(H.fullmatch(s[1].strip()).group(3)) - float(H.fullmatch(s[1].strip()).group(1))) > 30 for s in S)
    verts = [(s[0], float(m.group(3)) - float(m.group(2))) for s in S for m in [V.match(s[1].strip())] if m and s[1].strip().count(" ") <= 3 and "C" not in s[1] and "Q" not in s[1]]
    f["stem"] = any(abs(abs(v) - 62) < 14 or abs(v) > 50 for _, v in verts)
    f["desc"] = any(r == "struct" and 0 < v <= 45 for r, v in verts)
    f["connector"] = any(s[0] == "struct" and ("Q" in s[1] or "C" in s[1]) and not s[1].strip().startswith("M 8") for s in S)
    f["second_form"] = any(s[0] == "second" for s in S)
    f["accent"] = any(s[0] == "accent" for s in S)
    f["n_body"] = sum(1 for s in S if s[0] == "body")
    f["n_strokes"] = len(S)
    f["self_cross"] = any(j["t"] == "cross" for j in l["junctions"])
    f["skeleton"] = "barless" if not f["bar"] else "stem" if f["stem"] else "desc" if f["desc"] else "hang"
    return f

def main():
    F = [classify(l) for l in G]
    n = len(F)
    def share(key): c = Counter(f[key] for f in F); return {str(k): round(v / n, 3) for k, v in sorted(c.items(), key=lambda kv: -kv[1])}
    prof = {"n": n, "skeleton": share("skeleton"), "n_body": share("n_body"), "connector": share("connector"), "second_form": share("second_form"),
            "accent": share("accent"), "cross": share("self_cross"),
            "letters": [{"iast": l["iast"], "variant": l["variant"], **classify(l)} for l in G]}
    # connection patterns of the body strokes (from the mined catalogue)
    P = json.load(open(os.path.join(HERE, "../body_connections/patterns.json")))
    prof["body_start"] = dict(Counter(p["start"].split("@")[0].split(":")[1].split(" ")[0] + ":" + p["start"].split(":")[0] if p["start"] != "free" else "free" for p in P))
    prof["body_end_free"] = round(sum(p["end"] == "free" for p in P) / len(P), 3)
    json.dump(prof, open(os.path.join(HERE, "profile.json"), "w"), indent=1, ensure_ascii=False)
    for k in ("skeleton", "n_body", "connector", "second_form", "accent", "cross"): print(k, prof[k])
    print("body start", prof["body_start"], "free end", prof["body_end_free"])
    print([ (x["iast"], x["skeleton"]) for x in prof["letters"] if x["skeleton"] in ("barless",)])
main()
