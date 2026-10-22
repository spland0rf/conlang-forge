"""Generate a writing system from a seed (plus optional pins). Pure standard library and fully deterministic: each part
of the script draws from its own random stream, so pinning one dial changes only what depends on it.

Stage 1 covers linear alphabets and abjads, and abugidas whose vowel signs sit in slots around the consonant letter.
Letters are grown as connected stroke graphs (motifs.py); roundness is applied only when drawing."""
from __future__ import annotations

import math

from ..wordgen import rng_for
from .geometry import LINES, bbox, dot, mirror_x, pin_junctions, place, shift, stroke, transform
from .graph import analyse, distance, far_enough, mean_distance, points
from . import bias, kana
from .marks import grow_part, make_part, place_part
from .motifs import _tag, make_styled_body
from .families import FORMS, MODS
from . import forms as shape_forms
from .motifs import FAMILY_WEIGHTS
from .shapes import (BAR_OPS, CLASS_OF, CLASS_ORDER, GROUP_FAMILIES, GROUP_OF, GROUP_ORDER, MOTIFS, ORTHO_MOTIFS, VARIANTS,
                     XFORMS, op_allowed, vertical_of, apply_variant, eligible, simplify, stroke_budget, style_strokes, usable)
from .spec import DEFAULT_CONSONANTS, DEFAULT_VOWELS, resolve

STEP = 0.11
STDW = 0.8          # letters are compared as if they were this wide, so a wider or narrower copy is not a new letter


def _npts(strokes, w, step=STEP):
    """The ink as sampled points with x measured in letter widths (scaled to STDW). Comparing these makes two letters that
    differ only by horizontal stretching look identical to the distinctness checks (rule C)."""
    k = STDW / (w or STDW)
    return [(x * k, y) for x, y in points(strokes, step=step)]


def norm_points(letter, step=0.05):
    k = STDW / (letter["width"] or STDW)
    return [(x * k, y) for x, y in points(letter["strokes"], step=step)]


def _family_weights(group, loops):
    w = dict(FAMILY_WEIGHTS)
    w["ring"] *= 0.3 + 1.6 * loops
    w["C"] *= 0.7 + 0.6 * loops
    if group in GROUP_FAMILIES:
        base = {f: 0.05 for f in w}
        base.update(GROUP_FAMILIES[group])
        return base
    return None


def _count(strokes):
    return len([s for s in strokes if "stub" not in s])


def _budget(spec, frac=0.0):
    """Strokes allowed per letter: set by the complexity dial, loosened a little when the alphabet is crowded."""
    return stroke_budget(spec["complexity"]) + (1 if frac > 0.5 else 0) + (2 if frac > 0.8 else 0)


def _floor(spec, frac=0.0):
    """Fewest strokes a letter may have: ornate scripts do not use bare one-stroke letters (relaxed when crowded)."""
    c = spec["complexity"]
    base = 4 if c < 0.15 else 3 if c < 0.4 else 1
    return max(1, base - (1 if frac > 0.5 else 0) - (1 if frac > 0.8 else 0))


def _extend(core, band, kind):
    """An ascender or descender: a stroke from the body's top (or bottom) down or up to the ascender (descender) line. The
    body itself stays in the main frame (rules A and B)."""
    if band not in ("asc", "desc"):
        return core
    pts = points(core, step=0.04)
    up = band == "asc"
    ey = max(p[1] for p in pts) if up else min(p[1] for p in pts)
    x0, _, x1, _ = bbox(core)
    a = min((p for p in pts if abs(p[1] - ey) < 0.03), key=lambda p: abs(p[0] - (x0 + x1) / 2))
    k = kind if kind in ("s", "m", "b") else "b"
    return core + [dict(stroke([a, (a[0], LINES["ascender"] if up else LINES["descender"])]), k=k)]
# which sound a derived letter is built from (mirror twins and marked letters follow related sounds)
PARENT = {
    "b": "p", "d": "t", "g": "k", "z": "s", "v": "f", "ʒ": "ʃ", "dʒ": "tʃ", "ð": "θ", "ɣ": "x", "pʰ": "p", "tʰ": "t",
    "kʰ": "k", "ŋ": "n", "ɲ": "n", "ts": "t", "ʃ": "s", "ʔ": "h", "x": "h", "q": "k", "θ": "t", "tʃ": "t",
    "y": "i", "ø": "e", "ɛ": "e", "ɔ": "o", "æ": "a", "ə": "a", "ɑ": "a", "ɪ": "i", "ʊ": "u",
}
# the feature a derived sound adds to its parent: letters with the same feature share one mark (or modifier) in a script
FEATURE = {**{k: "voiced" for k in "b d g z v ʒ dʒ ð ɣ".split()}, **{k: "aspirated" for k in "pʰ tʰ kʰ".split()},
           **{k: "rounded" for k in "y ø".split()}, **{k: "open" for k in "ɛ ɔ æ".split()}, **{k: "lax" for k in "ə ɑ ɪ ʊ".split()}}
_SAFE_OPS = ("underline", "overline", "bar_h", "bar_lo", "cross", "slash", "tail", "x_in")       # modifiers that fit any base
_WIDTH_FACTOR = {"stem": 0.55, "diag": 0.85, "bar": 0.9, "hook": 0.8, "tail": 0.85, "corner": 0.85, "V": 0.95}


def _band(rng, spec):
    r = rng.random()
    if r < spec["descender_share"]:
        return "desc", (LINES["descender"], 1.0)
    if r < spec["descender_share"] + spec["ascender_share"] and spec["topline"] == "none":
        return "asc", (0.0, LINES["ascender"])
    return "x", (0.0, 1.0)


def _reach(strokes, y, tol=0.02):
    """Link the strokes to the horizontal line at height y with a vertical stroke when they stop short of it."""
    pts = points(strokes, step=0.04) or [tuple(s["p"][0]) for s in strokes]
    p = min(pts, key=lambda q: abs(q[1] - y))
    if abs(p[1] - y) > tol:
        return strokes + [stroke([(p[0], p[1]), (p[0], y)])]
    return strokes


