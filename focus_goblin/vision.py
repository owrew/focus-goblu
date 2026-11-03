"""Camera and models live on a worker; a single pending image bounds UI memory."""
import os
import threading
import time
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from .engine import Observation


class PhoneWorker(threading.Thread):
    """One pending frame. Heavy phone inference cannot block face updates."""
    def __init__(self, model, confidence, status):
        super().__init__(daemon=True,name='FocusGoblinPhone')
        self.model = model; self.confidence = confidence; self.status = status
        self.lock = threading.Lock(); self.stopping = threading.Event()
        self.frame = None; self.result = (False,0.)
        self.details = {'score':0.,'boxes':[],'visible':False}

    def submit(self,frame):
        with self.lock: self.frame = frame

    def visible(self):
        with self.lock: visible,stamp = self.result
        return visible and time.monotonic()-stamp < 4

    def detection(self):
        with self.lock:
            return dict(self.details) if time.monotonic()-self.result[1] < 4 else {'score':0.,'boxes':[],'visible':False}

    def run(self):
        while not self.stopping.is_set():
            with self.lock: frame,self.frame = self.frame,None
            if frame is None:
                self.stopping.wait(.05); continue
            try:
                if hasattr(self.model,'detect'):
                    details = self.model.detect(frame); visible = details['visible']
                elif hasattr(self.model,'predict_phone'):
                    visible = self.model.predict_phone(frame); details = {'score':float(visible),'boxes':[],'visible':visible}
                else:
                    predictions = self.model.predict(frame,imgsz=320,device='cpu',classes=[67],conf=self.confidence,verbose=False)
                    visible = any(len(p.boxes) for p in predictions)
                    details = {'score':max([float(b.conf[0]) for p in predictions for b in p.boxes] or [0]),'boxes':[],'visible':visible}
                with self.lock: self.result = (bool(visible),time.monotonic()); self.details = details
            except Exception as exc:
                self.status.emit(f'Phone detector disabled: {exc}')
                with self.lock: self.result = (False,0.)
                break
            self.stopping.wait(.8)

    def stop(self):
        self.stopping.set()
        with self.lock: self.frame = None; self.result = (False,0.)


