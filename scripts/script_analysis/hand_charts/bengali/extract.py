import os
import cv2, numpy as np, json, math
from grid import *; from trace import *
W,Hh=240,236
def plen(P): return sum(math.dist(a,b) for a,b in zip(P,P[1:]))
def blobs(m,minarea):
    n,lab,st,cen=cv2.connectedComponentsWithStats(m.astype(np.uint8),8)
    return [(i,st[i],cen[i]) for i in range(1,n) if st[i,4]>=minarea]
def join_gaps(strokes,maxgap=34):
    """join stroke ends of the same colour across short gaps when they point at each other"""
    changed=True
    while changed:
        changed=False
        for i in range(len(strokes)):
            for j in range(len(strokes)):
                if i>=j: continue
                A,B=strokes[i],strokes[j]
                for ea in (0,-1):
                    for eb in (0,-1):
                        pa,pb=A[ea],B[eb]; g=math.dist(pa,pb)
                        if g>maxgap or g<0.5: 
                            if g<0.5: pass
                            else: continue
                        ta=tang([(p[1],p[0]) for p in A],ea,6); tb=tang([(p[1],p[0]) for p in B],eb,6)
                        v=np.array([pb[0]-pa[0],pb[1]-pa[1]],float); n=np.linalg.norm(v)
                        if n<1e-6: ok=True
                        else:
                            v/=n; ok=float(np.dot(ta,v))>0.8 and float(np.dot(tb,-v))>0.8 and float(np.dot(ta,-tb))>0.4
                        if ok:
                            a=A if ea==-1 else A[::-1]; b=B if eb==0 else B[::-1]
                            strokes[i]=a+b; strokes.pop(j); changed=True; break
                    if changed: break
                if changed: break
            if changed: break
    return strokes
