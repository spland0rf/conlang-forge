"""Lexicon construction and versioned upgrade."""
from __future__ import annotations

from .wordgen import make_word, render, rng_for, syllable_count

MAX_ATTEMPTS = 400


def _entry(spec, concept: dict, used: set, vocab_version: str) -> dict:
    for attempt in range(MAX_ATTEMPTS):
        r = rng_for(spec.seed, "word", concept["concept_id"], attempt)
        syl = make_word(spec, r, syllable_count(spec, r, concept, attempt))
        form, ipa = render(spec, syl)
        if form not in used:
            used.add(form)
            return {"concept_id": concept["concept_id"], "gloss": concept["gloss"],
                    "lemma": concept["lemma"], "is_function": concept["is_function"],
                    "form": form, "ipa": ipa, "syllables": [list(s) for s in syl],
                    "attempt": attempt, "retired": False, "added_in": vocab_version}
    raise RuntimeError(f"Could not find a unique form for {concept['concept_id']}")


def build_lexicon(spec, vocab: dict) -> list:
    used: set = set()
    return [_entry(spec, c, used, vocab["version"])
            for c in sorted(vocab["entries"], key=lambda e: e["concept_id"])]


def extend_lexicon(spec, lexicon: list, vocab: dict) -> tuple[list, dict]:
    """Upgrade a lexicon to a newer vocab version.

    Existing entries are never modified (except the `retired` flag). New concepts
    get new words; concepts missing from the new vocab are flagged retired, not deleted.
    """
    aliases = vocab.get("aliases", {})
    current = {e["concept_id"]: e for e in vocab["entries"]}
    out = [dict(e) for e in lexicon]
    for e in out:  # honor renames: keep the word, point it at the new concept id
        new_id = aliases.get(e["concept_id"])
        if new_id and new_id in current and e["concept_id"] not in current:
            e["concept_id"], e["gloss"], e["lemma"] = new_id, current[new_id]["gloss"], current[new_id]["lemma"]
    have = {e["concept_id"] for e in out}
    used = {e["form"] for e in out}
    report = {"added": [], "retired": [], "unretired": []}
    for e in out:
        gone = e["concept_id"] not in current
        if gone and not e["retired"]:
            report["retired"].append(e["concept_id"])
        if not gone and e["retired"]:
            report["unretired"].append(e["concept_id"])
        e["retired"] = gone
    for cid in sorted(set(current) - have):
        out.append(_entry(spec, current[cid], used, vocab["version"]))
        report["added"].append(cid)
    out.sort(key=lambda e: e["concept_id"])
    return out, report
