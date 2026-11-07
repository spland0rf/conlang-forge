"""Adapter: the imported Devanagari corpus (SVG path strings with roles) -> compound_gen-style letter records."""
import json, os, re, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..")); sys.path.insert(0, os.path.join(HERE, "..", "compound_gen"))
import script_config as SC
CORPUS = SC.path("corpus"); BAR_Y = SC.get()["frame"]["bar_y"]; BASE_Y = SC.get()["frame"]["base_y"]

def parse(d):
    t = re.findall(r"[MLHVCQZ]|-?\d+(?:\.\d+)?", d); i = 0; cur = (0.0, 0.0); P = []; cmd = None
    def num(): 
        nonlocal i; v = float(t[i]); i += 1; return v
    while i < len(t):
        if re.match(r"[A-Z]", t[i]): cmd = t[i]; i += 1
        if cmd == "M": cur = (num(), num()); P.append(cur); cmd = "L"
        elif cmd == "L": cur = (num(), num()); P.append(cur)
        elif cmd == "H": cur = (num(), cur[1]); P.append(cur)
        elif cmd == "V": cur = (cur[0], num()); P.append(cur)
        elif cmd == "C":
            c1 = (num(), num()); c2 = (num(), num()); e = (num(), num())
            for k in range(1, 13):
                u = k / 12; P.append(tuple((1-u)**3*cur[a] + 3*(1-u)**2*u*c1[a] + 3*(1-u)*u*u*c2[a] + u**3*e[a] for a in (0, 1)))
            cur = e
        elif cmd == "Q":
            c1 = (num(), num()); e = (num(), num())
            for k in range(1, 9):
                u = k / 8; P.append(tuple((1-u)**2*cur[a] + 2*(1-u)*u*c1[a] + u*u*e[a] for a in (0, 1)))
            cur = e
        else: i += 1
    return P

def plen(P): return sum(math.dist(a, b) for a, b in zip(P, P[1:]))

def build_record(raw, J, **meta):
    """raw: [(role, polyline)], J: junction list [kind, x, y]."""
    bars = [P for r, P in raw if r == "struct" and len(P) == 2 and abs(P[0][1] - P[1][1]) < .5 and abs(P[0][1] - BAR_Y) < 1.5 and abs(P[0][0] - P[1][0]) > 20]
    bar = [min(min(p[0] for p in P) for P in bars), max(max(p[0] for p in P) for P in bars)] if bars else None
    stems = [(r, P) for r, P in raw if r != "struct" and len(P) == 2 and abs(P[0][0] - P[1][0]) < .5 and plen(P) >= BASE_Y - BAR_Y - 13 and min(P[0][1], P[1][1]) < BAR_Y + 4]
    stem_item = stems[0] if stems else None
    rest = [(r, P) for r, P in raw if not (r == "struct" and P in bars) and not (stem_item and P is stem_item[1])]
    descs = [P for r, P in raw if r == "struct" and len(P) == 2 and abs(P[0][0] - P[1][0]) < .5 and P[0][1] < BAR_Y + 4]
    if stems: sk = {"kind": "stem", "S": stems[0][1][0][0]}
    elif descs: sk = {"kind": "desc", "x": descs[0][0][0]}
    else: sk = {"kind": "hang"}
    body = [P for r, P in rest if len(P) >= 2 and r != "accent"]       # struct descenders / connectors travel with the body group
    body_roles = [r for r, P in rest if len(P) >= 2 and r != "accent"]
    d = {"bar": bar, "sk": sk, "stem_item": stem_item, "strokes": body, "stroke_roles": body_roles, "struct": [P for r, P in rest if r == "accent" and len(P) >= 2], "roles": [r for r, _ in raw], "J": J}
    d.update(meta); return d

def records():
    d = json.load(open(CORPUS)); out = []
    for st in d["styles"]:
        for n, l in enumerate(st["letters"]):
            out.append(build_record([(r, parse(p)) for r, p in l["s"]], l["j"], style=st["id"], idx=n, key=l.get("key"), acc=l.get("acc")))
    return out

def page_records(path=os.path.join(HERE, "page_seed7_letters.json")):
    """The letters the 'Generated Devanagari-like script' page draws (seed 7, five style configs), read out of the rendered page."""
    out = []
    for n, l in enumerate(json.load(open(path))["letters"]):
        raw = [(q["cls"].split()[0], parse(q["d"])) for q in l["paths"] if q["cls"].split()[:1] and q["cls"].split()[0] in ("body", "second", "struct", "accent")]
        J = [["red" if "#c9372c" in m.split("<circle")[1] else "touch", float(re.search(r'cx="([\d.]+)"', m).group(1)), float(re.search(r'cy="([\d.]+)"', m).group(1))] for m in l["marks"] if "<circle" in m]
        out.append(build_record(raw, J, style=0, idx=n, key=l["head"]))
    return out
if __name__ == "__main__":
    R = records(); print(len(R), "letters;", sum(1 for r in R if r["bar"]), "with bar;", {k: sum(1 for r in R if r["sk"]["kind"] == k) for k in ("stem", "desc", "hang")})
