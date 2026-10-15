"""Characteristic shapes: a few medium-complexity figures (a ring, two stacked rings, a triangle, a crossed X, a
trident...) that a script reuses across related letters. A letter built from a shape is the shape plus one variant
(a stem, a bar, an open gap, a rotation, a dot...), so related sounds look related, as in featural writing systems."""
from __future__ import annotations

import math

from .geometry import dot, stroke
from .graph import analyse, points
from .motifs import RIGHT, classify

_RING = [(.5, 0), (.87, .13), (1, .5), (.87, .87), (.5, 1), (.13, .87), (0, .5), (.13, .13)]


def _ring(cx, cy, r):
    return stroke([(cx + r * (x - .5) / .5, cy + r * (y - .5) / .5) for x, y in _RING], True)


# round and angular figures (drawn smooth, sharp or mixed depending on the script's corner style)
MOTIFS = {
    "ring": lambda: [_ring(.5, .5, .5)],
    "ring2": lambda: [_ring(.5, .75, .25), _ring(.5, .25, .25)],
    "tri": lambda: [stroke([(.5, 1), (1, 0), (0, 0)], True)],
    "tri_down": lambda: [stroke([(0, 1), (1, 1), (.5, 0)], True)],
    "X": lambda: [stroke([(0, 0), (1, 1)]), stroke([(0, 1), (1, 0)])],
    "diamond": lambda: [stroke([(.5, 0), (1, .5), (.5, 1), (0, .5)], True)],
    "ringcross": lambda: [_ring(.5, .5, .5), stroke([(.5, 0), (.5, 1)])],
    "trident": lambda: [stroke([(0, 1), (0, .4), (.5, 0), (1, .4), (1, 1)]), stroke([(.5, 0), (.5, 1)])],
    "target": lambda: [_ring(.5, .5, .5), _ring(.5, .5, .2), stroke([(.5, .7), (.5, 1)])],
    "tri2": lambda: [stroke([(.5, 1), (1, .5), (0, .5)], True), stroke([(.5, .5), (1, 0), (0, 0)], True)],
}
# right-angle figures for blocky scripts
ORTHO_MOTIFS = {
    "box": lambda: [stroke([(0, 0), (1, 0), (1, 1), (0, 1)], True)],
    "box2": lambda: [stroke([(0, 0), (1, 0), (1, .5), (0, .5)], True), stroke([(0, .5), (1, .5), (1, 1), (0, 1)], True)],
    "plus": lambda: [stroke([(.5, 0), (.5, 1)]), stroke([(0, .5), (1, .5)])],
    "boxplus": lambda: [stroke([(0, 0), (1, 0), (1, 1), (0, 1)], True), stroke([(.5, 0), (.5, 1)])],
    "ladder": lambda: [stroke([(0, 0), (0, 1)]), stroke([(1, 0), (1, 1)]), stroke([(0, .33), (1, .33)]), stroke([(0, .66), (1, .66)])],
    "nest": lambda: [stroke([(0, 0), (1, 0), (1, 1), (0, 1)], True), stroke([(.3, .3), (.7, .3), (.7, .7), (.3, .7)], True),
                     stroke([(.5, .7), (.5, 1)])],
    "E3": lambda: [stroke([(0, 0), (0, 1)]), stroke([(0, 1), (1, 1)]), stroke([(0, .5), (.8, .5)]), stroke([(0, 0), (1, 0)])],
}

# ---- Grammar v3: more figures, from pictorial (ornate) to structural (bold) -------------------------------------------
def _arc(cx, cy, rx, ry, a0, a1, n=7):
    return [(round(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), 3),
             round(cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n)), 3)) for i in range(n + 1)]


