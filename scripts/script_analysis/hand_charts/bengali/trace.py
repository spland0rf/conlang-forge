import cv2, numpy as np, math
from skimage.morphology import skeletonize
from grid import *
NB=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
def rdp(P,eps):
    if len(P)<3: return P
    a=np.array(P[0]);b=np.array(P[-1]);ab=b-a;n=np.linalg.norm(ab)
    d=[abs(ab[0]*(p[1]-a[1])-ab[1]*(p[0]-a[0]))/n if n>0 else np.linalg.norm(np.array(p)-a) for p in P[1:-1]]
    k=int(np.argmax(d))
    if d[k]>eps: return rdp(P[:k+2],eps)[:-1]+rdp(P[k+1:],eps)
    return [P[0],P[-1]]
def skel_graph(sk):
    """Return list of edges (pixel paths) between nodes (deg!=2) of a skeleton image."""
    ys,xs=np.nonzero(sk); S=set(zip(ys.tolist(),xs.tolist()))
    def nbrs(p): return [(p[0]+dy,p[1]+dx) for dy,dx in NB if (p[0]+dy,p[1]+dx) in S]
    deg={p:len(nbrs(p)) for p in S}
    nodes={p for p,d in deg.items() if d!=2}
    seen=set(); edges=[]
    for n0 in nodes:
        for q in nbrs(n0):
            if (n0,q) in seen: continue
            path=[n0,q]; prev=n0; cur=q
            while cur not in nodes:
                nx=[r for r in nbrs(cur) if r!=prev]
                if not nx: break
                prev,cur=cur,nx[0]; path.append(cur)
            seen.add((n0,q)); seen.add((cur,path[-2]))
            edges.append(path)
    # isolated loops (no nodes)
    return edges,deg
def prune(sk,minlen):
    """remove spurs (edges ending in a degree-1 pixel that are shorter than minlen)"""
    for _ in range(3):
        edges,deg=skel_graph(sk); ch=False
        for e in edges:
            if len(e)<minlen and (deg[e[0]]==1 or deg[e[-1]]==1) and (deg[e[0]]>2 or deg[e[-1]]>2):
                for p in e[1:-1] if deg[e[0]]>2 and deg[e[-1]]>2 else (e[:-1] if deg[e[0]]==1 else e[1:]): sk[p]=0
                ch=True
        if not ch: break
    return sk
def tang(path,end,k=7):
    """unit direction leaving `end` (0 or -1) along the path"""
    pts=path if end==0 else path[::-1]; q=pts[min(k,len(pts)-1)]; p=pts[0]
    v=np.array([q[1]-p[1],q[0]-p[0]],float); n=np.linalg.norm(v); return v/n if n else v
def pair_edges(edges,deg):
    """merge edges that meet at nodes: at degree-2/3/4 nodes join straightest pairs (angle<40deg)"""
    by_node={}
    for i,e in enumerate(edges):
        for end in (0,-1): by_node.setdefault(e[end],[]).append((i,end))
    link={}   # (edge,end)->(edge,end)
    for node,lst in by_node.items():
        if len(lst)<2: continue
        cand=[]
        for a in range(len(lst)):
            for b in range(a+1,len(lst)):
                (i,ei),(j,ej)=lst[a],lst[b]
                if i==j: continue
                ta,tb=tang(edges[i],ei),tang(edges[j],ej); cosang=float(np.dot(ta,tb))      # straight continuation = tangents opposite (-1)
                cand.append((cosang,lst[a],lst[b]))
        cand.sort(key=lambda t:t[0]); used=set()
        for cosang,A,B in cand:
            if cosang>-0.62: break                    # more than ~52 degrees off straight: not a continuation
            if A in used or B in used: continue
            link[A]=B; link[B]=A; used.add(A); used.add(B)
    return link
def merge(edges,link):
    used=set(); strokes=[]
    for i in range(len(edges)):
        if i in used: continue
        # walk backwards to the start of the chain
        cur=(i,0); 
        # find chain start
        start=(i,0); seenc=set([i])
        while start in link:
            j,ej=link[start]
            if j in seenc: break
            seenc.add(j); start=(j,1-0 if ej==0 else 0) if False else (j,(-1 if ej==0 else 0)); 
        # now walk forward from `start` (leaving through the opposite end of start's edge)
        path=[]; e,ent=start; guard=0
        while True:
            used.add(e); P=edges[e]; 
            seg=P if ent==0 else P[::-1]
            path+=seg if not path else seg[1:]
            exit_end=-1 if ent==0 else 0
            nxt=link.get((e,exit_end))
            if not nxt or nxt[0] in used: break
            e,ent_=nxt; ent=0 if ent_==0 else -1; guard+=1
            if guard>60: break
        strokes.append(path)
    return strokes
