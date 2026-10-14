"""Writing-system generator: seeded, deterministic glyph inventories described as stroke graphs (see docs/script-design.md)."""
from .generate import generate
from .layout import compose, sample_words, set_text
from .render import sheet_svg, text_svg

__all__ = ["generate", "compose", "sample_words", "set_text", "sheet_svg", "text_svg"]