def _dress(strokes, w, spec, kind="m"):
    """Add the script-level devices: topline bar, baseline join stubs (marked with the side they are on, so a letter
    that does not join on one side can drop them later)."""
    out = list(strokes)
    base = len(out)
    if spec["topline"] == "bar":
        out = _reach(out, 1.0) + [stroke([(0, 1.0), (w, 1.0)])]
    if spec["joining"] in ("baseline", "partial"):
        pts = points(strokes, step=0.04)
        near = ([p for p in pts if abs(p[1]) <= 0.03] or [p for p in pts if abs(p[1]) <= 0.12]
                or [min(pts, key=lambda q: abs(q[1]))])       # real contacts with the baseline first, so no short drop stubs
        lx, rx = min(p[0] for p in near), max(p[0] for p in near)
        lp, rp = min(near, key=lambda p: p[0]), max(near, key=lambda p: p[0])
        for p, side in ((lp, "L"), (rp, "R")):
            if abs(p[1]) > 0.02:
                out.append(dict(stroke([(p[0], p[1]), (p[0], 0.0)]), stub=side))
        if lx > 0.02:
            out.append(dict(stroke([(0, 0.0), (lx, 0.0)]), stub="L"))
        if rx < w - 0.02:
            out.append(dict(stroke([(rx, 0.0), (w, 0.0)]), stub="R"))
    return pin_junctions(out[:base] + _tag(out[base:], kind))


def _apply_joins(strokes, joins, direction):
    """Drop the stubs on the sides where this letter does not join (joins: both | prev | none)."""
    prev_side = "L" if direction == "ltr" else "R"
    keep = {"both": {"L", "R"}, "prev": {prev_side}, "none": set()}[joins]
    return [s for s in strokes if "stub" not in s or s["stub"] in keep]


def _fit(body, w, y0, y1):
    """Stretch a body so its ink fills the band exactly (letters fill their band, as in real scripts). A body with
    no height to speak of (a lone horizontal bar) is rejected; a stem with no width is centred."""
    bx0, by0, bx1, by1 = bbox(body)
    if by1 - by0 < 0.4:
        return None
    if bx1 - bx0 < 0.3:
        return transform(body, lambda x: w / 2 + (x - (bx0 + bx1) / 2), lambda y: y0 + (y - by0) * (y1 - y0) / (by1 - by0))
    return place(body, (0, y0, w, y1), (bx0, by0, bx1, by1))


def _fits(cand_pts, pool, d, skip=()):
    for gid, pts in pool:
        if gid in skip:
            continue
        if distance(cand_pts, pts) < d:
            return False
    return True


def _mind(cand_pts, pool, floor=0.0):
    """Distance to the nearest pooled letter; stops early once it is known to be below `floor`. The exact distance is only
    worked out for a letter that could lower the running minimum (a cheap yes/no test settles the rest)."""
    m = 9.0
    for _, pts in pool:
        if far_enough(cand_pts, pts, max(floor, m)):       # at least as far as the running minimum: it cannot change it
            continue
        m = min(m, distance(cand_pts, pts))
        if m < floor:
            break
    return m


def _make_glyph(rng, spec, pool, weights=None, tries=450, d_scale=1.0, group=None):
    """One new base letter, distinct from everything in the pool. If the space is crowded the threshold relaxes and
    the shapes get more complex; if nothing passes, the most distinct candidate seen is used."""
    base_d = spec["min_distance"] * d_scale
    exempt = rng.random() < 0.12
    band, _ = _band(rng, spec)         # decided once, so crowding cannot bias letters toward tall bands
    y0, y1 = 0.0, 1.0                  # the body always fills the main frame; ascenders and descenders are added to it
    best, best_score = None, -1.0
    for attempt in range(tries):
        frac = attempt / tries
        d = base_d * (1.0 if frac < 0.4 else 0.85 if frac < 0.7 else 0.7)
        density = min(1.0, spec["density"] * (1.15 - spec["complexity"]) + (0.5 if frac > 0.75 else 0.25 if frac > 0.5 else 0.0))
        body, fam, kind = make_styled_body(rng, density, spec["loops"], _family_weights(group, spec["loops"]) if group else weights, spec["corner_style"])
        w = max(0.3, spec["width"] * rng.uniform(0.9, 1.1) * (0.6 if fam in ("stem", "bar") and rng.random() < 0.5 else 1.0))
        body = simplify(body, spec["complexity"]) if spec["complexity"] >= 0.5 else body
        core = _fit(body, w, y0, y1)
        if core is None:
            continue
        if spec["corner_style"] == "mixed":                          # angles change when a body is stretched: classify again
            core, kind = style_strokes(rng, core, "mixed")
        # most letters sit in the standard frame with their weight near its middle; a few are allowed to be lopsided
        if not exempt and _balance(core, w, y0, y1) > spec["frame_tolerance"] * (1.0 if frac < 0.6 else 1.6 if frac < 0.85 else 9.0):
            continue
        core = _extend(core, band, kind)
        if _too_repetitive(core) or not _one_diagonal(core) or _uneven_repeats(core):
            continue
        if _count(core) > _budget(spec, frac) or _count(core) < _floor(spec, frac):
            continue
        if spec["topline"] == "bar":
            core = _reach(core, 1.0)
        pts = _npts(_dress(core, w, spec, kind), w)     # what the reader sees, including the topline
        if not pool or all(far_enough(pts, p, d) for _, p in pool):
            best, best_score = (core, w, fam, band, pts, kind), 9.0
            break
        if best is None or frac > 0.6:                    # only track the best fallback once the space looks crowded
            score = _mind(pts, pool, max(best_score, 0.0) if best else 0.0)
            if score > best_score:
                best, best_score = (core, w, fam, band, pts, kind), score
    if best is None:
        return _make_glyph(rng, spec, pool, None, tries, d_scale, None)
    core, w, fam, band, pts, kind = best
    return {"strokes": _dress(core, w, spec, kind), "width": round(w, 3), "family": fam, "band": band, "_pts": pts,
            "_core": core, "kind": kind}


def _reversals(p):
    """How often a stroke turns back on itself along its busier axis: a triangle or bump repeated three times has five."""
    best = 0
    for ax in (0, 1):
        d = [p[i + 1][ax] - p[i][ax] for i in range(len(p) - 1)]
        d = [x for x in d if abs(x) > 0.02]
        best = max(best, sum(1 for a, b in zip(d, d[1:]) if a * b < 0))
    return best


def _too_repetitive(core):
    """Base letters repeat a peak, bump or wave at most twice (circles aside): three is too much to write and to read."""
    return any(_reversals(st["p"]) >= 5 for st in core if not st.get("dot") and len(st["p"]) > 4)


def _diagonal_angles(core):
    """Distinct diagonal directions (folded left/right, in degrees) among the sharp or blocky lines of a letter."""
    found = []
    for st in core:
        if st.get("dot") or st.get("k", "m") == "m":
            continue
        for a, b in zip(st["p"], st["p"][1:] + (st["p"][:1] if st.get("closed") else [])):
            dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
            if math.hypot(dx, dy) < 0.08:
                continue
            ang = math.degrees(math.atan2(dy, dx))
            if 8 < ang < 82 and not any(abs(ang - f) <= 10 for f in found):
                found.append(ang)
    return found


def _one_diagonal(core):
    """Sharp letters use one diagonal direction (mirrored sides count as one); several slants, or a curve made of many
    differently angled corners, look like a drawing error."""
    return len(_diagonal_angles(core)) <= 1


