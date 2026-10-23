"""SVG output: a specimen sheet (every letter, signs, digits, punctuation) and sample text."""
from __future__ import annotations

import math
from html import escape

from .geometry import flatten, svg_path
from .layout import compose, sample_words, set_lines, set_text

INK = "#1b1b1b"
WEIGHT = 0.1        # stroke thickness in em for the monoline sans first pass


def _lean(s, t):
    """A stroke sheared to the right about the baseline: x grows by y * tan(slant)."""
    return dict(s, p=[[x + y * t, y] for x, y in s["p"]])


def strokes_svg(strokes, roundness, scale=100.0, ox=0.0, oy=0.0, color=INK, weight=WEIGHT, slant=0.0):
    out = []
    t = math.tan(math.radians(slant)) if slant else 0.0
    for s in strokes:
        if t:
            s = _lean(s, t)
        if s.get("dot"):
            x, y = s["p"][0]
            out.append(f'<circle cx="{(x + ox) * scale:.1f}" cy="{(oy - y) * scale:.1f}" r="{s["r"] * scale:.1f}" fill="{color}"/>')
        elif s.get("fill"):             # a filled wedge (cuneiform): sharp corners, a thin outline so the thin tail stays visible
            out.append(f'<path d="{svg_path(s, 0.0, scale, ox, oy)}" fill="{color}" stroke="{color}" stroke-width="{0.025 * scale:.1f}" stroke-linejoin="miter"/>')
        else:
            out.append(f'<path d="{svg_path(s, roundness, scale, ox, oy)}" fill="none" stroke="{color}" '
                       f'stroke-width="{weight * scale:.1f}" stroke-linecap="{"round" if s.get("k", "m") == "m" and roundness > 0.2 else "butt"}" '
                       f'stroke-linejoin="{"round" if s.get("k", "m") == "m" and roundness > 0.2 else "miter"}"/>')
    return "".join(out)


def text_svg(script, words=None, scale=60.0, pad=0.4, bare=False):
    """One line of sample text as a standalone SVG. `bare` draws it for a list row: no white background, and the strokes take the
    text colour of the page (so it follows light and dark themes)."""
    words = words or sample_words(script, 6)
    strokes, w = set_text(script, words)
    h = 2.6
    body = strokes_svg(strokes, script["spec"]["roundness"], scale, pad, 1.55 + pad / 2, slant=script["spec"].get("slant", 0.0), **({"color": "currentColor"} if bare else {}))
    bg = "" if bare else '<rect width="100%" height="100%" fill="#fff"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{(w + 2 * pad) * scale:.0f}" height="{h * scale:.0f}" '
            f'viewBox="0 0 {(w + 2 * pad) * scale:.0f} {h * scale:.0f}">{bg}{body}</svg>')


def sheet_svg(script, scale=70.0, cols=8):
    spec = script["spec"]
    r = spec["roundness"]
    cw, ch = 1.7, 2.9
    items = []
    for l in script["letters"]:
        sub = f"{l['motif']}/{l['variant']}" if l.get("motif") else f"{l['from']}+{l.get('feature') or l.get('relation')}" if l.get("from") else ""
        if len(sub) > 20:
            sub = sub[:19] + "…"
        items.append((l["id"] + ("|" + sub if sub else ""), l["strokes"], l["width"]))
    for s in script.get("signs", []):
        base = next((l["id"] for l in script["letters"] if l["role"] == "consonant"), script["letters"][0]["id"])
        st, w = compose(script, base, s["id"])
        items.append((("+" if s["long_of"] is None else "+") + s["id"] + (" (long)" if s["long_of"] else ""), st, w))
    if script.get("virama"):
        base = script["letters"][0]["id"]
        st, w = compose(script, base, None, True)
        items.append(("virama", st, w))
    for d in script["digits"]:
        sub = f"{d['motif']}/{d['variant']}" if d.get("motif") else "random"
        items.append((d["id"] + "|" + (sub[:19] + "…" if len(sub) > 20 else sub), d["strokes"], d["width"]))
    for k, p in script["punct"].items():
        items.append((k, p["strokes"], p["width"]))
    rows = -(-len(items) // cols)
    sample_h = 8.4
    W, H = cols * cw + 0.6, rows * ch + sample_h + 1.2
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * scale:.0f}" height="{H * scale:.0f}" viewBox="0 0 {W * scale:.0f} {H * scale:.0f}">'
           f'<rect width="100%" height="100%" fill="#fff"/>']
    title = (f'seed {spec["seed"]} · {spec["kind"]} · {spec["direction"]}'
             f'{" · topline" if spec["topline"] == "bar" else ""}{" · joined" if spec["joining"] == "baseline" else ""}'
             f' · roundness {spec["roundness"]}')
    out.append(f'<text x="{0.3 * scale}" y="{0.5 * scale}" font-family="sans-serif" font-size="{0.3 * scale:.0f}" fill="#555">{escape(title)}</text>')
    for i, (label, strokes, w) in enumerate(items):
        cx, cy = 0.3 + (i % cols) * cw, 0.9 + (i // cols) * ch
        base_y = cy + 1.9
        for yy, col in ((0, "#cfd8e8"), (1.0, "#e4e8f0")):
            out.append(f'<line x1="{cx * scale:.0f}" x2="{(cx + cw - 0.15) * scale:.0f}" y1="{(base_y - yy) * scale:.0f}" y2="{(base_y - yy) * scale:.0f}" stroke="{col}"/>')
        out.append(strokes_svg(strokes, r, scale, cx + 0.45, base_y, slant=spec.get("slant", 0.0)))
        name, _, note = str(label).partition("|")
        out.append(f'<text x="{(cx + 0.1) * scale:.0f}" y="{(cy + 2.6) * scale:.0f}" font-family="sans-serif" font-size="{0.26 * scale:.0f}" fill="#777">{escape(name)}</text>')
        if note:
            out.append(f'<text x="{(cx + 0.1) * scale:.0f}" y="{(cy + 2.85) * scale:.0f}" font-family="sans-serif" font-size="{0.17 * scale:.0f}" fill="#aaa">{escape(note)}</text>')
    y0 = 0.9 + rows * ch + 0.4
    words = sample_words(script, 14, "sample")
    for line, (st, w) in enumerate(set_lines(script, words, W - 0.8)[:3]):
        ox = (W - 0.3 - w) if spec["direction"] == "rtl" else 0.3
        out.append(strokes_svg(st, r, scale, ox, y0 + 1.55 + line * 2.3, slant=spec.get("slant", 0.0)))
    out.append("</svg>")
    return "".join(out)