def extract_cell(i,M,box=None):
    x0,y0=(box if box else cell_box(i)[:2]); sub={k:v[y0:y0+Hh,x0:x0+W] for k,v in M.items()}
    out={"strokes":[],"reds":[],"rings":[],"crosses":[],"accents":[]}
    for k,role in (("purple","struct"),("blue","body"),("green","second")):
        ss=[rdp(s,1.6) for s in trace_mask(sub[k]) ]; ss=[s for s in ss if plen(s)>=16]
        ss=join_gaps(ss,40)
        if k=="purple":      # spurs and halos around the red dots are not strokes: keep long strokes, and vertical short descenders
            def keep(s):
                xs=[p[0] for p in s]; ys=[p[1] for p in s]; diag=math.hypot(max(xs)-min(xs),max(ys)-min(ys))
                return diag>=34 or (diag>=26 and max(xs)-min(xs)<8)
            ss=[s for s in ss if keep(s)]
        out["strokes"]+= [{"role":role,"pts":[[round(x,1),round(y,1)] for x,y in s]} for s in ss]
    out["_snap"]=True
    out["balls"]=[]
    for k in ("blue","green"):
        mk=cv2.morphologyEx(sub[k].astype(np.uint8),cv2.MORPH_OPEN,np.ones((2,2),np.uint8)); dt=cv2.distanceTransform(mk,cv2.DIST_L2,5)
        # a ball terminal: a thick blob (radius >= 4.3 px; ordinary strokes are ~2.5-3.5) at the end of a stroke
        n,lab,st,cen=cv2.connectedComponentsWithStats((dt>=4.3).astype(np.uint8),8)
        for i_ in range(1,n):
            if st[i_,4]>=6: out["balls"].append([round(float(cen[i_][0]),1),round(float(cen[i_][1]),1),k])
    for i_,st,c in blobs(cv2.morphologyEx(sub["red"],cv2.MORPH_CLOSE,np.ones((3,3),np.uint8)),22): out["reds"].append([round(float(c[0]),1),round(float(c[1]),1),int(st[4])])
    om=cv2.morphologyEx(sub["orange"].astype(np.uint8),cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
    for i_,st,c in blobs(om,18):
        w,h,area=st[2],st[3],st[4]; comp=(cv2.connectedComponents(om)[1]==i_).astype(np.uint8)
        sk=skeletonize(comp>0).astype(np.uint8); length=int(sk.sum())
        cnts,hier=cv2.findContours(comp,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE); has_hole=hier is not None and any(h_[3]>=0 for h_ in hier[0])
        ring=(0.55<w/max(h,1)<1.8) and 12<=max(w,h)<=52 and (area<0.62*w*h or has_hole)
        if not (ring and has_hole) and (max(w,h)>=48 or length>=55):
            tr=[rdp(s,1.6) for s in trace_mask(comp,close=5,prune_len=8)]; tr=[s for s in tr if plen(s)>=18]
            for s in tr:
                Ls=plen(s); xs_=[p[0] for p in s]; ys_=[p[1] for p in s]
                if math.dist(s[0],s[-1])<0.3*Ls or max(max(xs_)-min(xs_),max(ys_)-min(ys_))<45:      # a closed loop or a short bit: an orange ring, not an accent stroke
                    out["rings"].append([round((min(xs_)+max(xs_))/2,1),round((min(ys_)+max(ys_))/2,1),int(max(max(xs_)-min(xs_),max(ys_)-min(ys_)))])
                else: out["accents"].append({"role":"accent","pts":[[round(x,1),round(y,1)] for x,y in s]})
        elif ring: out["rings"].append([round(float(c[0]),1),round(float(c[1]),1),int(max(w,h))])
        else: out["crosses"].append([round(float(c[0]),1),round(float(c[1]),1),int(max(w,h))])
    hints=[(r[0],r[1],r[2]) for r in out["rings"]]+[(r[0],r[1],r[2]) for r in out["crosses"]]
    if hints and os.environ.get('ACUTE','1')=='1':        # re-trace blue/green with the rings as acute-tip hints (two strokes meeting tangentially, not a 3-way fork)
        import trace as _T; _T.FIRED.clear(); old=out["strokes"]
        keep=[s for s in out["strokes"] if s["role"] not in ("body","second")]; new=[]
        for k,role in (("blue","body"),("green","second")):
            ss=[rdp(s,1.6) for s in trace_mask(sub[k],hints=hints)]; ss=[s for s in ss if plen(s)>=16]; ss=join_gaps(ss,40)
            new+=[{"role":role,"pts":[[round(x,1),round(y,1)] for x,y in s]} for s in ss]
        out["strokes"]=keep+new if _T.FIRED else old      # only letters where the acute-tip rule fired take the re-trace
        out["acute"]=[list(p) for p in _T.FIRED]
    # snap stroke ends that stop short of a red dot onto it (the dot hides the ink under it), then re-join same-colour strokes that meet there
    for rx,ry,_ in out["reds"]:
        for s in out["strokes"]:
            for e_ in (0,-1):
                p=s["pts"][e_]
                if 2<math.dist(p,(rx,ry))<24: s["pts"].insert(0 if e_==0 else len(s["pts"]),[rx,ry])
    for role in ("struct","body","second"):
        grp=[s["pts"] for s in out["strokes"] if s["role"]==role]; rest=[s for s in out["strokes"] if s["role"]!=role]
        grp=join_gaps(grp,6); out["strokes"]=rest+[{"role":role,"pts":g} for g in grp]
    out.pop("_snap")
    return out
def extra_accents(M,x0,y0,lift=75):
    """orange strokes that rise above the cell (ai, au flourishes): search a crop lifted above the cell, return strokes in cell coordinates"""
    om=M["orange"][max(0,y0-lift):y0+60,x0:x0+W]; om=cv2.morphologyEx(om.astype(np.uint8),cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
    off=y0-max(0,y0-lift); res=[]
    n,lab,st,cen=cv2.connectedComponentsWithStats(om,8)
    for i_ in range(1,n):
        if st[i_,3]>=40 and st[i_,1]<lift-5 or st[i_,4]>400 and st[i_,1]<lift-25:
            comp=(lab==i_).astype(np.uint8)
            for s in trace_mask(comp,close=5,prune_len=8):
                P=rdp(s,1.6)
                if plen(P)>=30: res.append({"role":"accent","pts":[[round(x,1),round(y-off,1)] for x,y in P]})
    return res
if __name__=="__main__":
    im=cv2.imread("page.jpg"); M=dict(np.load("masks_soft.npz")); raw={}
    for i,n in enumerate(NAMES): raw[n]=extract_cell(i,M)
    for a,b in SWAPS: raw[a],raw[b]=raw[b],raw[a]
    json.dump(raw,open("raw.json","w"))
    print({n:(len(v["strokes"]),len(v["reds"]),len(v["rings"]),len(v["crosses"]),len(v["accents"])) for n,v in raw.items()})
