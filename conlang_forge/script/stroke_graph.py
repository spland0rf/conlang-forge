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


BAR_OVERHANG = 8.0          # model units: the headline carries on a little past the last stroke that meets it


def _contacts(items):
    """x of every point (not on a bar) that lies on the headline line."""
    xs = []
    for it in items:
        if is_bar(it[0], it[1]):
            continue
        xs += [x for x, y in polyline(it[1]) if abs(y - TOP_Y) < 1.5]
    return xs


def _with_bar_overhang(items):
    """Real letters: a purple bar that stops exactly at its last contact is carried on a little to the right."""
    xs, out = _contacts(items), []
    for it in items:
        if is_bar(it[0], it[1]):
            m = re.fullmatch(r"M([\d.]+) ([\d.]+) H([\d.]+)", it[1].strip())
            x0, x1 = float(m.group(1)), float(m.group(3))
            if xs and abs(x1 - max(xs)) < 2.0:
                it = (it[0], f"M{x0:g} {TOP_Y:g} H{x1 + BAR_OVERHANG:g}", *it[2:])
        out.append(it)
    return out


def own_bar(items):
    """Corpus letters: a headline from the left edge to the right edge, and past the last contact by the overhang (so a letter whose
    stem is its right edge still has bar beyond it). Returns the bar path, or None."""
    allx = [x for it in items for x, _ in polyline(it[1])]
    xs = _contacts(items)
    if not xs:
        return None
    return f"M{min(allx):g} {TOP_Y:g} H{max(max(allx), max(xs) + BAR_OVERHANG):g}"


def strokes_of(items, keep_bar=False):
    """Pen-engine strokes from (role, path) pairs. Straight verticals/horizontals keep exactly two points."""
    out = []
    if keep_bar:
        items = _with_bar_overhang(items)
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


def junctions(letter):
    """(type, x, y) marks in the unit box: red (forms meet), touch (orange circle), cross (orange x)."""
    return [(j[0], j[1] / 100.0, (BASE_Y - j[2]) / (BASE_Y - TOP_Y)) for j in letter["j"]]


def real_junctions(glyph, variant=None):
    for l in real_letters():
        if l["glyph"] == glyph and (variant is None or l["variant"] == variant):
            return [(j["t"], j["x"] / 100.0, (BASE_Y - j["y"]) / (BASE_Y - TOP_Y)) for j in l["junctions"]]
    raise KeyError(glyph)


def real_letters():
    return _load("devanagari_graph.json")["letters"]


def real_strokes(glyph, variant=None, keep_bar=False):
    for l in real_letters():
        if l["glyph"] == glyph and (variant is None or l["variant"] == variant):
            return strokes_of(l["strokes"], keep_bar)
    raise KeyError(glyph)


def no_bar(key):
    """Generator v2 letter key (bar|right side|body|...): a letter with no bar of its own, or with the reversed "3" body, is drawn without
    the purple headline (the model's "3" forms carry no bar; a joined green form brings its own short top bar)."""
    f = key.split("|")
    return f[0] == "0" or f[2] == "rev3"


def corpus():
    return _load("devanagari_corpus.json")["styles"]


def corpus_letter(rng, style_id=None):
    """A new letter from the corpus: its strokes (no bar) in the unit box. Without a style id it picks any style."""
    sts = corpus()
    st = sts[style_id % len(sts)] if style_id is not None else rng.choice(sts)
    letter = rng.choice(st["letters"])
    items = [tuple(i) for i in letter["s"] if not is_bar(i[0], i[1])]
    if no_bar(letter["key"]):
        return [dict(t, nobar=True) for t in strokes_of(items)]
    bar = own_bar(items)
    out = strokes_of(items + [("struct", bar)], keep_bar=True) if bar else strokes_of(items)
    return [dict(t, nobar=True) for t in out]               # the letter brings its own headline; the caller adds none
