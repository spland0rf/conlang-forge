# Bengali model (fresh slate)

Everything here is measured from the 44 hand-fitted letters in `conlang_forge/script/forms/bengali_graph.json` and nothing else.
It does not read the shared generator config, the Devanagari rules or any Devanagari data.

`measure_model.py` writes `bengali_model.json`: per-letter skeleton records, per-stroke records (length, turn, start/end heading, ends),
per-junction records (type, which ends meet, angle between the two strokes) and a `summary` of distributions.

Headings are degrees with y up (0 = east, -90 = straight down).
Planned next: a Bengali-only generator that samples from these records (skeleton class, stroke shapes, junction types and angles).
