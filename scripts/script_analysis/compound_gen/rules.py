"""The hard rules of stroke-letter generation. They are DATA now: the numbers live in script_config/<script>.json ("rules", with a short note per
rule in "rule_notes"); the script is chosen with $CONLANG_SCRIPT (default devanagari). Everything in RULES is fixed input: the generators build to it
(where they can) and the validator enforces it (always); neither may change it. Only what is not listed is left to randomness."""
import os, sys
from types import MappingProxyType
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import script_config as SC

CFG = SC.get()
RULES = MappingProxyType(dict(CFG["rules"]))
R = RULES
FRAME = MappingProxyType(dict(CFG["frame"]))            # box, bar_y, base_y, desc_y, half_top
