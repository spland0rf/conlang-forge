"""Stroke-graph forms: the traced Devanagari letters (`forms/devanagari_graph.json`, from the stroke-graph model) and a corpus of
new "Devanagari-like" letters (`forms/devanagari_corpus.json`) built offline by Generator v2 (scripts/script_analysis/
devanagari_stroke_model/generator/gen_corpus.js).

Both are stored in the model's 100 x 100 box (x right, y down, headline at y = 20, baseline at y = 88) as SVG path strings with a
role per stroke: body (blue), second (green), struct (purple: headline and short descenders), accent (orange). `to_unit` maps them
into the pen engine's unit box (y up, headline at TOP = 1, baseline 0). The headline bar itself is left out: the caller draws it
over the letter's width, so the descenders and stems that touch it simply reach y = 1."""
from __future__ import annotations

import json
import math
import os
import re

from .geometry import stroke

_DIR = os.path.join(os.path.dirname(__file__), "forms")
TOP_Y, BASE_Y = 20.0, 88.0
_TOK = re.compile(r"[MHVLCQ]|-?\d+\.?\d*")
_cache: dict = {}


def _load(name):
    if name not in _cache:
        with open(os.path.join(_DIR, name), encoding="utf-8") as f:
            _cache[name] = json.load(f)
    return _cache[name]


def polyline(d, n=10):
    """Sample an M/H/V/L/C/Q path into points (model coordinates)."""
    tk, i, cur, cmd, pts = _TOK.findall(d), 0, (0.0, 0.0), None, []

    def num():
        nonlocal i
        i += 1
        return float(tk[i - 1])

    while i < len(tk):
        if tk[i].isalpha():
            cmd = tk[i]
            i += 1
        if cmd == "M":
            cur = (num(), num())
            pts.append(cur)
        elif cmd == "H":
            x = num()
            pts.append((x, cur[1]))
            cur = (x, cur[1])
        elif cmd == "V":
            y = num()
            pts.append((cur[0], y))
            cur = (cur[0], y)
        elif cmd == "L":
            cur = (num(), num())
            pts.append(cur)
        elif cmd == "Q":
            c, p = (num(), num()), (num(), num())
            for k in range(1, n + 1):
                t = k / n
                pts.append(tuple((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * e for a, b, e in zip(cur, c, p)))
            cur = p
        elif cmd == "C":
            c1, c2, p = (num(), num()), (num(), num()), (num(), num())
            for k in range(1, n + 1):
                t = k / n
                pts.append(tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * e for a, b, c, e in zip(cur, c1, c2, p)))
            cur = p
    return pts


def is_bar(role, d):
    m = re.fullmatch(r"M([\d.]+) ([\d.]+) H([\d.]+)", d.strip())
    return role == "struct" and bool(m) and abs(float(m.group(2)) - TOP_Y) < 0.01 and abs(float(m.group(3)) - float(m.group(1))) > 30


def to_unit(pts):
    return [(x / 100.0, (BASE_Y - y) / (BASE_Y - TOP_Y)) for x, y in pts]


def strokes_of(items, keep_bar=False):
    """Pen-engine strokes from (role, path) pairs. Straight verticals/horizontals keep exactly two points."""
    out = []
    for it in items:
        role, d = it[0], it[1]
        if is_bar(role, d) and not keep_bar:
            continue
        pts = polyline(d)
        # drop repeated points
        clean = [pts[0]] + [p for a, p in zip(pts, pts[1:]) if math.dist(a, p) > 1e-6]
        if len(clean) < 2:
            continue
        u = to_unit(clean)
        out.append(dict(stroke([(round(x, 4), round(y, 4)) for x, y in u]), role=role))
    return out


def real_letters():
    return _load("devanagari_graph.json")["letters"]


def real_strokes(glyph, variant=None, keep_bar=False):
    for l in real_letters():
        if l["glyph"] == glyph and (variant is None or l["variant"] == variant):
            return strokes_of(l["strokes"], keep_bar)
    raise KeyError(glyph)


def corpus():
    return _load("devanagari_corpus.json")["styles"]


def corpus_letter(rng, style_id=None):
    """A new letter from the corpus: its strokes (no bar) in the unit box. Without a style id it picks any style."""
    sts = corpus()
    st = sts[style_id % len(sts)] if style_id is not None else rng.choice(sts)
    letter = rng.choice(st["letters"])
    return strokes_of(letter["s"])
