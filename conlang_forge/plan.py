"""Per-language plan: how the root map is realised, driven by word frequency instead of a cutoff.

Natural languages tend to give their most frequent words short, simple, unrelated forms, while rarer
words are more often derived or compounded from a base. The root map is the *idealised* structure; this
step applies that tendency probabilistically for one language:

  * a derived word becomes an independent root with p = f^1.5 * independence(relation)
  * a compound becomes a simple root with p = f^1.5 * COMPOUND_WEIGHT
  * a non-head family member leaves its family with p = f^1.5 * LEAVE_WEIGHT (families keep >= 2 roots)
  * a family's head (the member that is the bare stem) is drawn with weight f^2 + eps, so the most
    frequent member usually, but not always, is the head

f is the commonness score (frequency.py). Every draw is keyed on (seed, concept), so decisions are
reproducible, and they are stored in the language state: a vocabulary upgrade only decides the *new*
concepts and never revisits an old one, even if the frequency data changes later.
"""
from __future__ import annotations

import copy

from .relations import DEFAULT_INDEPENDENCE, INDEPENDENCE
from .wordgen import rng_for

COMPOUND_WEIGHT = .7
LEAVE_WEIGHT = .8
HEAD_EPS = .02
CURATED_HEAD_BONUS = 1.5


def make_plan(rm: dict, f: dict, seed, prior: dict | None = None, gen: dict | None = None) -> dict:
    """Decide what the language does with each concept of `rm` (already gender-adapted).

    `f` maps concept id -> commonness. `prior` is the plan stored by an earlier build; its decisions stand."""
    prior = prior or {}
    gen = gen or {}
    expo = gen.get("frequency_exponent", 1.5)                   # how strongly common words become independent roots
    cw = gen.get("compound_independence", COMPOUND_WEIGHT)
    lw = gen.get("family_leaving", LEAVE_WEIGHT)
    ds = gen.get("derivation_independence", 1.0)
    independent = dict(prior.get("independent", {}))   # concept -> "derivation" | "compound"
    kept = set(prior.get("kept", []))                  # derived/compound concepts decided to stay as written
    left = dict(prior.get("left_family", {}))          # concept -> family it left
    stayed = set(prior.get("stayed_in_family", []))
    heads = dict(prior.get("heads", {}))
    fget = lambda c: f.get(c, .25)
    pend = set(rm.get("pending", {}))   # planned words not in the vocabulary yet: decided when they arrive

    for c, node in sorted(rm["recipes"].items()):
        if c in independent or c in kept or node["op"] == "same":
            continue
        if node["op"] == "derive":
            p = fget(c) ** expo * min(1.0, INDEPENDENCE.get(node["rel"], DEFAULT_INDEPENDENCE) * ds)
            kind = "derivation"
        else:
            p = fget(c) ** expo * cw
            kind = "compound"
        if rng_for(seed, "plan-ind", c).random() < p:
            independent[c] = kind
        else:
            kept.add(c)

    for fam, roots in sorted(rm["families"].items()):
        for r in roots[1:]:
            if r in pend:
                continue
            if r in left or r in stayed or r in prior.get("heads", {}).values():
                continue
            if rng_for(seed, "plan-leave", r).random() < fget(r) ** expo * lw:
                left[r] = fam
            else:
                stayed.add(r)
        if fam not in heads:
            cands = [r for r in roots if r not in left and r not in pend]
            if cands:
                w = [fget(r) ** 2 + HEAD_EPS for r in cands]
                w[0] *= CURATED_HEAD_BONUS if cands[0] == roots[0] else 1
                heads[fam] = rng_for(seed, "plan-head", fam).choices(cands, w)[0]
    return {"independent": independent, "kept": sorted(kept), "left_family": left,
            "stayed_in_family": sorted(stayed), "heads": heads}


def apply_plan(rm: dict, plan: dict | None) -> dict:
    """The root map as this language realises it. Pure function of (rm, plan)."""
    if not plan:
        return rm
    rm = copy.deepcopy(rm)
    recipes, fams, rf = rm["recipes"], rm["families"], rm["root_family"]
    detached = []
    for c, kind in plan["independent"].items():
        if c in recipes:
            detached.append({"concept": c, "kind": kind})
            del recipes[c]
    dissolved = []
    for fam in list(fams):
        roots = list(fams[fam])
        gone = [r for r in roots if plan["left_family"].get(r) == fam]
        keep = [r for r in roots if r not in gone]
        pend = rm.get("pending", {})
        if sum(1 for r in keep if r not in pend) < 2:   # nothing left to share a stem with
            gone, keep = roots, []
        for r in gone:
            rf.pop(r, None)
            if plan["left_family"].get(r) == fam:
                detached.append({"concept": r, "kind": "family", "was": fam})
        if not keep:
            del fams[fam]
            dissolved.append(fam)
            continue
        head = plan["heads"].get(fam)
        if head in keep:
            keep.remove(head)
            keep.insert(0, head)
        fams[fam] = keep
    sg = {}
    for name, members in rm["sibling_groups"].items():
        members = [m for m in members if m in fams]
        if len(members) >= 2:
            sg[name] = members
    rm["sibling_groups"] = sg
    rm["detached"], rm["dissolved_families"] = detached, dissolved
    return rm
