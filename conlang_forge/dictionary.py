"""The two-way dictionary: English → conlang and conlang → English, as Markdown, CSV and plain rows.

What a user sees for each word:

    **abbey** *n.* — **shäz** /ˈʃæz/ · fem. · pl. uduzshe · cf. agriculture

* part of speech (see pos.py), noun gender, plural (and dual) forms, tense forms of verbs, gender agreement
  of adjectives. All of these are produced by the same Grammar engine that writes the grammar book, so a form in
  the dictionary is always the form the language really uses.
* how the word is built (root family, affix, compound, synonym) and its nearest relatives in the family.
* the language's own alphabet order: digraphs are letters of their own (sh follows s,
  ä follows a), and the conlang → English half is sorted and headed that way.

Nothing here uses an LLM. The rows are deterministic functions of (spec, state, vocabulary).
"""
from __future__ import annotations

import csv
import io
import unicodedata

from . import curriculum
from .grammar import Grammar, GrammarError
from .morph import render_flat
from .pos import ADJ, NAMES, NOUN, VERB, pos_of
from .relations import GLOSS

GENDER_ABBR = {"masculine": "masc.", "feminine": "fem.", "neuter": "neut.", "animate": "anim.", "inanimate": "inan."}


def _plain(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))


# ---------------------------------------------------------------------- the language's alphabet
def alphabet(spec) -> list:
    """The language's letters in dictionary order: each digraph is a letter of its own."""
    letters = sorted(set(spec.orthography.romanization[p] for p in spec.phonology.consonants + spec.phonology.vowels))
    return sorted(letters, key=lambda t: (_plain(t)[0], len(t) > 1, _plain(t), t != _plain(t), t))


class Sorter:
    def __init__(self, spec):
        self.letters = alphabet(spec)
        self.index = {t: i for i, t in enumerate(self.letters)}
        self.by_len = sorted(self.letters, key=len, reverse=True)

    def tokens(self, word: str) -> list:
        w, out, i = word.lower(), [], 0
        while i < len(w):
            for t in self.by_len:
                if w.startswith(t, i):
                    out.append(t)
                    i += len(t)
                    break
            else:
                out.append(w[i])
                i += 1
        return out

    def key(self, word: str):
        return [self.index.get(t, 1000 + ord(t[0])) for t in self.tokens(word)]

    def initial(self, word: str) -> str:
        t = self.tokens(word)
        return t[0] if t else "#"


# ---------------------------------------------------------------------- rows
def _readable_recipe(e: dict, gloss_of: dict) -> str | None:
    r = e.get("recipe")
    if not r:
        return None
    if " | " in r:
        return " + ".join(r.split(" | "))
    if r.endswith(" +SAME"):
        return "same as " + r.split(" +")[0]
    base, _, rel = r.partition(" +")
    return f"{base} + {rel}" if rel else r


