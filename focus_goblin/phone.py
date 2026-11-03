"""OpenCV Darknet class scores already include objectness; never multiply twice."""
import sys
from pathlib import Path


def find_phone_model(selected='',prefer_eco=False):
    if selected and Path(selected).is_file(): return Path(selected)
    for base in (Path(sys.executable).parent,Path(__file__).resolve().parent.parent):
        modern=base/'models'/'phone-yolox.onnx'
        if modern.is_file() and not prefer_eco:return modern
        path = base/'models'/'yolov4-tiny.weights'
        if path.is_file() and path.with_suffix('.cfg').is_file(): return path
    return None


class TinyPhoneDetector:
    def __init__(self, weights, confidence=.25, size=416):
        import cv2
        config = Path(weights).with_suffix('.cfg')
        if not config.is_file():
            raise FileNotFoundError('YOLOv4-tiny needs its matching .cfg beside the .weights file')
        self.net = cv2.dnn.readNetFromDarknet(str(config),str(weights))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.layers = self.net.getUnconnectedOutLayersNames()
        self.confidence = confidence; self.size = size

    @staticmethod
    def decode(outputs, width, height, scale, pad_x, pad_y, size, threshold):
        import cv2
        import numpy as np
        boxes,confidences = [],[]; peak = 0.
        for output in outputs:
            for row in output:
                if len(row) < 85 or int(np.argmax(row[5:])) != 67: continue
                confidence = float(row[5+67]); peak = max(peak,confidence)
                if confidence < threshold: continue
                cx,cy,bw,bh = [float(v)*size for v in row[:4]]
                x1 = max(0,int((cx-bw/2-pad_x)/scale)); y1 = max(0,int((cy-bh/2-pad_y)/scale))
                x2 = min(width,int((cx+bw/2-pad_x)/scale)); y2 = min(height,int((cy+bh/2-pad_y)/scale))
                if x2 > x1 and y2 > y1:
                    boxes.append([x1,y1,x2-x1,y2-y1]); confidences.append(confidence)
        indices = cv2.dnn.NMSBoxes(boxes,confidences,threshold,.4) if boxes else []
        return {'score':peak,'boxes':[(boxes[int(i)],confidences[int(i)]) for i in np.array(indices).flatten()], 'visible':len(indices)>0}

    def detect(self,frame):
        import cv2
        import numpy as np
        height,width = frame.shape[:2]; scale = self.size/max(width,height)
        nw,nh = round(width*scale),round(height*scale)
        x,y = (self.size-nw)//2,(self.size-nh)//2
        canvas = np.full((self.size,self.size,3),114,dtype=np.uint8)
        canvas[y:y+nh,x:x+nw] = cv2.resize(frame,(nw,nh))
        self.net.setInput(cv2.dnn.blobFromImage(canvas,1/255.,(self.size,self.size),swapRB=True,crop=False))
        return self.decode(self.net.forward(self.layers),width,height,scale,x,y,self.size,self.confidence)

    def predict_phone(self,frame): return self.detect(frame)['visible']


class YoloXPhoneDetector:
    """YOLOX-S COCO through OpenCV; no PyTorch or runtime model download."""
    def __init__(self,path,confidence=.25):
        import cv2
        import numpy as np
        self.net=cv2.dnn.readNetFromONNX(str(path));self.confidence=confidence
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV);self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        grids=[];strides=[]
        for stride in (8,16,32):
            y,x=np.mgrid[:640//stride,:640//stride]
            grids.append(np.stack((x,y),axis=-1).reshape(-1,2));strides.append(np.full((x.size,1),stride))
        self.grid=np.concatenate(grids);self.strides=np.concatenate(strides)

    def detect(self,frame):
        import cv2
        import numpy as np
        h,w=frame.shape[:2];scale=640/max(h,w)
        canvas=np.full((640,640,3),114,dtype=np.float32)
        nh,nw=int(h*scale),int(w*scale)
        canvas[:nh,:nw]=cv2.cvtColor(cv2.resize(frame,(nw,nh)),cv2.COLOR_BGR2RGB)
        self.net.setInput(canvas.transpose(2,0,1)[None])
        output=self.net.forward()[0]
        centers=(output[:,:2]+self.grid)*self.strides
        sizes=np.exp(np.clip(output[:,2:4],-20,20))*self.strides
        scores=output[:,4:5]*output[:,5:]
        mask=np.argmax(scores,axis=1)==67;phone_scores=scores[:,67]
        peak=float(np.max(phone_scores[mask])) if np.any(mask) else 0.
        indices=np.flatnonzero(mask & (phone_scores>=self.confidence))
        boxes=[];conf=[]
        for i in indices:
            x1,y1=(centers[i]-sizes[i]/2)/scale;x2,y2=(centers[i]+sizes[i]/2)/scale
            x1,y1=max(0,int(x1)),max(0,int(y1));x2,y2=min(w,int(x2)),min(h,int(y2))
            if x2>x1 and y2>y1:boxes.append([x1,y1,x2-x1,y2-y1]);conf.append(float(phone_scores[i]))
        keep=cv2.dnn.NMSBoxes(boxes,conf,self.confidence,.45) if boxes else []
        return {'score':peak,'boxes':[(boxes[int(i)],conf[int(i)]) for i in np.array(keep).flatten()],'visible':len(keep)>0}

    def predict_phone(self,frame):return self.detect(frame)['visible']
