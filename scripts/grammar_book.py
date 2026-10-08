"""Write the beginner's course for a generated language: python scripts/grammar_book.py SEED OUT.md [key=value pins]"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from conlang_forge.frequency import load_freq
from conlang_forge.grammar_book import build_book
from conlang_forge.rootgen import build_language
from conlang_forge.roots import load_rootmap
from conlang_forge.spec import sample_spec
from conlang_forge.vocab import load_vocab

if __name__ == "__main__":
    seed, out = int(sys.argv[1]), sys.argv[2]
    pins = dict(a.split("=", 1) for a in sys.argv[3:])
    vocab = load_vocab(ROOT / "data/vocab/v1.2.json")
    rm = load_rootmap(ROOT / "data/roots/v1.2.rootmap.json")
    freq = load_freq(ROOT / "data/vocab/v1.2.freq.json")
    spec = sample_spec(seed, pins)
    state, _ = build_language(spec, vocab, rm, freq)
    Path(out).write_text(build_book(spec, state, vocab), encoding="utf-8")
    print(f"wrote {out}")
