"""Root map: links every vocab concept to a root via derivation / compounding, and groups
related roots into sound-sharing families.

The root map is a stable, versioned artifact. It is keyed by concept_id and stored beside the
vocab version it was built for. A new vocab version starts from a copy of the previous map;
words with no entry default to being their own free root, so only new words need review.

Text format (see data/roots/*.roots.txt):
    word = base +REL [+REL ...]       derivation (chains apply left to right)
    word = a | b [| c] [+REL ...]     compound (head-final), optional affixes
    word = base +SAME                 exact alias (spelling variant)
    @name                             declares a bound root (not a dictionary word)
    family NAME: w1 w2 ...            related roots that share an opening sound (at most 5 roots, 6 only with very strong affinity)
    ~word                             inside a family line: a word planned for a future vocabulary version
                                      (it keeps its place; it joins the family when the word is added)
    siblings GROUP: fam1 fam2 ...     families split from one natural group; sounds related, not identical
Concepts that are never defined are their own free roots.

Size rules: the cap (FAMILY_TARGET 5, hard FAMILY_MAX 6) applies ONLY to conceptual families.
Derivations and compounds are uncapped, because each is built algorithmically from its parts
and is therefore uniquely reconstructible.

A recipe node is JSON:  {"op": "derive", "base": REF, "rel": REL}
                        {"op": "compound", "parts": [REF, ...]}
                        {"op": "same", "base": REF}
where REF is a concept_id, "@bound", or a nested recipe node.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from .relations import RELATIONS, SAME

REL_SET = set(RELATIONS) | {SAME}
FAMILY_TARGET = 5  # normal cap per conceptual family
FAMILY_MAX = 6     # hard cap: a 6th root is allowed only when all members have a very strong affinity


class RootMapError(ValueError):
    pass


def _deps(node):
    if isinstance(node, str):
        yield node
    elif node["op"] == "compound":
        for p in node["parts"]:
            yield from _deps(p)
    else:
        yield from _deps(node["base"])


def recipe_text(node) -> str:
    if isinstance(node, str):
        return node
    if node["op"] == "compound":
        return " | ".join(recipe_text(p) for p in node["parts"])
    if node["op"] == "same":
        return f"{recipe_text(node['base'])} +SAME"
    return f"{recipe_text(node['base'])} +{node['rel']}"


def parse_roots(text: str, vocab: dict) -> dict:
    ids = {e["concept_id"] for e in vocab["entries"]}
    errors, warnings = [], []
    lines = [(n, l.strip()) for n, l in enumerate(text.splitlines(), 1)]
    bound = [l for _, l in lines if l.startswith("@") and "=" not in l]
    for b in bound:
        if not re.fullmatch(r"@[a-z]+", b):
            errors.append(f"bad bound root {b!r}")
    known = ids | set(bound)
    recipes, fam_lines, sib_lines = {}, {}, {}

    for n, line in lines:
        if not line or line.startswith("#") or (line.startswith("@") and "=" not in line):
            continue
        if line.startswith("siblings "):
            name, _, rest = line[9:].partition(":")
            if name.strip() in sib_lines:
                errors.append(f"line {n}: duplicate siblings group {name.strip()}")
            sib_lines[name.strip()] = (n, rest.split())
            continue
        if line.startswith("family "):
            name, _, rest = line[7:].partition(":")
            if name.strip() in fam_lines:
                errors.append(f"line {n}: duplicate family {name.strip()}")
            fam_lines[name.strip()] = (n, rest.split())
            continue
        lhs, sep, rhs = line.partition(" = ")
        lhs, rhs = lhs.strip(), rhs.strip()
        if not sep:
            errors.append(f"line {n}: cannot parse {line!r}")
            continue
        if lhs not in ids:
            errors.append(f"line {n}: {lhs!r} is not in the vocabulary")
            continue
        if lhs in recipes:
            errors.append(f"line {n}: {lhs!r} defined twice")
            continue
        base_part, *rels = re.split(r"\s+\+", rhs)
        parts = [p.strip() for p in base_part.split("|")]
        bad = [p for p in parts if p not in known]
        if bad:
            errors.append(f"line {n}: unknown concept(s) {bad}")
            continue
        if parts == [lhs]:
            errors.append(f"line {n}: {lhs!r} refers to itself")
            continue
        badrel = [r for r in rels if r not in REL_SET]
        if badrel:
            errors.append(f"line {n}: unknown relation(s) {badrel}")
            continue
        if SAME in rels and (len(rels) != 1 or len(parts) != 1):
            errors.append(f"line {n}: SAME must be the only relation on a single base")
            continue
        node = {"op": "compound", "parts": parts} if len(parts) > 1 else parts[0]
        for r in rels:
            node = {"op": "same", "base": node} if r == SAME else {"op": "derive", "base": node, "rel": r}
        if isinstance(node, str):
            errors.append(f"line {n}: {lhs!r} has no relation or compound")
            continue
        recipes[lhs] = node

    state = {}

    def visit(c, path):
        if state.get(c) == 2:
            return
        if state.get(c) == 1:
            errors.append("cycle: " + " -> ".join(path + [c]))
            return
        state[c] = 1
        if c in recipes:
            for d in _deps(recipes[c]):
                if not d.startswith("@"):
                    visit(d, path + [c])
        state[c] = 2

    for c in list(recipes):
        visit(c, [])
    if errors:
        raise RootMapError("\n".join(errors))

    def root_of(ref):
        while True:
            if isinstance(ref, dict):
                if ref["op"] == "compound":
                    raise RootMapError(f"compound {recipe_text(ref)!r} cannot be a family member")
                ref = ref["base"]
            elif ref in recipes:
                ref = recipes[ref]
            else:
                return ref

    families, root_family, pending = {}, {}, {}
    for name, (n, members) in fam_lines.items():
        roots = []
        for m in members:
            if m.startswith("~"):  # a word planned for a future vocabulary version: reserved a place in this family
                m = m[1:]
                if m in known:
                    warnings.append(f"line {n}: family {name}: {m!r} is in the vocabulary now; drop the ~")
                elif not re.fullmatch(r"[a-z]+", m) or m in pending or m in root_family:
                    errors.append(f"line {n}: family {name}: bad or repeated planned word {m!r}")
                else:
                    roots.append(m)
                    root_family[m] = name
                    pending[m] = name
                    continue
            if m not in known:
                errors.append(f"line {n}: family {name}: unknown {m!r}")
                continue
            try:
                r = root_of(m)
            except RootMapError as e:
                errors.append(f"line {n}: family {name}: {e}")
                continue
            if r in root_family and root_family[r] != name:
                errors.append(f"line {n}: family {name}: root {r!r} (from {m!r}) is already in family {root_family[r]!r}")
            elif r not in roots:
                roots.append(r)
                root_family[r] = name
        if len(roots) < 2:
            warnings.append(f"family {name} has fewer than 2 roots")
        if len(roots) > FAMILY_MAX:
            errors.append(f"family {name} has {len(roots)} roots; cap is {FAMILY_MAX} (normally {FAMILY_TARGET}). "
                          "The cap applies to conceptual families only.")
        families[name] = roots
    if errors:
        raise RootMapError("\n".join(errors))

    sibling_groups, seen_sib = {}, {}
    for name, (n, fams) in sib_lines.items():
        if len(fams) < 2:
            errors.append(f"line {n}: siblings {name} needs at least 2 families")
        for f in fams:
            if f not in families:
                errors.append(f"line {n}: siblings {name}: unknown family {f!r}")
            elif f in seen_sib:
                errors.append(f"line {n}: family {f!r} is in two sibling groups ({seen_sib[f]!r}, {name!r})")
            else:
                seen_sib[f] = name
        sibling_groups[name] = fams
    if errors:
        raise RootMapError("\n".join(errors))

    free = [c for c in sorted(ids) if c not in recipes]
    compounds = sum(1 for r in recipes.values() if r["op"] == "compound")
    aliases = sum(1 for r in recipes.values() if r["op"] == "same")
    stats = {
        "concepts": len(ids), "free_roots": len(free), "bound_roots": len(bound),
        "derived": len(recipes) - compounds - aliases, "compounds": compounds, "aliases": aliases,
        "families": len(families), "sibling_groups": len(sibling_groups), "roots_in_families": len(root_family),
        "planned_words": len(pending),
        "families_of_max": sorted(n for n, v in families.items() if len(v) > FAMILY_TARGET),
        "largest_family": max((len(v) for v in families.values()), default=0),
    }
    stats["roots_total"] = len(free) + len(bound)
    sib_members = {f for fs in sibling_groups.values() for f in fs}
    stats["root_groups"] = (len(families) - len(sib_members) + len(sibling_groups)
                            + sum(1 for r in free + bound if r not in root_family))
    return {"format": "conlang-forge-rootmap/1", "vocab_version": vocab["version"],
            "bound_roots": bound, "recipes": recipes, "families": families, "pending": pending,
            "root_family": root_family, "sibling_groups": sibling_groups,
            "stats": stats, "warnings": warnings}


def adapt_rootmap(rm: dict, gender_base: str = "male") -> dict:
    """Per-language view of a root map.

    The map is written with the male term of each gender pair as the unmarked root
    ("queen = king +FEMALE"). A language with gender_base="female" gets the mirror image: the female
    term is the unmarked root and takes the male term's place in its family, and the male term is
    derived ("king = queen +MALE"). Compound pairs follow ("grandmother = @grand | mother").
    """
    if gender_base != "female":
        return rm
    rm = copy.deepcopy(rm)
    recipes, fams, rf = rm["recipes"], rm["families"], rm["root_family"]
    pairs = {}
    for f, node in recipes.items():
        if node["op"] == "derive" and node["rel"] == "FEMALE":
            m = node["base"] if isinstance(node["base"], str) else next(
                (k for k, v in recipes.items() if v == node["base"] and k != f), None)
            if m is not None:
                pairs[f] = m
    female_of = {m: f for f, m in pairs.items()}

    def tr(x):
        if isinstance(x, str):
            return female_of.get(x, x)
        if x["op"] == "compound":
            return {"op": "compound", "parts": [tr(p) for p in x["parts"]]}
        return dict(x, base=tr(x["base"]))

    swapped = []
    for f, m in list(pairs.items()):
        old = recipes[f]
        if isinstance(old["base"], str):
            if m in recipes:  # the male term is itself derived: leave this pair as written
                continue
            del recipes[f]
        else:
            recipes[f] = tr(old["base"])
        recipes[m] = {"op": "derive", "base": f, "rel": "MALE"}
        for lst in fams.values():
            for i, r in enumerate(lst):
                if r == m:
                    lst[i] = f
        if m in rf:
            rf[f] = rf.pop(m)
        swapped.append(f)
    rm["gender_pairs_swapped"] = sorted(swapped)
    return rm


def build_rootmap(roots_txt: str | Path, vocab: dict) -> dict:
    return parse_roots(Path(roots_txt).read_text(encoding="utf-8"), vocab)


def save_rootmap(rm: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(rm, ensure_ascii=False, indent=1), encoding="utf-8")


def load_rootmap(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