def _line_class(op):
    for cls in (BAR_OPS, {"slash", "tail", "x_in"}):
        if op in cls:
            return id(cls) if cls is BAR_OPS else "diag"
    return None


def _look_alike_ops(a, b):
    """Two modifiers of one figure that differ only inside one family (a bar at another height, another diagonal) leave the
    letters topologically the same, so one of them may not be used once the other is taken."""
    pa, pb = set(a.split("+")), set(b.split("+"))
    da, db = pa - pb, pb - pa
    if not da or not db:
        return False
    classes = {_line_class(o) for o in da | db}
    return len(classes) == 1 and None not in classes and (pa & set(XFORMS)) == (pb & set(XFORMS))


def _clear_part(core, slot, part):
    """A diacritic placed so it stays visible: clear of the letter's own lines (a dot that overlaps a stroke disappears into
    it). Parts that are meant to touch the letter are left as placed. Floating parts slide away from the letter until clear;
    None if there is no room."""
    out = place_part(core, slot, part)
    if part["touch"] or slot in ("left", "right"):
        return out
    base = points(core, step=0.04)
    sign = 1 if slot == "above" else -1
    for k in range(0, 9):
        cand = shift(out, 0, sign * 0.05 * k)
        mine = points(cand, step=0.04) or [tuple(s["p"][0]) for s in cand]
        if all(math.hypot(a[0] - b[0], a[1] - b[1]) >= 0.1 for a in mine for b in base):
            return cand
    return None


def _uneven_repeats(core):
    """Repeated parts of a letter are the same size: two similar closed shapes (or similar open ones) whose sizes differ
    by a little look like a drawing error. Nested shapes of very different size (a ring in a ring) are fine."""
    body = [s for s in core if not s.get("dot") and len(s["p"]) >= 3]
    for i, a in enumerate(body):
        for b in body[i + 1:]:
            if bool(a.get("closed")) != bool(b.get("closed")) or len(a["p"]) != len(b["p"]):
                continue
            A, B = bbox([a]), bbox([b])
            sa, sb = (A[2] - A[0]) * (A[3] - A[1]), (B[2] - B[0]) * (B[3] - B[1])
            if sa > 1e-6 and sb > 1e-6 and 0.5 < min(sa, sb) / max(sa, sb) < 0.97:
                return True
    return False


def _balance(core, w, y0, y1):
    """How far the ink's centre of gravity sits from the middle of the letter frame (0 = centred, in frame units)."""
    pts = [p for p in points(core, step=0.05) if y0 - 0.02 <= p[1] <= y1 + 0.02]      # ascender and descender strokes do not count
    if not pts:
        return 0.0
    cx = sum(p[0] for p in pts) / len(pts) / (w or 1)
    cy = (sum(p[1] for p in pts) / len(pts) - y0) / ((y1 - y0) or 1)
    return max(abs(cx - 0.5), abs(cy - 0.5))


def _make_motif_glyph(rng, spec, pool, shape, used, kin=(), group=None, lib=None, relax=1.0):
    """A letter built from a characteristic shape plus one variant nobody else using that shape has taken. The shape sits
    in the main frame at its natural proportions; variants that add a stem reach the ascender or descender line.
    Letters of one sound group prefer the same variants (rule D)."""
    ortho = spec["corner_style"] == "blocky"
    table = lib["table"]
    c = spec["complexity"]
    singles = [o for o in ["plain"] + lib["mods"] + lib["xforms"] if o not in used and op_allowed(o, c)]
    rng.shuffle(singles)
    pref = lib["place_ops"].get(group, [])
    singles.sort(key=lambda o: (0 if o in pref else 1))
    pairs = [f"{a}+{b}" for i, a in enumerate(lib["mods"]) for b in lib["mods"][i + 1:]]
    pairs += [f"{x}+{m}" for x in lib["xforms"] for m in lib["mods"]]
    rng.shuffle(pairs)
    pairs = [p for p in pairs if p not in used and op_allowed(p, c)][:30]
    ops = singles + pairs
    d = spec["min_distance"] * 0.7 * relax
    for op in ops:
        if any(_look_alike_ops(op, u) for u in used):
            continue
        if spec["topline"] == "bar" and "overline" in op.split("+"):      # a line along the top vanishes into the topline
            continue
        vert = vertical_of(op)
        if vert in ("asc", "both") and (spec["topline"] == "bar" or spec["ascender_share"] < 0.02):
            continue
        if vert in ("desc", "both") and spec["descender_share"] < 0.02:
            continue
        if vert:                                        # the ascender/descender shares are rates, not just gates
            vs = lib["vstate"]
            if vs["vert"] >= (spec["ascender_share"] + spec["descender_share"]) * (vs["made"] + 1) + 0.5:
                continue
        base_shape = table[shape]()
        if spec["complexity"] >= 0.5:                       # simplify the figure itself, before the variant adds its stem
            base_shape = simplify(base_shape, spec["complexity"])
        v = apply_variant(base_shape, op, ortho)
        if not v or not usable(v, ortho):
            continue
        band = {"asc": "asc", "desc": "desc", "both": "asc+desc"}[vert] if vert else _band(rng, spec)[0]
        cw = max(0.4, spec["width"] * (rng.uniform(0.9, 1.05)))
        body, kind = style_strokes(rng, v, spec["corner_style"])
        placed = transform(body, lambda x: x * cw, lambda y: y)        # unit shape -> main frame, extras beyond it
        x0 = min(bbox(placed)[0], 0.0)
        core = shift(placed, -x0, 0)
        w = max(bbox(core)[2], cw)
        if spec["corner_style"] == "mixed":
            core, kind = style_strokes(rng, core, "mixed")
        if _balance(core, w, 0.0, 1.0) > spec["frame_tolerance"] * 1.5:
            continue
        if not vert:
            core = _extend(core, band, kind)
        if _count(core) > _budget(spec, 0.6) or (_count(core) < _floor(spec, 0.4) and shape not in lib.get("pinned", ())):      # a shape the user chose may be plainer than the style
            continue
        if spec["topline"] == "bar":
            core = _reach(core, 1.0)
        dressed = _dress(core, w, spec, kind)
        if _too_repetitive(core) or not _one_diagonal(core) or _uneven_repeats(core):
            continue
        if analyse(dressed)["parts"] != 1:                  # a variant can leave a stem or hook floating free
            continue
        pts = _npts(dressed, w)
        # relatives (same shape) may look alike -- that is the point -- but others must stay clearly apart
        if pool and not all(far_enough(pts, p, d * (0.8 if gid in kin else 1.0)) for gid, p in pool):
            continue
        lib["vstate"]["made"] += 1
        lib["vstate"]["vert"] += 1 if vert else 0
        return {"strokes": _dress(core, w, spec, kind), "width": round(w, 3), "family": f"motif:{shape}", "band": band,
                "_pts": pts, "_core": core, "kind": kind, "motif": shape, "variant": op}, op
    return None, None