MOTIFS.update({
    # pictorial / ornate: small details, several strokes (the Proto-Sinaitic end of the chart)
    "eye": lambda: [stroke([(0, .5), (.3, .85), (.7, .85), (1, .5), (.7, .15), (.3, .15)], True), _ring(.5, .5, .16), stroke([(.5, .66), (.5, .85)])],
    "ankh": lambda: [_ring(.5, .75, .25), stroke([(.5, .5), (.5, 0)]), stroke([(.2, .3), (.8, .3)])],
    "fish": lambda: [stroke([(0, .5), (.35, .85), (.75, .5), (.35, .15)], True), stroke([(.75, .5), (1, .85)]), stroke([(.75, .5), (1, .15)])],
    "person": lambda: [_ring(.5, .85, .15), stroke([(.5, .7), (.5, .35)]), stroke([(.1, .6), (.9, .6)]),
                       stroke([(.5, .35), (.15, 0)]), stroke([(.5, .35), (.85, 0)])],
    "harp": lambda: [stroke([(0, .1), (1, .1)])] + [stroke([(x, .1), (x, 1)]) for x in (.15, .5, .85)],
    "comb": lambda: [stroke([(0, 0), (0, 1)])] + [stroke([(0, y), (1, y)]) for y in (.1, .5, .9)],
    "curl": lambda: [stroke(_arc(.5, .6, .38, .38, 90, 450, 12)), stroke([(.5, .22), (.5, 0)])],
    "house": lambda: [stroke([(0, 0), (1, 0), (1, .7), (0, .7)], True), stroke([(.5, 0), (.5, .7)]), stroke([(.5, .7), (.5, 1)])],
    # structural parts: the letters of the Greek and Latin end (stem+bowl, stem+branches, loop+tail, crossings, zigzags...)
    "P": lambda: [stroke([(0, 0), (0, 1), (.65, 1), (1, .8), (1, .65), (.65, .45), (0, .45)])],
    "B": lambda: [stroke([(0, 0), (0, 1)]), stroke([(0, 1), (.7, 1), (1, .75), (.7, .5), (0, .5)]),
                  stroke([(0, .5), (.7, .5), (1, .25), (.7, 0), (0, 0)])],
    "F": lambda: [stroke([(0, 0), (0, 1)]), stroke([(0, 1), (1, 1)]), stroke([(0, .5), (.7, .5)])],
    "E": lambda: [stroke([(0, 0), (0, 1)]), stroke([(0, 1), (1, 1)]), stroke([(0, .5), (.7, .5)]), stroke([(0, 0), (1, 0)])],
    "Y": lambda: [stroke([(0, 1), (.5, .5), (1, 1)]), stroke([(.5, .5), (.5, 0)])],
    "T": lambda: [stroke([(0, 1), (1, 1)]), stroke([(.5, 1), (.5, 0)])],
    "L": lambda: [stroke([(0, 1), (0, 0), (1, 0)])],
    "H": lambda: [stroke([(0, 0), (0, 1)]), stroke([(1, 0), (1, 1)]), stroke([(0, .5), (1, .5)])],
    "Z": lambda: [stroke([(0, 1), (1, 1), (0, 0), (1, 0)])],
    "N": lambda: [stroke([(0, 0), (0, 1), (1, 0), (1, 1)])],
    "M": lambda: [stroke([(0, 0), (0, 1), (.5, .4), (1, 1), (1, 0)])],
    "W": lambda: [stroke([(0, 1), (.25, 0), (.5, .7), (.75, 0), (1, 1)])],
    "V": lambda: [stroke([(0, 1), (.5, 0), (1, 1)])],
    "K": lambda: [stroke([(0, 0), (0, 1)]), stroke([(1, 1), (0, .5), (1, 0)])],
    "Q": lambda: [_ring(.5, .55, .45), stroke([(.6, .35), (1, 0)])],
    "arc": lambda: [stroke([(1, .9), (.55, 1), (0, .5), (.55, 0), (1, .1)])],
    "S": lambda: [stroke([(1, .9), (.5, 1), (0, .75), (.5, .5), (1, .25), (.5, 0), (0, .1)])],
})
ORTHO_MOTIFS.update({
    "L": lambda: [stroke([(0, 1), (0, 0), (1, 0)])],
    "T": lambda: [stroke([(0, 1), (1, 1)]), stroke([(.5, 1), (.5, 0)])],
    "H": lambda: [stroke([(0, 0), (0, 1)]), stroke([(1, 0), (1, 1)]), stroke([(0, .5), (1, .5)])],
    "F": lambda: [stroke([(0, 0), (0, 1)]), stroke([(0, 1), (1, 1)]), stroke([(0, .5), (.7, .5)])],
    "P": lambda: [stroke([(0, 0), (0, 1), (1, 1), (1, .45), (0, .45)])],
    "Pi": lambda: [stroke([(0, 0), (0, 1), (1, 1), (1, 0)])],
    "Zq": lambda: [stroke([(0, 1), (1, 1), (1, .5), (0, .5), (0, 0), (1, 0)])],
    "comb": lambda: [stroke([(0, 0), (0, 1)])] + [stroke([(0, y), (1, y)]) for y in (.1, .5, .9)],
    "harp": lambda: [stroke([(0, .1), (1, .1)])] + [stroke([(x, .1), (x, 1)]) for x in (.1, .5, .9)],
    "house": lambda: [stroke([(0, 0), (1, 0), (1, .7), (0, .7)], True), stroke([(.5, 0), (.5, .7)]), stroke([(.5, .7), (.5, 1)])],
})
# the complexity window (0 ornate .. 1 bold) in which a figure is offered, and the corner styles it suits
LEVELS = {
    "eye": (0, .45), "ankh": (0, .5), "fish": (0, .5), "person": (0, .4), "harp": (0, .5), "comb": (0, .55), "curl": (0, .5),
    "zigzag": (0, .7), "house": (0, .5), "target": (0, .45), "tri2": (0, .6), "ring2": (0, .7), "ringcross": (0, .8), "trident": (0, .8),
    "nest": (0, .45), "ladder": (0, .5), "box2": (0, .7), "boxplus": (0, .7), "B": (.3, 1), "Q": (.2, 1), "W": (.3, 1),
    "M": (.3, 1), "K": (.3, 1), "S": (.3, 1), "P": (.3, 1), "F": (.3, 1), "E": (.3, 1), "Y": (.3, 1), "T": (.3, 1), "L": (.35, 1),
    "H": (.3, 1), "Z": (.3, 1), "N": (.35, 1), "V": (.4, 1), "arc": (.3, 1), "tri": (.25, 1), "tri_down": (.25, 1), "diamond": (.2, 1),
}
LEVELS.update({n: (0, .3) for n in ("ladder", "E3", "harp", "comb", "person", "nest", "house", "boxplus", "target")})   # dense figures: ornate only
ROUND_ONLY = {"eye", "ankh", "fish", "curl", "ring", "ring2", "ringcross", "target", "Q", "arc", "S", "diamond"}
ANGULAR_ONLY = {"tri", "tri_down", "tri2", "diamond", "zigzag", "Z", "N", "M", "W", "V", "K", "Y", "L", "T", "H", "F", "E",
                "X", "trident", "comb", "harp", "person", "fish"}


