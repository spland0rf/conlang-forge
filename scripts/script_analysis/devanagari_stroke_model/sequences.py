"""Draft stroke-order records for the real Devanagari letters: each letter's drawing order as steps (lists of model stroke ids), read
from the user's black-and-red sequence sheets. Default is the model's stroke order, one stroke per step; OVERRIDES hold what the
sheets show differently. `units` marks visual-grammar breaks inside one pen stroke (fraction along it). A long curve that loops and
crosses itself is ONE pen stroke; a 3 is one path with a cusp (two cups).  usage: python3 sequences.py > sequences.json"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE, "model/letters.json")))
# letters whose order was checked against the sheet rows (the rest follow the model order and are listed as draft)
CHECKED = {"a", "ka", "ga", "pa", "pha", "ma", "ba", "va", "ta", "na", "ṭa", "ṭha", "ḍa", "da", "ṇa", "ṅa", "ja", "ca", "e", "ai", "i", "ī", "ra", "la", "ya"}
OVERRIDES = {
    "ā": [["s1", "s2"], ["s3"], ["s4"], ["s5"], ["s6", "s7"]],
    "o": [["s1", "s2"], ["s3"], ["s4"], ["s5"], ["s6", "s7"], ["s8"]],
    "au": [["s1", "s2"], ["s3"], ["s4"], ["s5"], ["s6", "s7"], ["s8"], ["s9"]],
    "a": [["s1", "s2"], ["s3"], ["s4"], ["s5"]],
    "pa": [["s1"], ["s3"], ["s2"]],
    "pha": [["s1"], ["s3"], ["s2"], ["s4"]],
    "dha": [["s3", "s4"], ["s1"], ["s2"]],
}
UNITS = {"i": {"s3": [0.55]}, "ī": {"s3": [0.55]}}        # the S, then its crossing tail: one pen stroke
out = []
for l in L:
    key = l["iast"] + ((" " + l["variant"]) if l["variant"] else "")
    ids = [s["id"] for s in l["strokes"]]
    steps = OVERRIDES.get(l["iast"]) if not l["variant"] else None
    if steps is None:
        steps = [[i] for i in ids]
    flat = [i for st in steps for i in st]
    assert sorted(flat) == sorted(ids), (key, flat, ids)
    out.append({"glyph": l["glyph"], "name": key, "steps": steps, "units": UNITS.get(l["iast"], {}) if not l["variant"] else {},
                "status": "read" if (l["iast"] in CHECKED and not l["variant"]) or l["iast"] in OVERRIDES and l["iast"] != "dha" else "draft"})
json.dump(out, open(os.path.join(HERE, "sequences.json"), "w"), ensure_ascii=False, indent=1)
print(sum(o["status"] == "read" for o in out), "read,", sum(o["status"] == "draft" for o in out), "draft")