def _make_kana_glyph(rng, spec, pool, group, owned, tries=160):
    """A letter of the stroke family (kana.py): its own arrangement of a few short strokes, drawn from one of the
    archetypes its sound class owns (family resemblance among related sounds), else from any. The pieces may be separate;
    they must read as one letter. Distinct from everything in the pool; the threshold relaxes if the alphabet is crowded."""
    hand = spec["stroke_hand"]
    kind = "s" if hand == "angular" or (hand == "pen" and spec["corner_style"] in ("sharp", "blocky")) else "m"
    names = kana.archetypes(hand, spec.get("pen_frame", "both"))
    wts = kana.weights(hand, spec["complexity"], spec["loops"])
    best, best_score = None, -1.0
    for attempt in range(tries):
        frac = attempt / tries
        d = spec["min_distance"] * (1.0 if frac < 0.4 else 0.8 if frac < 0.7 else 0.6)
        name = rng.choice(owned) if owned and rng.random() < (0.7 if frac < 0.5 else 0.3) else rng.choices(names, [wts[n] for n in names])[0]
        _, st = kana.make(rng, hand, name, extra=spec["stroke_ticks"], cross=spec["stroke_crossings"], join=spec["stroke_joins"], style=spec["corner_style"])
        fh, fw = kana.FILL.get(hand, (0.78, 0.55))
        if not kana.fills(st, fh if frac < 0.6 else fh * 0.77, fw if frac < 0.6 else fw * 0.73):
            continue
        if len([x for x in st if not x.get("dot")]) > _budget(spec, frac):
            continue
        w = max(0.35, spec["width"] * rng.uniform(0.9, 1.1))
        core = [dict(x, k=x.get("k", kind)) for x in transform(st, lambda x: x * w, lambda y: y)]
        if not kana.reads_as_one(core):
            continue
        pts = _npts(core, w)
        if not pool or all(far_enough(pts, p, d) for _, p in pool):
            best, best_score = (core, w, name, pts), 9.0
            break
        score = _mind(pts, pool, max(best_score, 0.0) if best else 0.0)
        if score > best_score:
            best, best_score = (core, w, name, pts), score
    core, w, name, pts = best
    lo, hi = bbox(core)[1], bbox(core)[3]
    band = "asc+desc" if lo < -0.12 and hi > 1.12 else "desc" if lo < -0.12 else "asc" if hi > 1.12 else "x"
    return {"strokes": _dress(core, w, spec, kind), "width": round(w, 3), "family": f"stroke:{name}", "band": band, "_pts": pts,
            "_core": core, "kind": kind, "arch": name}


def _glyph_of(core, w, spec, fam, band, relation=None, parent=None, mark=None, kind="m"):
    return {"kind": kind, "strokes": _dress(core, w, spec, kind), "width": round(w, 3), "family": fam, "band": band,
            "relation": relation, "from": parent, "mark": mark, "_pts": _npts(_dress(core, w, spec, kind), w), "_core": core}


def _turn(core, w, how):
    """A letter body turned or mirrored inside its frame (width w, height 1): any letter can be derived from another this way."""
    if how == "flip_x":
        return transform(core, lambda x: w - x, lambda y: y)
    if how == "flip_y":
        return transform(core, lambda x: x, lambda y: 1.0 - y)
    if how == "rot180":
        return transform(core, lambda x: w - x, lambda y: 1.0 - y)
    out = []
    for s in core:                                           # quarter turns: (u, v) -> (1 - v, u) or (v, 1 - u) in frame units
        t = dict(s)
        t["p"] = [[round((1 - y) * w, 4), round(x / w, 4)] if how == "rot90" else [round(y * w, 4), round(1 - x / w, 4)]
                  for x, y in s["p"]]
        if t.get("k") == "b" and not t.get("dot") and len(t["p"]) > 2:         # stretching can spoil a right angle: soften it
            from .motifs import classify
            c = classify([t])
            if c["angular"] or c["gentle"]:
                t["k"] = "m"
        out.append(t)
    return out


def _derive_transform(rng, g, spec, tried):
    """Candidate (core, relation) twins of a letter by mirror or turn, in random order, skipping ones already used on it.
    Letters with an ascender or descender only mirror left to right, so their stems stay on the right lines."""
    hows = ["flip_x", "flip_y", "rot90", "rot270", "rot180"] if g["band"] == "x" else ["flip_x"]
    if spec["topline"] == "bar" or spec["joining"] != "none":
        hows = ["flip_x"] if g["band"] == "x" else []
    rng.shuffle(hows)
    return [(_turn(g["_core"], g["width"], h), h) for h in hows if h not in tried]


def _symmetric(g, other_core, w, spec):
    return distance(g["_pts"], _npts(other_core, g["width"])) < spec["min_distance"] * 0.5


