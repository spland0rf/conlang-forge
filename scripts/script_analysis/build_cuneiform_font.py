"""Builds a measurement-only TrueType font from the Noto Sans Cuneiform UFO sources (notofonts/cuneiform, SIL OFL 1.1), so
the reference corpus can measure real cuneiform signs. Usage: python3 build_cuneiform_font.py <ufo glyphs dir> <out.ttf>.
Glyphs from this font are never copied into generated output."""
import re
import sys

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.pointPen import AbstractPointPen, PointToSegmentPen
from fontTools.pens.transformPen import TransformPointPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ufoLib.glifLib import GlyphSet

gs = GlyphSet(sys.argv[1])


class Wrap(AbstractPointPen):
    def __init__(s, out):
        s.out = out

    def beginPath(s, identifier=None, **kw):
        s.out.beginPath()

    def endPath(s):
        s.out.endPath()

    def addPoint(s, pt, segmentType=None, smooth=False, name=None, identifier=None, **kw):
        s.out.addPoint(pt, segmentType, smooth, name)

    def addComponent(s, base, transform, identifier=None, **kw):
        draw(base, TransformPointPen(s.out, transform))


def draw(n, out):
    gs.readGlyph(n, None, Wrap(out))


order = [".notdef"] + sorted(n for n in gs.keys() if re.fullmatch(r"u1[0-9A-Fa-f]{4}", n))
fb = FontBuilder(1000, isTTF=True)
fb.setupGlyphOrder(order)
fb.setupCharacterMap({int(n[1:], 16): n for n in order[1:]})
glyphs, metrics = {}, {}
for n in order:
    tp = TTGlyphPen(None)
    try:
        draw("_notdef" if n == ".notdef" else n, PointToSegmentPen(Cu2QuPen(tp, 1.0, reverse_direction=True)))
    except KeyError:
        pass
    glyphs[n] = tp.glyph()
    metrics[n] = (1000, 0)
fb.setupGlyf(glyphs)
fb.setupHorizontalMetrics(metrics)
fb.setupHorizontalHeader(ascent=800, descent=-200)
fb.setupNameTable({"familyName": "NotoSansCuneiformMeasure", "styleName": "Regular"})
fb.setupOS2()
fb.setupPost()
fb.save(sys.argv[2])
print(len(order), "glyphs")
