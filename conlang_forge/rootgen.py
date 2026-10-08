"""Root-based lexicon generation.

Pipeline (each phase is deterministic; every word is keyed by seed + concept id + attempt):
  A. Family stems   - each conceptual family owns one stem syllable (more if the language is short of
                      syllables). Families split from one natural group get related stems.
  B. Family roots   - the family head is the bare stem; other members are the stem modified by one
                      lexical transformation (formative, vowel/consonant change, ...), using only the
                      language's LEXICAL sounds.
  C. Free roots     - concepts with no family get independent words; bound roots (@name) likewise.
  D. Derived words  - roots plus regular relation affixes (GRAMMATICAL sounds), and compounds.
Candidates are rejected if they are too close (phonetics.MIN_DIST) to an existing root, are not
phonotactically valid, or collide with a derivation of another root. The checks relax in stages so
generation always terminates; relaxed words are flagged. `extend` adds only missing concepts, so a
vocabulary upgrade never changes an existing word.
"""
from __future__ import annotations

from collections import defaultdict

from .morph import (SPACE, apply_relation, build_table, glue, join, render_flat, valid_word)
from .phonetics import MIN_DIST, NearIndex, pdist
from .relations import RELATIONS
from .roots import adapt_rootmap, recipe_text
from .frequency import f_of
from .plan import apply_plan, make_plan
from .smallwords import SHORT, TINY, is_efficient, tiny_leak
from .wordgen import _poisson, _syllable, make_word, rng_for

ROOT_KINDS = {"head", "family", "free", "bound"}


class GenError(RuntimeError):
    pass


def _flat(sylls):
    return [p for s in sylls for p in s]


def _contains(seq, sub) -> bool:
    n = len(sub)
    return any(list(seq[i:i + n]) == list(sub) for i in range(len(seq) - n + 1))


