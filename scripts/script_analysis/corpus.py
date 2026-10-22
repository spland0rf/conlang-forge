"""The reference corpus: base letters of 13 scripts, and a font that covers each one.
Used only to *measure* real scripts. Glyphs from these fonts are never copied into generated output."""
import sys
from fontTools.ttLib import TTFont, TTCollection

FREE = "/usr/share/fonts/truetype/freefont/"
DJV = "/usr/share/fonts/truetype/dejavu/"
NOTO = "/usr/share/fonts/opentype/noto/"
LOMA = "/usr/share/fonts/opentype/tlwg/Loma.otf"


def rng(a, b): return [chr(c) for c in range(a, b + 1)]


SCRIPTS = {
    "Latin":      dict(letters=rng(0x41, 0x5A) + rng(0x61, 0x7A), fonts=[FREE + "FreeSans.ttf", DJV + "DejaVuSans.ttf"], dir="ltr"),
    "Greek":      dict(letters=rng(0x391, 0x3A9) + rng(0x3B1, 0x3C9), fonts=[FREE + "FreeSans.ttf", DJV + "DejaVuSans.ttf"], dir="ltr"),
    "Cyrillic":   dict(letters=rng(0x410, 0x42F) + rng(0x430, 0x44F), fonts=[FREE + "FreeSans.ttf", DJV + "DejaVuSans.ttf"], dir="ltr"),
    "Armenian":   dict(letters=rng(0x531, 0x556) + rng(0x561, 0x586), fonts=[DJV + "DejaVuSans.ttf", FREE + "FreeSerif.ttf"], dir="ltr"),
    "Georgian":   dict(letters=rng(0x10D0, 0x10F0), fonts=[DJV + "DejaVuSans.ttf", FREE + "FreeSerif.ttf"], dir="ltr"),
    "Hebrew":     dict(letters=rng(0x5D0, 0x5EA), fonts=[FREE + "FreeSans.ttf", DJV + "DejaVuSans.ttf"], dir="rtl"),
    "Arabic":     dict(letters=rng(0x627, 0x64A), fonts=[DJV + "DejaVuSans.ttf", FREE + "FreeSerif.ttf"], dir="rtl"),
    "Devanagari": dict(letters=rng(0x905, 0x914) + rng(0x915, 0x939), fonts=[FREE + "FreeSans.ttf", FREE + "FreeSerif.ttf"], dir="ltr"),
    "Bengali":    dict(letters=rng(0x985, 0x994) + rng(0x995, 0x9B9), fonts=[FREE + "FreeSans.ttf", FREE + "FreeSerif.ttf"], dir="ltr"),
    "Tamil":      dict(letters=rng(0xB85, 0xB94) + rng(0xB95, 0xBB9), fonts=[FREE + "FreeSans.ttf", FREE + "FreeSerif.ttf"], dir="ltr"),
    "Thai":       dict(letters=rng(0xE01, 0xE2E), fonts=[LOMA, FREE + "FreeSerif.ttf"], dir="ltr"),
    "Ethiopic":   dict(letters=[chr(c) for c in range(0x1200, 0x1348, 8)], fonts=[FREE + "FreeSerif.ttf"], dir="ltr"),
    "Hangul":     dict(letters=rng(0x3131, 0x3163) + list("가나다라마바사아자차카타파하글한"), fonts=[NOTO + "NotoSansCJK-Regular.ttc"], dir="ltr"),
    # the 46 basic kana plus the 25 voiced ones (so the detached voicing marks are measured too); Noto Sans CJK's first face is the Japanese one
    "Hiragana":   dict(letters=list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん" "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ"), fonts=[NOTO + "NotoSansCJK-Regular.ttc"], dir="ltr"),
    "Katakana":   dict(letters=list("アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン" "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ"), fonts=[NOTO + "NotoSansCJK-Regular.ttc"], dir="ltr"),
}


def load(path):
    if path.endswith(".ttc"):
        return TTCollection(path).fonts[0]
    return TTFont(path)


def font_for(name):
    """First font that has every letter of the script (or the best-covering one)."""
    best = None
    for p in SCRIPTS[name]["fonts"]:
        try:
            f = load(p)
        except Exception:
            continue
        cm = f.getBestCmap()
        have = sum(ord(c) in cm for c in SCRIPTS[name]["letters"])
        if best is None or have > best[0]:
            best = (have, p, f)
        if have == len(SCRIPTS[name]["letters"]):
            break
    return best[1], best[2], best[0]


if __name__ == "__main__":
    for n in SCRIPTS:
        p, f, have = font_for(n)
        print(f"{n:11s} {have}/{len(SCRIPTS[n]['letters'])}  {p.split('/')[-1]}")
