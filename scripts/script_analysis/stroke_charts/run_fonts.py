"""Draft the strokes of every font-based script:  python -m stroke_charts.run_fonts FONTDIR OUTDIR [script ...]
(run from scripts/script_analysis; FONTDIR holds the Noto Sans files, see corpus.py)"""
import os
import sys
from fontTools.ttLib import TTFont
from .fontdraft import draft

rng = lambda a, b: [chr(c) for c in range(a, b + 1)]
DJV = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SCRIPTS = {   # name: (font file under FONTDIR or absolute, characters, title)
    "hebrew": (DJV, rng(0x5D0, 0x5EA), "Hebrew"),
    "arabic": ("NotoNaskhArabic[wght].ttf", rng(0x627, 0x64A), "Arabic (isolated forms)"),
    "thai": ("NotoSansThai[wdth,wght].ttf", rng(0xE01, 0xE2E), "Thai"),
    "tamil": ("NotoSansTamil[wdth,wght].ttf", rng(0xB85, 0xB94) + rng(0xB95, 0xBB9), "Tamil"),
    "devanagari": ("NotoSansDevanagari[wdth,wght].ttf", rng(0x905, 0x914) + rng(0x915, 0x939), "Devanagari"),
    "bengali": ("NotoSansBengali[wdth,wght].ttf", rng(0x985, 0x994) + rng(0x995, 0x9B9), "Bengali"),
    "armenian": ("NotoSansArmenian[wdth,wght].ttf", rng(0x531, 0x556) + rng(0x561, 0x586), "Armenian"),
}

if __name__ == "__main__":
    fonts, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for name in (sys.argv[3:] or SCRIPTS):
        f, chars, title = SCRIPTS[name]
        font = TTFont(f if os.path.isabs(f) else os.path.join(fonts, f))
        if "fvar" in font:                                       # a variable font: use its lightest weight, where strokes are thin and crossings stay crisp
            from fontTools.varLib import instancer
            lim = {a.axisTag: (a.minValue if a.axisTag == "wght" else a.defaultValue) for a in font["fvar"].axes}
            font = instancer.instantiateVariableFont(font, lim)
        rep = draft(font, chars, title + " (from the font, junction rules)", os.path.join(out, name))
        print(name, len(rep), "letters", sum(r["strokes"] for r in rep) / max(1, len(rep)), "strokes each", flush=True)
