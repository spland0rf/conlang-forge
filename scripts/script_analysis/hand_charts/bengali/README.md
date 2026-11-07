# Bengali hand-drawn stroke chart: tracing (second pass, from the close-up photos)

The sheet (6 columns, 44 letters a..ha) uses the same markup as the Devanagari one: purple bar, blue/green body, orange accents, red dots between forms,
orange rings = touch, orange crosses = cross. For Bengali, blue and green are NOT different kinds of form: they only break a complex body stroke into sequences.
The user swapped two pairs of drawings between cells (two-headed arrows): ṭa<->ṭha and va<->śa (`SWAPS` in `grid.py`).
The thick blobs at stroke ends are ball terminals (recorded as an end style, `ends` in the graph).

Photos: `photo_top.jpg` (rows a..ḍa) and `photo_bottom.jpg` (rows ḍha..ha); `photo_first_pass.jpg` is the first full-page photo (less sharp, kept for reference).
Run from a folder holding the two close-ups (copy them as `top.jpg` and `bot.jpg`, or edit the names in `run2.py`):

1. `python3 run2.py`: rescales each photo to the cell size the thresholds are tuned for, classifies ink in Lab colour relative to the local paper (hysteresis for faint strokes),
   skeletonises each colour into strokes, joins short gaps, snaps ends to red dots, finds ball terminals and rings, applies the swaps: `raw2.json`, `cells_sw.json`.
2. `python3 build_graph.py raw2.json draft2.json`: 100x100 box (scale 0.46: bar y 26 for headroom, stem bottoms about 85), strokes as paths, junctions from the red dots and orange marks
   (touch/cross decided by geometry), ball ends, hand corrections from the user's review.
3. `python3 review.py draft2.json sheet.png a ā i ...`: photo next to the traced graph, for checking.

Status: shapes follow the drawings; junction types and a few ring/cross marks still need the user's confirmation before this becomes `bengali_graph.json`.
