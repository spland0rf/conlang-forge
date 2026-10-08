"""Show the same root families in several languages: python scripts/family_demo.py out.md"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from conlang_forge.export import summarize_spec
from conlang_forge.morph import render_flat
from conlang_forge.frequency import load_freq
from conlang_forge.rootgen import build_language, verify
from conlang_forge.roots import load_rootmap
from conlang_forge.spec import sample_spec
from conlang_forge.vocab import load_vocab

vocab = load_vocab(ROOT / "data/vocab/v1.2.json")
rm = load_rootmap(ROOT / "data/roots/v1.2.rootmap.json")
LANGS = [("A", 1, {"morphology.gender_base": "male"}),
         ("B", 11, {"morphology.typology": "agglutinative", "morphology.gender_base": "female"}),
         ("C", 12, {"morphology.typology": "isolating", "morphology.gender_base": "male"})]
SETS = [("dwellings: homes | larger buildings (tent, barn are outliers)", ["house", "home", "cottage", "hut", "apartment", "manor", "hotel", "inn", "tent", "barn"]),
        ("officials: sole rulers | professional representatives", ["president", "mayor", "chief", "dictator", "minister", "ambassador", "delegate", "judge", "jury"]),
        ("limbs: hand | foot | joints | limbs", ["hand", "finger", "thumb", "palm", "foot", "toe", "shoulder", "knee", "arm", "leg", "wing"]),
        ("birds and creeping things", ["bird", "feather", "hen", "chicken", "duck", "lizard", "spider", "insect"]),
        ("terrain: overland | holes in the ground", ["mountain", "hill", "valley", "canyon", "cave", "tunnel", "hole", "chasm", "abyss", "pit"]),
        ("opposites and size pairs (common ones tend to be unrelated words; ← shows a derivation)", ["big", "small", "new", "old", "begin", "end"]),
        ("less frequent opposites tend to stay related", ["near", "far", "guilty", "innocent", "wet", "dry", "soft", "hard"]),
        ("gender pairs (unmarked term depends on the language's setting)", ["king", "queen", "man", "woman", "father", "mother", "she", "he", "grandfather", "grandmother"]),
        ("friendly humanoids vs monsters (separate families)", ["elf", "dwarf", "monster", "orc", "goblin", "demon", "dragon", "hobgoblin", "giant", "troll", "ogre", "werewolf", "vampire", "ghost"]),
        ("water family", ["water", "river", "lake", "sea", "ocean", "rain"]),
        ("grammatical forms of one root", ["environment", "environmental", "act", "active", "actor", "activity", "react"]),
        ("frequent vs rare opposites (frequent pairs are usually unrelated words)", ["hot", "cold", "big", "small", "old", "new", "good", "bad", "strong", "weak", "fast", "slow", "early", "late"]),
        ("compounds", ["every", "everybody", "everyone", "everything", "everywhere"])]
FREQ = load_freq("data/vocab/v1.2.freq.json")
built = []
for tag, seed, pins in LANGS:
    spec = sample_spec(seed, pins)
    state, _ = build_language(spec, vocab, rm, FREQ)
    built.append((tag, spec, state, {e["concept_id"]: e for e in state["entries"]}, verify(spec, rm, state)))
L = ["# Root families across three sample languages", "",
     "The same root map, three languages. Words in one family share a stem; derived words add a regular affix.",
     "Frequent words tend to be short and to stand alone; rare words tend to be derived or compound (decided per language, by chance weighted by frequency).", ""]
for tag, spec, state, E, q in built:
    A = state["table"]["affixes"]
    ex = ", ".join(f"{r} {render_flat(spec, A[r]['phonemes'])[0]}" for r in ("PLURAL", "ADJ", "AGENT", "NEG"))
    L += [f"**Language {tag}: {spec.name}** — {spec.morphology.gender_base}-unmarked gender, {spec.morphology.typology}, {len(spec.phonology.consonants)} consonants, "
          f"{len(spec.phonology.vowels)} vowels. One-syllable stems: {q['stems_by_syllables'][1]}/{q['stems']}. "
          f"Affixes: {ex}.", ""]
for title, words in SETS:
    L += [f"## {title}", "", "| English | " + " | ".join(f"{t}: {s.name}" for t, s, *_ in built) + " |", "|---|" + "---|" * len(built)]
    for w in words:
        L.append(f"| {w} | " + " | ".join(E[w]['form'] + (f" ← {E[w]['recipe']}".replace("|", "\\|") if E[w]['kind'] in ('derived', 'compound') else "") for _, _, _, E, _ in built) + " |")
    L.append("")
L += ["## How often a word has its own root, by frequency", "",
      "Share of the root map's derived words and compounds that this language made independent, by commonness f.", "",
      "| f | words | " + " | ".join(t for t, *_ in built) + " |", "|---|---|" + "---|" * len(built)]
rec = rm["recipes"]
bins = [("f ≥ 0.7 (rank ≲ 200)", .7, 9), ("0.4 – 0.7", .4, .7), ("0.2 – 0.4", .2, .4), ("0.1 – 0.2", .1, .2), ("< 0.1", 0, .1)]
for label, lo, hi in bins:
    ids = [c for c, n in rec.items() if n["op"] != "same" and lo <= built[0][3][c]["f"] < hi]
    cells = [f"{sum(1 for c in ids if E[c]['kind'] not in ('derived', 'compound')) / max(len(ids), 1):.0%}" for _, _, _, E, _ in built]
    L.append(f"| {label} | {len(ids)} | " + " | ".join(cells) + " |")
L.append("")
L += ["## Quality checks", "", "| Check | " + " | ".join(t for t, *_ in built) + " |", "|---|" + "---|" * len(built)]
for label, key in [("Entries", "entries"), ("Duplicate forms", "duplicate_forms"), ("Near-identical root pairs", "near_root_pairs"),
                   ("Family pairs below min distance", "family_pairs_below_min"), ("Words readable as another word + affix", "false_parses"),
                   ("Family roots keeping the whole stem", "family_roots_keeping_whole_stem")]:
    L.append(f"| {label} | " + " | ".join(str(q[key]) for *_, q in built) + " |")
Path(sys.argv[1] if len(sys.argv) > 1 else "family_demo.md").write_text("\n".join(L) + "\n", encoding="utf-8")
