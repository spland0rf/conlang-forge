# Writing-system generator: the visual grammar (analysis and proposal)

Status: proposal from a measured analysis of 13 reference scripts. Nothing is built yet except the analysis tooling in `scripts/script_analysis/`.

## 1. Goal and the owner's steer
Generate alphabetic-style writing systems (random, settings, hybrid, or inferred from an uploaded sample image) that can be paired with a conlang. Owner decision: **the exact shape of curves matters much less than connectivity**. So the grammar describes *how strokes connect* (a stroke graph plus where things attach and what sits beside it); curve geometry, contrast, serifs and slant are a separate, freely varied style layer.

## 2. What was analysed
Letters (not digits or punctuation) of Latin, Greek, Cyrillic, Armenian, Georgian, Hebrew, Arabic (isolated forms), Devanagari, Bengali, Tamil, Thai, Ethiopic (the first-order syllables) and Hangul (compatibility jamo plus sample syllables), rendered from installed fonts (sans where available; Arabic and Ethiopic only had a serif/neutral face). 13 scripts, about 620 letters. Tooling: `scripts/script_analysis/{corpus,render,measure,topology,motifs}.py`; results in `measurements.json`, `topology.json`, `motifs.json`.
Per letter: skeleton graph (stroke ends, junctions and their degree, loops, stroke count), where junctions and ends sit (top/middle/bottom, left/middle/right), detached marks (kind and position), reference-line contact (flat top, flat base, ascender, descender), stroke orientation shares, outline angularity, stroke-width contrast, and a pairwise shape distance for distinctiveness.
Caveats: fonts are one design per script; Tamil and Bengali lost a few unassigned code points; Arabic joins and Devanagari/Bengali/Tamil/Thai conjuncts and vowel signs were not rendered (studied from knowledge, see section 5); skeleton noise remains (stroke counts are approximate); numbers are used as priors, not truth.

## 3. What the measurements say

| Script | Closed letters | Ends / letter | Junctions / letter | Detached-mark letters | Flat top bar | Descenders | Distinct body topologies |
|---|---|---|---|---|---|---|---|
| Latin | 29% | 2.6 | 0.75 | 4% | 35% | 10% | 14 |
| Greek | 31% | 2.7 | 0.78 | 2% | 37% | 22% | 16 |
| Cyrillic | 39% | 2.5 | 1.0 | 3% | 23% | 9% | 13 |
| Armenian | 32% | 2.7 | 0.75 | 0% | 11% | 29% | 20 |
| Georgian | 39% | 2.6 | 0.61 | 0% | 36% | 48% | 13 |
| Hebrew | 7% | 2.3 | 0.48 | 0% | 56% | 19% | 4 |
| Arabic | 25% | 2.3 | 0.28 | **61%** | 11% | 58% | 7 |
| Devanagari | 30% | 4.9 | 2.7 | 9% | **85%** | 13% | 21 |
| Bengali | 39% | 4.4 | 1.9 | 2% | 48% | 0% | 20 |
| Tamil | 77% | 2.5 | 1.5 | 3% | 34% | 49% | 21 |
| Thai | **96%** | 2.1 | 0.6 | 2% | 11% | 11% | 16 |
| Ethiopic | 46% | 3.6 | 1.4 | 2% | 10% | 5% | **30** |
| Hangul | 28% | 2.8 | 1.1 | 0% | 28% | 0% | 13 |

Findings that shape the grammar:
1. **Most letters are tiny graphs.** Median letter: 2-3 stroke ends, 0-1 junctions, 0-1 loops. Branch junctions are almost all degree 3 (T, Y); degree 4 crossings are rare (X-like). Letters above 3 junctions only appear in the Devanagari/Bengali family, where a top bar hangs everything on one line.
2. **A handful of connectivity motifs cover everything.** Naming each body by (loops, ends, junctions) gives: open stroke, branch (T/Y/fork), branched tree (2+ junctions), ring, ring with tail, ring + branches, multi-loop. Their use is the main thing that differs between scripts: Hebrew is 52% open strokes and 33% branches; Thai is 48% rings and 35% multi-loop; Devanagari is 51% branched trees; Latin is a spread (25% branch, 21% open, 17% ring+branches).
3. **Topology alone does not separate letters.** Only 0-56% of letters in a script have a unique topology signature (Ethiopic highest at 56%, Hebrew and Arabic 0%). The rest are told apart by (a) *where* the parts attach, (b) proportions and which reference lines they touch, and (c) detached marks. So the grammar must include a placement layer and a mark layer, and the distinctiveness checker must work on all three.
4. **Reference lines are structural.** Devanagari hangs from a top line (85% have a flat top bar; junctions concentrate at the top: 44%); Hebrew is flat-topped (56% flat top) but sits on the baseline, with junctions spread evenly (31/38/31% top/middle/base); Latin/Greek/Cyrillic sit on a baseline with x-height and ascender bands; Georgian has a different, 3-band layout (48% descenders, 45% tall); Arabic uses a baseline with a long horizontal run and descending tails.
5. **Marks carry a whole alphabet's worth of distinctions in some scripts.** Arabic: 61% of letters have 1-3 detached dots (above 20, below 4, inside 2), so ~28 letters come from ~17 base shapes. Cyrillic (Й), Devanagari (nukta), and Latin (i, j) use the same device sparingly. Letters whose base shapes are identical (distance 0 in the checker) are exactly these base+mark families.
6. **Distinctiveness is measurable.** Mean nearest-neighbour shape distance between letters of the same script is about 0.45-0.6 on a 0-2 scale; the 10th percentile is 0.2-0.37 (excluding mark-only pairs, which are deliberately identical). A generator should reject a new glyph whose body is within ~0.2 of an existing one unless they are a declared base+mark or mirror pair.
7. **Style is mostly independent of connectivity.** Angularity (share of outline turning at sharp corners) ranges 0.11-0.56, stroke-width contrast 0.75-1.3, and scripts with the same motifs look different. Orientation mix is similar everywhere (about 25% horizontal, 35-45% vertical, 25-40% diagonal) except Hebrew/Armenian (vertical-heavy) and Hangul (almost no diagonals, 11%).

