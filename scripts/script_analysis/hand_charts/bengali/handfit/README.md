# Bengali hand-fit toolkit

The 39 letters in `bengali_graph.json` (all except ṅa, pa, va, śa, ha) were fitted by
hand from zoomed photos of the hand-drawn stroke-graph sheet.

* `gv.py`    - draws a pixel-labelled grid over a crop of a photo so stroke points can be read off.
* `s_*.py`   - one SPEC per letter: per-cell (x0, y0, cw), strokes as pixel polylines
               (options `V` vertical, `H` flat bar, `ball` start/end/both) and junctions.
* `hf.py`    - converts pixels to the 100x100 frame (`conv`), builds the letter dict, draws overlays.
* `sheet.py` - overlays specs on the photo to check the fit.

Photos are not committed; they live in the Project/session attachments.
