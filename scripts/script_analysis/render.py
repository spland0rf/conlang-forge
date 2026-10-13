"""Render each script's base letters (PIL) into per-script sheets and return the glyph bitmaps for measuring."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from corpus import SCRIPTS, font_for

SIZE = 120          # em size in pixels
CELL = 170


def glyph_bitmaps(name):
    path, tt, _ = font_for(name)
    cm = tt.getBestCmap()
    font = ImageFont.truetype(path, SIZE, index=0)
    out = []
    for ch in SCRIPTS[name]["letters"]:
        if ord(ch) not in cm:
            continue
        im = Image.new("L", (CELL * 2, CELL * 2), 0)
        d = ImageDraw.Draw(im)
        d.text((CELL * 0.6, CELL * 1.2), ch, font=font, fill=255, anchor="ls")   # baseline at y = 1.2 CELL
        out.append((ch, np.array(im) > 127))
    return out, CELL * 1.2


def sheet(name, outdir, cols=14):
    gl, _ = glyph_bitmaps(name)
    rows = (len(gl) + cols - 1) // cols
    W = Image.new("L", (cols * CELL, rows * CELL), 255)
    for i, (ch, bm) in enumerate(gl):
        ys, xs = np.nonzero(bm)
        tile = Image.fromarray((~bm * 255).astype("uint8")).crop((int(CELL * 0.5), int(CELL * 0.3), int(CELL * 1.5), int(CELL * 1.5)))
        tile.thumbnail((CELL, CELL))
        W.paste(tile, ((i % cols) * CELL, (i // cols) * CELL))
    W.save(os.path.join(outdir, name + ".png"))


if __name__ == "__main__":
    os.makedirs("/tmp/scriptsheets", exist_ok=True)
    for n in SCRIPTS:
        sheet(n, "/tmp/scriptsheets")
        print("ok", n)
