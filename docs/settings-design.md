# Settings editor, sample-text shaping and spelling (step 6)

## Spelling: plain letters, special letters as a view
- A language is stored as sounds (phonemes). Spelling is a view over them. The default is **plain English letters only**: consonants
  `sh ch th kh zh ng j y q`, vowels `a e i o u`, and the unusual vowels as letter pairs (`ae`, `oe`/`eu`/`oeh`, `ue`/`ui`/`ueh`, `uh`/`ey`/`uuh`).
  For each language the first spelling that cannot be misread as two other letters side by side is used (`inventory.romanization_map`).
- "Special letters" (š ž č ǧ ŋ þ ʼ ä ö ü ë) are an optional display: `plain.with_script(lang, "special")` re-renders the forms from the
  phonemes. API: `?script=special` on the language, dictionary, downloads; `script` in the translate body. The UI has a Plain/Special switch
  (remembered in the browser). Nothing stored changes.
- Typed input is folded to plain (`plain.fold`, language-aware via `own_fold`), so conlang-to-English accepts special letters too.
- Languages saved with accents are respelled on load (`plain.respell`): only `form` changes.
- "Say it like" hints (`inventory.SAY_LIKE`) are shown in the grammar book and in the settings editor.

## Settings
A language = seed + **pins** (settings the user fixed) + **tuning** (odds, rates, generator tendencies for what stays random).
- `spec.Sampler` records every random choice with its odds; `tuning.odds[key][option]` overrides weights, `tuning.rates[key]` the chance of
  yes/no settings, `tuning.gen[name]` numeric tendencies (word length, how often common words get their own root, and so on).
  With no tuning the output is identical to before (checked on 120 samples).
- New pin keys: `phonology.onset_clusters`, `coda_consonants`, `coda_clusters`, `max_cluster`.
- `settings_schema.py` lists every setting (label, help, kind, options, current value, pinned, odds), normalises edits (shares follow the
  inventory, core cases follow the alignment, clusters follow the consonants) and explains diffs in plain words. Impossible settings give a
  friendly message (for example too few distinct words).
- API: `GET /api/conlangs/{id}/settings`; `POST .../settings/preview` (cheap, no vocabulary build: shows what changes, including knock-on
  changes of settings left random); `POST .../settings/apply` with `mode` `replace` or `copy`. Body: `{set, unpin, tuning}`.
- Words are never edited by hand: applying rebuilds the vocabulary by the rules. Sample strings survive a rebuild.
- UI: Settings tab, grouped; every setting has a Random/Fixed switch and (for random ones) an odds editor; sticky save bar; review popup.
  Editing consonants, vowels and their shares is optional: a default inventory and distribution are generated, or derived from a sample.

## Sample-text shaping (`exemplar.py`, `backend/exemplars.py`)
- Phonology reader (code, free): spelling to sounds, syllables (maximal onsets), counts of consonants/vowels, syllable shapes, clusters, hiatus,
  word length. Short samples only add sounds and nudge shapes; large ones also remove unused sounds.
- Grammar reader (model, purpose `exemplar.analyze`): proposes word order, affix position, and so on from the text; output is validated
  against the schema and dropped if it names an unknown setting or value. Without a model only sounds are analysed.
- Output is a list of **proposals** `{key, current, proposed, kind: conflict|drift, confidence, evidence, source}`. `conflict` = disagrees with a
  setting the user fixed. The UI popup lists them with checkboxes (all ticked), "Use selected settings" stages them in the settings draft, the user
  reviews and applies. `POST .../exemplars/analyze`, `PUT .../exemplars`.

## New language from a sample
`POST /api/conlangs/from-sample {texts, name?, seed?, pins?, use_model?}` (UI: "Or start from a sample" in the Forge panel).
1. Settings the user fixed (`pins`) always win. 2. The sample is read in "fresh" mode: its sounds replace the random inventory (topped up to 8
consonants / 3 vowels from the random one when the sample is small). 3. Inferred settings become pins; everything else is drawn from the seed as usual,
so the same seed without a sample gives the same random choices for whatever the sample did not decide. 4. If the sample's sounds cannot form a full
vocabulary, it falls back to grammar-only, then to pure chance, and says so. The response carries `shaped: {applied, kept, notes}`; `kept` lists
sample suggestions that were overridden by the user's own settings. The plan limit is checked before the paid model call.

## Presets (genders, tenses, aspects, moods, number)
Each is a choice among several sensible sets (for example genders: none, masculine/feminine, masculine/feminine/neuter, animate/inanimate, 4 to 8 classes;
number: none, singular/plural, with dual, with paucal), each with editable odds. They are not free-form because the grammar engine only supports
these combinations.

## Counts and complex consonants
- `phonology.consonant_count` and `phonology.vowel_count` set how many ordinary consonants / vowels there are (the generator chooses which);
  `phonology.consonants` / `phonology.vowels` set the exact lists. A list overrides its count and choosing a count frees the list and its shares.
- **Minimums are computed, not fixed.** `settings_schema.capacity_of` counts the distinct words of up to three syllables the syllable shapes allow;
  the language needs at least `VOCAB_NEED` (8,000, about four times the vocabulary) and at least 3 vowels (tested: with 2 the generator could not find
  enough distinct endings in about half the trials). `min_consonants(vowels, templates, units)` and `min_vowels(consonants, templates)` give the least
  for the current shapes; `describe()["minimums"]` feeds the sliders, and a build that falls short names the exact numbers. The build itself is the
  final check (it can still fail rarely for a particular seed; the error says so).
- **Complex consonants** (`inventory.UNIT_DATA`: ts dz tl pf kx rzh kp gb mb nd tth tb tbl zl; units may have 2 or 3 parts). Each is one phoneme, one consonant slot in a syllable shape, one
  count toward consonant runs, its own letter in the alphabet and its own share; it never enters a consonant pair. Settings: `phonology.complex_count`
  (none, one, a few ... eight, with odds; default mostly none) and `phonology.complex_consonants` (exact list). Spellings avoid clashes where possible
  (`ts`/`tz`, `tl`/`tlh`, `rzh`/`rj`). `Phonology.complex_consonants` lists which members of `consonants` are units. Languages saved before this existed
  count as having none (`pins_of`).
- Sample text: `ts`/`tz`, `kp`, `gb`, `rzh`, `pf`, `kx` are read as one consonant; `tl`, `nd`, `mb`, `zl`, `tb`, `tbl` at the start OR the end of a word (longest match first, so `tbl` beats `tb`; inside a word they may be an
  ordinary pair). The sample proposes the units it uses.

## Known limits
- Interlinear glosses in conlang-to-English show plain letters even when Special is selected.
- Digraph ambiguity (`sh` = s+h) is resolved greedily, as in the dictionary alphabet.
- Preset lists are used for tenses, aspects, moods, number, genders (only combinations the grammar engine supports).
- The grammar reader is tested with a stub model only.
