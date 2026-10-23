"""Coordinate-descent tuning of a preset's dials against the real script it imitates (compare.py's measurements).

    python tune.py bengali --seeds 3 --rounds 2 --dials topline_share,loops,complexity [--out tune_bengali.json]

Cost = mean over the 19 metrics of min(3, |generated - real| / tolerance)^2 (a metric inside its tolerance costs <= 1, a wild one is
capped at 9). Each round tries, for every dial, a few values around the current one and keeps the best."""
import argparse
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import compare   # noqa: E402
from conlang_forge.script.presets import PRESETS   # noqa: E402
from conlang_forge.script.spec import DIALS        # noqa: E402

MEAS = json.load(open(os.path.join(HERE, "measurements.json")))
TOPO = json.load(open(os.path.join(HERE, "topology.json")))


def cost(entry_real, gen):
    xs = [min(3.0, abs(gen[k] - entry_real[k]) / tol) ** 2 for k, (_, tol) in compare.METRICS.items()]
    return float(np.mean(xs)), xs


def evaluate(pid, pins, seeds, procs):
    names = compare.REFERENCE[pid]
    ref = {k: float(np.mean([MEAS[n]["summary"][k] for n in names])) for k in ("height_median", "stroke_w")}
    os.environ["PINS"] = json.dumps(pins)
    with Pool(procs) as pool:
        rows = pool.map(compare.one, [(pid, s, ref) for s in range(1, seeds + 1)])
    gen = {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}
    real = compare.real(names, MEAS, TOPO)
    c, xs = cost(real, gen)
    return c, gen, real


def candidates(dial, cur):
    spec = DIALS[dial][0]
    if isinstance(spec[0], str):                                   # an enumeration: try every other value
        return [v for v in spec if v != cur]
    lo, hi = spec
    step = (hi - lo) / 4
    out = [round(min(hi, max(lo, cur + d * step)), 3) for d in (-1, -.5, .5, 1)]
    return sorted({v for v in out if abs(v - cur) > 1e-6})


def tune(pid, dials, seeds, rounds, procs, log):
    base = dict(next(p for p in PRESETS if p["id"] == pid)["pins"])
    best_c, gen, real = evaluate(pid, {}, seeds, procs)
    history = [("start", None, best_c)]
    log(f"{pid} start cost {best_c:.3f}")
    cur = dict(base)
    for r in range(rounds):
        improved = False
        for d in dials:
            now = cur.get(d, None)
            if now is None:
                spec = DIALS[d][0]
                now = spec[0] if isinstance(spec[0], str) else round((spec[0] + spec[1]) / 2, 3)
            for v in candidates(d, now):
                trial = {k: cur[k] for k in cur}
                trial[d] = v
                c, g, _ = evaluate(pid, {d: v, **{k: cur[k] for k in cur if k != d}}, seeds, procs)
                if c < best_c - 1e-3:
                    best_c, cur, gen, improved = c, trial, g, True
                    history.append((d, v, c))
                    log(f"  round {r + 1}: {d}={v} -> cost {c:.3f}")
        if not improved:
            break
    return dict(pid=pid, pins=cur, cost=best_c, history=history, gen=gen, real=real)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("preset")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--dials", default="topline_share,loops,complexity,width,roundness,density")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = tune(a.preset, a.dials.split(","), a.seeds, a.rounds, a.procs, lambda s: print(s, flush=True))
    out = a.out or os.path.join(HERE, f"tune_{a.preset}.json")
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in res["pins"].items()}, indent=1))
