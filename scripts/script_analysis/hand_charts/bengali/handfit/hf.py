import cv2, math, json, numpy as np
A="/mnt/user-data/attachments/9df3cbd6-5590-5857-9ad9-4bf9abf1a96b/"
SPEC={}
COL={"struct":(200,0,200),"body":(255,0,0),"second":(0,160,0),"accent":(0,140,255)}
def conv(cell,p):
    x0,y0,cw=cell; k=258.0/cw
    return (50+((p[0]-x0)*k-7-131)*0.46, 26+((p[1]-y0)*k-7-86)*0.46)
def plen(P): return sum(math.dist(a,b) for a,b in zip(P,P[1:]))
def nearest(P,q):
    best=(1e9,0); tot=plen(P) or 1; acc=0
    for a,b in zip(P,P[1:]):
        ab=(b[0]-a[0],b[1]-a[1]); L2=ab[0]**2+ab[1]**2; t=0 if L2==0 else max(0,min(1,((q[0]-a[0])*ab[0]+(q[1]-a[1])*ab[1])/L2))
        c=(a[0]+t*ab[0],a[1]+t*ab[1]); d=math.dist(c,q)
        if d<best[0]: best=(d,(acc+t*math.sqrt(L2))/tot)
        acc+=math.sqrt(L2)
    return best
def px_strokes(sp):
    out={}
    for role,sid,pts,*o in sp["S"]:
        o=o[0] if o else {}
        P=[tuple(p) for p in pts]
        if o.get("V"): mx=sum(p[0] for p in P)/len(P); P=[(mx,P[0][1]),(mx,P[-1][1])]
        if o.get("H"): my=sum(p[1] for p in P)/len(P); P=[(min(p[0] for p in P),my),(max(p[0] for p in P),my)]
        out[sid]=(role,P,o)
    return out
def build(name):
    sp=SPEC[name]; st=px_strokes(sp); cell=sp["cell"]; U={}
    for sid,(role,P,o) in st.items():
        Q=[conv(cell,p) for p in P]
        if o.get("H"): y=Q[0][1]; y=26.0 if abs(y-26)<4 else y; Q=[(Q[0][0],y),(Q[-1][0],y)]
        if o.get("V"): mx=Q[0][0]; Q=[(mx,Q[0][1]),(mx,Q[-1][1])]
        U[sid]=(role,Q,o)
    strokes=[[r,"M"+" L".join("%.1f %.1f"%p for p in Q),sid] for sid,(r,Q,o) in U.items()]
    ends={}
    for sid,(r,Q,o) in U.items():
        b=o.get("ball")
        if b: ends[sid]=["ball" if b in("start","both") else "plain","ball" if b in("end","both") else "plain"]
    J=[]
    for t,mem in sp["J"]:
        pts=[];members=[]
        for sid,ref in mem:
            role,P,o=st[sid]; Pu=U[sid][1]
            q=P[0] if ref=="start" else P[-1] if ref=="end" else ref
            qu=Pu[0] if ref=="start" else Pu[-1] if ref=="end" else None
            f=nearest(Pu,conv(cell,q))[1] if qu is None else (0.0 if ref=="start" else 1.0)
            members.append({"stroke":sid,"at":round(f,2),"where":"start" if f<0.04 else "end" if f>0.96 else "middle"}); pts.append(conv(cell,q))
        J.append({"t":t,"x":round(sum(p[0] for p in pts)/len(pts),1),"y":round(sum(p[1] for p in pts)/len(pts),1),"members":members,"loose":len(members)<2})
    return {"glyph":name,"iast":name,"variant":None,"strokes":strokes,"junctions":J,"ends":ends}
def overlay(name,out=None):
    sp=SPEC[name]; im=cv2.imread(A+sp["file"]+"-image.jpg"); st=px_strokes(sp)
    for sid,(role,P,o) in st.items():
        cv2.polylines(im,[np.array(P,np.int32)],False,COL[role],2)
        cv2.putText(im,sid,(int(P[0][0])+4,int(P[0][1])-4),cv2.FONT_HERSHEY_SIMPLEX,0.5,COL[role],1)
    for t,mem in sp["J"]:
        for sid,ref in mem:
            role,P,o=st[sid]; q=P[0] if ref=="start" else P[-1] if ref=="end" else ref
            cv2.circle(im,(int(q[0]),int(q[1])),9,{"red":(0,0,255),"touch":(0,140,255),"cross":(255,0,255)}[t],2)
    x0,y0,cw=sp["cell"]; c=im[max(0,y0-10):y0+cw+10,max(0,x0-10):x0+cw+10]
    o=out or "ov_%s.png"%name; cv2.imwrite(o,c); return o
