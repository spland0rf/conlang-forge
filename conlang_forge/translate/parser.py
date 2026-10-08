"""Shallow parser: restricted English text -> clause structures the grammar engine can realise.

The vocabulary is closed and every word has a part of speech, so a small backtracking parser is enough for the
simple sentences the Reducer writes (and the user edits). Anything it cannot read becomes an issue, never an exception:
a sentence that will not parse falls back to a word-by-word "loose" fragment, so there is always an answer.

Document shape (JSON-friendly):
  {"sentences": [{"clauses": [clause, ...], "links": ["and", ...], "mark": "." | "?" | "!"}]}
  clause  = {"kind": "clause", "subject": NP|None, "verb": cid|None, "object": NP|None, "predicate": dict|None,
             "pps": [[prep, NP]], "adverbs": [cid], "tense": ..., "aspect": ..., "mood": ..., "negated": bool,
             "question": None|"yes-no"|"wh"}
          | {"kind": "fragment", "words": [cid], "loose": bool}
  NP      = {"head": cid | "#Name", "number", "definite", "adjectives", "demonstrative", "numeral", "possessor"}
"""
from __future__ import annotations

import re

from . import english as en
from .lex import (AUX, DETERMINERS, NUMBER_WORDS, OBJECT_PRONOUN, POSSESSIVE_WORDS, EnglishVocab, ADJ, ADV, CONJ,
                  INTERJ, NOUN, PREP, PRON, VERB, WH_WORDS, PRONOUN)

CONTRACTIONS = {"don't": "do not", "doesn't": "does not", "didn't": "did not", "isn't": "is not", "aren't": "are not",
                "wasn't": "was not", "weren't": "were not", "won't": "will not", "can't": "can not",
                "cannot": "can not", "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
                "i'm": "i am", "you're": "you are", "we're": "we are", "they're": "they are", "it's": "it is",
                "he's": "he is", "she's": "she is", "that's": "that is", "what's": "what is", "who's": "who is",
                "there's": "there is", "here's": "here is", "where's": "where is", "i've": "i have",
                "you've": "you have", "we've": "we have", "they've": "they have", "i'll": "i will",
                "you'll": "you will", "he'll": "he will", "she'll": "she will", "we'll": "we will",
                "they'll": "they will", "i'd": "i would", "let's": "let us"}
TOKEN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+|[.?!,;:]")
BE = {"am", "is", "are", "was", "were", "be", "been", "being"}
MODALS = {"can", "could", "must", "may", "might", "should", "shall"}
INVERTING = BE | {"do", "does", "did", "will", "would", "have", "has", "had"} | MODALS
NEGATIVES = {"not", "never"}
TENSES_ADV = {}


def split_sentences(text: str):
    """[(tokens, mark)] where tokens keep their capitalisation."""
    out = []
    for line in re.split(r"\n+", text.strip()):
        cur = []
        for m in TOKEN.finditer(line):
            t = m.group(0)
            if t in ".?!":
                if cur:
                    out.append((cur, t))
                cur = []
            elif t in ",;:":
                cur.append(",")
            else:
                low = t.lower()
                if low in CONTRACTIONS:
                    cur += [(w.capitalize() if i == 0 and t[0].isupper() else w) for i, w in enumerate(CONTRACTIONS[low].split())]
                elif low.endswith("'s") and len(low) > 3:
                    cur += [t[:-2], "'s"]
                else:
                    cur.append(t.replace("'", ""))
        if cur:
            out.append((cur, "."))
    return out


class Issue(dict):
    def __init__(self, level, code, message, **kw):
        super().__init__(level=level, code=code, message=message, **kw)


class _Fail(Exception):
    pass


