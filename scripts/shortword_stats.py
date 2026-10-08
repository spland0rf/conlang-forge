"""How the short common words come out across many seeds: python scripts/shortword_stats.py [n_seeds]"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from conlang_forge.frequency import load_freq
from conlang_forge.rootgen import build_language
from conlang_forge.roots import load_rootmap
from conlang_forge.smallwords import SHORT, TINY
from conlang_forge.spec import sample_spec
from conlang_forge.vocab import load_vocab

vocab = load_vocab(ROOT / "data/vocab/v1.2.json")
rm = load_rootmap(ROOT / "data/roots/v1.2.rootmap.json")
freq = load_freq(ROOT / "data/vocab/v1.2.freq.json")


def letters(e):
    return len(e["form"].replace(" ", ""))


def stats(seed, pins=None):
    spec = sample_spec(seed, pins or {})
    state, _ = build_language(spec, vocab, rm, freq)
    E = [e for e in state["entries"] if e["kind"] not in ("alias", "bound") and not e["retired"]]
    short = [e for e in E if e["concept_id"] in SHORT]
    mono = sum(1 for e in short if len(e["syllables"]) == 1)
    tiny = [e for e in E if letters(e) <= TINY]
    tiny_short = [e for e in tiny if e["concept_id"] in SHORT or e["is_function"]]
    return dict(seed=seed, typ=spec.morphology.typology, n_short=len(short), mono=mono / len(short),
                tiny=len(tiny), tiny_share=len(tiny_short) / max(len(tiny), 1),
                content_tiny=[e["form"] for e in tiny if e not in tiny_short],
                mean_syl_short=sum(len(e["syllables"]) for e in short) / len(short),
                mean_syl_content=sum(len(e["syllables"]) for e in E if not e["is_function"]) / len(E))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    rows = [stats(s) for s in range(1, n + 1)] + [stats(11, {"morphology.typology": "agglutinative"}),
                                                 stats(12, {"morphology.typology": "isolating"})]
    print("seed typology   short  1-syl  tiny  tiny-share  syl(short) syl(other)  content-tiny")
    for r in rows:
        print(f"{r['seed']:>4} {r['typ']:<13}{r['n_short']:>5} {r['mono']:>6.0%} {r['tiny']:>5} {r['tiny_share']:>10.0%} "
              f"{r['mean_syl_short']:>10.2f} {r['mean_syl_content']:>10.2f}  {r['content_tiny'][:6]}")
