import sys,cv2,numpy as np,importlib
import hf
for m in sys.argv[2:]: importlib.import_module(m)
names=sys.argv[1].split(",")
tiles=[]
for n in names:
    p=hf.overlay(n); t=cv2.imread(p); t=cv2.resize(t,(520,520)); tiles.append(t)
while len(tiles)%3: tiles.append(np.full((520,520,3),255,np.uint8))
rows=[np.hstack(tiles[i:i+3]) for i in range(0,len(tiles),3)]
cv2.imwrite("sheet.png",np.vstack(rows))
