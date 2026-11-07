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
def trace_mask(m,close=9,prune_len=10):
    m=cv2.morphologyEx((m>0).astype(np.uint8),cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(close,close)))
    m=cv2.dilate(m,np.ones((3,3),np.uint8))
    sk=skeletonize(m>0).astype(np.uint8); sk=prune(sk,prune_len)
    edges,deg=skel_graph(sk)
    link=pair_edges(edges,deg); strokes=merge(edges,link)
    return [[(float(p[1]),float(p[0])) for p in s] for s in strokes if len(s)>=8]
