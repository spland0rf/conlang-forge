"""Named letter shapes the user can ask for: "vowels are rings", "stops are triangles".

A writing system gives each class of sounds one characteristic figure (see shapes.py and the motif code in generate.py):
every letter of that class is the figure plus one small variant (a stem, a bar, a dot, a turn...), so related sounds look
related. By default the generator chooses those figures from the script's style families. The `*_shape` dials let a user
choose the figure for a class, by name; anything left on "auto" is chosen as before.

This file is the vocabulary: a plain name -> the builder of the figure, taken from the family tables."""
from __future__ import annotations

from .families import FORMS

# name -> (family table, figure key). Every pair is checked against FORMS when the module loads.
SHAPES = {
    "ring": ("bubbly", "ring"), "double ring": ("bubbly", "ring2"), "ring with cross": ("bubbly", "ringcross"), "target": ("bubbly", "target"),
    "triangle": ("spikey", "tri"), "inverted triangle": ("spikey", "tri_down"), "diamond": ("spikey", "diamond"), "X": ("spikey", "X"),
    "trident": ("spikey", "trident"), "zigzag": ("spikey", "peak2"), "V": ("spikey", "V"), "W": ("spikey", "W"), "M": ("spikey", "M"),
    "N": ("spikey", "N"), "Z": ("spikey", "Z"), "Y": ("spikey", "Y"), "K": ("spikey", "K"),
    "box": ("boxy", "box"), "double box": ("boxy", "box2"), "plus": ("boxy", "plus"), "comb": ("boxy", "comb"),
    "T": ("boxy", "T"), "L": ("boxy", "L"), "H": ("boxy", "H"), "F": ("boxy", "F"), "P": ("boxy", "P"),
    "arc": ("curvy", "arc"), "S curve": ("curvy", "S"), "curl": ("curvy", "curl"), "wave": ("curvy", "wave1"),
    "arch": ("curvy", "arch"), "cup": ("curvy", "cup"),
}
SHAPE_NAMES = tuple(SHAPES)
# the sound classes a shape can be chosen for, and the dial that holds each choice
SHAPE_DIALS = {"vowel": "vowel_shape", "plosive": "plosive_shape", "fricative": "fricative_shape", "nasal": "nasal_shape",
               "approximant": "approximant_shape"}
for _name, (_fam, _key) in SHAPES.items():            # a typo here would otherwise only show when someone chose the shape
    assert _key in FORMS[_fam], (_name, _fam, _key)


def key(name: str) -> str:
    """The key of the figure in a script's figure table."""
    return ".".join(SHAPES[name])


def builder(name: str):
    """The function that draws the figure called `name` (unit box, y up)."""
    fam, key = SHAPES[name]
    return FORMS[fam][key][0]


def chosen(spec: dict) -> dict:
    """{sound group: shape name} for every group the user picked a shape for."""
    return {g: spec[d] for g, d in SHAPE_DIALS.items() if spec.get(d, "auto") != "auto"}
