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

## 11. Owner decisions (2026-10-13)
- **First pass = the simplest correct sans-serif version of each writing system.** Serifs, block/formal hands, calligraphic and cursive *styles* come later.
- **Joining is a setting of the script, not a style.** `joining` = none | primary (joined-primary, as in Arabic: the joined forms are the normal writing) | optional (an unjoined primary form with a secondary connected form, like Roman cursive). The first pass supports joined-primary scripts as one option, with deliberately simple rules: each letter has `joins` (both sides | previous only | none), baseline entry/exit ports, and up to four forms (isolated, initial, medial, final) derived from one body by simple rules (add connecting stubs, collapse descending bowls to a baseline tooth, keep marks with the body). More elaborate join transformations and ligatures are experiments for later.
- Reference images are being supplied script by script (Arabic first; observations from the Arabic charts: 6 right-joining-only letters, ~17 shared bodies for 28 letters, forms differ mainly by connecting strokes, bowls collapse to a tooth mid-word, dots stay with their body).

## 12. Grammar v2: revisions after reviewing reference images (Arabic, Devanagari, Bengali, Tamil, Thai, Ethiopic, Hangul)
Sections 4-5 are the first draft from font measurements. Where this section differs, this section wins. Source: owner-supplied charts and text samples (2026-10-13). The Latin, Greek, Cyrillic, Armenian, Georgian and Hebrew samples from fonts were judged sufficient for the first pass.

### 12.1 Script-level settings (chosen once per script)
- `kind`: alphabet | abjad | abugida | series | block.
- `layout`: linear | satellite (consonant base + vowel signs in slots) | series (syllable = base + fused order modifier) | block (syllable cell built from parts).
- `direction`: ltr | rtl | ttb.
- `joining`: none | primary (joined is the normal form) | optional (unjoined primary, connected secondary; later). `join_line`: baseline (Arabic) | topline (Devanagari, Bengali bar).
- `conjuncts` (satellite layout): none (explicit virama/pulli, Tamil, Thai) | linear (first consonant drops its right stem and joins at the bar) | stacked (stemless consonants stack vertically). Opaque ligatures and special ra/ya forms are later.
- `word_separator`: space | mark | none; `punctuation`: small dot-based set (word separator, sentence end). Thai writes no word spaces; Ethiopic has ፡ and ።.
- `case`: single | bicameral. `systematicness` and `featural` dials (below).
- First pass is simplest correct sans-serif, monoline. Serifs, calligraphic/cursive/block hands and loop-vs-open terminals are style, later.

### 12.2 The stroke graph (unchanged core)
Connectivity is the grammar: nodes (end, junction3, junction4, loop), edges with coarse orientation/length, reusable motifs, attachment zones, reference-line contact. Added parts vocabulary for satellite scripts: `bar` (headline), `stem`, `body`. A half-form (conjunct) is the body without its stem.

### 12.3 Joining (joined-primary)
Simple first-pass rules: each letter has `joins` (both | previous-only | none), entry and exit ports on the join line, and up to four forms (isolated, initial, medial, final) derived from one body: add connecting stubs, collapse a descending bowl to a baseline tooth when joined (Arabic ba/ta/tha/nun/ya share one tooth body), keep marks with the body. About 17 bodies carry 28 Arabic letters, so base+mark families are central. For topline joining the bar spans the letter's full width so neighbours touch. Ligatures (lam-alif) and richer transformations are later.

### 12.4 Marks, slots and frames (satellite layout)
- A consonant base takes marks in named **slots**: left (pre-base), right, above, below, or a **frame** that fills several (circumfix: left+right, right+above, left+above...). Each vowel sign is a frame, not a single mark.
- Left-slot signs are written before the consonant but read after it (layout reorder rule).
- A slot has **levels** (vowel nearest the base, then tone mark, then silencing mark), needed for Thai stacking.
- A frame part can be a stroke, a small mark, or a copy of another letter shape (Thai เ-ีย, ัว; Tamil ௌ).
- Signs may have **variants chosen by a property of the base** (Tamil u/ū attach differently to stem-final vs bowl-final consonants); keep to a default form plus one or two variants.
- Short/long vowel pairs differ by one added component (`+LONG`).
- Dots and virama/pulli attach (nukta below, virama below or pulli above); Arabic dots are detached marks. Independent vowels are either a carrier plus mark or separate shapes (setting).
- No inherent vowel written in some scripts (Thai) or visible virama (Tamil): the unwritten-vowel convention is a setting of the language pairing, not of the glyphs.

### 12.5 Families (what makes a script look systematic)
- `base+mark` (Arabic dots, Cyrillic й, nukta).
- `mirror/rotate`, `case rule`.
- `series` (Ethiopic): a base plus an ordered list of **orders**, each a modifier with an anchor zone and kind (tick at right-middle, foot at lower right, lengthened leg, small loop, ring, left hook), the same modifier applied to every base; optional extra columns (labialised); per-row exceptions allowed. A syllable is one compact glyph.
- `featural` (Hangul): five base shapes by place of articulation (velar angle, tongue-tip hook, lip box, tooth, circle); manner is added by strokes (aspirated = +1 stroke; further place variants add one); tense = doubling; one outlier (ㄹ). Vowels: one long stroke (vertical or horizontal) plus a tick on a side; two ticks = glide; compound vowels = concatenation of two vowel glyphs. About 40 parts generate every syllable block.
- `minimal pair` (Thai): one base plus one small visible change (notch, loop, tail, cusp): ข/ฃ, ค/ฅ, ฎ/ฏ, ถ/ฐ, ผ/ฝ, พ/ฟ, บ/ป. The distinctiveness check uses a lower threshold for declared pairs but requires the change to be visible at normal size.
- Checker additions: no base+modifier may look like a different base (series); parts must be distinct, then blocks are checked for legibility at their smaller size (block).

### 12.6 Block layout (Hangul-like)
A syllable cell is a square holding initial consonant (C), vowel (V) and optional final (F, one or two consonants). Arrangement is set by vowel orientation: vertical vowel = C|V side by side; horizontal vowel = C above V; compound vowel = C top-left, horizontal part below it, vertical part along the right; the final goes in a bottom row spanning the cell (split in two for a double final). A silent placeholder fills C when absent. Each part is scaled to its sub-cell. Blocks are never split across a line; modern text separates words with spaces.

### 12.7 Series layout details (Ethiopic-like)
7 orders typical (plus optional 8th/9th); about 33-35 bases, about 250 glyphs. Orders are defined once per script as modifiers and then applied to bases through the base's anchor zones.

### 12.8 Style layer (not structure)
Curve vs straight, angularity, contrast, terminals (flat, round, loop vs open: a Thai head loop is decoration, not identity), slant, weight, proportion. The first pass fixes these to a simple monoline sans.

### 12.9 Updated mapping of the reference scripts
| Script | kind/layout | joining | conjuncts | key rules |
|---|---|---|---|---|
| Latin/Greek/Cyrillic | alphabet/linear | none | n/a | baseline bands, mirror/rotate, base+mark |
| Armenian/Georgian | alphabet/linear | none | n/a | hooks and rings, tall/descending bands |
| Hebrew | abjad/linear, rtl | none | n/a | few motifs, flat tops, final forms |
| Arabic | abjad/linear, rtl | primary, baseline | n/a | 4 forms, shared bodies, detached dots, 6 right-joining-only letters |
| Devanagari | abugida/satellite | primary, topline | linear + stacked (+ special later) | bar/stem/body, slots incl. left i, frames o/au, nukta, virama |
| Bengali | abugida/satellite | primary, topline | linear + stacked | left e/ai, circumfix o/au, ra/ya subjoined forms |
| Tamil | abugida/satellite | none | none (pulli) | rounded, circumfix, base-dependent u/ū variants |
| Thai | abugida/satellite | none | none | four-sided frames, stacked levels, no word spaces, loop terminal |
| Ethiopic | series | none | none | orders as modifiers, extra columns, ፡ ። |
| Hangul | block | none | n/a | featural consonants, tick vowels, C/V/F cell layout |

### 12.10 First-pass scope (owner-approved direction)
Simplest correct sans-serif for each kind; joined-primary supported as a script setting with simple rules; conjuncts limited to none/linear/stacked; series and block layouts included. Deferred: cursive/calligraphic/serif styles, optional joined secondary forms, opaque ligatures, special subjoined forms beyond a simple ra/ya option, image inference, abugida reordering edge cases.

## 13. Generator stage 1 (implemented)

Package `conlang_forge/script/`; run with `python -m conlang_forge script --seed N [--pin dial=value ...] [--out script.json] [--svg sheet.svg]`.

