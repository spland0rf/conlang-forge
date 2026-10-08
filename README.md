# conlang-forge (steps 1-2a: core engine + root-based vocabulary)

Deterministic, seeded conlang generator. No LLM, no network. Same spec + seed = same language.

## Quick start
    python -m conlang_forge build-vocab data/source/words_v1.0.csv data/vocab/v1.0.manifest.json data/vocab/v1.0.json
    python -m conlang_forge generate --vocab data/vocab/v1.0.json --seed 7 --out out/seed7
    python -m conlang_forge generate --vocab data/vocab/v1.0.json --seed 7 --pins samples/pins_example.json
    python -m conlang_forge upgrade out/seed7/language.json --vocab data/vocab/v1.2.json --dry-run
    python -m conlang_forge diff-vocab data/vocab/v1.0.json data/vocab/v1.2.json
    python tests/run_without_pytest.py        # or: pytest

## Root-based vocabulary (current: vocab v1.2; v1.0 files are kept for upgrade tests)
    python -m conlang_forge build-freq data/vocab/v1.2.json data/vocab/v1.2.freq.json data/source/ngsl_1.2_stats.csv --extra data/source/top_100_english_nouns.csv data/source/top_100_english_verbs.csv data/source/top_100_ngsl_adjectives.csv
    python -m conlang_forge build-rootmap data/roots/v1.2.roots.txt data/vocab/v1.2.json data/roots/v1.2.rootmap.json
    python -m conlang_forge generate --vocab data/vocab/v1.2.json --rootmap data/roots/v1.2.rootmap.json --freq data/vocab/v1.2.freq.json --seed 7 --out out/root7
    python -m conlang_forge upgrade out/root7/language.json --vocab data/vocab/v1.2.json --rootmap data/roots/v1.2.rootmap.json --freq data/vocab/v1.2.freq.json
    python scripts/family_demo.py family_demo.md      # same families in three languages
    python scripts/language_examples.py language_examples.md  # sample words from three contrasting test languages
    python scripts/review_sheet.py data/roots/v1.0.rootmap.json review.md   # reviewable family table

How it works (modules `roots.py`, `morph.py`, `rootgen.py`, `phonetics.py`):
- **Root map** (`data/roots/*.roots.txt`): every vocab word is a free root, a derivation (`word = base +REL`),
  a compound (`word = a | b`), or an alias. Conceptual families (at most 5 roots, 6 only with very strong affinity) share a stem.
  `siblings` lines link families that were one group too big for the cap.
- **Stems:** one stem per family; the family head is the bare stem, other members are the stem plus one change.
  One-syllable stems are budgeted from the language's own syllable capacity: syllable-rich languages give
  most families a one-syllable stem, syllable-poor ones give them to the most common families and use
  multi-syllable stems for the rest. Commonness is the smooth score f (see *Frequency* below), so stem
  length shrinks gradually with frequency; there is no cutoff.
- **Two sound classes:** grammatical sounds (relation affixes, joining) vs lexical sounds (changes inside
  a root), so a within-word change is never mistaken for a grammatical one.
- **Distinguishability:** `phonetics.MIN_DIST`; candidates too close to an existing root are rejected.
- **Ambiguity checks:** unique forms; no word that can also be read as another word + affix
  (`verify()` reports the remainder); relaxation is staged and flagged (`relaxed`).
- **Frequency (no cutoff):** `frequency.py` turns the NGSL v1.2 rank list (2,809 lemmas; the top-100 per-POS lists only fill gaps) into
  f = 1/(1+(rank/500)^1.2); words with no rank get a low default (function words 0.6). `plan.py` then applies the natural-language tendency,
  *per language and probabilistically*: the more frequent a derived word (or compound), the more likely it gets
  a root of its own (p = f^1.5 x a per-relation weight, `relations.INDEPENDENCE`; opposites/size words most,
  grammatical relations least); a frequent non-head family member may leave its family; and a family's head
  (the bare stem) is drawn with weight f^2, so usually, not always, the commonest member. Rare words stay
  derived or compound. The same f also scales word and stem length. Decisions are keyed on (seed, concept)
  and stored in the language (`plan`), so upgrades never revisit them.
