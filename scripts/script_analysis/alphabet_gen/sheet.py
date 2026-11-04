"""Printable review sheet for the generated alphabet: 6 x 8 squares per page, in sequential pairs -- first the letter drawn as a coloured stroke
sequence with its number and a 1 2 3 4 score row (1 very un-Devanagari-like ... 4 very Devanagari-like), then a blank square to redraw it in.
usage: python3 sheet.py out.pdf [alphabet.json]"""
import json, os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
COLORS = ["#d62728", "#1f5fbf", "#1b9e5a", "#e08a00", "#7b3fb3", "#0b8c99"]

def ordered(l):
    """Stroke order for the sheet: vertical parts first, then the body strokes, the headline last (as in handwriting)."""
    S = []; sk = l["sk"]
    if l["skel"] == "stem": S.append([[sk["S"], 20], [sk["S"], 88]])
    if l["skel"] == "desc": S.append([[sk["x"], 20], [sk["x"], sk["y"]]])
    for d in l.get("descs") or []: S.append([[d[0], 20], [d[0], d[1]]])
    if l["skel"] == "half":
        st = l["struct"]                                      # right form (vertical, top stroke) then the connector
        S.append(l["strokes"][0]); S.append(st[-1]); S.append(st[0])
        for P in l["strokes"][1:]: S.append(P)
        S.append(st[1])
    else:
        for P in l["strokes"]: S.append(P)
        if l.get("bar"): S.append([[l["bar"][0], 20], [l["bar"][1], 20]])
    return S

def cell(l, i):
    s = '<svg viewBox="0 10 100 84" xmlns="http://www.w3.org/2000/svg">'
    for k, P in enumerate(ordered(l)):
        d = "M" + "L".join("%s %s" % (round(x, 1), round(y, 1)) for x, y in P)
        c = COLORS[k % len(COLORS)]
        s += '<path d="%s" fill="none" stroke="%s" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>' % (d, c)
    for k, P in enumerate(ordered(l)):
        c = COLORS[k % len(COLORS)]; x, y = P[0]
        s += '<circle cx="%s" cy="%s" r="4.2" fill="#fff" stroke="%s" stroke-width="1.2"/><text x="%s" y="%s" font-size="5.6" text-anchor="middle" fill="%s" font-family="Arial,sans-serif" font-weight="700">%d</text>' % (round(x, 1), round(y, 1), c, round(x, 1), round(y + 2, 1), c, k + 1)
    return s + "</svg>"

def build(letters):
    pages = []; per_page = 24
    for p0 in range(0, len(letters), per_page):
        cells = []
        for i, l in enumerate(letters[p0:p0 + per_page], p0 + 1):
            cells.append('<div class="sq"><div class="id">A%d</div>%s<div class="sc"><span>1</span><span>2</span><span>3</span><span>4</span></div></div>' % (i, cell(l, i)))
            cells.append('<div class="sq blank"><div class="id">A%d</div></div>' % i)
        while len(cells) < 48: cells.append('<div class="sq empty"></div>')
        pages.append('<section class="pg"><div class="hd">Generated alphabet &middot; sheet %d of %d &middot; left: stroke sequence (numbers = order) &middot; circle a score &middot; right: redraw</div><div class="grid">%s</div><div class="ft">1 very un-Devanagari-like &nbsp;&nbsp; 2 slightly un-Devanagari-like &nbsp;&nbsp; 3 slightly Devanagari-like &nbsp;&nbsp; 4 very Devanagari-like</div></section>' % (p0 // per_page + 1, (len(letters) + per_page - 1) // per_page, "".join(cells)))
    css = """@page{size:8.5in 11in;margin:0}*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;color:#222}
.pg{width:8.5in;height:11in;padding:.3in .5in 0;height:11in;overflow:hidden;page-break-after:always;position:relative}
.hd{font-size:8pt;height:.25in;line-height:.22in;color:#555}.ft{font-size:8pt;height:.2in;line-height:.2in;color:#555;margin-top:.05in}
.grid{display:grid;grid-template-columns:repeat(6,1.25in);grid-auto-rows:1.25in}
.sq{border:.6pt solid #999;margin:0 -.3pt -.3pt 0;position:relative;overflow:hidden}.sq.empty{border:none}
.sq svg{position:absolute;left:.04in;top:.15in;width:1.17in;height:.9in}
.id{position:absolute;left:.04in;top:.02in;font-size:7.5pt;font-weight:700;color:#444;z-index:2}.blank .id{color:#aaa;font-weight:400}
.sc{position:absolute;left:0;right:0;bottom:.03in;display:flex;justify-content:space-around;padding:0 .12in}
.sc span{width:.2in;height:.2in;line-height:.2in;text-align:center;font-size:9pt;color:#444}"""
    return "<!doctype html><meta charset=utf-8><style>%s</style>%s" % (css, "".join(pages))

if __name__ == "__main__":
    out = sys.argv[1]; src = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "alphabet.json")
    L = json.load(open(src))["letters"]; html = build(L)
    h = out.rsplit(".", 1)[0] + ".html"; open(h, "w").write(html)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(); pg.goto("file://" + os.path.abspath(h)); pg.pdf(path=out, width="8.5in", height="11in", print_background=True, prefer_css_page_size=True); b.close()
    print(len(L), "letters ->", out)