def eligible(table, c, style, levels=None):
    """Names of the figures offered at complexity c for a corner style (widened if too few fit)."""
    def ok(n, widen):
        lo, hi = (levels or LEVELS).get(n, (0, 1))
        if not (lo - widen <= c <= hi + widen):
            return False
        if style == "smooth" and n in ANGULAR_ONLY and n not in ROUND_ONLY:
            return False
        if style == "sharp" and n in ROUND_ONLY and n not in ANGULAR_ONLY:
            return False
        return True
    for widen in (0.0, 0.15, 0.4, 1.0):
        names = [n for n in table if ok(n, widen)]
        if len(names) >= 6:
            return names
    return list(table)


def stroke_budget(c):
    """Most strokes a letter may have at complexity c (relaxed a little when the alphabet is crowded)."""
    return 3 if c >= 0.75 else 4 if c >= 0.5 else 6 if c >= 0.25 else 8


XFORMS = ("rot90", "rot270", "rot180", "flip_x", "flip_y")        # turn or mirror a figure (any letter can be derived this way)
ALL_OPS = ["stem_down", "stem_up", "stem_left", "stem_right", "bar_h", "bar_v", "bar_lo", "bar_hi", "dot_in", "open", "rot90",
           "through_v", "through_h", "hook", "underline", "overline", "cross", "x_in", "slash", "tail", "flag", "arrow", "curl"]