class ClauseParser:
    def __init__(self, vocab: EnglishVocab, words, issues, mark="."):
        self.V, self.raw, self.issues, self.mark = vocab, list(words), issues, mark
        self.w = [x.lower() for x in words]
        self.n = len(words)
        self.notes = []

    # ------------------------------------------------------------------ word classes
    def cap(self, i):
        t = self.raw[i]
        return t[:1].isupper() and t != "I" and i > 0 or (i == 0 and t[:1].isupper() and not self.V.has(t) and t != "I")

    def noun_readings(self, word):
        out = []
        for lem, num in en.noun_candidates(word):
            if self.V.has(lem) and self.V.is_pos(lem, NOUN):
                out.append((lem, num))
        return out

    def verb_readings(self, word):
        out = []
        for lem, f in en.verb_candidates(word):
            if (self.V.has(lem) and self.V.is_pos(lem, VERB)) or lem == "be":
                out.append((lem, f))
        return out

    def is_adj(self, word):
        return self.V.is_pos(word, ADJ) or (self.V.is_pos(word, "det.") and word not in DETERMINERS and word not in PRONOUN
                                            and word not in ("no",))

    def is_adv(self, word):
        return self.V.is_pos(word, ADV) and not self.V.is_pos(word, ADJ)

    def is_prep(self, word):
        return self.V.is_pos(word, PREP) and word not in ("like",) or word in ("into", "onto")

    # ------------------------------------------------------------------ noun phrases (generator: longest first)
    def nps(self, i):
        w, n = self.w, self.n
        if i >= n:
            return
        t = w[i]
        # pronouns
        if t in PRONOUN or t in OBJECT_PRONOUN:
            head = OBJECT_PRONOUN.get(t, t)
            if not (t == "her" and i + 1 < n and self._starts_np_word(i + 1)):
                yield {"head": head}, i + 1
        if t in ("who", "what") and self.V.has(t):
            yield {"head": t}, i + 1
        # names
        if self.raw[i][:1].isupper() and self.raw[i] != "I" and (i > 0 or not self.V.has(self.raw[i])):
            j = i + 1
            while j < n and self.raw[j][:1].isupper() and not self.V.has(self.raw[j]):
                j += 1
            name = self.raw[i].capitalize()
            yield {"head": "#" + name}, j
        np = {}
        j = i
        if t in DETERMINERS:
            d = DETERMINERS[t]
            if d == "the":
                np["definite"] = True
            elif d == "a":
                np["definite"] = False
            else:
                np["demonstrative"] = d if d in ("this", "that") else {"these": "this", "those": "that"}[d]
                if d in ("these", "those"):
                    np["number"] = "plural"
            j += 1
        elif t in POSSESSIVE_WORDS:
            np["possessor"] = POSSESSIVE_WORDS[t]
            j += 1
        elif t.isdigit() or (t in NUMBER_WORDS and j + 1 < n):
            val = int(t) if t.isdigit() else NUMBER_WORDS[t]
            if val > 999:
                self.issues.append(Issue("warn", "number_too_big", f"{t} is too big; numbers go up to 999."))
                val = 999
            np["numeral"] = val
            j += 1
        # modifiers + head: run of word tokens
        k = j
        while k < n and re.fullmatch(r"[a-z]+", w[k]) and w[k] not in ("and", "but", "of", "not", "never") \
                and not (w[k] in AUX) and not self.is_prep(w[k]) and w[k] not in DETERMINERS:
            k += 1
        run = list(range(j, k))
        if not run and "possessor" not in np and "definite" not in np:
            return
        # genitive: "the king 's sword"
        for end in range(len(run), 0, -1):
            head_i = run[end - 1]
            for lem, num in (self.noun_readings(w[head_i]) or ([(w[head_i], "singular")] if not self.V.has(w[head_i]) else [])):
                mods = run[:end - 1]
                if not all(self.is_adj(w[m]) or self.noun_readings(w[m]) or not self.V.has(w[m]) for m in mods):
                    continue
                cand = dict(np)
                adjs, poss = [], cand.get("possessor")
                for m in mods:
                    if self.is_adj(w[m]) or (not self.V.has(w[m])):
                        adjs.append(w[m] if self.V.has(w[m]) else w[m])
                    else:
                        if poss is None:
                            poss = self.noun_readings(w[m])[0][0]
                        else:
                            self.issues.append(Issue("info", "noun_modifier_dropped", f"'{w[m]}' as a modifier was dropped.", word=w[m]))
                if poss is not None:
                    cand["possessor"] = poss
                if adjs:
                    cand["adjectives"] = adjs
                cand["head"] = lem if self.V.has(lem) else w[head_i]
                if not self.V.has(lem):
                    cand["unknown"] = True
                if num == "plural" and "numeral" not in cand:
                    cand["number"] = "plural"
                if num == "plural" and cand.get("numeral") == 1:
                    cand["numeral"] = None
                nxt = head_i + 1
                # 's possessor:  X 's Y  -> head Y, possessor X (handled by caller through nps_possessive)
                if nxt < n and w[nxt] == "'s":
                    continue
                # "of" phrase: sword of the king
                if nxt + 1 < n and w[nxt] == "of" and "possessor" not in cand:
                    for sub, e2 in self.nps(nxt + 1):
                        if sub.get("head") and not str(sub["head"]).startswith("#") or sub.get("head"):
                            c2 = dict(cand)
                            c2["possessor"] = sub["head"]
                            yield self._clean(c2), e2
                yield self._clean(cand), nxt
        # possessor + 's  + noun phrase :  "the king 's sword"
        for end in range(len(run), 0, -1):
            head_i = run[end - 1]
            nxt = head_i + 1
            if nxt < n and w[nxt] == "'s":
                owner = self.noun_readings(w[head_i])
                owner_head = owner[0][0] if owner else (self.raw[head_i].capitalize() if self.raw[head_i][:1].isupper() else w[head_i])
                if not owner and not self.raw[head_i][:1].isupper() and not self.V.has(w[head_i]):
                    owner_head = w[head_i]
                if self.raw[head_i][:1].isupper() and not owner:
                    owner_head = "#" + owner_head
                for sub, e2 in self.nps_no_det(nxt + 1):
                    c2 = dict(sub)
                    c2["possessor"] = owner_head
                    yield c2, e2

    def nps_no_det(self, i):
        for np, j in self.nps(i):
            yield np, j

    @staticmethod
    def _clean(np):
        return {k: v for k, v in np.items() if v is not None}

    def _starts_np_word(self, i):
        t = self.w[i]
        return t in DETERMINERS or bool(self.noun_readings(t)) or self.is_adj(t) or t.isdigit()

    # ------------------------------------------------------------------ verb groups
    def vg(self, i):
        """Generator of (info, j). info: tense, aspect, negated, verb (cid or None for copula), copula, mood_modal, passive."""
        w, n = self.w, self.n
        j = i
        chain = []
        neg = False
        while j < n and (w[j] in AUX or w[j] in NEGATIVES):
            if w[j] in NEGATIVES:
                neg = True
            else:
                chain.append(w[j])
            j += 1
            if j < n and w[j] in ("not",):
                pass
        # Option 1: a main verb follows the auxiliaries
        opts = []
        if j < n:
            for lem, f in self.verb_readings(w[j]) or ([] if self.V.has(w[j]) and not self.V.is_pos(w[j], VERB) else self._unknown_verb(w[j])):
                opts.append((lem, f, j + 1))
        # Option 2: the last auxiliary is itself the main verb (copula / have / do)
        if chain:
            opts.append((en_lemma_of_aux(chain[-1]), "aux", j))
        for lem, f, e in opts:
            info = self._features(chain[:-1] if f == "aux" else chain, lem, f, neg)
            if info is not None:
                if f == "aux":
                    info["_surface_main"] = chain[-1]
                yield info, e

    def _unknown_verb(self, word):
        out = []
        for lem, f in en.verb_candidates(word):
            if f != "base" or True:
                out.append((lem, f))
        return out[:1] if out and not self.V.has(word) and not self.noun_readings(word) and not self.is_adj(word) \
            and not self.is_adv(word) and not self.is_prep(word) else []

    def _features(self, aux, verb, form, neg):
        tense, aspect, passive, modal = None, None, False, None
        past = False
        a = list(aux)
        for x in a:
            if x in ("was", "were", "did", "had"):
                past = True
            if x in ("will", "shall"):
                tense = "future"
            if x == "would":
                tense = "future"
                modal = "would"
            if x in MODALS - {"shall"}:
                modal = x
        if form == "aux":
            main_aux = a  # features come from the earlier aux only; main verb is the last aux
        if verb == "be" and form in ("aux", "base"):
            pass
        has = any(x in ("have", "has", "had") for x in a)
        isbe = any(x in BE for x in a)
        if form == "pp" and has:
            aspect = "perfect"
        elif form == "pp" and isbe:
            passive = True
        elif form == "ing" and isbe:
            aspect = "progressive"
        elif form == "ing" or (form == "pp" and not has and not isbe):
            if form == "ing":
                return None
            past = True if not a else past          # "the king seen": read as past
        if form == "past" and not a:
            past = True
        if form in ("past",) and a and not any(x in ("did",) for x in a) and not has and not isbe:
            return None
        if form in ("third", "base", "past") and a and not any(x in ("do", "does", "did", "will", "would", "shall") or x in MODALS for x in a):
            return None
        if tense is None:
            tense = "past" if past else "present"
        if form == "aux":
            lemma_surface = None
        return {"tense": tense, "aspect": aspect, "negated": neg, "verb": verb, "passive": passive, "modal": modal,
                "copula": verb == "be", "form": form}

    # ------------------------------------------------------------------ complements
    def rest(self, i, copula):
        """Parse everything after the verb: [object|predicate] pps adverbs. Returns (dict, j) best effort, longest."""
        w, n = self.w, self.n
        res = {"object": None, "predicate": None, "pps": [], "adverbs": []}
        j = i
        first = True
        pending_np = []
        while j < n:
            t = w[j]
            if t == ",":
                j += 1
                continue
            if t in ("and", "but"):
                break
            if self.is_prep(t) or t in ("into", "onto"):
                got = None
                for np, e in self.nps(j + 1):
                    got = (np, e)
                    # prefer the NP that reaches furthest without swallowing a following preposition's NP
                    break
                if got is None:
                    self.issues.append(Issue("warn", "dangling_preposition", f"'{t}' has no noun after it.", word=t))
                    j += 1
                    continue
                res["pps"].append([self.V.cid(t) and t, got[0]])
                j = got[1]
                first = False
                continue
            if self.is_adv(t) and not any(True for _ in self.nps(j)):
                res["adverbs"].append(t)
                j += 1
                continue
            if self.is_adv(t) and self.V.is_pos(t, ADV) and not self.noun_readings(t) and not self.is_adj(t):
                res["adverbs"].append(t)
                j += 1
                continue
            if copula and res["predicate"] is None and res["object"] is None:
                if self.is_adj(t) and not any(self.noun_readings(w[x]) for x in range(j + 1, min(n, j + 2)) if x < n and w[x] not in ("and", "but", ",")):
                    res["predicate"] = {"adjective": t}
                    j += 1
                    continue
                if t in WH_WORDS and not self.V.is_pos(t, "pron."):
                    res["predicate"] = {"adverb": t}
                    j += 1
                    continue
                for np, e in self.nps(j):
                    res["predicate"] = dict(np)
                    j = e
                    break
                else:
                    if self.V.has(t):
                        res["predicate"] = {"adverb": t} if self.is_adv(t) else {"adjective": t}
                        j += 1
                    else:
                        res["predicate"] = {"adjective": t, "unknown": True}
                        j += 1
                continue
            got = None
            for np, e in self.nps(j):
                got = (np, e)
                break
            if got is None:
                break
            if res["object"] is None:
                res["object"] = got[0]
            else:                                  # "give the dog a bone": first NP is the recipient
                res["pps"].insert(0, ["to", res["object"]])
                res["object"] = got[0]
            j = got[1]
        return res, j

    # ------------------------------------------------------------------ one clause
    def parse(self):
        w, n = self.w, self.n
        if not n:
            raise _Fail("empty")
        q = None
        wh = None
        order = list(range(n))
        words = list(self.raw)
        first = w[0]
        wh_adv = None
        # --- questions: normalise to declarative order
        if first in WH_WORDS and self.V.has(first):
            q = "wh"
            if first in ("who", "what") and n > 1 and w[1] in INVERTING and w[1] not in BE and self._np_after_aux(1):
                tail = self._invert(1)
                words, wh = tail, ("object", first)
            elif first in ("who", "what"):
                words, wh = self.raw[:], ("subject", first)
            elif n > 1 and w[1] in BE and self._np_after_aux(1) and self._only_np_after(2):
                words, wh_adv = self._invert(1), first
                self.pred_adv = first
            elif n > 1 and w[1] in INVERTING and self._np_after_aux(1):
                words, wh_adv = self._invert(1), first
            else:
                words, wh_adv = self.raw[1:], first
        elif first in INVERTING and self.mark == "?" and self._np_after_aux(0):
            q = "yes-no"
            words = self._invert(0)
        elif self.mark == "?":
            q = "yes-no"
        self.w = [x.lower() for x in words]
        self.raw, self.n = list(words), len(words)
        w, n = self.w, self.n
        return self._declarative(q, wh, wh_adv)

    def _only_np_after(self, i):
        return any(e == self.n for _, e in self.nps(i))

    def _np_after_aux(self, i):
        return any(True for _ in self.nps(i + 1))

    def _invert(self, i):
        """tokens of [wh] AUX NP rest ... -> NP AUX rest (the wh word is kept out; caller knows it)."""
        start = i + 1
        best = None
        for np, e in self.nps(start):
            best = e
            break
        if best is None:
            return self.raw[i:]
        aux = self.raw[i]
        out = self.raw[start:best] + [aux] + self.raw[best:]
        return out

    def _declarative(self, q, wh, wh_adv):
        w, n = self.w, self.n
        best = None
        subjects = []
        # imperative or declarative: subject optional
        starts = list(self.nps(0))
        starts = [(s, j) for s, j in starts] + [(None, 0)]
        if wh and wh[0] == "subject":
            starts = [({"head": wh[1]}, 1)]
        for subj, j in starts:
            for info, j2 in self.vg(j):
                if info.get("copula") and info.get("form") == "aux" and info["_surface_main"] in BE:
                    pass
                rest, j3 = self.rest(j2, info["copula"])
                score = (j3, -len(rest.get("pps", [])) * 0, subj is not None)
                if best is None or score > best[0]:
                    best = (score, subj, info, rest, j3)
                if j3 == n:
                    break
            if best and best[4] == n:
                break
        if best is None:
            raise _Fail("no verb")
        _, subj, info, rest, j3 = best
        if j3 < n:
            left = " ".join(self.raw[j3:])
            self.issues.append(Issue("warn", "ignored_words", f"Could not read '{left}', so it was left out.", word=left))
        clause = {"kind": "clause", "subject": subj, "verb": None if info["copula"] else self._cid(info["verb"]),
                  "object": rest["object"], "predicate": rest["predicate"], "pps": rest["pps"],
                  "adverbs": [self._cid(a) for a in rest["adverbs"]], "tense": info["tense"], "aspect": info["aspect"],
                  "mood": "indicative", "negated": info["negated"], "question": q}
        if info["copula"]:
            if clause["predicate"] is None and clause["object"] is not None:
                clause["predicate"], clause["object"] = clause["object"], None
            if clause["predicate"] is None:
                clause["predicate"] = {"adjective": "good"} if False else None
        if subj is None and not wh:
            if q is None and self.mark != "?":
                clause["mood"] = "imperative"
                clause["tense"] = "present"
        if wh and wh[0] == "object":
            clause["object"] = {"head": wh[1]}
        if wh_adv:
            if clause["predicate"] is None and info["copula"]:
                clause["predicate"] = {"adverb": wh_adv}
            else:
                clause["adverbs"] = clause["adverbs"] + [wh_adv]
        if info["passive"]:
            self._passive(clause)
        if info["modal"]:
            self.issues.append(Issue("info", "modal_dropped", f"'{info['modal']}' has no equivalent here and was left out.", word=info["modal"]))
        return clause

    def _passive(self, clause):
        by = [p for p in clause["pps"] if p[0] == "by"]
        if by:
            agent = by[0][1]
            clause["pps"] = [p for p in clause["pps"] if p is not by[0]]
            patient = clause["subject"]
            clause["subject"], clause["object"] = agent, patient
            self.issues.append(Issue("info", "passive_rewritten", "A passive sentence was turned into an active one."))
        else:
            clause["object"], clause["subject"] = clause["subject"], {"head": "they"}
            self.issues.append(Issue("info", "passive_rewritten", "A passive sentence without an agent was rewritten with 'they'."))

    def _cid(self, w):
        if w is None:
            return None
        return self.V.cid(w) or w


