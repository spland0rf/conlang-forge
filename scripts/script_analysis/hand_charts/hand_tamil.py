"""Hand-transcribed Tamil letters (from the user's stroke charts #2/#3), as stroke data in the unit box (y up), then measured like the font."""
import json, math, os, sys
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, HERE); sys.path.insert(0, HERE + "/../..")
import compare, measure, topology

def arc(cx, cy, r, a0, a1, n=28, ry=None):
    ry = ry or r
    return [[cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))] for i in range(n + 1)]
def ring(cx, cy, r, ry=None):
    return {"p": arc(cx, cy, r, 0, 360, 36, ry), "closed": True, "k": "m"}
def S(*pts): return {"p": [list(p) for p in pts], "k": "m"}
def P(pts): return {"p": pts, "k": "m"}

L = {}
L["ட"] = [S((.15, 1), (.15, 0)), S((.15, 0), (.85, 0))]
L["ப"] = L["ட"] + [S((.85, 0), (.85, 1))]
L["ம"] = L["ப"] + [P(arc(.5, .75, .12, 180, 0, 12) )]                 # (approx.) a small arch inside the cup
L["ய"] = L["ப"] + [S((.15, .55), (0, .55))]                            # (approx.) a left tick
L["ஃ"] = [ring(.2, .15, .1), ring(.8, .15, .1), ring(.5, .85, .1)]
L["வ"] = [P(arc(.35, .6, .28, 90, 330, 28)), P(arc(.7, .36, .22, 180, 360, 14) + [[.92, .9]])]   # (approx.) a ring that swings into a right tail
L["ல"] = [ring(.25, .65, .2), P([[.45, .65]] + arc(.55, .45, .35, 80, -80, 20)[1:] + arc(.4, .1, .15, -80, -260, 14)[1:])]
L["ஸ"] = [ring(.2, .6, .17), P(arc(.55, .6, .35, 180, 360, 16, ry=.4) + arc(.55, .2, .15, 0, -140, 8)[1:])]
L["ஹ"] = [ring(.2, .62, .17), P([[.38, .75]] + arc(.55, .75, .17, 180, -80, 14)[1:] + [[.6, .35], [.8, .35]] + arc(.6, .15, .15, 90, 270, 10)[1:])]
L["ஶ்ரீ"] = [S((.05, 1), (.05, .35), (.45, .35)), S((.45, .35), (.45, .9)), P(arc(.7, .75, .22, 180, 0, 14)), S((.92, .75), (.92, .35)),
            ring(.2, .1, .1, ry=.07), P([[.28, .06]] + arc(.55, .15, .35, -90, 60, 18, ry=.4)[1:]), ring(.85, 1.05, .05)]

if __name__ == "__main__":
    meas = json.load(open(HERE + "/measurements.json"))
    ref = {k: meas["Tamil"]["summary"][k] for k in ("height_median", "stroke_w")}
    script = {"letters": [{"id": ch, "strokes": st} for ch, st in L.items()], "spec": {"roundness": 1.0}}
    json.dump(L, open(os.path.dirname(__file__) + "/hand_tamil.json", "w"))
    bm = compare.bitmaps(script, ref)
    measure.glyph_bitmaps = topology.glyph_bitmaps = lambda name, bm=bm: bm
    rows, dist = measure.measure("gen")
    for r in rows: print(r["ch"] if "ch" in r else "?", "angular", round(r["angular"], 2), "ends", r["ends"], "junc", r["junctions"])
    s = measure.summarise(rows)
    print("HAND   angular", s["angular"], "ends", s["ends_mean"], "junctions", s["junctions_mean"], "horiz/vert/diag", s["horiz"], s["vert"], s["diag"])
    t = meas["Tamil"]["summary"]
    print("FONT   angular", t["angular"], "ends", t["ends_mean"], "junctions", t["junctions_mean"], "horiz/vert/diag", t["horiz"], t["vert"], t["diag"])