**Modules.** `spec.py` (the dials, priors, `resolve(seed, pins)`), `geometry.py` (strokes, Chaikin rounding, SVG paths), `graph.py` (connectivity analysis, symmetric q90 shape distance), `motifs.py` (bodies grown on a 5x5 grid, connected by construction), `marks.py` (parts and slot placement), `generate.py` (letters, families, signs, punctuation, digits), `layout.py` (syllable composition, spacing, direction, line breaks), `render.py` (SVG specimen and sample text).

**Covered.** Linear alphabets, abjads (optionally with vowel points), abugidas with slot-based vowel signs (left, right, above, below, two-part frames), the `+LONG` rule (a long vowel sign is the short sign plus one stroke or dot), virama, diacritic marks, mirror and 180-degree rotation twins that follow related sounds (p/b, t/d, s/z, ...), optional topline bar, optional baseline joining (simple end stubs), word separators, digits, punctuation, ltr/rtl. Every dial can be pinned; unpinned dials are drawn from priors. One random stream per part, so pinning one dial leaves unrelated parts unchanged. Roundness never changes strokes (tested), so style stays a pure rendering choice.

**Distinctiveness.** Each new letter must be at least `min_distance` (default 0.22 em) from every other letter. If the space is crowded the threshold relaxes in two steps and shapes get denser; failing that, the most distinct candidate seen is used. Declared pairs (mirror, mark, long/short) are exempt, which the q90 metric needs because a dot or tick is only a few percent of a letter's ink.

**Calibration (60 seeds).** Median letter has 2 ends, 1 junction, 0 loops (reference scripts: 2-3 / 0-1 / 0-1); 8-87% of letters have a loop depending on the loops dial (references 0-56%, Hangul-style and Tamil higher); no letter outside the declared mark families is disconnected; nearest-neighbour distance p10 is 0.15 median overall and 0.22 for alphabets (references 0.2-0.37). Generation takes about 0.5 s per script.

**Known gaps (next stages).** Series (Ethiopic) and block (Hangul) layouts; Arabic-style joined forms with shared bodies and four positional shapes; conjuncts; pairing a script with a conlang's phonology; font export; image inference; serif, cursive and brush styles. Letters are plain on purpose: no glyph is polished by hand, so a few shapes will look odd and the owner's review of specimen sheets should drive the next tuning of `FAMILY_WEIGHTS` and the abugida sign sizes.

**Smooth drawing (added after owner review of the first specimens).** Strokes are drawn with fillets, not as raw polylines: a right angle (within 18 degrees of 90) stays crisp, every acute or oblique corner inside a stroke becomes a smooth quadratic curve, and runs of short segments blend into one curve. Rings are 8-point and arches carry shoulder points, so they draw as ellipses and round arches rather than hexagons. The roundness dial prior now favours fully smooth (about 90% of seeds); 0 remains available as a deliberate angular style. Bodies with hairpin turns, very short strokes or stubs are rejected. Known remaining roughness: two separate strokes that meet at an acute apex (A, V built from two strokes) are not yet rounded, and abugida vowel signs can crowd their letter.

**Corner styles (revised after owner review).** Each stroke is drawn one way: sharp (V, A, W: crisp angular corners), smooth (O, G, S: every corner rounded), blocky (E, H, F: right angles only) or hybrid (D, B, P: crisp right angles beside rounded curves). One stroke never mixes sharp and smooth corners, but a compound letter may combine strokes of different kinds. The `corner_style` dial picks `mixed` (each stroke chooses by its own corners; the default), or forces `smooth`, `sharp` or `blocky` for the whole script (blocky grows letters from right-angle skeletons such as E, F, H, L, P, S, T, Z and caps the inventory at 22 consonants because the form space is smaller). `roundness` now only sets how round the rounded corners are. Sharp apexes where two strokes meet are allowed as intentional shapes. A final safety pass replaces any two unrelated letters that came out nearly identical.

**Characteristic shapes and the letter frame (added after owner review).** Each script picks `motif_count` (0-6) characteristic shapes of medium complexity: ring, two stacked rings, triangle, inverted triangle, crossed X, diamond, ring with a bar, trident, target, double triangle (blocky scripts use box, stacked boxes, plus, box with bar, ladder, nested boxes, E-like). Sound classes (labial, coronal, dorsal, glottal, front/back/central vowels) are each given a shape, and the letters of a class are that shape plus one variant (stem down/up/left/right, bar, dot inside, open gap, rotation, flip, hook) that no other letter of the class uses; `motif_share` sets how many class members follow the rule. Voiced/aspirated partners still derive from their base letter by mirror or mark. Letters also sit in one standard frame: ink fills the frame top to bottom and left to right, widths vary by about 10%, only a minority of letters rise or fall outside it (ascender and descender shares now default to 0-12%), and a letter's centre of gravity must stay within `frame_tolerance` of the frame centre (a few lopsided letters, narrow stems and bars are exempt). Specimen sheets label each motif letter with its shape and variant.

**Joining modes (implemented).** `topline: bar` and `joining: baseline` give fully connected scripts (a shared bar along the top, or a join line along the bottom). `joining: partial` joins some letters and breaks the chain at others, as in Arabic's non-joining letters: each letter is `both` (joins on both sides), `prev` (joins only to the letter before it) or `none`, and a link is drawn between two neighbours only when the first joins forward and the second joins backward. `joining: none` leaves every letter free-standing. Join stubs are marked per side and trimmed per letter, so right-to-left scripts connect on the correct side. Not yet: positional letter forms (initial, medial, final) and shared-body joined shapes.

## 14. Tuning notes (letterform pass 2)

- **Sign placement.** Left and right vowel signs stay inside the letter frame (bottom, middle or top aligned) and attach to the nearest ink in that band, with a short tether stroke when needed. Above and below signs are clamped to the descender-to-ascender range.
- **Distinctness.** `min_distance` defaults to 0.28 (motif relatives use half). Candidate bodies are tested with an early-exit threshold check (`far_enough`). The band (x-height, ascender, descender) is chosen once per glyph, so crowded inventories do not drift toward tall letters.
- **Safety net.** After generation, any two unrelated letters closer than 0.05 (measured at a fine 0.05 sampling step, because coarse sampling can hide near-duplicates) are regenerated; the pass repeats until stable.
- **Speed.** Median about 1.5 s per script; crowded abugidas take up to about 8 s.

## 15. Letter-frame and similarity rules (pass 3)

Rules from the user's review of the specimen sheets:

- **A. Bodies stay in the frame.** A letter body (including every characteristic shape) is drawn at its natural proportions inside the main frame, baseline to x-height. It is never stretched to fill an ascender or descender band.
- **B. Ascenders and descenders reach the lines.** They are an added stroke from the body's top or bottom to the ascender (1.55) or descender (-0.5) line. Shape variants `stem_up`, `stem_down`, `hook` and `through_v` do the same and decide the letter's band.
- **C. Variants differ by topology, not scale or placement.** Distinctness is measured on points with x normalised by letter width, and bodies fill the frame, so a stretched or shifted copy of a shape counts as the same letter. Mirrors and rotations remain legal distinctions. Rotating a shape that is symmetric under that rotation (an X turned 90 degrees) is rejected as too close.
- **D. Similar looking letters sound alike.** Each phoneme belongs to a sound group (vowel, plosive, affricate, fricative, nasal, approximant). A group owns one characteristic shape, and vowels never wear a consonant's shape. The place of articulation selects the variant (`PLACE_OPS`), so every labial wears similar variants across manners. Plain bodies grow from stroke families preferred by the group (`GROUP_FAMILIES`). At least four shapes are used whenever motifs are on. `metrics.sound_coherence` reports within-group against across-group distance and how often a letter's nearest look-alike is in its own group.
- **Safety net.** The final pass compares at a 0.05 sampling step (coarser steps hid near-duplicates) and repeats until stable.

## 16. Grammar v3: the complexity spectrum (from the Egyptian to Latin alphabet-evolution chart)

Source: the owner's chart of the same letters in Egyptian hieroglyphs, Proto-Sinaitic, Phoenician, Ancient Greek and Latin (2026-10-14). The hieroglyphs are not copied. The other four columns show one set of letters at four points between *complex and pictorial* and *simple and bold*. We take rules from them, not shapes.

### 16.1 The complexity dial

`complexity` (0 = ornate and pictorial, 1 = minimal and bold) is a script-level dial that sets how a letter's core shape is built. It replaces ad-hoc density and loops settings at the extremes, and the existing `density` and `loops` dials act only within it.

| Level | Reference column | Strokes per letter | Curves | Corners | Details |
|---|---|---|---|---|---|
| 0.0 - 0.25 ornate | Proto-Sinaitic | 4-7, often several junctions | many, organic, uneven | few sharp | small features: an eye, a loop, a curl, a tick, a finger |
| 0.25 - 0.5 | Phoenician | 2-4 | a few | some sharp | one or two details survive, otherwise one line plus a branch |
| 0.5 - 0.75 | Ancient Greek | 1-3 | few | mostly straight with sharp corners and right angles | features are structural (a bar, a bowl) |
| 0.75 - 1.0 bold | Latin | 1-3, one decisive feature each | very few | straight strokes, right angles, one bowl | no decoration; each letter is one idea |

