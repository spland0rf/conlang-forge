"""Words of a generated language -> restricted English (a clause structure), the reverse of realize.py.

It reads each word with WordAnalyzer, then uses the language's own word order, case marking and agreement to decide
who did what. Where a language genuinely hides information (no tense, no cases, zero copula) the answer is the
natural reading and the Smoother (a model) gets the interlinear gloss as well, so it can use context.
"""
from __future__ import annotations

from ..grammar import Grammar, POSSESSIVE, PRONOUN, WH_WORDS
from ..morph import is_analytic
from ..pos import ADJ, ADV, CONJ, DET, INTERJ, NOUN, NUM, PREP, PRON, VERB
from .analyze import WordAnalyzer
from .lex import EnglishVocab

OBLIQUE_PREP = {"locative": "in", "inessive": "in", "allative": "to", "dative": "to", "ablative": "from", "elative": "from",
                "comitative": "with", "instrumental": "with", "benefactive": "for", "essive": "by"}
POSSESSIVE_CIDS = set(POSSESSIVE.values())
DEMO = {"this": ("this", False), "that": ("that", False), "these": ("this", True), "those": ("that", True)}
PAST = {"past", "recent past", "remote past"}
VERB_KEYS = ("tense:", "aspect:", "mood:", "evid:", "agr:")
AGR_PERSON = {"1sg": "i", "2sg": "you", "3sg": "he", "1pl": "we", "2pl": "you", "3pl": "they"}


