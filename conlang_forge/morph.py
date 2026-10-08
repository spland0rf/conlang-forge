"""Per-language morphology table: relation affixes, root formatives, joining rules, rendering.

Sounds are split into two classes: grammatical (relation affixes, joining sounds across word and
compound boundaries) and lexical (formatives and sound changes inside a root), so a listener can tell a
within-word change from a grammatical one. Phoneme sequences are flat lists of IPA symbols. SPACE separates words inside a multi-word form
(used by analytic/isolating languages, where affixes are separate particles).

The relation-affix pool and the root-formative pool are kept disjoint and mutually distinguishable
(distance >= MIN_DIST) so a parser can always tell a grammatical affix from part of a root.
"""
from __future__ import annotations

from .infl_inventory import inventory as infl_inventory, position as infl_position
from .phonetics import MIN_DIST, pdist
from .relations import FREQUENCY_ORDER, PREFIX_LEANING, RELATIONS
from .wordgen import rng_for

SPACE = " "
N_FORMATIVES = 10


def is_analytic(spec) -> bool:
    return spec.morphology.affix_position == "none"


def _position(spec, rel: str) -> str:
    ap = spec.morphology.affix_position
    if ap == "prefixing":
        return "prefix"
    if ap == "suffixing":
        return "suffix"
    return "prefix" if rel in PREFIX_LEANING else "suffix"  # mixed, or particles in analytic languages


def split_sound_classes(spec) -> dict:
    """Split the inventory into a 'grammatical' class (affixes, joining sounds) and a 'lexical' class
    (changes inside a root: formatives, vowel/consonant swaps). Where the inventory is too small to give
    each class enough sounds, the classes overlap and `disjoint_*` is False."""
    ph = spec.phonology
    r = rng_for(spec.seed, "soundclass")

    def split(items, weights, frac, minside):
        if len(items) < 2 * minside:
            return list(items), list(items), False
        order = sorted(items, key=lambda x: weights[x] * r.uniform(.6, 1.4), reverse=True)
        k = max(minside, min(len(items) - minside, round(frac * len(items))))
        return order[:k], order[k:], True

    gc, lc, dc = split(ph.consonants, ph.consonant_weights, .55, 3)
    gv, lv, dv = split(ph.vowels, ph.vowel_weights, .5, 2)
    return {"grammatical": {"consonants": gc, "vowels": gv}, "lexical": {"consonants": lc, "vowels": lv},
            "disjoint_consonants": dc, "disjoint_vowels": dv}


def build_table(spec) -> dict:
    ph, typ = spec.phonology, spec.morphology.typology
    sc = split_sound_classes(spec)
    chosen: list = []

    def draw(key, shapes, cons, vows):
        cw = [ph.consonant_weights[c] for c in cons]
        vw = [ph.vowel_weights[v] for v in vows]
        coda = [c for c in ph.coda_consonants if c in cons] or list(ph.coda_consonants)
        for attempt in range(600):
            r = rng_for(spec.seed, key, attempt)
            if attempt < 120:
                pool = shapes
            elif attempt < 300:
                pool = [("CV", .5), ("V", .1), ("CVC", .2), ("VC", .2)]
            else:
                pool = [("CVCV", 1.0)]
            shape = r.choices([s for s, _ in pool], [w for _, w in pool])[0]
            seq = []
            for i, ch in enumerate(shape):
                if ch == "V":
                    seq.append(r.choices(vows, vw)[0])
                elif i == len(shape) - 1 and i > 0:
                    if not coda:
                        seq = None
                        break
                    seq.append(r.choices(coda, [ph.consonant_weights[c] for c in coda])[0])
                else:
                    seq.append(r.choices(cons, cw)[0])
            if seq is None:
                continue
            thr = MIN_DIST if attempt < 400 else 0.3
            if all(pdist(seq, c) >= thr for c in chosen):
                chosen.append(seq)
                return seq
        raise RuntimeError(f"cannot find a distinct morpheme for {key}")

    shapes = {"isolating": [("CV", 1.0)],
              "agglutinative": [("CV", .8), ("V", .2)],
              "fusional": [("V", .45), ("CV", .4), ("VC", .15)],
              "polysynthetic": [("CV", .8), ("V", .2)]}[typ]
    if is_analytic(spec):
        shapes = [("CV", 1.0)]
    g, l = sc["grammatical"], sc["lexical"]
    pref = ["j", "w", "h", "n", "r", "l", "ʔ", "m", "t", "s"]

    def link_c(pool):
        return next((c for c in pref if c in pool), max(pool, key=lambda c: ph.consonant_weights[c]))

    def link_v(pool):
        return max(pool, key=lambda v: ph.vowel_weights[v])

    # The joining consonants are reserved: no affix or formative contains them, so "link + affix" can
    # never be mistaken for a different affix.
    gl, ll = link_c(g["consonants"]), link_c(l["consonants"])
    g_cons = [c for c in g["consonants"] if c != gl] if len(g["consonants"]) > 2 else g["consonants"]
    l_cons = [c for c in l["consonants"] if c != ll] if len(l["consonants"]) > 2 else l["consonants"]
    drawn = {rel: draw(f"affix|{rel}", shapes, g_cons, g["vowels"]) for rel in FREQUENCY_ORDER}
    affixes = {rel: {"phonemes": drawn[rel], "position": _position(spec, rel)} for rel in RELATIONS}
    formatives = [draw(f"formative|{i}", [("CV", 1.0)], l_cons, l["vowels"]) for i in range(N_FORMATIVES)]

    # Inflectional morphemes (case, tense, agreement ...). Drawn after everything above, so adding them never
    # changes an affix or formative. Some reuse a derivational affix (plural, accusative, genitive).
    infl = {}
    for it in infl_inventory(spec):
        if it["reuse"]:
            a = affixes[it["reuse"]]
            infl[it["key"]] = {"phonemes": list(a["phonemes"]), "position": a["position"], "reuse": it["reuse"],
                               "category": it["category"], "gloss": it["gloss"]}
        else:
            infl[it["key"]] = {"phonemes": draw("infl|" + it["key"], shapes, g_cons, g["vowels"]),
                               "position": infl_position(spec, it["category"]), "reuse": None,
                               "category": it["category"], "gloss": it["gloss"]}

    return {"affixes": affixes, "formatives": formatives, "infl": infl, "sound_classes": sc,
            "link_consonant": gl, "link_vowel": link_v(g["vowels"]),
            "form_link_consonant": ll, "form_link_vowel": link_v(l["vowels"])}


