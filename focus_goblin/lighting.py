"""Face-weighted tone mapping changes image pixels, never room/screen brightness."""
import math


class FaceLighting:
    def __init__(self): self.gamma = 1.; self.roi = None; self.level = 128.

    def correct(self,frame,target=128,enabled=True):
        import cv2
        import numpy as np
        if not enabled: return frame.copy()
        h,w = frame.shape[:2]
        x1,y1,x2,y2 = self.roi or (int(w*.25),int(h*.18),int(w*.75),int(h*.85))
        roi = frame[max(0,y1):min(h,y2),max(0,x1):min(w,x2)]
        if roi.size == 0: roi = frame
        self.level = float(np.median(cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY)))
        desired = math.log(max(1,min(254,target))/255)/math.log(max(2,min(253,self.level))/255)
        self.gamma += (max(.55,min(1.8,desired))-self.gamma)*.12
        lut = np.clip((np.arange(256)/255.)**self.gamma*255,0,255).astype(np.uint8)
        lab = cv2.cvtColor(cv2.LUT(frame,lut),cv2.COLOR_BGR2LAB)
        lab[:,:,0] = cv2.createCLAHE(clipLimit=1.5,tileGridSize=(8,8)).apply(lab[:,:,0])
        return cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)

    def update_face(self,landmarks,width,height):
        xs=[p.x for p in landmarks]; ys=[p.y for p in landmarks]
        self.roi=(int(min(xs)*width),int(min(ys)*height),int(max(xs)*width),int(max(ys)*height))