def build_rows(spec, state: dict, vocab) -> list:
    """One dict per dictionary entry (bound roots are left out)."""
    g = Grammar(spec, state, vocab)
    g.set_semantics(curriculum.semantics())
    rel_of = {}
    for e in state["entries"]:
        r = e.get("recipe") or ""
        if " +" in r and not r.endswith("+SAME"):
            rel_of[e["concept_id"]] = r.rsplit("+", 1)[1]
    entries = [e for e in state["entries"] if e["kind"] != "bound"]
    live = {e["concept_id"]: e for e in entries if not e["retired"]}
    fam = {}
    for e in live.values():
        if e["family"] and e["kind"] in ("head", "family"):
            fam.setdefault(e["family"], []).append(e)
    derived_from = {}
    for e in live.values():
        r = e.get("recipe") or ""
        if e["kind"] == "derived" and " +" in r:
            derived_from.setdefault(r.split(" +")[0], []).append(e)
    tense_keys = [k for k in g.infl if k.startswith("tense:")]
    genders = [x for x in spec.morphology.genders if f"gender:{x}" in g.infl]
    rows = []
    for e in entries:
        cid = e["concept_id"]
        pos = pos_of(cid, e["lemma"], rel_of.get(cid))
        row = {"concept_id": cid, "gloss": e["gloss"], "lemma": e["lemma"], "form": e["form"], "ipa": e["ipa"],
               "pos": pos, "gender": None, "plural": None, "dual": None, "tenses": {}, "agreement": {},
               "derivation": _readable_recipe(e, {}), "family": e["family"], "kind": e["kind"],
               "related": [], "retired": e["retired"], "is_function": e["is_function"], "added_in": e["added_in"]}
        if not e["retired"]:
            try:
                if NOUN in pos and genders:
                    row["gender"] = g.gender_of(cid)
                if NOUN in pos and "number:plural" in g.infl:
                    row["plural"] = g.render(g.word(cid, ["number:plural"]))[0]
                if NOUN in pos and "number:dual" in g.infl:
                    row["dual"] = g.render(g.word(cid, ["number:dual"]))[0]
                if VERB in pos:
                    for k in tense_keys:
                        row["tenses"][k.split(":")[1]] = g.render(g.word(cid, [k]))[0]
                if ADJ in pos and genders and not g.analytic:
                    forms = {x: g.render(g.word(cid, [f"gender:{x}"]))[0] for x in genders}
                    row["agreement"] = forms
            except GrammarError:
                pass
            rel = []
            if e["family"] and e["kind"] in ("head", "family"):
                rel = [x for x in fam.get(e["family"], []) if x["concept_id"] != cid]
            else:
                base = (e.get("recipe") or "").split(" +")[0]
                if e["kind"] == "derived" and base in live:
                    rel = [live[base]] + [x for x in derived_from.get(base, []) if x["concept_id"] != cid]
            if e["kind"] in ("head", "family") and cid in derived_from:
                rel += derived_from[cid]
            row["related"] = [(x["gloss"], x["form"]) for x in rel[:6]]
        rows.append(row)
    return rows


# ---------------------------------------------------------------------- Markdown
def _pos_label(row) -> str:
    return "/".join(p.rstrip(".") + "." for p in row["pos"][:2])


def _details(row, *, english_side: bool) -> str:
    bits = []
    if row["gender"]:
        bits.append(GENDER_ABBR.get(row["gender"], row["gender"]))
    if row["dual"]:
        bits.append(f"du. {row['dual']}")
    if row["plural"]:
        bits.append(f"pl. {row['plural']}")
    for t, f in row["tenses"].items():
        bits.append(f"{t} {f}")
    ag = row["agreement"]
    if ag and len(set(ag.values())) > 1:
        bits.append(" / ".join(f"{GENDER_ABBR.get(k, k)} {v}" for k, v in ag.items()))
    if row["derivation"]:
        bits.append(f"← {row['derivation']}")
    if row["related"]:
        bits.append("cf. " + ", ".join(f"{f} ({g})" for g, f in row["related"][:4]))
    return "".join(f" · {b}" for b in bits)