- **Gender pairs:** the roots file writes each pair once as `queen = king +FEMALE`. Each language has a
  `morphology.gender_base` setting (male / female); `roots.adapt_rootmap()` mirrors the pairs for female-base
  languages (`king = queen +MALE`, `grandmother = @grand | mother`). Pin it with
  `{"morphology.gender_base": "female"}`.
- **Fantasy beings:** `humanoid` (elf, dwarf) and `monster` (monster, orc, goblin, demon, dragon) are separate
  families. To grow either, add a family and link it with a `siblings` line.
- **Upgrades:** `extend()` adds missing concepts only; existing words never change.

## Concepts
- **Vocab version**: cleaned word list with stable `concept_id`s (see `data/vocab/*.manifest.json` for fixes,
  restored words, quarantined entries, and aliases/renames).
- **LanguageSpec**: JSON description of phonology, morphology, syntax, orthography. `pins` fix any field
  (this is the hook for Settings and Exemplar modes); `provenance` records random vs pinned.
- **Word identity**: each word = hash(seed, concept_id, attempt). Upgrades only add words; nothing existing changes.
- **Retired words** stay in the dictionary, flagged, when a newer vocab drops them.

## Layout
    conlang_forge/vocab.py     load/clean/diff versioned vocab
    conlang_forge/inventory.py phoneme pool + romanization
    conlang_forge/spec.py      spec dataclasses, sampler, pins, validation
    conlang_forge/wordgen.py   deterministic word generation
    conlang_forge/lexicon.py   build + upgrade lexicon
    conlang_forge/export.py    dictionary (Markdown/CSV), spec summary
    conlang_forge/roots.py     root map parser/validator
    conlang_forge/relations.py derivational relations (ADJ, AGENT, ...)
    conlang_forge/phonetics.py phonetic distance + near-neighbour index
    conlang_forge/morph.py     affix/formative table, joining, rendering
    conlang_forge/rootgen.py   root-based lexicon generation, upgrade, verification
    conlang_forge/cli.py       CLI

## Short common words

`conlang_forge/smallwords.py` lists the pronouns, articles, conjunctions, negation, question words, prepositions, auxiliaries and adverbs that are made short (usually one syllable) and that own most one- and two-letter words. `python scripts/shortword_stats.py [n_seeds]` prints how this comes out over many seeds. See `docs/short_words_section.md`.

## Grammar book (beginner's course)

`conlang_forge/grammar.py` realises sentences (word order, cases, gender/number agreement, tense/aspect/mood, verb agreement, negation, questions, numerals) from the language's own lexicon and inflection table (`table["infl"]`, drawn in `morph.build_table` from the spec). `conlang_forge/grammar_book.py` writes an 11-lesson "Language 101" course from it, with word-by-word glossed examples, practice exercises with an answer key, an all-endings cheat sheet and a mini-dictionary. Lessons for features the language lacks (cases, genders, tenses ...) are replaced by a note. `conlang-forge generate` now also writes `grammar_book.md`; `python scripts/grammar_book.py SEED out.md [key=value pins]` writes one directly. The word lists for the lessons are in `conlang_forge/curriculum.py`.

## The dictionary

`dictionary.md` (and `dictionary.csv`) are written with every language: a complete English → language half and a
language → English half (about 2,000 entries each), generated by `conlang_forge/dictionary.py`. Entries carry part of
speech (`pos.py`, a curated table plus derivation rules), noun gender, plural/dual forms, tense forms of verbs, gender
agreement of adjectives, how the word was built, and root-family relatives. The forms come from the same `Grammar`
engine as the grammar book. The language → English half follows the language's own alphabet (digraphs
are letters). `python scripts/dictionary.py SEED OUT.md [pins]` writes one directly.

