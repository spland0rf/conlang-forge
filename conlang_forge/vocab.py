"""Versioned Reduced English Dictionary: loading, cleaning, diffing.

A vocab version is a JSON document. Each entry has a stable `concept_id`
(the lemma, or lemma#sense) that survives across versions, so languages
can be upgraded without existing words changing.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path

INVISIBLE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
SENSE_RE = re.compile(r"^([a-z][a-z'\-]*) \(([a-z][a-z ]*)\)$")
LEMMA_RE = re.compile(r"^[a-z][a-z'\-]*$")

# Function words get shorter forms in generated languages. Only those that
# actually appear in the vocabulary are flagged.
FUNCTION_WORDS = frozenset("""
a an the this that these those my your his her its our their mine yours hers
ours theirs i me you he she it we they him them us myself yourself himself
herself itself ourselves themselves who whom whose what which when where why
how of in on at to for with by from about above across after against along
among around before behind below beneath beside between beyond down during
except inside into like near off onto out outside over past since through
throughout toward towards under until up upon within without and or but nor
so yet if because although while unless than as not no yes is am are be been
being do does have can could will would shall should may might must there
here all any some each every both few many more most other another such
only own same too very just also then now again already always never ever
""".split())


def clean_token(raw: str) -> str:
    s = unicodedata.normalize("NFKC", raw)
    s = INVISIBLE.sub("", s).strip().lower()
    return re.sub(r"\s+", " ", s)


def _concept_id(lemma: str, sense: str | None) -> str:
    return f"{lemma}#{sense.replace(' ', '_')}" if sense else lemma


def build_vocab(source_csv: str | Path, manifest_path: str | Path) -> dict:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    fixes = {clean_token(k): clean_token(v) for k, v in manifest.get("fixes", {}).items()}
    quarantine = {clean_token(x) for x in manifest.get("quarantine", [])}
    restore = [clean_token(x) for x in manifest.get("restore", [])]
    tiers = {clean_token(w): int(t) for t, ws in manifest.get("tiers", {}).items() for w in ws}

    raw = Path(source_csv).read_bytes()
    rows: list[str] = []
    with open(source_csv, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if row:
                rows.append(row[0])

    report = {"rows_read": len(rows), "fixes_applied": [], "duplicates_merged": [],
              "quarantined": [], "restored": [], "needs_review": []}
    entries: dict[str, dict] = {}

    def add(token: str, origin: str) -> None:
        if not token:
            return
        if token in fixes:
            report["fixes_applied"].append(f"{token} -> {fixes[token]}")
            token = fixes[token]
        if token in quarantine:
            report["quarantined"].append(token)
            return
        m = SENSE_RE.match(token)
        if m:
            lemma, sense = m.group(1), m.group(2)
        elif LEMMA_RE.match(token):
            lemma, sense = token, None
        else:
            report["needs_review"].append(token)
            return
        cid = _concept_id(lemma, sense)
        if cid in entries:
            if origin == "source":
                report["duplicates_merged"].append(cid)
            return
        gloss = "I" if lemma == "i" else lemma
        if sense:
            gloss = f"{lemma} ({sense})"
        if origin == "restore":
            report["restored"].append(cid)
        entries[cid] = {"concept_id": cid, "lemma": lemma, "sense": sense, "gloss": gloss,
                        "is_function": sense is None and lemma in FUNCTION_WORDS, "tags": []}
        if cid in tiers:
            entries[cid]["tier"] = tiers[cid]

    for r in rows:
        add(clean_token(r), "source")
    for r in restore:
        add(r, "restore")

    return {
        "format": "conlang-forge-vocab/1",
        "version": manifest["version"],
        "notes": manifest.get("notes", ""),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "aliases": manifest.get("aliases", {}),
        "entries": [entries[k] for k in sorted(entries)],
        "report": report,
    }


def save_vocab(vocab: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(vocab, ensure_ascii=False, indent=1), encoding="utf-8")


def load_vocab(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def diff_vocab(old: dict, new: dict) -> dict:
    """Compare two vocab versions by concept_id, honoring the new version's aliases."""
    aliases = new.get("aliases", {})
    old_ids = {aliases.get(e["concept_id"], e["concept_id"]) for e in old["entries"]}
    new_ids = {e["concept_id"] for e in new["entries"]}
    return {"added": sorted(new_ids - old_ids), "removed": sorted(old_ids - new_ids),
            "unchanged": len(new_ids & old_ids)}


def default_tier(entry: dict) -> int:
    """Commonness tier: 1 = core (shortest stems), 2 = common, 3 = specialized (longest stems).

    Used when the vocab has no explicit `tier`. Heuristic: function words are core, and English word
    length is a rough proxy for rarity (Zipf's law of abbreviation). Real frequency data should replace
    this: put concept ids under "tiers" in the vocab manifest.
    """
    if entry.get("is_function"):
        return 1
    n = len(entry["lemma"])
    return 1 if n <= 4 else 2 if n <= 7 else 3
