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
        self.frame = None; self.result = 0.
        self.calibrating = False
        self.details = {'score':0.,'boxes':[],'visible':False}

    def submit(self, frame, origin, direction, include_objects, gamma=1.):
        with self.lock:
            self.frame = (frame, time.monotonic(), origin, direction, include_objects, gamma)

    def detection(self):
        with self.lock:
            if time.monotonic()-self.result < 3:
                return dict(self.details)
        return {'score':0.,'boxes':[],'visible':False}

    def run(self):
        import cv2
        import numpy as np
        from .phone import YoloXPhoneDetector, aligned_with_look, near_hand
        hands = None
        previous = ''
        zoom = False
        try:
            while not self.stopping.is_set():
                with self.lock:
                    packet, self.frame = self.frame, None
                if packet is None:
                    self.stopping.wait(.05)
                    continue
                frame, captured, origin, direction, include_objects, gamma = packet
                calibrating = self.calibrating
                include_objects = include_objects and not calibrating
                if abs(gamma-1) > .08:
                    lookup = np.clip((np.arange(256)/255.)**gamma*255,0,255).astype(np.uint8)
                    frame = cv2.LUT(frame,lookup)
                # Alternate full and center-cropped views during guided checks, with one inference per frame.
                size = frame.shape[1], frame.shape[0]
                zoom = calibrating and not zoom
                left, top = (size[0]//7,size[1]//8) if zoom else (0,0)
                model_frame = frame[top:size[1]-top,left:size[0]-left]
                threshold = min(self.confidence,.15) if calibrating else self.confidence
                if hasattr(self.model,'confidence'):
                    self.model.confidence = threshold
                if isinstance(self.model, YoloXPhoneDetector):
                    details = self.model.detect(model_frame, include_objects)
                elif hasattr(self.model, 'detect'):
                    details = self.model.detect(model_frame)
                else:
                    predictions = self.model.predict(model_frame,imgsz=320,device='cpu',classes=[67],
                                                     conf=threshold,verbose=False)
                    boxes = []
                    for prediction in predictions:
                        for box in prediction.boxes:
                            x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                            boxes.append(([x1,y1,x2-x1,y2-y1],float(box.conf[0])))
                    details = {'score':max((score for _,score in boxes),default=0.),
                               'boxes':boxes,'visible':bool(boxes)}
                if zoom:
                    details['boxes'] = [([x+left,y+top,w,h],score) for (x,y,w,h),score in details['boxes']]
                candidates = [(box,score,'phone') for box,score in details['boxes']]
                candidates += details.get('objects', [])
                aligned = [(box,score,label) for box,score,label in candidates
                           if aligned_with_look(box,origin,direction,size)]
                label = ''
                if aligned and include_objects:
                    if hands is None:
                        from mediapipe.python.solutions.hands import Hands
                        hands = Hands(static_image_mode=True, max_num_hands=2, model_complexity=0)
                    hand_frame = cv2.resize(frame,(480,max(1,round(480*size[1]/size[0]))))
                    detected = hands.process(cv2.cvtColor(hand_frame,cv2.COLOR_BGR2RGB))
                    points = [(p.x,p.y) for hand in detected.multi_hand_landmarks or [] for p in hand.landmark]
                    held = [(name,score,box) for box,score,name in aligned if near_hand(box,points,size)]
                    if held:
                        label,score,box = max(held,key=lambda item:(item[0]=='phone',item[1]))
                        if label == previous:
                            details['held'] = (label,score,box)
                previous = label
                details['stamp'] = captured
                details['calibrating'] = calibrating
                with self.lock:
                    self.result = captured
                    self.details = details
                self.stopping.wait(.45)
        except Exception as exc:
            self.status.emit(f'Phone detector disabled: {exc}')
            with self.lock:
                self.result = 0.
        finally:
            if hands is not None:
                hands.close()

    def stop(self):
        self.stopping.set()
        with self.lock:
            self.frame = None
            self.result = 0.


class VisionWorker(QThread):
    status = Signal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.baseline = settings.baseline
        self.phone_confidence = settings.phone_confidence
        self.phone_calibrating = False
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
            from .phone import find_phone_model, aligned_with_look
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
            self.status.emit(f"Camera active | {actual} | phone {phone_state} · driver exposure {'accepted' if exposure_ok else 'unchanged / unsupported'}")
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
                obs = Observation(frame_size=(frame.shape[1],frame.shape[0]))
                origin = (.5,.5)
                direction = (0.,0.)
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
                    origin = ((lm[33].x+lm[263].x)/2,eye_y)
                    by,bp,gx,gy = self.baseline
                    eye_x = obs.gaze_x-gx if obs.eyes_open else 0.
                    eye_down = obs.gaze_y-gy if obs.eyes_open else 0.
                    if abs(obs.yaw-by) > s.head_tolerance*.65 or abs(obs.pitch-bp) > s.head_tolerance*.65 or max(abs(eye_x),abs(eye_down)) > s.gaze_tolerance:
                        direction = (obs.yaw-by+eye_x*.35,obs.pitch-bp+eye_down*.35)
                else:
                    smooth = None; lighting.roi = None
                if phone_worker:
                    phone_worker.confidence = self.phone_confidence
                    phone_worker.calibrating = self.phone_calibrating
                    phone_worker.submit(frame,origin,direction,s.handheld_context,lighting.gamma if s.auto_light else 1.)
                    detection = phone_worker.detection()
                    obs.phone = detection['visible'] and (self.phone_calibrating or not detection.get('calibrating'))
                    obs.phone_score = detection['score']
                    obs.phone_stamp = detection.get('stamp',0.)
                    obs.phone_check_result = detection.get('calibrating',False)
                    obs.phone_aligned = any(aligned_with_look(box,origin,direction,obs.frame_size)
                                            for box,_ in detection['boxes'])
                    if 'held' in detection:
                        label,score,box = detection['held']
                        if aligned_with_look(box,origin,direction,obs.frame_size):
                            obs.object_label,obs.object_score,obs.object_held = label,score,True
                    for (x,y,bw,bh),score in detection['boxes']:
                        sx,sy = 640/frame.shape[1],360/frame.shape[0]
                        a,b = (int(x*sx),int(y*sy)),(int((x+bw)*sx),int((y+bh)*sy))
                        cv2.rectangle(rgb,a,b,(255,185,89),2)
                        cv2.putText(rgb,f'Phone {score:.0%}',(a[0],max(14,a[1]-6)),cv2.FONT_HERSHEY_SIMPLEX,.45,(255,214,142),1)
                obs.backlight = float(small[::12,::12].mean()) - obs.light_level if obs.face else 0.
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
