"""Chart of font glyph | extracted graph for every letter in graph_<script>.json.   python chart_graphs.py bengali"""
import json, sys
from PIL import Image, ImageDraw, ImageFont
from font_topo import render, FONT
name = sys.argv[1]; g = json.load(open(f"/home/claude/graph_{name}.json")); font = ImageFont.truetype(FONT, 120)
cols, cw, ch = 4, 330, 190; rows = (len(g) + cols - 1) // cols
M = Image.new("RGB", (cols * cw, rows * ch), "white"); d = ImageDraw.Draw(M)
for i, (code, v) in enumerate(g.items()):
    x, y = (i % cols) * cw, (i // cols) * ch
    d.text((x + 6, y + 4), f"{code} {v['metrics']['loops']}L {v['metrics']['junctions']}J {v['metrics']['ends']}E", fill=(0, 120, 0))
    d.text((x + 20, y + 30), v["char"], font=font, fill=0)
    M.paste(render(v).resize((150, 150)), (x + 165, y + 28))
M.save(f"/home/claude/chart_{name}.png"); print(M.size)