class Assembler:
    def __init__(self, spec, state, vocab: EnglishVocab, grammar: Grammar | None = None):
        self.spec, self.V = spec, vocab
        self.g = grammar or Grammar(spec, state, None)
        self.A = WordAnalyzer(spec, state)
        self.analytic = is_analytic(spec)
        self.numerals = {}
        for n in range(0, 1000):
            try:
                self.numerals.setdefault(tuple(self.g.numeral_words(n)), n)
            except Exception:
                break

    # ------------------------------------------------------------------ tokens
    def _pos(self, cid):
        return (self.V.pos.get(cid) or [NOUN])[0] if cid else None

    def read_word(self, text):
        readings = self.A.analyze(text)
        if not readings:
            return {"text": text, "stem": None, "keys": [], "glosses": [], "kind": "unknown", "pos": NOUN,
                    "name": "#" + text.capitalize()}
        r = readings[0]
        if r["kind"] == "name":
            keys = [m["key"] for m in r["morphs"]]
            return {"text": text, "stem": None, "keys": keys, "glosses": [m["gloss"] for m in r["morphs"]], "kind": "name",
                    "pos": NOUN, "name": "#" + r["name"].capitalize(), "alts": []}
        for cand in readings:                           # prefer a reading whose stem is a known English word
            if cand["stem"] is None or cand["stem"] in self.V.concepts:
                r = cand
                break
        keys = [m["key"] for m in r["morphs"]]
        alts = []
        for cand in readings:
            if cand["stem"] and cand["stem"] != r["stem"] and cand["stem"] in self.V.concepts and cand["stem"] not in alts:
                alts.append(cand["stem"])
        return {"text": text, "alts": alts[:3], "stem": r["stem"], "keys": keys, "glosses": [m["gloss"] for m in r["morphs"]],
                "kind": r["kind"], "pos": self._pos(r["stem"]), "poslist": self.V.pos.get(r["stem"], [])}

    def merge_particles(self, toks):
        """Analytic languages write endings as separate words: fold them into the content word they belong to."""
        out, pending = [], []
        for t in toks:
            if t["kind"] != "particle":
                t = dict(t)
                t["keys"] = list(pending) + t["keys"]
                t["glosses"] = [self.A.particles[x["text"]]["gloss"] for x in []] + t["glosses"]
                pending = []
                out.append(t)
                continue
            key = t["keys"][0]
            m = self.A.particles.get(t["text"], {})
            clause_level = key.startswith(("q:", "cop"))
            if clause_level:
                out.append(t)
            elif m.get("position") == "suffix" and out and out[-1]["kind"] != "particle":
                out[-1]["keys"].append(key)
                out[-1]["glosses"].append(t["glosses"][0])
            else:
                pending.append(key)
        return out

    @staticmethod
    def feats(keys):
        f = {"case": None, "number": None, "tense": None, "aspect": None, "mood": None, "agr_s": None, "agr_o": None,
             "neg": False, "q": False, "cop": False, "definite": None, "gender": None}
        for k in keys:
            if k.startswith("case:"):
                f["case"] = k[5:]
            elif k == "affix:OBJ":
                f["case"] = "accusative"
            elif k == "affix:POSS":
                f["case"] = "genitive"
            elif k.startswith("number:"):
                f["number"] = "plural"
            elif k == "affix:PLURAL":
                f["number"] = "plural"
            elif k.startswith("tense:"):
                f["tense"] = k[6:]
            elif k.startswith("aspect:"):
                f["aspect"] = k[7:]
            elif k.startswith("mood:"):
                f["mood"] = k[5:]
            elif k.startswith("agr:subj:"):
                f["agr_s"] = k[9:]
            elif k.startswith("agr:obj:"):
                f["agr_o"] = k[8:]
            elif k == "affix:NEG":
                f["neg"] = True
            elif k.startswith("q:"):
                f["q"] = True
            elif k == "cop":
                f["cop"] = True
            elif k.startswith("def:"):
                f["definite"] = True
            elif k.startswith("gender:"):
                f["gender"] = k[7:]
        return f

    # ------------------------------------------------------------------ classification
    def category(self, t):
        f = self.feats(t["keys"])
        t["f"] = f
        stem = t["stem"]
        if t["kind"] in ("unknown", "name"):
            return "noun"
        if t["kind"] == "particle":
            return "particle"
        if stem == "not":
            return "neg"
        if stem in ("and", "but", "or"):
            return "conj"
        if stem in DEMO or stem in ("the", "a"):
            return "det"
        if stem in POSSESSIVE_CIDS:
            return "poss"
        if stem in PRONOUN or stem in ("who", "what"):
            return "noun"
        if stem in WH_WORDS:
            return "wh_adv"
        pl = t.get("poslist") or []
        verbish = bool(f["tense"] or f["aspect"] or f["mood"] or f["agr_s"] or f["agr_o"] or f["neg"])
        if stem == "be" or (stem in ("have", "do") and verbish):
            return "verb"
        if verbish and VERB in pl:
            return "verb"
        if NUM in pl:
            return "num"
        if PREP in pl and PREP == pl[0]:
            return "prep"
        if ADV in pl and pl[0] == ADV:
            return "adv"
        if INTERJ in pl and pl[0] == INTERJ:
            return "interj"
        if CONJ in pl and pl[0] == CONJ:
            return "conj"
        if f["case"] == "genitive":
            return "gen"
        if pl and pl[0] == ADJ or (f["gender"] and ADJ in pl) or (pl and pl[0] == DET):
            return "adj"
        if pl and pl[0] == VERB and not (f["case"] or f["number"] or f["definite"]):
            return "verb"
        return "noun"

    # ------------------------------------------------------------------ noun phrases
    def chunk(self, items):
        """items: [(cat, tok)] in order, only noun-phrase material. Returns [NPdict]."""
        adj_first = self.spec.syntax.adjective_order == "adjective-noun"
        nps, cur = [], None

        def new():
            return {"mods": [], "head": None, "adj": [], "det": None, "num": [], "poss": None, "after_adj": []}

        pending_adj = []
        for cat, t in items:
            if cat in ("det", "num", "poss", "gen"):
                if cur is None or cur["head"] is not None:
                    if cur is not None:
                        nps.append(cur)
                    cur = new()
                    cur["adj"] += pending_adj
                    pending_adj = []
                if cat == "det":
                    cur["det"] = t["stem"]
                elif cat == "num":
                    cur["num"].append(t["stem"])
                else:
                    cur["poss"] = t["stem"] if cat == "gen" else t["stem"]
                continue
            if cat == "adj":
                if adj_first:
                    if cur is None or cur["head"] is not None:
                        pending_adj.append(t["stem"])
                    else:
                        cur["adj"].append(t["stem"])
                else:
                    if cur is not None and cur["head"] is not None:
                        cur["after_adj"].append(t["stem"])
                    else:
                        pending_adj.append(t["stem"])
                continue
            # a head
            if cur is None or cur["head"] is not None:
                if cur is not None:
                    nps.append(cur)
                cur = new()
            cur["adj"] += pending_adj
            pending_adj = []
            cur["head"] = t
        if cur is not None:
            nps.append(cur)
        if pending_adj:
            nps.append({"head": None, "adj": pending_adj, "det": None, "num": [], "poss": None, "after_adj": []})
        return nps

    def np_dict(self, c):
        t = c["head"]
        if t is None:
            return None
        f = t["f"]
        head = t.get("name") or t["stem"]
        d = {"head": head}
        if t["kind"] == "unknown" or str(head).startswith("#"):
            pass
        adjs = [a for a in c["adj"] + c["after_adj"]]
        det = c["det"]
        if det in DEMO:
            d["demonstrative"], plural = DEMO[det][0], DEMO[det][1]
            if plural:
                d["number"] = "plural"
        elif det == "the" or f["definite"]:
            d["definite"] = True
        elif det == "a":
            d["definite"] = False
        if c["num"]:
            n = self.numerals.get(tuple(c["num"]))
            if n is not None:
                d["numeral"] = n
        if f["number"] == "plural" or (d.get("numeral") or 0) > 1:
            d["number"] = "plural"
        if c["poss"]:
            d["possessor"] = c["poss"] if c["poss"] in POSSESSIVE_CIDS and False else self._poss_of(c["poss"])
        if adjs:
            d["adjectives"] = adjs
        return d

    @staticmethod
    def _poss_of(cid):
        for pron, poss in POSSESSIVE.items():
            if poss == cid:
                return pron
        return cid

    # ------------------------------------------------------------------ one clause
    def pick_bare_verb(self, cats):
        """Languages that do not inflect verbs write a bare word: choose the verb-capable word by position."""
        if any(c in ("verb",) for c, _ in cats) or any(t["stem"] == "be" for _, t in cats):
            return cats
        cand = [i for i, (c, t) in enumerate(cats)
                if c == "noun" and t["kind"] == "word" and VERB in (t.get("poslist") or []) and not t["keys"]
                and (i == 0 or cats[i - 1][0] not in ("det", "num", "adj", "poss"))]
        if not cand or len(cats) < 2 and False:
            return cats
        order = self.spec.syntax.word_order
        if order.endswith("V"):
            pick = cand[-1]
        elif order.startswith("V"):
            pick = cand[0]
        else:
            later = [i for i in cand if i > 0]
            pick = later[0] if later else cand[0]
        cats = list(cats)
        cats[pick] = ("verb", cats[pick][1])
        return cats

    def clause(self, toks, mark):
        cats = [(self.category(t), t) for t in toks]
        cats = self.pick_bare_verb(cats)
        verbs = [(i, t) for i, (c, t) in enumerate(cats) if c == "verb"]
        negs = [(i, t) for i, (c, t) in enumerate(cats) if c == "neg"]
        q = None
        info = {"tense": None, "aspect": None, "mood": None, "agr_s": None, "agr_o": None, "neg": False, "q": False,
                "copula": False}
        verb_cid = None
        for i, t in verbs[:1]:
            f = t["f"]
            verb_cid = t["stem"]
            info["agr_o"] = f["agr_o"]
            for k in ("tense", "aspect", "mood", "agr_s", "q"):
                info[k] = f[k]
            info["neg"] = f["neg"]
            if f["cop"]:
                info["copula"] = True
        for i, t in negs:                     # negative particle or auxiliary (which may carry the endings)
            info["neg"] = True
            f = t["f"]
            for k in ("tense", "aspect", "mood", "agr_s"):
                info[k] = info[k] or f[k]
        for c, t in cats:
            if c == "particle":
                if t["keys"][0].startswith("q:"):
                    info["q"] = True
                if t["keys"][0] == "cop":
                    info["copula"] = True
        if verb_cid == "be":
            info["copula"], verb_cid = True, None
        wh_adv = [t["stem"] for c, t in cats if c == "wh_adv"]
        has_wh_np = any(c == "noun" and t["stem"] in ("who", "what") for c, t in cats)
        # ---- noun-phrase material, split by verbs / prepositions / adverbs
        prep_pos = self.spec.syntax.adposition
        groups, cur, pps_raw, adverbs, loose = [], [], [], [], []
        for i, (c, t) in enumerate(cats):
            if c in ("noun", "adj", "det", "num", "poss", "gen"):
                cur.append((c, t))
            else:
                if cur:
                    groups.append(("np", cur))
                    cur = []
                if c == "prep":
                    groups.append(("prep", t))
                elif c == "adv":
                    adverbs.append(t["stem"])
                elif c == "interj":
                    loose.append(t["stem"])
                elif c == "verb":
                    groups.append(("verb", t))
        if cur:
            groups.append(("np", cur))
        # ---- NPs and prepositions in order
        np_list, pps = [], []
        flat = []
        for kind, g in groups:
            if kind == "np":
                for c in self.chunk(g):
                    flat.append(("np", c, len(flat)))
            elif kind == "prep":
                flat.append(("prep", g, len(flat)))
            elif kind == "verb":
                flat.append(("verb", g, len(flat)))
        used = set()
        for idx, (kind, obj, _) in enumerate(flat):
            if kind != "prep":
                continue
            nb = None
            rng = range(idx + 1, len(flat)) if prep_pos == "preposition" else range(idx - 1, -1, -1)
            for j in rng:
                if flat[j][0] == "np" and j not in used:
                    nb = j
                    break
                if flat[j][0] != "np":
                    break
            if nb is not None:
                used.add(nb)
                np = self.np_dict(flat[nb][1])
                if np:
                    pps.append([obj["stem"], np])
            used.add(idx)
        for idx, (kind, obj, _) in enumerate(flat):
            if kind == "np" and idx not in used:
                np_list.append((idx, obj))
        verb_idx = next((i for i, (k, o, _) in enumerate(flat) if k == "verb"), None)
        subject = object_ = None
        pred = None
        order = [c for c in self.spec.syntax.word_order if c in "SO"]
        marks = self.spec.morphology.cases
        core, obliques = [], []
        for idx, c in np_list:
            if c["head"] is None:                 # orphan adjectives
                if info["copula"] or verb_idx is None:
                    pred = {"adjective": c["adj"][0]} if c["adj"] else pred
                continue
            case = c["head"]["f"]["case"]
            if case in OBLIQUE_PREP:
                p = OBLIQUE_PREP[case]
                np = self.np_dict(c)
                pps.append([p, np])
            elif case == "genitive":
                core.append((idx, c))
            else:
                core.append((idx, c))
        # roles: case marks first, then agreement, then the language's word order
        subject, object_, pred = self.roles(core, info, verb_idx, pred)
        if info["copula"] and object_ is not None and pred is None:
            pred, object_ = object_, None
        # ---- subject from verb agreement when the pronoun was dropped
        if subject is None and info["agr_s"] in AGR_PERSON and info["mood"] != "imperative":
            subject = {"head": AGR_PERSON[info["agr_s"]]}
            if info["agr_s"].endswith("pl"):
                subject["number"] = "plural" if subject["head"] not in PRONOUN else None
                subject.pop("number", None)
        is_wh = bool(has_wh_np or wh_adv)
        if subject is not None and subject.get("head") not in PRONOUN and (info.get("agr_s") or "").endswith("pl") \
                and "number" not in subject and "numeral" not in subject:
            subject["number"] = "plural"
        if object_ is not None and object_.get("head") not in PRONOUN and (info.get("agr_o") or "").endswith("pl") \
                and "number" not in object_ and "numeral" not in object_:
            object_["number"] = "plural"
        if verb_idx is None and verb_cid is None and not info["copula"] and wh_adv and subject is not None and pred is None:
            pred = {"adverb": wh_adv.pop(0)}
        if (verb_idx is None or info["copula"]) and verb_cid is None and pred is None and subject is not None \
                and object_ is None and subject.get("adjectives") and mark != "?" and not wh_adv:
            subject = dict(subject)
            pred = {"adjective": subject["adjectives"][-1]}
            subject["adjectives"] = subject["adjectives"][:-1]
            if not subject["adjectives"]:
                del subject["adjectives"]
        tense = "past" if info["tense"] in PAST else "future" if info["tense"] == "future" else "present"
        aspect = None
        if info["aspect"] in ("progressive", "imperfective", "continuative"):
            aspect = "progressive"
        elif info["aspect"] in ("completive", "perfect"):
            aspect = "perfect"
        question = None
        if is_wh:
            question = "wh"
        elif info["q"] or mark == "?":
            question = "yes-no"
        clause = {"kind": "clause", "subject": subject, "verb": verb_cid, "object": object_, "predicate": pred,
                  "pps": pps, "adverbs": adverbs + wh_adv, "tense": tense, "aspect": aspect,
                  "mood": "imperative" if info["mood"] == "imperative" else "indicative", "negated": info["neg"],
                  "question": question}
        if clause["verb"] is None and not info["copula"] and verb_idx is None:
            if subject is None and pred is None and not adverbs and not pps:
                words = loose or [t["stem"] or t.get("name") for c, t in cats if (t["stem"] or t.get("name"))]
                return {"kind": "fragment", "words": [w for w in words if w], "loose": False}
        if info["copula"] and clause["predicate"] is None and wh_adv:
            clause["predicate"] = {"adverb": wh_adv[0]}
            clause["adverbs"] = adverbs
        if clause["verb"] is None and clause["predicate"] is None and subject is not None and info["copula"] is False \
                and verb_idx is None and len(core) >= 2:
            pass
        if clause["subject"] is None and clause["mood"] != "imperative" and clause["verb"] is None \
                and clause["predicate"] is None and clause["object"] is None and not pps:
            return {"kind": "fragment", "words": [w for w in loose if w], "loose": False}
        return clause

    def roles(self, core, info, verb_idx, pred):
        """core: [(index, chunk)] of noun phrases that are neither obliques nor prepositional. Returns (S, O, pred)."""
        subject = object_ = None
        ergative = not self.spec.morphology.case_alignment.startswith("nom")
        transitive_hint = bool(info.get("agr_o"))
        unmarked = []
        for idx, c in core:
            case = c["head"]["f"]["case"] if c["head"] else None
            np = self.np_dict(c)
            if case == "accusative":
                object_ = object_ or np
                transitive_hint = True
            elif case == "ergative":
                subject = subject or np
                transitive_hint = True
            elif case == "genitive":
                continue
            else:
                unmarked.append((idx, np))
        word_order = self.spec.syntax.word_order
        vpos = word_order.index("V")
        pre_roles, post_roles = list(word_order[:vpos]), list(word_order[vpos + 1:])
        if verb_idx is None:
            seq = [n for _, n in unmarked]
            if seq and subject is None:
                subject = seq.pop(0)
            if seq and pred is None:
                pred = seq.pop(0)
            return subject, object_, pred
        before = [n for i, n in unmarked if i < verb_idx]
        after = [n for i, n in unmarked if i > verb_idx]
        # roles still open
        open_roles = [r for r in ("S", "O") if (r == "S" and subject is None) or (r == "O" and object_ is None)]
        if not open_roles:
            return subject, object_, pred
        if len(open_roles) == 1:
            role = open_roles[0]
            rest = before + after
            if rest:
                if role == "S":
                    subject = rest[0]
                else:
                    object_ = rest[0]
            return subject, object_, pred
        for side, roles in ((before, pre_roles), (after, post_roles)):
            if not side:
                continue
            if len(side) >= len(roles):
                for r, np in zip(roles, side[-len(roles):] if side is before else side[:len(roles)]):
                    if r == "S":
                        subject = subject or np
                    else:
                        object_ = object_ or np
            elif len(roles) == 2:                       # one noun phrase where two roles are possible
                np = side[0]
                if transitive_hint and (info.get("agr_s") or not info.get("copula")) and not info.get("copula") \
                        and (ergative or info.get("agr_o")):
                    object_ = object_ or np
                else:
                    subject = subject or np
            elif roles:
                r = roles[-1] if side is before else roles[0]
                if r == "S":
                    subject = subject or side[0]
                else:
                    object_ = object_ or side[0]
        return subject, object_, pred

    # ------------------------------------------------------------------ text
    def read(self, text: str):
        """Returns (doc, interlinear) where interlinear is one list of {text, gloss} per sentence."""
        sentences, inter = [], []
        for words, mark in self.A.sentences(text):
            toks = [self.read_word(w) for w in self.A.multiword(words)]
            if self.analytic:
                toks = self.merge_particles(toks)
            for t in toks:
                t["gloss"] = self._gloss(t)
            inter.append([{"text": t["text"], "gloss": t["gloss"], "known": t["kind"] not in ("unknown", "name"),
                           **({"alts": [self.V.lemma_of.get(a, a) for a in t["alts"]]} if t.get("alts") else {})}
                          for t in toks])
            for t in toks:
                self.category(t)
            segs, cur, links = [], [], []
            for t in toks:
                if self.category(t) == "conj" and t["stem"] in ("and", "but") and cur:
                    segs.append(cur)
                    links.append(t["stem"])
                    cur = []
                else:
                    cur.append(t)
            if cur:
                segs.append(cur)
            clauses = [self.clause(s, mark if len(segs) == 1 else ".") for s in segs]
            sentences.append({"clauses": clauses, "links": links[:max(0, len(clauses) - 1)], "mark": mark})
        return {"sentences": sentences}, inter

    def _gloss(self, t):
        if t["kind"] == "unknown":
            return "?"
        if t["kind"] == "name":
            return "-".join([t["name"][1:].upper()] + t["glosses"])
        if t["stem"] is None:
            return "-".join(t["glosses"])
        base = self.V.lemma_of.get(t["stem"], t["stem"])
        return "-".join([base] + t["glosses"])
