"""Do generated scripts look like the real ones, statistically?

For each "Create like..." preset: generate several scripts from the preset's settings (different seeds), draw their letters as
bitmaps the way render.py draws font glyphs, run the SAME measurements (measure.py, topology.py) on them, and compare the means
with the real script's numbers (measurements.json, topology.json). A metric is flagged when the generated mean is further from
the real value than a tolerance. Only ratios and shares are compared, so size does not matter.

    python compare.py run   [--seeds 6] [--presets latin,hebrew] [--out comparison.json]   (slow: a few minutes per preset)
    python compare.py report [--in comparison.json]                                         (markdown table of the mismatches)

Real glyphs are only measured, never copied."""
import argparse
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))

import measure          # noqa: E402
import topology         # noqa: E402
from conlang_forge.script.generate import generate      # noqa: E402
from conlang_forge.script.geometry import flatten       # noqa: E402
from conlang_forge.script.presets import PRESETS        # noqa: E402

CELL, SIZE = 170, 120
# which real script(s) each preset is compared with (the mean of their numbers)
REFERENCE = {"latin": ["Latin", "Greek", "Cyrillic"], "armenian": ["Armenian"], "georgian": ["Georgian"], "hebrew": ["Hebrew"],
             "arabic": ["Arabic"], "devanagari": ["Devanagari"], "bengali": ["Bengali"], "tamil": ["Tamil"], "thai": ["Thai"],
             "ethiopic": ["Ethiopic"], "hangul": ["Hangul"], "katakana": ["Katakana"], "hiragana": ["Hiragana"], "elvish": ["Tengwar"]}

# metric -> (where it lives, tolerance). Shares and ratios only.
METRICS = {
    "aspect_median": ("m", 0.15), "share_closed": ("m", 0.12), "ends_mean": ("m", 0.9), "junctions_mean": ("m", 0.7),
    "horiz": ("m", 0.10), "vert": ("m", 0.10), "diag": ("m", 0.10), "angular": ("m", 0.12), "parts_mean": ("m", 0.5),
    "share_with_marks": ("m", 0.12), "share_topbar": ("m", 0.15), "share_basebar": ("m", 0.15), "share_descending": ("m", 0.15),
    "symlr": ("m", 0.12),
    "strokes_mean": ("t", 1.0), "junction_deg3": ("t", 0.15), "loops_0": ("t", 0.12), "topology_class_share": ("t", 0.15),
    "share_letters_with_detached_mark": ("t", 0.12),
}


SS = 4          # drawn at 4x and shrunk, like an anti-aliased font glyph, so the outline is smooth (a jagged one grows skeleton spurs)


def _crisp(d, pts, sw):
    """A polyline drawn as one rectangle per segment (flat ends) with a wedge filling each corner."""
    h = sw / 2
    norms = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = max(1e-6, ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5)
        nx, ny = -(y1 - y0) / L * h, (x1 - x0) / L * h
        norms.append((nx, ny))
        d.polygon([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], fill=255)
    for (x, y), (a, b) in zip(pts[1:-1], zip(norms, norms[1:])):
        for sg in (1, -1):
            d.polygon([(x, y), (x + sg * a[0], y + sg * a[1]), (x + sg * b[0], y + sg * b[1])], fill=255)


def _draw(letter, unit, stroke_px, roundness):
    im = Image.new("L", (CELL * 2 * SS, CELL * 2 * SS), 0)
    d = ImageDraw.Draw(im)
    unit, sw = unit * SS, stroke_px * SS
    ox, base = CELL * 0.6 * SS, CELL * 1.2 * SS
    for s in letter["strokes"]:
        if s.get("stub"):                                  # joining stubs are not part of an isolated letter
            continue
        if s.get("dot"):
            x, y = s["p"][0]
            r = max(s.get("r", 0.09) * unit, sw * 0.6)
            d.ellipse([ox + x * unit - r, base - y * unit - r, ox + x * unit + r, base - y * unit + r], fill=255)
            continue
        pts = [(ox + x * unit, base - y * unit) for x, y in flatten(s, roundness)]
        if s.get("k", "m") in ("s", "b") or roundness < 0.2:      # crisp strokes: flat ends and sharp corners, like an angular font
            _crisp(d, pts, sw)
            continue
        if len(pts) > 1:
            d.line(pts, fill=255, width=max(2, int(round(sw))), joint="curve")
        for x, y in pts:                                         # round caps and joints
            d.ellipse([x - sw / 2, y - sw / 2, x + sw / 2, y + sw / 2], fill=255)
    im = im.resize((CELL * 2, CELL * 2), Image.LANCZOS)
    return np.array(im) > 127


