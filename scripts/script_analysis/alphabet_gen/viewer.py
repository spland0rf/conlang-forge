import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
A = json.load(open(os.path.join(HERE, "alphabet.json"))); A["profile"] = json.load(open(os.path.join(HERE, "profile.json")))
A["profile"].pop("letters", None)
open(sys.argv[1], "w").write(open(os.path.join(HERE, "viewer_template.html")).read().replace("/*DATA*/null", json.dumps(A)))
