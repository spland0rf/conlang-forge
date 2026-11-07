"""Mine how each body stroke of the 49 real Devanagari letters connects to the rest of its letter (from the stroke graph):
what sits at its start, at its end and along its middle -- junction type, partner role/orientation, where on the partner.
usage: python3 mine.py  -> patterns.json"""
import json, os, re
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "../../../conlang_forge/script/forms/devanagari_graph.json")))["letters"]

def orient(role, d):
    if re.fullmatch(r"M[\d. ]+H[\d.]+", d.strip()):
        return "bar" if abs(float(d.split()[1]) - 20) < 1.5 else "horiz"
    if re.fullmatch(r"M[\d. ]+V[\d.]+", d.strip()): return "vert"
    return "curve"

def side(w, at):
    if w == "start": return "start"
    if w == "end": return "end"
    return "mid-early" if at < .34 else "mid-late" if at > .66 else "mid"

def mine():
    pats = []
    for l in G:
        S = {s[2]: s for s in l["strokes"]}
        for sid, (role, d, _) in S.items():
            if role != "body": continue
            ends = {"start": "free", "end": "free"}; mids = []; selfx = 0
            for j in l["junctions"]:
                mem = [m for m in j["members"] if m["stroke"] == sid]
                if not mem: continue
                oth = [m for m in j["members"] if m["stroke"] != sid]
                if not oth:                                         # the stroke crosses itself
                    selfx += 1; continue
                o = oth[0]; od = S[o["stroke"]]
                desc = "%s:%s %s@%s" % (j["t"], od[0], orient(od[0], od[1]), side(o["where"], o["at"]))
                m = mem[0]
                if m["where"] in ("start", "end"): ends[m["where"]] = desc
                else: mids.append((side(m["where"], m["at"]), desc))
            pats.append({"glyph": l["glyph"], "iast": l["iast"], "variant": l["variant"], "stroke": sid, "start": ends["start"], "end": ends["end"],
                         "mid": sorted(mids), "self_cross": selfx, "d": d})
    return pats

if __name__ == "__main__":
    P = mine()
    json.dump(P, open(os.path.join(HERE, "patterns.json"), "w"), ensure_ascii=False, indent=0)
    print(len(P), "body strokes")
    print("start:", Counter(p["start"] for p in P).most_common())
    print("end:", Counter(p["end"] for p in P).most_common())
    print("mids:", Counter(m for p in P for m in p["mid"]).most_common(12))
    print("self cross:", Counter(p["self_cross"] for p in P))
    print("free-free:", sum(p["start"] == "free" and p["end"] == "free" for p in P), "free-end:", sum(p["end"] == "free" for p in P))