## Backend: accounts, permissions, quotas, the metered LLM wrapper

`conlang_forge/backend/` holds everything the future API will call. It has no web-framework code, so the website
and the phone apps share it. See `claude/backend-design.md` in the project for the decisions.

* `accounts.py` registration, login (lockout), rotating refresh tokens with reuse detection, admin user management
* `permissions.py` roles (user, admin) as sets of `resource.action:own|any` permissions; one `require()` check
* `limits.py` plans plus per-user overrides; `quota.py` atomic reserve / settle / release of tokens, per-minute rate limit, global cap
* `llm/` the only code allowed to call a model: `MeteredLLM.complete(actor, purpose, ...)`; providers: Anthropic (HTTPS, no SDK) and a fake one
* `usage.py` the admin graph queries and each user's own meter; `conlangs.py` ownership and conlang-count limits
* `app.py` `Backend(Config(...))` wires it all together. `python -m conlang_forge create-admin --email you@example.com` makes the first admin.

Tests: `python tests/run_without_pytest.py test_backend test_api test_translate` (26 + 8 + 13 tests).

## Run the website locally

```
python -m conlang_forge serve --demo      # sample users and fake usage, in a throwaway database
python -m conlang_forge serve             # real: data kept in ./data (database + secret key)
```

Then open http://127.0.0.1:8000 (use `--port` to change it). On the first real run an admin account is created: set
`CONLANG_FORGE_ADMIN_EMAIL` and `CONLANG_FORGE_ADMIN_PASSWORD` beforehand, or a random password is printed once.
`--demo` prints its own sign-in details (admin and four sample users); never use `--demo` for real data.

Environment variables: `ANTHROPIC_API_KEY` (model calls; none are made by the site yet), `GOOGLE_CLIENT_ID`
(turns on "Sign in with Google"), `CONLANG_FORGE_SECRET` (token-signing key; otherwise a file beside the database).

### Sign in with Google
1. In Google Cloud Console create a project, then APIs & Services > OAuth consent screen (External; add yourself as a test user).
2. Credentials > Create credentials > OAuth client ID > Web application.
3. Under Authorized JavaScript origins add `http://localhost:8000` (and later your real domain). No redirect URI is needed.
4. Copy the client ID and start the server with `GOOGLE_CLIENT_ID=...apps.googleusercontent.com python -m conlang_forge serve`.

The browser gets a signed Google ID token; the server checks its signature, issuer, audience, expiry and verified email.
A known Google account signs in; otherwise a user with the same verified email is linked; otherwise a new account is
created. Facebook and Apple are not built (Apple reuses the same verifier; Facebook needs a Graph API check).

## Translation (English <-> your language)

On a language's page, the **Translate** tab takes ordinary English, simplifies it to the language's vocabulary with a model, and
translates it with the grammar engine (word order, endings, agreement). It shows the simplified English so you can edit it and
translate again for free, and a word-by-word gloss. The other direction reads text in the language back into English (word
analysis is code; an optional model pass smooths it).

* With `ANTHROPIC_API_KEY` set the model does the simplifying and smoothing, metered per user like everything else.
* With `serve --demo` a stand-in passes English through unchanged, so you can try the flow without a key (simple sentences work best).
* Without a key, tick "My text is already simple English" to translate with no model at all.
* Design: `claude/translation-design.md`. Code: `conlang_forge/translate/`.


## Settings, sample text and spelling (step 6)
See `docs/settings-design.md`. In short: every language setting is editable from the Settings tab
(fix or leave random, odds for random choices, generator tendencies). A sample text can propose settings, which you approve in one popup.
Languages are written with plain English letters; a Plain/Special switch only changes how words are drawn. Tests: `tests/test_settings.py`.
