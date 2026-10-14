"""Setting letters into text: composing an abugida syllable (letter + vowel sign + virama), spacing, topline and join
connections, word separators and direction."""
from __future__ import annotations

from ..wordgen import rng_for
from .geometry import bbox, shift, stroke
from .marks import place_part

GAP = 0.22          # space between letters that do not connect
WORD_GAP = 0.6


def _letters(script):
    return {l["id"]: l for l in script["letters"]}


def _signs(script):
    d = {s["id"]: s for s in script.get("signs", [])}
    if script.get("virama"):
        d["virama"] = script["virama"]
    return d


def compose(script, base, sign=None, virama=False):
    """A syllable's strokes, moved so its ink starts at x = 0, and its width. `sign` is a vowel id (or None for the
    inherent vowel); `virama` kills the inherent vowel."""
    letters, signs = _letters(script), _signs(script)
    g = letters[base]
    strokes = list(g["strokes"])
    extra = []
    for key in ([sign] if sign else []) + (["virama"] if virama and "virama" in signs else []):
        for slot, part in signs[key]["parts"].items():
            extra += place_part(strokes + extra, slot, part)
    strokes += extra
    x0, _, x1, _ = bbox(strokes)
    x0 = min(x0, 0.0)
    return shift(strokes, -x0), max(x1, g["width"]) - x0


def sample_words(script, n_words=6, seed_part="sample"):
    """Invented words (as lists of tokens) built from the script's own inventory."""
    rng = rng_for(script["spec"]["seed"], "script", seed_part)
    letters = script["letters"]
    cons = [l["id"] for l in letters if l["role"] == "consonant"]
    vows = [l["id"] for l in letters if l["role"] == "vowel"]
    signs = [s["id"] for s in script.get("signs", [])]
    kind = script["spec"]["kind"]
    words = []
    for _ in range(n_words):
        syl = rng.choice([2, 2, 3, 3, 4])
        word = []
        for k in range(syl):
            if signs or kind == "abjad":
                c = rng.choice(cons)
                v = rng.choice(signs + [None, None]) if signs else None
                virama = (not v) and k < syl - 1 and kind == "abugida" and "virama" in script and rng.random() < 0.2
                word.append(("syll", c, v, virama))
            else:
                word.append(("letter", rng.choice(cons)))
                if vows:
                    word.append(("letter", rng.choice(vows)))
        words.append(word)
    return words


def _item(script, tok):
    if tok[0] == "syll":
        return compose(script, tok[1], tok[2], tok[3])
    return compose(script, tok[1])


def set_text(script, words, end_mark="stop"):
    """Lay words out on a line. Returns (strokes, width). Right-to-left scripts run from the right edge; glyphs are
    repositioned, never mirrored. Letters of a topline or joined script are linked by a short connector."""
    spec = script["spec"]
    link_y = 1.0 if spec["topline"] == "bar" else (0.0 if spec["joining"] in ("baseline", "partial") else None)
    gap_in_word = 0.1 if link_y is not None else GAP
    joins = {l["id"]: l.get("joins", "both") for l in script["letters"]}
    partial = spec["joining"] == "partial" and spec["topline"] != "bar"
    items, x = [], 0.0                      # (strokes, x, advance) and connectors (x, length)
    links = []
    for wi, word in enumerate(words):
        if wi:
            if spec["word_separator"] == "dot":
                sep = script["punct"]["separator"]
                items.append((sep["strokes"], x + 0.1, 0.0))
                x += WORD_GAP * 0.5 + sep["width"]
            else:
                x += WORD_GAP if spec["word_separator"] == "space" else 0.25
        for ti, tok in enumerate(word):
            strokes, adv = _item(script, tok)
            if ti:
                a_id, b_id = word[ti - 1][1], tok[1]
                linked = link_y is not None and (not partial or (joins[a_id] == "both" and joins[b_id] in ("both", "prev")))
                if linked:
                    links.append((x, gap_in_word))
                x += gap_in_word if linked else GAP
            items.append((strokes, x, adv))
            x += adv
    if end_mark:
        p = script["punct"][end_mark]
        x += 0.15
        items.append((p["strokes"], x, p["width"]))
        x += p["width"]
    rtl = spec["direction"] == "rtl"
    out = []
    for strokes, ix, adv in items:
        out += shift(strokes, (x - ix - adv) if rtl else ix, 0)
    for lx, ln in links:
        a = (x - lx - ln) if rtl else lx
        out.append(dict(stroke([(a, link_y), (a + ln, link_y)]), k="m" if spec["corner_style"] == "smooth" else "b"))
    return out, x


def set_lines(script, words, max_width, end_mark="stop"):
    """Break words into lines no wider than max_width. Returns a list of (strokes, width)."""
    lines, cur = [], []
    for w in words:
        trial = cur + [w]
        if cur and set_text(script, trial, None)[1] > max_width:
            lines.append(cur)
            cur = [w]
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return [set_text(script, ln, end_mark if i == len(lines) - 1 else None) for i, ln in enumerate(lines)]
