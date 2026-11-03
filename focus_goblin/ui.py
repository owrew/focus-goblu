import copy
import io
import json
import math
import statistics
import time
import wave
import struct
from collections import deque
from dataclasses import asdict
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QUrl
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QFont, QPixmap, QKeySequence, QShortcut
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QTabWidget, QScrollArea, QFormLayout,
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QLineEdit, QFileDialog, QColorDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from .engine import Settings, AttentionEngine, Observation, Decision
from .storage import Store, data_dir
from .mascot import Mascot, LINES
from .vision import VisionWorker


def duration(seconds):
    seconds = int(seconds)
    return f"{seconds//60:02d}:{seconds%60:02d}"


class Chart(QWidget):
    def __init__(self, bars=False):
        super().__init__()
        self.values = []
        self.bars = bars
        self.accent = "#40dfcf"
        self.setMinimumHeight(180)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(35,15,-18,-28)
        p.setFont(QFont("Segoe UI",8))
        for i in range(5):
            y = r.bottom()-r.height()*i/4
            p.setPen(QPen(QColor("#29334c"),1)); p.drawLine(QPointF(r.left(),y),QPointF(r.right(),y))
            p.setPen(QColor("#8390ac")); p.drawText(0,int(y)+4,str(i*25) if not self.bars else "")
        if not self.values:
            p.setPen(QColor("#a3afc7")); p.drawText(r,Qt.AlignmentFlag.AlignCenter,"Your next session starts the story.")
            return
        if self.bars:
            maximum = max(max(v for _,v in self.values),60)
            slot = r.width()/len(self.values)
            for i,(label,v) in enumerate(self.values):
                height = v/maximum*(r.height()-20)
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(self.accent))
                p.drawRoundedRect(QRectF(r.left()+i*slot+8,r.bottom()-height,slot-16,max(height,2)),5,5)
                p.setPen(QColor("#b3bdd4")); p.drawText(int(r.left()+i*slot),r.bottom()+19,label[5:])
                p.drawText(int(r.left()+i*slot+6),int(r.bottom()-height-5),f"{v/60:.0f}m")
        else:
            path = QPainterPath()
            for i,v in enumerate(self.values):
                point = QPointF(r.left()+i*r.width()/max(1,len(self.values)-1),r.bottom()-v*r.height())
                path.moveTo(point) if i == 0 else path.lineTo(point)
            p.setPen(QPen(QColor(self.accent),3)); p.drawPath(path)
            p.setPen(QColor("#8390ac")); p.drawText(r.left(),r.bottom()+20,"Recent estimated attention · up to 5 minutes")
        p.end()


