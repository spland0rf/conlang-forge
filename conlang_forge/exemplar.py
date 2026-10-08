"""Shaping a language from sample text.

The user pastes strings in the sound they want (made-up words, or real text from a language they like). Two readers look
at them:

* a phonology reader in plain code (no model): it spells the text back into sounds, splits it into syllables and counts
  consonants, vowels, syllable shapes, consonant clusters and word length;
* a grammar reader (the model, only when one is available): it guesses word order, endings and so on from the text.

Both only *propose*. Each proposal says which setting would change, from what to what, and why. The user approves them
(all at once or one by one) and the settings editor applies them. Nothing is changed silently.

Texts are written the way this app spells: sh ch th kh zh ng, plain a e i o u, and ae oe for the unusual vowels.
Accented letters (š č ö ü ä ë þ ŋ) are understood too.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter

from . import settings_schema as S
from .inventory import BASE_CONSONANTS, CONSONANTS, UNIT_DATA, UNIT_MAX, UNIT_PAIRS, UNITS, VOWELS, manner
from .spec import LanguageSpec

MAX_TEXTS, MAX_CHARS = 40, 3000

SPECIAL_PRE = {"ö": "ø", "ø": "ø", "ü": "y", "ë": "ə", "ə": "ə", "ä": "æ", "æ": "æ", "š": "ʃ", "ž": "ʒ", "č": "tʃ", "ǧ": "dʒ",
               "ŋ": "ŋ", "þ": "θ", "ð": "θ", "ʔ": "ʔ", "ʼ": "ʔ", "ñ": "n"}
DIGRAPHS = {"tz": ["ts"], "ch": ["tʃ"], "sh": ["ʃ"], "th": ["θ"], "kh": ["x"], "zh": ["ʒ"], "ng": ["ŋ"], "ph": ["f"], "ck": ["k"],
            "qu": ["k", "w"], "dj": ["dʒ"], "ae": ["æ"], "oe": ["ø"], "ee": ["i"], "oo": ["u"]}
SINGLES = {"b": ["b"], "c": ["k"], "d": ["d"], "f": ["f"], "g": ["g"], "h": ["h"], "j": ["dʒ"], "k": ["k"], "l": ["l"],
           "m": ["m"], "n": ["n"], "p": ["p"], "q": ["ʔ"], "r": ["r"], "s": ["s"], "t": ["t"], "v": ["v"], "w": ["w"],
           "x": ["k", "s"], "z": ["z"]}
PLAIN_VOWELS = "aeiou"


def _is_v(p):
    return p in VOWELS


def to_phonemes(word: str) -> list:
    """Spell a written word back into the sounds this app would use for it."""
    w = word.lower()
    out, i = [], 0
    chars = []
    for ch in w:
        if ch in SPECIAL_PRE:
            chars.append(("S", SPECIAL_PRE[ch]))
        else:
            base = "".join(c for c in unicodedata.normalize("NFD", ch) if ord(c) < 128)
            chars.extend(("L", c) for c in base)
    # chars: ("S", phoneme) already a sound, ("L", letter) to read
    j = 0
    while j < len(chars):
        kind, c = chars[j]
        if kind == "S":
            if c in CONSONANTS or c in VOWELS:
                out.append(c)
            j += 1
            continue
        nxt = chars[j + 1][1] if j + 1 < len(chars) and chars[j + 1][0] == "L" else ""
        pair = c + nxt
        if pair in DIGRAPHS:
            out += DIGRAPHS[pair]
            j += 2
            continue
        if c in PLAIN_VOWELS:
            out.append(c)
        elif c == "y":
            prev_v = bool(out) and _is_v(out[-1])
            nxt_v = nxt in PLAIN_VOWELS
            out.append("j" if (nxt_v and not prev_v) or not out else "i")
        elif c == "c" and nxt in ("e", "i", "y"):
            out.append("s")
        elif c in SINGLES:
            out += SINGLES[c]
        j += 1
    out = [p for p in out if p in CONSONANTS or p in VOWELS]
    return _merge_units(out)


def _merge_units(ph: list) -> list:
    """Read sequences such as ts, kp, zl or tbl as ONE consonant (a complex consonant) when they cannot be an ordinary
    consonant cluster, or when they sit at the START or the END of a word (so word-initial tl and word-final nd are
    units, but the nd of 'anda' is n + d). The longest match wins (tbl before tb)."""
    out, i, n = [], 0, len(ph)
    while i < n:
        hit = None
        for size in range(min(UNIT_MAX, n - i), 1, -1):
            seq = tuple(ph[i:i + size])
            u = UNIT_PAIRS.get(seq)
            if u is None or any(_is_v(p) for p in seq):
                continue
            edge = i == 0 or i + size == n
            legal = all(_onset_ok(a, b) or _coda_ok(a, b) for a, b in zip(seq, seq[1:]))
            if edge or not legal:
                hit = (u, size)
                break
        if hit:
            out.append(hit[0])
            i += hit[1]
        else:
            out.append(ph[i])
            i += 1
    return out


def words_of(text: str) -> list:
    return re.findall(r"[^\W\d_]+(?:['’ʼ][^\W\d_]+)*", text, flags=re.UNICODE)


def _onset_ok(a, b):
    return (manner(a) in ("stop", "fricative") and manner(b) in ("liquid", "glide") and a not in ("ʔ", "h")) or \
           (a == "s" and manner(b) == "stop" and b != "ʔ")


def _coda_ok(a, b):
    return (manner(a) in ("nasal", "liquid") or a == "s") and manner(b) == "stop" and b != "ʔ"


def syllabify(ph: list) -> list:
    """[(onset, nucleus, coda)] with maximal onsets; each vowel is its own nucleus."""
    nuclei = [i for i, p in enumerate(ph) if _is_v(p)]
    if not nuclei:
        return []
    sy, start = [], 0
    for n, vi in enumerate(nuclei):
        if n == 0:
            onset = ph[0:vi]
        else:
            onset = ph[start:vi]
        end = nuclei[n + 1] if n + 1 < len(nuclei) else len(ph)
        between = ph[vi + 1:end]
        if n + 1 < len(nuclei):
            k = min(len(between), 2)
            while k > 1 and not _onset_ok(between[-2], between[-1]):
                k -= 1
            coda = between[:len(between) - k]
            start = vi + 1 + len(coda)
        else:
            coda = between
        sy.append((onset, ph[vi], coda))
    return sy


def template_of(sy) -> str:
    on, _, co = sy
    return "C" * min(len(on), 2) + "V" + "C" * min(len(co), 2)


class PhonologyReport:
    """What the sample sounds like."""

    def __init__(self, texts: list):
        self.words = [w for t in texts for w in words_of(t)]
        self.cons, self.vows, self.templates = Counter(), Counter(), Counter()
        self.onsets, self.codas, self.coda_pairs = Counter(), Counter(), Counter()
        self.hiatus_words = self.sylls = self.max_run = self.skipped_clusters = 0
        counts = []
        for w in self.words:
            ph = to_phonemes(w)
            if not any(_is_v(p) for p in ph):
                continue
            for p in ph:
                (self.vows if _is_v(p) else self.cons)[p] += 1
            sy = syllabify(ph)
            counts.append(len(sy))
            self.sylls += len(sy)
            run = best = 0
            for p in ph:
                run = 0 if _is_v(p) else run + 1
                best = max(best, run)
            self.max_run = max(self.max_run, best)
            if any(_is_v(a) and _is_v(b) for a, b in zip(ph, ph[1:])):
                self.hiatus_words += 1
            for on, v, co in sy:
                self.templates[template_of((on, v, co))] += 1
                if len(on) >= 2:
                    pair = tuple(on[-2:])
                    if _onset_ok(*pair):
                        self.onsets[pair] += 1
                    else:
                        self.skipped_clusters += 1
                for c in co:
                    self.codas[c] += 1
                if len(co) >= 2:
                    pair = tuple(co[:2])
                    if _coda_ok(*pair):
                        self.coda_pairs[pair] += 1
                    else:
                        self.skipped_clusters += 1
        self.n_words = len(counts)
        self.mean_syllables = sum(counts) / len(counts) if counts else 0

    def size(self) -> str:
        n = sum(self.cons.values()) + sum(self.vows.values())
        return "high" if n >= 400 else "medium" if n >= 120 else "low"


def _tv(a: dict, b: dict) -> float:
    """Total variation distance between two share tables."""
    keys = set(a) | set(b)
    return .5 * sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys)


def _norm(d):
    t = sum(d.values()) or 1
    return {k: v / t for k, v in d.items()}


def _item(key, spec, proposed, why, conf, source="text", pinned=None):
    cur = S.spec_value(spec, key)
    cur_c = S._value_for_client(S.BY_KEY[key], cur)
    s = S.BY_KEY[key]
    prop = proposed
    return {"key": key, "label": s["label"], "group": s["group"], "current": cur_c, "proposed": prop,
            "current_show": S.show(key, cur), "proposed_show": S.show(key, S.clean_value(key, prop, {})),
            "kind": "conflict" if (pinned if pinned is not None else key in S.pins_of(spec)) else "drift",
            "confidence": conf, "evidence": why, "source": source}


def phonology_proposals(spec: LanguageSpec, rep: PhonologyReport, fresh: bool = False) -> list:
    """Settings the sample's sounds point to, where they differ from the language's present settings.
    `fresh`: the language is being made from the sample, so the sample's inventory replaces the random one (topped up
    to a workable minimum from the random one) instead of only adding to it."""
    out = []
    if rep.n_words < 3:
        return out
    conf = rep.size()
    ph = spec.phonology
    pins = S.pins_of(spec)

    def add(key, proposed, why):
        try:
            out.append(_item(key, spec, proposed, why, conf, pinned=key in pins))
        except Exception:
            pass

    ncons, nvow = sum(rep.cons.values()), sum(rep.vows.values())
    ph_base = [c for c in ph.consonants if c not in UNIT_DATA]
    big_c = ncons >= 150 or fresh
    # --- consonants (ordinary ones), complex consonants, vowels: the sample's sounds, topped up only as far as needed
    cons = [c for c in BASE_CONSONANTS if rep.cons[c] > 0 or (not big_c and c in ph_base)]
    units = [u for u in UNITS if rep.cons[u] >= 2 or (not big_c and u in ph.complex_consonants)]
    vows = [v for v in VOWELS if rep.vows[v] > 0 or not (nvow >= 80 or fresh) and v in ph.vowels]
    tmpl = ph.syllable_templates

    def enough():
        return len(cons) >= 4 and len(vows) >= S.MIN_VOWELS and S.feasible(len(cons) + len(units), len(vows), tmpl)

    pool_c = sorted((c for c in BASE_CONSONANTS if c not in cons), key=lambda c: (-ph.consonant_weights.get(c, 0), -CONSONANTS[c][3]))
    pool_v = sorted((v for v in VOWELS if v not in vows), key=lambda v: (-ph.vowel_weights.get(v, 0), -VOWELS[v][1]))
    while not enough() and (pool_c or pool_v):
        if len(vows) < S.MIN_VOWELS and pool_v or not pool_c:
            vows.append(pool_v.pop(0))
        elif len(cons) < 4 or len(cons) <= 2 * len(vows) or not pool_v:
            cons.append(pool_c.pop(0))
        else:
            vows.append(pool_v.pop(0))
    cons = [c for c in BASE_CONSONANTS if c in cons]
    vows = [v for v in VOWELS if v in vows]
    added = [c for c in cons if c not in ph_base]
    dropped = [c for c in ph_base if c not in cons]
    if added or dropped or fresh:
        bits = []
        if added:
            bits.append("the sample uses " + ", ".join(CONSONANTS[c][0] for c in added))
        if dropped:
            bits.append("the sample never uses " + ", ".join(CONSONANTS[c][0] for c in dropped))
        add("phonology.consonants", cons, "; ".join(bits) or "these are the consonants the sample uses")
    if units != list(ph.complex_consonants) and (units or ph.complex_consonants) or (fresh and units):
        add("phonology.complex_consonants", units,
            ("the sample treats " + ", ".join(CONSONANTS[u][0] for u in units) + " as single sounds") if units else
            "the sample has no sequences that act as single consonants")
    allc = [c for c in CONSONANTS if c in cons or c in units]
    prior = max(.5, ncons * .01)
    cw = _norm({c: rep.cons[c] + (prior if rep.cons[c] == 0 else 0) for c in allc})
    base = _norm({c: ph.consonant_weights.get(c, 0) for c in allc}) if any(c in ph.consonant_weights for c in allc) else {}
    if (added or dropped or _tv(cw, base) > .12) and ncons >= 20:
        top = sorted(cw.items(), key=lambda kv: -kv[1])[:3]
        add("phonology.consonant_weights", {c: round(w, 5) for c, w in cw.items()},
            "the commonest consonants in the sample are " + ", ".join(f"{CONSONANTS[c][0]} ({round(w * 100)}%)" for c, w in top))
    va = [v for v in vows if v not in ph.vowels]
    vd = [v for v in ph.vowels if v not in vows]
    if va or vd or fresh:
        bits = []
        if va:
            bits.append("the sample uses " + ", ".join(S.VOWEL_SPELLINGS[v][0] for v in va))
        if vd:
            bits.append("the sample never uses " + ", ".join(S.VOWEL_SPELLINGS[v][0] for v in vd))
        add("phonology.vowels", vows, "; ".join(bits) or "these are the vowels the sample uses")
    vw = _norm({v: rep.vows[v] + (max(.5, nvow * .01) if rep.vows[v] == 0 else 0) for v in vows})
    vbase = _norm({v: ph.vowel_weights.get(v, 0) for v in vows}) if any(v in ph.vowel_weights for v in vows) else {}
    if (va or vd or _tv(vw, vbase) > .12) and nvow >= 20:
        top = sorted(vw.items(), key=lambda kv: -kv[1])[:3]
        add("phonology.vowel_weights", {v: round(w, 5) for v, w in vw.items()},
            "the commonest vowels in the sample are " + ", ".join(f"{S.VOWEL_SPELLINGS[v][0]} ({round(w * 100)}%)" for v, w in top))
    # --- syllable shapes
    total = sum(rep.templates.values())
    if total >= 8:
        t = _norm({k: v for k, v in rep.templates.items() if k in S.TEMPLATES})
        cur_t = _norm(ph.syllable_templates)
        if total < 40:                                       # a small sample only nudges
            t = _norm({k: .5 * t.get(k, 0) + .5 * cur_t.get(k, 0) for k in set(t) | set(cur_t)})
        t = {k: round(v, 4) for k, v in t.items() if v >= .01}
        if t and _tv(t, cur_t) > .12:
            top = sorted(t.items(), key=lambda kv: -kv[1])[:3]
            add("phonology.syllable_templates", t, "common syllable shapes in the sample: " + ", ".join(f"{k} ({round(w * 100)}%)" for k, w in top))
    # --- clusters, codas
    on_all = {S.cluster_id(p) for p in S.candidate_clusters("onset", cons)}
    if rep.onsets:
        pairs = [list(p) for p, _ in rep.onsets.most_common() if S.cluster_id(p) in on_all]
        have = {S.cluster_id(p) for p in ph.onset_clusters}
        if pairs and {S.cluster_id(p) for p in pairs} - have:
            add("phonology.onset_clusters", sorted(pairs, key=lambda p: S.cluster_id(p)) if False else pairs,
                "the sample starts syllables with " + ", ".join("".join(CONSONANTS[c][0] for c in p) for p in pairs[:6]))
    if rep.codas:
        codas = [c for c in cons if rep.codas[c] > 0]
        if set(codas) - set(ph.coda_consonants):
            add("phonology.coda_consonants", codas, "the sample ends syllables with " + ", ".join(CONSONANTS[c][0] for c in codas[:8]))
        cc_all = {S.cluster_id(p) for p in S.candidate_clusters("coda", cons, codas)}
        pairs = [list(p) for p, _ in rep.coda_pairs.most_common() if S.cluster_id(p) in cc_all]
        if pairs and {S.cluster_id(p) for p in pairs} - {S.cluster_id(p) for p in ph.coda_clusters}:
            add("phonology.coda_clusters", pairs, "the sample ends syllables with pairs like " + ", ".join("".join(CONSONANTS[c][0] for c in p) for p in pairs[:5]))
    if rep.max_run and min(max(rep.max_run, 1), 4) != ph.max_cluster and rep.n_words >= 10:
        add("phonology.max_cluster", min(max(rep.max_run, 1), 4), f"the longest run of consonants in the sample is {rep.max_run}")
    # --- vowels side by side, word length
    share = rep.hiatus_words / max(rep.n_words, 1)
    if rep.n_words >= 10 and ((share >= .05) != ph.allow_hiatus):
        add("phonology.allow_hiatus", share >= .05,
            f"{round(share * 100)}% of the words in the sample have two vowels side by side")
    if rep.n_words >= 10:
        m = round(min(4.0, max(1.0, rep.mean_syllables)), 2)
        if abs(m - ph.mean_root_syllables) >= .3:
            add("phonology.mean_root_syllables", m, f"words in the sample average {round(rep.mean_syllables, 1)} syllables")
    return out


# ---------------------------------------------------------------------------------------------------- grammar (model)
GRAMMAR_KEYS = ["morphology.typology", "morphology.affix_position", "morphology.noun_number", "morphology.case_alignment",
                "morphology.definiteness", "morphology.verb_agreement", "morphology.negation", "syntax.word_order",
                "syntax.adposition", "syntax.adjective_order", "syntax.genitive_order", "syntax.relative_clause",
                "syntax.question_strategy", "syntax.pro_drop", "syntax.has_copula", "phonology.stress"]

SYSTEM = """You help shape an invented language. The user gives sample sentences or phrases (sometimes with an English \
meaning after a |). Judge which grammar settings the sample most plausibly implies. Answer with JSON only:
{"settings":[{"key":"...","value":<one of the allowed values>,"confidence":"high|medium|low","evidence":"one short sentence a \
non-linguist can follow"}]}
Only include settings the sample actually gives evidence for. Never invent evidence. If the sample gives no grammar \
evidence (for example a list of single words), answer {"settings":[]}."""


def grammar_prompt(texts: list) -> str:
    menu = []
    for k in GRAMMAR_KEYS:
        s = S.BY_KEY[k]
        vals = [o["value"] for o in s["options"]] if s["kind"] == "enum" else [True, False]
        menu.append(f'- {k} ({s["label"]}): ' + json.dumps(vals, ensure_ascii=False))
    return "Allowed settings and values:\n" + "\n".join(menu) + "\n\nSample:\n" + "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))


def parse_grammar(text: str, spec: LanguageSpec) -> list:
    m = re.search(r"\{.*\}", text or "", flags=re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return []
    pins, out = S.pins_of(spec), []
    for it in data.get("settings", []) if isinstance(data, dict) else []:
        if not isinstance(it, dict) or it.get("key") not in GRAMMAR_KEYS:
            continue
        key = it["key"]
        try:
            val = S.clean_value(key, it.get("value"), {})
        except Exception:
            continue
        if val == S.spec_value(spec, key):
            continue
        conf = it.get("confidence") if it.get("confidence") in ("high", "medium", "low") else "low"
        out.append(_item(key, spec, val, str(it.get("evidence", ""))[:240], conf, source="model", pinned=key in pins))
    return out


def clean_texts(raw) -> list:
    if isinstance(raw, str):
        raw = [ln for ln in raw.splitlines()]
    if not isinstance(raw, list):
        from .backend.errors import ValidationFailed
        raise ValidationFailed("texts must be a list of strings")
    from .backend.errors import ValidationFailed
    out = []
    for t in raw:
        if not isinstance(t, str):
            raise ValidationFailed("texts must be strings")
        t = t.strip()
        if t:
            out.append(t[:MAX_CHARS])
    if not out:
        raise ValidationFailed("Paste some sample text first.")
    if len(out) > MAX_TEXTS:
        raise ValidationFailed(f"Use at most {MAX_TEXTS} lines of sample text.")
    return out


def summary_of(rep: PhonologyReport) -> dict:
    return {"words": rep.n_words, "syllables": rep.sylls, "confidence": rep.size(), "mean_syllables": round(rep.mean_syllables, 2),
            "consonants": "".join(CONSONANTS[c][0] + " " for c, _ in rep.cons.most_common(12)).strip(),
            "vowels": " ".join(S.VOWEL_SPELLINGS[v][0] for v, _ in rep.vows.most_common()),
            "unmodelled_clusters": rep.skipped_clusters}