## 4. The grammar

### Layer A: script system (chosen once per script)
- `kind`: alphabet | abjad | abugida | syllabary | featural-block (Hangul-like).
- `direction`: ltr | rtl | ttb.
- `case`: single | bicameral (second set derived from the first by a "case rule": scale, simplify, ascend).
- `lines`: which reference lines exist and which are used: baseline, x-height, ascender, descender, **topline** (hanging) , **midline**. Per letter, a glyph declares contact: `sits`, `hangs`, `floats`.
- `joining`: none | cursive (entry/exit points, 2-4 positional forms) | hanging-bar (letters share a topline) | block (syllable cells).
- `density` (typical strokes and junctions per letter) and `inventory size` (from the language's phonemes).

### Layer B: the stroke graph (the core)
A glyph body is a small connected graph:
- **Nodes:** `end` (free stroke end), `junction3` (T/Y), `junction4` (cross), `loop` (a cycle, optionally with a tail). 
- **Edges (strokes):** each has only a coarse class: orientation (H, V, D, curve), length class (short, normal, long), and for curves which way they open. No coordinates.
- **Motifs** (reusable sub-graphs; the "letter parts"): `stem`, `arc`, `hook`, `bar`, `ring`, `ring+tail`, `fork` (Y), `tee` (T), `comb` (stem with k teeth: m, n, Ethiopic), `ladder` (several bars on a stem), `cross`, `double-ring`, `spiral/curl`.
- **Attachment rules:** a motif attaches to another at a *zone* (top, middle, base; left, centre, right) and *side* (to the left/right of a stem, on top, through). The measurements give the priors: across scripts junctions sit in the top third 25-64% of the time, middle 24-52%, base 11-37%; stroke ends sit top 33-70%, base 20-48% (even in most alphabets, top-heavy in Arabic, base-heavy in Tamil).
- A glyph = 1-4 motifs joined by attachment rules, with a reference-line contact for each (e.g. `stem sits`, `bowl attaches right-middle of stem`).

### Layer C: marks (detached or attached)
- `kind`: dot | bar/stroke | small-ring | hook | complex.
- `position`: above | below | inside | beside (and `count` 1-3, plus doubling).
- `function`: distinguishes consonants (Arabic dots), vowels/tones (Thai, Devanagari signs), length/palatalisation (Cyrillic breve, Latin accents).
- Mark vocabulary is small and shared across the whole script (Arabic: 1, 2, 3 dots above/below; 7 bars above).

### Layer D: families and derivation (makes a script look systematic)
Letters are related by one of:
- `base+mark` (Arabic ب ت ث; Cyrillic и/й),
- `mirror/rotate/flip` (b d p q; Hebrew pairs; Ethiopic orders),
- `stem series` (Ethiopic: one base per consonant, 7 vowel orders by small fixed modifications; Devanagari matras attach to a consonant),
- `featural` (Hangul: place of articulation to base shape; aspiration or tenseness to an added stroke or doubling),
- `case rule` (upper/lower).
A "systematicness" dial sets how many letters belong to families vs. are independent (Latin lowish, Hangul/Ethiopic highest). Because our generator already knows each language's sound classes, families can follow phonology: voiced/voiceless pairs, vowel orders, nasal series.

### Layer E: composition and layout
- `linear` (alphabets, abjads): letters in a row on the lines.
- `satellite` (abugidas): consonant base + vowel sign in a slot (`pre`, `post`, `above`, `below`) + optional virama/conjunct.
- `block` (Hangul-like): initial/medial/final parts packed in a square by fixed layout rules (e.g. vertical medial right, horizontal medial below).
- `cursive`: each letter declares entry/exit points on the baseline and up to 4 positional shapes (isolated/initial/medial/final) that differ only in connecting strokes. (Deferred to a later stage.)

### Layer F: style (free parameters, do not affect connectivity)
Curve vs. straight ratio, angularity, stroke-width contrast and pen angle, terminals (flat, round, serif, flare), slant, width/proportion, roundness of loops, overall weight and size. Chosen per script, with small per-letter jitter. Exact curve geometry is generated, not specified.

## 5. Expressing the 13 reference scripts in the grammar
| Script | Kind / layout | Characteristic grammar |
|---|---|---|
| Latin | alphabet, linear, bicameral | sits on baseline, ascender/descender bands; motifs spread; few marks; letters related by mirror/rotate (b d p q) |
| Greek | alphabet, linear, bicameral | like Latin with more open curves; final-form variant |
| Cyrillic | alphabet, linear, bicameral | more branched/ring+branch; base+mark (й) and shared stems |
| Armenian | alphabet, linear, bicameral | many hooks/tails, descending; hook terminals |
| Georgian | alphabet, linear, unicameral(ish) | rings and tails, 3-band layout (tall + descending) |
| Hebrew | abjad, rtl | few motifs (open stroke, branch), flat-topped on the baseline, final forms (stem extended below) |
| Arabic | abjad, rtl, cursive | ~17 base shapes x dot marks; baseline join, 4 positional forms |
| Devanagari | abugida | hanging bar topline; branched trees; vowel signs pre/post/above/below; conjuncts |
| Bengali | abugida | like Devanagari, rounder, some without bar |
| Tamil | abugida | loops and rings dominant, no bar, vowel signs around base, pulli mark |
| Thai | abugida | ring/loop-chain heads, tone marks above, vowel signs 4 sides |
| Ethiopic | abugida/syllabary-like | stem series: ~35 bases x 7 orders by small appended strokes |
| Hangul | featural-block | place-of-articulation shapes + added strokes; block composition |
The grammar can express all of these at the connectivity level by construction (the motifs and attachment zones were derived from them). A test of the claim is stage 2: generate letters from the grammar and check that measured statistics fall inside the range of the references.

## 6. Priors for "likely" random scripts
Derived from the table above, with ranges so generated scripts look real:
- loops per letter: 0 for 40-70% of letters; 1 for 25-60%; 2+ rare (under 10%) except in Thai/Tamil-like scripts.
- stroke ends per letter: 2-3 typical (alphabets), up to 5 for hanging-bar scripts.
- junctions per letter: 0.3-1.0 typical; up to 2-3 for hanging-bar scripts; degree-3 junctions about 95% of all junctions.
- detached marks: 0-4% of letters for most scripts; 60% for a dot-differentiated abjad.
- topology classes: 13-30 distinct body topologies for a 30-40 letter script; use position and marks to separate the rest.
- reference lines: baseline always; ascender/descender ~10-50% of letters; topline scripts have 50-85% flat-top letters.
- orientation mix: 25% horizontal / 40% vertical / 30% diagonal as the default; shift toward vertical for rounded or Armenian-like styles, away from diagonals for Hangul-like.

## 7. Distinctiveness checker (needed before any generation)
Pairwise distance on the three layers: connectivity signature, attachment-zone pattern with reference-line contact, and mark pattern. Reject new letters within ~0.2 (pixel-normalised) or with identical topology + zones + marks unless declared a family pair. The measured pair distances above calibrate this.

## 8. Sample-image inference (later)
Image -> components -> skeleton graph -> the same signatures as above, so an uploaded sample yields: kind guess, direction, line structure, motif histogram, mark share, style parameters (angularity, contrast, terminals). The model then makes the judgement calls (is that a diacritic or a letter? abugida or alphabet?) and the result is shown as editable settings. The analysis code here is the basis for that step.

## 9. Suggested build order
1. Review and adjust this grammar (owner).
2. Generator for linear, unconnected alphabets: motifs -> glyph graphs -> simple stroke geometry -> SVG; distinctiveness checker; statistics tests against section 6.
3. Pair with a language (letter per phoneme, families follow sound classes), render in dictionary/grammar book/translator, export an SVG sheet and (optionally) a font.
4. Marks and families dials; featural option.
5. Image inference.
6. Satellite (abugida), block, and cursive layouts.

## 10. Open questions
- Font export vs. SVG-only? (font requires the layout rules for marks and joining)
- Should the first release include abugida/block layouts, or alphabets only?
- Style range: realistic calligraphic only, or also runic/angular/fantastical?
- Upload your own images of these scripts (handwriting, inscriptions, other fonts) to test the analysis beyond clean fonts.