def bitmaps(script, ref):
    """The generated letters drawn at the real script's letter height and stroke thickness."""
    from conlang_forge.script.geometry import bbox
    hs = sorted(bbox([s for s in l["strokes"] if not s.get("stub") and not s.get("dot")])[3] - bbox([s for s in l["strokes"] if not s.get("stub") and not s.get("dot")])[1]
                for l in script["letters"] if any(not s.get("stub") and not s.get("dot") for s in l["strokes"]))
    unit = ref["height_median"] * SIZE / max(1.0, hs[len(hs) // 2])        # letters taller than the x-height (stems that reach above or below) are scaled down to the real letter height
    out = []
    for letter in script["letters"]:
        bm = _draw(letter, unit, ref["stroke_w"] * SIZE, script["spec"]["roundness"])
        if bm.sum() >= 20:
            out.append((letter["id"], bm))
    return out, CELL * 1.2


def one(args):
    """Generate and measure one script: returns {metric: value}."""
    preset_id, seed, ref = args
    pins = next(p for p in PRESETS if p["id"] == preset_id)["pins"]
    script = generate(seed, pins)
    bm = bitmaps(script, ref)
    measure.glyph_bitmaps = topology.glyph_bitmaps = lambda name, bm=bm: bm
    rows, dist = measure.measure("gen")
    m = measure.summarise(rows)
    t = topology.run("gen")
    t["topology_class_share"] = t["topology_classes"] / max(1, t["letters"])
    out = {k: m[k] for k, (w, _) in METRICS.items() if w == "m"}
    out.update({k: t[k] for k, (w, _) in METRICS.items() if w == "t"})
    out["nn_mean"] = dist["nn_mean"]
    return out


def real(names, meas, topo):
    """The real script's numbers (the mean over the named scripts) for every metric."""
    vals = {}
    for k, (w, _) in METRICS.items():
        if k == "topology_class_share":
            xs = [topo[n]["topology_classes"] / topo[n]["letters"] for n in names]
        elif w == "m":
            xs = [meas[n]["summary"][k] for n in names]
        else:
            xs = [topo[n][k] for n in names]
        vals[k] = float(np.mean(xs))
    vals["nn_mean"] = float(np.mean([meas[n]["distinct"]["nn_mean"] for n in names]))
    return vals


def run(preset_ids, seeds, out_path, procs):
    meas = json.load(open(os.path.join(HERE, "measurements.json")))
    topo = json.load(open(os.path.join(HERE, "topology.json")))
    result = json.load(open(out_path)) if os.path.exists(out_path) else {}
    for pid in preset_ids:
        names = REFERENCE[pid]
        ref = {k: float(np.mean([meas[n]["summary"][k] for n in names])) for k in ("height_median", "stroke_w")}
        with Pool(procs) as pool:
            rows = pool.map(one, [(pid, s, ref) for s in range(1, seeds + 1)])
        gen = {k: [r[k] for r in rows] for k in rows[0]}
        result[pid] = {"reference": names, "real": real(names, meas, topo),
                       "gen_mean": {k: float(np.mean(v)) for k, v in gen.items()}, "gen_sd": {k: float(np.std(v)) for k, v in gen.items()},
                       "seeds": seeds}
        json.dump(result, open(out_path, "w"), indent=1)
        print("done", pid, file=sys.stderr, flush=True)


def mismatches(entry):
    out = []
    for k, (_, tol) in METRICS.items():
        r, g = entry["real"][k], entry["gen_mean"][k]
        if abs(g - r) > tol:
            out.append((k, r, g, entry["gen_sd"][k]))
    return out


def report(path):
    data = json.load(open(path))
    lines = ["| Preset | Compared with | Metrics off | Largest gaps (real -> generated) |", "|---|---|---|---|"]
    for pid, e in data.items():
        mm = mismatches(e)
        mm.sort(key=lambda x: -abs(x[2] - x[1]) / METRICS[x[0]][1])
        top = "; ".join(f"{k} {r:.2f} -> {g:.2f}" for k, r, g, _ in mm[:5]) or "none"
        lines.append(f"| {pid} | {', '.join(e['reference'])} | {len(mm)} of {len(METRICS)} | {top} |")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "report"])
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--presets", default="all")
    ap.add_argument("--out", default=os.path.join(HERE, "comparison.json"))
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    if a.cmd == "run":
        ids = list(REFERENCE) if a.presets == "all" else a.presets.split(",")
        run(ids, a.seeds, a.out, a.procs)
    else:
        report(a.out)
