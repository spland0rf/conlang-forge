# Devanagari stroke model + generator: handoff (2 Nov 2026)

## Pages (in your Claude account)
- Stroke table: https://claude.ai/artifact/8ydYfX5X3shTBBDwspPJgg
- Stroke geometry (per-letter drawings, descriptions, junction graph): https://claude.ai/artifact/3eVJMrFyfFBrPpXoWXUgCn
- Generated Devanagari-like script (generator v2): https://claude.ai/artifact/T9Cr4yTTVgyV2a3vEc9Vzz

## Folders
- `model/`: Devanagari stroke graph (Checkpoint v1.1 plus shape tags). See `model/README.md` for colors, junction rules and the coordinate system. Rebuild: `python3 build.py && python3 graph.py && python3 semantic.py && python3 render.py`
- `generator/`: generator v2. `gen2.js` holds the five configs, body builders, mutation and similarity code. `build_page.py` assembles `generator.html` with `real_pts.json`.

## Conventions agreed
- **Colors:** blue = main body, green = second fused form, purple = headline / short descenders / connectors, orange = accents.
- **Orange means a grammatical function:** vowel signs ā (आ ओ औ) and e/ai (ऐ ओ औ), and length marks (ई ऊ ॠ ॡ). Marks that only distinguish consonants stay green (फ tail, ब/ष diagonals, छ curl). The bar running over the ā sign is purple.
- **Junctions:** red dot = between forms or with the headline; orange ○ = touch within one form (including corners); orange × = crossing within one form.
- **Accent rules:** four accent types (1L, 2L, 1R, 2R; 2R for generated scripts only). At most one accent per letter, always on the right-most point where a line meets the bar from below.
- **Novelty:** generated letters may not copy a real letter (recipe match or near-identical shape). Adding or removing the top bar, or the full-height stem, counts as a new letter. Letters sharing a frame need a larger shape distance (3.0 vs 2.2). Similar variants are drawn to exaggerate their differences.

## Next steps
1. Stroke-sequence diagrams (black/red) → build a set of body building blocks and rules for combining them.
2. A sheet of क + each vowel sign and diacritic → real accent anchor points around the letter.
3. Push similar generated letters apart along their distinguishing feature (instead of rejecting one).
4. New scripts: Bengali → (Gurmukhi) → Tamil → Amharic/Ge'ez.

## Reference photos
`reference_photos/` has every photo uploaded in this chat: the full colored sheets (first to latest markup) and the close-ups the geometry was traced from.