_BOLD_OPS = {"plain", "stem_down", "stem_up", "stem_left", "stem_right", "bar_h", "bar_v", "bar_lo", "bar_hi", "open", "slash", "tail",
             "underline", "overline", "rot90", "rot270", "rot180", "flip_x", "flip_y"}
_MID_BAN = {"through_v", "through_h", "dot_in"}


def op_allowed(op, c):
    """Whether a modifier (or pair) may be used at complexity c: bold scripts keep to plain strokes and bars."""
    parts = op.split("+")
    if c >= 0.75:
        return all(p in _BOLD_OPS for p in parts) and len(parts) == 1
    if c >= 0.5:
        return not any(p in _MID_BAN for p in parts)
    return True


def allowed_ops(c):
    return {o for o in ["plain"] + ALL_OPS + list(XFORMS) if op_allowed(o, c)}


def simplify(strokes, c):
    """Simplification operators for bold scripts: drop dots, then drop the shortest strokes that are not needed for
    connectivity until the stroke budget is met."""
    from .geometry import length
    out = [s for s in strokes if not (c >= 0.5 and s.get("dot"))]
    budget = stroke_budget(c)
    while len(out) > budget:
        order = sorted(range(len(out)), key=lambda i: length(out[i]["p"]) if not out[i].get("dot") else 0)
        for i in order:
            trial = out[:i] + out[i + 1:]
            if analyse(trial)["parts"] == 1:
                out = trial
                break
        else:
            break
    return out


VARIANTS = ["plain", "stem_down", "stem_up", "stem_left", "stem_right", "bar_h", "bar_v", "dot_in", "open", "rot90",
            "through_v", "through_h", "flip_y", "hook"]

# phoneme -> the class that shares a characteristic shape
CLASSES = {
    "labial": "p b m f v w pʰ".split(), "coronal": "t d n s z l r θ ð ts ʃ ʒ tʃ dʒ tʰ".split(),
    "dorsal": "k g ŋ x ɣ j ɲ q kʰ".split(), "glottal": "h ʔ".split(),
    "front": "i e y ø ɛ æ ɪ".split(), "back": "u o ɔ ʊ ɑ".split(), "central": "a ə".split(),
}
CLASS_ORDER = list(CLASSES)
CLASS_OF = {p: c for c, ps in CLASSES.items() for p in ps}

# Rule D: letters that look alike should sound alike. Every phoneme belongs to a sound group (vowel, or a manner of
# articulation); a group steers both which stroke families its plain letters grow from and which variant of a
# characteristic shape its letters wear, so a plosive resembles another plosive more than it resembles a vowel.
MANNERS = {
    "vowel": "a i u e o ə ɔ ɛ ɪ y ø ɑ æ ʊ".split(),
    "plosive": "p t k b d g q ʔ pʰ tʰ kʰ".split(),
    "affricate": "ts tʃ dʒ".split(),
    "fricative": "f v s z ʃ ʒ θ ð x ɣ h".split(),
    "nasal": "m n ŋ ɲ".split(),
    "approximant": "l r j w".split(),
}
GROUP_OF = {p: g for g, ps in MANNERS.items() for p in ps}
GROUP_FAMILIES = {          # stroke-family weights for plain (non-motif) bodies; unlisted families get a low base weight
    "vowel": {"ring": 3.0, "C": 2.0, "U": 1.6, "hook": 0.6, "stem": 0.3},
    "plosive": {"stem": 3.0, "bar": 1.6, "corner": 1.6, "fork": 0.9, "arch": 0.5, "diag": 0.4},
    "affricate": {"corner": 1.6, "Z": 1.6, "zig": 1.3, "stem": 1.2, "diag": 1.0, "fork": 0.8},
    "fricative": {"diag": 2.6, "zig": 2.0, "V": 1.6, "W": 1.2, "Z": 1.2, "fork": 1.0},
    "nasal": {"arch": 2.8, "wave": 2.0, "U": 1.0, "S": 0.8},
    "approximant": {"curl": 2.2, "S": 2.0, "hook": 2.0, "tail": 1.3},
}
PLACE_OPS = {               # the variant of a group's shape that marks the place of articulation (or vowel class)
    "labial": ["plain", "dot_in", "bar_h"], "coronal": ["bar_v", "stem_down", "through_h"],
    "dorsal": ["stem_up", "hook", "rot90"], "glottal": ["open", "flip_y", "through_v"],
    "front": ["plain", "bar_v", "dot_in"], "back": ["open", "flip_y", "rot90"], "central": ["bar_h", "dot_in", "through_h"],
}
GROUP_ORDER = ["plosive", "fricative", "nasal", "approximant", "vowel", "affricate"]
# variants that reach the ascender or descender line (the shape itself stays in the main frame)
_VERT = {"stem_down": "desc", "hook": "desc", "curl": "desc", "stem_up": "asc", "flag": "asc", "arrow": "asc", "through_v": "both"}
VERTICAL_OPS = _VERT


