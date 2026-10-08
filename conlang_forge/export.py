"""Dictionary exports (Markdown / CSV) and a short spec summary. No LLM involved."""
from __future__ import annotations

import csv
import io
import unicodedata

from .inventory import CONSONANTS, VOWELS


def _sort_key(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))


def _initial(s: str) -> str:
    return (_sort_key(s)[:1] or "#").upper()


def summarize_spec(spec) -> str:
    ph, m, sy = spec.phonology, spec.morphology, spec.syntax
    rom = spec.orthography.romanization
    top = sorted(ph.consonant_weights, key=ph.consonant_weights.get, reverse=True)[:5]
    return "\n".join([
        f"{spec.name}  (seed {spec.seed})",
        f"  typology:   {m.typology} (synthesis index {m.synthesis_index}), affixes: {m.affix_position}",
        f"  word order: {sy.word_order}, {sy.adposition}s, {sy.adjective_order}, {sy.genitive_order}",
        f"  phonemes:   {len(ph.consonants)} consonants, {len(ph.vowels)} vowels; common: "
        + " ".join(f"{rom[c]}" for c in top),
        f"  syllables:  {'/'.join(ph.syllable_templates)}, stress {ph.stress}, mean root {ph.mean_root_syllables} syll",
        f"  gender:     {m.gender_base} term of each pair is the unmarked root",
        f"  cases:      {len(m.cases)}, genders: {len(m.genders)}, tenses: {len(m.tenses)}, agreement: {m.verb_agreement}",
    ])


def dictionary_markdown(spec, lexicon: list, vocab_version: str) -> str:
    rom = spec.orthography.romanization
    live = [e for e in lexicon if not e["retired"]]
    lines = [f"# {spec.name} Dictionary", "",
             f"Reduced English vocabulary v{vocab_version} · {len(live)} words"
             + (f" · {len(lexicon) - len(live)} retired (†)" if len(live) != len(lexicon) else ""), "",
             "## Pronunciation guide", "", "| Letter | IPA |", "|---|---|"]
    for p in spec.phonology.consonants + spec.phonology.vowels:
        lines.append(f"| {rom[p]} | /{p}/ |")
    lines += ["", f"Stress: {spec.phonology.stress}.", "", "---", "", f"## English → {spec.name}", ""]

    def section(items, key, fmt):
        cur = None
        for e in sorted(items, key=lambda e: _sort_key(key(e))):
            ini = _initial(key(e))
            if ini != cur:
                cur = ini
                lines.extend(["", f"### {ini}", ""])
            lines.append(fmt(e))
    mark = lambda e: " †" if e["retired"] else ""
    section(lexicon, lambda e: e["gloss"],
            lambda e: f"- **{e['gloss']}** — {e['form']} {e['ipa']}{mark(e)}")
    lines += ["", "---", "", f"## {spec.name} → English", ""]
    section(lexicon, lambda e: e["form"],
            lambda e: f"- **{e['form']}** {e['ipa']} — {e['gloss']}{mark(e)}")
    return "\n".join(lines) + "\n"


def dictionary_csv(lexicon: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["english", "conlang", "ipa", "concept_id", "is_function", "retired", "added_in"])
    for e in sorted(lexicon, key=lambda e: _sort_key(e["gloss"])):
        w.writerow([e["gloss"], e["form"], e["ipa"], e["concept_id"], e["is_function"],
                    e["retired"], e["added_in"]])
    return buf.getvalue()


# ---------------------------------------------------------------------- root-based languages (format /2)
def _fmt_affix(spec, a) -> str:
    from .morph import render_flat
    form = render_flat(spec, a["phonemes"])[0]
    if spec.morphology.affix_position == "none":
        return f"{form} (particle, {'before' if a['position'] == 'prefix' else 'after'} the word)"
    return f"{form}-" if a["position"] == "prefix" else f"-{form}"


