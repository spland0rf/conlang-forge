# Bengali hand-drawn stroke chart: tracing (first pass)

`page1.jpg` is the user's hand-drawn sheet (6 columns, 44 letters a..ha; same markup as the Devanagari sheet: purple bar, blue/green body, orange accents,
red dots between forms, orange rings = touch, orange crosses = cross). The user swapped two pairs of drawings between cells (two-headed arrows): ṭa<->ṭha and va<->śa (`SWAPS` in `grid.py`).
For Bengali, blue and green are NOT different kinds of form: they only break a complex body stroke into sequences.

Run from a folder holding `page1.jpg` saved as `page.jpg` (the scripts read it from the working directory):

1. `python3 -c "import cv2,numpy as np; from grid import *; np.savez_compressed('masks_soft.npz', **soft_masks(cv2.imread('page.jpg')))"`: ink classes in Lab colour relative to the local paper, with hysteresis for faint strokes.
2. `python3 extract.py`: skeletonise each colour, split into strokes, join short gaps, snap ends to red dots: `raw.json` (cell pixel coordinates).
3. `python3 build_graph.py raw.json draft.json`: 100x100 box (scale 0.5: bar y 20, stem bottoms about 83), strokes as paths, junctions from the red dots and orange marks (touch/cross decided by geometry).
4. `python3 review.py draft.json sheet.png a ā i ...`: photo next to the traced graph, for checking.

Status: shapes are mostly right, but the last stretch of strokes near ball terminals and red dots is often lost, so letters need hand correction before they become `bengali_graph.json`.
