"""Writing a language's text in a writing system: spelling -> sounds -> the script's letters (closest fit) -> SVG.

The script need not have been designed for the language. Each sound the script lacks is written with its closest
available sound (see sounds.py) and the report says which ones, so the reader knows the rendering is approximate."""
from __future__ import annotations

import re

from .layout import set_lines
from .render import strokes_svg
from .sounds import closest, is_consonant

TOKEN = re.compile(r"[^\W\d_]+(?:['’ʼ][^\W\d_]+)*|\d+|[.!?;:,]")
LINE_HEIGHT = 2.7


def inventory_of(script: dict) -> tuple[list, list]:
    """(consonants, vowels) the script has letters or signs for, as ipa strings."""
    letters = script["letters"]
    cons = [l["id"] for l in letters if l["role"] == "consonant"]
    if script.get("signs"):
        vows = [s["id"] for s in script["signs"]]
    else:
        vows = [l["id"] for l in letters if l["role"] == "vowel"]
    return cons, vows


def to_sounds(word: str, romanization: dict | None) -> list:
    """Read a written word of the language into its sounds, longest spelling first."""
    from ..exemplar import to_phonemes
    w = word.lower().replace("’", "'")
    rev = {}
    for ipa, sp in (romanization or {}).items():
        rev.setdefault(str(sp).lower(), ipa)
    longest = max((len(k) for k in rev), default=1)
    out, i = [], 0
    while i < len(w):
        for n in range(min(longest, len(w) - i), 0, -1):
            hit = rev.get(w[i:i + n])
            if hit:
                out.append(hit)
                i += n
                break
        else:
            if w[i] != "'":
                out += to_phonemes(w[i])
            i += 1
    return out


def _carrier(script, cons) -> str:
    ids = {l["id"] for l in script["letters"]}
    for c in ("ʔ", "h"):
        if c in ids:
            return c
    return cons[0] if cons else script["letters"][0]["id"]


def write_word(script: dict, sounds: list, used: dict) -> list:
    """The tokens (see layout.set_text) that write a word's sounds. `used` collects how each distinct sound was matched."""
    cons, vows = inventory_of(script)
    steps = []
    for s in sounds:
        m = closest(s, cons, vows)
        if s not in used:
            used[s] = m
        steps += m["to"]
    kind = script["spec"]["kind"]
    signs = {x["id"] for x in script.get("signs", [])}
    ids = {l["id"] for l in script["letters"]}
    if not signs and kind != "alphabet":                     # a bare abjad leaves the vowels out
        letters = [x for x in steps if x in ids and is_consonant(x)]
        return [("letter", x) for x in (letters or [_carrier(script, cons)])]
    if kind == "alphabet" or not signs:
        return [("letter", x) for x in steps if x in ids]
    carrier, has_virama = _carrier(script, cons), bool(script.get("virama"))
    out, i = [], 0
    while i < len(steps):
        x = steps[i]
        if x in signs and not (x in ids and is_consonant(x)):           # a vowel with no consonant before it
            out.append(("syll", carrier, x, False))
            i += 1
        elif i + 1 < len(steps) and steps[i + 1] in signs and not (steps[i + 1] in ids and is_consonant(steps[i + 1])):
            out.append(("syll", x, steps[i + 1], False))
            i += 2
        else:
            out.append(("syll", x, None, has_virama))
            i += 1
    return out


def split_sentences(text: str) -> list:
    """[(items, end)] where items are ("w", word) / ("n", digits) / ("c",) and end is "stop", "question" or None."""
    sents, cur = [], []
    for m in TOKEN.finditer(text or ""):
        t = m.group()
        if t in ".!?":
            if cur:
                sents.append((cur, "question" if t == "?" else "stop"))
            cur = []
        elif t in ",;:":
            if cur:
                cur.append(("c",))
        elif t.isdigit():
            cur.append(("n", t))
        else:
            cur.append(("w", t))
    if cur:
        sents.append((cur, None))
    return sents


def render_text(script: dict, text: str, romanization: dict | None, own_fold: dict | None = None,
                scale: float = 48.0, max_width: float = 15.0) -> dict:
    """Write `text` (the language's own spelling) in `script`. Returns the lines as SVG plus a report of every sound that
    had to be approximated."""
    from ..plain import fold
    used, out, every = {}, [], []
    spec = script["spec"]
    has_digits = bool(script.get("digits"))
    for items, end in split_sentences(fold(text or "", own_fold)):
        words, shown = [], []
        for it in items:
            if it[0] == "w":
                snd = to_sounds(it[1], romanization)
                toks = write_word(script, snd, used) if snd else []
                if toks:
                    words.append(toks)
                    shown.append(it[1])
            elif it[0] == "n" and has_digits:
                words.append([("digit", d) for d in it[1] if any(x["id"] == d for x in script["digits"])])
                shown.append(it[1])
            elif it[0] == "c":
                words.append([("punct", "comma")])
        words = [w for w in words if w]
        if not words:
            continue
        lines = set_lines(script, words, max_width, end)
        every += lines
        out.append({"text": " ".join(shown), "svg": _svg(lines, spec, scale, max_width)})
    # one picture of all sentences, on white, for showing and downloading
    return {"sentences": out, "svg": _svg(every, spec, scale, max_width, background=True) if every else "",
            "approximations": _report(used)}


def _svg(lines, spec, scale, max_width, background=False):
    W = max([w for _, w in lines] + [3.0]) + 0.8
    H = len(lines) * LINE_HEIGHT + 0.3
    body = []
    for i, (strokes, w) in enumerate(lines):
        ox = (W - 0.4 - w) if spec["direction"] == "rtl" else 0.4
        body.append(strokes_svg(strokes, spec["roundness"], scale, ox, 2.15 + i * LINE_HEIGHT))
    bg = '<rect width="100%" height="100%" fill="#fff"/>' if background else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * scale:.0f}" height="{H * scale:.0f}" '
            f'viewBox="0 0 {W * scale:.0f} {H * scale:.0f}">{bg}{"".join(body)}</svg>')


def _report(used: dict) -> list:
    rows = [{"sound": s, "written_as": m["to"], "exact": m["exact"], "how": m["how"]}
            for s, m in used.items() if not m["exact"]]
    return sorted(rows, key=lambda r: r["sound"])


def coverage(script: dict, consonants: list, vowels: list) -> dict:
    """Which of a language's sounds this script writes exactly, and how it writes the others."""
    cons, vows = inventory_of(script)
    rows, exact = [], 0
    for p in list(consonants) + list(vowels):
        m = closest(p, cons, vows)
        exact += m["exact"]
        if not m["exact"]:
            rows.append({"sound": p, "written_as": m["to"], "how": m["how"]})
    total = len(consonants) + len(vowels)
    return {"exact": exact, "total": total, "approximate": rows}

