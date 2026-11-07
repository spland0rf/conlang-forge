import sys, math, numpy as np
sys.path.insert(0,'.')
import slide_check as S
from slide_check import real, gen, thin, plen, R
def pts(P): return np.array([p for s in P for p in thin(s, 2.0)])
def dd(A,B):
    d=np.sqrt(((A[:,None,:]-B[None,:,:])**2).sum(-1)); return d.min(1)
def haus(A,B,q=97): return max(np.percentile(dd(A,B),q), np.percentile(dd(B,A),q))
def prep(L):
    body,rest=L; return (pts(body) if body else np.zeros((0,2)), pts(rest) if rest else np.zeros((0,2)), (sum(plen(P) for P in body)/len(body)) if body else 0)
def dist(X,Y,slide=True):
    xb,xr,xl=X; yb,yr,yl=Y
    base=haus(np.vstack([xb,xr]),np.vstack([yb,yr]))
    if not slide or len(xb)==0: return base
    s=R["ATTACH_SLIDE_TOL"]*xl; best=base
    for dx in (-s,-s/2,0,s/2,s):
        for dy in (-s,-s/2,0,s/2,s):
            best=min(best,haus(np.vstack([xb+[dx,dy],xr]),np.vstack([yb,yr])))
    return best
def sym(X,Y): return min(dist(X,Y),dist(Y,X))
if __name__=="__main__":
    RL={k:prep(v) for k,v in real().items()}; GL={k:prep(v) for k,v in gen().items()}
    keep=["A3","A6","A11","A17","A20","A21","A22","A24","A25","A26","A29","A30","A31"]
    ks=list(RL); rp=[]
    for i,a in enumerate(ks):
        for b in ks[i+1:]: rp.append((sym(RL[a],RL[b]),a,b))
    rp.sort(); print("closest real pairs:",[(round(d,1),a,b) for d,a,b in rp[:14]])
    print("A28 vs real:",sorted((round(sym(GL['A28'],v),1),k) for k,v in RL.items())[:3])
    kr=sorted((round(min(sym(GL[a],v) for v in RL.values()),1),a,min(RL,key=lambda k:sym(GL[a],RL[k]))) for a in keep); print("keeper->nearest real:",kr[:6])
    kk=sorted((round(sym(GL[a],GL[b]),1),a,b) for i,a in enumerate(keep) for b in keep[i+1:]); print("keeper pairs:",kk[:8])