def generate(seed: int, pins: dict | None = None, phonemes: dict | None = None) -> dict:
    spec = resolve(seed, pins)
    cons = list((phonemes or {}).get("consonants") or DEFAULT_CONSONANTS[:spec["consonants"]])
    vows = list((phonemes or {}).get("vowels") or DEFAULT_VOWELS[:spec["vowels"]])
    if phonemes:
        spec["consonants"], spec["vowels"] = len(cons), len(vows)
    kind = spec["kind"]
    sign_vowels = kind == "abugida" or (kind == "abjad" and vows)
    letter_ids = cons + ([] if sign_vowels else vows)
    n = len(letter_ids)

    # which letters are derived from another letter
    mrng = rng_for(spec["seed"], "script", "derive")
    derivable = [i for i in letter_ids if PARENT.get(i) in letter_ids and PARENT[i] != i]
    mrng.shuffle(derivable)
    n_mirror = min(len(derivable), round(spec["mirror_share"] * n))
    n_mark = min(len(derivable) - n_mirror, round(spec["mark_share"] * n))
    mirror_ids = derivable[:n_mirror]
    rest = derivable[n_mirror:]
    by_feat: dict[str, list] = {}
    for i in rest:                                   # one feature (voicing, aspiration...) is marked on all its letters, or on none
        by_feat.setdefault(FEATURE.get(i) or f"x:{i}", []).append(i)
    feats = list(by_feat)
    mrng.shuffle(feats)
    if spec["mark_shape"] == "voicing" and "voiced" in feats:      # kana-style marks: voicing is the one marked feature that is always there
        feats.remove("voiced")
        feats.insert(0, "voiced")
    mark_ids = []
    for f in feats:
        if len(mark_ids) >= n_mark:
            break
        mark_ids += by_feat[f]
    # a parent must itself be an original letter
    derived = set(mirror_ids) | set(mark_ids)
    mirror_ids = [i for i in mirror_ids if PARENT[i] not in derived]
    mark_ids = [i for i in mark_ids if PARENT[i] not in derived]
    derived = set(mirror_ids) | set(mark_ids)

    glyphs: dict[str, dict] = {}
    pool: list = []
    lrng = rng_for(spec["seed"], "script", "letters")
    vowel_w = {"ring": 2.0, "C": 1.6, "U": 1.3, "hook": 0.5, "stem": 0.7}
    # characteristic shapes: one per sound class (labials, coronals, dorsals, vowels...), reused with variants
    mrng2 = rng_for(spec["seed"], "script", "motifs")
    c = spec["complexity"]
    fams = [spec["family"]] + ([spec["family2"]] if spec["family2"] != "none" else [])
    table, levels, by_family = {}, {}, {}
    for fam in fams:
        for n, (build, win) in FORMS[fam].items():
            table[f"{fam}.{n}"], levels[f"{fam}.{n}"] = build, win
            by_family.setdefault(fam, []).append(f"{fam}.{n}")
    pools = {fam: eligible({k: table[k] for k in names}, c, "mixed", levels) for fam, names in by_family.items()}
    for fam in fams:
        pools.setdefault(fam, [])          # the stroke family has no figure table
    for fam in pools:
        mrng2.shuffle(pools[fam])
    fit = {}
    brng = rng_for(spec["seed"], "script", "bias")          # lean on figures made of the wanted lines and holding (or avoiding) loops; a little noise keeps variety
    fit = {k: (bias.score(table[k](), spec["stroke_bias"]) if spec["stroke_bias"] != "balanced" else 0.0) + brng.uniform(0, 0.2) for k in table}
    for k in table:
        if analyse(table[k]())["loops"]:
            fit[k] += (spec["loops"] - 0.4) * 1.5
    for fam in pools:
        pools[fam].sort(key=lambda k: -fit[k])
    primary = pools[fams[0]]
    secondary = pools[fams[1]] if len(fams) > 1 else pools[fams[0]]
    # modifiers: a subset of the families' lines, shared by the whole script
    krng = rng_for(spec["seed"], "script", "modifiers")
    union = []
    for fam in fams:
        union += [m for m in MODS[fam] if m not in union]
    union = [m for m in union if op_allowed(m, c)]
    krng.shuffle(union)
    mods = union[:max(5, min(len(union), krng.randint(6, 9)))]
    place_ops = {cl: mods[i::7] or mods[:1] for i, cl in enumerate(CLASS_ORDER)}
    xforms = [x for x in XFORMS if op_allowed(x, c)]
    krng.shuffle(xforms)
    xforms = xforms[:krng.randint(3, 5)]          # which turns and mirrorings this script uses on figures
    lib = {"table": table, "mods": mods, "xforms": xforms, "place_ops": place_ops, "vstate": {"made": 0, "vert": 0}}
    n_motifs = min(max(spec["motif_count"], 4) if spec["motif_count"] else 0, len(primary) - 1) if spec["family"] != "stroke" else 0   # a shape for each consonant manner
    group_shape = {}
    if n_motifs:                   # one shape per manner of articulation; vowels get one no consonant uses (rule D)
        cons_shapes = primary[:n_motifs]
        for i, grp in enumerate(["plosive", "fricative", "nasal", "approximant"]):
            group_shape[grp] = cons_shapes[i % n_motifs]
        if len(fams) > 1 and len(secondary) > 1:        # a second family gives the script its blend: vowels and one manner
            group_shape["approximant"] = secondary[1]
        group_shape["affricate"] = group_shape["plosive"]
        vcands = [n for n in secondary if n not in group_shape.values()] or [n for n in primary if n not in group_shape.values()]
        group_shape["vowel"] = vcands[0] if vcands else primary[-1]
    pinned = shape_forms.chosen(spec)
    for grp, name in pinned.items():       # shapes the user chose: used whatever the complexity or families
        k = shape_forms.key(name)
        table.setdefault(k, shape_forms.builder(name))
        group_shape[grp] = k
        if grp == "plosive":
            group_shape["affricate"] = k
    lib["pinned"] = {group_shape[g] for g in pinned}
    # stroke-family letters (kana.py): each sound class owns a few archetypes, so related sounds look related
    # which letters are stroke letters: the share the stroke_share dial asks for, taken sound class by sound class (vowels first,
    # then approximants, nasals, fricatives, stops), a partly used class at random; a class whose shape the user chose is left out
    kana_letters: set = set()
    if kana.HANDS.count(spec["stroke_hand"]) and (spec["family"] == "stroke" or spec["stroke_share"] > 0):
        want = len(letter_ids) if spec["family"] == "stroke" else round(spec["stroke_share"] * len(letter_ids))
        srng = rng_for(spec["seed"], "script", "strokeshare")
        for grp in ("vowel", "approximant", "nasal", "fricative", "plosive", "affricate", None):
            if len(kana_letters) >= want or (grp in pinned and spec["family"] != "stroke"):
                continue
            members = [i for i in letter_ids if GROUP_OF.get(i) == grp and GROUP_OF.get(i) not in pinned]
            srng.shuffle(members)
            kana_letters.update(members[:max(0, want - len(kana_letters))])
    arng = rng_for(spec["seed"], "script", "kana")
    arch = kana.archetypes(spec["stroke_hand"], spec.get("pen_frame", "both")) if spec["stroke_hand"] in kana.HANDS else []
    if arch:           # a weighted shuffle: busier archetypes first in ornate scripts, plainer first in bold ones
        wt = kana.weights(spec["stroke_hand"], spec["complexity"], spec["loops"])
        arch.sort(key=lambda n: -(arng.random() ** (1.0 / wt[n])))
    else:
        arng.shuffle(arch)
    owned = {g: arch[i * 3:i * 3 + 3] or arch[:3] for i, g in enumerate(GROUP_ORDER)}
    owned["affricate"] = owned["plosive"]

    def _kana(lid, pool_):
        return _make_kana_glyph(lrng, spec, pool_, GROUP_OF.get(lid), owned.get(GROUP_OF.get(lid), []))
    used_ops: dict[str, set] = {}

    def _new_letter(lid, pool_=None, own=True):
        """An independent letter for a sound: a figure of the script's families wearing its group's shape if one fits,
        else any figure, else (last resort) a plain generated body."""
        grp, cls = GROUP_OF.get(lid), CLASS_OF.get(lid)
        pl = pool if pool_ is None else pool_
        if lid in kana_letters:
            g = _kana(lid, pl)
            g.update(relation=None, **{"from": None, "mark": None, "role": "vowel" if lid in vows else "consonant"})
            return g
        tries = ([group_shape[grp]] if own and grp in group_shape else []) + (sorted(mrng2.sample(sorted(table), min(16, len(table))), key=lambda k: -fit.get(k, 0)) if group_shape else [])
        g = None
        for k, shp in enumerate(tries):
            kin_ = {key for key, v in glyphs.items() if v.get("motif") == shp} if (k == 0 and own) else ()
            for relax in (((1.0, 0.8, 0.65, 0.5, 0.35) if grp in pinned else (1.0, 0.8, 0.65)) if k == 0 and own else (1.0, 0.75, 0.55)):      # keep the group's shape if it can be made to fit
                g, op = _make_motif_glyph(mrng2, spec, pl, shp, used_ops.setdefault(shp, set()), kin_, cls, lib, relax)
                if g:
                    fine = _npts(g["strokes"], g["width"], 0.05)       # the coarse check can miss near-twins (a bar on a figure that has one)
                    if any(distance(fine, _npts(v["strokes"], v["width"], 0.05)) < 0.06 for v in glyphs.values()):
                        used_ops[shp].add(op)
                        g = None
                        continue
                    used_ops[shp].add(op)
                    break
            if g:
                break
        if g is None:
            g = _make_glyph(lrng, spec, pl, vowel_w if lid in vows else None, group=grp)
        g.update(relation=None, **{"from": None, "mark": None, "role": "vowel" if lid in vows else "consonant"})
        return g
    for lid in letter_ids:
        if lid in derived:
            continue
        isv = lid in vows
        if lid in kana_letters:
            g = _kana(lid, pool)
        elif group_shape:
            g = _new_letter(lid, own=mrng2.random() < spec["motif_share"])
        else:
            g = _make_glyph(lrng, spec, pool, vowel_w if isv else None, group=GROUP_OF.get(lid))
        g.update(relation=None, **{"from": None, "mark": None, "role": "vowel" if isv else "consonant"})
        glyphs[lid] = g
        pool.append((lid, g["_pts"]))

    # turned and mirrored twins of related letters: up to three per parent (a lower distance threshold applies to the pair)
    mirrored: dict[str, set] = {}
    for lid in mirror_ids:
        par = glyphs[PARENT[lid]]
        tried = mirrored.setdefault(PARENT[lid], set())
        g = None
        if len(tried) < 3:
            for core, rel in _derive_transform(lrng, par, spec, tried):
                pts = _npts(core, par["width"])
                if distance(pts, par["_pts"]) < spec["min_distance"] * 0.5 or not _fits(pts, pool, spec["min_distance"] * 0.7, (PARENT[lid],)):
                    continue
                tried.add(rel)
                g = _glyph_of(core, par["width"], spec, par["family"], par["band"], rel, PARENT[lid], None, par["kind"])
                g["role"] = "vowel" if lid in vows else "consonant"
                break
        if g is None:                       # no twin was different enough: make an independent letter instead
            g = _new_letter(lid)
        glyphs[lid] = g
        pool.append((lid, g["_pts"]))

    # marked letters: the same feature always gets the same mark (a detached part in a slot) or the same line added to the
    # base (a modifier from the script's family), so "voiced" looks the same on every letter that has it
    marks = []
    feat_mark: dict[str, tuple] = {}
    if mark_ids:
        krng = rng_for(spec["seed"], "script", "marks")

        voicing_hand = spec["stroke_hand"] if spec["stroke_hand"] in ("angular", "flowing") else ("angular" if spec["corner_style"] in ("sharp", "blocky") else "flowing")
        kana_marks = kana.voicing_marks(voicing_hand) if spec["mark_shape"] == "voicing" else []           # any family can use the kana voicing marks

        def new_mark(feature=None):
            want = 0 if feature == "voiced" else 1      # kana: voicing is two ticks, the next feature a small ring, both above the letter
            if kana_marks:
                have = [m for m in marks if m["kind"] == kana_marks[want]["kind"]]
                if have:                                # every other feature shares the ring, as the p-row does
                    return have[0]
                m = dict(kana_marks[want], id=f"m{len(marks) + 1}", slot="above")
                marks.append(m)
                return m
            for _ in range(30):
                slot = krng.choice(["above", "above", "below"])
                m = dict(make_part(krng, slot, 0.15, 0.2, 0.45, spec["corner_style"], spec["mark_shape"]), id=f"m{len(marks) + 1}", slot=slot)
                if all(m["slot"] != o["slot"] or m["kind"] != o["kind"] for o in marks):
                    break
            marks.append(m)
            return m

        safe = [m for m in lib["mods"] if m in _SAFE_OPS]
        krng.shuffle(safe)
        for lid in mark_ids:
            f = FEATURE.get(lid) or f"x:{lid}"
            if f not in feat_mark:
                if f in FEATURE.values() and safe and not kana_marks and krng.random() < 0.5:
                    feat_mark[f] = ("op", safe.pop())
                else:
                    feat_mark[f] = ("part", new_mark(f))
        for lid in mark_ids:
            par = glyphs[PARENT[lid]]
            f = FEATURE.get(lid) or f"x:{lid}"
            mode, what = feat_mark[f]
            g = None
            if mode == "part":
                placed = _clear_part(par["_core"], what["slot"], what)
                if placed:
                    g = _glyph_of(par["_core"] + placed, par["width"], spec, par["family"], par["band"], "mark", PARENT[lid], what["id"], par["kind"])
            else:
                w0 = par["width"]
                unit = transform(par["_core"], lambda x: x / w0, lambda y: y)
                v = apply_variant(unit, what, spec["corner_style"] == "blocky")
                if v:
                    core = [dict(s, k=s.get("k", par["kind"])) if not s.get("dot") else s for s in transform(v, lambda x: x * w0, lambda y: y)]
                    x0 = min(bbox(core)[0], 0.0)
                    core = shift(core, -x0, 0)
                    w1 = max(w0, bbox(core)[2])
                    cand = _glyph_of(core, w1, spec, par["family"], par["band"], "modifier", PARENT[lid], f"op:{what}", par["kind"])
                    if distance(cand["_pts"], par["_pts"]) >= spec["min_distance"] * 0.4 and _fits(cand["_pts"], pool, spec["min_distance"] * 0.5, (PARENT[lid],)):
                        g = cand
            if g is None:                   # the line did not fit this base: the sound gets its own letter
                g = _new_letter(lid)
            else:
                g["role"] = "vowel" if lid in vows else "consonant"
            g["feature"] = FEATURE.get(lid)
            glyphs[lid] = g
            pool.append((lid, g["_pts"]))

    # safety net: no two unrelated letters may end up (nearly) identical, whatever path produced them
    final = {lid: _npts(glyphs[lid]["strokes"], glyphs[lid]["width"], 0.05) for lid in letter_ids}
    parents = {g.get("from") for g in glyphs.values() if g.get("from")}
    for _pass in range(4):
        changed = False
        for i, lid in enumerate(letter_ids):
            for prev in letter_ids[:i]:
                g, pg = glyphs[lid], glyphs[prev]
                if g.get("from") == prev or pg.get("from") == lid or g.get("mark") or pg.get("mark"):
                    continue
                if distance(final[lid], final[prev]) >= 0.05:
                    continue
                victim = lid if lid not in parents else (prev if prev not in parents else None)
                if victim is None:
                    continue
                pool2 = [(k, v) for k, v in final.items() if k != victim and k in glyphs]
                ng = (_kana(victim, pool2) if victim in kana_letters
                      else _make_glyph(lrng, spec, pool2, vowel_w if victim in vows else None, group=GROUP_OF.get(victim)))
                ng.update(relation=None, **{"from": None, "mark": None, "role": "vowel" if victim in vows else "consonant"})
                glyphs[victim] = ng
                final[victim] = _npts(ng["strokes"], ng["width"], 0.05)
                changed = True
                if victim == lid:
                    break
        if not changed:
            break

    # keep the declared order of the inventory
    letters = []
    jrng = rng_for(spec["seed"], "script", "joins")
    for lid in letter_ids:
        g = glyphs[lid]
        if spec["joining"] == "partial":
            g["joins"] = jrng.choices(["both", "prev", "none"], [0.55, 0.2, 0.25])[0]
        else:
            g["joins"] = "both" if spec["joining"] == "baseline" else "none"
        g["strokes"] = _apply_joins(g["strokes"], g["joins"], spec["direction"]) if spec["joining"] != "none" else g["strokes"]
        letters.append({"id": lid, "role": g["role"], "strokes": g["strokes"], "width": g["width"], "family": g["family"],
                        "band": g["band"], "relation": g.get("relation"), "from": g.get("from"), "mark": g.get("mark"),
                        "motif": g.get("motif"), "variant": g.get("variant"), "feature": g.get("feature"), "joins": g["joins"]})

    shape_classes = {}
    for c, sh in group_shape.items():
        shape_classes.setdefault(sh, []).append(c)
    script = {"version": 1, "spec": spec, "letters": letters,
              "motifs": [{"shape": sh, "classes": cs} for sh, cs in shape_classes.items()], "marks": [_public_part(m) for m in marks]}
    if pinned:       # how many letters of each chosen class actually wear the chosen shape (a shape can clash with the corner style)
        script["shape_report"] = {grp: {"shape": name, "letters": sum(1 for l in letters if GROUP_OF.get(l["id"]) == grp),
                                        "wearing": sum(1 for l in letters if GROUP_OF.get(l["id"]) == grp and l.get("motif") == group_shape[grp])}
                                  for grp, name in pinned.items()}
    if sign_vowels:
        script["signs"] = _make_signs(spec, vows, glyphs)
        if kind == "abugida":
            script["virama"] = _make_virama(spec, script["signs"])
    script["punct"] = _make_punct(spec)
    script["digits"] = _make_digits(spec, [(l["id"], _npts(l["strokes"], l["width"])) for l in letters], lib if group_shape else None)
    script["metrics"] = metrics(script)
    return script


