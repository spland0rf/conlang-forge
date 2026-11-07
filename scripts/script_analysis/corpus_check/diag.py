import pickle, collections
from corpus_load import records
import sig as SG, compound_gen as C, repair as RP
from repair_corpus import inside
R=C.R
res=pickle.load(open('repair_res.pkl','rb'))
stuck=[r for r,N,h in res if h!='ok' and N is None]
tot=collections.Counter(); first=collections.Counter()
for r in stuck:
    if not any(j[0]=="red" for j in r["J"]): continue
    s0=SG.sig(SG.letter_strokes(r)); per=collections.Counter()
    opts=[(0,"anchor"),(15,"anchor"),(-15,"anchor")]+([(0,"stem"),(0,"stemL")] if r["sk"]["kind"]=="stem" else [])
    ay=next(j[2] for j in r["J"] if j[0]=="red"); ymax=max(p[1] for P in r["strokes"] for p in P); gmax=max(1.0,(90.0-ay)/max(ymax-ay,1.0))
    for f in [1.0]+RP.FAST_SCALES:
        for g in sorted({1.0,min(f,gmax),min(1.25*f,gmax),min(1.5*f,gmax)}):
            if f==1.0 and g==1.0: continue
            for dx,pv in opts:
                N=RP.transform(r,f,g,dx,"stem" if pv.startswith("stem") else pv,1.0 if pv=="stemL" else None)
                if C.primary_size(N)<R["PRIMARY_MIN"]: per["primary"]+=1; continue
                if not inside(N, r): per["outside"]+=1; continue
                if C.white_fraction(N)>R["WHITE_MAX"]: per["white"]+=1; continue
                if N["sk"]["kind"] in("stem","desc") and C.max_void(N)>R["MAX_VOID"]: per["void"]+=1; continue
                if SG.sig(SG.letter_strokes(N))!=s0: per["sig"]+=1; continue
                per["ok"]+=1
    tot+=per; first[per.most_common(1)[0][0]]+=1
print(len(stuck),"stuck; most common blocker per letter:",dict(first)); print("all candidates:",dict(tot))
