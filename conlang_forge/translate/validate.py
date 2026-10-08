"""Validator and deterministic repair for parsed restricted English."""
from __future__ import annotations

import copy

from .lex import EnglishVocab
from .parser import Issue


def _np_refs(np, where, out):
    if not np:
        return
    h = np.get("head")
    if h and not str(h).startswith("#") and (h not in ("who", "what")):
        out.append((h, "noun", where))
    for a in np.get("adjectives", []):
        out.append((a, "adjective", where))
    p = np.get("possessor")
    if p and not str(p).startswith("#"):
        out.append((p, "noun", where))


def references(doc):
    """[(word-or-cid, kind, (sentence, clause, slot))] for every vocabulary word the document uses."""
    refs = []
    for si, s in enumerate(doc["sentences"]):
        for ci, c in enumerate(s["clauses"]):
            if c.get("kind") == "fragment":
                for k, w in enumerate(c["words"]):
                    if not str(w).startswith("#"):
                        refs.append((w, "any", (si, ci, f"words.{k}")))
                continue
            _np_refs(c.get("subject"), (si, ci, "subject"), refs)
            _np_refs(c.get("object"), (si, ci, "object"), refs)
            if c.get("verb"):
                refs.append((c["verb"], "verb", (si, ci, "verb")))
            p = c.get("predicate")
            if p:
                if "adjective" in p:
                    refs.append((p["adjective"], "adjective", (si, ci, "predicate")))
                elif "adverb" in p:
                    refs.append((p["adverb"], "adverb", (si, ci, "predicate")))
                else:
                    _np_refs(p, (si, ci, "predicate"), refs)
            for k, (prep, n) in enumerate(c.get("pps", [])):
                refs.append((prep, "prep", (si, ci, f"pps.{k}")))
                _np_refs(n, (si, ci, f"pps.{k}"), refs)
            for k, a in enumerate(c.get("adverbs", [])):
                refs.append((a, "adverb", (si, ci, f"adverbs.{k}")))
    return refs


def validate(doc, V: EnglishVocab, g=None):
    """Issues for words that are not in the language. `g` (a Grammar) is optional: with it, words must also exist
    in the generated lexicon, not just the vocabulary."""
    issues, seen = [], set()
    for w, kind, (si, ci, slot) in references(doc):
        ok = w in V.concepts and (g is None or g.has(w))
        if ok or w in seen:
            continue
        seen.add(w)
        issues.append(Issue("error", "unknown_word", f"'{w}' is not in the vocabulary.", sentence=si, clause=ci, slot=slot,
                            word=w, kind=kind, suggestions=V.suggest(w, {"noun": "n.", "verb": "v.", "adjective": "adj.",
                                                                          "adverb": "adv."}.get(kind))))
    return issues


def unknown_words(issues):
    return sorted({i["word"] for i in issues if i["code"] == "unknown_word" and i.get("word")})


def autorepair(doc, V: EnglishVocab, g=None):
    """Last resort once the model has had its chances: nothing is refused, silly beats an error.
    Unknown nouns become names (spelled with the language's sounds), unknown adjectives, adverbs and prepositions are
    dropped, an unknown verb becomes its closest vocabulary word, or the clause becomes a word-by-word fragment."""
    doc = copy.deepcopy(doc)
    notes = []
    bad = {i["word"] for i in validate(doc, V, g)}

    def ok(w):
        return w not in bad

    def fix_np(np):
        if not np:
            return np
        h = np.get("head")
        if h and not str(h).startswith("#") and h not in ("who", "what") and not ok(h):
            np["head"] = "#" + h.capitalize()
            np.pop("unknown", None)
            notes.append(Issue("warn", "kept_as_name", f"'{h}' is not in the vocabulary, so it was kept as a name.", word=h))
        if np.get("adjectives"):
            keep = [a for a in np["adjectives"] if ok(a)]
            for a in np["adjectives"]:
                if not ok(a):
                    notes.append(Issue("warn", "word_dropped", f"'{a}' is not in the vocabulary and was left out.", word=a))
            np["adjectives"] = keep
            if not keep:
                del np["adjectives"]
        p = np.get("possessor")
        if p and not str(p).startswith("#") and not ok(p):
            np["possessor"] = "#" + p.capitalize()
        return np

    for s in doc["sentences"]:
        for c in s["clauses"]:
            if c.get("kind") == "fragment":
                c["words"] = [w for w in c["words"] if str(w).startswith("#") or ok(w)]
                continue
            for k in ("subject", "object"):
                fix_np(c.get(k))
            pr = c.get("predicate")
            if pr:
                if "head" in pr:
                    fix_np(pr)
                elif "adjective" in pr and not ok(pr["adjective"]):
                    notes.append(Issue("warn", "word_dropped", f"'{pr['adjective']}' was left out.", word=pr["adjective"]))
                    c["predicate"] = None
                elif "adverb" in pr and not ok(pr["adverb"]):
                    c["predicate"] = None
            c["pps"] = [[p, fix_np(n)] for p, n in c.get("pps", []) if ok(p)]
            c["adverbs"] = [a for a in c.get("adverbs", []) if ok(a)]
            v = c.get("verb")
            if v and not ok(v):
                near = V.suggest(v, "v.", 1)
                if near:
                    notes.append(Issue("warn", "word_replaced", f"'{v}' is not in the vocabulary; '{near[0]}' was used instead.", word=v))
                    c["verb"] = V.cid(near[0])
                else:
                    notes.append(Issue("warn", "word_dropped", f"The verb '{v}' is not in the vocabulary and was left out.", word=v))
                    c["verb"] = None
                    if c.get("predicate") is None:
                        words = [x.get("head") for x in (c.get("subject"), c.get("object")) if x and x.get("head")]
                        c.clear()
                        c.update({"kind": "fragment", "words": words, "loose": True})
    return doc, notes
