# How Conlang Forge makes "Devanagari-like" letters

This is the end state of the Devanagari stroke work on `feat/compound-vocab` (checkpoint, 6 Nov 2026). It explains how a generated script gets letters that look like Devanagari without copying it: how a letter is described, how new ones are built, how they are checked, how bad ones are repaired, and how the ones you accepted reach the engine.

## The idea in one paragraph

Real Devanagari letters are a few strokes that attach to each other at a small number of recurring points: a top bar, a full-height stem, a short descender, or the end or middle of another stroke. We describe every letter as a **stroke graph**, learn which pieces and joins real letters use, then build new letters from the same pieces and the same joins, in new combinations. A new letter must read as Devanagari (the right pieces, the right joins, the right proportions) but must not be a real letter and must not duplicate another new one. People look at the results, and what they accept is stored as a curated library the engine draws from.

## 1. How a letter is described

Every letter lives in a 100 x 100 model box (x right, y down). The top bar is at y = 20 and the baseline at y = 88. A letter is a set of strokes, each with a role, plus a list of junctions.

- **Roles:** body (blue), second (green, a second fused form), struct (purple: the bar, short descenders, connectors), accent (orange: a small flourish that meets the bar from below).
- **Junctions:** red (two forms meet, or a form meets the bar), touch (strokes of one form touch), cross (strokes cross).
- **Skeletons** (what the body hangs from): a **stem** (bar plus a full-height vertical), a **descender** (bar plus a short purple drop to y = 36), **hang** (strokes straight from the bar), and **half-bar** (a form on the left, a short connector, and a form with its own top stroke on the right; no bar of its own).

The 49 real letters are stored this way (`conlang_forge/script/forms/devanagari_graph.json`) and are the fixed reference. They were confirmed against the user's drawings and tagged `devanagari-stroke-checkpoint-v1`.

## 2. Where new letters come from

There are two generators, which feed one curated library.

**Generator v2 (`scripts/script_analysis/devanagari_stroke_model/generator/gen2.js`).** Made in a parallel chat. It draws a style (how often a bar, which right-hand stem, which body shapes, how often accents) and builds letters from hand-written body forms such as hooks, cups, loops and arcs. It rejects letters that are too close to a real one or to each other. `gen_corpus.js` runs it over 40 styles and gives about 1,026 letters (the corpus). That pool is large and rough: only about 370 distinct structures, and about a quarter fail the size rules below. The user's page of 26 (G1 to G26, seed 7) is a hand-filtered slice of the same generator.

**The compound-letter generator (`scripts/script_analysis/compound_gen/`).** Built here. It makes letters from pieces measured on the real letters:

1. Pick a skeleton (stem, descender, hang) and an **anchor**, the first junction (on the bar, or the descender foot).
2. Build one to three body strokes. Each is a chain of **units** (a line, an arc, or a double cup, the "3" shape) sampled from the real bodies, rotated and scaled so its ends land on chosen junctions: the bar, the descender foot, the stem, or the end or middle of an earlier stroke. Recipes: chain, branch, land.
3. Half-bar letters (`compound_half.py`) are built separately: a left form (often a "3"), a connector leaving the base of one of its cups, and a right form that is either a G shape (vertical with a top stroke) or a short top stroke with a body hanging from its left end.

The rules (all in `rules.py`, frozen) come from the user's reviews. Examples: no floating strokes, every stroke end is on a junction or is a free end; strokes start and arrive along an axis; straight lines are exactly vertical or horizontal; no stroke closes into a ring or turns more than 300 degrees; the bar covers the body and the body is roughly centred under it; half-bar tops are about 0.30 of the vertical and the connector joins it at 0.28 to 0.56 of its height.

## 3. How a candidate is checked

A generated letter is kept only if it passes, in this order (cheap geometric checks first, the numpy tests last, which cut sampling time from about 150 s to about 100 s):

