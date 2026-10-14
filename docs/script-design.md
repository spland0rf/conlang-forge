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
