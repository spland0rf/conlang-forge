"""Generate a writing system from a seed (plus optional pins). Pure standard library and fully deterministic: each part
of the script draws from its own random stream, so pinning one dial changes only what depends on it.

Stage 1 covers linear alphabets and abjads, and abugidas whose vowel signs sit in slots around the consonant letter.
Letters are grown as connected stroke graphs (motifs.py); roundness is applied only when drawing."""
from __future__ import annotations

import math

from ..wordgen import rng_for
from .geometry import LINES, bbox, dot, mirror_x, place, shift, stroke, transform
from .graph import analyse, distance, far_enough, points
from .marks import grow_part, make_part, place_part
from .motifs import _tag, make_styled_body
from .shapes import CLASS_OF, CLASS_ORDER, MOTIFS, ORTHO_MOTIFS, VARIANTS, apply_variant, style_strokes, usable
from .spec import DEFAULT_CONSONANTS, DEFAULT_VOWELS, resolve

STEP = 0.11
# which sound a derived letter is built from (mirror twins and marked letters follow related sounds)
PARENT = {
    "b": "p", "d": "t", "g": "k", "z": "s", "v": "f", "ʒ": "ʃ", "dʒ": "tʃ", "ð": "θ", "ɣ": "x", "pʰ": "p", "tʰ": "t",
    "kʰ": "k", "ŋ": "n", "ɲ": "n", "ts": "t", "ʃ": "s", "ʔ": "h", "x": "h", "q": "k", "θ": "t", "tʃ": "t",
    "y": "i", "ø": "e", "ɛ": "e", "ɔ": "o", "æ": "a", "ə": "a", "ɑ": "a", "ɪ": "i", "ʊ": "u",
}
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
        near = [p for p in pts if abs(p[1]) <= 0.12] or [min(pts, key=lambda q: abs(q[1]))]
        lx, rx = min(p[0] for p in near), max(p[0] for p in near)
        lp, rp = min(near, key=lambda p: p[0]), max(near, key=lambda p: p[0])
        for p, side in ((lp, "L"), (rp, "R")):
            if abs(p[1]) > 0.02:
                out.append(dict(stroke([(p[0], p[1]), (p[0], 0.0)]), stub=side))
        if lx > 0.02:
            out.append(dict(stroke([(0, 0.0), (lx, 0.0)]), stub="L"))
        if rx < w - 0.02:
            out.append(dict(stroke([(rx, 0.0), (w, 0.0)]), stub="R"))
    return out[:base] + _tag(out[base:], kind)


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
    """Distance to the nearest pooled letter; stops early once it is known to be below `floor`."""
    m = 9.0
    for _, pts in pool:
        m = min(m, distance(cand_pts, pts))
        if m < floor:
            break
    return m


def _make_glyph(rng, spec, pool, weights=None, tries=450, d_scale=1.0):
    """One new base letter, distinct from everything in the pool. If the space is crowded the threshold relaxes and
    the shapes get more complex; if nothing passes, the most distinct candidate seen is used."""
    base_d = spec["min_distance"] * d_scale
    exempt = rng.random() < 0.12
    band, (y0, y1) = _band(rng, spec)         # decided once, so crowding cannot bias letters toward tall bands
    best, best_score = None, -1.0
    for attempt in range(tries):
        frac = attempt / tries
        d = base_d * (1.0 if frac < 0.4 else 0.85 if frac < 0.7 else 0.7)
        density = min(1.0, spec["density"] + (0.5 if frac > 0.75 else 0.25 if frac > 0.5 else 0.0))
        body, fam, kind = make_styled_body(rng, density, spec["loops"], weights, spec["corner_style"])
        w = max(0.3, spec["width"] * rng.uniform(0.9, 1.1) * (0.6 if fam in ("stem", "bar") and rng.random() < 0.5 else 1.0))
        core = _fit(body, w, y0, y1)
        if core is None:
            continue
        if spec["corner_style"] == "mixed":                          # angles change when a body is stretched: classify again
            core, kind = style_strokes(rng, core, "mixed")
        # most letters sit in the standard frame with their weight near its middle; a few are allowed to be lopsided
        if not exempt and _balance(core, w, y0, y1) > spec["frame_tolerance"] * (1.0 if frac < 0.6 else 1.6 if frac < 0.85 else 9.0):
            continue
        if spec["topline"] == "bar":
            core = _reach(core, 1.0)
        pts = points(_dress(core, w, spec, kind), step=STEP)     # what the reader sees, including the topline
        if not pool or all(far_enough(pts, p, d) for _, p in pool):
            best, best_score = (core, w, fam, band, pts, kind), 9.0
            break
        if best is None or frac > 0.6:                    # only track the best fallback once the space looks crowded
            score = _mind(pts, pool, max(best_score, 0.0) if best else 0.0)
            if score > best_score:
                best, best_score = (core, w, fam, band, pts, kind), score
    if best is None:
        return _make_glyph(rng, spec, pool, None, tries, d_scale)
    core, w, fam, band, pts, kind = best
    return {"strokes": _dress(core, w, spec, kind), "width": round(w, 3), "family": fam, "band": band, "_pts": pts,
            "_core": core, "kind": kind}


