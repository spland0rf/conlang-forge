import cv2, numpy as np, json
from grid import *; import extract
K=0.758
PH={"top":dict(cols=[55,401,743,1085,1428,1775,2129],rows=[46,397,742,1087],row0=0),
    "bot":dict(cols=[106,448,786,1122,1459,1798,2143],rows=[281,620,958,1297],row0=4)}
ims={};Ms={};cells={}
for f,p in PH.items():
    im=cv2.resize(cv2.imread(f+".jpg"),None,fx=K,fy=K,interpolation=cv2.INTER_AREA); ims[f]=im; cv2.imwrite(f+"_s.png",im)
    Ms[f]=soft_masks(im)
    for r,y in enumerate(p["rows"]):
        for c in range(6):
            idx=(p["row0"]+r)*6+c
            if idx<len(NAMES): cells[NAMES[idx]]=(f,int(p["cols"][c]*K)+7,int(y*K)+7)
json.dump(cells,open("cells.json","w"),ensure_ascii=False)
raw={}
for n,(f,x0,y0) in cells.items():
    raw[n]=extract.extract_cell(0,Ms[f],(x0,y0))
    if n in ("ai","au","ṛ","e","o"): 
        ex=extract.extra_accents(Ms[f],x0,y0); have=[a["pts"] for a in raw[n]["accents"]]
        if ex and not raw[n]["accents"]: raw[n]["accents"]+=ex
for a,b in SWAPS: raw[a],raw[b]=raw[b],raw[a]; cells[a],cells[b]=cells[b],cells[a]
json.dump(raw,open("raw2.json","w")); json.dump(cells,open("cells_sw.json","w"),ensure_ascii=False)
print(len(raw),[n for n in NAMES if n not in raw])
