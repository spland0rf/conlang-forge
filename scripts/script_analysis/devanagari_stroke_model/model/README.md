# Stroke-graph model — Checkpoint v1.1 (stroke graph)

2 November 2026. All 47 Devanagari letters, plus double-cup variants of ॠ and ॡ, are confirmed correct against the hand-drawn reference sheet and its close-ups.

## Files

| File | What it is |
|---|---|
| `letters.json` | The model: one record per letter with strokes, junctions, structure and description |
| `graph.py` | Reclassifies grammatical marks as accents, splits corner strokes, gives every junction its member strokes and positions, adds frame info, and reports loose junctions |
| `build.py` | Source for the traced geometry (stroke paths and junction points). Later `add()` calls override earlier ones for the same letter |
| `semantic.py` | Derives the proportional `structure` list and English `description` from the paths |
| `render.py` | Builds `geometry.html` from `letters.json` |
| `geometry.html` | Letters drawn from the model, with tap-for-description |
| `stroke_table.html` | Junction counts, families, findings, and the accent grammar with Strict / Generated modes |

Rebuild: `python3 build.py && python3 graph.py && python3 semantic.py && python3 render.py`

## Coordinate system

- 100 × 100 box, x to the right, y downward.
- The headline (top bar) sits at y = 20; the baseline is about y = 88.
- Proportional only: shapes are approximate, structure is exact.
- In descriptions, "across" is measured along the bar (or the letter's full width if it has no bar), and "down" runs from the bar (0%) to the baseline (100%).

## Stroke roles (colors)

| Role | Color | Meaning |
|---|---|---|
| `body` | blue | Main compound form |
| `second` | green | A second compound form fused into the letter, structurally equal to blue (e.g. the Г shape, a plain stem, tails, diagonals) |
| `struct` | purple | Headline, short descenders, and short connectors between forms |
| `accent` | orange | Small modifier strokes above the bar, treated as independent "atoms" |

## Junction types

| Type | Mark | Meaning |
|---|---|---|
| `red` | red dot | Where different forms meet, or a form meets the headline |
| `touch` | orange ○ | Where strokes of one form touch (including corners between two strokes of one form) |
| `cross` | orange × | Where strokes of one form cross |

A point can carry both ○ and × (the 5-branch centre of ऋ / ॠ).

## Accent grammar

- Four accent types: 1 stroke left, 2 strokes left, 1 stroke right, 2 strokes right.
- Real Devanagari uses the first three (ऐ ओ, औ, ई). "2 strokes right" is for generated scripts only.
- An accent attaches only at an anchor, a point where a line touches the bar from below.
- At most one accent per letter, always on the right-most anchor. This keeps letters easy to tell apart.
- Modes: **Strict** reproduces real Devanagari. **Generated** applies the same rules to any script with a top bar, with selectable accent types.

## Key structural findings (Devanagari)

- Self-crossings come in two kinds: a tail crossing itself (इ ई झ द श), or a body crossing a stem (ऋ ॠ भ म).
- Open cup + connector to the stem is a common pattern: च ज ञ थ य स.
- True loops on the stem are rare: क ख व ब. Only ब has two loops.
- Open lobes and cups: ऌ ॡ ल (two lobes at a cusp), उ ऊ घ ध ह.
- Short purple descenders touch the bar (○) and meet the body at a red dot: इ ई ऌ ॡ ङ छ ट ठ ड ढ द ह.
- The Г shape (stem plus touching flag) appears in अ आ ओ औ ध भ. आ has two Г shapes touching.
- 5-branch junctions occur in ऋ, ॠ and औ. 3-stroke touches occur in ञ, स and ह.

## Next

1. A generated "Devanagari-like" script built from these statistics.
2. New scripts, in this order: Bengali, (optionally Gurmukhi), Tamil, Amharic / Ge'ez.

## Changes in v1.1

- **Grammatical marks are accents.** The ā vowel sign (आ ओ औ), the e/ai signs above the bar (ऐ ओ औ), and the length marks (ई ऊ ॠ ॡ) are orange, with a `function` tag. Marks that only distinguish consonants (फ tail, ब/ष diagonals) stay green.
- **Stroke graph.** Every stroke has an `id` and `kind`. Every junction has `members` (stroke id, `at` = fraction along the stroke, `where` = start / end / middle) and `branches` (ends count 1, pass-throughs count 2). 162 junctions, all validated with no loose ones.
- **Corners split.** Where a touch sits at a corner inside one path (Г corners, tail corners, double-cup cusps), the path is split into two strokes.
- **Frame record** per letter: headline extent, stems, bounding box, width-to-height ratio.
- **Fixes:** झ crossing point and ढ curl touch point now sit exactly on the strokes.
