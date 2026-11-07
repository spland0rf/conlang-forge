"""Per-script configuration for the stroke generators. `get()` returns the config of the script named by $CONLANG_SCRIPT (default: devanagari).
Add a script by dropping <name>.json beside devanagari.json (same keys). The stroke vocabulary itself (roles, junction kinds) is shared by all scripts."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
_cache = {}
def name(): return os.environ.get("CONLANG_SCRIPT", "devanagari")
def get(script=None):
    s = script or name()
    if s not in _cache: _cache[s] = json.load(open(os.path.join(HERE, s + ".json")))
    return _cache[s]
def path(key, script=None):
    """repo-absolute path of cfg['paths'][key]"""
    return os.path.join(ROOT, get(script)["paths"][key])

REQUIRED = {"id": str, "frame": dict, "rules": dict, "recipes": dict, "skeleton": dict, "half": dict, "paths": dict, "history": dict, "engine": dict}
FRAME_KEYS = {"box", "bar_y", "base_y", "desc_y", "half_top"}
def validate(script=None):
    """Raise ValueError if a script's config lacks a section, a frame value, or a rule that the Devanagari reference config defines."""
    cfg, ref = get(script), get("devanagari"); bad = []
    for k, t in REQUIRED.items():
        if not isinstance(cfg.get(k), t): bad.append("section %s missing" % k)
    bad += ["frame.%s missing" % k for k in FRAME_KEYS - set(cfg.get("frame", {}))]
    bad += ["rule %s missing" % k for k in set(ref["rules"]) - set(cfg.get("rules", {}))]
    bad += ["skeleton.%s missing" % k for k in set(ref["skeleton"]) - set(cfg.get("skeleton", {}))]
    bad += ["half.%s missing" % k for k in set(ref["half"]) - set(cfg.get("half", {}))]
    bad += ["paths.%s missing" % k for k in set(ref["paths"]) - set(cfg.get("paths", {}))]
    if bad: raise ValueError("%s config: %s" % (cfg.get("id", script), "; ".join(sorted(bad))))
    return cfg