def glue(spec, table: dict, left, right, kind: str = "form") -> list:
    """Concatenate two morphemes into one word, repairing the seam."""
    ph = spec.phonology
    V = set(ph.vowels)
    left, right = list(left), list(right)
    lc = table["form_link_consonant"] if kind == "form" else table["link_consonant"]
    lvw = table["form_link_vowel"] if kind == "form" else table["link_vowel"]
    lv, rv = left[-1] in V, right[0] in V
    if lv and rv:
        if ph.allow_hiatus:
            return left + right
        if kind == "affix" and spec.morphology.typology == "fusional" and len(left) > 1:
            elided = left[:-1] + right  # vowel elision, unless it would erase the affix entirely
            if elided != left:
                return elided
        return left + [lc] + right
    if not lv and not rv:
        t = 0
        for p in reversed(left):
            if p in V:
                break
            t += 1
        lead = 0
        for p in right:
            if p in V:
                break
            lead += 1
        if t + lead > ph.max_cluster:
            return left + [lvw] + right
    return left + right


def join(spec, table: dict, left, right, kind: str = "affix") -> list:
    """Join across a morpheme or compound boundary (separate words in analytic languages)."""
    if is_analytic(spec):
        return list(left) + [SPACE] + list(right)
    return glue(spec, table, left, right, kind)


def apply_relation(spec, table: dict, base, rel: str, kind: str = "affix") -> list:
    """kind="affix_noelide" disables vowel elision (used to break a collision between two derived words)."""
    a = table["affixes"][rel]
    if a["position"] == "prefix":
        return join(spec, table, a["phonemes"], base, kind)
    return join(spec, table, base, a["phonemes"], kind)


def valid_word(spec, w) -> bool:
    """Phonotactic check for a single word (no SPACE)."""
    ph = spec.phonology
    V = set(ph.vowels)
    n = len(w)
    if n == 0:
        return False
    tpl = list(ph.syllable_templates)
    has_coda = any(t.endswith("C") for t in tpl)
    has_cc_coda = any(t.endswith("CC") for t in tpl)
    has_cc_onset = any(t.startswith("CC") for t in tpl)
    has_v_init = any(t.startswith("V") for t in tpl)
    lead = 0
    while lead < n and w[lead] not in V:
        lead += 1
    if lead == n:
        return False
    if lead == 0 and not has_v_init:
        return False
    if lead > 2 or (lead == 2 and (not has_cc_onset or [w[0], w[1]] not in ph.onset_clusters)):
        return False
    trail = 0
    while trail < n and w[n - 1 - trail] not in V:
        trail += 1
    if trail:
        if not has_coda or trail > 2:
            return False
        if trail == 1 and w[-1] not in ph.coda_consonants:
            return False
        if trail == 2 and (not has_cc_coda or [w[-2], w[-1]] not in ph.coda_clusters):
            return False
    run = best = 0
    for p in w:
        run = 0 if p in V else run + 1
        best = max(best, run)
    return best <= ph.max_cluster


def syllabify_word(spec, w) -> list:
    ph = spec.phonology
    V = set(ph.vowels)
    onsets = {tuple(c) for c in ph.onset_clusters}
    nuc = [i for i, p in enumerate(w) if p in V]
    cuts = []
    for a, b in zip(nuc, nuc[1:]):
        run = w[a + 1:b]
        n_on = 2 if len(run) >= 2 and tuple(run[-2:]) in onsets else (1 if run else 0)
        cuts.append(b - n_on)
    out, prev = [], 0
    for c in cuts:
        out.append(list(w[prev:c]))
        prev = c
    out.append(list(w[prev:]))
    return out


def split_words(flat) -> list:
    words, cur = [], []
    for p in flat:
        if p == SPACE:
            words.append(cur)
            cur = []
        else:
            cur.append(p)
    words.append(cur)
    return words


def render_flat(spec, flat) -> tuple:
    """Return (romanized form, IPA string, syllables) for a flat phoneme list."""
    rom = spec.orthography.romanization
    n_stress = spec.phonology.stress
    forms, ipas, sylls = [], [], []
    for w in split_words(flat):
        forms.append("".join(rom[p] for p in w))
        sy = syllabify_word(spec, w)
        sylls.extend(sy)
        n = len(sy)
        mark = {"initial": 0, "final": n - 1, "penultimate": max(n - 2, 0), "none": None}[n_stress]
        ipas.append(".".join(("ˈ" if i == mark and n > 1 else "") + "".join(s) for i, s in enumerate(sy)))
    return " ".join(forms), "/" + " ".join(ipas) + "/", sylls
