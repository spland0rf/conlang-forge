"""Word-level analysis of text in a generated language: stem + endings, found by "analysis by synthesis".

For each written word we look for dictionary stems that occur inside it, then grow each candidate with the language's
own endings using the same joining code the generator uses, keeping only growths that are still substrings of the
word. A growth that spells the word exactly is an analysis. So whatever the generator can produce, this can read.
"""
from __future__ import annotations

import re

from ..morph import SPACE, is_analytic, join, render_flat

MAX_MORPHS = 7
AFFIX_KEYS = ("OBJ", "POSS", "NEG", "PLURAL")


class WordAnalyzer:
    def __init__(self, spec, state):
        self.spec, self.table = spec, state["table"]
        self.analytic = is_analytic(spec)
        self.entries = [e for e in state["entries"] if not e.get("retired")]
        self.by_form = {}                         # written form -> [cid]
        for e in self.entries:
            self.by_form.setdefault(e["form"], []).append(e["concept_id"])
        self.flat = {e["concept_id"]: list(e["phonemes"]) for e in self.entries}
        self.lemma = {e["concept_id"]: e["lemma"] for e in self.entries}
        self.freq = {e["concept_id"]: e.get("f") or 0 for e in self.entries}      # commoner words win ties
        self.morphs = self._morphemes()
        self.particles = {}                       # analytic: written form -> morpheme
        if self.analytic:
            for m in self.morphs:
                self.particles.setdefault(render_flat(spec, m["phonemes"])[0], m)
        self._suffixes = sorted(((render_flat(spec, m["phonemes"])[0], m) for m in self.morphs if m["position"] == "suffix"),
                                key=lambda x: -len(x[0]))
        self._stem_forms = sorted(((e["form"], e["concept_id"]) for e in self.entries), key=lambda x: -len(x[0]))
        self._cache = {}

    def _morphemes(self):
        seen, out = set(), []
        for k, m in self.table["infl"].items():
            key = (tuple(m["phonemes"]), m["position"])
            seen.add(key)
            out.append({"key": k, "phonemes": list(m["phonemes"]), "position": m["position"], "gloss": m["gloss"]})
        for k in AFFIX_KEYS:
            a = self.table["affixes"].get(k)
            if a and (tuple(a["phonemes"]), a["position"]) not in seen:
                out.append({"key": f"affix:{k}", "phonemes": list(a["phonemes"]), "position": a["position"],
                            "gloss": {"OBJ": "ACC", "POSS": "POSS", "NEG": "NEG", "PLURAL": "PL"}[k]})
        return out

    def _join(self, flat, m):
        if m["position"] == "prefix":
            return join(self.spec, self.table, m["phonemes"], flat, "affix")
        return join(self.spec, self.table, flat, m["phonemes"], "affix")

    def _write(self, flat):
        return render_flat(self.spec, flat)[0]

    # ------------------------------------------------------------------ one word
    def analyze(self, word: str) -> list:
        """All readings, best first: [{"stem": cid, "morphs": [{key, gloss}], "kind": "word"}], or [] if unknown."""
        w = word.lower()
        if w not in self.by_form and w[:1] in "'\u2019\u02bc" and not self._known(w):
            w = w[1:]
        if w in self._cache:
            return self._cache[w]
        out = []
        for cid in self.by_form.get(w, []):
            out.append({"stem": cid, "morphs": [], "kind": "word"})
        if self.analytic:
            m = self.particles.get(w)
            if m:
                out.append({"stem": None, "morphs": [{"key": m["key"], "gloss": m["gloss"]}], "kind": "particle"})
        if not out and not self.analytic:
            out = self._grow(w) or self._name_with_endings(w)
        self._cache[w] = out
        return out

    def _name_with_endings(self, w):
        """An unknown word may be a personal name carrying the language's case or number endings: peel them off."""
        peeled, rest = [], w
        for _ in range(3):
            for form, m in self._suffixes:
                if rest.endswith(form) and len(rest) - len(form) >= 3:
                    peeled.append(m)
                    rest = rest[:-len(form)]
                    break
            else:
                break
        if not peeled:
            return []
        return [{"stem": None, "name": rest, "kind": "name",
                 "morphs": [{"key": m["key"], "gloss": m["gloss"]} for m in reversed(peeled)]}]

    def _known(self, w):
        return w in self.by_form or w in self.particles

    def multiword(self, words):
        """Analytic languages can spell one dictionary word as several (queen = king + feminine). Join them."""
        out, i = [], 0
        longest = max([f.count(" ") for f in self.by_form] + [0]) + 1
        while i < len(words):
            for n in range(min(longest, len(words) - i), 1, -1):
                cand = " ".join(words[i:i + n]).lower()
                if cand in self.by_form:
                    out.append(cand)
                    i += n
                    break
            else:
                out.append(words[i])
                i += 1
        return out

    def _grow(self, w):
        # a stem may lose its last sound where an ending joins it (elision), so its front part must occur in the word
        cands = []
        for form, cid in self._stem_forms:
            if form in w or (len(form) >= 4 and form[:-1] in w) or (len(form) >= 5 and form[:-2] in w):
                cands.append(cid)
        cands = cands[:80]
        found = []
        for cid in cands:
            frontier = [(self.flat[cid], [])]
            for depth in range(MAX_MORPHS):
                nxt = []
                for flat, path in frontier:
                    for m in self.morphs:
                        if any(p["key"] == m["key"] for p in path):
                            continue
                        f2 = self._join(flat, m)
                        written = self._write(f2)
                        if written == w:
                            found.append({"stem": cid, "morphs": [{"key": x["key"], "gloss": x["gloss"]} for x in path + [m]],
                                          "kind": "word"})
                        elif written in w and len(written) < len(w):
                            nxt.append((f2, path + [m]))
                frontier = nxt[:400]
                if not frontier or found:
                    break
        found.sort(key=lambda r: (len(r["morphs"]), -self.freq.get(r["stem"], 0)))
        return found

    # ------------------------------------------------------------------ text
    def tokens(self, text: str):
        """[(word, mark_after)] with sentence marks kept as separate items."""
        from ..plain import fold, own_fold
        return re.findall(r"['\u2019\u02bc]?[^\W\d_]+(?:['\u2019\u02bc\-][^\W\d_]+)*|[.?!]", fold(text, own_fold(self.spec.orthography.romanization)), flags=re.UNICODE)

    def sentences(self, text: str):
        out, cur = [], []
        for t in self.tokens(text):
            if t in ".?!":
                if cur:
                    out.append((cur, t))
                cur = []
            else:
                cur.append(t)
        if cur:
            out.append((cur, "."))
        return out