def _public_part(p):
    return {k: v for k, v in p.items() if not k.startswith("_")}


def _ref_base():
    return [stroke([(0, 0), (0, 1), (0.8, 1), (0.8, 0)], True)]


def _sign_points(sign):
    ref = _ref_base()
    parts = []
    for slot, part in sign["parts"].items():
        parts += place_part(ref, slot, part)
    return points(ref + parts, step=STEP)


def _make_signs(spec, vows, glyphs):
    """Vowel signs for an abugida (or abjad vowel points): short signs first, the longs built from them (+LONG)."""
    srng = rng_for(spec["seed"], "script", "signs")
    n = len(vows)
    n_long = n // 3
    shorts = vows[:n - n_long]
    slot_w = {"right": 0.3, "above": 0.3, "below": 0.25, "left": 0.15}
    if spec["kind"] == "abjad":
        slot_w = {"above": 0.6, "below": 0.4}
    pairs = [("left", "right"), ("above", "right"), ("left", "above"), ("below", "right"), ("above", "below")]
    if spec["kind"] == "abjad":
        pairs = []
    if spec["vowel_sign_slot"] != "mixed":                                     # the script keeps its vowel signs to one side
        slot_w, pairs = {spec["vowel_sign_slot"]: 1.0}, []
    signs, pool = [], []
    for vid in shorts:
        sign = None
        for attempt in range(200):
            if pairs and srng.random() < spec["sign_frames"]:
                slots = list(srng.choice(pairs))
            else:
                slots = [srng.choices(list(slot_w), list(slot_w.values()))[0]]
            parts = {s: make_part(srng, s, 0.12, 0.25, 0.25, spec["corner_style"], spec["mark_shape"]) for s in slots}
            cand = {"id": vid, "slots": slots, "parts": parts, "long_of": None}
            pts = _sign_points(cand)
            if all(distance(pts, p) >= 0.13 for _, p in pool):
                sign = cand
                break
            sign = sign or cand
        signs.append(sign)
        pool.append((vid, _sign_points(sign)))
    for i, vid in enumerate(vows[n - n_long:]):
        short = signs[i]
        lg = None
        for _ in range(30):
            slot = srng.choice(short["slots"])
            part = grow_part(srng, short["parts"][slot], slot)
            if part:
                parts = dict(short["parts"])
                parts[slot] = part
                cand = {"id": vid, "slots": list(short["slots"]), "parts": parts, "long_of": short["id"]}
                if all(distance(_sign_points(cand), p) >= 0.05 for _, p in pool):
                    lg = cand
                    break
        if lg is None:                      # could not extend the sign: give the long vowel an independent sign
            lg = {"id": vid, "slots": list(short["slots"]), "long_of": None,
                  "parts": {s: make_part(srng, s, 0.12, 0.25, 0.25, spec["corner_style"], spec["mark_shape"]) for s in short["slots"]}}
        signs.append(lg)
        pool.append((vid, _sign_points(lg)))
    return [_public_sign(s) for s in signs]