class Ring(QWidget):
    def __init__(self):
        super().__init__(); self.value = 0; self.accent = "#40dfcf"; self.setFixedSize(155,155)

    def paintEvent(self,e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#2b3450"),10)); p.drawEllipse(QRectF(12,12,130,130))
        p.setPen(QPen(QColor(self.accent),10,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(12,12,130,130),90*16,-int(self.value*360*16))
        p.setPen(QColor("#f2f5ff")); p.setFont(QFont("Segoe UI",25,QFont.Weight.Bold))
        p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,f"{self.value*100:.0f}%")


class MainWindow(QMainWindow):
    def __init__(self, store=None):
        super().__init__()
        self.store = store or Store()
        self.settings = self.store.load_settings()
        self.engine = AttentionEngine(self.settings)
        self.worker = None
        self.sid = None
        self.demo = False
        self.paused = False
        self.closing = False
        self.last_frame = self.last_tick = time.monotonic()
        self.last_sample = 0
        self.last_state = "ready"
        self.samples = deque(maxlen=300)
        self.calibration = None
        self.observation = Observation(valid=False)
        self.overlay = Mascot(True)
        self.overlay.action.connect(self.pet_action)
        self.setWindowTitle("Focus Goblin · local focus companion")
        self.resize(1280,880)
        self.setMinimumSize(980,720)
        self.build()
        self.apply_theme()
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(80)
        QShortcut(QKeySequence("Escape"),self,activated=self.stop)
        self.refresh_history()
        if self.settings.pet:
            self.show_overlay()

    def button(self, text, callback, primary=False):
        b = QPushButton(text); b.clicked.connect(callback)
        if primary: b.setObjectName("primary")
        return b

    def panel(self, title):
        f = QFrame(); f.setObjectName("panel")
        layout = QVBoxLayout(f)
        heading = QLabel(title); heading.setObjectName("sectionTitle"); layout.addWidget(heading)
        return f,layout

    def build(self):
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(26,20,26,18); layout.setSpacing(14)
        top = QHBoxLayout()
        brand = QLabel("Focus Goblin"); brand.setObjectName("brand")
        top.addWidget(brand); top.addStretch()
        self.camera_status = QLabel("● Camera off · local processing")
        top.addWidget(self.camera_status); layout.addLayout(top)
        sub = QLabel("A little chaos. A little accountability. A place to return to your work.")
        sub.setObjectName("muted"); layout.addWidget(sub)
        controls = QHBoxLayout()
        self.start_button = self.button("Start camera",self.start_camera,True)
        self.pause_button = self.button("Pause",self.pause)
        self.stop_button = self.button("Stop / Goblin off",self.stop)
        self.demo_button = self.button("Try camera-free demo",self.start_demo)
        self.calibrate_button = self.button("Calibrate · 3 seconds",self.calibrate)
        for b in (self.start_button,self.pause_button,self.stop_button,self.demo_button,self.calibrate_button): controls.addWidget(b)
        layout.addLayout(controls)
        self.notice = QLabel("Ready. Start the camera, then calibrate while looking naturally at your screen.")
        self.notice.setWordWrap(True); self.notice.setObjectName("notice"); layout.addWidget(self.notice)
        self.tabs = QTabWidget(); layout.addWidget(self.tabs,1)
        page = QWidget(); page.setMinimumHeight(740)
        observatory = QScrollArea(); observatory.setWidgetResizable(True); observatory.setWidget(page)
        self.tabs.addTab(observatory,"Observatory")
        grid = QGridLayout(page); grid.setSpacing(14)
        self.metrics = {}
        row = QHBoxLayout()
        for key,title in [("focus","Estimated focus"),("distracted","Likely distraction"),("longest","Longest streak"),("alerts","Goblin alerts")]:
            card,inner = self.panel(title)
            value = QLabel("00:00" if key != "alerts" else "0"); value.setObjectName("metric")
            inner.addWidget(value); self.metrics[key] = value; row.addWidget(card)
        grid.addLayout(row,0,0,1,2)
        live,inner = self.panel("Local camera / attention signals")
        self.preview = QLabel("Camera off\nNo images are recorded.")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview.setMinimumSize(400,210)
        self.preview.setObjectName("preview"); inner.addWidget(self.preview,1)
        self.signals = QLabel("Head and iris estimates appear after calibration."); self.signals.setWordWrap(True)
        inner.addWidget(self.signals); grid.addWidget(live,1,0)
        creature,inner = self.panel("The cave")
        line = QHBoxLayout()
        self.mascot = Mascot(); self.mascot.setMinimumSize(260,240); line.addWidget(self.mascot,1)
        right = QVBoxLayout(); self.ring = Ring(); right.addWidget(self.ring)
        self.state_label = QLabel("Ready"); self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.state_label); line.addLayout(right); inner.addLayout(line)
        actions = QHBoxLayout()
        actions.addWidget(self.button("Preview reaction",self.preview_reaction))
        actions.addWidget(self.button("Show cave",self.show_overlay))
        actions.addWidget(self.button("Take a break",self.take_break))
        inner.addLayout(actions); grid.addWidget(creature,1,1)
        chart,inner = self.panel("Attention signal")
        self.chart = Chart(); inner.addWidget(self.chart); grid.addWidget(chart,2,0)
        week,inner = self.panel("Daily focus · real sessions only")
        self.week = Chart(True); inner.addWidget(self.week); grid.addWidget(week,2,1)
        self.footer = QLabel("Break timer 00:00 · Face absence and uncalibrated time are excluded from focus.")
        self.footer.setWordWrap(True); grid.addWidget(self.footer,3,0,1,2)
        grid.setColumnStretch(0,1); grid.setColumnStretch(1,1)
        grid.setRowStretch(1,2); grid.setRowStretch(2,1)
        self.build_settings()
        history = QWidget(); h = QVBoxLayout(history)
        h.addWidget(QLabel("Saved session summaries · demo sessions are labelled and excluded from daily focus."))
        self.history = QTableWidget(0,7); self.history.setHorizontalHeaderLabels(["Started","Mode","Source","Focus","Distraction","Streak","Alerts"])
        self.history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        h.addWidget(self.history); h.addWidget(self.button("Export session CSV",self.export))
        self.tabs.addTab(history,"Session archive")
        privacy = QLabel("Camera frames stay in memory. SQLite saves durations, scores and events on this PC.\n"
            "Pause and Stop release the camera. Escape stops monitoring while this window has focus.\n"
            "Head pose and gaze are rough landmark ratios, not eye-tracker measurements.\n"
            "Looking at the screen does not prove concentration. Phone visibility does not prove phone use.\n"
            "Break reminders use elapsed monitoring time; sitting posture is not detected.\n\n"
            "Data folder: " + str(data_dir()))
        privacy.setWordWrap(True); privacy.setMargin(25); privacy.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tabs.addTab(privacy,"Privacy & limits")

    def build_settings(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        page = QWidget(); form = QFormLayout(page); form.setSpacing(12)
        self.fields = {}
        def spin(key,label,low,high,step=1,decimal=False):
            w = QDoubleSpinBox() if decimal else QSpinBox(); w.setRange(low,high); w.setSingleStep(step)
            w.setValue(getattr(self.settings,key)); self.fields[key] = w; form.addRow(label,w)
        def combo(key,label,items):
            w = QComboBox(); w.addItems(items); w.setCurrentText(getattr(self.settings,key)); self.fields[key] = w; form.addRow(label,w)
        def check(key,label):
            w = QCheckBox(label); w.setChecked(getattr(self.settings,key)); self.fields[key] = w; form.addRow(w)
        combo("mode","Session mode",["Study","Work","Deep focus","Light monitoring"])
        combo("personality","Personality",list(LINES))
        combo("style","Dashboard finish",["Aurora glass","Quiet graphite"])
        spin("camera","Camera index",0,9)
        combo("resolution","Requested capture resolution",["1280x720","1920x1080"])
        spin("fps","Processing frames per second",5,20)
        spin("warning_seconds","Warning after (seconds)",1,60,1,True)
        spin("alert_seconds","Reaction after (seconds)",2,120,1,True)
        spin("cooldown_seconds","Repeat alert cooldown (seconds)",1,300,1,True)
        spin("head_tolerance","Head direction tolerance (higher = gentler)",.03,.8,.01,True)
        spin("gaze_tolerance","Iris tolerance (higher = gentler)",.03,1.,.01,True)
        spin("phone_confidence","Phone minimum confidence",.1,.95,.05,True)
        spin("break_minutes","Break reminder every (minutes)",1,180)
        spin("goal_minutes","Daily focus goal (minutes)",5,480)
        spin("volume","Sound volume (%)",0,100)
        spin("intensity","Reaction intensity (1 = gentle, 3 = chaotic)",1,3)
        for key,label in [("overlay","Enable desktop overlay"),("pet","Show desktop pet on launch (camera stays off)"),("fire","Cartoon fire"),("reduced_motion","Reduced motion"),("sound","Enable synthetic goblin shriek"),("paper_mode","Paper / keyboard mode: allow looking down without a visible phone")]: check(key,label)
        modelrow = QHBoxLayout(); self.modelpath = QLineEdit(self.settings.phone_model)
        modelrow.addWidget(self.modelpath); modelrow.addWidget(self.button("Browse local YOLO model",self.choose_model)); form.addRow("Optional phone model (.pt)",modelrow)
        form.addRow(QLabel("Recommended: local YOLOv4-tiny .weights + matching .cfg (OpenCV, no extra dependencies).\nOptional .pt models need requirements-phone.txt. Camera settings apply to the next session."))
        form.addRow(self.button("Choose RGB accent",self.choose_color))
        form.addRow(self.button("Apply and save settings",self.save_settings,True))
        self.fields['mode'].currentTextChanged.connect(self.mode_preset)
        scroll.setWidget(page); self.tabs.addTab(scroll,"Control room")

    def mode_preset(self,mode):
        warning,alert = {'Study':(4,8),'Work':(5,10),'Deep focus':(3,6),'Light monitoring':(8,16)}[mode]
        self.fields['warning_seconds'].setValue(warning)
        self.fields['alert_seconds'].setValue(alert)

    def choose_model(self):
        path,_ = QFileDialog.getOpenFileName(self,"Choose a trusted local model", "", "YOLO weights (*.weights *.pt)")
        if path: self.modelpath.setText(path)

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.settings.accent),self)
        if color.isValid(): self.settings.accent = color.name(); self.apply_theme()

    def save_settings(self):
        for key,w in self.fields.items():
            setattr(self.settings,key,w.isChecked() if isinstance(w,QCheckBox) else w.currentText() if isinstance(w,QComboBox) else w.value())
        self.settings.phone_model = self.modelpath.text().strip()
        self.settings = self.settings.validated(); self.engine.settings = self.settings
        self.store.save_settings(self.settings); self.apply_theme()
        self.notice.setText("Settings saved. Camera/model changes apply after Stop and Start. Calibrate after moving the camera.")
        if not self.settings.overlay: self.overlay.hide()

    def apply_theme(self):
        accent = self.settings.accent
        if not QColor(accent).isValid(): accent = "#40dfcf"
        panel = "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #202b46,stop:1 #131b30)" if self.settings.style == "Aurora glass" else "#1b2232"
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background:#0d1221; color:#eaf0ff; font-family:'Segoe UI'; font-size:13px; }}
            QFrame#panel {{ background:{panel}; border:1px solid #394665; border-radius:16px; }}
            QFrame#panel QLabel, QFrame#panel QWidget {{ background:transparent; }}
            QLabel#brand {{ font-size:32px; font-weight:750; color:{accent}; }}
            QLabel#metric {{ font-size:29px; font-weight:700; }}
            QLabel#sectionTitle {{ font-size:14px; color:#bdc9e5; font-weight:600; }}
            QLabel#muted {{ color:#94a5c7; }}
            QLabel#notice {{ background:#202d47; border-left:3px solid {accent}; padding:10px; border-radius:5px; }}
            QLabel#preview {{ background:#090f1d; border-radius:10px; color:#97a7c5; }}
            QPushButton {{ background:#26334e; border:1px solid #435571; border-radius:8px; padding:9px 13px; }}
            QPushButton:hover {{ border-color:{accent}; background:#344662; }}
            QPushButton:focus {{ border:2px solid {accent}; }}
            QPushButton:disabled {{ color:#6e7b92; background:#182032; }}
            QPushButton#primary {{ background:{accent}; color:#0d1420; font-weight:700; }}
            QTabWidget::pane {{ border:0; }}
            QTabBar::tab {{ background:#182239; padding:11px 20px; margin-right:5px; border-radius:6px; }}
            QTabBar::tab:selected {{ background:#34425f; color:{accent}; }}
            QSpinBox,QDoubleSpinBox,QComboBox,QLineEdit {{ padding:7px; background:#202b43; border:1px solid #455674; border-radius:5px; }}
            QTableWidget {{ gridline-color:#34405c; alternate-background-color:#1c263c; }}
            QHeaderView::section {{ background:#283550; padding:9px; border:0; }}
            QScrollArea {{ border:0; }}
        """)
        self.chart.accent = self.week.accent = self.ring.accent = accent
        for m in (self.mascot,self.overlay):
            m.personality = self.settings.personality; m.reduced = self.settings.reduced_motion
            m.fire = self.settings.fire; m.intensity = self.settings.intensity
        self.update()

    def busy(self):
        return self.worker is not None and self.worker.isRunning()

    def start_camera(self):
        if self.sid is not None or self.busy(): return
        self.begin(False); self.start_worker()

    def start_worker(self):
        self.observation = Observation(valid=False)
        self.worker = VisionWorker(copy.deepcopy(self.settings))
        self.worker.status.connect(self.worker_status)
        self.worker.start(); self.last_frame = time.monotonic()
        self.camera_status.setText("● Camera opening…")

    def worker_status(self,text):
        self.camera_status.setText(text)
        if "error" in text.lower() or "unavailable" in text.lower() or "disabled" in text.lower(): self.notice.setText(text)

    def begin(self,demo):
        self.demo = demo; self.paused = False
        self.engine = AttentionEngine(copy.deepcopy(self.settings))
        if demo: self.engine.settings.calibrated = True
        self.sid = self.store.start(self.settings.mode,demo)
        self.samples.clear(); self.last_sample = 0; self.last_state = "ready"
        self.last_tick = time.monotonic(); self.pause_button.setText("Pause")
        self.start_button.setEnabled(False); self.demo_button.setEnabled(False)
        self.notice.setText("DEMO · simulated signals; camera stays off." if demo else "Camera starting. Look at the screen and calibrate.")
        self.show_overlay()

    def start_demo(self):
        if self.sid is not None or self.busy(): return
        self.begin(True); self.camera_status.setText("● Camera off · DEMO signals")
        self.preview.setText("DEMO / no camera\nCycle: focused → looking down + phone → refocus")

    def pause(self):
        if self.sid is None: return
        if not self.paused:
            self.paused = True
            if self.worker: self.worker.stop()
            self.preview.clear(); self.preview.setText("Paused · camera closing")
            self.overlay.hide(); self.calibration = None
            self.engine.take_break()
            self.pause_button.setText("Resume"); self.store.event(self.sid,"pause","User paused monitoring")
        elif not self.busy():
            self.paused = False; self.pause_button.setText("Pause")
            if not self.demo: self.start_worker()
            self.last_tick = time.monotonic(); self.show_overlay()

    def stop(self):
        if self.worker: self.worker.stop()
        if self.sid is not None:
            self.store.checkpoint(self.sid,self.engine.summary(),True)
            self.sid = None
        self.paused = False; self.calibration = None
        self.preview.clear(); self.preview.setText("Camera off / closing\nNo images are recorded.")
        self.overlay.hide(); self.mascot.state = "ready"
        self.pause_button.setText("Pause"); self.start_button.setEnabled(True); self.demo_button.setEnabled(True)
        self.notice.setText("Monitoring stopped. Session saved locally.")
        self.refresh_history()

    def calibrate(self):
        if self.sid is None or self.demo or self.paused:
            self.notice.setText("Start a real camera session before calibration."); return
        self.engine.settings.calibrated = False
        self.calibration = (time.monotonic(),[])
        self.notice.setText("Calibrating: look naturally at the screen for 3 seconds. Keep your face still.")

    def show_overlay(self):
        if self.settings.overlay:
            self.overlay.show()

    def pet_action(self,action):
        if action == 'dashboard':
            self.showNormal(); self.raise_(); self.activateWindow()
        elif action == 'pause': self.pause()
        elif action == 'break': self.take_break()
        elif action == 'stop': self.stop()
        elif action == 'hide': self.overlay.hide()

    def preview_reaction(self):
        self.mascot.state = self.overlay.state = "angry"; self.show_overlay()
        self.shriek()
        QTimer.singleShot(4000,lambda: self.restore_mascot())

    def restore_mascot(self):
        self.mascot.state = self.overlay.state = self.engine.state if self.sid else "ready"

    def take_break(self):
        if self.sid:
            self.engine.take_break(); self.store.event(self.sid,"break","User requested break")
            if not self.paused: self.pause()
        self.mascot.state = self.overlay.state = "break"; self.show_overlay()
        self.notice.setText("Break time. Monitoring is paused. Stand, stretch, walk; press Resume when ready.")

    def shriek(self):
        if not self.settings.sound: return
        path = data_dir()/"goblin.wav"
        if not path.exists():
            with wave.open(str(path),"wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
                audio = bytearray()
                for i in range(14000):
                    t = i/22050
                    value = math.sin(2*math.pi*(370*t+85*t*t)+1.4*math.sin(2*math.pi*26*t))
                    audio.extend(struct.pack("<h",int(9500*math.sin(math.pi*i/14000)*value)))
                w.writeframes(audio)
        if not hasattr(self,"sound_effect"):
            self.sound_effect = QSoundEffect(self); self.sound_effect.setSource(QUrl.fromLocalFile(str(path)))
        self.sound_effect.setVolume(self.settings.volume/100); self.sound_effect.play()

    def tick(self):
        now = time.monotonic(); dt = min(now-self.last_tick,.5); self.last_tick = now
        if self.worker and not self.worker.isRunning():
            self.worker.wait(); self.worker = None
            if self.paused: self.camera_status.setText("● Camera off · paused")
            elif self.sid is None: self.camera_status.setText("● Camera off")
            elif not self.demo:
                self.camera_status.setText("● Camera off · worker stopped")
                self.notice.setText("Camera stopped. Stop this session, check permissions and camera index, then restart.")
        if self.sid is None or self.paused: return
        obs = None
        if self.demo:
            cycle = self.engine.active%25
            by,bp,gx,gy = self.engine.settings.baseline
            obs = Observation(True,by,bp+(.4 if 6<cycle<18 else 0),gx,gy,True,6<cycle<18)
        elif self.worker:
            result = self.worker.take()
            if result:
                obs,image,stamp,latency = result
                self.last_frame = stamp
                self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
                self.signals.setText(f"Head ratios {obs.yaw:+.2f} / {obs.pitch:+.2f} · Iris {obs.gaze_x:.2f} / {obs.gaze_y:.2f}\n"
                    f"Face {'visible' if obs.face else 'absent'} · Phone {'visible' if obs.phone else 'not detected / off'} · Processing {latency*1000:.0f} ms")
                if self.calibration:
                    began,points = self.calibration
                    if obs.face and obs.eyes_open: points.append((obs.yaw,obs.pitch,obs.gaze_x,obs.gaze_y))
                    if now-began >= 3:
                        if len(points) >= 12:
                            baseline = tuple(statistics.median(p[i] for p in points) for i in range(4))
                            spread = max(statistics.pstdev(p[i] for p in points) for i in range(4))
                            if spread < .16:
                                self.settings.baseline = baseline; self.settings.calibrated = True
                                self.engine.settings.baseline = baseline; self.engine.settings.calibrated = True
                                self.store.save_settings(self.settings)
                                self.notice.setText("Calibration saved. Brief glances are allowed; tune tolerances in Control room.")
                            else: self.notice.setText("Calibration was unstable. Hold still with eyes open and try again.")
                        else: self.notice.setText("Not enough clear face samples. Improve lighting and try calibration again.")
                        self.calibration = None
        if obs is not None: self.observation = obs
        if not self.demo and now-self.last_frame > 1:
            self.observation = Observation(valid=False)
            self.preview.clear(); self.preview.setText("Camera signal unavailable")
        decision = self.engine.step(self.observation,dt)
        self.mascot.state = self.overlay.state = decision.state
        self.state_label.setText(decision.state.capitalize()+"\nEstimated attention")
        self.ring.value = decision.confidence; self.ring.update()
        self.footer.setText(f"Break timer {duration(self.engine.since_break)} / {self.settings.break_minutes}m · Goal {self.settings.goal_minutes}m/day · "
            f"Distractions {self.engine.distractions} · Phone events {self.engine.phone_events} · "
            f"Absent {duration(self.engine.absent)} · Unobserved/grace {duration(self.engine.unknown)}\n{decision.reason}")
        for key,label in self.metrics.items():
            label.setText(str(self.engine.alerts) if key == "alerts" else duration(getattr(self.engine,key)))
        if decision.state != self.last_state:
            self.store.event(self.sid,"state",decision.state+": "+decision.reason); self.last_state = decision.state
        if decision.alert:
            self.store.event(self.sid,"alert",self.settings.personality); self.shriek(); self.show_overlay()
        if self.engine.active-self.last_sample >= 1:
            self.last_sample = self.engine.active; self.samples.append(decision.confidence)
            self.chart.values = list(self.samples); self.chart.update()
            self.store.sample(self.sid,self.engine.active,decision.confidence,decision.state)
            self.store.checkpoint(self.sid,self.engine.summary())
        if self.engine.break_due():
            self.store.event(self.sid,"reminder","Elapsed monitoring break reminder")
            self.take_break()

    def refresh_history(self):
        rows = self.store.history(); self.history.setRowCount(len(rows))
        for i,(_,started,mode,demo,payload) in enumerate(rows):
            s = json.loads(payload)
            values = [started[:16].replace("T"," "),mode,"Demo" if demo else "Camera",duration(s.get("focus",0)),duration(s.get("distracted",0)),duration(s.get("longest",0)),str(s.get("alerts",0))]
            for j,v in enumerate(values): self.history.setItem(i,j,QTableWidgetItem(v))
        self.week.values = self.store.daily(); self.week.update()

    def export(self):
        path,_ = QFileDialog.getSaveFileName(self,"Export summaries","focus-sessions.csv","CSV (*.csv)")
        if path: self.store.export(path); self.notice.setText("Session summaries exported. No camera frames included.")

    def closeEvent(self,event):
        self.stop()
        if self.busy():
            self.notice.setText("Releasing camera before closing…")
            event.ignore(); QTimer.singleShot(250,self.close); return
        self.overlay.close(); self.store.close(); event.accept()
