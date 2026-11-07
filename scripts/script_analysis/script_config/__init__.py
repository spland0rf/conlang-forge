"""Per-script configuration for the stroke generators, and the PROFILE that says which script supplies which ingredient.

A script's data lives in <script>.json beside this file (same keys as devanagari.json).  A Profile maps each INGREDIENT of a letter to a script:
    frame     the box (bar / baseline / descender heights) the script's drawings use, and its mapping into the common frame
    rules     validity + size thresholds, review history, reference (real) letters, spec, engine file names
    skeleton  the skeleton types, recipe mix, anchor ranges and half-bar geometry
    body      the body-form vocabulary (units, keepers, connection patterns)
    modifier  supplementary / accent strokes (no consumer yet: reserved so that a profile can already name its source)
Today every ingredient comes from one script (`Profile.of("devanagari")`).  Mixing is just a profile whose sources differ; nothing else changes.

The generators read the ACTIVE profile at call time, never at import:  `with SC.use(profile): ...` switches it; with no `use`, the profile of
$CONLANG_SCRIPT (default devanagari) is active.  The stroke vocabulary (roles body/second/struct/accent, junctions red/touch/cross) is shared."""
import json, os
from collections.abc import Mapping
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
INGREDIENTS = ("frame", "rules", "skeleton", "body", "modifier")
COMMON = {"box": 100.0, "bar_y": 20.0, "base_y": 88.0}      # the common frame every script's drawings map into (Devanagari's own frame)
_cache = {}


def name(): return os.environ.get("CONLANG_SCRIPT", "devanagari")


def get(script=None):
    """The raw config dict of a script (default: the active profile's rules script)."""
    s = script or active().sources["rules"]
    if s not in _cache: _cache[s] = json.load(open(os.path.join(HERE, s + ".json")))
    return _cache[s]


# which ingredient's script owns each config section / path key
SECTION_INGREDIENT = {"frame": "frame", "rules": "rules", "rule_notes": "rules", "history": "rules", "engine": "rules",
                      "recipes": "skeleton", "skeleton": "skeleton", "half": "skeleton"}
KEY_INGREDIENT = {"units": "body", "keepers": "body", "patterns": "body", "unit_source": "body"}      # every other path key belongs to "rules" (reference data)


class Profile:
    def __init__(self, sources=None, label=None):
        sources = dict(sources or {}); base = name()
        self.sources = {i: sources.get(i, base) for i in INGREDIENTS}
        self.label = label or ("+".join(sorted(set(self.sources.values()))) if len(set(self.sources.values())) > 1 else self.sources["rules"])

    @classmethod
    def of(cls, script): return cls({i: script for i in INGREDIENTS}, script)

    def scripts(self): return sorted(set(self.sources.values()))        # every script whose real letters a new letter must differ from
    def section(self, key): return get(self.sources[SECTION_INGREDIENT[key]])[key]
    @property
    def frame(self): return self.section("frame")
    @property
    def rules(self): return self.section("rules")
    @property
    def history(self): return self.section("history")
    @property
    def recipes(self): return self.section("recipes")
    @property
    def skeleton(self): return self.section("skeleton")
    @property
    def half(self): return self.section("half")
    @property
    def engine(self): return self.section("engine")

    def path(self, key, script=None):
        """repo-absolute path of a config path key, from the script that owns it (or `script`)"""
        s = script or self.sources[KEY_INGREDIENT.get(key, "rules")]
        return os.path.join(ROOT, get(s)["paths"][key])

    # ---- common frame: a point drawn in script S's box <-> the common box -------------------------------------------------------------------
    def _map(self, script):
        f = get(script)["frame"]; sy = (COMMON["base_y"] - COMMON["bar_y"]) / (f["base_y"] - f["bar_y"])
        return f.get("x_scale", 1.0), f.get("x_offset", 0.0), sy, COMMON["bar_y"] - sy * f["bar_y"]
    def to_common(self, pts, script=None):
        sx, dx, sy, dy = self._map(script or self.sources["frame"]); return [(sx * x + dx, sy * y + dy) for x, y in pts]
    def from_common(self, pts, script=None):
        sx, dx, sy, dy = self._map(script or self.sources["frame"]); return [((x - dx) / sx, (y - dy) / sy) for x, y in pts]


_state = {"profile": None, "rules": None}
def active():
    if _state["profile"] is None: _activate(Profile.of(name()))
    return _state["profile"]
def _activate(p): _state["profile"] = p; _state["rules"] = p.rules
@contextmanager
def use(profile):
    """Make `profile` (a Profile, or a script name) the active one inside the block."""
    p = Profile.of(profile) if isinstance(profile, str) else profile; old = _state["profile"]; _activate(p)
    try: yield p
    finally:
        if old is None: _state["profile"] = _state["rules"] = None
        else: _activate(old)


class RulesView(Mapping):
    """Read-only view of the active profile's rules.  One dict lookup per access (the validators call it in their inner loops)."""
    def __getitem__(self, k):
        r = _state["rules"]
        if r is None: active(); r = _state["rules"]
        return r[k]
    def __iter__(self): active(); return iter(_state["rules"])
    def __len__(self): active(); return len(_state["rules"])


def path(key, script=None): return active().path(key, script)


REQUIRED = {"id": str, "frame": dict, "rules": dict, "recipes": dict, "skeleton": dict, "half": dict, "paths": dict, "history": dict, "engine": dict}
FRAME_KEYS = {"box", "bar_y", "base_y", "desc_y", "half_top"}
def validate(script=None):
    """Raise ValueError if a script's config lacks a section, a frame value, or a rule that the Devanagari reference config defines."""
    cfg, ref = get(script or name()), get("devanagari"); bad = []
    for k, t in REQUIRED.items():
        if not isinstance(cfg.get(k), t): bad.append("section %s missing" % k)
    bad += ["frame.%s missing" % k for k in FRAME_KEYS - set(cfg.get("frame", {}))]
    bad += ["rule %s missing" % k for k in set(ref["rules"]) - set(cfg.get("rules", {}))]
    bad += ["skeleton.%s missing" % k for k in set(ref["skeleton"]) - set(cfg.get("skeleton", {}))]
    bad += ["half.%s missing" % k for k in set(ref["half"]) - set(cfg.get("half", {}))]
    bad += ["paths.%s missing" % k for k in set(ref["paths"]) - set(cfg.get("paths", {}))]
    fr = cfg.get("frame", {})
    if not bad and not (fr["bar_y"] < fr["desc_y"] < fr["base_y"]): bad.append("frame heights out of order")
    if bad: raise ValueError("%s config: %s" % (cfg.get("id", script), "; ".join(sorted(bad))))
    return cfg
