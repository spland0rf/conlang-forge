import cv2, sys
A="/mnt/user-data/attachments/9df3cbd6-5590-5857-9ad9-4bf9abf1a96b/"
def gv(f,y0,y1,x0=0,x1=None,step=50):
    im=cv2.imread(A+f+"-image.jpg"); x1=x1 or im.shape[1]; c=im[y0:y1,x0:x1].copy()
    for x in range((x0//step+1)*step,x1,step):
        cv2.line(c,(x-x0,0),(x-x0,c.shape[0]),(150,150,150) if x%100 else (90,90,255),1)
        if x%100==0: cv2.putText(c,str(x),(x-x0+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,0,200),1)
    for y in range((y0//step+1)*step,y1,step):
        cv2.line(c,(0,y-y0),(c.shape[1],y-y0),(150,150,150) if y%100 else (90,90,255),1)
        if y%100==0: cv2.putText(c,str(y),(2,y-y0-3),cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,0,200),1)
    o="%s_%d_%d_%d.png"%(f,y0,y1,x0); cv2.imwrite(o,c); return o
if __name__=="__main__":
    f,y0,y1=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]); x0=int(sys.argv[4]) if len(sys.argv)>4 else 0; x1=int(sys.argv[5]) if len(sys.argv)>5 else None
    print(gv(f,y0,y1,x0,x1))