class _Ctx:
    def __init__(self, spec, rootmap, vocab, state, bumps, freq=None):
        self.spec, self.rm, self.bumps = spec, rootmap, bumps
        self.freq = freq
        self.table = state["table"]
        self.vocab = {e["concept_id"]: e for e in vocab["entries"]}
        self.vver = vocab["version"]
        self.recipes = rootmap["recipes"]
        self.root_family = rootmap["root_family"]
        self.ph = spec.phonology
        self.rom = spec.orthography.romanization
        self.tuning = (spec.tuning or {}).get("gen") or {}
        self.V = set(self.ph.vowels)
        self.entries = {e["concept_id"]: e for e in state["entries"]}
        self.frozen = set(self.entries)
        self.stems = dict(state["stems"])
        self.budget = state.get("stem_budget")
        self.new: list = []
        self.all_forms: set = set()
        self.rom_forms: set = set()   # spellings in use: two different sound sequences can be written alike (n+g and ŋ = "ng")
        self.root_index = NearIndex()
        self.fam_index = defaultdict(NearIndex)
        self.root_forms: set = set()
        self.deriv: set = set()
        self.reserved: set = set()
        for a in self.table["affixes"].values():
            self._reserve(a["phonemes"])
        for f in self.table["formatives"]:
            self._reserve(f)
        for a in self.table.get("infl", {}).values():   # case, tense, agreement ... endings are not roots either
            self._reserve(a["phonemes"])
        lex = self.table["sound_classes"]["lexical"]
        self.lex_c, self.lex_v = lex["consonants"], lex["vowels"]
        for e in self.entries.values():
            if e["kind"] != "alias":
                self._index(tuple(e["phonemes"]), e.get("family") if e["kind"] in ROOT_KINDS else None,
                            e["kind"] in ROOT_KINDS)
        for fam, st in self.stems.items():
            self._index(tuple(st["phonemes"]), fam, True)

    # ------------------------------------------------------------------ indexing and checks
    def _reserve(self, ph):
        t = tuple(ph)
        self.reserved.add(t)
        self.root_index.add(t)

    def _derivs(self, t):
        return [tuple(apply_relation(self.spec, self.table, list(t), rel)) for rel in RELATIONS]

    def romstr(self, t) -> str:
        return "".join(self.rom.get(p, p) for p in t)

    def _index(self, t, family, is_root):
        self.all_forms.add(t)
        self.rom_forms.add(self.romstr(t))
        if is_root:
            self.root_index.add(t)
            self.root_forms.add(t)
            if family:
                self.fam_index[family].add(t)
            self.deriv.update(self._derivs(t))

    def letters(self, t) -> int:
        """Length of a form in written letters (spaces between words do not count)."""
        return sum(len(self.rom.get(p, p)) for p in t if p != SPACE)

    def _check(self, t, family, level, tiny_ok=False, near=True) -> bool:
        if t in self.all_forms or t in self.reserved or self.romstr(t) in self.rom_forms:
            return False
        if not tiny_ok and self.letters(t) <= TINY:   # one- and two-letter forms belong to the short common words
            return False
        if level >= 2:
            return True
        if family and self.fam_index[family].near(t):
            return False
        if level == 1:
            return True
        if (near and self.root_index.near(t)) or t in self.deriv:
            return False
        return not any(d in self.root_forms for d in self._derivs(t))

    @staticmethod
    def _level(attempt) -> int:
        return 0 if attempt < 150 else 1 if attempt < 300 else 2

    def _bump(self, cid) -> int:
        return self.bumps.get(cid, 0)

    def f(self, cid) -> float:
        """Commonness in (0, 1]; there is no cutoff, it scales word length continuously."""
        return f_of(self.vocab.get(cid), self.freq)

    def tier(self, cid) -> int:
        """Coarse bucket of f, for reporting and for ordering stem allocation: 1 common ... 3 rare."""
        f = self.f(cid)
        return 1 if f >= .5 else 2 if f >= .2 else 3

    def gen(self, name, default):
        v = self.tuning.get(name)
        return default if v is None else v

    def length_scale(self, f) -> float:
        k = self.gen("commonness_shortening", 1.35)       # how strongly common words are shorter than rare ones
        return min(1.4, max(.6, 1.46 + .34 * (k - 1.35) - k * f))     # k=1.35: f=.6 -> .65, f=.25 -> 1.1, f=.08 -> 1.35

    def _n_syllables(self, r, concept, attempt, f) -> int:
        mean = self.ph.mean_root_syllables * self.length_scale(f)
        if concept["is_function"]:
            mean = max(1.0, mean * self.gen("function_word_shortening", .8))
        return min(1 + _poisson(r, max(mean - 1, .05)), int(self.gen("max_root_syllables", 5))) + attempt // 4

    def _entry(self, cid, flat, kind, **extra):
        form, ipa, sylls = render_flat(self.spec, flat)
        c = self.vocab.get(cid)
        if c:
            gloss, lemma, isf = c["gloss"], c["lemma"], c["is_function"]
        else:
            gloss, lemma, isf = cid, cid.lstrip("@"), False
        e = {"concept_id": cid, "gloss": gloss, "lemma": lemma, "is_function": isf, "form": form,
             "ipa": ipa, "phonemes": list(flat), "syllables": sylls, "kind": kind, "family": None,
             "retired": False, "added_in": self.vver, "attempt": 0, "relaxed": 0, "recipe": None,
             "tier": self.tier(cid), "f": round(self.f(cid), 3)}
        e.update(extra)
        self.entries[cid] = e
        self.new.append(cid)
        return e

    # ------------------------------------------------------------------ phase A: stems
    def _fam_roots(self, fam):
        return [r for r in self.rm["families"][fam] if r in self.vocab or r.startswith("@")]

    # -- one-syllable stem budget: sized from the language's own syllable capacity ---------------
    def _short_candidates(self):
        ph = self.ph
        tw = ph.syllable_templates
        out, seen = [], set()
        for name, tweight in tw.items():
            on = len(name) - len(name.lstrip("C"))
            co = len(name) - len(name.rstrip("C"))
            onsets = [[]] if on == 0 else [[c] for c in ph.consonants] if on == 1 else [list(x) for x in ph.onset_clusters]
            codas = [[]] if co == 0 else [[c] for c in ph.coda_consonants] if co == 1 else [list(x) for x in ph.coda_clusters]
            for o in onsets:
                for v in ph.vowels:
                    for c in codas:
                        cand = tuple(o + [v] + c)
                        if cand in seen or not valid_word(self.spec, list(cand)):
                            continue
                        seen.add(cand)
                        w = tweight
                        for p_ in cand:
                            w *= ph.vowel_weights.get(p_) or ph.consonant_weights.get(p_, 1.0)
                        out.append((cand, w))
        return out

    def _plan_short_stems(self):
        """Estimate how many mutually distinguishable one-syllable stems fit, and keep 60% of that for
        stems (the rest of the short-syllable space is left for modified roots and other words)."""
        if hasattr(self, "short_all"):
            return
        self.short_all = self._short_candidates()
        # one- and two-letter forms are kept for the short common words; ordinary stems use longer ones
        self.short_cands = [(t, w) for t, w in self.short_all if self.letters(t) > TINY]
        self.small_cands = [(t, w * (3.0 if self.letters(t) <= TINY else 1.0))
                            for t, w in self.short_all if len(t) <= 3]
        if self.budget is None:
            idx = NearIndex()
            for t in self.reserved:
                idx.add(t)
            size = 0
            for t, _ in sorted(self.short_cands, key=lambda x: -x[1]):
                if not idx.near(t) and not idx.has(t):
                    idx.add(t)
                    size += 1
            self.budget = {"one_syllable_capacity": size, "cap1": max(6, int(.6 * size))}
        self.cap1 = self.budget["cap1"]

    def _pick_short_stem(self, fam):
        leak = tiny_leak(self.spec.seed, "stem:" + fam, self.gen("tiny_word_leak", .05))
        surv = [(t, w) for t, w in (self.short_all if leak else self.short_cands)
                if t not in self.all_forms and t not in self.reserved
                and not self.root_index.near(t) and t not in self.deriv]
        r = rng_for(self.spec.seed, "shortstem", fam, self._bump("stem:" + fam))
        for _ in range(80):
            if not surv:
                return None
            i = r.choices(range(len(surv)), [w for _, w in surv])[0]
            t = surv.pop(i)[0]
            if self._check(t, None, 0, tiny_ok=leak):
                return list(t)
        return None

    # -- the short common words: efficient (one-syllable, light) forms, allocated before everything else
    def _small_family(self, fam) -> bool:
        roots = self._fam_roots(fam)
        return bool(roots) and roots[0] in SHORT and is_efficient(self.spec.seed, roots[0], self.gen("short_word_efficiency", 1.0))

    def _pick_small(self, key):
        r = rng_for(self.spec.seed, "smallform", key, self._bump(key))
        for level in (0, 1):   # prefer forms clear of every other root; short words may settle for ones that merely differ from their neighbours by one sound
            surv = [(t, w) for t, w in self.small_cands
                    if t not in self.all_forms and t not in self.reserved and t not in self.deriv]
            for _ in range(160):
                if not surv:
                    break
                k = r.choices(range(len(surv)), [w for _, w in surv])[0]
                t = surv.pop(k)[0]
                if self._check(t, None, 0, tiny_ok=True, near=not level):
                    return list(t)
        return None

    def phase_small(self):
        self._plan_short_stems()
        seed = self.spec.seed
        todo = sorted((c for c in self.vocab if c in SHORT and c not in self.recipes
                       and c not in self.root_family and c not in self.entries),
                      key=lambda c: (-self.f(c), c))   # the most common words choose first
        for cid in todo:
            if not is_efficient(seed, cid, self.gen("short_word_efficiency", 1.0)):
                continue
            flat = self._pick_small(cid)
            if flat:
                self._index(tuple(flat), None, True)
                self._entry(cid, flat, "free", attempt=0, relaxed=0, short=True)

    def _accept_stem(self, fam, cand, tier, gtier, sibling_of=None):
        cand = list(cand)
        self.stems[fam] = {"phonemes": cand, "sibling_of": sibling_of, "tier": tier, "group_tier": gtier,
                           "syllables": sum(1 for p in cand if p in self.V) or 1}
        self._index(tuple(cand), fam, True)

    def _alloc_stem(self, fam, base_fam, tier, gtier):
        seed, bump = self.spec.seed, self._bump("stem:" + fam)
        n_short = sum(1 for s in self.stems.values() if s["syllables"] == 1 and not s.get("small"))
        short_ok = n_short < self.cap1
        base = self.stems[base_fam] if base_fam else None
        if self._small_family(fam):   # a family of short common words (this/that/here/now, who/what/which ...)
            cand = self._pick_small("stem:" + fam)
            if cand:
                self._accept_stem(fam, cand, tier, gtier)
                self.stems[fam]["small"] = True
                return
        leak = tiny_leak(seed, "stem:" + fam, self.gen("tiny_word_leak", .05))
        if base:  # siblings share the base stem's whole first syllable, or are a small variant of it
            bp = base["phonemes"]
            for attempt in range(120):
                r = rng_for(seed, "stem", fam, bump, attempt)
                if base["syllables"] > 1 or short_ok:
                    cand = self._sibling_variant(bp, r, attempt)
                else:  # budget spent: base syllable + a lexical syllable
                    cand = glue(self.spec, self.table, bp, r.choice(self.table["formatives"]))
                if cand is None or not valid_word(self.spec, cand) or pdist(bp, cand) < MIN_DIST:
                    continue
                if self._check(tuple(cand), None, 0, tiny_ok=leak):
                    self._accept_stem(fam, cand, tier, gtier, base_fam)
                    return
        if short_ok:
            cand = self._pick_short_stem(fam)
            if cand:
                self._accept_stem(fam, cand, tier, gtier)
                return
        for attempt in range(900):  # multi-syllable stem
            r = rng_for(seed, "stem2", fam, bump, attempt)
            n, cv = (2, True) if attempt < 250 else (2, False) if attempt < 450 else (3, True)
            cand = _flat([_syllable(self.spec, r, i == 0, force_cv=cv) for i in range(n)])
            if valid_word(self.spec, cand) and self._check(tuple(cand), None, 0 if attempt < 700 else 2, tiny_ok=leak):
                self._accept_stem(fam, cand, tier, gtier)
                return
        raise GenError(f"no stem found for family {fam}")

    def _sibling_variant(self, base, r, attempt):
        V = self.V
        cand = list(base)
        if attempt % 2 == 0:  # change the vowel, keep onset and coda
            idx = [i for i, p in enumerate(cand) if p in V]
            others = [v for v in self.ph.vowels if v != cand[idx[0]]]
            if not others:
                return None
            cand[idx[0]] = r.choice(others)
            return cand
        if cand[-1] in V:  # add a coda
            coda = self.ph.coda_consonants
            return cand + [r.choice(coda)] if coda else None
        return cand[:-1]  # drop the coda

    def phase_stems(self):
        self._plan_short_stems()
        base_of, group_of = {}, {}
        for g, fams in self.rm.get("sibling_groups", {}).items():
            for f in fams:
                group_of[f] = fams[0]
            for f in fams[1:]:
                base_of[f] = fams[0]
        order = {f: i for i, f in enumerate(self.rm["families"])}
        todo = [f for f in self.rm["families"] if f not in self.stems and self._fam_roots(f)]
        tier_of = {f: self.tier(self._fam_roots(f)[0]) for f in todo}
        gtier: dict = {}
        gfreq: dict = {}
        for fm in todo:  # a sibling group is as common as its most common member
            g = group_of.get(fm, fm)
            gtier[g] = min(gtier.get(g, 9), tier_of[fm])
            gfreq[g] = max(gfreq.get(g, 0), self.f(self._fam_roots(fm)[0]))
        gt = lambda f: gtier[group_of.get(f, f)]
        gf = lambda f: gfreq[group_of.get(f, f)]
        for fam in sorted(todo, key=lambda f: (-gf(f), order[f])):  # most common concepts pick first
            if fam in self.stems:
                continue
            base = base_of.get(fam)
            if base and base not in self.stems and base in self.rm["families"] and self._fam_roots(base):
                self._alloc_stem(base, None, self.tier(self._fam_roots(base)[0]), gt(fam))
            self._alloc_stem(fam, base if base in self.stems else None, tier_of[fam], gt(fam))

    # ------------------------------------------------------------------ phase B: family roots
    def _pick(self, r, pool, weights):
        return r.choices(pool, [weights[p] for p in pool])[0]

    def _op_weights(self, attempt, f=.25):
        m = self.spec.morphology
        typ = m.typology
        prefix_ok = m.affix_position in ("prefixing", "mixed") or typ == "polysynthetic"
        base = {"isolating": {"vowel": .3, "onset": .25, "coda": .25, "redup": .1, "suffix": .1},
                "agglutinative": {"suffix": .5, "prefix": .1, "coda": .1, "vowel": .1, "onset": .05, "combo": .15},
                "fusional": {"suffix": .3, "vowel": .3, "coda": .1, "onset": .1, "combo": .2},
                "polysynthetic": {"prefix": .3, "suffix": .35, "combo": .15, "coda": .1, "vowel": .1}}[typ]
        w = dict(base)
        if not prefix_ok and "prefix" in w:
            w["suffix"] = w.get("suffix", 0) + w.pop("prefix")
        if typ == "isolating" and attempt >= 80:
            w = {"suffix": .4, "combo": .2, "vowel": .2, "onset": .2}
        if attempt >= 300:
            return {"suffix": .5, "suffix2": .5}
        longer = {"suffix": 1, "prefix": 1, "redup": 1, "combo": 1}  # ops that add length
        scale = min(1.7, max(.35, 1.58 - 2.31 * f))
        return {k: v * (scale if k in longer else 1.0) for k, v in w.items()}

    def _apply_op(self, op, stem, r):
        ph, V = self.ph, self.V
        t = self.table
        stem = list(stem)
        if op == "vowel":
            idx = [i for i, p in enumerate(stem) if p in V]
            i = idx[0] if r.random() < .6 else idx[-1]
            others = [v for v in self.lex_v if v != stem[i]]
            if not others:
                return None
            stem[i] = self._pick(r, others, ph.vowel_weights)
            return stem
        if op == "onset":
            c = self._pick(r, self.lex_c, ph.consonant_weights)
            if stem[0] in V:
                return [c] + stem
            if c == stem[0]:
                return None
            stem[0] = c
            return stem
        if op == "coda":
            pool = [c for c in ph.coda_consonants if c in self.lex_c] or list(ph.coda_consonants)
            if not pool:
                return None
            c = self._pick(r, pool, ph.consonant_weights)
            if stem[-1] in V:
                return stem + [c]
            if c == stem[-1]:
                return None
            stem[-1] = c
            return stem
        if op in ("suffix", "prefix"):
            f = r.choice(t["formatives"])
            return glue(self.spec, t, stem, f) if op == "suffix" else glue(self.spec, t, f, stem)
        if op == "suffix2":
            f1, f2 = r.choice(t["formatives"]), r.choice(t["formatives"])
            return glue(self.spec, t, glue(self.spec, t, stem, f1), f2)
        if op == "redup":
            if sum(p in V for p in stem) != 1:
                return None
            return glue(self.spec, t, stem, stem)
        if op == "combo":
            a, b = r.sample(["vowel", "onset", "coda", "suffix"], 2)
            if "suffix" in (a, b):
                a, b = (b, a) if a == "suffix" else (a, b)  # suffix last
            first = self._apply_op(a, stem, r)
            return None if first is None else self._apply_op(b, first, r)
        return None

    def phase_family_roots(self):
        for fam, roots in self.rm["families"].items():
            stem = self.stems.get(fam)
            if not stem:
                continue
            for root in roots:
                if root not in self.vocab or root in self.entries:
                    continue
                if root == roots[0]:
                    self._entry(root, stem["phonemes"], "head", family=fam, recipe=None)
                    continue
                self._make_modified(root, fam, stem["phonemes"])

    def _make_modified(self, root, fam, stem):
        small = root in SHORT and is_efficient(self.spec.seed, root, self.gen("short_word_efficiency", 1.0)) and self.stems[fam].get("small", False)
        leak = tiny_leak(self.spec.seed, root, self.gen("tiny_word_leak", .05))
        for attempt in range(900):
            r = rng_for(self.spec.seed, "famroot", root, self._bump(root), attempt)
            if small and attempt < 150:   # keep it one syllable: change a sound, do not add one
                w = {"vowel": .5, "onset": .3, "coda": .2}
            else:
                w = self._op_weights(attempt, self.f(root))
            op = r.choices(list(w), list(w.values()))[0]
            cand = self._apply_op(op, stem, r)
            if cand is None or SPACE in cand or not valid_word(self.spec, cand):
                continue
            level = 0 if small and attempt < 300 else self._level(attempt)   # a longer form beats a relaxed one
            if self._check(tuple(cand), fam, level, tiny_ok=small or root in SHORT or leak):
                self._index(tuple(cand), fam, True)
                self._entry(root, cand, "family", family=fam, op=op, attempt=attempt, relaxed=level,
                            intact=_contains(cand, stem))
                return
        raise GenError(f"no form found for family root {root}")

    # ------------------------------------------------------------------ phase C: free and bound roots
    def phase_free(self):
        free = sorted(c for c in self.vocab if c not in self.recipes and c not in self.root_family
                      and c not in self.entries)
        bound = [b for b in self.rm.get("bound_roots", []) if b not in self.entries]
        for cid in free + bound:
            concept = self.vocab.get(cid, {"concept_id": cid, "lemma": cid.lstrip("@"), "is_function": False})
            for attempt in range(900):
                r = rng_for(self.spec.seed, "rootword", cid, self._bump(cid), attempt)
                cand = _flat(make_word(self.spec, r, self._n_syllables(r, concept, attempt, self.f(cid))))
                if not valid_word(self.spec, cand):
                    continue
                level = self._level(attempt)
                if self._check(tuple(cand), None, level, tiny_ok=cid in SHORT or tiny_leak(self.spec.seed, cid, self.gen("tiny_word_leak", .05))):
                    self._index(tuple(cand), None, True)
                    self._entry(cid, cand, "bound" if cid.startswith("@") else "free",
                                attempt=attempt, relaxed=level)
                    break
            else:
                raise GenError(f"no form found for {cid}")

    # ------------------------------------------------------------------ phase D: derived words
    def _eval(self, node, kind="affix"):
        if isinstance(node, str):
            return self._flat_of(node)
        if node["op"] == "same":
            return self._eval(node["base"], kind)
        if node["op"] == "derive":
            return apply_relation(self.spec, self.table, self._eval(node["base"]), node["rel"], kind)
        parts = [self._eval(p) for p in node["parts"]]
        out = parts[0]
        for p in parts[1:]:
            out = join(self.spec, self.table, out, p, "compound")
        return out

    def _flat_of(self, ref):
        if ref not in self.entries:
            if ref not in self.recipes:
                raise GenError(f"no form for {ref!r}")
            self._derive(ref)
        return list(self.entries[ref]["phonemes"])

    def _derive(self, cid):
        node = self.recipes[cid]
        flat = self._eval(node, "affix_noelide" if self.bumps.get("join:" + cid) else "affix")
        kind = "alias" if node["op"] == "same" else "compound" if node["op"] == "compound" else "derived"
        extra = {"alias_of": node["base"]} if kind == "alias" and isinstance(node["base"], str) else {}
        e = self._entry(cid, flat, kind, recipe=recipe_text(node), **extra)
        if kind != "alias":
            self.all_forms.add(tuple(flat))
            self.rom_forms.add(self.romstr(flat))
        return e

    def phase_derived(self):
        for cid in sorted(self.vocab):
            if cid in self.recipes and cid not in self.entries:
                self._derive(cid)

    # ------------------------------------------------------------------ collisions
    def collisions(self):
        by = defaultdict(list)
        for cid, e in self.entries.items():
            if e["kind"] != "alias" and not e["retired"]:
                by[e["form"]].append(cid)
        return [sorted(g) for g in by.values() if len(g) > 1 and any(c not in self.frozen for c in g)]

    def _leaves(self, ref, out):
        if isinstance(ref, dict):
            for d in ([ref["base"]] if ref["op"] != "compound" else ref["parts"]):
                self._leaves(d, out)
        elif ref in self.recipes:
            self._leaves(self.recipes[ref], out)
        else:
            out.add(ref)

    def pick_bumpable(self, group):
        leaves = set()
        for cid in group:
            if cid not in self.frozen:
                self._leaves(cid, leaves)
        cands = [c for c in leaves if c not in self.frozen and self.entries[c]["kind"] in ("free", "bound", "family")]
        if not cands:
            return None
        order = {"free": 0, "bound": 1, "family": 2}
        return min(cands, key=lambda c: (order[self.entries[c]["kind"]], c))


