"""Write a Markdown review sheet for a root map: python scripts/review_sheet.py rootmap.json out.md"""
import json
import sys

rm = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2]
sib = {f: g for g, fs in rm["sibling_groups"].items() for f in fs}
st = rm["stats"]
L = ["# Root map review sheet", "",
     f"{st['families']} families ({st['sibling_groups']} sibling groups), largest family {st['largest_family']} roots, "
     f"{st['root_groups']} root groups in all. {st['derived']} derived words, {st['compounds']} compounds.", "",
     "Which derived words and compounds become independent roots in a given language is decided per language by "
     "word frequency (plan.py); this sheet shows the idealised map.", ""]
SEMANTIC = {"FEMALE", "MALE", "OPPOSITE", "NEG", "REVERSE", "DIMIN", "AUGMENT", "YOUNG"}
rec, rf, pend = rm["recipes"], rm["root_family"], rm.get("pending", {})


def root_of(c):
    while True:
        node = rec.get(c)
        if node is None or node["op"] != "derive":
            return c
        c = node["base"] if isinstance(node["base"], str) else None
        if c is None:
            return None


also = {}
for w, node in rec.items():
    if node["op"] == "derive" and node["rel"] in SEMANTIC and isinstance(node["base"], str):
        r = root_of(node["base"])
        if r in rf:
            also.setdefault(rf[r], []).append(f"{w} ({node['base']} +{node['rel']})")
L += ["## Conceptual families", "",
      "A family = roots that share a stem (at most 5; 6 only with very strong affinity). *Sibling group* = families split from one natural group; they get related, not identical, stems. "
      "*Planned* words (in italics) are not in the dictionary yet; they keep their place and join the family when added. "
      "*Also* lists words derived from a member by a meaning-changing relation (e.g. sister = brother +FEMALE): they share the member's stem.", "",
      "| Family | Size | Sibling group | Roots (first = head, the bare stem) | Also (derived) |", "|---|---|---|---|---|"]
for n, r in rm["families"].items():
    L.append(f"| {n} | {len(r)} | {sib.get(n, '')} | {', '.join('*' + x + '*' if x in pend else x for x in r)} | {'; '.join(also.get(n, []))} |")
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