def _balance(core, w, y0, y1):
    """How far the ink's centre of gravity sits from the middle of the letter frame (0 = centred, in frame units)."""
    pts = points(core, step=0.05)
    if not pts:
        return 0.0
    cx = sum(p[0] for p in pts) / len(pts) / (w or 1)
    cy = (sum(p[1] for p in pts) / len(pts) - y0) / ((y1 - y0) or 1)
    return max(abs(cx - 0.5), abs(cy - 0.5))


def _make_motif_glyph(rng, spec, pool, shape, used, kin=()):
    """A letter built from a characteristic shape plus one variant nobody else in its class has used."""
    ortho = spec["corner_style"] == "blocky"
    table = ORTHO_MOTIFS if ortho else MOTIFS
    ops = [o for o in VARIANTS if o not in used]
    rng.shuffle(ops)
    d = spec["min_distance"] * 0.7
    band, (y0, y1) = _band(rng, spec)
    for op in ops:
        v = apply_variant(table[shape](), op, ortho)
        if not v or not usable(v, ortho):
            continue
        body, kind = style_strokes(rng, v, spec["corner_style"])
        w = max(0.4, spec["width"] * rng.uniform(0.7, 0.95))
        core = _fit(body, w, y0, y1)
        if core is None:
            continue
        if spec["corner_style"] == "mixed":
            core, kind = style_strokes(rng, core, "mixed")
        if _balance(core, w, y0, y1) > spec["frame_tolerance"] * 1.5:
            continue
        if spec["topline"] == "bar":
            core = _reach(core, 1.0)
        pts = points(_dress(core, w, spec, kind), step=STEP)
        # relatives (same shape) may look alike -- that is the point -- but others must stay clearly apart
        if pool and not all(far_enough(pts, p, d * (0.5 if gid in kin else 1.0)) for gid, p in pool):
            continue
        return {"strokes": _dress(core, w, spec, kind), "width": round(w, 3), "family": f"motif:{shape}", "band": band,
                "_pts": pts, "_core": core, "kind": kind, "motif": shape, "variant": op}, op
    return None, None


def _glyph_of(core, w, spec, fam, band, relation=None, parent=None, mark=None, kind="m"):
    return {"kind": kind, "strokes": _dress(core, w, spec, kind), "width": round(w, 3), "family": fam, "band": band,
            "relation": relation, "from": parent, "mark": mark, "_pts": points(_dress(core, w, spec, kind), step=STEP), "_core": core}


def _derive_mirror(rng, g, spec):
    """A mirror (or, without a topline, sometimes a 180-degree rotated) twin of a letter body."""
    w = g["width"]
    core = g["_core"]
    if spec["topline"] == "none" and spec["joining"] == "none" and g["band"] == "x" and rng.random() < 0.3:
        return transform(core, lambda x: w - x, lambda y: 1.0 - y), "rotate"
    return mirror_x(core, w), "mirror"