def _empty_state(spec):
    return {"table": build_table(spec), "stems": {}, "entries": [], "stem_budget": None, "plan": None}


MAX_ROUNDS = 30
PATIENCE = 5


def extend(spec, vocab, rootmap, state=None, freq=None):
    """Add every concept the state does not have yet. Existing entries are never modified (only their
    `retired` flag may change). Returns (state, report).

    Each round regenerates all new words; collisions between different concepts are removed by
    re-rolling a root (or switching off vowel elision). Words that can still be read as another word plus
    an affix ("false parses") are reduced the same way until improvement stalls; the best round is kept
    and any remainder is reported by verify()."""
    state = state or _empty_state(spec)
    rootmap = adapt_rootmap(rootmap, spec.morphology.gender_base)
    ventries = {e["concept_id"]: e for e in vocab["entries"]}
    fmap = {c: f_of(ventries.get(c), freq) for c in set(rootmap["recipes"]) | set(rootmap["root_family"])}
    plan = make_plan(rootmap, fmap, spec.seed, state.get("plan"), (spec.tuning or {}).get("gen"))   # earlier decisions stand; only new concepts are decided
    rootmap = apply_plan(rootmap, plan)
    bumps: dict = {}
    best, stale = None, 0
    for rnd in range(MAX_ROUNDS):
        ctx = _Ctx(spec, rootmap, vocab, state, bumps, freq)
        ctx.phase_small()
        ctx.phase_stems()
        ctx.phase_family_roots()
        ctx.phase_free()
        ctx.phase_derived()
        coll = ctx.collisions()
        if coll:
            changed = False
            for group in coll:
                derived = [c for c in group if c not in ctx.frozen and ctx.entries[c]["kind"] == "derived"
                           and not bumps.get("join:" + c)]
                if derived:  # structural collision between derived words: switch off elision for one
                    bumps["join:" + derived[-1]] = 1
                    changed = True
                    continue
                leaf = ctx.pick_bumpable(group)
                if leaf:
                    bumps[leaf] = bumps.get(leaf, 0) + 1
                    changed = True
            if not changed:
                raise GenError(f"unresolvable form collision: {coll[:3]}")
            continue
        fp = find_false_parses(spec, ctx.table, ctx.recipes, list(ctx.entries.values()))
        fp = [(c, srcs) for c, srcs in fp if c not in ctx.frozen or any(x not in ctx.frozen for x, _ in srcs)]
        if best is None or len(fp) < best[0]:
            best, stale = (len(fp), ctx, rnd), 0
        else:
            stale += 1
        if not fp or stale >= PATIENCE:
            break
        moved = False
        for c, srcs in fp:
            if c not in ctx.frozen and ctx.entries[c]["kind"] == "derived" and not bumps.get("join:" + c):
                bumps["join:" + c] = 1  # first remedy: no vowel elision
                moved = True
                continue
            leaf = ctx.pick_bumpable([c] + [x for x, _ in srcs])  # then: re-roll a root involved
            if leaf:
                bumps[leaf] = bumps.get(leaf, 0) + 1
                moved = True
        if not moved:
            break
    if best is None:
        raise GenError("could not resolve form collisions")
    _, ctx, rnd = best

    report = {"added": [c for c in ctx.new if not c.startswith("@")], "retired": [], "unretired": [],
              "collision_rounds": rnd}
    for cid, e in ctx.entries.items():
        if cid.startswith("@"):
            continue
        gone = cid not in ctx.vocab
        if gone and not e["retired"]:
            report["retired"].append(cid)
        if not gone and e["retired"]:
            report["unretired"].append(cid)
        e["retired"] = gone
    out = {"table": state["table"], "stems": ctx.stems, "stem_budget": ctx.budget,
           "entries": [ctx.entries[k] for k in sorted(ctx.entries)], "plan": plan}
    return out, report