def _public_sign(s):
    return {"id": s["id"], "slots": s["slots"], "long_of": s["long_of"],
            "parts": {k: _public_part(v) for k, v in s["parts"].items()}}


def _make_virama(spec, signs):
    vrng = rng_for(spec["seed"], "script", "virama")
    used = [(s["id"], _sign_points(s)) for s in signs]
    best = None
    for _ in range(60):
        slot = vrng.choice(["below", "below", "above", "right"])
        part = make_part(vrng, slot, 0.0, 0.0, 0.5, spec["corner_style"], spec["mark_shape"])
        cand = {"id": "virama", "slots": [slot], "parts": {slot: part}, "long_of": None}
        pts = _sign_points(cand)
        best = best or cand
        if all(distance(pts, p) >= 0.13 for _, p in used):
            best = cand
            break
    return _public_sign(best)


def _make_punct(spec):
    prng = rng_for(spec["seed"], "script", "punct")
    stop = prng.choice(["dot", "ring", "bar"])
    out = {}
    out["stop"] = {"dot": [dot(0.1, 0.1, 0.09)], "ring": [stroke([(0.1, 0), (0.2, 0.1), (0.1, 0.2), (0, 0.1)], True)],
                   "bar": [stroke([(0.1, 0), (0.1, 1.0)])]}[stop]
    out["comma"] = [stroke([(0.15, 0.1), (0.05, -0.2)])]
    q = prng.choice(["hook", "curl"])
    out["question"] = ([stroke([(0, 0.9), (0.15, 1.0), (0.3, 0.9), (0.15, 0.5), (0.15, 0.3)]), dot(0.15, 0.05, 0.07)]
                       if q == "hook" else [stroke([(0.3, 1.0), (0, 0.7), (0.3, 0.4), (0.3, 0.2)]), dot(0.3, 0.0, 0.07)])
    out["separator"] = [dot(0.08, 0.5, 0.07)]
    ck = "m" if spec["corner_style"] == "smooth" else "b"
    return {k: {"strokes": _tag(v, ck), "width": round(max(bbox(v)[2], 0.2) + 0.1, 3)} for k, v in out.items()}


