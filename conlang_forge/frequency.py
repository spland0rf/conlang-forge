"""English word-frequency data and the commonness score f used by the generator.

Main source: the New General Service List v1.2 stats file (2,809 lemmas ranked by SFI rank across all parts of
speech; columns `Lemma,SFI Rank,...`). Optional extra sources: one-column ranked lists (`Rank,<Word>`), used only
for words the main list lacks, with their rank multiplied by EXTRA_RANK_FACTOR (they rank within one part of speech).
Output: `{"ranks": {concept_id: rank}}`, stored next to the vocabulary as `<version>.freq.json`.

`commonness(rank)` is a smooth score in (0, 1]: about 1 for the commonest words, 0.5 at rank 500, and falling off
slowly. There is no cutoff anywhere; the generator turns f into *probabilities* (see plan.py) and into word-length
scaling (see rootgen.py). A word with no rank is rare for our purposes (see UNRANKED_F), except function words.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .vocab import default_tier

IRREGULAR = {"went": "go", "said": "say", "was": "be", "were": "be", "been": "be", "had": "have", "has": "have",
             "did": "do", "does": "do", "made": "make", "found": "find", "saw": "see", "took": "take",
             "got": "get", "began": "begin", "men": "man", "feet": "foot", "children": "child"}
HALF_RANK, STEEPNESS = 500.0, 1.2
EXTRA_RANK_FACTOR = 5          # a rank within one part of speech ~ 5x that rank overall
FUNCTION_F = 0.6               # a function word the list does not rank
def commonness(rank: float) -> float:
    return 1.0 / (1.0 + (rank / HALF_RANK) ** STEEPNESS)


def _norm(w: str) -> str:
    return IRREGULAR.get(w.strip().lower(), w.strip().lower())


def read_ngsl(path: str | Path) -> list:
    out = []
    for r in csv.DictReader(open(path, newline="", encoding="utf-8-sig")):
        if r.get("Lemma") and (r.get("SFI Rank") or "").strip().isdigit():
            out.append((int(r["SFI Rank"]), _norm(r["Lemma"])))
    return out


def read_ranked(path: str | Path) -> list:
    rows = list(csv.reader(open(path, newline="", encoding="utf-8-sig")))
    return [(int(r[0]), _norm(r[1])) for r in rows[1:] if len(r) >= 2 and r[0].strip().isdigit() and r[1].strip()]


def build_freq(ngsl_path, vocab: dict, extras: list = ()) -> dict:
    """{concept_id: rank}. A lemma ranks every sense of it (case, case#court, ...). Returns the freq dict
    plus a coverage report."""
    by_lemma = defaultdict(list)
    for e in vocab["entries"]:
        by_lemma[e["lemma"].lower()].append(e["concept_id"])
    ranks, missing_main, from_extra = {}, [], []
    for rank, w in read_ngsl(ngsl_path):
        if w not in by_lemma:
            missing_main.append(w)
            continue
        for cid in by_lemma[w]:
            ranks[cid] = min(rank, ranks.get(cid, rank))
    for p in extras:
        for rank, w in read_ranked(p):
            for cid in by_lemma.get(w, []):
                if cid not in ranks:
                    ranks[cid] = rank * EXTRA_RANK_FACTOR
                    from_extra.append(cid)
    unranked = sorted(e["concept_id"] for e in vocab["entries"] if e["concept_id"] not in ranks)
    return {"format": "conlang-forge-freq/2", "vocab_version": vocab["version"],
            "sources": [Path(ngsl_path).name] + [Path(p).name for p in extras],
            "ranks": dict(sorted(ranks.items(), key=lambda kv: kv[1])),
            "report": {"ranked": len(ranks), "vocab_words_without_rank": len(unranked),
                       "list_words_not_in_vocab": len(missing_main), "taken_from_extra_lists": from_extra}}


def save_freq(freq: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(freq, ensure_ascii=False, indent=1), encoding="utf-8")


def load_freq(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


UNRANKED_F = commonness(4000)


def f_of(entry: dict | None, freq: dict | None) -> float:
    """Commonness of one concept: from its rank if it has one; otherwise low (function words excepted)."""
    if entry is None:
        return UNRANKED_F
    rank = ((freq or {}).get("ranks") or {}).get(entry["concept_id"])
    if rank is not None:
        return commonness(rank)
    if freq is None:   # no frequency data at all: fall back to the coarse tier
        return {1: 0.6, 2: 0.25, 3: 0.08}[entry.get("tier") or default_tier(entry)]
    return FUNCTION_F if entry.get("is_function") else UNRANKED_F