### 16.2 Simplification operators (how a complex shape becomes a plain cousin)

These make the evolution reproducible: apply them, in order of increasing complexity setting, to a core shape.

1. **Drop details.** Remove strokes shorter than a threshold, and dots or tiny loops that do not change connectivity.
2. **Straighten.** Replace a curved stroke by a straight one, or by a polyline with one corner.
3. **Open or close.** An enclosed outline loses a side (box to bracket, ring to arc) or a gap closes (C to O). The loop count is then a variant axis, not a property of the shape.
4. **Collapse parallels.** A group of parallel strokes (ladder, harp, comb) becomes two or three.
5. **Normalise orientation.** Rotate or mirror the figure to the nearest upright, left-to-right orientation; the shape keeps its identity and stops tilting.
6. **Reduce to the skeleton.** Keep the stem plus the one or two strokes that make the shape distinct.

Rule: simplification must keep the letter distinct (rules A-D, section 15 still apply). If two letters collapse to one shape, the simpler form stays on one and the other keeps its complexity or takes a variant.

### 16.3 Recurring structural parts (the "family parts")

Related letters in the chart are assembled from a small set of parts. Letters are built by choosing a part and one modifier:

| Part | Latin examples | Notes |
|---|---|---|
| stem + bowl | B D P R | bowl position (upper, lower, left, right) and size distinguish the letters |
| stem + branches | E F Y K | branch count, direction and where they attach |
| loop + tail | Q R G | ring with one stroke leaving it |
| circle, open or closed | O C G | the aperture (side and size) is the variant |
| crossing | X T + | two strokes crossing or meeting at a T |
| parallel bars + link | Z I H | two bars and a joining stroke |
| zigzag, wave | M N S W | peaks and troughs; count and phase vary |
| box or bracket | Proto-Sinaitic house, D | enclosed rectangle losing a side as it simplifies |
| angle, hook | L J V | one corner with one or two arms |

Modifiers are the existing variants (stem, bar, dot, open, rotate, mirror, flip, hook, through) plus: *aperture side*, *bowl position*, *branch count*, *peak count*, *tail direction*.

### 16.4 Style families and subset selection

Each core part and each modifier is tagged with the style families it suits (round, angular, blocky, spiky, pictorial, minimal). A script draws a subset of parts and a subset of modifiers whose tags overlap, so scripts look different from each other but consistent inside. The complexity dial picks the form of each part (ornate form to bold form). The owner's own drawings of core shapes and modifier classes (planned) become the pool for these tags. Until then, the hand-built list in `shapes.py` is the pool.

### 16.5 Checks added to the tests (planned)

- Median strokes per letter falls as `complexity` rises (monotonic across seeds).
- Bold scripts (complexity above 0.75) have at most 3 strokes per letter and no dots or tiny loops.
- Ornate scripts (below 0.25) allow details but still pass the distinctness rules.
- A letter simplified from a complex form is still at least `min_distance` from every other letter.

### 16.6 Implemented (first version)

- `complexity` dial (0-1, prior 0.1-0.95). It sets a stroke budget per letter (8 / 6 / 4 / 3 strokes at 0 / 0.25 / 0.5 / 0.75), a stroke floor for ornate scripts (4 strokes below 0.15, 3 below 0.4), and the effective density of plain bodies. The budget and floor are relaxed a little when the alphabet is crowded.
- Library: about 36 round and angular figures plus blocky ones, in `shapes.py`. Ornate: eye, ankh, fish, person, harp, comb, curl, zigzag, house, target, nested rings. Structural: P, B, F, E, Y, T, L, H, Z, N, M, W, V, K, Q, arc, S. Each has a complexity window (`LEVELS`) and round or angular tags that filter the pool by corner style (`eligible`).
- Simplification (`simplify`): at 0.5 and above, dots are dropped and the shortest non-essential strokes go until the budget is met. At 0.5 and above the variants `dot_in`, `through_v` and `through_h` are not used; at 0.75 and above `hook` is also excluded.
- Variants that add a stem now reach the descender or ascender line exactly, whatever the figure's own extent.
- Not yet implemented: open/close and collapse-parallels operators, the aperture, bowl-position, branch-count and peak-count modifiers, and the owner's drawn library as an extra pool.

## 17. Style families from the owner's drawn sheet (implemented first version)

Source: the owner's hand-drawn sheet (2026-10-14) with four families, each with base forms and "modified with lines" rows. Owner answers: a script may blend two families (never all four, and never all modifiers); a modifier may bend; a modified form is a letter in its own right in a pure alphabet, while in scripts with diacritics, standard limbs or inflections it marks a different pronunciation (voicing, vowel context) of the same base; any letter may be derived from another by mirroring, a 180-degree turn, or a 90-degree turn either way.

- **Families** (`families.py`): spikey (peaks x1-3, triangles, chevrons, diamonds single/side by side/stacked, X, stacked triangles), curvy (C, reverse C, arches and cups x1-3, S and mirror, waves x1-3, 3 and epsilon, six, spiral), bubbly (circle, two or three stacked, two or three in a row, D, B, domes, circle in dome or triangle), boxy (box, open boxes, T and inverted T, steps, crenellations x2-3, stacked and side-by-side boxes). Each form has a complexity window.
- **Selection** (`family`, `family2` dials): one or two families per script. A pinned corner style steers the family (smooth gives curvy or bubbly, sharp gives spikey, blocky gives boxy); a pinned family steers the corner style (mixed if the two families differ in style). The second family supplies the vowels' shape and one consonant manner.
- **Modifiers** (`MODS`): each family has a list of line additions (stem up or down to the ascender or descender line, bars, cross, X, through-lines, underline, overline, slash, tail, flag, arrow, hook, curl, dot). Each script draws 6-9 of its families' modifiers and 3-5 turns or mirrorings (`flip_x`, `flip_y`, `rot90`, `rot270`, `rot180`). Letters wear a single modifier, then pairs, if singles run out. Bold scripts only use plain strokes and bars.
- **Turned and mirrored twins**: a related letter (voiced partner and so on) is a turned or mirrored copy of its parent, up to three per parent, chosen at random from the transforms that stay distinct. Letters with an ascender or descender only mirror left to right.
- **Not yet done**: modifier as a diacritic mark for voicing or vowel inflection (the same line used consistently across all bases, as the owner described for non-alphabetic scripts); bent modifier variants beyond hook and curl; the clusters and nested figures in the sheet's bubbly rows; per-family weights for modifiers.

### 17.1 The earlier library is kept (additive)

Owner request (2026-10-14): the owner's drawn library is added to, not substituted for, the earlier shapes. Every figure from `shapes.py` (rings, nested rings, triangles, X, trident, target, the Egyptian-to-Latin structural parts, the orthogonal boxes and ladders) now also belongs to the family it fits, and a fifth family, `classic`, holds the letter-like figures (P, B, F, E, Y, T, L, H, Z, N, M, W, V, K, Q, arc, S and the pictorial ones) with the earlier modifier set. A script can pick `classic` as its main or second family. The earlier random-body generator remains the fallback when `motif_count` is 0. New real-script or invented forms are added to `FORMS` the same way. Group shapes are kept where possible: when a letter does not fit its group's shape, the distance threshold is relaxed in two steps before another figure is tried.

## 18. Feature marks and the Writing systems screen

### 18.1 Consistent marks
Sounds that differ by one feature (voiced, aspirated, rounded, open, lax) share one mark per feature in a script. The mark is either a small diacritic part or a safe modifier (underline, overline, bar, cross, slash, tail, x_in) applied to the base letter's shape. If the mark does not fit, the sound becomes its own letter. Letter records carry `feature`, `mark` and `relation`.

### 18.2 Dense figures
Dense figures (ladder, E3, harp, comb, person, nest, house, boxplus, target) only appear in ornate scripts (complexity 0 to 0.3) so bold scripts stay simple.

### 18.3 API and UI
- `GET /api/script/dials` returns the dial catalogue grouped for display (Style, Size, Shape mix, Letters, Joining).
- `POST /api/script/generate {seed, pins}` returns `spec` (all resolved values), `metrics`, `script`, `specimen` (SVG sheet) and `sample` (SVG of sample words). Bad seeds or pins give HTTP 422. Results are cached by (seed, pins).
- Web page `#/scripts`: a seed field, Randomize, a control per dial. Changing a dial locks it; unlocked dials show the value the seed chose. "Unlock all" clears the locks.

### 18.4 No triple repeats in base forms
A base letter repeats a peak, triangle, bump or wave at most twice; triples are too much to write and to read. Circles are the exception: three circles are allowed. A repeat of three is only acceptable as a modifier that carries a grammatical meaning. Implemented by removing the triple figures from the families (3-peak spikes, 3-triangle chains, 3-bump arches, 3-period waves, 3-notch crenellations, the open zigzag, the three-curve sigma) and by a guard on every generated letter and digit that rejects a stroke turning back on itself five or more times. The two-period wave is kept for ornate scripts only (complexity up to 0.4).

