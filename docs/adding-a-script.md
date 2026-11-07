# Adding a script to the stroke generators

The Devanagari-like generator takes its numbers, skeleton mix and file locations from one config file per script:
`scripts/script_analysis/script_config/<script>.json`. Choose the script with `CONLANG_SCRIPT=<script>` (default `devanagari`).
`script_config.validate("<script>")` checks that a new file has every section and every rule the Devanagari reference defines
(`tests/test_script_config.py` runs it).

The stroke vocabulary is shared by all scripts and stays in code: roles body / second / struct / accent, junctions red / touch / cross,
the 100x100 box with y down. Drawings for a new script use the same colours and markup.

## Profiles: which script supplies which ingredient

A **profile** (`script_config.Profile`) names the script behind each ingredient of a letter: `frame`, `rules`, `skeleton`, `body` (units, keepers,
patterns) and `modifier` (reserved: no consumer yet). Today every ingredient comes from one script, `Profile.of("devanagari")`. The generators read the
**active** profile at call time, never at import, so mixing later means a profile whose sources differ and nothing else:

```python
import script_config as SC
with SC.use(SC.Profile({"rules": "devanagari", "skeleton": "devanagari", "body": "bengali"})):
    ...   # Devanagari skeletons and rules, Bengali body forms
```

- `CONLANG_SCRIPT=<script>` still picks the default profile.
- Novelty checks use `profile.scripts()`: a new letter must differ from the real letters of every script in the profile.
- Every script's drawings map into one **common frame** (bar y 20, baseline y 88, the Devanagari frame) with `profile.to_common()` / `from_common()`.
  The mapping comes from the script's own `frame` (and optional `x_scale`, `x_offset`), so a script with a different bar or baseline height needs no code.
- Components carry their source: `body_gen.vocab()` is per script (`.script`), and library entries have a `source` field.

## What the config holds

| Section | Holds |
|---|---|
| `frame` | box size, bar (headline) y, baseline y, descender y, top of a half-bar form |
| `rules` | every validity and size threshold (see `rule_notes` for what each means and where it came from) |
| `recipes` | how a second stroke relates to the first (chain / branch / land): weight and allowed skeletons |
| `skeleton` | where stems, descenders and first strokes may sit |
| `half` | the geometry of half-bar letters (right-hand form, connector, left form) |
| `history` | letters the reviewer rejected as near copies, and the seed picks of the first rounds (Devanagari only; empty for a new script) |
| `paths` | traced real letters, corpus, curated library output, spec, units, keepers, patterns, profile |
| `engine` | file names and archetype weights the engine uses |

## Steps for a new script

1. Draw the real letters in the shared stroke-graph format and trace them to `conlang_forge/script/forms/<script>_graph.json`.
2. Copy `devanagari.json` to `<script>.json`; set `id`, `frame`, and point `paths` at the new script's files.
3. Build the script's vocabulary: `units.py` (body units), `mine.py` (connection patterns), `profile.py` (skeleton shares). They read and write the config paths.
4. Set rules from measurement first, then from review rounds. Several Devanagari rules can be switched off by value: `RING_FRAC` 0 allows closed loops, a large `MAX_TURN` allows long curls.
5. Run `sampler.py` for a sheet, review it, freeze approved letters, and build `<script>_library.json` with `build_engine_library.py`.
6. Wire the engine: `stroke_graph.library("<script>")` and `corpus("<script>")` load by name; a `pen_vocab` archetype and preset still need adding by hand.

## Still Devanagari-specific in code

- The four skeleton types (stem, descender, hang, half-bar) and their builders. All are built around a headline bar, so scripts without one (Thai and Armenian, for example) need new skeleton types and builders. That is the main code work for them.
- The orientation rules in `orient_ok` (strokes start along an axis, cups open along an axis, a "3" stacks, an S stands upright): their thresholds are config, but their existence is not.
- `templates.py` and the double-cup ("3") step in `body_gen.walk`: constructive body forms with Devanagari constants in the code.
- Mixing itself: generating from two vocabularies in one letter needs the pieces built in the common frame, and a rule policy for blends. Not built yet.
- The engine archetypes `dg_corpus` and `dg_library` and their weights in `pen_vocab.py`.
- `sig.py` thresholds (contact distance, merge distance, curve-run size) are shared constants, tuned on Devanagari.
