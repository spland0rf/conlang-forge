"""Stroke bias: which lines a script's base letters lean on (vertical, horizontal, diagonal, round, or a mix).

Each base figure gets a score for a bias, the share of its ink that matches; the script's characteristic shapes are then
taken from the best-scoring figures first. "balanced" changes nothing."""
from __future__ import annotations

import math

from .shapes import _segs, stroke_shape

PARTS = {"vertical": ("v",), "horizontal": ("h",), "diagonal": ("d",), "round": ("r",),
         "vertical+diagonal": ("v", "d"), "horizontal+vertical": ("h", "v")}
TOL = 18.0            # degrees from true vertical or horizontal that still counts as vertical or horizontal


def profile(strokes) -> dict:
    """Share of a figure's ink (by length) that is vertical (v), horizontal (h), diagonal (d) and round (r)."""
    tot = {"v": 0.0, "h": 0.0, "d": 0.0, "r": 0.0}
    for s in strokes:
        if s.get("dot"):
            continue
        segs = _segs(s["p"], s.get("closed", False))
        round_ = stroke_shape(s) == "curve"
        for dx, dy in segs:
            ln = math.hypot(dx, dy)
            ang = abs(math.degrees(math.atan2(dy, dx))) % 180
            if round_:
                tot["r"] += ln
            elif abs(ang - 90) <= TOL:
                tot["v"] += ln
            elif ang <= TOL or ang >= 180 - TOL:
                tot["h"] += ln
            else:
                tot["d"] += ln
    n = sum(tot.values()) or 1.0
    return {k: v / n for k, v in tot.items()}


def score(strokes, bias: str) -> float:
    """0..1: how well a figure fits the bias (1 = all of its ink is of the wanted kinds)."""
    parts = PARTS.get(bias)
    if not parts:
        return 0.0
    p = profile(strokes)
    return sum(p[k] for k in parts)