### 18.5 Snorkel modifiers
A snorkel is a modifier stroke: a short segment, a 90-degree bend (rounded in smooth styles, sharp in blocky ones), then a longer segment. It is a standard part kind in `marks.py` (`make_snorkel`), chosen for about 30% of non-dot parts in any slot. Above and below it starts vertical and runs sideways; at the sides it starts horizontal and runs up or down. Direction (mirrored or flipped) and the length of the short segment vary, so snorkels in one script differ from each other. Its long version (+LONG) adds a tick back across the end of the long segment. It always touches the base letter.

## 19. Clarity rules from review of the sample scripts
1. **Diagonals only on simple shapes.** A slash, an X or a diagonal tail goes only on a one-stroke shape: a plain box or a curve that bends one way (a ring, C, arch, U). Never on an angular shape, an S, or a figure with several strokes. A figure that already has diagonals, or that is already wavy, takes no diagonal mark.
2. **One diagonal direction per sharp letter.** Mirrored sides count as one direction. A sharp or blocky letter with several different slants, or a curve made of many differently angled corners, is rejected (smooth curves are exempt).
3. **Implied structure lines.** A figure implies centre lines and lines through its corners. An extra bar or cross must sit exactly on one of those lines (a bar across the middle of a diamond), or keep clear of all of them. A bar that almost but not quite matches is rejected. Where three similar parallel strokes exist they are equal in length and evenly spaced, so the classic E (short middle bar) is replaced by the even comb.
4. **Marks must be visible.** A dot, or a diacritic part, keeps clear of every stroke of its letter (0.1 or more). A floating mark slides outward until clear; if there is no room, the sound gets its own letter. A dot in the middle of a shape needs 0.2 of clearance.
5. **No look-alikes through one kind of change.** Two letters made from one figure may not differ only by a bar at another height, or by two different diagonals. They need a different kind of change. Overlines are not used under a topline.
6. **Two changes at once** only on a plain figure (at most two strokes, boxes or one-way curves) and never with a diagonal.
7. **Joined corners stay joined.** A corner where another stroke starts or ends is not smoothed, so a stem on the tip of a diamond meets a sharp point.
8. **No ghost correspondence.** Letters may look different even when their sounds are alike, but letters whose sounds are unlike should not look alike more often than chance. The metric `ghost_ratio` compares the share of unlike-sound pairs among the closest-looking 15 percent of pairs with their share overall; it should stay at or below 1 (currently about 0.85). Two letters made from one figure must differ by at least 0.8 of the normal distance, so figures reused for related sounds are still clearly apart.
9. **Repeated parts are the same size.** Where a letter repeats a shape (two triangles, two bumps of a B), the copies have the same size and proportions. Closed or open parts of the same kind whose areas differ by less than about half are rejected; nested shapes of very different size (a ring in a ring) are fine. The B and stacked-triangle figures were redrawn with equal parts and the fish figure (a diamond with a smaller wedge) was removed.
10. **Bars at other heights sit on the figure's own lines.** A low or high bar goes exactly on a corner or end line of the figure that lies in that third of the letter; if there is none, the modifier does not apply. A middle bar or cross is skipped if it would almost but not quite match a line of the figure (this now includes through-lines).
11. **The last-resort random shape is rare.** Letters and digits first try every figure of the script's families at three levels of crowding; across 30 test scripts only 1 letter and 1 digit still fell back to a random shape.
12. **Baseline joins** attach at real contacts with the baseline, not at a point 0.1 above it, so no short drop stubs appear. A small polygon that another stroke joins is drawn fully sharp rather than part smooth, part sharp.
13. **Combs may sit anywhere on their line.** A set of parallel bars (an F, or an F with three bars, or a full comb) must have bars of equal length, evenly spaced. It need not fill the whole line: bunching them at the top or bottom of the spine is fine and is not an error. So F now has two equal bars, the old E with a shorter middle bar is gone, and `comb_top` (three equal bars at the top half of a spine) was added; its flip gives the bottom-bunched version. Rungs between two rails (ladder, H) are a different figure and are not subject to this.

## 20. Writing systems linked to languages

### 20.1 Model
- A **writing system** is stored as its recipe, never as drawings: `writing_systems(id, owner_id, conlang_id, name, seed, pins_json)`. The generator is deterministic, so letters are rebuilt on demand (cached in `script/service.py`).
- A system may be **designed for** a conlang (`conlang_id`). Its letters then cover exactly that language's consonants and vowels (`generate(seed, pins, phonemes)`), and it follows the language when the language's sounds change (settings apply, replace mode). The consonant and vowel count dials are set by the language and disabled in the editor. If the language is deleted the system stands alone.
- Each conlang has one **primary** system (`conlangs.primary_script_id`). `POST /api/conlangs/{id}/scripts/primary` returns it and makes it the first time it is asked for (seeded from the language's own seed). Only a system designed for the language can be its primary.

### 20.2 Writing a language in any system (closest fit)
`script/text.py` reads the language's own spelling back into sounds (longest spelling first, using the language's romanization, so complex consonants such as `ts` or `kp` stay one sound only when the language has them), then writes each sound with the script's letters. A sound the script lacks uses the closest one it has (`script/sounds.py`):
- Consonants: distance from place (0.55 per step), manner (a small table: stop-affricate-fricative, stop-nasal, lateral-trill, glides), voicing (0.8) and aspiration (0.3). Vowels: height and backness with a rounding penalty.
- A complex consonant the script lacks is written as its parts. A glide (j, w) may be written with the vowel it resembles (i, u). A glottal stop with nothing near it is left out.
- Abugida and abjad-with-signs: a consonant followed by a vowel is one syllable; a consonant with no vowel takes the virama; a vowel with no consonant uses a carrier letter (ʔ, else h, else the first consonant). A bare abjad leaves vowels out.
- The result lists every approximated sound (`approximations`) and a `coverage` count (exact sounds out of all), so a rendering in a non-matching script is shown as approximate, the way names are carried between human writing systems.

### 20.3 API
`GET/POST /api/scripts`, `GET/PUT/DELETE /api/scripts/{id}`, `POST /api/scripts/preview` (regenerate without saving; used by the editor on every dial change), `GET /api/conlangs/{id}/scripts`, `POST /api/conlangs/{id}/scripts/primary`, `PUT /api/conlangs/{id}/primary-script`, `POST /api/conlangs/{id}/render {text, script_id?}`. When a language is attached, `detail` and `preview` also return `sentences`: five fixed English sentences translated with the free restricted-English translator and written in the system. Permission `script.manage:own`; at most 60 systems per user.

### 20.4 Web UI
- Writing systems page: the list of saved systems; the editor has name, "Designed for", seed, Randomize, Lock all / Unlock all and every dial (lock = pin), with letters, sample text and the language's sentences redrawn after each change; Save, Make primary, Delete.
- Language page, new **Writing** tab: writes the language's sample sentences (or any pasted text) in the primary system; a chooser switches to any other system, with the list of approximated sounds. The Translate tab can show a translation in a writing system.
- The mobile app has the same screens (section 24).

## 21. Design by description (text)

