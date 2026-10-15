"""Draw the app icon (the Ekki Potak glyph: a ring with a dot, two bars, a stem and a hook) in every size the web, Android and
iOS need. The glyph is drawn once as SVG, with thicker strokes and a squarer outline than the original so it reads at small
sizes; PNGs are rasterised with Chromium (Playwright). Run: python scripts/make_icons.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PURPLE = "#6A3FC8"
WHITE = "#FFFFFF"
# glyph in its own units, centred on (0, 0); strokes are 11 wide with round caps
GLYPH = ('<g fill="none" stroke="{c}" stroke-width="13" stroke-linecap="round" stroke-linejoin="round">'
         '<ellipse cx="0" cy="6" rx="34" ry="27"/>'
         '<path d="M-47 -21H47M-47 33H47M0 33V51"/>'
         '<path d="M-14 -56V-47Q-14 -39 -6 -39H10"/></g>'
         '<circle cx="0" cy="6" r="9.5" fill="{c}"/>')
CENTER_Y = -2.5          # the glyph's vertical middle (it runs from about -62 to 57)
HEIGHT = 121.0           # the glyph's height in glyph units, stroke ends included


def svg(size: int, scale: float, background: str | None, radius: float = 0.0, color: str = WHITE) -> str:
    """A square icon `size` px wide with the glyph scaled by `scale` (px per glyph unit), on `background` or transparent."""
    bg = f'<rect width="{size}" height="{size}" rx="{radius * size}" fill="{background}"/>' if background else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">{bg}'
            f'<g transform="translate({size / 2} {size / 2 - CENTER_Y * scale}) scale({scale})">{GLYPH.format(c=color)}</g></svg>')


def main() -> None:
    from playwright.sync_api import sync_playwright
    web = ROOT / "conlang_forge/web/static"
    store = ROOT / "mobile/store/icons"
    assets = ROOT / "mobile/assets"
    (web / "favicon.svg").write_text(svg(64, 64 * 0.78 / HEIGHT, PURPLE, 0.22))
    # (file, pixel size, share of the size the glyph's height fills, background, corner radius)
    jobs = [
        (assets / "icon.png", 1024, 0.76, PURPLE, 0),                     # iOS and Expo: opaque square, the system rounds it
        (assets / "adaptive-icon.png", 1024, 0.58, None, 0),              # Android foreground: well inside the central 66% (circle-safe)
        (assets / "splash-icon.png", 1024, 0.5, None, 0),
        (ROOT / "mobile/store/play-icon-512.png", 512, 0.76, PURPLE, 0),
        (web / "icon-512.png", 512, 0.72, PURPLE, 0),
        (web / "icon-192.png", 192, 0.72, PURPLE, 0),
        (web / "apple-touch-icon.png", 180, 0.74, PURPLE, 0),             # iOS home screen: opaque
        (web / "favicon-32.png", 32, 0.8, PURPLE, 0.18),
        (web / "favicon-16.png", 16, 0.84, PURPLE, 0.18),
    ]
    for px in (48, 72, 96, 144, 192):                                     # Android launcher sizes: mdpi .. xxxhdpi, square and round
        jobs += [(store / f"android-{px}.png", px, 0.72, PURPLE, 0.18), (store / f"android-round-{px}.png", px, 0.62, PURPLE, 0.5)]
    for px in (20, 29, 40, 58, 60, 76, 80, 87, 120, 152, 167, 180, 1024):  # iOS AppIcon sizes (opaque; iOS applies the corners)
        jobs.append((store / f"ios-{px}.png", px, 0.76, PURPLE, 0))
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        for path, size, frac, bg, radius in jobs:
            scale = size * frac / HEIGHT
            page.set_viewport_size({"width": size, "height": size})
            page.set_content(f'<body style="margin:0;background:transparent">{svg(size, scale, bg, radius)}</body>')
            page.screenshot(path=str(path), omit_background=True, clip={"x": 0, "y": 0, "width": size, "height": size})
        b.close()
    print(f"wrote {len(jobs) + 1} icons")


if __name__ == "__main__":
    sys.exit(main())