def dictionary_markdown_full(spec, state: dict, vocab, vocab_version: str, rows: list | None = None) -> str:
    rom, table = spec.orthography.romanization, state["table"]
    rows = rows or build_rows(spec, state, vocab)
    live = [r for r in rows if not r["retired"]]
    st = Sorter(spec)
    g = Grammar(spec, state, vocab)
    sc = table["sound_classes"]
    name = spec.name
    L = [f"# {name} Dictionary", "",
         f"Reduced English vocabulary v{vocab_version} · {len(live)} words"
         + (f" · {len(rows) - len(live)} retired (†)" if len(live) != len(rows) else ""), ""]

    # ---- how to read an entry
    ex = next((r for r in live if r["pos"][0] == NOUN and r["plural"]), None) or next(r for r in live)
    L += ["## How to use this dictionary", "",
          "Each half is in alphabetical order. The English half gives the word in this language; the "
          f"{name} half gives the meaning of a {name} word. After the word and its pronunciation come the part of "
          "speech and whatever the word needs to be used correctly: the gender of a noun, its plural, the tense "
          "forms of a verb, the agreement forms of an adjective, how the word was built, and close relatives "
          "(*cf.*).", "",
          f"> **{ex['gloss']}** *{_pos_label(ex)}* — **{ex['form']}** {ex['ipa']}{_details(ex, english_side=True)}", "",
          "| Abbreviation | Meaning |", "|---|---|"]
    used = sorted({p for r in live for p in r["pos"]}, key=lambda p: list(NAMES).index(p))
    L += [f"| *{p}* | {NAMES[p]} |" for p in used]
    extra = [("masc. / fem. / neut.", "gender of a noun (masculine, feminine, neuter)"),
             ("anim. / inan.", "animate / inanimate noun")]
    L += [f"| {a} | {b} |" for a, b in extra if any(r["gender"] and GENDER_ABBR.get(r["gender"]) in a for r in live)]
    L += ["| du. / pl. | dual / plural form of a noun |"] if any(r["dual"] for r in live) else []
    L += ["| pl. | plural form of a noun |"] if not any(r["dual"] for r in live) and any(r["plural"] for r in live) else []
    L += ["| *cf.* | related words from the same root family |", "| ← | how the word is built (see Word formation) |",
          "| † | retired word, kept so that old texts stay readable |", ""]

    # ---- alphabet and pronunciation
    ipa_of = {}
    for p in spec.phonology.consonants + spec.phonology.vowels:
        ipa_of.setdefault(rom[p], p)
    L += ["## Alphabet and pronunciation", "",
          f"{name} is written with {len(st.letters)} letters, listed here in dictionary order. A digraph (two "
          "letters, one sound) counts as one letter and has its own heading in the "
          f"{name}→English half.", "",
          "| Letter | IPA | | Letter | IPA |", "|---|---|---|---|---|"]
    half = (len(st.letters) + 1) // 2
    for i in range(half):
        a = st.letters[i]
        b = st.letters[i + half] if i + half < len(st.letters) else None
        L.append(f"| **{a}** | /{ipa_of[a]}/ | | " + (f"**{b}** | /{ipa_of[b]}/ |" if b else " | |"))
    L += ["", f"Stress: {spec.phonology.stress}.", ""]

    # ---- inflection reference
    if g.infl:
        L += ["## Endings and particles", "",
              "Every overt marker the language uses on nouns, verbs and adjectives. The dictionary lists the "
              "resulting plural, tense and agreement forms for each word; the Grammar Book explains when to use them.",
              "", "| Category | Value | Marker | Where it goes |", "|---|---|---|---|"]
        analytic = g.analytic
        for key, it in g.infl.items():
            cat, _, val = key.partition(":")
            form = render_flat(spec, it["phonemes"])[0]
            pos = it["position"]
            where = ({"prefix": "particle before the word", "suffix": "particle after the word"}[pos] if analytic
                     else {"prefix": "prefix", "suffix": "suffix"}[pos])
            shown = f"{form}-" if (pos == "prefix" and not analytic) else (f"-{form}" if not analytic else form)
            L.append(f"| {cat} | {val or '—'} | **{shown}** *({it['gloss']})* | {where} |")
        L.append("")

    # ---- word formation (as before)
    L += ["## Word formation", "",
          "Related words are built from shared roots by regular rules. Two separate groups of sounds keep "
          "the rules apart: **grammatical sounds** appear only in the affixes below, and **lexical sounds** "
          "appear only in changes made inside a root.", "",
          f"- Grammatical sounds: {' '.join(rom[p] for p in sc['grammatical']['consonants'] + sc['grammatical']['vowels'])}",
          f"- Lexical sounds: {' '.join(rom[p] for p in sc['lexical']['consonants'] + sc['lexical']['vowels'])}", "",
          "### Derivation affixes", "", "| Relation | Form | Meaning |", "|---|---|---|"]
    from .export import _fmt_affix
    L += [f"| {rel} | {_fmt_affix(spec, a)} | {GLOSS[rel]} |" for rel, a in table["affixes"].items()]
    base = spec.morphology.gender_base
    other = "MALE" if base == "female" else "FEMALE"
    ent = {r["concept_id"]: r for r in rows}
    pair = {"male": ("king", "queen"), "female": ("queen", "king")}[base]
    if all(p in ent for p in pair):
        L += ["", f"**Gender pairs.** In {name} the {base} term of a pair is the plain root and the other is made "
                  f"with the {other} affix: {ent[pair[0]]['form']} ({pair[0]}) → {ent[pair[1]]['form']} ({pair[1]}).", ""]
    fm = ", ".join(render_flat(spec, f)[0] for f in table["formatives"])
    L += ["### Root formatives", "", f"Short endings or beginnings used to tell members of a root family apart: {fm}.", ""]

    # ---- root families
    L += ["### Root families", "",
          "Each family shares one stem syllable (or more). The head word is the bare stem; the other members "
          "are the stem with one change.", ""]
    by_fam = {}
    for r in live:
        if r["family"] and r["kind"] in ("head", "family"):
            by_fam.setdefault(r["family"], []).append(r)
    for fam, rs in sorted(by_fam.items()):
        s = state["stems"].get(fam)
        if not s:
            continue
        sib = f" (sibling of {s['sibling_of']})" if s.get("sibling_of") else ""
        L.append(f"- **{render_flat(spec, s['phonemes'])[0]}** — {fam}{sib}: "
                 + ", ".join(f"{r['gloss']} *{r['form']}*" for r in rs))

    # ---- English -> conlang
    mark = lambda r: " †" if r["retired"] else ""
    L += ["", "---", "", f"## English → {name}", ""]
    eng = sorted(rows, key=lambda r: (_plain(r["gloss"]), r["concept_id"]))
    letters = sorted({(_plain(r["gloss"])[:1] or "#").upper() for r in eng})
    L += [" · ".join(f"[{c}](#english-{c.lower()})" for c in letters), ""]
    cur = None
    for r in eng:
        ini = (_plain(r["gloss"])[:1] or "#").upper()
        if ini != cur:
            cur = ini
            L += ["", f'<a id="english-{ini.lower()}"></a>', f"### {ini}", ""]
        L.append(f"- **{r['gloss']}** *{_pos_label(r)}* — **{r['form']}** {r['ipa']}{_details(r, english_side=True)}{mark(r)}")

    # ---- conlang -> English
    L += ["", "---", "", f"## {name} → English", ""]
    con = sorted(rows, key=lambda r: (st.key(r["form"]), r["concept_id"]))
    heads = []
    for r in con:
        i = st.initial(r["form"])
        if i not in heads:
            heads.append(i)
    L += [" · ".join(f"[{h.capitalize()}](#c{st.index.get(h, 0)})" for h in heads), ""]
    cur = None
    for r in con:
        ini = st.initial(r["form"])
        if ini != cur:
            cur = ini
            L += ["", f'<a id="c{st.index.get(ini, 0)}"></a>', f"### {ini.capitalize()} {ini}", ""]
        L.append(f"- **{r['form']}** {r['ipa']} *{_pos_label(r)}"
                 + (f" {GENDER_ABBR.get(r['gender'], r['gender'])}" if r["gender"] else "") + f"* — {r['gloss']}"
                 + ("".join(f" · {b}" for b in _reverse_bits(r))) + mark(r))
    return "\n".join(L) + "\n"


def _reverse_bits(r) -> list:
    """The conlang → English half stays short: meaning, how the word is built, close relatives."""
    bits = []
    if r["derivation"]:
        bits.append(f"← {r['derivation']}")
    if r["related"]:
        bits.append("cf. " + ", ".join(f"{f} ({g})" for g, f in r["related"][:3]))
    return bits


# ---------------------------------------------------------------------- CSV / JSON
CSV_COLUMNS = ["english", "conlang", "ipa", "pos", "gender", "plural", "dual", "tense_forms", "derivation",
               "family", "concept_id", "is_function", "retired", "added_in"]


def dictionary_csv_full(rows: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_COLUMNS)
    for r in sorted(rows, key=lambda r: (_plain(r["gloss"]), r["concept_id"])):
        w.writerow([r["gloss"], r["form"], r["ipa"], "/".join(r["pos"]), r["gender"] or "", r["plural"] or "",
                    r["dual"] or "", "; ".join(f"{k}={v}" for k, v in r["tenses"].items()), r["derivation"] or "",
                    r["family"] or "", r["concept_id"], r["is_function"], r["retired"], r["added_in"]])
    return buf.getvalue()
