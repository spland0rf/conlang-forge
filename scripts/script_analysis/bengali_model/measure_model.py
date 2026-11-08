"""Measure the Bengali stroke model from the 44 hand-fitted letters ONLY (conlang_forge/script/forms/bengali_graph.json).
Nothing here reads another script's data or the shared generator config.  Writes bengali_model.json (records + summaries) and prints a summary.
Frame: 100 x 100, y down, headings in degrees with y UP (0 = east, 90 = north), so a stroke heading straight down is -90.
usage: python3 measure_model.py"""
import json, math, os, re, statistics as st
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
GRAPH = os.path.join(HERE, "..", "..", "..", "conlang_forge", "script", "forms", "bengali_graph.json")

def pts(d): v = [float(x) for x in re.findall(r"-?\d+\.?\d*", d)]; return list(zip(v[0::2], v[1::2]))
def head(a, b): return math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))
def dh(a, b): return (b - a + 180) % 360 - 180
def length(P): return sum(math.dist(p, q) for p, q in zip(P, P[1:]))
def resample(P, step=1.0):
    out = [P[0]]
    for a, b in zip(P, P[1:]):
        n = max(1, int(math.dist(a, b) // step))
        for i in range(1, n + 1): out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out
def turns(P):
    """signed total turn (+ = anticlockwise on the page as drawn y-up) and the largest single corner, from the polyline vertices"""
    Q = [p for i, p in enumerate(P) if i == 0 or math.dist(p, P[i - 1]) > 0.4]
    hs = [head(a, b) for a, b in zip(Q, Q[1:])]; ds = [dh(a, b) for a, b in zip(hs, hs[1:])]
    return sum(ds), (max(ds, key=abs) if ds else 0.0), sum(abs(d) for d in ds)
def q(xs, p):
    xs = sorted(xs); return round(xs[min(len(xs) - 1, int(p * len(xs)))], 1) if xs else None
def summ(xs): return {"n": len(xs), "min": q(xs, 0), "p10": q(xs, .1), "p25": q(xs, .25), "med": q(xs, .5), "p75": q(xs, .75), "p90": q(xs, .9), "max": q(xs, 1)} if xs else {"n": 0}
def tangent_at(P, f, out_dir, span=6.0):
    """heading of the stroke at fraction f of its length, in the direction `out_dir` (+1 along the stroke, -1 against it)"""
    R = resample(P); n = len(R) - 1; i = min(n, max(0, round(f * n))); k = max(2, int(span))
    a, b = (R[i], R[min(n, i + k)]) if out_dir > 0 else (R[i], R[max(0, i - k)])
    return head(a, b) if math.dist(a, b) > 0.2 else None
def is_vertical(P): return len(P) == 2 and abs(P[0][0] - P[1][0]) < 1.0

def model():
    G = json.load(open(GRAPH)); letters = []; strokes = []; junctions = []
    for l in G["letters"]:
        S = {s[2]: (s[0], pts(s[1])) for s in l["strokes"]}
        bar = next(((sid, P) for sid, (r, P) in S.items() if r == "struct" and len(P) == 2 and abs(P[0][1] - P[1][1]) < 0.6 and abs(P[0][0] - P[1][0]) > 30), None)
        bar_x = sorted((bar[1][0][0], bar[1][1][0])) if bar else None
        info = {"iast": l["iast"], "has_bar": bool(bar), "bar_x0": bar_x and round(bar_x[0], 1), "bar_x1": bar_x and round(bar_x[1], 1), "bar_y": bar and round(bar[1][0][1], 1)}
        info["n_body"] = sum(r == "body" for r, _ in S.values()); info["n_second"] = sum(r == "second" for r, _ in S.values())
        info["n_accent"] = sum(r == "accent" for r, _ in S.values()); info["n_struct_other"] = sum(r == "struct" for sid, (r, _) in S.items()) - bool(bar)
        verts = [(sid, P) for sid, (r, P) in S.items() if r != "struct" and is_vertical(P) or r == "struct" and not (bar and sid == bar[0]) and is_vertical(P)]
        info["verticals"] = [{"id": sid, "x": round(P[0][0], 1), "y0": round(min(P[0][1], P[1][1]), 1), "y1": round(max(P[0][1], P[1][1]), 1),
                              "x_frac_of_bar": round((P[0][0] - bar_x[0]) / (bar_x[1] - bar_x[0]), 2) if bar else None} for sid, P in verts]
        longest = max((length(P) for r, P in S.values() if r != "struct" or not (bar and False)), default=0)
        info["ink_len"] = round(sum(length(P) for r, P in S.values()), 1)
        xs = [p[0] for _, P in S.values() for p in P]; ys = [p[1] for _, P in S.values() for p in P]
        info["bbox"] = [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)]
        # skeleton class: what carries the letter
        tall = [v for v in info["verticals"] if v["y1"] - v["y0"] >= 40]
        info["skeleton"] = ("bar+stem" if bar and tall else "bar+short" if bar and info["verticals"] else "bar+bodies" if bar else "stem-only" if tall else "free")
        letters.append(info)
        for sid, (r, P) in S.items():
            if r in ("struct",) and bar and sid == bar[0]: continue
            tt, mx, ab = turns(P)
            ends = l.get("ends", {}).get(sid, ["plain", "plain"])
            strokes.append({"iast": l["iast"], "id": sid, "role": r, "len": round(length(P), 1), "turn": round(tt, 1), "abs_turn": round(ab, 1), "max_corner": round(mx, 1), "n_pts": len(P),
                            "vertical": is_vertical(P), "h_start": round(head(P[0], P[1]), 1), "h_end": round(head(P[-2], P[-1]), 1), "chord": round(head(P[0], P[-1]), 1),
                            "x0": round(P[0][0], 1), "y0": round(P[0][1], 1), "x1": round(P[-1][0], 1), "y1": round(P[-1][1], 1),
                            "end_start": ends[0], "end_end": ends[1], "ball": ends[0] == "ball" or ends[1] == "ball"})
        for j in l["junctions"]:
            mem = j["members"]
            if len(mem) < 2: junctions.append({"iast": l["iast"], "t": j["t"], "kind": "self" if len(mem) == 1 else "loose", "x": j["x"], "y": j["y"]}); continue
            dirs = []
            for m in mem:
                r, P = S[m["stroke"]]
                if m["where"] == "start": d = tangent_at(P, 0.0, +1)
                elif m["where"] == "end": d = tangent_at(P, 1.0, -1)
                else: d = tangent_at(P, m["at"], +1)
                dirs.append((m, r, d, P))
            for a in range(len(dirs)):
                for b in range(a + 1, len(dirs)):
                    (ma, ra, da, Pa), (mb, rb, db, Pb) = dirs[a], dirs[b]
                    if da is None or db is None: continue
                    ang = abs(dh(da, db))
                    if ma["where"] == "middle": ang = min(ang, 180 - ang) if mb["where"] != "middle" else min(ang, 180 - ang)
                    if mb["where"] == "middle" and ma["where"] != "middle": ang = min(ang, 180 - ang)
                    junctions.append({"iast": l["iast"], "t": j["t"], "a": ma["stroke"], "b": mb["stroke"], "role_a": ra, "role_b": rb,
                                      "where_a": ma["where"], "where_b": mb["where"], "at_a": ma["at"], "at_b": mb["at"], "angle": round(ang, 1),
                                      "bar": ra == "struct" and not is_vertical(Pa) or rb == "struct" and not is_vertical(Pb), "x": j["x"], "y": j["y"]})
    return letters, strokes, junctions

def main():
    letters, strokes, junctions = model()
    body = [s for s in strokes if s["role"] in ("body", "second")]
    M = {"source": "conlang_forge/script/forms/bengali_graph.json (44 hand-fitted letters)", "letters": letters, "strokes": strokes, "junctions": junctions}
    M["summary"] = {
        "skeleton_classes": dict(Counter(l["skeleton"] for l in letters)),
        "has_bar": sum(l["has_bar"] for l in letters),
        "bar": {"y": summ([l["bar_y"] for l in letters if l["has_bar"]]), "x0": summ([l["bar_x0"] for l in letters if l["has_bar"]]), "x1": summ([l["bar_x1"] for l in letters if l["has_bar"]]),
                "width": summ([l["bar_x1"] - l["bar_x0"] for l in letters if l["has_bar"]])},
        "vertical_x_frac_of_bar": summ([v["x_frac_of_bar"] for l in letters for v in l["verticals"] if v["x_frac_of_bar"] is not None]),
        "vertical_length": summ([v["y1"] - v["y0"] for l in letters for v in l["verticals"]]),
        "vertical_top_y": summ([v["y0"] for l in letters for v in l["verticals"]]), "vertical_bottom_y": summ([v["y1"] for l in letters for v in l["verticals"]]),
        "verticals_per_letter": dict(Counter(len(l["verticals"]) for l in letters)),
        "strokes_per_letter": dict(Counter(l["n_body"] + l["n_second"] for l in letters)),
        "accents_per_letter": dict(Counter(l["n_accent"] for l in letters)),
        "body_len": summ([s["len"] for s in body if not s["vertical"]]), "body_abs_turn": summ([s["abs_turn"] for s in body if not s["vertical"]]),
        "body_signed_turn": summ([s["turn"] for s in body if not s["vertical"]]),
        "body_max_corner": summ([abs(s["max_corner"]) for s in body if not s["vertical"]]),
        "straight_nonvertical": sum(1 for s in body if not s["vertical"] and s["abs_turn"] < 12),
        "start_heading": dict(Counter(("down" if -135 < s["h_start"] <= -45 else "up" if 45 <= s["h_start"] < 135 else "right" if abs(s["h_start"]) < 45 else "left") for s in body)),
        "ball_ends": sum(s["ball"] for s in strokes),
        "junction_types": dict(Counter(j["t"] for j in junctions)),
        "junction_angle_touch": summ([j["angle"] for j in junctions if j["t"] == "touch" and "angle" in j]),
        "junction_angle_red_nonbar": summ([j["angle"] for j in junctions if j["t"] == "red" and "angle" in j and not j["bar"]]),
        "junction_angle_red_bar": summ([j["angle"] for j in junctions if j["t"] == "red" and "angle" in j and j["bar"]]),
        "touch_where": dict(Counter("%s-%s" % tuple(sorted((j["where_a"], j["where_b"]))) for j in junctions if j["t"] == "touch" and "where_a" in j)),
        "red_where": dict(Counter("%s-%s" % tuple(sorted((j["where_a"], j["where_b"]))) for j in junctions if j["t"] == "red" and "where_a" in j)),
    }
    json.dump(M, open(os.path.join(HERE, "bengali_model.json"), "w"), ensure_ascii=False, indent=1)
    for k, v in M["summary"].items(): print(k, v)

if __name__ == "__main__": main()