1. **Shape rules** (`valid()` in `compound_gen.py`): stroke shape, clearances from the bar, from the stem or descender, and from each other, crossings only at junctions, bounds.
2. **Size and whitespace rules**, calibrated on the user's redraws of letters they rejected for being too small and crammed:
   - the largest single stroke must be at least 0.40 of the bar width or the letter height;
   - the unfilled share of the frame (points farther than 10 from any ink) must be at most 0.50;
   - the largest empty circle must have a radius of at most 47.
   Stroke count per grid box is used only to compare two variants of one letter, never as a cap, and a mild preference keeps width and height about equal.
3. **Structural signature** (`sig.py`): strokes are merged when they continue end to end; each is labelled (vertical, straight, or a curve with a turn pattern and size class and opening direction); and the contact graph records which strokes touch and whether at an end or a middle. **Where along a stroke a contact sits is ignored**, so small shifts of an attachment point do not make a new letter (the user's rule). Equal signatures mean the same letter. A new letter must differ from all 49 real letters and from every letter already kept.
4. **Ink distance** against rejected and kept letters (a chamfer distance; half-bar letters are compared only with other half-bar letters on the left form and connector, because they all share the right-hand frame).

## 4. Repair instead of reject

A letter that fails only the size rules is repaired, not discarded (`repair.py`). The body group is scaled about its anchor (the stem, or the join with the bar), optionally slid along the bar, and optionally stretched on one side of the stem. Options include a **width-only stretch** (height unchanged) and height growth capped by the frame. The smallest change that passes wins. The structural signature must not change (same strokes, same joins, no new crossings), and the shape rules are re-checked. This fixed the user's four "too small" letters (A1, A4, A7, A12) the way the user redrew them. `repair_fast` tries about 40 candidates, cheap tests first, and finishes in milliseconds per letter. A full run of the sampler (`alphabet_gen/sampler.py`, settings in `spec.json`) takes about two minutes for 30 to 40 letters (stem 13 to 14, descender 7 to 8, hang 4, half-bar 6).

## 5. How the user's judgement enters

Each round the generator draws a numbered sheet. The user scores each letter 1 to 4 (very un- to very Devanagari-like), marks duplicates (D), and redraws or edits any that are close. Those answers turn into rules (for example the size rules above and the duplicate rule) and into curated letters. Review notes: `claude/alphabet-review-1.md` and `-2.md` in the Project. Edits to curated letters are made on data files (`approved_review1.json`, `approved_review2.json`, and the edit scripts beside them), so every change is reproducible.

## 6. The curated library and the engine

`conlang_forge/script/forms/devanagari_library.json` holds the accepted forms: the Generator v2 page letters with the user's edits, the descender and half-bar letters of review 2, and the approved letters of review 1, 54 in all, of which 51 are used (three match another letter by structure and are skipped). It is built by `alphabet_gen/build_engine_library.py` from the data files above, in the same role and path format as the corpus.

In the engine (`conlang_forge/script/stroke_graph.py` and `pen_vocab.py`) a Devanagari-like script draws consonants from three sources: the pen archetypes, the generated corpus (`dg_corpus`), and the curated library (`dg_library`, weight 12). Each library letter brings its own top bar, or none for half-bar and bar-less forms. Tests (`tests/test_stroke_graph.py`) check that real, corpus and library letters are one connected shape inside the box, and that the preset is deterministic and can draw library letters.

## 7. How to run it

```
python3 scripts/script_analysis/alphabet_gen/sampler.py            # a fresh sheet of generated letters
python3 scripts/script_analysis/alphabet_gen/build_engine_library.py  # rebuild the engine library from the data files
python3 -m pytest tests/test_stroke_graph.py tests/test_stroke_family.py
```

## 8. What is not done

- The generators' size, attachment and body-form ranges are not yet refitted to the curated library; the library is used as drawn forms only. That is the obvious next step, and it should raise the yield of the generators.
- Descender and stem letters still fall short of their targets (the generator needs many tries per accepted letter).
- The other scripts (Bengali, Tamil, Tengwar, Amharic, Hebrew) still use the older vocabulary. The same method applies once the user supplies stroke drawings for them.
- One older test (`tests/test_pen.py::test_style_sets_the_stroke_kind`) fails on the base branch and is untouched.
