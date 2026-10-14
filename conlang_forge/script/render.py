"""SVG output: a specimen sheet (every letter, signs, digits, punctuation) and sample text."""
from __future__ import annotations

from html import escape

from .geometry import flatten, svg_path
from .layout import compose, sample_words, set_lines, set_text

INK = "#1b1b1b"
WEIGHT = 0.1        # stroke thickness in em for the monoline sans first pass


def strokes_svg(strokes, roundness, scale=100.0, ox=0.0, oy=0.0, color=INK, weight=WEIGHT):
    out = []
    for s in strokes:
        if s.get("dot"):
            x, y = s["p"][0]
            out.append(f'<circle cx="{(x + ox) * scale:.1f}" cy="{(oy - y) * scale:.1f}" r="{s["r"] * scale:.1f}" fill="{color}"/>')
        else:
            out.append(f'<path d="{svg_path(s, roundness, scale, ox, oy)}" fill="none" stroke="{color}" '
                       f'stroke-width="{weight * scale:.1f}" stroke-linecap="{"round" if s.get("k", "m") == "m" and roundness > 0.2 else "butt"}" '
                       f'stroke-linejoin="{"round" if s.get("k", "m") == "m" and roundness > 0.2 else "miter"}"/>')
    return "".join(out)


def text_svg(script, words=None, scale=60.0, pad=0.4):
    """One line of sample text as a standalone SVG."""
    words = words or sample_words(script, 6)
    strokes, w = set_text(script, words)
    h = 2.6
    body = strokes_svg(strokes, script["spec"]["roundness"], scale, pad, 1.55 + pad / 2)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{(w + 2 * pad) * scale:.0f}" height="{h * scale:.0f}" '
            f'viewBox="0 0 {(w + 2 * pad) * scale:.0f} {h * scale:.0f}"><rect width="100%" height="100%" fill="#fff"/>{body}</svg>')


def sheet_svg(script, scale=70.0, cols=8):
    spec = script["spec"]
    r = spec["roundness"]
    cw, ch = 1.7, 2.9
    items = []
    for l in script["letters"]:
        items.append((l["id"], l["strokes"], l["width"]))
    for s in script.get("signs", []):
        base = next((l["id"] for l in script["letters"] if l["role"] == "consonant"), script["letters"][0]["id"])
        st, w = compose(script, base, s["id"])
        items.append((("+" if s["long_of"] is None else "+") + s["id"] + (" (long)" if s["long_of"] else ""), st, w))
    if script.get("virama"):
        base = script["letters"][0]["id"]
        st, w = compose(script, base, None, True)
        items.append(("virama", st, w))
    for d in script["digits"]:
        items.append((d["id"], d["strokes"], d["width"]))
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
        out.append(strokes_svg(strokes, r, scale, cx + 0.45, base_y))
        out.append(f'<text x="{(cx + 0.1) * scale:.0f}" y="{(cy + 2.75) * scale:.0f}" font-family="sans-serif" font-size="{0.26 * scale:.0f}" fill="#777">{escape(str(label))}</text>')
    y0 = 0.9 + rows * ch + 0.4
    words = sample_words(script, 14, "sample")
    for line, (st, w) in enumerate(set_lines(script, words, W - 0.8)[:3]):
        ox = (W - 0.3 - w) if spec["direction"] == "rtl" else 0.3
        out.append(strokes_svg(st, r, scale, ox, y0 + 1.55 + line * 2.3))
    out.append("</svg>")
    return "".join(out)