def en_lemma_of_aux(a):
    return {"am": "be", "is": "be", "are": "be", "was": "be", "were": "be", "been": "be", "being": "be", "be": "be",
            "does": "do", "did": "do", "has": "have", "had": "have"}.get(a, a)


# ======================================================================== document level
def _cids(clause, V):
    """Replace lemma words by concept ids in noun phrases."""
    def np(d):
        if not d:
            return d
        d = dict(d)
        h = d.get("head")
        if h and not str(h).startswith("#"):
            d["head"] = V.cid(h) or h
        d["adjectives"] = [V.cid(a) or a for a in d.get("adjectives", [])]
        if not d["adjectives"]:
            d.pop("adjectives")
        if d.get("possessor") and not str(d["possessor"]).startswith("#"):
            d["possessor"] = V.cid(d["possessor"]) or d["possessor"]
        d.pop("unknown", None) if V.has(str(d.get("head", ""))) else None
        return d
    c = dict(clause)
    for k in ("subject", "object"):
        c[k] = np(c.get(k))
    p = c.get("predicate")
    if p:
        p = dict(p)
        if "head" in p:
            p = np(p)
        elif "adjective" in p:
            p["adjective"] = V.cid(p["adjective"]) or p["adjective"]
        elif "adverb" in p:
            p["adverb"] = V.cid(p["adverb"]) or p["adverb"]
        c["predicate"] = p
    c["pps"] = [[V.cid(a) or a, np(b)] for a, b in c.get("pps", [])]
    return c