class VisionWorker(QThread):
    status = Signal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.latest = None

    def take(self):
        with self.lock:
            result, self.latest = self.latest, None
        return result

    def run(self):
        cap = mesh = phone_worker = None
        try:
            import cv2
            import mediapipe as mp
            cv2.setNumThreads(1)
            s = self.settings
            from .lighting import FaceLighting
            from .phone import find_phone_model
            lighting = FaceLighting(); smooth = None
            mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True,
                min_detection_confidence=.6, min_tracking_confidence=.6)
            phone_model = None
            selected = find_phone_model(s.phone_model if s.phone_backend=='Custom' else '',s.phone_backend=='Eco YOLOv4') if s.phone_enabled else None
            if selected:
                try:
                    # Require an existing path: runtime never auto-downloads weights.
                    if not Path(selected).is_file():
                        raise FileNotFoundError("Select an existing local .pt model")
                    os.environ["YOLO_OFFLINE"] = "true"
                    os.environ["YOLO_AUTOINSTALL"] = "false"
                    if Path(selected).suffix == '.onnx':
                        from .phone import YoloXPhoneDetector
                        phone_model=YoloXPhoneDetector(selected,s.phone_confidence)
                    elif Path(selected).suffix == '.weights':
                        from .phone import TinyPhoneDetector
                        phone_model = TinyPhoneDetector(selected,s.phone_confidence,s.phone_size)
                    else:
                        from ultralytics import YOLO
                        phone_model = YOLO(str(selected))
                except Exception as exc:
                    self.status.emit(f"Phone detection unavailable: {exc}")
            cap = cv2.VideoCapture(s.camera, cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY)
            w, h = map(int, s.resolution.split("x"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            cap.set(cv2.CAP_PROP_FPS, s.fps)
            exposure_ok=cap.set(cv2.CAP_PROP_AUTO_EXPOSURE,1. if os.name=='nt' else .75) if s.camera_auto_exposure else False
            if not cap.isOpened():
                raise RuntimeError("Camera unavailable. Check Windows camera permissions or close other camera apps.")
            actual = f"{int(cap.get(3))}×{int(cap.get(4))}"
            phone_state = f'ready ({Path(selected).name})' if phone_model else 'missing model' if s.phone_enabled else 'disabled'
            self.status.emit(f"Camera active · {actual} · phone {phone_state} · driver exposure {'accepted' if exposure_ok else 'unchanged / unsupported'}")
            if phone_model:
                phone_worker = PhoneWorker(phone_model,s.phone_confidence,self.status); phone_worker.start()
            while not self.stop_event.is_set():
                began = time.monotonic()
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Camera stopped delivering frames")
                small = cv2.resize(frame, (640, 360))
                corrected = lighting.correct(small,s.face_brightness,s.auto_light)
                rgb = cv2.cvtColor(corrected, cv2.COLOR_BGR2RGB)
                result = mesh.process(rgb)
                obs = Observation()
                obs.phone_status = phone_state
                obs.light_level = lighting.level; obs.light_gain = lighting.gamma
                if result.multi_face_landmarks:
                    lm = result.multi_face_landmarks[0].landmark
                    lighting.update_face(lm,640,360)
                    span = max(abs(lm[454].x-lm[234].x), .01)
                    eye_y = (lm[33].y+lm[263].y)/2
                    face_height = max(lm[152].y-lm[10].y, .01)
                    obs.face = True
                    obs.yaw = (lm[1].x-(lm[234].x+lm[454].x)/2)/span
                    obs.pitch = (lm[1].y-eye_y)/face_height
                    def iris(center, left, right, top, bottom):
                        x = (lm[center].x-min(lm[left].x,lm[right].x))/max(abs(lm[right].x-lm[left].x), .001)
                        y = (lm[center].y-lm[top].y)/max(lm[bottom].y-lm[top].y, .002)
                        return x, y
                    a = iris(468,33,133,159,145)
                    b = iris(473,362,263,386,374)
                    obs.gaze_x, obs.gaze_y = (a[0]+b[0])/2, (a[1]+b[1])/2
                    obs.eyes_open = abs(lm[159].y-lm[145].y)/max(abs(lm[33].x-lm[133].x), .001) > .12
                    if s.dense_landmarks:
                        for i,point in enumerate(lm):
                            cv2.circle(rgb,(int(point.x*640),int(point.y*360)),1,(62,182,161),-1)
                    for i in (1,33,263,468,473):
                        cv2.circle(rgb, (int(lm[i].x*640),int(lm[i].y*360)), 3, (231,199,111), -1)
                    current = (obs.yaw,obs.pitch,obs.gaze_x,obs.gaze_y)
                    smooth = current if smooth is None else tuple(a*.55+b*.45 for a,b in zip(current,smooth))
                    obs.yaw,obs.pitch,obs.gaze_x,obs.gaze_y = smooth
                else:
                    smooth = None; lighting.roi = None
                if phone_worker:
                    if hasattr(phone_model,'confidence'):phone_model.confidence=s.phone_confidence
                    if s.auto_light:
                        import numpy as np
                        lut=np.clip((np.arange(256)/255.)**lighting.gamma*255,0,255).astype(np.uint8)
                        phone_worker.submit(cv2.LUT(frame,lut))
                    else:phone_worker.submit(frame)
                    obs.phone = phone_worker.visible()
                    detection = phone_worker.detection(); obs.phone_score = detection['score']
                    for (x,y,bw,bh),score in detection['boxes']:
                        sx,sy = 640/frame.shape[1],360/frame.shape[0]
                        a,b = (int(x*sx),int(y*sy)),(int((x+bw)*sx),int((y+bh)*sy))
                        cv2.rectangle(rgb,a,b,(255,185,89),2)
                        cv2.putText(rgb,f'Phone {score:.0%}',(a[0],max(14,a[1]-6)),cv2.FONT_HERSHEY_SIMPLEX,.45,(255,214,142),1)
                image = QImage(rgb.data,640,360,rgb.strides[0],QImage.Format.Format_RGB888).copy()
                with self.lock:
                    self.latest = (obs, image, time.monotonic(), time.monotonic()-began)
                self.stop_event.wait(max(0,1/s.fps-(time.monotonic()-began)))
        except Exception as exc:
            self.status.emit(f"Camera error · {exc}")
        finally:
            if phone_worker:
                phone_worker.stop(); phone_worker.join(timeout=3)
            if cap is not None:
                cap.release()
            if mesh is not None:
                mesh.close()

    def stop(self):
        self.stop_event.set()
