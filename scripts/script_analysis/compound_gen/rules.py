"""The hard rules of stroke-letter generation, as DATA: the numbers live in script_config/<script>.json ("rules", with a note per rule in
"rule_notes").  `R` is a live view of the ACTIVE profile's rules (script_config.active(); switch with `script_config.use(...)`), so a module that
imports R reads the rules at call time, never frozen at import.  Everything in R is fixed input: the generators build to it (where they can)
and the validator enforces it (always); neither may change it.  Only what is not listed is left to randomness."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import script_config as SC

R = RULES = SC.RulesView()
def active(): return SC.active()
