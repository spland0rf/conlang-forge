"""Run tune.py as many small, resumable pieces: python tune_chain.py OUTDIR  (re-run after a kill; finished pieces are skipped)."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]
START = {}
PIECES = {
    "bengali": ["stroke_ticks,stroke_crossings", "topline_share,loops", "complexity,roundness,width"],
    "devanagari": ["stroke_ticks,stroke_crossings", "topline_share,loops", "complexity,roundness,width"],
    "tamil": ["stroke_ticks,stroke_crossings", "corner_style,roundness", "loops,width"],
    "thai": ["stroke_ticks,stroke_crossings", "corner_style,roundness", "loops,width"],
    "hangul": ["stroke_ticks,stroke_crossings", "loops,roundness", "width"],
}
for pid, pieces in PIECES.items():
    pins = dict(START.get(pid, {}))
    for i, dials in enumerate(pieces):
        f = os.path.join(out, f"piece_{pid}_{i}.json")
        if not os.path.exists(f):
            subprocess.run([sys.executable, os.path.join(HERE, "tune.py"), pid, "--seeds", "3", "--rounds", "1", "--dials", dials,
                            "--start", json.dumps(pins), "--out", f], stdout=open(f + ".log", "w"), stderr=subprocess.STDOUT, check=False)
        if os.path.exists(f):
            pins = json.load(open(f))["pins"]
            print(pid, i, json.load(open(f))["cost"], flush=True)
open(os.path.join(out, "chain.done"), "w").write("ok")