def parse_clause_words(V, words, mark, issues):
    p = ClauseParser(V, words, issues, mark)
    try:
        return _cids(p.parse(), V)
    except _Fail:
        return None


def parse_sentence(V: EnglishVocab, tokens, mark, index, issues):
    """tokens: list of words (with ',' and conjunctions). Returns a sentence dict."""
    toks = [t for t in tokens]
    # split on 'and' / 'but' where both sides read as clauses
    spans = [(0, len(toks))]
    links = []
    clauses = []
    cur_start = 0
    pieces, linkw = [], []
    i = 0
    cut_points = [k for k, t in enumerate(toks) if t.lower() in ("and", "but") and 0 < k < len(toks) - 1]
    segs = [toks]
    for k in cut_points:
        left = toks[cur_start:k]
        while left and left[-1] == ",":
            left = left[:-1]
        right = toks[k + 1:]
        trial_issues = []
        lp = ClauseParser(V, left, trial_issues, ".")
        rp = ClauseParser(V, [x for x in right if x != ","], trial_issues, ".")
        try:
            lc, rc = lp.parse(), rp.parse()
        except _Fail:
            continue
        if rc.get("subject") is None and rc.get("mood") == "imperative" and lc.get("mood") != "imperative":
            continue
        if any(i["level"] == "warn" and i["code"] == "ignored_words" for i in trial_issues):
            continue
        pieces.append(left)
        linkw.append(toks[k].lower())
        cur_start = k + 1
    pieces.append(toks[cur_start:])
    for seg in pieces:
        seg = [x for x in seg if x != ","]
        if not seg:
            continue
        local = []
        c = parse_clause_words(V, seg, mark if len(pieces) == 1 else ".", local)
        for it in local:
            it["sentence"] = index
        issues.extend(local)
        if c is None:
            c = loose_fragment(V, seg, index, issues)
        clauses.append(c)
    return {"clauses": clauses, "links": linkw[:max(0, len(clauses) - 1)], "mark": mark}


