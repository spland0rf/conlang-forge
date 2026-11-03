"""Derive the first top-down alphabet spec from the real-Devanagari profile (profile.json). Edit spec.json by hand to change the mix."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(HERE, "profile.json")))
sk = P["skeleton"]                                           # stem / desc / barless / hang
spec = {
  "size": 40, "seed": 1,
  "source": "real Devanagari profile (49 letters): " + json.dumps(sk),
  "skeleton_share": {"stem": sk["stem"], "desc": sk["desc"], "hang": sk["hang"], "half": sk["barless"]},
  "skeleton_recipes": {"chain": 0.35, "branch": 0.35, "land": 0.30},            # how a second stroke relates to the first
  "half": {"three_share": 0.57,                                                  # 4 of the 7 real bar-less letters are '3' forms
           "join_at": {"top": 0.2, "mid": 0.4, "bottom": 0.4},                    # where the connector leaves the left form (user's brief)
           "right_form": {"G": 0.7, "hook": 0.3}},
  "per_bucket_try_budget": 4000, "max_per_family": 3, "avoid_checkpoint": False,
  "note": "Rules (orientation, joins, bar, sizes) are NOT here: they are fixed in compound_gen/rules.py and cannot be altered by the spec."
}
json.dump(spec, open(os.path.join(HERE, "spec.json"), "w"), indent=1)
print(json.dumps(spec, indent=1))
