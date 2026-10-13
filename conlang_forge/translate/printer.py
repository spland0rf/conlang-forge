"""Structured clauses -> restricted English text (the form the user sees and may edit). Inverse of parser.parse."""
from __future__ import annotations

from ..grammar import POSSESSIVE
from . import english as en
from .lex import EnglishVocab

OBJ = {"i": "me", "he": "him", "she": "her", "we": "us", "they": "them", "you": "you", "it": "it"}
PERSON = {"i": (1, "sg"), "you": (2, "sg"), "he": (3, "sg"), "she": (3, "sg"), "it": (3, "sg"), "we": (1, "pl"), "they": (3, "pl")}


class Printer:
    def __init__(self, V: EnglishVocab):
        self.V = V

    def word(self, cid):
        if cid is None:
            return ""
        if str(cid).startswith("#"):
            return cid[1:]
        return self.V.lemma_of.get(cid, cid)

    def adjective(self, cid, degree=None, equative=False):
        """'old' + comparative -> 'older'; most -> 'most beautiful'; less -> 'less old'."""
        lem = self.word(cid)
        if equative or degree == "equative":
            return "as " + lem
        return en.degree_form(lem, degree) if degree in ("comparative", "superlative", "less", "least") else lem

    # ------------------------------------------------------------------ noun phrases
    def np(self, d, role="subj"):
        if not d:
            return ""
        head = d.get("head")
        if head in PERSON or head in ("who", "what"):
            return OBJ[head] if role == "obj" and head in OBJ else ("I" if head == "i" else head)
        parts = []
        plural = d.get("number") == "plural" or (d.get("numeral") not in (None, 1))
        if d.get("possessor"):
            pos = d["possessor"]
            parts.append(POSSESSIVE[pos] if pos in POSSESSIVE else self.word(pos) + "'s")
        elif d.get("demonstrative"):
            dm = d["demonstrative"]
            parts.append({"this": "these", "that": "those"}[dm] if plural else dm)
        elif d.get("definite") is True:
            parts.append("the")
        elif d.get("definite") is False and not plural:
            lem = self.word(head)
            parts.append("an" if lem[:1] in "aeiou" and d.get("adjectives", [None])[0] is None else "a")
        if d.get("numeral") is not None:
            parts.append(str(d["numeral"]))
        degs = d.get("degrees") or []
        parts += [self.adjective(a, degs[i] if i < len(degs) else None) for i, a in enumerate(d.get("adjectives", []))]
        if str(head).startswith("#"):
            parts.append(head[1:])
        else:
            lem = self.word(head)
            parts.append(en.plural(lem) if plural else lem)
        out = " ".join(parts)
        if d.get("relative"):
            out += " " + self.relative(d["relative"])
        # "a" before an adjective that starts with a vowel needs "an"
        if d.get("definite") is False and not plural and d.get("adjectives"):
            first = self.word(d["adjectives"][0])
            out = out.replace("a " + first, ("an " if first[:1] in "aeiou" else "a ") + first, 1)
        return out

    def relative(self, rel):
        """'who sleeps' / 'that the king saw' / 'where the king sleeps' / 'whose dog bit the king' after the noun they describe."""
        clause = rel["clause"]
        if rel.get("gap") == "possessor":                    # the clause carries the owner; the English says it as 'whose'
            subj = dict(clause.get("subject") or {})
            subj.pop("possessor", None)
            clause = {**clause, "subject": subj}
        return self._join([rel.get("word", "that"), self.clause(clause)])

    def person(self, d):
        if not d:
            return (3, "sg")
        h = d.get("head")
        if h in PERSON:
            return PERSON[h]
        plural = d.get("number") == "plural" or (d.get("numeral") not in (None, 1))
        return (3, "pl" if plural else "sg")

    # ------------------------------------------------------------------ verb groups
    def be(self, tense, person):
        if tense == "past":
            return "were" if person[1] == "pl" or person[0] == 2 else "was"
        if person == (1, "sg"):
            return "am"
        return "are" if person[1] == "pl" or person[0] == 2 else "is"

    def chain(self, tense, aspect, neg, verb, person, copula):
        """Returns (auxiliaries, main word): auxiliaries are in front of the subject-inversion point."""
        v = "be" if copula else verb
        if not v:
            return [], None
        plural = person[1] == "pl" or person[0] in (1, 2)
        aux, main = [], None
        if tense == "future":
            aux.append("will")
            if aspect == "perfect":
                aux.append("have")
                main = en.participle(v)
            elif aspect == "progressive":
                aux.append("be")
                main = en.ing(v)
            else:
                main = v
        elif aspect == "perfect":
            aux.append("had" if tense == "past" else ("have" if plural else "has"))
            main = en.participle(v)
        elif aspect == "progressive":
            aux.append(self.be(tense, person))
            main = en.ing(v)
        elif v == "be":
            aux, main = [self.be(tense, person)], None
        elif neg or False:
            aux.append("did" if tense == "past" else ("do" if plural else "does"))
            main = v
        else:
            main = en.past(v) if tense == "past" else (v if plural else en.third(v))
        if v == "be" and aspect is None and tense != "future":
            main = None
        return aux, main

    # ------------------------------------------------------------------ clauses
    def clause(self, c):
        if c.get("kind") == "fragment":
            return " ".join(self.word(w) for w in c["words"])
        if c.get("embedded"):
            return self._embedded(c)
        subj, obj, pred = c.get("subject"), c.get("object"), c.get("predicate")
        verb = self.word(c["verb"]) if c.get("verb") else None
        copula = c.get("verb") is None and pred is not None
        tense, aspect, neg, q = c.get("tense") or "present", c.get("aspect"), c.get("negated"), c.get("question")
        person = self.person(subj)
        if c.get("mood") == "imperative":
            body = ("do not " if neg else "") + (verb or "be")
            return self._join([body, self._rest(c)])
        yesno = q == "yes-no"
        wh = q == "wh"
        wh_obj = obj and obj.get("head") in ("who", "what") and wh
        wh_adv = [a for a in c.get("adverbs", []) if self.word(a) in ("where", "when", "why", "how")] if wh else []
        pred_adv = pred and "adverb" in pred and self.word(pred["adverb"]) in ("where", "when", "why", "how") and wh
        need_do = (yesno or wh_obj or (wh_adv and not copula)) and not neg
        aux, main = self.chain(tense, aspect, neg or need_do and False, verb, person, copula)
        if (yesno or wh_obj or wh_adv) and not aux and not copula:
            aux = ["did" if tense == "past" else ("do" if person[1] == "pl" or person[0] in (1, 2) else "does")]
            main = verb
        subj_wh = subj and subj.get("head") in ("who", "what") and wh
        neg_word = ["not"] if neg else []
        S = self.np(subj, "subj") if subj else ""
        rest = self._rest(c, skip_obj=wh_obj, skip_adv=bool(wh_adv), skip_pred=bool(pred_adv))
        wh_front = ""
        if wh_obj:
            wh_front = obj["head"]
        elif wh_adv:
            wh_front = self.word(wh_adv[0])
        elif pred_adv:
            wh_front = self.word(pred["adverb"])
        if yesno or wh_obj or wh_adv or pred_adv:
            first = aux[0]
            tail = aux[1:] + neg_word + ([main] if main else [])
            if neg and len(aux) == 1:       # "does the king not see": keep 'not' after the subject
                tail = neg_word + ([main] if main else [])
            parts = [wh_front, first, S] + tail
            if wh_obj is False:
                pass
            return self._join([" ".join(x for x in parts if x), rest])
        # declarative / subject-wh
        if neg and not aux:
            aux = ["did" if tense == "past" else ("do" if person[1] == "pl" or person[0] in (1, 2) else "does")]
            main = verb
        seq = []
        if aux:
            seq.append(aux[0])
            seq += neg_word
            seq += aux[1:]
        elif neg:
            seq += neg_word
        if main:
            seq.append(main)
        return self._join([S, " ".join(seq), rest])

    def _embedded(self, c):
        """'what the king saw' / 'who saw the dog' / 'who the king is': a question asked inside a statement (no inversion)."""
        plain = {**c, "embedded": False, "question": None}
        subj, obj, pred = c.get("subject"), c.get("object"), c.get("predicate")
        wh = lambda d: bool(d) and d.get("head") in ("who", "what")
        if wh(subj):
            return self.clause(plain)
        if wh(obj):
            return self._join([obj["head"], self.clause({**plain, "object": None})])
        if wh(pred):
            if c.get("verb"):
                return self._join([pred["head"], self.clause({**plain, "predicate": None})])
            tense = c.get("tense") or "present"
            return self._join([pred["head"], self.np(subj, "subj") if subj else "", self.be(tense, self.person(subj))])
        return self.clause(plain)

    def _rest(self, c, skip_obj=False, skip_adv=False, skip_pred=False):
        out = []
        pred, obj = c.get("predicate"), c.get("object")
        if pred and not skip_pred:
            if "adjective" in pred:
                out.append(self.adjective(pred["adjective"], pred.get("degree"), c.get("equative")))
            elif "adverb" in pred:
                out.append(self.word(pred["adverb"]))
            else:
                out.append(self.np(pred, "obj"))
        if obj and not skip_obj:
            out.append(self.np(obj, "obj"))
        pps = list(c.get("pps", []))
        # the indirect object reads best as "gave the dog a bone": keep the preposition form (parser accepts both)
        pp_out = []
        for prep, n in pps:
            if c.get("equative") and prep == "like":                      # "old like the king" is written "as old as the king"
                pp_out.append("as " + self.np(n, "obj"))
            else:
                pp_out.append(self.word(prep) + " " + self.np(n, "obj"))
        adverbs = [self.word(a) for a in c.get("adverbs", [])]
        adv_out = []
        k = 0
        while k < len(adverbs):
            a = adverbs[k]
            if skip_adv and a in ("where", "when", "why", "how"):
                k += 1
                continue
            if a in ("more", "most", "less", "least") and k + 1 < len(adverbs):          # "more fast" -> "faster"
                deg = {"more": "comparative", "most": "superlative"}.get(a, a)
                adv_out.append(en.degree_form(adverbs[k + 1], deg))
                k += 2
                continue
            if c.get("equative") and not (pred and "adjective" in pred) and k == 0:
                a = "as " + a
            adv_out.append(a)
            k += 1
        standard = any(p[0] == "than" or (c.get("equative") and p[0] == "like") for p in pps)
        out += (adv_out + pp_out) if standard else (pp_out + adv_out)
        return " ".join(x for x in out if x)

    @staticmethod
    def _join(parts):
        return " ".join(p for p in parts if p).strip()

    # ------------------------------------------------------------------ documents
    def sentence(self, s):
        text, prev = "", None
        for i, c in enumerate(s["clauses"]):
            t = self.clause(c)
            if c.get("polite"):
                t = "please " + t
            if c.get("intro"):
                t = self.word(c["intro"]) + " " + t
            if i:
                link = s["links"][i - 1] if i - 1 < len(s["links"]) else "and"
                if link:
                    text += ", " + link + " "
                else:                                   # a dependent clause: after its main clause with no comma, before it with one
                    text += ", " if prev and prev.get("intro") else " "
            text += t
            prev = c
        text = text[:1].upper() + text[1:] + s.get("mark", ".")
        return '"' + text + '"' if s.get("quote") else text

    def document(self, doc):
        return "\n".join(self.sentence(s) for s in doc["sentences"])
