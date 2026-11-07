import cv2, numpy as np
ROWS=[33,301,551,808,1069,1330,1592,1853,2112]; COLS=[71,329,587,848,1108,1366,1633]
NAMES="a ā i ī u ū ṛ e ai o au ka kha ga gha ṅa ca cha ja jha ña ṭa ṭha ḍa ḍha ṇa ta tha da dha na pa pha ba bha ma ya ra la va śa ṣa sa ha".split()
SWAPS=[("ṭa","ṭha"),("va","śa")]       # the user swapped these drawings between cells (two-headed arrows)
def cell_box(i,inset=7):
    r,c=divmod(i,6); return COLS[c]+inset,ROWS[r]+inset,COLS[c+1]-inset,ROWS[r+1]-inset
def page_masks(im):
    """Classify ink pixels of the whole page: darker than the local paper, then by colour."""
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY); bg=cv2.medianBlur(g,51); dark=cv2.subtract(bg,g).astype(int)
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV); H,S,V=[hsv[...,k].astype(int) for k in range(3)]
    B,G,R=[im[...,k].astype(int) for k in range(3)]
    ink=dark>22; weak=dark>9
    m={}
    m["red"]=ink&(R>G+60)&(R>B+60)&((H<7)|(H>=165))&(S>110)
    m["orange"]=ink&(R>B+50)&(R>G+15)&(H>=7)&(H<=26)&(S>80)&~m["red"]
    m["blue"]=(S>38)&(H>=92)&(H<=126)&(B>R+12)&(V<235)
    m["green"]=(S>38)&(H>=28)&(H<=85)&(G>R+3)&(G>B+8)&(V<235)
    m["purple"]=ink&(S>25)&(S<100)&(B>G+4)&(R>G+4)&~m["red"]&~m["orange"]&~m["blue"]&~m["green"]
    return {k:v.astype(np.uint8) for k,v in m.items()}

def clean(mask, close=2, minarea=12):
    k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)); m=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,k,iterations=close)
    n,lab,st,_=cv2.connectedComponentsWithStats(m,8)
    keep=np.zeros_like(m)
    for i in range(1,n):
        if st[i,4]>=minarea: keep[lab==i]=1
    return keep


def lab_masks(im):
    """Ink classes from Lab colour relative to the local paper (robust to uneven lighting)."""
    lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)
    bg=np.stack([cv2.medianBlur(lab[...,k].astype(np.uint8),61).astype(np.float32) for k in range(3)],-1)
    d=lab-bg; L,a,b=d[...,0],d[...,1],d[...,2]; ch=np.hypot(a,b)
    ink=(L<-22)
    m={}
    m["red"]=ink&(a>16)&(L<-70)&(b>-8)
    m["green"]=ink&(a<-7)&(b>8)
    m["blue"]=(L<-13)&(b<-8)&(a<5)&(a>-22)
    m["orange"]=(L<-12)&(a>3)&(b>12)&~m["red"]
    m["purple"]=ink&(a>4)&(b<6)&(b>-12)&(ch>6)&~m["red"]&~m["blue"]
    return {k:cv2.morphologyEx(v.astype(np.uint8),cv2.MORPH_OPEN,np.ones((2,2),np.uint8)) for k,v in m.items()}


from skimage.filters import apply_hysteresis_threshold as _hyst
def soft_masks(im):
    """Hysteresis version of lab_masks: faint pixels count when connected to confident ones."""
    lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)
    bg=np.stack([cv2.medianBlur(lab[...,k].astype(np.uint8),61).astype(np.float32) for k in range(3)],-1)
    d=lab-bg; L,a,b=d[...,0],d[...,1],d[...,2]
    m=lab_masks(im)
    dark=(L<-9)
    blue_s=np.where(dark&(a<6)&(a>-24),-b,0); blue_s=np.maximum(blue_s,np.where((L<-50)&(b<-4)&(a<6)&(a>-24),9,0)); green_s=np.where(dark&(a<-2),b,0); purple_s=np.where(dark&(a>2)&(b<8)&(b>-14),a,0)
    out=dict(m)
    out["blue"]=_hyst(blue_s,7,13).astype(np.uint8)&(~(m["green"]>0)).astype(np.uint8)
    out["green"]=_hyst(green_s,8,15).astype(np.uint8)
    out["purple"]=_hyst(purple_s,4.5,8).astype(np.uint8)&(~(m["blue"]>0)).astype(np.uint8)
    orange_s=np.where((L<-8)&(a>2)&(b>7)&(a<30),b,0)
    out["orange"]=_hyst(orange_s,10,17).astype(np.uint8)&(~(m["red"]>0)).astype(np.uint8)
    return out