def dictionary_markdown_v2(spec, state: dict, vocab_version: str) -> str:
    from .morph import render_flat
    from .relations import GLOSS
    rom, table = spec.orthography.romanization, state["table"]
    entries = [e for e in state["entries"] if e["kind"] != "bound"]
    live = [e for e in entries if not e["retired"]]
    sc = table["sound_classes"]
    L = [f"# {spec.name} Dictionary", "",
         f"Reduced English vocabulary v{vocab_version} · {len(live)} words"
         + (f" · {len(entries) - len(live)} retired (†)" if len(live) != len(entries) else ""), "",
         "## Pronunciation guide", "", "| Letter | IPA |", "|---|---|"]
    L += [f"| {rom[p]} | /{p}/ |" for p in spec.phonology.consonants + spec.phonology.vowels]
    L += ["", f"Stress: {spec.phonology.stress}.", "", "## Word formation", "",
          "Related words are built from shared roots by regular rules. Two separate groups of sounds keep "
          "the rules apart: **grammatical sounds** appear only in the affixes below, and **lexical sounds** "
          "appear only in changes made inside a root.", "",
          f"- Grammatical sounds: {' '.join(rom[p] for p in sc['grammatical']['consonants'] + sc['grammatical']['vowels'])}",
          f"- Lexical sounds: {' '.join(rom[p] for p in sc['lexical']['consonants'] + sc['lexical']['vowels'])}", "",
          "### Grammatical affixes", "", "| Relation | Form | Meaning |", "|---|---|---|"]
    L += [f"| {rel} | {_fmt_affix(spec, a)} | {GLOSS[rel]} |" for rel, a in table["affixes"].items()]
    base = spec.morphology.gender_base
    other = "MALE" if base == "female" else "FEMALE"
    ex = {"male": ("king", "queen"), "female": ("queen", "king")}[base]
    ent = {e["concept_id"]: e for e in entries}
    L += ["", f"**Gender pairs.** In {spec.name} the {base} term of a pair is the plain root and the other is made with "
              f"the {other} affix: {ent[ex[0]]['form']} ({ex[0]}) → {ent[ex[1]]['form']} ({ex[1]}).", ""]
    fm = ", ".join(render_flat(spec, f)[0] for f in table["formatives"])
    L += ["", "### Root formatives", "", f"Short endings or beginnings used to tell members of a root family apart: {fm}.",
          "", "### Root families", "",
          "Each family shares one stem syllable (or more). The head word is the bare stem; the other members "
          "are the stem with one change.", ""]
    by_fam = {}
    for e in live:
        if e["family"] and e["kind"] in ("head", "family"):
            by_fam.setdefault(e["family"], []).append(e)
    for fam, es in sorted(by_fam.items()):
        st = state["stems"].get(fam)
        if not st:
            continue
        sib = f" (sibling of {st['sibling_of']})" if st.get("sibling_of") else ""
        L.append(f"- **{render_flat(spec, st['phonemes'])[0]}** — {fam}{sib}: "
                 + ", ".join(f"{e['gloss']} *{e['form']}*" for e in es))
    L += ["", "---", "", f"## English → {spec.name}", ""]

    def section(key, fmt):
        cur = None
        for e in sorted(entries, key=lambda e: _sort_key(key(e))):
            ini = _initial(key(e))
            if ini != cur:
                cur = ini
                L.extend(["", f"### {ini}", ""])
            L.append(fmt(e))
    mark = lambda e: " †" if e["retired"] else ""
    note = lambda e: f" ← {e['recipe']}" if e.get("recipe") else ""
    section(lambda e: e["gloss"], lambda e: f"- **{e['gloss']}** — {e['form']} {e['ipa']}{note(e)}{mark(e)}")
    L += ["", "---", "", f"## {spec.name} → English", ""]
    section(lambda e: e["form"], lambda e: f"- **{e['form']}** {e['ipa']} — {e['gloss']}{note(e)}{mark(e)}")
    return "\n".join(L) + "\n"