FIRED=[]
def acute_tips(edges,deg,hints,maxstub=45):
    """An orange ring marks two strokes meeting at a very acute tip.  Their fused ink skeletonises as a short stub (tip end of degree 1) running to a
    degree-3 node: three branches that look like one fork.  Replace stub + the two arms by ONE stroke that goes arm A -> tip -> arm B."""
    for hx,hy,*r in hints:
        if (hx,hy) in FIRED: continue
        R=max(r[0]/2 if r else 0,8)+14
        for si,s in enumerate(edges):
            for tip_end in (0,-1):
                tip=s[tip_end]; node=s[-1 if tip_end==0 else 0]
                if deg.get(tip)!=1 or deg.get(node) not in (3,4) or len(s)>maxstub or math.dist((tip[1],tip[0]),(hx,hy))>R: continue
                arms=[(i,e) for i,x in enumerate(edges) if i!=si for e in (0,-1) if x[e]==node]
                if len(arms)!=2: continue
                (ia,ea),(ib,eb)=arms
                if ia==ib: continue
                if float(np.dot(tang(edges[ia],ea,12),tang(edges[ib],eb,12)))<0.15: continue      # a tangent tip: both arms leave the node on the same side
                A=edges[ia] if ea==-1 else edges[ia][::-1]      # arm A running INTO the node
                B=edges[ib] if eb==0 else edges[ib][::-1]       # arm B running OUT of the node
                stub=s if tip_end==-1 else s[::-1]              # node -> tip ... ; build node->tip
                stub=stub[::-1] if stub[0]!=node else stub
                tipp=stub[-1]; cut=len(stub)+6                                  # two strokes meeting at the tip, as a thin V: each arm is trimmed back past the fused stub, then runs straight to the tip
                def trim(P,keep_end):
                    P=list(P); n=0
                    while len(P)>3 and n<cut:
                        n+=1; (P.pop() if keep_end else P.pop(0))
                    return P
                A2=trim(A,True)+[tipp]; B2=[tipp]+trim(B,False)
                # the fused stub is shared by both arms: let the less-straight arm LEAVE THE TIP at once, so the two strokes touch only at the tip (no shared run)
                uv=np.array([node[0]-tipp[0],node[1]-tipp[1]],float); uv/=max(np.linalg.norm(uv),1e-6)
                def away(P,k): v=np.array([P[min(k,len(P)-1)][0]-tipp[0],P[min(k,len(P)-1)][1]-tipp[1]],float); return v/max(np.linalg.norm(v),1e-6)
                Aout=A2[::-1]; Bout=B2
                if float(np.dot(away(Aout,cut+4),uv))>=float(np.dot(away(Bout,cut+4),uv)): stem,other,flip=Aout,Bout,False
                else: stem,other,flip=Bout,Aout,True
                su=away(stem,cut+4)
                for j in range(1,len(other)):
                    v=np.array([other[j][0]-tipp[0],other[j][1]-tipp[1]],float); d=np.linalg.norm(v)
                    if d>=cut+4 and abs(su[0]*v[1]-su[1]*v[0])>=0.3*d: other=[tipp]+other[j:]; break
                if flip: A2=other[::-1]
                else: B2=other
                for k in sorted({si,ia,ib},reverse=True): edges.pop(k)
                edges.append(A2); edges.append(B2); deg[tipp]=2; FIRED.append((hx,hy)); return True
    return False
def trace_mask(m,close=9,prune_len=10,hints=None):
    m=cv2.morphologyEx((m>0).astype(np.uint8),cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(close,close)))
    m=cv2.dilate(m,np.ones((3,3),np.uint8))
    sk=skeletonize(m>0).astype(np.uint8); sk=prune(sk,prune_len)
    edges,deg=skel_graph(sk)
    for _ in range(6):
        if not (hints and acute_tips(edges,deg,hints)): break
    link=pair_edges(edges,deg); strokes=merge(edges,link)
    return [[(float(p[1]),float(p[0])) for p in s] for s in strokes if len(s)>=8]
