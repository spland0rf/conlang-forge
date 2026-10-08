"""Sample words from three very different test languages: python scripts/language_examples.py out.md"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from conlang_forge.frequency import load_freq
from conlang_forge.morph import render_flat
from conlang_forge.rootgen import build_language, verify
from conlang_forge.roots import load_rootmap
from conlang_forge.smallwords import CLASSES, SHORT, TINY
from conlang_forge.spec import sample_spec
from conlang_forge.vocab import load_vocab

vocab = load_vocab(ROOT / "data/vocab/v1.2.json")
rm = load_rootmap(ROOT / "data/roots/v1.2.rootmap.json")
freq = load_freq(ROOT / "data/vocab/v1.2.freq.json")

LANGS = [  # (label, seed, pins, one-line character)
    ("A", 5, {}, "prefixing, subject-verb-object, many vowels"),
    ("B", 11, {"morphology.typology": "agglutinative"}, "agglutinative, only 3 vowels and open syllables, long words"),
    ("C", 12, {"morphology.typology": "isolating"}, "isolating, heavy consonant clusters, short words, particles instead of affixes"),
]
built = []
for tag, seed, pins, note in LANGS:
    spec = sample_spec(seed, pins)
    state, _ = build_language(spec, vocab, rm, freq)
    built.append(dict(tag=tag, spec=spec, state=state, E={e["concept_id"]: e for e in state["entries"]},
                      q=verify(spec, rm, state), note=note, pins=pins))


def cell(b, w, recipe=True):
    e = b["E"].get(w)
    if e is None:
        return "-"
    s = e["form"]
    if recipe and e["kind"] in ("derived", "compound") and e.get("recipe"):
        s += f" <sub>= {e['recipe']}</sub>".replace("|", "\\|")
    return s


def table(title, words, recipe=False, note=""):
    L = [f"### {title}", ""] + ([note, ""] if note else [])
    L += ["| English | " + " | ".join(f"{b['tag']}: {b['spec'].name}" for b in built) + " |", "|---|" + "---|" * len(built)]
    for w in words:
        L.append(f"| {w} | " + " | ".join(cell(b, w, recipe) for b in built) + " |")
    return L + [""]


L = ["# Three test languages, side by side", "",
     "Conlang Forge v1.2 vocabulary (2,022 words), root map v1.2, NGSL frequency data. The three languages use different seeds and "
     "typology settings, so everything else (sounds, word shapes, grammar features) comes out different. Words are shown in the "
     "language's own spelling. The grammar book and sentence translation are not built yet, so this file shows vocabulary and word "
     "formation only.", ""]

L += ["## The languages at a glance", "",
      "| | " + " | ".join(f"**{b['tag']}: {b['spec'].name}**" for b in built) + " |", "|---|" + "---|" * len(built)]
rows = [
    ("Character", lambda b: b["note"]),
    ("Typology", lambda b: f"{b['spec'].morphology.typology} (synthesis {b['spec'].morphology.synthesis_index})"),
    ("Affixes", lambda b: b["spec"].morphology.affix_position),
    ("Word order", lambda b: f"{b['spec'].syntax.word_order}, {b['spec'].syntax.adposition}s, {b['spec'].syntax.adjective_order}"),
    ("Consonants / vowels", lambda b: f"{len(b['spec'].phonology.consonants)} / {len(b['spec'].phonology.vowels)}"),
    ("Syllable shapes", lambda b: " ".join(b["spec"].phonology.syllable_templates)),
    ("Stress", lambda b: b["spec"].phonology.stress),
    ("Cases / genders / tenses", lambda b: f"{len(b['spec'].morphology.cases)} / {len(b['spec'].morphology.genders)} / {len(b['spec'].morphology.tenses)}"),
    ("Unmarked gender term", lambda b: b["spec"].morphology.gender_base),
    ("Average word length (syllables)", lambda b: f"{sum(len(e['syllables']) for e in b['state']['entries'] if not e['retired'] and e['kind'] != 'bound') / sum(1 for e in b['state']['entries'] if not e['retired'] and e['kind'] != 'bound'):.2f}"),
    ("One-syllable family stems", lambda b: f"{b['q']['stems_by_syllables'][1]} of {b['q']['stems']}"),
]
for label, fn in rows:
    L.append(f"| {label} | " + " | ".join(fn(b) for b in built) + " |")
L.append("")

L += ["## Sounds", ""]
for b in built:
    ph, rom = b["spec"].phonology, b["spec"].orthography.romanization
    L += [f"**{b['tag']}: {b['spec'].name}**", "",
          f"- Consonants: {' '.join(rom[c] for c in ph.consonants)}",
          f"- Vowels: {' '.join(rom[v] for v in ph.vowels)}", ""]

L += ["## Sample words", "",
      "Words that are derived from another word show how, in small print (for example `= king +FEMALE`). Common words tend to be short "
      "and stand alone; the same English word can be a root in one language and a derivation in another.", ""]
L += table("Numbers", ["one", "two", "three", "four", "five", "ten", "hundred"])
L += table("People and family", ["man", "woman", "child", "mother", "father", "brother", "sister", "friend", "king", "queen", "enemy"], True)
L += table("Body", ["head", "eye", "hand", "foot", "heart", "blood", "bone", "mouth"])
L += table("Nature and world", ["sun", "moon", "star", "fire", "water", "river", "mountain", "forest", "stone", "wind", "rain", "snow"])
L += table("Animals", ["dog", "horse", "bird", "fish", "fox", "bear", "spider", "dragon"])
L += table("Fantasy", ["wizard", "magic", "sword", "castle", "dragon", "elf", "dwarf", "orc", "troll", "ghost", "treasure", "curse"], True)
L += table("Everyday verbs", ["be", "have", "go", "come", "see", "hear", "eat", "drink", "sleep", "love", "fight", "die", "give", "say"])
L += table("Qualities", ["big", "small", "old", "new", "good", "bad", "hot", "cold", "dark", "strong", "fast", "red", "white", "black"], True)

def live(b):
    return [e for e in b["state"]["entries"] if not e["retired"] and e["kind"] not in ("alias", "bound")]


def letters(e):
    return len(e["form"].replace(" ", ""))


L += ["## The short common words", "",
      "Pronouns, articles, conjunctions, negation, question words, prepositions, auxiliaries and a few adverbs are used so often that "
      "languages make them cheap to say: mostly one syllable, and they take most of the one- and two-letter words. Each word in the "
      "list has its own chance of getting a short form in a given language (about 95% for the most basic ones such as *and*, *of*, "
      "*the*, *I*; 35-60% for longer ones such as *beneath*, *between*, *although*). Derived forms (*me*, *my*, *him*, *these* ...) "
      "are built from their base word, so they stay short too.", "",
      "| | " + " | ".join(f"{b['tag']}: {b['spec'].name}" for b in built) + " |", "|---|" + "---|" * len(built)]
def share(b, f):
    sh = [e for e in live(b) if e["concept_id"] in SHORT]
    return f(b, sh)
L.append("| Short words with one syllable | " + " | ".join(share(b, lambda b, sh: f"{sum(1 for e in sh if len(e['syllables']) == 1)} of {len(sh)}") for b in built) + " |")
L.append("| Average syllables: short words / all other words | " + " | ".join(share(b, lambda b, sh: "%.2f / %.2f" % (
    sum(len(e["syllables"]) for e in sh) / len(sh),
    sum(len(e["syllables"]) for e in live(b) if e["concept_id"] not in SHORT) / sum(1 for e in live(b) if e["concept_id"] not in SHORT))) for b in built) + " |")
def tiny_share(b):
    t = [e for e in live(b) if letters(e) <= TINY]
    mine = [e for e in t if e["concept_id"] in SHORT or e["is_function"]]
    return f"{len(mine)} of {len(t)}"
L.append(f"| One- and two-letter words that are function words | " + " | ".join(tiny_share(b) for b in built) + " |")
L.append("")
for cls, ws in CLASSES.items():
    L += table(cls[0].upper() + cls[1:], [w for w in ws if w in built[0]["E"]])
L += ["### Derived from the short words", "",
      "| English | " + " | ".join(f"{b['tag']}: {b['spec'].name}" for b in built) + " |", "|---|" + "---|" * len(built)]
for w in ["me", "my", "him", "she", "these", "those", "whom", "there", "off", "out", "into"]:
    L.append(f"| {w} | " + " | ".join(cell(b, w, True) for b in built) + " |")
L.append("")
L += ["### Every one- and two-letter word in each language", "",
      "Words that are not function words are marked with an asterisk (a small chance is left open for them).", ""]
for b in built:
    t = sorted(live(b), key=lambda e: (letters(e), e["form"]))
    t = [e for e in t if letters(e) <= TINY]
    L.append(f"**{b['tag']}: {b['spec'].name}** ({len(t)}): " + ", ".join(
        f"{e['form']} ({e['lemma']})" + ("" if (e["concept_id"] in SHORT or e["is_function"]) else "*") for e in t))
    L.append("")

L += ["## How words are built", "",
      "Each language has one regular affix (or particle, in the isolating language) per relation. The same English derivation uses the "
      "same affix everywhere in that language.", ""]
L += table("Derived forms", ["teacher", "queen", "poor", "quickly", "careful", "dangerous", "friendly", "darkness", "freedom", "height"], True)

for b in built:
    A = b["state"]["table"]["affixes"]
    spec = b["spec"]
    items = [f"{r.lower()} {render_flat(spec, A[r]['phonemes'])[0]} ({A[r]['position']})" for r in
             ("PLURAL", "ADJ", "ADV", "AGENT", "NEG", "OPPOSITE", "AGAIN", "FEMALE", "DIMIN", "ABSTRACT") if r in A]
    L += [f"**{b['tag']}: {spec.name}** — " + "; ".join(items), ""]

L += ["## Related words share sounds", "",
      "Words in one conceptual family share a stem; unrelated words do not. Compare a family with its neighbours:", ""]
L += table("Water family (water, river, lake, sea, ocean)", ["water", "river", "lake", "sea", "ocean", "fire", "stone"])
L += table("Hand family and its sibling families", ["hand", "finger", "thumb", "palm", "wrist", "foot", "toe", "arm", "leg"])
L += table("Orc, brute and monster families (siblings)", ["monster", "demon", "dragon", "orc", "goblin", "hobgoblin", "werewolf", "giant", "troll", "ogre"])

L += ["## Word order illustration", "",
      "Not real grammar (cases, agreement and tense are not generated yet): just the content words of *the old wizard sees the dragon* in "
      "each language's basic word order, using plain root words.", ""]
for b in built:
    spec, E = b["spec"], b["E"]
    f = lambda w: E[w]["form"]
    order = spec.syntax.word_order
    subj = f"{f('old')} {f('wizard')}" if spec.syntax.adjective_order.startswith("adjective") else f"{f('wizard')} {f('old')}"
    obj, verb = f("dragon"), f("see")
    seq = {"SOV": [subj, obj, verb], "SVO": [subj, verb, obj], "VSO": [verb, subj, obj], "VOS": [verb, obj, subj],
           "OVS": [obj, verb, subj], "OSV": [obj, subj, verb]}[order]
    L.append(f"- **{b['tag']}: {spec.name}** ({order}, {spec.syntax.adjective_order}): {' '.join(seq)}")
L.append("")

L += ["## Quality checks", "", "| Check | " + " | ".join(b["tag"] for b in built) + " |", "|---|" + "---|" * len(built)]
for label, key in [("Entries", "entries"), ("Duplicate forms", "duplicate_forms"), ("Near-identical root pairs", "near_root_pairs"),
                   ("Family pairs below minimum distance", "family_pairs_below_min"),
                   ("Words readable as another word + affix", "false_parses")]:
    L.append(f"| {label} | " + " | ".join(str(b["q"][key]) for b in built) + " |")
Path(sys.argv[1] if len(sys.argv) > 1 else "language_examples.md").write_text("\n".join(L) + "\n", encoding="utf-8")