def loose_fragment(V, words, index, issues):
    """Word-by-word fallback: every word we know, in order; the rest become names. Never fails."""
    out, bad = [], []
    for raw in words:
        w = raw.lower()
        if w in ("'s",):
            continue
        if V.has(w):
            out.append(V.cid(w))
            continue
        base = None
        for lem, _ in en.noun_candidates(w) + en.verb_candidates(w):
            if V.has(lem):
                base = lem
                break
        if base:
            out.append(V.cid(base))
        elif raw[:1].isupper():
            out.append("#" + raw.capitalize())
        else:
            bad.append(raw)
    simple = len(words) <= 3 and not any(V.is_pos(x.lower(), VERB) and not V.is_pos(x.lower(), INTERJ, NOUN) for x in words)
    if not simple:
        msg = "Could not read this as a sentence, so it is translated word by word."
        issues.append(Issue("warn", "loose_fragment", msg, sentence=index, words=[W for W in words]))
    for b in bad:
        issues.append(Issue("error", "unknown_word", f"'{b}' is not in the vocabulary.", sentence=index, word=b,
                            suggestions=V.suggest(b)))
    return {"kind": "fragment", "words": out, "loose": not simple}


def parse(V: EnglishVocab, text: str):
    """Restricted English text -> (doc, issues)."""
    issues = []
    sentences = []
    for idx, (tokens, mark) in enumerate(split_sentences(text)):
        s = parse_sentence(V, tokens, mark, idx, issues)
        sentences.append(s)
    return {"sentences": sentences}, issues
