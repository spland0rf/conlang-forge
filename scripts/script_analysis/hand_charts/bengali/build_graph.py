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

# ---- hand corrections from the user's review (applied to the strokes before junctions are detected) -------------------------------------
def _near_idx(P,q): return min(range(len(P)),key=lambda i:math.dist(P[i],q))
def _find(strokes,role,end_near,which):
    """the stroke of `role` whose start (0) / end (-1) is closest to end_near"""
    c=[s for s in strokes if s["role"]==role]; return min(c,key=lambda s:math.dist(s["P"][which],end_near))
def single_bar(strokes):
    """every top bar is ONE long horizontal stroke: merge the bar pieces, drop the small purple bumps around the red dots"""
    bars=[s for s in strokes if s["role"]=="struct" and (max(p[0] for p in s["P"])-min(p[0] for p in s["P"]))>=20 and (max(p[1] for p in s["P"])-min(p[1] for p in s["P"]))<=7]
    if not bars: return strokes
    xs=[p[0] for s in bars for p in s["P"]]; y=sum(plen(s["P"])*sum(p[1] for p in s["P"])/len(s["P"]) for s in bars)/sum(plen(s["P"]) for s in bars)
    keep=[s for s in strokes if s["role"]!="struct" or (s not in bars and (plen(s["P"])>=14 or abs(s["P"][0][0]-s["P"][-1][0])<3 and False))]
    keep=[s for s in keep if not (s["role"]=="struct" and plen(s["P"])<14)]
    keep.append({"role":"struct","P":[(min(xs),y),(max(xs),y)]}); return keep
def split_at(strokes,st,q):
    d,t,i,c=nearest(st["P"],q); P=list(st["P"])
    if math.dist(c,P[i])>0.3 and math.dist(c,P[i+1])>0.3: P.insert(i+1,c); i=i+1
    else: i=i if math.dist(c,P[i])<=math.dist(c,P[i+1]) else i+1
    if 0<i<len(P)-1:
        a={"role":st["role"],"P":P[:i+1]}; b={"role":st["role"],"P":P[i:]}
        for k in ("ball",): 
            if st.get(k): a[k]=st[k]; b[k]=st[k]
        strokes.remove(st); strokes+= [a,b]; return a,b
    return st,None

def _pl_dist(P,q): return nearest(P,q)[0]
def _alen(P,i0=0,i1=None):
    i1=len(P)-1 if i1 is None else i1; return sum(math.dist(P[k],P[k+1]) for k in range(i0,i1))
def fork_to_tip(strokes,rings,sep=4.5):
    """Two strokes that meet at a very acute tip must touch ONLY at the tip.  Two tracing artefacts are repaired:
    (a) a branch that starts on the stem a few units BELOW the stem's tip (3 lines at an intermediate point), and
    (b) two strokes that run side by side down from a shared end.  The less straight stroke is made to leave the tip directly, straight to the first
    vertex that is `sep` units clear of the other stroke."""
    body=[s for s in strokes if s["role"] in ("body","second")]
    for S in body:
        for e_i in (0,-1):
            e=S["P"][e_i]
            if not any(math.dist(e,r)<=9.0 for r in rings): continue        # a tip carries an orange ring
            for T in body:
                if T is S: continue
                for t_i in (0,-1):
                    f=T["P"][t_i]; case=None
                    if math.dist(f,e)<=5.0: case="shared"
                    else:
                        d,t,i,c=nearest(S["P"],f)
                        if d<=3.0:
                            # arclength from S's end e to the projected point of f, must be a short stub (the stem continues past the branch)
                            along=(_alen(S["P"],0,i)+math.dist(S["P"][i],c)) if e_i==0 else (_alen(S["P"],i+1)+math.dist(S["P"][i+1],c))
                            if 2.0<=along<=18.0: case="fork"
                    if not case: continue
                    # who leaves: the stroke whose first vertices are farther from the other
                    Tp=T["P"] if t_i==0 else T["P"][::-1]
                    # drop T's vertices that lie within sep of S, then start at the tip
                    j=next((k for k in range(1,len(Tp)) if _pl_dist(S["P"],Tp[k])>=sep and math.dist(Tp[k],e)>=sep),None)
                    if j is None: continue
                    newT=[e]+Tp[j:]
                    if case=="shared":
                        # the straighter stroke stays: compare how far each strays from the other 10 units out
                        def turn(A):       # how much a stroke bends away from its own first stretch (the branch bends, the stem does not)
                            def at(L): 
                                k=min(range(len(A)),key=lambda m:abs(_alen(A,0,m)-L)); return A[k]
                            a=(at(10)[0]-A[0][0],at(10)[1]-A[0][1]); c=(at(40)[0]-A[0][0],at(40)[1]-A[0][1])
                            na,nc=math.hypot(*a),math.hypot(*c)
                            return 0.0 if na<1e-6 or nc<1e-6 else 1-(a[0]*c[0]+a[1]*c[1])/(na*nc)
                        Sp=S["P"] if e_i==0 else S["P"][::-1]
                        if turn(Sp) > turn(Tp): continue         # S is the branch: handled when roles swap
                    T["P"]=newT if t_i==0 else newT[::-1]
                    return True
    return False


