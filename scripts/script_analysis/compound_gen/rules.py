"""The hard rules of Devanagari-like letter generation, in ONE place. Everything in RULES is fixed input: the generators build to it (where they
can) and the validator enforces it (always); neither may change it. Only what is not listed here is left to randomness.
Each entry says where it came from (the user's review, 2026-11-03)."""
from types import MappingProxyType

RULES = MappingProxyType({
    # frame
    "BAR_Y": 20.0, "BASE_Y": 88.0, "BAR_GAP": 7.0,            # headline height, baseline, clear gap under the bar
    "DESC_Y": 36.0,                                           # every short purple descender has this height
    # orientation (degrees)
    "START_AXIS_TOL": 12.0,                                   # strokes start along an axis (down / left / right)
    "CUP_OPEN_TOL": 14.0, "CUP_MIN_TURN": 100.0,              # big open curves open up / down / left / right
    "THREE_STACK_TOL": 14.0, "S_UPRIGHT_TOL": 30.0,           # a '3' stacks along an axis; an S stands upright
    "LINE_AXIS_TOL": 4.0, "LINE_MIN_LEN": 8.0,                # straight lines are exactly vertical / horizontal
    "VERT_FULL_BOTTOM": 84.0, "VERT_MIN_LEN": 12.0,           # vertical bars run to the baseline (no intermediate heights)
    "SLIGHT_TURN": 45.0, "SLIGHT_MIN_LEN": 14.0, "SLIGHT_VERT_TOL": 40.0,   # no slight curves hanging down
    "RELAXED_TOL": 45.0,                                      # a stroke attached at both ends may sit near 45 degrees
    # size / shape
    "MAX_TURN": 300.0, "MAX_SPAN": 45.0, "RING_FRAC": 0.25, "RING_MIN_LEN": 70.0,    # no giant loops, no ring closed on itself
    "MIN_STROKE_LEN": 18.0, "MAX_STROKE_LEN": 150.0, "MIN_SELF_GAP": 7.0, "MIN_STROKE_CLEAR": 5.0, "JOINT_ZONE": 9.0,
    # joins
    "JOIN_AT_END_P": 0.8, "SHORT_FIRST_LEN": 35.0,            # a second stroke meets the first at its end (always if the first is short)
    # bar
    "BAR_MIN_WIDTH": 56.0, "BAR_OVERHANG": 8.0, "BAR_CENTER_LO": 0.30, "BAR_CENTER_HI": 0.70, "ANCHOR_LO": 0.15, "ANCHOR_HI": 0.90,
    # distinctness
    "FAMILY_TURN": 100.0, "INK_MIN_DIST": 8.0,
    # two letters whose shapes are the same except for a small slide of an attachment point along a stroke are one letter
    "WHITE_MAX": 0.50, "WHITE_TARGET": 0.40, "PRIMARY_MIN": 0.40, "MAX_VOID": 47.0, "HALF_INK_MIN_DIST": 6.5,   # radius of the largest empty circle (stem/descender letters): original A1/A4/A7 were 48-52; the user redraws measure A1 46, A7 43, others <= 32
      # the main body stroke must be big enough to read (user: A1 sideways stroke wider, A7 quarter-circle ~half the character)
    "WHITE_R": 10.0,   # share of the letter frame farther than WHITE_R from any ink (original A1/A4/A7: 0.49-0.54; approved originals: <= 0.44)    # hypot(drop below bar / letter height, body width / bar width): bodies need room (A1, A4, A7, A12, A3 redraws)
    "ATTACH_SLIDE_TOL": 0.25,   # fraction of the stroke length (user review 1: A28 vs real a)
})
R = RULES