def vertical_of(op):
    """"asc", "desc" or "both" when the modifier (or a pair of them) reaches the ascender and/or descender line."""
    kinds = {_VERT[p] for p in op.split("+") if p in _VERT}
    if not kinds:
        return None
    return "both" if (len(kinds) > 1 or "both" in kinds) else kinds.pop()


def _extreme(pts, key, pick):
    best = pick(key(p) for p in pts)
    tied = [p for p in pts if abs(key(p) - best) < 0.03]
    return sorted(tied, key=lambda p: abs(p[0] - .5) + abs(p[1] - .5))[0]


def _rot90(strokes):
    out = []
    for s in strokes:
        t = dict(s)
        t["p"] = [[round(1 - y, 4), round(x, 4)] for x, y in s["p"]]
        out.append(t)
    return out


def apply_variant(strokes, op, ortho=False):
    """The figure with a modifier (or two, "a+b") applied, or None if it does not apply or would look confusing."""
    cur = strokes
    parts = sorted(op.split("+"), key=lambda p: 0 if p in XFORMS else 1)           # turn or mirror first, then add lines
    turned = strokes
    for part in parts:
        cur = _apply_one(cur, part, ortho)
        if cur is None:
            return None
        if part in XFORMS:
            turned = cur
    return cur if _variant_ok(turned, parts, cur) else None


# ---- what makes a modification look wrong (design feedback on the sample scripts) ------------------------------------
DIAGONAL_OPS = {"slash", "x_in", "tail"}
BAR_OPS = {"bar_h", "bar_lo", "bar_hi", "underline", "overline", "through_h"}       # bars at different heights are one kind of change


def _segs(p, closed=False):
    q = [tuple(a) for a in p] + ([tuple(p[0])] if closed else [])
    return [(b[0] - a[0], b[1] - a[1]) for a, b in zip(q, q[1:]) if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6]


def _turns(segs):
    out = []
    for (ax, ay), (bx, by) in zip(segs, segs[1:] + segs[:1]):
        out.append((math.degrees(math.atan2(ax * by - ay * bx, ax * bx + ay * by))))
    return out


def stroke_shape(s):
    """'axis' (only horizontal and vertical lines), 'curve' (many short segments turning gently, one way) or 'angular'."""
    segs = _segs(s["p"], s.get("closed", False))
    if all(abs(dx) < 1e-3 or abs(dy) < 1e-3 or min(abs(dx), abs(dy)) / max(abs(dx), abs(dy)) < 0.1 for dx, dy in segs):
        return "axis"
    t = _turns(segs) if s.get("closed") else _turns(segs)[:-1]
    if len(segs) >= 6 and max(abs(a) for a in t) <= 62 and (all(a >= -1 for a in t) or all(a <= 1 for a in t)):
        return "curve"
    return "angular"


