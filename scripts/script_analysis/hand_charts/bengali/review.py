import cv2, numpy as np, json, sys, math
from grid import *; from overlay import SRC, im, W, Hh
COL={"struct":(200,0,200),"body":(255,0,0),"second":(0,150,0),"accent":(0,130,255)}
def parse(d):
    t=d.replace("M"," ").replace("L"," ").split(); v=list(map(float,t)); return list(zip(v[0::2],v[1::2]))
def render(l,sc=2.6,pad=8):
    img=np.full((int(100*sc)+2*pad,int(100*sc)+2*pad,3),255,np.uint8)
    f=lambda p:(int(pad+p[0]*sc),int(pad+p[1]*sc))
    cv2.line(img,f((0,20)),f((100,20)),(235,235,235),1); cv2.line(img,f((0,83)),f((100,83)),(235,235,235),1)
    for role,d,sid in l["strokes"]:
        P=[f(p) for p in parse(d)]; cv2.polylines(img,[np.array(P,np.int32)],False,COL[role],2,cv2.LINE_AA)
        cv2.putText(img,sid,(P[0][0]+3,P[0][1]-3),cv2.FONT_HERSHEY_SIMPLEX,0.35,(90,90,90),1)
        for q in (P[0],P[-1]): cv2.circle(img,q,2,(0,0,0),-1)
    for j in l["junctions"]:
        c=f((j["x"],j["y"]))
        if j["t"]=="red": cv2.circle(img,c,6,(0,0,255),-1)
        elif j["t"]=="touch": cv2.circle(img,c,7,(0,140,255),2)
        else: cv2.drawMarker(img,c,(0,140,255),cv2.MARKER_TILTED_CROSS,14,2)
        if j.get("loose"): cv2.circle(img,c,11,(0,0,0),1)
    cv2.putText(img,l["glyph"],(4,18),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,0),2)
    return img
def photo(name):
    i=NAMES.index(SRC[name]); x0,y0,_,_=cell_box(i); c=im[y0+12:y0+Hh,x0:x0+W]; return cv2.resize(c,None,fx=1.15,fy=1.15)
def sheet(letters,fn):
    rows=[]
    for l in letters:
        a=photo(l["glyph"]); b=render(l); h=max(a.shape[0],b.shape[0]); 
        pad=lambda x:np.vstack([x,np.full((h-x.shape[0],x.shape[1],3),255,np.uint8)])
        rows.append(np.hstack([pad(a),pad(b)]))
    cols=2; 
    while len(rows)%cols: rows.append(np.full_like(rows[0],255))
    cv2.imwrite(fn,np.vstack([np.hstack(rows[i:i+cols]) for i in range(0,len(rows),cols)]))
if __name__=="__main__":
    G=json.load(open(sys.argv[1])); by={l["glyph"]:l for l in G}
    names=sys.argv[3:] if len(sys.argv)>3 else [l["glyph"] for l in G]
    sheet([by[n] for n in names],sys.argv[2])