def build_language(spec, vocab, rootmap, freq=None):
    return extend(spec, vocab, rootmap, None, freq)


def find_false_parses(spec, table, recipes, entries) -> list:
    """Words that can also be read as (another word + a relation affix). Returns [(cid, [sources])]."""
    produced = defaultdict(set)
    for e in entries:
        if e["kind"] == "bound" or e["retired"]:
            continue
        for rel in RELATIONS:
            produced[tuple(apply_relation(spec, table, e["phonemes"], rel))].add((e["concept_id"], rel))
    out = []
    for e in entries:
        if e["kind"] in ("alias", "bound") or e["retired"]:
            continue
        srcs = produced.get(tuple(e["phonemes"]), set())
        own = None
        if e["kind"] == "derived":
            node = recipes.get(e["concept_id"])
            if node and node["op"] == "derive" and isinstance(node["base"], str):
                own = (node["base"], node["rel"])
        bad = [x for x in srcs if x != own and x[0] != e["concept_id"]]
        if bad:
            out.append((e["concept_id"], sorted(bad)[:2]))
    return out


# ---------------------------------------------------------------------- verification and report
def verify(spec, rootmap, state) -> dict:
    """Quality and ambiguity checks on a finished lexicon. Pure function of the state."""
    rootmap = apply_plan(adapt_rootmap(rootmap, spec.morphology.gender_base), state.get("plan"))
    table, entries = state["table"], [e for e in state["entries"] if not e["retired"]]
    forms = defaultdict(list)
    for e in entries:
        if e["kind"] != "alias":
            forms[e["form"]].append(e["concept_id"])
    duplicates = {f: c for f, c in forms.items() if len(c) > 1}

    roots = [e for e in entries if e["kind"] in ROOT_KINDS]
    # Two short common words may differ by a single similar sound (ta / da): context tells them apart and every
    # real language does it. Every other pair counts.
    idx, idx_other = NearIndex(), NearIndex()
    for e in roots:
        idx.add(e["phonemes"])
        if e["concept_id"] not in SHORT:
            idx_other.add(e["phonemes"])
    near_pairs = sum((idx_other if e["concept_id"] in SHORT else idx).near_count(e["phonemes"]) for e in roots) // 2

    fam_min, fam_bad = None, 0
    by_fam = defaultdict(list)
    for e in roots:
        if e["family"]:
            by_fam[e["family"]].append(e)
    for fam, es in by_fam.items():
        for i in range(len(es)):
            for j in range(i + 1, len(es)):
                d = pdist(es[i]["phonemes"], es[j]["phonemes"])
                fam_min = d if fam_min is None else min(fam_min, d)
                fam_bad += d < MIN_DIST

    false_parses = find_false_parses(spec, table, rootmap["recipes"], entries)

    fam_entries = [e for e in entries if e["kind"] == "family"]
    stems = state["stems"]
    kinds = defaultdict(int)
    for e in entries:
        kinds[e["kind"]] += 1
    syl = lambda es: sum(len(e["syllables"]) for e in es) / max(len(es), 1)
    return {
        "entries": len(entries), "kinds": dict(kinds), "duplicate_forms": len(duplicates),
        "near_root_pairs": near_pairs, "family_min_distance": None if fam_min is None else round(fam_min, 2),
        "family_pairs_below_min": fam_bad, "false_parses": len(false_parses),
        "false_parse_examples": false_parses[:5],
        "relaxed_roots": sum(1 for e in roots if e.get("relaxed")),
        "stems": len(stems), "stems_multi_syllable": sum(1 for s in stems.values() if s["syllables"] > 1),
        "family_roots_keeping_whole_stem": round(sum(1 for e in fam_entries if e.get("intact")) / max(len(fam_entries), 1), 2),
        "mean_syllables_by_tier": {t: round(syl([e for e in entries if e.get("tier") == t and e["kind"] != "bound"]), 2)
                                   for t in (1, 2, 3)},
        "stems_by_syllables": {n: sum(1 for s in stems.values() if s["syllables"] == n) for n in (1, 2, 3)},
        "mean_syllables_function": round(syl([e for e in entries if e["is_function"]]), 2),
        "mean_syllables_content": round(syl([e for e in entries if not e["is_function"] and e["kind"] != "bound"]), 2),
        "disjoint_sound_classes": [table["sound_classes"]["disjoint_consonants"], table["sound_classes"]["disjoint_vowels"]],
    }
