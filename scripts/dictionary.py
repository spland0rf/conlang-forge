"""Write the two-way dictionary: python scripts/dictionary.py SEED OUT.md [key=value pins] (CSV is written beside it)"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from conlang_forge.dictionary import build_rows, dictionary_csv_full, dictionary_markdown_full
from conlang_forge.frequency import load_freq
from conlang_forge.rootgen import build_language
from conlang_forge.roots import load_rootmap
from conlang_forge.spec import sample_spec
from conlang_forge.vocab import load_vocab

if __name__ == "__main__":
    seed, out = int(sys.argv[1]), Path(sys.argv[2])
    pins = dict(a.split("=", 1) for a in sys.argv[3:])
    vocab = load_vocab(ROOT / "data/vocab/v1.2.json")
    rm = load_rootmap(ROOT / "data/roots/v1.2.rootmap.json")
    freq = load_freq(ROOT / "data/vocab/v1.2.freq.json")
    spec = sample_spec(seed, pins)
    state, _ = build_language(spec, vocab, rm, freq)
    rows = build_rows(spec, state, vocab)
    out.write_text(dictionary_markdown_full(spec, state, vocab, vocab["version"], rows), encoding="utf-8")
    out.with_suffix(".csv").write_text(dictionary_csv_full(rows), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} entries)")
