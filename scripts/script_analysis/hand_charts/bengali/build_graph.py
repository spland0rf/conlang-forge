import json, math, numpy as np, sys
from trace import rdp
S=0.46; CX=131.0; BY=86.0; BAR=26.0   # cell px -> 100-box: uniform scale, bar centre x -> 50, bar y -> 26 (headroom for tall stems), stem bottoms about 85
def nm(p): return (50+(p[0]-CX)*S, BAR+(p[1]-BY)*S)
def plen(P): return sum(math.dist(a,b) for a,b in zip(P,P[1:]))
def nearest(P,q):
    """(distance, arc fraction, index of segment) of the closest point on polyline P to q"""
    best=(1e9,0,0,None); tot=plen(P); acc=0
    for i,(a,b) in enumerate(zip(P,P[1:])):
        ab=(b[0]-a[0],b[1]-a[1]); L2=ab[0]**2+ab[1]**2; t=0 if L2==0 else max(0,min(1,((q[0]-a[0])*ab[0]+(q[1]-a[1])*ab[1])/L2))
        c=(a[0]+t*ab[0],a[1]+t*ab[1]); d=math.dist(c,q)
        if d<best[0]: best=(d,(acc+t*math.sqrt(L2))/tot if tot else 0,i,c)
        acc+=math.sqrt(L2)
    return best
def seg_cross(P,Q):
    """True if two polylines properly cross"""
    def o(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for a,b in zip(P,P[1:]):
        for c,d in zip(Q,Q[1:]):
            if o(a,b,c)*o(a,b,d)<0 and o(c,d,a)*o(c,d,b)<0: return True
    return False
def path_str(P): return "M"+" L".join("%.1f %.1f"%(x,y) for x,y in P).replace("M","M",1)
def nearest_red_candidate(j,v): return True
def build_letter(name,v,R=6.0):
    strokes=[]
    for s in v["strokes"]+v["accents"]:
        P=[nm(p) for p in s["pts"]]; P=rdp(P,0.7)
        if plen(P)<4: continue
        strokes.append({"role":s["role"],"P":P})
    # ball terminals: extend the stroke end that stops short of a thick blob onto its centre and record the end style
    ends={}
    for bx,by,bk in v.get("balls",[]):
        best=None
        for st_ in strokes:
            if st_["role"] not in ("body","second"): continue
            for e_ in (0,-1):
                d=math.dist(st_["P"][e_],nm((bx,by)))
                if d<9 and (best is None or d<best[0]): best=(d,st_,e_)
        if best:
            d,st_,e_=best
            if d>1.0: st_["P"].insert(0 if e_==0 else len(st_["P"]),nm((bx,by)))
            st_.setdefault("ball",set()).add("start" if e_==0 else "end")
    order={"struct":0,"body":1,"second":2,"accent":3}; strokes.sort(key=lambda s:(order[s["role"]],s["P"][0][0]))
    for i,s in enumerate(strokes): s["id"]="s%d"%(i+1)
    marks=[(nm(p[:2]),"red") for p in v["reds"]]+[(nm(p[:2]),"orange") for p in v["rings"]+v["crosses"]]
    # merge markers closer than 5 units (same kind)
    pts=[]
    for q,k in marks:
        for m in pts:
            if m["k"]==k and math.dist(m["q"],q)<(9 if k=="orange" else 5): m["q"]=((m["q"][0]+q[0])/2,(m["q"][1]+q[1])/2); break
        else: pts.append({"q":q,"k":k})
    J=[]
    for m in pts:
        q=m["q"]; mem=[]
        for s in strokes:
            d,t,i,c=nearest(s["P"],q)
            if d<=R: mem.append((s,d,t,c))
        if len(mem)<1: continue
        kind="red" if m["k"]=="red" else "touch"
        if kind=="touch" and any(seg_cross(a[0]["P"],b[0]["P"]) and math.dist(a[3],b[3])<R*1.4 for ai,a in enumerate(mem) for b in mem[ai+1:]): kind="cross"
        # junction position: mean of the closest points
        x=float(np.mean([c[3][0] for c in mem])); y=float(np.mean([c[3][1] for c in mem]))
        J.append({"t":kind,"x":round(x,1),"y":round(y,1),"members":[{"stroke":s["id"],"at":round(t,2),"where":"start" if t<0.07 else "end" if t>0.93 else "middle"} for s,d,t,c in mem],"loose":len(mem)<2})
    # hand corrections from the user's review
    for j in J:
        if name=="gha" and j["t"]=="red" and 28<j["y"]<52 and j["x"]<45: j["t"]="touch"          # user: the red dot in the middle of the blue strokes is just an orange circle
        if name in ("ma","bha","pha") and j["t"]=="cross": j["t"]="touch"                       # user: these letters have only rings, no crosses
        if name in ("ga","ṇa") and j["t"]=="touch" and any(m["where"]=="middle" for m in j["members"]) and j["t"]!="red" and nearest_red_candidate(j,v): j["t"]="red"
    ends={s["id"]:sorted(s["ball"]) for s in strokes if s.get("ball")}
    return {"glyph":name,"iast":name,"variant":None,"strokes":[[s["role"],path_str(s["P"]),s["id"]] for s in strokes],"junctions":J,"ends":{k:["ball" if x else "plain" for x in (("start" in v_),("end" in v_))] for k,v_ in ends.items()},"_pts":{s["id"]:s["P"] for s in strokes}}
if __name__=="__main__":
    raw=json.load(open(sys.argv[1])); out=[build_letter(n,v) for n,v in raw.items()]
    json.dump(out,open(sys.argv[2],"w"),ensure_ascii=False)
    for l in out: print(l["glyph"],len(l["strokes"]),"J",len(l["junctions"]),"loose",sum(j["loose"] for j in l["junctions"]),end=" | ")