def simple_for_diagonal(strokes):
    """A diagonal slash only goes on a simple shape: one stroke that is a plain box or a curve that bends one way. Slashing an
    angular shape, an S or a figure with several strokes reads as clutter."""
    body = [s for s in strokes if not s.get("dot")]
    return len(body) == 1 and len(body) == len(strokes) and stroke_shape(body[0]) in ("axis", "curve")


def _reversals_of(p):
    best = 0
    for ax in (0, 1):
        d = [p[i + 1][ax] - p[i][ax] for i in range(len(p) - 1)]
        d = [x for x in d if abs(x) > 0.02]
        best = max(best, sum(1 for a, b in zip(d, d[1:]) if a * b < 0))
    return best


def _structure(strokes):
    """The lines a figure implies: its centre lines and the positions of its corners and ends."""
    ys, xs = {0.0, 0.5, 1.0}, {0.0, 0.5, 1.0}
    for s in strokes:
        for x, y in s["p"]:
            xs.add(round(x, 3))
            ys.add(round(y, 3))
    return sorted(xs), sorted(ys)


def _near_miss(c, lines, lo=0.025, hi=0.13):
    return any(lo < abs(c - l) < hi for l in lines)


def _variant_ok(base, parts, result):
    if any(p in DIAGONAL_OPS for p in parts) and not simple_for_diagonal(base):
        return False
    lines_ = [p for p in parts if p not in XFORMS]
    body = [s for s in base if not s.get("dot")]
    if lines_ and any(_reversals_of(s["p"]) >= 4 for s in body):     # an already wavy figure takes no further marks
        return False
    if len(lines_) > 1:                                  # two additions at once: only on a plain figure, and never a slash
        plain = len(body) <= 2 and all(stroke_shape(s) in ("axis", "curve") for s in body)
        if not plain or any(p in DIAGONAL_OPS for p in lines_):
            return False
    xs, ys = _structure(base)
    for p in parts:                                      # extra strokes line up with the figure's own lines, or keep clear of them
        if p in ("bar_h", "cross", "through_h") and _near_miss(.5, ys):
            return False
        if p in ("bar_v", "cross", "through_v") and _near_miss(.5, xs):
            return False
    lines = [s for s in result if not s.get("dot")]
    for d in (s for s in result if s.get("dot")):        # a dot must stand clear of every line, or it vanishes into the figure
        cx, cy = d["p"][0]
        if any(math.hypot(x - cx, y - cy) < 0.2 for x, y in points(lines, step=0.04)):
            return False
    return True