- **Two new dials.** `stroke_bias` (balanced, vertical, horizontal, diagonal, round, vertical+diagonal, horizontal+vertical) re-orders each family's figures by how much of their ink is of the wanted kinds (`script/bias.py`: share of vertical, horizontal, diagonal and round ink within 18 degrees), so the script's characteristic shapes come from the best fits first. `mark_shape` (any, dots, circles, ticks, snorkels) decides what diacritics, vowel signs and the virama are made of (`make_part(shape=...)`). Both default to "no change" without drawing any random number, so scripts made before them are identical.
- **Reading a description.** `POST /api/scripts/interpret {text, use_model?}` returns `{proposals: [{key, value, evidence, source}], notes, usage}`. With a model (purpose `script.describe`, plan tokens) the reply is validated dial by dial (`script/describe.py`: unknown dials, out-of-range numbers and values not in the dial's list are dropped; the first proposal per dial wins; consonants, vowels and the two tolerances cannot be set). Without a model, or when its reply has nothing usable, a keyword reader covers the common phrases. Nothing is saved by the call.
- **UI.** A "Describe the look" card in the editor lists the proposals with their evidence and checkboxes; "Apply selected" pins them and redraws. The lock controls were renamed "Keep all settings" / "Release all" with a plain explanation (pinned dials are marked with a coloured edge).

## 22. Design by example picture

- **Where the work happens.** The project has no image library, so the browser does the measuring (`web/static/js/imagemeasure.js`): it shrinks the picture to at most 1024 pixels on a side, separates ink from background (Otsu threshold; light-on-dark is inverted), and measures (a) the share of ink by stroke direction in 12 steps of 15 degrees from a blurred-mask gradient, (b) ink coverage, (c) number of separate shapes and enclosed loops per shape, (d) the longest unbroken horizontal run along the bottom and top of the inked area. Only the shrunken JPEG and these numbers are uploaded.
- **Two readers, merged.** `POST /api/scripts/interpret-image {image: {media_type, data}, measures, use_model?}`. The measurements alone give proposals with no model (`describe.measure_proposals`): spread-out directions (normalised entropy of the off-axis directions >= 0.9) mean round; vertical and diagonal, horizontal and vertical (with the boxy family), mainly diagonal (with spikey) or mainly vertical or horizontal otherwise; a long bottom run means a joined baseline, a long top run a top bar; loops per shape sets the loops dial. With a model (purpose `script.describe_image`, vision) the picture and the numbers are shown to it once; its validated settings win and the measurements fill the dials it left alone.
- **Not copying.** The prompt asks only for style settings and forbids transcribing letters or naming a real script or font; the generator composes from its own shape library, so the result is "in the spirit of" the picture. The UI says so.
- **Privacy and cost.** The picture is never stored or logged (call previews keep only the text prompt). A picture is metered as about 1,500 tokens (`IMAGE_CHARS`) against the plan quota. Limits: PNG, JPEG or WebP, 2 MB after shrinking, magic bytes checked.
- **Model wrapper.** `Message` gained `images`; the Anthropic provider sends image blocks before the text.

## 23. Versions (checkpoints) of languages and writing systems

**Rule:** nothing is versioned automatically. A user presses *Create checkpoint* (optionally with a note); only then is anything stored. Editing, saving and regenerating never create a checkpoint.

**Model.** The language or writing system itself is always the *working version* and is the only thing that can be edited. A checkpoint is an immutable, read-only copy stored as the next number (v1, v2 ...); the working version is then shown as one higher (v2 after the first checkpoint). Before the first checkpoint the item shows "no checkpoints yet" and has no version number.

**Snapshot, not recipe.** The generators are deterministic only for one release of the code; rules change (several did while writing this section), so a recipe could redraw differently later. A checkpoint stores the result:
- language: the stored language JSON (spec, tables, lexicon, history) plus name, seed, vocabulary version. About 700 KB raw, ~77 KB compressed.
- writing system: the recipe (seed, pins, designed-for language, frozen sound inventory) plus the generated script. About 16 KB raw, ~3.5 KB compressed.

Snapshots are canonical JSON (sorted keys), lzma-compressed, base85 text in `versions.packed` (portable across SQLite and PostgreSQL). `digest` (sha256 of the canonical JSON) makes a checkpoint of an unchanged item a no-op error (409, "Nothing has changed since version N"). Limits: 50 checkpoints per item and 100 MB per user. Deleting an item deletes its checkpoints.

**Reading.** A checkpoint view is read only: a language shows name, seed, size, sounds, typology and word order; a writing system shows its sample text, sentences and letters drawn from the stored script (not regenerated). Both list what the working version has changed since (`changes_since`).

**New version from this one.** Creates a separate, editable item identical to the checkpoint (`branched_from` records origin). A language is inserted straight from the snapshot (no regeneration). A writing system is rebuilt from its recipe; if today's generator no longer draws the stored letters the API returns `exact: false` and the UI says so.

**API** (for `/api/conlangs/{cid}` and `/api/scripts/{sid}`): `GET|POST /versions`, `GET|DELETE /versions/{n}`, `POST /versions/{n}/branch`. Table: migration 6 (`versions`, plus `branched_from` on `conlangs` and `writing_systems`). Web: `js/versions.js`; a Versions tab on a language and a Versions section in the writing-system editor (saves pending edits first, since a checkpoint keeps the saved state).

**Not done:** the mobile app; full read-only browsing of an old language's dictionary and grammar book (use *New version from this one* to open it); restoring an old version over the working one.

## 25. Choosing letter shapes

Besides the generator's own choice of one characteristic figure per sound class (section on motifs), a writing system can pin the figure for a class. Five dials — `vowel_shape`, `plosive_shape`, `fricative_shape`, `nasal_shape`, `approximant_shape` — each take `auto` (default) or one of 32 plain names (ring, double ring, ring with cross, target, triangle, inverted triangle, diamond, X, trident, zigzag, V, W, M, N, Z, Y, K, box, double box, plus, comb, T, L, H, F, P, arc, S curve, curl, wave, arch, cup). Vocabulary: `script/forms.py` (name → family figure; checked when the module loads).

**Behaviour.** A pinned class uses its figure whatever the complexity or family (the figure is added to the script's figure table, so a "boxy" script can still have ring vowels). Affricates follow the plosive choice. Every letter of the class is still the figure plus one variant, so related sounds stay related. A pinned figure may be plainer than the style's stroke floor, and is retried at looser spacing before the generator falls back to another figure. Defaults draw no random numbers, so every script made before these dials existed is unchanged; the same seed and pins always give the same script.

**Limits.** A figure still has to suit the corner style: rings and curls need smooth or mixed corners; triangles and diamonds suit sharp or mixed; blocky (orthogonal-only) scripts can draw only boxy figures. When a pin could not be applied to at least half of its class, `script.shape_report` (`{group: {shape, letters, wearing}}`, present only when a shape is pinned) says so and the web editor shows a one-line hint.

**Describing it in words.** The keyword reader and the model prompt (`script/describe.py`) read phrases such as "vowels are rings", "triangular stops", "nasals made of waves", "consonants are boxes" (all four consonant classes). Words spent on a class's shape no longer also set the whole script's style (so "circular vowels" does not switch the family to bubbly). Model values are validated against the shape list like any other dial. The picture reader does not set shapes.

**Clients.** Both editors are catalogue-driven, so the dials appear under *Shape mix* automatically. The mobile editor (PR #42) needs no change beyond the dial catalogue; its hint for weakly applied shapes can be added after that PR merges.
## 24. Mobile app

The Expo app now matches the website for writing systems and versions: a **Writing** tab on each language (primary system by default, any other of the user's systems with the approximated sounds listed), the **writing area** under an English-to-language translation (Primary / None / others, remembered between translations, PNG and SVG download via the share sheet), a **Writing** top-level tab with the list and the editor (name, designed-for language, seed, Randomize, Keep all / Release all, every dial with a Keep box, redraw after each change, a sticky sample while the dials are changed, Save, Make primary, Delete), **Describe the look** (words, or a picture chosen from the photo library), and **Versions** (checkpoints) on both a language and a writing system.

Notes: the server's SVG is drawn with `react-native-svg`; a PNG is a screenshot of that view (`react-native-view-shot`). The picture is shrunk by `expo-image-manipulator`, decoded with `jpeg-js` and measured by `src/measure.ts`, a port of `imagemeasure.js` whose output is tested equal to the website's. A transparent PNG becomes JPEG with a dark background on some phones, which can misread the ink; photos and scans are fine. Not run on a device from the build sandbox (no npm registry there): type-checked, unit-tested, and its API calls exercised against the demo server.

## 26. The stroke family (kana-like letters)

Owner request (2026-10-21): letters that look like katakana or hiragana. The existing families draw every letter as one figure plus a small variant, built as one connected graph. Kana are the opposite: each letter is its own arrangement of one to four short strokes, and the strokes may be separate. So the stroke family is a new *letter maker* (`script/kana.py`), not a new table of figures.

- **Dials.** `family` / `family2` accept `stroke`; a new dial `stroke_hand` (`auto`, `angular`, `flowing`) picks the look. Angular is katakana-like: straight strokes, sharp corners, slashes, hooks and short ticks. Flowing is hiragana-like: curved strokes, hooks and small loops, drawn with rounded corners. `auto` draws the hand from the seed. Stroke is never chosen at random when no family is pinned, so every script made before it is unchanged.
- **Archetypes.** Each hand has 13-15 archetypes ("a bar crossed by a slash", "two slashes like a roof", "a stem with a branch", "a bar that drops and hooks", "a stroke that loops", "two curved bars on a stem"...), each with jittered positions, lengths and bends and an occasional mirror, so one archetype gives many letters.
- **Rules.** A letter fills its square (at least 0.78 high and 0.55 wide, relaxed when the alphabet is crowded), has at most three separate pieces, and every piece lies within 0.3 of another (it reads as one letter). Letters are distinct from each other by the usual distance check. Related sounds look related: each sound class owns three archetypes and draws 70% of its letters from them. Voicing-style relations use the existing marks (short ticks, like a dakuten).
- **Defaults when unpinned.** With `family: stroke`: no top bar, no joining, no ascenders or descenders, no mirror twins, marked letters 25%, marks made of ticks, corners sharp (angular) or smooth (flowing). Digits are stroke letters too.
- **Blend.** With `family2: stroke` (and another main family) the vowels and the approximants are drawn as stroke letters and the rest keep the main family's figures.
- **Describing it in words.** "like katakana" gives stroke + angular; "like hiragana" gives stroke + flowing; "kana" gives stroke.
- **Not done yet.** A syllabary mode (one glyph per consonant+vowel syllable), a paired angular + flowing script for one language (as katakana/hiragana), and varying stroke weight along a stroke (brush taper). With 13-15 archetypes per hand, alphabets over about 30 letters start to show family resemblances that are close to repeats.

## 27. Starting settings that resemble real writing systems (estimates)

Best-estimate dial values for a generated script that *feels* like each reference script. They are not tested for resemblance, except the two stroke-family looks, which were checked by eye on specimen sheets. The numbers come from the reference measurements in section 3 (the loops dial maps roughly to 8-87% of letters with a loop, so Georgian's 39% closed letters is about loops 0.4) plus the grammar notes. Dials not listed keep their random defaults. Topline and joining are "none" unless a row says otherwise.

**Where each reference came from.** Latin, Greek, Cyrillic, Armenian, Georgian and Hebrew: Unicode letters rendered from installed fonts only (section 2); no pictures were needed. Arabic, Devanagari, Bengali, Tamil, Thai, Ethiopic and Hangul: first measured from fonts, then revised after the owner's charts and text samples (section 12). Katakana and Hiragana were first set from the stroke-family design (section 26) and later measured against Noto Sans CJK and the owner's charts (section 28); Elvish was measured from an open-licence Tengwar font (end of section 28).

### Font / Unicode references (no pictures)
| Setting | Latin / Greek / Cyrillic | Armenian | Georgian | Hebrew |
|---|---|---|---|---|
| kind, direction | alphabet, ltr | alphabet, ltr | alphabet, ltr | abjad, rtl |
| consonants / vowels | 18-22 / 5-7 | 29 / 7 | 28 / 5 | 22 / 0 |
| family, family2 | classic, none | curvy, bubbly | bubbly, curvy | boxy, none |
| corner_style, roundness | mixed, 1.0 | smooth, 1.0 | smooth, 1.0 | blocky, 0.2 |
| complexity, width | 0.8, 0.75 | 0.45, 0.7 | 0.5, 0.7 | 0.75, 0.7 |
| density, loops | 0.35, 0.3 | 0.4, 0.3 | 0.4, 0.4 | 0.3, 0.0 |
| stroke_bias | vertical+diagonal | vertical | round | horizontal+vertical |
| ascender, descender | 0.2, 0.15 | 0.2, 0.3 | 0.25, 0.4 | 0.1, 0.2 |
| mirror_share | 0.25 | 0.1 | 0.05 | 0.1 |
| mark_share, mark_shape | 0.15, dots | 0, any | 0, any | 0.3, dots |
| motif_count, motif_share | 5, 0.5 | 5, 0.5 | 5, 0.5 | 4, 0.6 |
| min_distance, frame_tolerance | 0.3, 0.2 | 0.25, 0.25 | 0.3, 0.25 | 0.3, 0.2 |
| word_separator | space | space | space | space |

### Charts and text samples from the owner (plus fonts)
| Setting | Ethiopic | Arabic | Devanagari | Bengali |
|---|---|---|---|---|
| kind, direction | abugida, ltr | abjad, rtl | abugida, ltr | abugida, ltr |
| consonants / vowels | 30 / 7 | 28 / 0 | 34 / 10 | 34 / 10 |
| family, family2 | bubbly, boxy | curvy, none | boxy, curvy | curvy, boxy |
| corner_style, roundness | mixed, 0.8 | smooth, 1.0 | mixed, 0.8 | smooth, 1.0 |
| complexity, width | 0.6, 0.8 | 0.6, 0.7 | 0.3, 0.75 | 0.35, 0.75 |
| density, loops | 0.5, 0.5 | 0.3, 0.2 | 0.7, 0.3 | 0.6, 0.4 |
| stroke_bias | balanced | horizontal | vertical | vertical |
| ascender, descender | 0.03, 0.05 | 0.1, 0.4 | 0, 0.1 | 0, 0 |
| topline, joining | none, none | none, partial | bar, none | bar, none |
| mirror_share | 0.05 | 0.1 | 0 | 0 |
| mark_share, mark_shape | 0, ticks | 0.4, dots | 0, dots | 0, dots |
| motif_count, motif_share | 6, 0.85 | 4, 0.8 | 5, 0.6 | 5, 0.6 |
| min_distance, frame_tolerance | 0.25, 0.3 | 0.22, 0.2 | 0.25, 0.2 | 0.25, 0.2 |
| word_separator, sign_frames | dot, 0.1 | space, n/a | space, 0.5 | space, 0.7 |

### Owner charts (Tamil, Thai, Hangul) and the two stroke-family looks
| Setting | Tamil | Thai | Hangul | Katakana-like | Hiragana-like |
|---|---|---|---|---|---|
| kind, direction | abugida, ltr | abugida, ltr | alphabet, ltr | alphabet, ltr | alphabet, ltr |
| consonants / vowels | 18 / 12 | 34 / 12 | 19 / 10 | 22 / 5 | 22 / 5 |
| family, family2 | bubbly, curvy | bubbly, curvy | boxy, bubbly | stroke (angular), none | stroke (flowing), none |
| corner_style, roundness | smooth, 1.0 | smooth, 1.0 | mixed, 0.3 | sharp, 0 | smooth, 1.0 |
| complexity, width | 0.4, 0.8 | 0.45, 0.7 | 0.8, 0.8 | 0.75, 0.9 | 0.5, 0.9 |
| density, loops | 0.5, 0.87 | 0.35, 1.0 | 0.2, 0.25 | n/a | n/a |
| stroke_bias | round | round | horizontal+vertical | n/a | n/a |
| ascender, descender | 0.05, 0.4 | 0.15, 0.1 | 0, 0 | 0, 0 | 0, 0 |
| mirror_share | 0 | 0 | 0.3 | 0 | 0 |
| mark_share, mark_shape | 0, dots | 0, ticks | 0.3, ticks | 0.3, ticks | 0.3, ticks |
| motif_count, motif_share | 5, 0.8 | 5, 0.8 | 4, 0.9 | n/a | n/a |
| min_distance, frame_tolerance | 0.25, 0.25 | 0.25, 0.25 | 0.25, 0.2 | 0.25, n/a | 0.25, n/a |
| word_separator, sign_frames | space, 0.6 | none, 0.7 | space, n/a | none, n/a | none, n/a |

**Known mismatches.** Katakana, hiragana: no syllable-per-glyph mode yet. Hangul: no block (syllable cell) layout, so jamo come out in a line. Ethiopic: vowel orders are signs beside the base, not changes to it. Arabic: joined forms use simple stubs, not real positional shapes. Hebrew: no final forms. Thai: the dial caps at 34 consonants (real Thai has 44).

**In the app: "Create like...".** The tables above are served as presets (`script/presets.py`, in the `presets` list of `GET /api/script/dials`) and offered as a drop-down in the *Create a writing system* panel on the website and in the app: Latin/Greek/Cyrillic, Armenian, Georgian, Hebrew, Arabic, Devanagari, Bengali, Tamil, Thai, Ethiopic, Hangul, Katakana, Hiragana. A preset is a set of pinned dials, so the seed still chooses everything else. Order of say: settings the person chose in the panel, then the preset, then anything read from a description or picture. When the script is designed for a language, the preset's sound counts are dropped (the language decides). `tests/test_script_presets.py` checks that every preset's pins are valid and kept, and that scripts can be made from them. Nothing is copied from the real script, only its structure and style.

## 28. Calibrating the generator against the real scripts (harness and first results)

**Harness.** `scripts/script_analysis/compare.py` generates several scripts per "Create like..." preset, draws their letters the way `render.py` draws font glyphs (same letter height and stroke thickness as the real script; crisp flat-ended strokes for angular styles, round strokes for smooth ones; drawn at 4x and shrunk so outlines are smooth), runs the same `measure.py` and `topology.py` measurements, and compares means with the real script's numbers (`measurements.json`, `topology.json`, now including Hiragana and Katakana from Noto Sans CJK JP). 19 scale-free metrics (aspect, closed share, ends, junctions, strokes, orientation shares, angularity, pieces, marks, top and base bars, descenders, left-right symmetry, topology classes, loop shares) each have a tolerance; a metric outside it is "off". `python compare.py run` then `report`; results in `comparison.json`. Real glyphs are only measured.

**Lessons about the measurement itself.** (1) A jagged bitmap of a generated letter makes the skeleton tool invent strokes and junctions: Georgian went from 7 metrics off to 2 once the letters were drawn smoothly. (2) Angular scripts need crisp corners and flat ends in the bitmap: Katakana junction and end counts matched only after that. Compare like with like or the numbers mislead.

**Generator changes (now the defaults for every script; the hidden `preset` dial that once gated them was removed, because scripts made earlier are allowed to change).** `ascender_share` and `descender_share` become rates (the first letters may rise or drop, later ones only while the running share is below the dial); `loops` prefers or avoids figures that hold a loop when ordering figures; letters are drawn about 25% wider (0.9-1.05 of the width dial); with the stroke family, archetypes with more strokes are preferred at low complexity. The stroke family also gained more archetypes (crossings and loops: ホ テ チ モ ネ, あ な き ふ む), small detached ticks and short crossing strokes, and a closing-loop fix so loops really enclose a counter.

**Results (6 seeds per preset; metrics off out of 19; first run 122 off in total, now 82 of 247).**
| Preset | Off | Largest remaining gaps (real -> generated) |
|---|---|---|
| Georgian | 2 | base-bar share 0.55 -> 0.25 |
| Katakana | 0 (after the kana retune below) | none |
| Armenian | 4 | closed letters 0.32 -> 0.46 |
| Tamil | 5 | angularity 0.75 -> 0.40; symmetry 0.43 -> 0.78 |
| Thai | 5 | angularity 0.72 -> 0.39; symmetry 0.36 -> 0.61 |
| Hiragana | 3 (after the kana retune below) | junctions 3.5 -> 2.1; ends 6.1 -> 4.6; deg-3 share 0.63 -> 0.81 |
| Ethiopic | 7 | diagonal share 0.41 -> 0.20; descending 0.05 -> 0.34 |
| Hebrew | 7 | horizontal share 0.25 -> 0.44; diagonal 0.22 -> 0.06 |
| Hangul | 7 | ends 4.5 -> 2.0; closed 0.28 -> 0.60; pieces 1.6 -> 1.0 |
| Arabic | 8 | letters with detached marks 0.61 -> 0.21; closed 0.25 -> 0.00 |
| Latin/Greek/Cyrillic | 9 | diagonal 0.34 -> 0.52; top bars 0.32 -> 0.08; topology classes 0.27 -> 0.49 |
| Devanagari | 9 | descending 0.13 -> 0.51; diagonal 0.24 -> 0.06 |
| Bengali | 11 | top bars 0.48 -> 1.00 (all or none); aspect |

Small changes to one dial often broke other numbers (with 6 seeds there is noise too), so a second round of preset tweaks was kept only where it helped (Tamil, Ethiopic, Armenian, Thai) and reverted elsewhere.

**What the settings cannot fix: capabilities to add** (the aim is a precise visual design tool, so these are the next generator features):
1. **Partial top bar** (`topline: partial`, a share of letters): Bengali, and Devanagari's few barless letters.
2. **Rate control for marks**: Arabic's 61% dotted letters (our marks are limited to voicing-style pairs) and kana voicing ticks; a `mark_rate` that creates base+mark families on any letters.
3. **Topology variety control**: real scripts reuse a few body shapes much more than the generator does (Hebrew 0.15 vs 0.48 classes per letter); a dial for how many distinct bodies a script uses.
4. **Flat base and flat top control** (share of letters sitting on a bar), and a **symmetry** dial (round scripts come out too symmetric).
5. **Diagonal control**: Hebrew, Ethiopic and Latin differ in diagonal share; stroke_bias moves it but unevenly. A per-family diagonal weight is needed.
6. **Terminals and stroke weight**: flat versus round ends, tapered brush ends, thick-thin contrast; angularity differences (Tamil, Thai) are mostly terminals.
7. **Richer kana archetypes**: real hiragana pen strokes are longer and cross more (3.5 junctions per letter); a second set of archetypes drawn from measured stroke paths, and photographs of handwriting, would help.
8. **Layouts**: syllabary (one glyph per syllable), Hangul-style blocks, true Ethiopic orders, joined positional forms.

### Kana charts from the owner (Katakana x2, Hiragana x1) compared with the font numbers

`scripts/script_analysis/chart_glyphs.py` cuts a chart image into single letters (near-black ink, a small dilation to join the pieces of a letter, romaji and titles dropped by colour and size) and `chart_measure.py` measures them with the same code as the font glyphs (`chart_measurements.json`). Letters are scaled to the font's letter height, so ratios compare directly.

| | letters | stroke width (em) | closed | ends | junctions | strokes | parts | marks | diag |
|---|---|---|---|---|---|---|---|---|---|
| Katakana, thin gothic chart (basic 46) | 46 | 0.03 | 0.02 | 3.5 | 1.2 | 3.2 | 1.04 | 0.02 | 0.38 |
| Katakana, mincho/brush poster (basic 46) | 45 | 0.05 | 0.02 | 6.4 | 3.1 | 4.1 | 1.44 | 0.11 | 0.44 |
| Katakana, Noto Sans CJK (71 incl. voiced) | 71 | 0.08 | 0.06 | 5.5 | 2.5 | 3.5 | 1.99 | 0.34 | 0.38 |
| Hiragana, rounded sans chart (71 incl. voiced) | 71 | 0.05 | 0.32 | 5.9 | 3.4 | 5.3 | 2.18 | 0.42 | 0.43 |
| Hiragana, Noto Sans CJK | 71 | 0.08 | 0.32 | 6.1 | 3.5 | 4.8 | 2.14 | 0.41 | 0.40 |
| Hiragana, monoline pen sticker (basic 46) | 46 | 0.06 | 0.35 | 4.9 | 2.7 | 4.9 | 1.41 | 0.15 | 0.45 |
| Hiragana, picture chart (26 of the 46; small, noisy) | 26 | 0.05 | 0.38 | 6.3 | 5.0 | 6.6 | 1.81 | 0.42 | 0.40 |
| Hiragana, bold brush lettering (pieces split; weight only) | 55 | 0.18 | 0.29 | 4.3 | 2.5 | 4.8 | 1.27 | 0.09 | 0.39 |

What this says:
- **Hiragana**: the chart agrees with the font on every metric (closed 0.32, strokes about 5, junctions about 3.5, parts about 2.2), so the font numbers are a good target and the hiragana preset's shortfalls (junctions 1.1, ends 4.1, closed 0.15, strokes 2.8) are real generator gaps.
- **Katakana**: the font numbers for marks and parts (0.34, 1.99) come from the 25 voiced letters (two voicing ticks). The basic 46 are nearly always one piece (parts 1.0 to 1.4, marks 0.02 to 0.11). The katakana preset should therefore make a voicing mark on about a third of letters as a separate "voiced" family, not a tick on a fifth of base letters; the base shapes should be single pieces.
- **Stroke weight varies by typeface** (0.03 thin gothic, 0.05 poster/rounded, 0.08 Noto), which is a dial, not a property of the script; the mincho/brush poster also has tapered, thick-thin strokes (the terminals and contrast capability, item 6 above).
- Not in the generator yet: small kana (ャ ュ ョ ッ) and digraph pairs (キャ), and the long-vowel mark ー.

More hiragana charts (the stray "Katakana" chart in that batch was the same thin gothic katakana image as above and was ignored a second time):
- The basic 46 (no voicing marks) are mostly one or two pieces (1.4), with marks on 0.15 of letters (the sticker); the 0.41 marks in the font numbers again come from the 25 voiced letters. Closed shapes (0.32 to 0.38), strokes (about 5) and junctions (2.7 to 3.5) agree across typefaces, so those are the stable hiragana targets.
- The small picture chart's junctions (5.0) are inflated by tiny, noisy bitmaps (38 px letters); not used as a target.
- The bold brush lettering has stroke width 0.18 em (twice the heaviest font) and merges strokes into blobs, so a brush look needs a stroke-weight dial up to about 0.2 em, tapered ends and blob joins; its pieces split under the cutter, so only its weight was used.
- The two charts with kanji beside the kana (wi/we columns) and the ruled table were not measured (kanji and table lines would need to be removed first); they confirm the obsolete letters ゐ ゑ exist but are not needed.

### Kana retune (second round)

Changes made after the chart measurements (all defaults now; earlier scripts change):
- **Voicing marks in kana scripts**: the "voiced" feature is always the first marked feature and is drawn as two short ticks (dakuten) above the letter; every other marked feature shares a small ring (handakuten). They replace the generic random marks, which also removes marks that fell below the baseline.
- **Base letters**: small detached ticks are rarer for the angular hand (0.1 instead of 0.4), so basic katakana are mostly one piece; crossings 0.25 (angular) and 0.6 (flowing).
- **Joined strokes** (`kana.JOIN`): one or two strokes are drawn on to a neighbouring stroke, making T-junctions as in real kana (0.1 angular, 0.6 flowing).
- **Seven denser hiragana archetypes** (ほ ぬ ね さ た ち せ) and a loop weight: the `loops` dial raises or lowers the share of archetypes that hold a closed loop.
- The Hiragana preset now has `complexity` 0.2 and `loops` 0.6.

Result (6 seeds, 19 metrics): Katakana 0 off; Hiragana 3 off (junctions 3.5 -> 2.1, ends 6.1 -> 4.6, T-junction share 0.63 -> 0.81: real hiragana cross strokes more than ours). The other presets did not regress when the preset gating was removed (Latin 9, Armenian 4, Georgian 2, Hebrew 7, Arabic 8, Devanagari 9, Bengali 11, Tamil 5, Thai 5, Ethiopic 7, Hangul 7; 77 in total against 82 before).
Still missing for kana: small kana and digraph pairs, the long-vowel mark, a stroke-weight dial (0.03 to 0.2 em) and tapered/brush terminals, and more crossing hiragana shapes.

### Elvish ("Looks like: Elvish")

**Reference.** Tolkien's Tengwar is not in Unicode (only in private-use mappings). It was measured from the open-licence font Alcarin Tengwar (SIL OFL 1.1, fetched by `scripts/script_analysis/fetch_fonts.sh`, not committed): 47 letters of the main set, U+E000 to U+E02F in the private-use mapping. Nothing is copied: only the structure and statistics are used, and in the app the style is called "Elvish", with no Tengwar names, letters or glyphs.

**What the letters are made of.** A vertical stem carrying one or two round bows (on the right or the left), the stem reaching below the line (the tinco and parma kinds), above it (the raised kinds) or neither; some bows are open at the stem. A few letters are curls, rings, hooks and lambdas. Vowels are marks above the consonant letters. Measured: height 0.72 em (letters hang above and below the baseline; 51% drop below it), aspect 0.84, closed shapes 0.38, strokes 4.5 (the font's flared terminals add branches), all letters one piece, no detached marks.

**Generator.** A third stroke hand, `stroke_hand: bowed`, in `kana.py` (14 archetypes: single, double, left, left-double, raised, raised-double, raised-left, short and tall stems with bows; ring, hook, curl, lambda, arch). Bows are open about 70% of the time and about as wide as the stem is long below them. The hand has fixed archetype weights, no detached ticks, crossings or joins, no mirror twins and no voicing marks; abugida vowel signs are forced into the "above" slot. The preset `elvish` is `kind abugida`, 24 consonants, 5 vowels, smooth corners, roundness 1, complexity 0.5, width 1.0, mark shape any. The description reader maps "Elvish" and "stems with round bows" to it.

**Harness.** The harness now scales generated letters by their own median height (letters that reach above or below the x-height are scaled down to the real letter height instead of looking 1.4 times too tall). Result: 5 of 19 metrics off: ends 3.7 -> 1.9, junctions 2.8 -> 1.0 and strokes 4.5 -> 2.4 (the font's flared stroke ends add skeleton branches; matching them needs a "terminals" capability), diagonal share 0.38 -> 0.27 and flat-base share 0.28 -> 0.09.

### Shared stroke features (any family where they make sense)

Rules that were first built for one stroke hand are now dials that any script can use:
- `mark_shape: voicing` (any family, alphabet or abjad): the "voiced" feature is drawn as two short ticks above the letter and the next feature as a small ring (the kana way); other marks are ticks. The stroke family's kana hands set it by default; the Katakana and Hiragana presets pin it. The words "dakuten", "voicing marks" or "two ticks above" set it from a description. The tick style follows the stroke hand, or the corner style when there is none.
- `vowel_sign_slot` (mixed, above, below, right, left; any abugida): where vowel signs sit. Mixed is the old behaviour; the bowed (Elvish) hand defaults to above.
- `stroke_ticks`, `stroke_crossings`, `stroke_joins` (0 to 1): how often a stroke letter gets a detached tick, a crossing stroke or a joined stroke. Each hand sets its own defaults (the old per-hand constants), they apply to all three hands (a bowed script can now have ticks) and in a stroke blend (second style), and a pinned value wins.

Still tied to the stroke family by design: the archetype shape libraries (angular, flowing, bowed), because each archetype is a whole letter, not a figure the other families combine with variants. In a blend only the vowels and approximants use them. The kana defaults that switch off the top bar, joining, ascenders/descenders and mirror twins apply only when the stroke family is the main style and only unless pinned, so any of them can be set on a stroke script. (Bowed letters take their stems above and below the line from the shapes themselves, so the descender share does not change them.)

### Stroke share (stroke letters in any script)

`stroke_share` (0 to 1) is the share of letters drawn as stroke letters in the script's stroke hand. A pure stroke script is 1.0 (set automatically); a script with the stroke family as its second style defaults to 0.35 (about the vowels and approximants, as before); and any other script may ask for some (for example a Latin-like script with a quarter of its letters bowed). Letters are taken sound class by sound class (vowels, approximants, nasals, fricatives, stops, then affricates), a partly used class at random; a class whose shape the user chose stays as chosen, and derived letters copy their parent, so the share is approximate. The stroke hand, ticks, crossings and joins dials apply to those letters. With share 0 and no stroke family nothing changes.

## 29. The pen hand (Devanagari-, Bengali- and Tamil-like letters)

**Problem.** The Devanagari, Bengali and Tamil presets were built from the figure families (a base shape plus a small variant), so each letter read as one geometric shape with parts attached, not as the path a pen draws. Those scripts are a few strokes in which each begins from, or lands on, another.

**The hand.** A fourth stroke hand, `stroke_hand: pen` (`pen.py`, hooked in through `kana.py`, so it keeps `stroke_share`, marks, vowel signs, digits and the compare harness). A `Pen` draws strokes one after another with these moves: `begin` (free, at the end of the previous stroke, or at the middle of an earlier stroke leaving at a right angle), `line`, `turn` (a corner), `arc` (a curve that carries on in the direction the pen was going), `to` (end exactly on another stroke) and `at(stroke, t)` (a point a fraction t along an earlier stroke, with its heading). Attachment is therefore anywhere: a short connector off the middle of a stem, the end of one stroke becoming the start of the next, or an arm that lands on the middle of the stroke beside it.

**Frames** (`pen_frame`: auto, stem, free):
- *stem* (Devanagari, Bengali): a long vertical stroke from the top bar. Recipes: arm that curls into a bowl, two arms, foot hook with a bar, two stems joined by a bar that lands on the second, arm with a loop, slanted arm and acute turn, bowl hung on the stem, arm with a tick, ring on an arm, a fork into two slanting arms, and a slanting stroke across the stem. About 45% get a second feature (flick at the head, small arm on the right, tick at the foot) and about 40% a tick or hook anywhere.
- *free* (Tamil): no stem. Recipes: loop with a tail, S-curve, ring with a stroke at a right angle, hook with a bar, double loop, angle (ட), cup with a stroke from its foot, arch into a stem, spiral. Every letter without a loop gets a ring beside it 90% of the time, 70% get one more tick, hook or ring, the letter is stretched to fill the box and 45% hang below the baseline.
- auto: stem when the script has a top bar, otherwise a random choice.

**Style.** The existing `corner_style` sets how the parts are drawn: smooth is arcs and round bowls (Devanagari), sharp is straight legs meeting at angles, with the arcs replaced by acute points (Bengali), mixed gives each stroke one or the other (Tamil). Loops and rings (a turn of 240 degrees or more) are always drawn round, even in a sharp stroke. The `loops` dial raises the share of recipes that hold a ring or loop. Recipes that close a hole (two stems with a bar, a bowl on the stem) are liked less (`LIKE` in `pen.py`) because about a third of real Devanagari letters hold a hole.

**Presets.** Devanagari: stem, smooth, `loops` 0.1. Bengali: stem, sharp, `width` 0.85, `loops` 0.6. Tamil: free, mixed, `roundness` 0.2, `loops` 1.0.

**Result** (8 seeds, 19 metrics; before: 9, 11 and 5 off with the figure families): Devanagari 2 off (width/height ratio 0.95 -> 1.11, top-bar share 0.85 -> 1.00), Bengali 4 off (top bar 0.48 -> 1.00, diagonal 0.33 -> 0.19, horizontal 0.31 -> 0.42, closed share 0.39 -> 0.26), Tamil 7 off (top bar 0.34 -> 0.01, angular 0.75 -> 0.51, diagonal 0.28 -> 0.45, width/height ratio 1.24 -> 1.02, closed share 0.77 -> 0.62). Tamil is measurably less like the real script than the old preset on a few metrics (junctions and stroke count are better, diagonals worse); it looks much more like a pen script.

**Still missing.** A partial top bar (Bengali and Tamil have it on only about half of the letters; ours is on all or none), a wider letter than the width dial allows (Tamil), pen width and brush terminals (deliberately left for a later rendering phase), conjunct and vowel-sign forms drawn as pen strokes (the signs are still the old dots, ticks and snorkels), and richer recipes (more of the real letters' hooks, double bowls and flags). Bengali needs more diagonal and closed letters; Tamil fewer diagonals and more corners.

Pen tests: `tests/test_pen.py`.