def straighten(strokes,bar_y=BAR,vert_tol=3.2,vert_min=26.0):
    """User: anything close to ONE flat horizontal bar is one perfectly horizontal bar (at the headline height), and anything close to one long vertical
    bar is one perfectly vertical bar.  Bars: replace by a 2-point horizontal line.  Verticals: a run of vertices that stays within vert_tol of its
    mean x and spans at least vert_min in y (monotonic) becomes exactly vertical at that mean x."""
    moved=[]
    for s in strokes:
        P=s["P"]; xs=[p[0] for p in P]; ys=[p[1] for p in P]
        ms=sorted(ys)[len(ys)//2]
        mxs=sorted(xs)[len(xs)//2]
        if s["role"]=="struct" and max(xs)-min(xs)<30 and max(ys)-min(ys)>=8:       # the short purple stem under a bar: one straight vertical (ink blobs at its red dot are dropped)
            keep=[p for p in P if abs(p[0]-mxs)<=3.0]
            if len(keep)>=2 and max(p[1] for p in keep)-min(p[1] for p in keep)>=6:
                s["P"]=[(mxs,min(p[1] for p in keep)),(mxs,max(p[1] for p in keep))]; continue
        if s["role"]=="struct" and max(xs)-min(xs)>=30 and sum(abs(y-ms)<=3.5 for y in ys)>=0.5*len(ys):      # a bar, even with a small hook or blob at a red dot
            my=ms; y0=bar_y if abs(my-bar_y)<=4.0 else my          # the frame's headline height unless this letter's bar really sits lower or higher (i, ī, u, ū, ṭha)
            s["P"]=[(min(xs),y0),(max(xs),y0)]; continue
        if s["role"] in ("body","second") and max(xs)-min(xs)<=8.0 and max(ys)-min(ys)>=40 and all(b[1]-a[1]>=-0.5 for a,b in zip(P,P[1:])):      # a long stem with a jog in it: ONE vertical
            mx=sum(xs)/len(xs); moved.append((list(P),mx)); s["P"]=[(mx,P[0][1]),(mx,P[-1][1])]; continue
        i=0; out=[]; n=len(P)
        while i<n:
            best=None
            for j in range(i+1,n):
                run=P[i:j+1]; rx=[p[0] for p in run]
                if max(rx)-min(rx)>2*vert_tol: break
                dy=[b[1]-a[1] for a,b in zip(run,run[1:])]
                if not (all(d>=-0.5 for d in dy) or all(d<=0.5 for d in dy)): break
                if abs(run[-1][1]-run[0][1])>=vert_min: best=j
            if best is None: out.append(P[i]); i+=1; continue
            run=P[i:best+1]; mx=sum(p[0] for p in run)/len(run)
            out+= [(mx,run[0][1]),(mx,run[-1][1])]; i=best+1
        # drop duplicates produced by joining
        clean=[out[0]]
        for p in out[1:]:
            if math.dist(p,clean[-1])>1e-6: clean.append(p)
        s["P"]=clean if len(clean)>=2 else P
    for old,mx in moved:      # a branch that ended on the old stem now ends on the new one
        for s in strokes:
            for e in (0,-1):
                q=s["P"][e]
                for o in (old[0],old[-1]):
                    if math.dist(q,o)<=3.5 and abs(q[0]-mx)>0.2 and len(s["P"])>2: s["P"][e]=(mx,q[1]); break


def trim_shadow(strokes,tol=2.5,min_run=10.0):
    """A stroke end that just runs ALONG another stroke (the straightened stem) for min_run units or more is a duplicate line: start the stroke where it
    leaves the other one."""
    ch=False
    for s in strokes:
        if s["role"] not in ("body","second"): continue
        for rev in (False,True):
            P=s["P"][::-1] if rev else s["P"]
            for o in strokes:
                if o is s or o["role"] not in ("body","second"): continue
                k=0
                while k<len(P)-2 and nearest(o["P"],P[k+1])[0]<=tol: k+=1
                if k>=1 and nearest(o["P"],P[0])[0]<=tol and plen(P[:k+1])>=min_run:
                    P=[nearest(o["P"],P[k])[3]]+P[k+1:]; ch=True; break
            s["P"]=P[::-1] if rev else P
    return ch

def patch_strokes(name,strokes,rings=()):
    for s in list(strokes):      # an out-and-back spike: split into two strokes that meet at the tip
        P=s["P"]
        for k in range(1,len(P)-1):
            if s["role"] in ("body","second") and math.dist(P[k-1],P[k+1])<2.0 and math.dist(P[k],P[k-1])>=4.0 and k+2<len(P):
                A=P[:k+1]; B=[P[k]]+P[k+2:]; s["P"]=A; strokes.append({"role":s["role"],"P":B}); break
    if name=="a":      # the stem ends at the bottom ring; a second green line comes from the middle red dot to the same tip (a V); the hook past the ring was a tracing artefact
        stem=[s for s in strokes if s["role"]=="second"]
        if stem:
            top=stem[0]["P"][0]; stem[0]["P"]=[top,(top[0],78.9)]
            strokes.append({"role":"second","P":[(63.8,64.8),(top[0],78.9)]})
    if name=="ū":      # the inner tail runs straight from its upper end to the ring at the bottom curve; the zigzag points were artefacts
        t=[s for s in strokes if s["role"]=="body" and any(math.dist(p,(36.7,49.5))<2.5 for p in s["P"])]
        for s in t:
            if len(s["P"])<=6: s["P"]=[(36.7,49.5),(47.7,66.5),(55.0,75.2)]
    strokes=single_bar(strokes)
    if name=="ū":
        big=max((s for s in strokes if s["role"]=="body"),key=lambda s:plen(s["P"])); inner=[s for s in strokes if s["role"]=="body" and s is not big][0]
        d,t,i,P=nearest(big["P"],(55.0,75.2)); a,b=split_at(strokes,big,P)               # both tails end on the bottom curve at one point
        inner["P"][-1]=P
    if name=="ṛ":
        stem=max((s for s in strokes if s["role"]=="body"),key=lambda s:abs(s["P"][0][1]-s["P"][-1][1])); x=43.0
        y0,y1=stem["P"][0][1],stem["P"][-1][1]; old=[p for p in stem["P"]]
        stem["P"]=[(x,y0),(x,y1)]                                                         # one straight vertical stroke
        for s in strokes:
            if s is stem: continue
            for e in (0,-1):
                if min(abs(p[1]-s["P"][e][1])<1e9 and math.dist(p,s["P"][e]) for p in old)<7 and abs(s["P"][e][0]-x)<7: s["P"][e]=(x,s["P"][e][1])
    if name=="ha":      # only the bottom-left ring: the top has a real orange cross that the rule must not touch
        for _ in range(3):
            if not fork_to_tip(strokes,[r for r in rings if r[1]>60]): break
    if name not in ("ha","śa","o","va"):      # every letter but these: an orange ring on a sharp tip means two strokes meeting at the very end (ha has a real cross; śa and o changed for the worse)
        for _ in range(3):
            if not fork_to_tip(strokes,rings): break
    if name=="ṣa":
        tipq=nm((164.0,223.0)); body=[s for s in strokes if s["role"]=="body"]
        d=[s for s in body if math.dist(s["P"][-1],(64.3,78.4))<4]
        if d: d[0]["P"].append(tipq)            # the diagonal runs on to the stem's end (the ring), where the fork rule then separates the two
    if name=="la":
        # the dip of the m-shaped stroke is a deep SHARP V whose tip is the orange ring: two curved strokes meet there at an acute angle
        curl=max((s for s in strokes if s["role"]=="body"),key=lambda s:len(s["P"]))
        p0=nm((153,120)); p1=nm((120,116)); i0=min(range(len(curl["P"])),key=lambda i:math.dist(curl["P"][i],p0)); i1=min(range(len(curl["P"])),key=lambda i:math.dist(curl["P"][i],p1))
        if i0>i1: i0,i1=i1,i0
        tip=[nm(p) for p in ((146,127),(139,141),(133.5,154.0),(131.5,141),(127.5,127))]
        if curl["P"][i0][0]>curl["P"][i1][0]: tip=tip   # path runs stem-side first, then over the hump
        curl["P"]=curl["P"][:i0+1]+tip+curl["P"][i1:]
    if name=="ī":
        body=[s for s in strokes if s["role"]=="body"]
        if len(body)==2:
            q=(43.0,84.0); ball=(31.7,73.0)
            # the curl is ONE open stroke: ball (left) -> over the red dot -> down -> sweeping to the lower-left ring; the diagonal + stem start on it.
            # the tracer joined the ball to the ring by mistake: cut that jump, then lay the curl's tail on the ring
            curl=min(body,key=lambda s:min(math.dist(p,ball) for p in s["P"])); diag=[s for s in body if s is not curl][0]
            if math.dist(curl["P"][0],q)<math.dist(curl["P"][-1],q): curl["P"].reverse()      # ring end last
            if math.dist(curl["P"][-1],q)<12: curl["P"]=curl["P"][:-1]                          # drop the ball->ring jump (now ends at the ball side)
            if math.dist(diag["P"][0],q)>math.dist(diag["P"][-1],q): diag["P"].reverse()      # diagonal starts at the ring end
            P1=diag["P"][1]; ring=diag["P"][0]; diag["P"]=diag["P"][1:]
            if math.dist(curl["P"][0],P1)>math.dist(curl["P"][-1],P1): curl["P"].reverse()
            curl["P"]=[ring]+curl["P"] if False else curl["P"]
            # curl runs from its joint with the diagonal (near P1) over the dot to the ball; its tail beyond P1 reaches the ring
            curl["P"]=[ring]+curl["P"]
    if name=="ka":
        body=[s for s in strokes if s["role"]=="body"]; stem=max(body,key=lambda s:max(p[1] for p in s["P"])-min(p[1] for p in s["P"])); low=[s for s in body if s is not stem][0]
        T=(55.1,22.7); a,b=split_at(strokes,stem,T)                                       # the stem and the top-left edge are two strokes meeting at the bar dot
        down,edge=(a,b) if max(p[1] for p in a["P"])>max(p[1] for p in b["P"]) else (b,a)
        bx=sum(p[0] for p in down["P"])/len(down["P"]); yb=max(p[1] for p in down["P"]); yt=min(p[1] for p in down["P"])
        down["P"]=[(bx,yt),(bx,yb)]; edge["P"][0 if math.dist(edge["P"][0],T)<math.dist(edge["P"][-1],T) else -1]=(bx,yt)
        L=edge["P"][-1] if math.dist(edge["P"][0],(bx,yt))<math.dist(edge["P"][-1],(bx,yt)) else edge["P"][0]
        d0=math.dist(low["P"][0],L)<math.dist(low["P"][-1],L)
        low["P"][0 if d0 else -1]=L; low["P"][-1 if d0 else 0]=(bx,yb)                      # the third side closes the triangle
    return strokes
def snap_loose(strokes,reds,R=6.0,reach=16.0):
    """a red/touch mark with only one stroke on it pulls the nearest free stroke end (within reach) onto it, so a stroke stops at its dot instead of short of it"""
    for q in reds:
        mem=[s for s in strokes if min(math.dist(p,q) for p in s["P"])<=R]
        if len(mem)>=2: continue
        c=[(math.dist(s["P"][e],q),s,e) for s in strokes if s not in mem and s["role"] in ("body","second") for e in (0,-1)]
        c=[t for t in c if t[0]<=reach]
        if c:
            d,s,e=min(c,key=lambda t:t[0]); s["P"].insert(0 if e==0 else len(s["P"]),q)

def nearest_red_candidate(j,v): return True

# ---- hand-fitted letters (from the user's zoomed photos): curls/spirals are too fine for the automatic trace ----
HAND={
 "pa":dict(cal=(918,840,830,1690,64.2,12.2,82.1),
  strokes=[("body","s1","U",[(64.2,12.2),(64.2,82.1)],()),
   ("body","s2","P",[(918,840),(924,905),(960,970),(1010,1040),(1080,1100)],()),
   ("second","s3","P",[(888,1125),(800,1030),(720,985),(640,962),(560,965),(500,990),(475,1030),(480,1075),(520,1100),(565,1100),(595,1075),(590,1045),(560,1035),(538,1055),(552,1070)],("end",)),
   ("second","s4","P",[(888,1135),(760,1190),(640,1235),(520,1295),(440,1330)],()),
   ("second","s5","P",[(440,1330),(500,1280),(570,1210),(620,1150),(638,1100),(618,1062),(597,1055)],())],
  J=[("red",[("s1",(888,1130)),("s3","start"),("s4","start")]),("touch",[("s1","start"),("s2","start")]),("touch",[("s4","end"),("s5","start")]),("touch",[("s5","end"),("s3",(597,1055))])]),
 "śa":dict(cal=(885,800,865,1580,54.6,18.2,86.3),
  strokes=[("body","s1","U",[(54.6,18.2),(54.6,86.3)],()),
   ("body","s2","P",[(885,800),(878,870),(940,940),(1010,1010),(1070,1070)],()),
   ("second","s3","P",[(395,1040),(440,1012),(500,990),(550,1010),(580,1060),(595,1120),(598,1170),(570,1215),(530,1245),(490,1240),(463,1215),(480,1190),(500,1195)],("end",)),
   ("second","s4","P",[(868,1020),(800,980),(760,968),(700,990),(650,1030),(625,1090),(620,1150),(650,1190),(690,1190),(710,1165),(695,1145),(675,1160)],("end",))],
  J=[("red",[("s1",(868,1030)),("s4","start")]),("touch",[("s1","start"),("s2","start")]),("touch",[("s3",(615,1150)),("s4",(615,1150))])]),
}
def hand_letter(name):
    h=HAND[name]; tx,ty,bx,by,ux,ty_u,by_u=h["cal"]; k=(by-ty)/(by_u-ty_u)
    def conv(px,py):
        sx=tx+(py-ty)*(bx-tx)/(by-ty); return (round(ux+(px-sx)/k,1),round(ty_u+(py-ty)/k,1))
    st={}; strokes=[]; ends={}
    for role,sid,kind,pts,ball in h["strokes"]:
        P=pts if kind=="U" else [conv(*p) for p in pts]; st[sid]=P; strokes.append([role,path_str(P),sid])
        if ball: ends[sid]=["plain","ball"]
    J=[]
    for t,mem in h["J"]:
        pts=[]; members=[]
        for sid,w in mem:
            P=st[sid]
            if w=="start": q=P[0]
            elif w=="end": q=P[-1]
            else:
                src=next(s for s in h["strokes"] if s[1]==sid); q=w if src[2]=="U" else conv(*w)
            f=nearest(P,q)[1]; members.append({"stroke":sid,"at":round(f,2),"where":"start" if f<0.04 else "end" if f>0.96 else "middle"}); pts.append(q)
        x=sum(p[0] for p in pts)/len(pts); y=sum(p[1] for p in pts)/len(pts)
        J.append({"t":t,"x":round(x,1),"y":round(y,1),"members":members,"loose":len(members)<2})
    return {"glyph":name,"iast":name,"variant":None,"strokes":strokes,"junctions":J,"ends":ends,"_pts":st}
def build_letter(name,v,R=6.0):
    if name in HAND: return hand_letter(name)
    if name=="ṣa": v=dict(v); v["rings"]=list(v["rings"])+[[164.0,223.0,26]]      # the bottom ring was not detected: stem and diagonal meet at it
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
    strokes=patch_strokes(name,strokes,[nm(p[:2]) for p in v["rings"]+v["crosses"]])
    ja_keep=[list(s["P"]) for s in strokes if s["role"]=="second"] if name=="ja" else None
    if name!="ha": straighten(strokes)
    if ja_keep:      # user: ja is the one exception - its green stroke keeps its leftward bend
        for s,P in zip([s for s in strokes if s["role"]=="second"],ja_keep): s["P"]=P
    snap_loose(strokes,[nm(p[:2]) for p in v["reds"]]+[nm(p[:2]) for p in v["rings"]])
    if name!="ha": trim_shadow(strokes)
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
        if kind=="touch" and any(seg_cross(a[0]["P"],b[0]["P"]) and math.dist(a[3],b[3])<R*1.4 and min(a[2],1-a[2])*plen(a[0]["P"])>=4.0 and min(b[2],1-b[2])*plen(b[0]["P"])>=4.0 for ai,a in enumerate(mem) for b in mem[ai+1:]): kind="cross"      # a cross needs BOTH strokes to run on past it (an end that overshoots is a touch)
        # junction position: mean of the closest points
        x=float(np.mean([c[3][0] for c in mem])); y=float(np.mean([c[3][1] for c in mem]))
        J.append({"t":kind,"x":round(x,1),"y":round(y,1),"members":[{"stroke":s["id"],"at":round(t,2),"where":"start" if t<0.07 else "end" if t>0.93 else "middle"} for s,d,t,c in mem],"loose":len(mem)<2})
    # hand corrections from the user's review
    for j in J:
        if name=="gha" and j["t"]=="red" and 28<j["y"]<52 and j["x"]<45: j["t"]="touch"          # user: the red dot in the middle of the blue strokes is just an orange circle
        if name in ("ma","bha","pha","ū") and j["t"]=="cross": j["t"]="touch"                       # user: these letters have only rings, no crosses
        if name in ("ga","ṇa") and j["t"]=="touch" and any(m["where"]=="middle" for m in j["members"]) and j["t"]!="red" and nearest_red_candidate(j,v): j["t"]="red"
    if name=="ha":
        # user: ha is ONE continuous blue stroke that crosses itself once (the orange X): down the stem, round the small left loop, back across the stem, over the big arc to the bottom-left ring.
        bar=next(s for s in strokes if s["role"]=="struct"); tail=max((s for s in strokes if s["role"]=="body"),key=lambda s:s["P"][0][0])
        main=[(42.4,27.6),(41.5,33.5),(40.8,40.2),(38.4,47.0),(33.5,54.5),(29.0,57.4),(27.0,55.6),(27.8,49.5),(32.0,44.2),(36.5,42.2),(41.5,41.0),(46.0,40.8),(51.0,41.6),(55.8,44.6),(58.8,49.8),(59.4,56.0),(56.4,62.4),(48.6,67.9),(41.0,73.0),tail["P"][-1]]
        ms={"role":"body","P":main,"id":"s2"}; tl={"role":"body","P":tail["P"],"id":"s3"}; bar["id"]="s1"
        def at(P,q): d,t,i,c=nearest(P,q); return round(t,2)
        # the self-crossing: where the return path (fraction ~0.5) meets the stem (fraction ~0.2)
        X=(40.9,41.0); tip=main[-1]
        J=[{"t":"red","x":42.4,"y":27.8,"members":[{"stroke":"s1","at":at(bar["P"],(42.4,28.1)),"where":"middle"},{"stroke":"s2","at":0.0,"where":"start"}],"loose":False},
           {"t":"cross","x":X[0],"y":X[1],"members":[{"stroke":"s2","at":0.2,"where":"middle"},{"stroke":"s2","at":0.5,"where":"middle"}],"loose":False},
           {"t":"touch","x":round(tip[0],1),"y":round(tip[1],1),"members":[{"stroke":"s2","at":1.0,"where":"end"},{"stroke":"s3","at":1.0,"where":"end"}],"loose":False}]
        # exact fractions of the two crossing passes along the stroke
        tot=plen(main); acc=0; fr=[]
        for p,q in zip(main,main[1:]):
            acc+=math.dist(p,q); fr.append(acc/tot)
        J[1]["members"][0]["at"]=round(nearest(main[:4],X)[1]*plen(main[:4])/tot,2); 
        k=nearest(main[8:12],X); J[1]["members"][1]["at"]=round((sum(math.dist(main[m],main[m+1]) for m in range(8))+k[1]*plen(main[8:12]))/tot,2)
        strokes=[bar,ms,tl]
    if name=="ṅa":      # user's drawing has ONE orange X here: drop the ring fragments next to it
        cx=[j for j in J if j["t"]=="cross"]
        J=[j for j in J if j["t"]=="cross" or not any(math.dist((j["x"],j["y"]),(c["x"],c["y"]))<14 for c in cx)]
    if name=="ṅa":
        # user's zoomed photo: ONE blue stroke with ONE orange X: in from the left, over the small loop, back down through the X and round the big arc.
        s1=next(s for s in strokes if s["P"][0][0]<30 and s["P"][-1][1]>35)
        arc=[p for p in s1["P"] if p[1]>=38.4 and p[0]>46.5]; tail=s1["P"][s1["P"].index(arc[0]):] if arc else s1["P"][-8:]
        C,D=(41.0,29.6),(52.8,27.4); A,B=(50.0,24.5),(44.8,33.5)
        den=(C[0]-D[0])*(A[1]-B[1])-(C[1]-D[1])*(A[0]-B[0])
        t=((C[0]-A[0])*(A[1]-B[1])-(C[1]-A[1])*(A[0]-B[0]))/den; X=(C[0]+t*(D[0]-C[0]),C[1]+t*(D[1]-C[1]))
        main=[(27.0,25.5),(33.9,27.8),C,D,(57.8,26.5),(61.0,23.2),(61.5,20.9),(60.6,19.6),(55.5,19.6),(52.3,22.3),A,B,(47.2,38.4)]+tail
        tot=plen(main); cum=lambda k: sum(math.dist(main[m],main[m+1]) for m in range(k))
        fa=(cum(2)+t*math.dist(C,D))/tot; fb=(cum(10)+math.dist(A,X))/tot
        strokes=[{"role":"body","P":main,"id":"s1","ball":set(s1.get("ball",set()))}]
        J=[{"t":"cross","x":round(X[0],1),"y":round(X[1],1),"members":[{"stroke":"s1","at":round(fa,2),"where":"middle"},{"stroke":"s1","at":round(fb,2),"where":"middle"}],"loose":False}]
        ends={k:v_ for k,v_ in ends.items() if k=="s1"}
    if name in ("i","ī"):
        stub=[s for s in strokes if s["role"]=="struct" and s["P"][0][0]==s["P"][-1][0]]
        if stub:
            T=min(stub[0]["P"],key=lambda p:p[1]); bar=next(s for s in strokes if s["role"]=="struct" and s is not stub[0])
            J=[j for j in J if math.dist((j["x"],j["y"]),T)>9.0]
            J.append({"t":"touch","x":round(T[0],1),"y":round(T[1],1),"members":[{"stroke":bar["id"],"at":round(nearest(bar["P"],T)[1],2),"where":"middle"},{"stroke":stub[0]["id"],"at":0.0,"where":"start"}],"loose":False})
    if name in ("ī","ṇa"):      # ha is the only Bengali letter whose stroke crosses ITSELF; ṅa has a real cross between two strokes.  In ī and ṇa the crosses are ring fragments: make them rings and merge rings closer than 4 units
        for j in J:
            if j["t"]=="cross": j["t"]="touch"
        merged=[]
        for j in J:
            for m in merged:
                if m["t"]==j["t"]=="touch" and math.dist((m["x"],m["y"]),(j["x"],j["y"]))<4.0:
                    seen={(x["stroke"],x["where"]) for x in m["members"]}
                    m["members"]+=[x for x in j["members"] if (x["stroke"],x["where"]) not in seen]; m["loose"]=len(m["members"])<2; break
            else: merged.append(j)
        J=merged
    ends={s["id"]:sorted(s["ball"]) for s in strokes if s.get("ball")}
    return {"glyph":name,"iast":name,"variant":None,"strokes":[[s["role"],path_str(s["P"]),s["id"]] for s in strokes],"junctions":J,"ends":{k:["ball" if x else "plain" for x in (("start" in v_),("end" in v_))] for k,v_ in ends.items()},"_pts":{s["id"]:s["P"] for s in strokes}}
if __name__=="__main__":
    raw=json.load(open(sys.argv[1])); out=[build_letter(n,v) for n,v in raw.items()]
    json.dump(out,open(sys.argv[2],"w"),ensure_ascii=False)
    for l in out: print(l["glyph"],len(l["strokes"]),"J",len(l["junctions"]),"loose",sum(j["loose"] for j in l["junctions"]),end=" | ")
