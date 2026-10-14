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
    "tri2": lambda: [stroke([(.5, 1), (.85, .5), (.15, .5)], True), stroke([(.5, .5), (1, 0), (0, 0)], True)],
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
VERTICAL_OPS = {"stem_down": "desc", "hook": "desc", "stem_up": "asc", "through_v": "both"}


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
    """The shape with one change. Returns None if the change does not apply to this shape."""
    base = [dict(s, p=[list(p) for p in s["p"]]) for s in strokes]
    pts = points(base, step=0.05)
    if op == "plain":
        return base
    if op.startswith("stem_"):
        d = op[5:]
        key, pick, vec = {"down": (lambda p: p[1], min, (0, -.5)), "up": (lambda p: p[1], max, (0, .55)),
                          "left": (lambda p: p[0], min, (-.5, 0)), "right": (lambda p: p[0], max, (.5, 0))}[d]
        a = _extreme(pts, key, pick)
        return base + [stroke([a, (a[0] + vec[0], a[1] + vec[1])])]
    if op == "hook":
        a = _extreme(pts, lambda p: p[1], min)
        if ortho:
            return base + [stroke([a, (a[0], a[1] - .4), (a[0] + .4, a[1] - .4)])]
        return base + [stroke([a, (a[0], a[1] - .3), (a[0] + .25, a[1] - .5)])]
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
