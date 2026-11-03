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

    def submit(self,frame):
        with self.lock: self.frame = frame

    def visible(self):
        with self.lock: visible,stamp = self.result
        return visible and time.monotonic()-stamp < 4

    def run(self):
        while not self.stopping.is_set():
            with self.lock: frame,self.frame = self.frame,None
            if frame is None:
                self.stopping.wait(.05); continue
            try:
                if hasattr(self.model,'predict_phone'): visible = self.model.predict_phone(frame)
                else:
                    predictions = self.model.predict(frame,imgsz=320,device='cpu',classes=[67],conf=self.confidence,verbose=False)
                    visible = any(len(p.boxes) for p in predictions)
                with self.lock: self.result = (bool(visible),time.monotonic())
            except Exception as exc:
                self.status.emit(f'Phone detector disabled: {exc}')
                with self.lock: self.result = (False,0.)
                break
            self.stopping.wait(2.)

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
            mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True,
                min_detection_confidence=.6, min_tracking_confidence=.6)
            phone_model = None
            if s.phone_model:
                try:
                    # Require an existing path: runtime never auto-downloads weights.
                    if not Path(s.phone_model).is_file():
                        raise FileNotFoundError("Select an existing local .pt model")
                    os.environ["YOLO_OFFLINE"] = "true"
                    os.environ["YOLO_AUTOINSTALL"] = "false"
                    if Path(s.phone_model).suffix == '.weights':
                        from .phone import TinyPhoneDetector
                        phone_model = TinyPhoneDetector(s.phone_model,s.phone_confidence)
                    else:
                        from ultralytics import YOLO
                        phone_model = YOLO(s.phone_model)
                except Exception as exc:
                    self.status.emit(f"Phone detection unavailable: {exc}")
            cap = cv2.VideoCapture(s.camera, cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY)
            w, h = map(int, s.resolution.split("x"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            cap.set(cv2.CAP_PROP_FPS, s.fps)
            if not cap.isOpened():
                raise RuntimeError("Camera unavailable. Check Windows camera permissions or close other camera apps.")
            actual = f"{int(cap.get(3))}×{int(cap.get(4))}"
            self.status.emit(f"Camera active · {actual} · phone {'enabled' if phone_model else 'off'}")
            if phone_model:
                phone_worker = PhoneWorker(phone_model,s.phone_confidence,self.status); phone_worker.start()
            while not self.stop_event.is_set():
                began = time.monotonic()
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Camera stopped delivering frames")
                small = cv2.resize(frame, (640, 360))
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                result = mesh.process(rgb)
                obs = Observation()
                if result.multi_face_landmarks:
                    lm = result.multi_face_landmarks[0].landmark
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
                    for i in (1,33,263,468,473):
                        cv2.circle(rgb, (int(lm[i].x*640),int(lm[i].y*360)), 2, (64,223,207), -1)
                if phone_worker:
                    phone_worker.submit(small)
                    obs.phone = phone_worker.visible()
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