def _make_digits(spec, letter_pts=(), lib=None):
    drng = rng_for(spec["seed"], "script", "digits")
    dspec = dict(spec, topline="none", joining="none", ascender_share=0.0, descender_share=0.0, min_distance=0.2)
    pool, out = list(letter_pts), []
    used: dict[str, set] = {}
    for i in range(10):
        g = None
        if lib:                         # digits wear the script's own figures, so they match its style family
            for shp in drng.sample(sorted(lib["table"]), min(16, len(lib["table"]))):
                for relax in (1.0, 0.75, 0.55):
                    g, op = _make_motif_glyph(drng, dspec, pool, shp, used.setdefault(shp, set()), (), None, lib, relax)
                    if g:
                        used[shp].add(op)
                        break
                if g:
                    break
        if g is None and spec["family"] == "stroke":
            g = _make_kana_glyph(drng, dspec, pool, None, [])
        if g is None:
            g = _make_glyph(drng, dspec, pool, tries=150)
        pool.append((i, g["_pts"]))
        out.append({"id": str(i), "strokes": g["strokes"], "width": g["width"], "motif": g.get("motif"), "variant": g.get("variant")})
    return out


def metrics(script: dict) -> dict:
    """Shape statistics for comparing against the reference scripts (median ends/junctions/loops, share with marks...)."""
    ends, juncs, loops, detached = [], [], [], 0
    letters = script["letters"]
    for l in letters:
        a = analyse(l["strokes"])
        ends.append(a["ends"])
        juncs.append(len(a["junctions"]))
        loops.append(a["loops"])
        if a["parts"] > 1:
            detached += 1
    pts = [(l["id"], _npts(l["strokes"], l["width"])) for l in letters]
    related = {frozenset((l["id"], l["from"])) for l in letters if l["from"]}     # declared pairs are allowed to be close
    kin = [l for l in letters if l["from"]]
    related |= {frozenset((a["id"], b["id"])) for a in kin for b in kin if a["from"] == b["from"] and a is not b}
    nn = []
    for i, (a, p) in enumerate(pts):
        nn.append(min((distance(p, q) for j, (b, q) in enumerate(pts) if j != i and frozenset((a, b)) not in related), default=9.0))
    med = lambda v: sorted(v)[len(v) // 2] if v else 0
    nn.sort()
    return {"sound_coherence": coherence(letters, pts, related), "letters": len(letters), "median_ends": med(ends), "median_junctions": med(juncs), "median_loops": med(loops),
            "share_loops": round(sum(1 for v in loops if v) / max(1, len(loops)), 2),
            "share_detached": round(detached / max(1, len(letters)), 2),
            "nn_distance_p10": round(nn[int(0.1 * len(nn))], 3) if nn else None}


def coherence(letters, pts, related):
    """Rule D, measured. Mean shape distance between letters of the same sound group against letters of different groups
    (vowels against consonants; among consonants, one manner against another), plus how often a letter's most similar
    unrelated letter belongs to its own group. Related pairs are left out."""
    grp = {l["id"]: GROUP_OF.get(l["id"]) for l in letters}
    items = [(a, p) for a, p in pts if grp[a]]
    dist = {}
    for i, (a, p) in enumerate(items):
        for b, q in items[i + 1:]:
            if frozenset((a, b)) not in related:
                dist[(a, b)] = dist[(b, a)] = mean_distance(p, q)

    def mean(sel):
        v = [d for (a, b), d in dist.items() if a < b and sel(grp[a], grp[b])]
        return round(sum(v) / len(v), 3) if v else None

    def agree(same):
        hit = tot = 0
        for a, _ in items:
            others = [(d, b) for (x, b), d in dist.items() if x == a and same(grp[a], grp[b], True)]
            pool = [(d, b) for (x, b), d in dist.items() if x == a]
            if len(others) and pool:
                tot += 1
                hit += min(pool)[1] in {b for _, b in others}
        return round(hit / tot, 2) if tot else None

    v = lambda x: x == "vowel"
    # "ghost correspondence": letters that look alike although their sounds are not alike. Of the closest-looking pairs,
    # what share are cross-group, relative to the share of all pairs that are cross-group? Above 1 is jarring.
    pairs = sorted((d, a, b) for (a, b), d in dist.items() if a < b)
    ghost = None
    if len(pairs) >= 10:
        cross = lambda a, b: grp[a] != grp[b]
        close = pairs[:max(3, len(pairs) * 15 // 100)]
        share_close = sum(cross(a, b) for _, a, b in close) / len(close)
        share_all = sum(cross(a, b) for _, a, b in pairs) / len(pairs)
        ghost = round(share_close / share_all, 2) if share_all else None
    return {"ghost_ratio": ghost, "vowel_within": mean(lambda x, y: v(x) and v(y)),
            "vowel_vs_consonant": mean(lambda x, y: v(x) != v(y)),
            "manner_within": mean(lambda x, y: not v(x) and not v(y) and x == y),
            "manner_across": mean(lambda x, y: not v(x) and not v(y) and x != y),
            "nearest_same_kind": agree(lambda x, y, _: v(x) == v(y)),
            "nearest_same_manner": agree(lambda x, y, _: x == y)}
