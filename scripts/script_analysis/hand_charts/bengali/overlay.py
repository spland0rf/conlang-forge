import cv2, numpy as np, json, sys
from grid import *
im=cv2.imread("page.jpg"); W,Hh=240,236
SRC={n:n for n in NAMES}
for a,b in SWAPS: SRC[a],SRC[b]=b,a        # the drawing of letter a sits in cell b
COL={"struct":(200,0,200),"body":(255,0,0),"second":(0,150,0),"accent":(0,130,255)}
def panel(name,raw,photo=True,scale=1.0):
    i=NAMES.index(SRC[name]); x0,y0,_,_=cell_box(i)
    base=im[y0:y0+Hh,x0:x0+W].copy()
    if photo: base=(base*0.55+255*0.45).astype(np.uint8)
    else: base[:]=255
    v=raw[name]
    for s in v["strokes"]+v["accents"]:
        P=np.array(s["pts"],np.int32); cv2.polylines(base,[P],False,COL[s["role"]],2,cv2.LINE_AA)
        for q in (P[0],P[-1]): cv2.circle(base,tuple(int(t) for t in q),3,(0,0,0),-1)
    for x,y,a in v["reds"]: cv2.circle(base,(int(x),int(y)),6,(0,0,255),2)
    for x,y,d in v["rings"]: cv2.circle(base,(int(x),int(y)),int(d/2),(0,140,255),2)
    for x,y,d in v["crosses"]: cv2.drawMarker(base,(int(x),int(y)),(0,140,255),cv2.MARKER_TILTED_CROSS,12,2)
    cv2.putText(base,name,(4,16),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,0),2)
    return base
def page(names,fn,cols=5):
    raw=json.load(open(sys.argv[1] if len(sys.argv)>1 else "raw.json")); ps=[panel(n,raw) for n in names]
    while len(ps)%cols: ps.append(np.full_like(ps[0],255))
    rows=[np.hstack(ps[i:i+cols]) for i in range(0,len(ps),cols)]
    cv2.imwrite(fn,np.vstack(rows))
if __name__=="__main__":
    for k in range(0,44,10): page(NAMES[k:k+10],"ov_%d.png"%(k//10),5)
