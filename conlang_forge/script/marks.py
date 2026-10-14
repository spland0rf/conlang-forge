"""Marks and slots: small parts (dots, ticks, hooks, short stems) that sit in a slot beside a letter body. The same
machinery draws diacritics (above/below), abugida vowel signs (left/right/above/below, one part or a two-part frame)
and the virama. A part is drawn in its own unit box and sized by (w, h); it attaches to the nearest ink of the base
so a "touching" part always forms one connected piece."""
from __future__ import annotations

from .geometry import LINES, bbox, dot, place, shift, stroke
from .graph import points
from .motifs import FAMILY_WEIGHTS, make_styled_body

SLOTS = ("left", "right", "above", "below")
_MINI = {k: 0.0 for k in FAMILY_WEIGHTS}
_MINI.update({"stem": 1.4, "diag": 1.0, "hook": 1.2, "tail": 0.9, "corner": 0.4, "C": 0.5})


def _dots(n, slot):
    if n == 1:
        pts = [(.5, .5)]
    elif n == 2:
        pts = [(.2, .5), (.8, .5)] if slot in ("above", "below") else [(.5, .2), (.5, .8)]
    else:
        pts = [(.2, .25), (.8, .25), (.5, .85)] if slot in ("above", "below") else [(.3, .15), (.3, .85), (.8, .5)]
    return [dot(x, y, 0.16) for x, y in pts]


def make_part(rng, slot, density=0.2, loops=0.3, dots_p=0.3, style="mixed"):
    """A random part for a slot: dots, or a simple connected mini-shape. Returns the part record."""
    side = slot in ("left", "right")
    if rng.random() < dots_p:
        n = rng.choice([1, 1, 2, 3])
        strokes, kind = _dots(n, slot), f"dots{n}"
        pw, ph = (0.24, 0.24 + 0.2 * (n - 1)) if side else (0.24 + 0.12 * (n - 1), 0.24)
        # a dot's radius is in unit-box units, so keep the box square-ish: draw dots in em units directly
        strokes = [dot(s["p"][0][0] * pw, s["p"][0][1] * ph, 0.065) for s in strokes]
        return {"kind": kind, "strokes": strokes, "w": pw, "h": ph, "box": "em", "touch": rng.random() < 0.3}
    body, fam, _ = make_styled_body(rng, 0.0, 0.0, _MINI, style)
    pw = rng.uniform(0.26, 0.42) if side else rng.uniform(0.38, 0.6)
    ph = rng.uniform(0.6, 1.05) if side else rng.uniform(0.26, 0.4)
    touch = True if side else rng.random() < 0.45
    return {"kind": fam, "strokes": body, "w": round(pw, 3), "h": round(ph, 3), "box": "unit", "touch": touch}


def grow_part(rng, part, slot):
    """The long version of a part: the same shape with one extra stroke (or one more dot) -- the +LONG rule."""
    from .motifs import grow, valid
    if part["kind"].startswith("dots"):
        n = min(3, int(part["kind"][4:]) + 1)
        if n == int(part["kind"][4:]):
            return None
        pw, ph = (0.24, 0.24 + 0.2 * (n - 1)) if slot in ("left", "right") else (0.24 + 0.12 * (n - 1), 0.24)
        strokes = [dot(s["p"][0][0] * pw, s["p"][0][1] * ph, 0.065) for s in _dots(n, slot)]
        return dict(part, kind=f"dots{n}", strokes=strokes, w=pw, h=ph)
    for _ in range(40):
        s2 = grow(rng, part["strokes"], 0.0)
        if len(s2) > len(part["strokes"]) and valid(s2, 3, 1, 6):
            k = part["strokes"][0].get("k", "m")
            return dict(part, strokes=s2[:-1] + [dict(s2[-1], k=k)], kind=part["kind"] + "+")
    return None


def _extreme(pts, key, pick):
    best = pick(key(p) for p in pts)
    tied = sorted((p for p in pts if abs(key(p) - best) < 0.03), key=lambda p: p[1] if key is _kx else p[0])
    return tied[len(tied) // 2]


def _kx(p):
    return p[0]


def _ky(p):
    return p[1]


def place_part(base, slot, part):
    """The part's strokes placed in `slot` of the base strokes (list of strokes), attached at the nearest ink."""
    pts = points(base, step=0.04)
    pw, ph = part["w"], part["h"]
    st = place(part["strokes"], (0, 0, pw, ph)) if part["box"] == "unit" else part["strokes"]
    mine = points(st, step=0.04) or [tuple(s["p"][0]) for s in st]
    gap = 0.0 if part["touch"] else (0.1 if slot in ("left", "right") else 0.12)
    if slot == "right":
        a, m = _extreme(pts, _kx, max), _extreme(mine, _kx, min)
        d = (a[0] - m[0] + gap, a[1] - m[1])
    elif slot == "left":
        a, m = _extreme(pts, _kx, min), _extreme(mine, _kx, max)
        d = (a[0] - m[0] - gap, a[1] - m[1])
    elif slot == "above":
        a, m = _extreme(pts, _ky, max), _extreme(mine, _ky, min)
        d = (a[0] - m[0], a[1] - m[1] + gap)
    else:
        a, m = _extreme(pts, _ky, min), _extreme(mine, _ky, max)
        d = (a[0] - m[0], a[1] - m[1] - gap)
    out = shift(st, *d)
    lo, hi = LINES["descender"] - 0.15, LINES["ascender"] + 0.5
    b = bbox(out)
    if b[1] < lo:
        out = shift(out, 0, lo - b[1])
    if b[3] > hi:
        out = shift(out, 0, hi - b[3])
    return out