def _apply_one(strokes, op, ortho=False):
    """The shape with one change. Returns None if the change does not apply to this shape."""
    base = [dict(s, p=[list(p) for p in s["p"]]) for s in strokes]
    pts = points(base, step=0.05)
    if op == "plain":
        return base
    if op in ("stem_down", "stem_up"):                  # stems reach the descender / ascender line exactly
        down = op == "stem_down"
        a = _extreme(pts, lambda p: p[1], min if down else max)
        return base + [stroke([a, (a[0], -.5 if down else 1.55)])]
    if op.startswith("stem_"):
        key, pick, vec = {"left": (lambda p: p[0], min, (-.5, 0)), "right": (lambda p: p[0], max, (.5, 0))}[op[5:]]
        a = _extreme(pts, key, pick)
        return base + [stroke([a, (a[0] + vec[0], a[1] + vec[1])])]
    if op == "hook":
        a = _extreme(pts, lambda p: p[1], min)
        if ortho:
            return base + [stroke([a, (a[0], -.5), (a[0] + .4, -.5)])]
        return base + [stroke([a, (a[0], -.25), (a[0] + .25, -.5)])]
    if op in ("underline", "overline"):
        return base + [stroke([(-.1, -.04 if op == "underline" else 1.04), (1.1, -.04 if op == "underline" else 1.04)])]
    if op in ("bar_lo", "bar_hi"):                       # a bar off the middle sits on one of the figure's own lines, or not at all
        lo = op == "bar_lo"
        cands = [y for y in _structure(base)[1] if (.2 <= y <= .4 if lo else .6 <= y <= .8)]
        if not cands:
            return None
        y = min(cands, key=lambda v: abs(v - (.3 if lo else .7)))
        return base + [stroke([(-.05, y), (1.05, y)])]
    if op == "cross":
        return base + [stroke([(.5, -.05), (.5, 1.05)]), stroke([(-.05, .5), (1.05, .5)])]
    if op == "x_in":
        return base + [stroke([(0, 0), (1, 1)]), stroke([(0, 1), (1, 0)])]
    if op == "slash":
        return base + [stroke([(-.05, -.05), (1.05, 1.05)])]
    if op == "tail":
        return base + [stroke([(.55, .35), (1.05, -.05)])]
    if op in ("flag", "arrow"):                          # a stem to the ascender line with a branch or a head on it
        a = _extreme(pts, lambda p: p[1], max)
        stem = stroke([a, (a[0], 1.55)])
        head = ([stroke([(a[0], 1.55), (a[0] + .3, 1.3)])] if op == "flag"
                else [stroke([(a[0] - .22, 1.33), (a[0], 1.55), (a[0] + .22, 1.33)])])
        return base + [stem] + head
    if op == "curl":                                     # a curved tail down to the descender line
        a = _extreme(pts, lambda p: p[1], min)
        return base + [stroke([a, (a[0], -.25), (a[0] + .2, -.5), (a[0] + .45, -.4)])]
    if op == "bar_h":
        return base + [stroke([(0, .5), (1, .5)])]
    if op == "bar_v":
        return base + [stroke([(.5, 0), (.5, 1)])]
    if op == "through_v":
        return base + [stroke([(.5, -.5), (.5, 1.55)])]
    if op == "through_h":
        return base + [stroke([(-.35, .5), (1.35, .5)])]
    if op == "dot_in":
        return base + [dot(.5, .5, .09)]
    if op == "open":
        for i, s in enumerate(base):
            if s.get("closed") and len(s["p"]) >= 4:
                k = max(range(len(s["p"])), key=lambda j: s["p"][j][0])      # open the shape on its right side
                p = s["p"][k:] + s["p"][:k + 1]
                base[i] = dict(s, p=p[1:], closed=False)
                return base
        return None
    if op == "rot90":
        return _rot90(base)
    if op == "rot270":
        return _rot90(_rot90(_rot90(base)))
    if op == "rot180":
        return _rot90(_rot90(base))
    if op == "flip_x":
        return [dict(s, p=[[round(1 - x, 4), y] for x, y in s["p"]]) for s in base]
    if op == "flip_y":
        return [dict(s, p=[[x, round(1 - y, 4)] for x, y in s["p"]]) for s in base]
    return None


def usable(strokes, ortho=False):
    """Connected, not too busy, not a doubled line."""
    if not strokes:
        return False
    a = analyse(strokes)
    if a["parts"] != 1 or a["ends"] > 6 or a["loops"] > 3 or any(d > 4 for d in a["junctions"]):
        return False
    if ortho:
        c = classify(strokes)
        if c["angular"] or c["gentle"] or c["diagonal"]:
            return False
    return True


def style_strokes(rng, strokes, style):
    """Tag every stroke with its corner kind ('s','m','b','h') the way make_styled_body does."""
    if style == "smooth":
        kinds = ["m"] * len(strokes)
    elif style == "sharp":
        kinds = ["s"] * len(strokes)
    elif style == "blocky":
        kinds = ["b"] * len(strokes)
    else:
        pref = "m" if rng.random() < 0.45 else "s"
        kinds = []
        for st in strokes:
            c = classify([st]) if not st.get("dot") else {"angular": 0, "gentle": 0, "right": 0}
            if c["angular"]:
                kinds.append(pref)
            elif c["gentle"]:
                kinds.append("h" if c["right"] and rng.random() < 0.6 else "m")
            elif c["right"]:
                kinds.append(rng.choices(["b", "m", "h"], [0.5, 0.3, 0.2])[0])
            else:
                kinds.append(None)
        main = next((k for k in kinds if k), pref)
        kinds = [k or main for k in kinds]
    return [dict(s, k=k) if not s.get("dot") else s for s, k in zip(strokes, kinds)], (kinds[0] if kinds else "m")
