"""Command-line interface for the core engine."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .frequency import build_freq, load_freq, save_freq
from .grammar_book import build_book
from .dictionary import build_rows, dictionary_csv_full, dictionary_markdown_full
from .export import dictionary_csv, dictionary_markdown, dictionary_markdown_v2, summarize_spec
from .lexicon import build_lexicon, extend_lexicon
from .spec import LanguageSpec, sample_spec, validate_spec
from .roots import build_rootmap, load_rootmap, save_rootmap
from .rootgen import build_language, extend, verify
from .vocab import build_vocab, diff_vocab, load_vocab, save_vocab


def _write_language(out: Path, lang: dict, spec: LanguageSpec) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "language.json").write_text(json.dumps(lang, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "dictionary.md").write_text(
        dictionary_markdown(spec, lang["lexicon"], lang["vocab_version"]), encoding="utf-8")
    (out / "dictionary.csv").write_text(dictionary_csv(lang["lexicon"]), encoding="utf-8")


def cmd_build_vocab(a):
    v = build_vocab(a.source, a.manifest)
    save_vocab(v, a.out)
    print(f"vocab v{v['version']}: {len(v['entries'])} concepts -> {a.out}")
    for k, items in v["report"].items():
        if items and k != "rows_read":
            print(f"  {k}: {items}")


def cmd_generate(a):
    vocab = load_vocab(a.vocab)
    pins = json.loads(Path(a.pins).read_text()) if a.pins else None
    spec = sample_spec(a.seed, pins)
    problems = validate_spec(spec)
    if problems:
        sys.exit(f"invalid spec: {problems}")
    if a.rootmap:
        return _generate_v2(a, spec, vocab)
    lex = build_lexicon(spec, vocab)
    lang = {"format": "conlang-forge-language/1", "vocab_version": vocab["version"],
            "spec": spec.to_dict(), "lexicon": lex,
            "history": [{"vocab_version": vocab["version"], "added": len(lex), "retired": 0}]}
    out = Path(a.out or f"out/seed{a.seed}")
    _write_language(out, lang, spec)
    print(summarize_spec(spec))
    print(f"  wrote {out}/ ({len(lex)} words)")


def _write_v2(out: Path, lang: dict, spec, vocab=None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    state = {"table": lang["table"], "stems": lang["stems"], "entries": lang["lexicon"], "plan": lang.get("plan")}
    (out / "language.json").write_text(json.dumps(lang, ensure_ascii=False, indent=1), encoding="utf-8")
    if vocab is not None:   # the full two-way dictionary (parts of speech, genders, plurals, tense forms)
        rows = build_rows(spec, state, vocab)
        (out / "dictionary.md").write_text(
            dictionary_markdown_full(spec, state, vocab, lang["vocab_version"], rows), encoding="utf-8")
        (out / "dictionary.csv").write_text(dictionary_csv_full(rows), encoding="utf-8")
    else:
        (out / "dictionary.md").write_text(dictionary_markdown_v2(spec, state, lang["vocab_version"]), encoding="utf-8")
        (out / "dictionary.csv").write_text(
            dictionary_csv([e for e in lang["lexicon"] if e["kind"] != "bound"]), encoding="utf-8")
    if vocab is not None:   # the beginner's course, written from the language itself
        (out / "grammar_book.md").write_text(build_book(spec, state, vocab), encoding="utf-8")


def _generate_v2(a, spec, vocab):
    rootmap = load_rootmap(a.rootmap)
    state, rep = build_language(spec, vocab, rootmap, load_freq(a.freq) if a.freq else None)
    q = verify(spec, rootmap, state)
    lang = {"format": "conlang-forge-language/2", "vocab_version": vocab["version"], "spec": spec.to_dict(),
            "table": state["table"], "stems": state["stems"], "stem_budget": state["stem_budget"],
            "lexicon": state["entries"], "plan": state["plan"], "quality": q,
            "history": [{"vocab_version": vocab["version"], "added": len(rep["added"]), "retired": 0}]}
    out = Path(a.out or f"out/seed{a.seed}")
    _write_v2(out, lang, spec, vocab)
    print(summarize_spec(spec))
    print(f"  stems: {q['stems_by_syllables']} (one-syllable capacity {state['stem_budget']['one_syllable_capacity']})")
    print(f"  quality: duplicates {q['duplicate_forms']}, near-identical roots {q['near_root_pairs']}, "
          f"family pairs below min distance {q['family_pairs_below_min']}, false parses {q['false_parses']}")
    print(f"  wrote {out}/ ({q['entries']} entries)")


def cmd_build_rootmap(a):
    rm = build_rootmap(a.roots, load_vocab(a.vocab))
    save_rootmap(rm, a.out)
    print(f"root map for vocab v{rm['vocab_version']}: {json.dumps(rm['stats'])}")


def cmd_upgrade(a):
    lang = json.loads(Path(a.language).read_text(encoding="utf-8"))
    vocab = load_vocab(a.vocab)
    spec = LanguageSpec.from_dict(lang["spec"])
    if lang.get("format", "").endswith("/2"):
        if not a.rootmap:
            sys.exit("root-based languages need --rootmap for the new vocab version")
        state = {"table": lang["table"], "stems": lang["stems"], "entries": lang["lexicon"],
                 "stem_budget": lang.get("stem_budget"), "plan": lang.get("plan")}
        new_state, rep = extend(spec, vocab, load_rootmap(a.rootmap), state, load_freq(a.freq) if a.freq else None)
        print(f"{spec.name}: v{lang['vocab_version']} -> v{vocab['version']}: +{len(rep['added'])} added, "
              f"{len(rep['retired'])} retired, {len(rep['unretired'])} restored")
        if a.dry_run:
            print("  new:", ", ".join(rep["added"][:40]))
            return
        lang.update(lexicon=new_state["entries"], stems=new_state["stems"], vocab_version=vocab["version"],
                    stem_budget=new_state["stem_budget"], plan=new_state["plan"])
        lang["history"].append({"vocab_version": vocab["version"], "added": len(rep["added"]),
                                "retired": len(rep["retired"])})
        _write_v2(Path(a.language).parent, lang, spec, vocab)
        return
    new_lex, rep = extend_lexicon(spec, lang["lexicon"], vocab)
    print(f"{spec.name}: v{lang['vocab_version']} -> v{vocab['version']}: "
          f"+{len(rep['added'])} added, {len(rep['retired'])} retired, {len(rep['unretired'])} restored")
    if a.dry_run:
        print("  new:", ", ".join(rep["added"][:40]), "..." if len(rep["added"]) > 40 else "")
        return
    lang["lexicon"], lang["vocab_version"] = new_lex, vocab["version"]
    lang["history"].append({"vocab_version": vocab["version"], "added": len(rep["added"]),
                            "retired": len(rep["retired"])})
    _write_language(Path(a.language).parent, lang, spec)


def cmd_build_freq(a):
    freq = build_freq(a.ngsl, load_vocab(a.vocab), a.extra)
    save_freq(freq, a.out)
    r = freq["report"]
    print(f"ranks for {len(freq['ranks'])} concepts -> {a.out}")
    print(f"  vocabulary words without a rank: {r['vocab_words_without_rank']}; list words not in the vocabulary: {r['list_words_not_in_vocab']}")
    print(f"  taken from the extra lists: {r['taken_from_extra_lists']}")


def cmd_diff(a):
    d = diff_vocab(load_vocab(a.old), load_vocab(a.new))
    print(f"added {len(d['added'])}: {d['added']}\nremoved {len(d['removed'])}: {d['removed']}\n"
          f"unchanged {d['unchanged']}")


def cmd_create_admin(a):
    """Create the first administrator. The password comes from CONLANG_FORGE_ADMIN_PASSWORD or a prompt."""
    import getpass
    import os

    from .backend.app import Backend, Config
    pw = os.environ.get("CONLANG_FORGE_ADMIN_PASSWORD") or getpass.getpass("Password: ")
    be = Backend(Config(database=a.db, signing_secret=os.environ.get("CONLANG_FORGE_SECRET", "x" * 40)))
    u = be.accounts.bootstrap_admin(a.email, pw, a.name)
    print(f"created administrator {u['email']} ({u['id']})")


def cmd_serve(a):
    from .backend.serve import run
    if a.demo and str(a.db).startswith("postgres"):
        raise SystemExit("--demo writes invented users and usage, so it will not run against a PostgreSQL database.")
    run(a.db, a.data, a.host, a.port, a.demo)


def main(argv=None):
    p = argparse.ArgumentParser(prog="conlang-forge")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-vocab", help="clean a word-list CSV into a versioned vocab JSON")
    b.add_argument("source"); b.add_argument("manifest"); b.add_argument("out"); b.set_defaults(fn=cmd_build_vocab)
    g = sub.add_parser("generate", help="generate a language from a seed (optionally with pins)")
    g.add_argument("--vocab", required=True); g.add_argument("--seed", type=int, required=True)
    g.add_argument("--pins", help="JSON file of dotted-key pins, e.g. {\"syntax.word_order\": \"SOV\"}")
    g.add_argument("--rootmap", help="root map JSON: build the vocabulary from shared roots")
    g.add_argument("--freq", help="frequency JSON from build-freq (common words get shorter, simpler forms)")
    g.add_argument("--out"); g.set_defaults(fn=cmd_generate)
    rb = sub.add_parser("build-rootmap", help="validate a roots .txt file against a vocab and save JSON")
    rb.add_argument("roots"); rb.add_argument("vocab"); rb.add_argument("out"); rb.set_defaults(fn=cmd_build_rootmap)
    u = sub.add_parser("upgrade", help="upgrade an existing language to a newer vocab version")
    u.add_argument("language"); u.add_argument("--vocab", required=True)
    u.add_argument("--rootmap"); u.add_argument("--freq"); u.add_argument("--dry-run", action="store_true"); u.set_defaults(fn=cmd_upgrade)
    bf = sub.add_parser("build-freq", help="turn the NGSL stats CSV (plus optional extra lists) into a frequency JSON")
    bf.add_argument("vocab"); bf.add_argument("out"); bf.add_argument("ngsl", help="NGSL stats CSV (Lemma,SFI Rank,...)")
    bf.add_argument("--extra", nargs="*", default=[], help="extra Rank,Word lists for words the NGSL lacks")
    bf.set_defaults(fn=cmd_build_freq)
    d = sub.add_parser("diff-vocab"); d.add_argument("old"); d.add_argument("new"); d.set_defaults(fn=cmd_diff)
    ca = sub.add_parser("create-admin", help="create the first administrator account in the backend database")
    ca.add_argument("--db", default=os.environ.get("DATABASE_URL", "conlang_forge.db")); ca.add_argument("--email", required=True)
    ca.add_argument("--name", default="Admin"); ca.set_defaults(fn=cmd_create_admin)
    sv = sub.add_parser("serve", help="run the website and API locally")
    sv.add_argument("--db", default=os.environ.get("DATABASE_URL", "conlang_forge.db"),
                    help="a SQLite file, or a postgresql:// URL (default: $DATABASE_URL, else conlang_forge.db)")
    sv.add_argument("--data", help="data directory (default: the repo's data/)")
    sv.add_argument("--host", default="127.0.0.1"); sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--demo", action="store_true", help="demo database with sample users and invented usage numbers")
    sv.set_defaults(fn=cmd_serve)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
