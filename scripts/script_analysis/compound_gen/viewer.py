import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "letters.json")))
if os.path.exists(os.path.join(HERE, "letters_half.json")): G += json.load(open(os.path.join(HERE, "letters_half.json")))
tpl = open(os.path.join(HERE, "viewer_template.html")).read()
open(sys.argv[1], "w").write(tpl.replace("/*DATA*/null", json.dumps(G)))