def _symmetric(g, other_core, w, spec):
    return distance(g["_pts"], points(other_core, step=STEP)) < spec["min_distance"] * 0.5


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
    mark_ids = derivable[n_mirror:n_mirror + n_mark]
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
    ortho = spec["corner_style"] == "blocky"
    table = ORTHO_MOTIFS if ortho else MOTIFS
    mrng2 = rng_for(spec["seed"], "script", "motifs")
    names = list(table)
    mrng2.shuffle(names)
    n_motifs = min(spec["motif_count"], len(names))
    shapes = names[:n_motifs]
    class_shape = {c: shapes[i % n_motifs] for i, c in enumerate(CLASS_ORDER)} if n_motifs else {}
    used_ops: dict[str, set] = {}
    for lid in letter_ids:
        if lid in derived:
            continue
        isv = lid in vows
        g = None
        cls = CLASS_OF.get(lid)
        if cls and class_shape and mrng2.random() < spec["motif_share"]:
            kin = {k for k, v in glyphs.items() if v.get("motif") == class_shape[cls]}
            g, op = _make_motif_glyph(mrng2, spec, pool, class_shape[cls], used_ops.setdefault(cls, set()), kin)
            if g:
                used_ops[cls].add(op)
        if g is None:
            g = _make_glyph(lrng, spec, pool, vowel_w if isv else None)
        g.update(relation=None, **{"from": None, "mark": None, "role": "vowel" if isv else "consonant"})
        glyphs[lid] = g
        pool.append((lid, g["_pts"]))

    # mirror twins (a lower threshold applies to declared pairs)
    mirrored = set()
    for lid in mirror_ids:
        par = glyphs[PARENT[lid]]
        core, rel = _derive_mirror(lrng, par, spec)
        pts = points(core, step=STEP)
        if PARENT[lid] in mirrored or distance(pts, par["_pts"]) < spec["min_distance"] * 0.5 or not _fits(pts, pool, spec["min_distance"] * 0.7, (PARENT[lid],)):
            # not different enough from its parent or too like another letter: make it an independent letter instead
            g = _make_glyph(lrng, spec, pool)
            g.update(relation=None, **{"from": None, "mark": None, "role": "vowel" if lid in vows else "consonant"})
        else:
            mirrored.add(PARENT[lid])
            g = _glyph_of(core, par["width"], spec, par["family"], par["band"], rel, PARENT[lid], None, par["kind"])
            g["role"] = "vowel" if lid in vows else "consonant"
        glyphs[lid] = g
        pool.append((lid, g["_pts"]))

    # diacritic marks (alphabets and abjads)
    marks = []
    if mark_ids:
        krng = rng_for(spec["seed"], "script", "marks")
        def new_mark():
            for _ in range(30):
                slot = krng.choice(["above", "above", "below"])
                m = dict(make_part(krng, slot, 0.15, 0.2, 0.45, spec["corner_style"]), id=f"m{len(marks) + 1}", slot=slot)
                if all(m["slot"] != o["slot"] or m["kind"] != o["kind"] for o in marks):
                    break
            marks.append(m)

        for _ in range(min(len(mark_ids), krng.choice([2, 2, 3, 3, 4]))):
            new_mark()
        used: dict[str, set] = {}
        for j, lid in enumerate(mark_ids):
            par = glyphs[PARENT[lid]]
            taken = used.setdefault(PARENT[lid], set())
            free = [m for m in marks if m["id"] not in taken]
            if not free:                    # siblings of one letter each need their own mark
                new_mark()
                free = [marks[-1]]
            mk = free[j % len(free)]
            taken.add(mk["id"])
            core = par["_core"] + place_part(par["_core"], mk["slot"], mk)
            g = _glyph_of(core, par["width"], spec, par["family"], par["band"], "mark", PARENT[lid], mk["id"], par["kind"])
            g["role"] = "vowel" if lid in vows else "consonant"
            glyphs[lid] = g
            pool.append((lid, g["_pts"]))

    # safety net: no two unrelated letters may end up (nearly) identical, whatever path produced them
    final = {lid: points(glyphs[lid]["strokes"], step=0.05) for lid in letter_ids}
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
                ng = _make_glyph(lrng, spec, pool2, vowel_w if victim in vows else None)
                ng.update(relation=None, **{"from": None, "mark": None, "role": "vowel" if victim in vows else "consonant"})
                glyphs[victim] = ng
                final[victim] = points(ng["strokes"], step=0.05)
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
                        "motif": g.get("motif"), "variant": g.get("variant"), "joins": g["joins"]})

    shape_classes = {}
    for c, sh in class_shape.items():
        shape_classes.setdefault(sh, []).append(c)
    script = {"version": 1, "spec": spec, "letters": letters,
              "motifs": [{"shape": sh, "classes": cs} for sh, cs in shape_classes.items()], "marks": [_public_part(m) for m in marks]}
    if sign_vowels:
        script["signs"] = _make_signs(spec, vows, glyphs)
        if kind == "abugida":
            script["virama"] = _make_virama(spec, script["signs"])
    script["punct"] = _make_punct(spec)
    script["digits"] = _make_digits(spec)
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
    signs, pool = [], []
    for vid in shorts:
        sign = None
        for attempt in range(200):
            if pairs and srng.random() < spec["sign_frames"]:
                slots = list(srng.choice(pairs))
            else:
                slots = [srng.choices(list(slot_w), list(slot_w.values()))[0]]
            parts = {s: make_part(srng, s, 0.12, 0.25, 0.25, spec["corner_style"]) for s in slots}
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
                  "parts": {s: make_part(srng, s, 0.12, 0.25, 0.25, spec["corner_style"]) for s in short["slots"]}}
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
        part = make_part(vrng, slot, 0.0, 0.0, 0.5, spec["corner_style"])
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


def _make_digits(spec):
    drng = rng_for(spec["seed"], "script", "digits")
    dspec = dict(spec, topline="none", joining="none", ascender_share=0.0, descender_share=0.0, min_distance=0.2)
    pool, out = [], []
    for i in range(10):
        g = _make_glyph(drng, dspec, pool, tries=150)
        pool.append((i, g["_pts"]))
        out.append({"id": str(i), "strokes": g["strokes"], "width": g["width"]})
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
    pts = [(l["id"], points(l["strokes"], step=STEP)) for l in letters]
    related = {frozenset((l["id"], l["from"])) for l in letters if l["from"]}     # declared pairs are allowed to be close
    kin = [l for l in letters if l["from"]]
    related |= {frozenset((a["id"], b["id"])) for a in kin for b in kin if a["from"] == b["from"] and a is not b}
    nn = []
    for i, (a, p) in enumerate(pts):
        nn.append(min((distance(p, q) for j, (b, q) in enumerate(pts) if j != i and frozenset((a, b)) not in related), default=9.0))
    med = lambda v: sorted(v)[len(v) // 2] if v else 0
    nn.sort()
    return {"letters": len(letters), "median_ends": med(ends), "median_junctions": med(juncs), "median_loops": med(loops),
            "share_loops": round(sum(1 for v in loops if v) / max(1, len(loops)), 2),
            "share_detached": round(detached / max(1, len(letters)), 2),
            "nn_distance_p10": round(nn[int(0.1 * len(nn))], 3) if nn else None}
