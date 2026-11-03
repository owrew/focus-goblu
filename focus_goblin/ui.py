import copy
import io
import json
import math
import statistics
import time
import wave
import struct
from pathlib import Path
from collections import deque
from dataclasses import asdict
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QUrl, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QFont, QPixmap, QKeySequence, QShortcut, QIcon, QLinearGradient
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QTabWidget, QScrollArea, QFormLayout,
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QLineEdit, QFileDialog, QColorDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QGraphicsOpacityEffect, QAbstractItemView)
from .engine import Settings, AttentionEngine, Observation, Decision
from .storage import Store, data_dir
from .mascot import Mascot, LINES
from .vision import VisionWorker
from .visuals import AuroraBackground, GlassPanel, CameraPreview, ASSETS
from .effects import ScreenFire
from .workspace import WorkspaceMixin


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
        self.setMouseTracking(True)

    def mouseMoveEvent(self,event):
        if self.values and not self.bars:
            index = round(max(0,min(1,(event.position().x()-35)/max(1,self.width()-53)))*(len(self.values)-1))
            self.setToolTip(f'Estimated attention: {self.values[index]*100:.0f}% · {len(self.values)-1-index} samples ago')

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
                gap=min(8,slot*.18)
                p.drawRoundedRect(QRectF(r.left()+i*slot+gap,r.bottom()-height,max(2,slot-gap*2),max(height,2)),3,3)
                if i%max(1,math.ceil(len(self.values)/8))==0:
                    p.setPen(QColor("#b3bdd4")); p.drawText(int(r.left()+i*slot),r.bottom()+19,label[5:])
                    p.drawText(int(r.left()+i*slot+2),int(r.bottom()-height-5),f"{v/60:.0f}m")
        else:
            path = QPainterPath()
            for i,v in enumerate(self.values):
                point = QPointF(r.left()+i*r.width()/max(1,len(self.values)-1),r.bottom()-v*r.height())
                path.moveTo(point) if i == 0 else path.lineTo(point)
            area = QPainterPath(path); area.lineTo(r.right(),r.bottom()); area.lineTo(r.left(),r.bottom()); area.closeSubpath()
            shade = QLinearGradient(0,r.top(),0,r.bottom())
            c = QColor(self.accent); c.setAlpha(65); shade.setColorAt(0,c); c.setAlpha(0); shade.setColorAt(1,c)
            p.fillPath(area,shade)
            p.setPen(QPen(QColor(self.accent),3,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)); p.drawPath(path)
            p.setPen(QColor("#8390ac")); p.drawText(r.left(),r.bottom()+20,"Recent estimated attention · up to 5 minutes")
        p.end()


class Ring(QWidget):
    def __init__(self):
        super().__init__(); self._value = self.display_value = 0.; self.accent = "#40dfcf"; self.setFixedSize(155,155)
        self.motion = QTimer(self); self.motion.timeout.connect(self.ease); self.motion.start(33)

    @property
    def value(self): return self._value

    @value.setter
    def value(self,value):
        self._value = max(0.,min(1.,value))
        if getattr(self,'reduced',False): self.display_value = self._value

    def ease(self):
        if abs(self.display_value-self._value) > .001:
            self.display_value += (self._value-self.display_value)*.18; self.update()

    def paintEvent(self,e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#2b3450"),10)); p.drawEllipse(QRectF(12,12,130,130))
        p.setPen(QPen(QColor(self.accent),10,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(12,12,130,130),90*16,-int(self.display_value*360*16))
        p.setPen(QColor("#f2f5ff")); p.setFont(QFont("Segoe UI",25,QFont.Weight.Bold))
        p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,f"{self.display_value*100:.0f}%")


class MainWindow(WorkspaceMixin,QMainWindow):
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
        self.preview_until = 0.
        self.screen_fire = ScreenFire()
        self.overlay = Mascot(True)
        self.overlay.action.connect(self.pet_action)
        self.setWindowTitle("Focus Goblin · local focus companion")
        self.setWindowIcon(QIcon(str(ASSETS/'goblin-logo.png')))
        self.resize(1280,880)
        self.setMinimumSize(980,720)
        self.build()
        self.setup_features()
        self.mascot.action.connect(self.pet_action)
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
        f = GlassPanel(); f.setObjectName("panel")
        layout = QVBoxLayout(f)
        layout.setContentsMargins(18,16,18,16)
        heading = QLabel(title); heading.setObjectName("sectionTitle"); heading.setFixedHeight(22); layout.addWidget(heading)
        return f,layout

    def build(self):
        root = AuroraBackground(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(26,20,26,18); layout.setSpacing(14)
        top = QHBoxLayout()
        logo = QLabel(); logo.setFixedSize(68,58)
        logo.setPixmap(QPixmap(str(ASSETS/'goblin-logo.png')).scaled(68,58,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        top.addWidget(logo)
        brand = QLabel("Focus Goblin"); brand.setObjectName("brand")
        top.addWidget(brand); top.addStretch()
        local = QLabel("Local companion  /  v0.3"); local.setObjectName('muted'); top.addWidget(local)
        self.camera_status = QLabel("● Camera off · local processing")
        top.addWidget(self.camera_status); layout.addLayout(top)
        sub = QLabel("Your focus has a guardian. Give it something worth guarding.")
        sub.setObjectName("muted"); layout.addWidget(sub)
        controls = QHBoxLayout()
        self.start_button = self.button("Start camera",self.start_camera,True)
        self.pause_button = self.button("Pause",self.pause)
        self.stop_button = self.button("Stop / Goblin off",self.stop)
        self.demo_button = self.button("Try camera-free demo",self.start_demo)
        self.calibrate_button = self.button("Calibrate · 5 seconds",self.calibrate)
        for b in (self.start_button,self.pause_button,self.stop_button,self.demo_button,self.calibrate_button): controls.addWidget(b)
        layout.addLayout(controls)
        self.notice = QLabel("Ready. Start the camera, then calibrate while looking naturally at your screen.")
        self.notice.setWordWrap(True); self.notice.setObjectName("notice"); layout.addWidget(self.notice)
        self.tabs = QTabWidget(); layout.addWidget(self.tabs,1)
        support = QLabel('<a style="color:#a9cbff" href="https://ko-fi.com/Z3J629YD9V/">☕ Buy me a coffee on Ko-fi</a>')
        support.setOpenExternalLinks(True)
        support.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(support)
        page = QWidget(); page.setMinimumHeight(780)
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
        self.preview = CameraPreview("Camera off\nStart a session to see your local preview.")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview.setMinimumSize(400,210)
        self.preview.setObjectName("preview"); inner.addWidget(self.preview,1)
        self.signals = QLabel("Head and iris estimates appear after calibration."); self.signals.setWordWrap(True)
        inner.addWidget(self.signals); grid.addWidget(live,1,0)
        self.signal_badges = QLabel('Face —     Phone —     Camera off')
        self.signal_badges.setObjectName('signalBadges'); inner.addWidget(self.signal_badges)
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
        mission,mission_inner = self.panel('Session rhythm')
        rhythm = QHBoxLayout()
        self.goal_label = QLabel('Daily goal · 0 / 60 min'); rhythm.addWidget(self.goal_label)
        self.goal_progress = QProgressBar(); self.goal_progress.setRange(0,100); self.goal_progress.setTextVisible(False); rhythm.addWidget(self.goal_progress,2)
        self.break_label = QLabel('Next stretch · 30 min'); rhythm.addWidget(self.break_label)
        self.break_progress = QProgressBar(); self.break_progress.setRange(0,100); self.break_progress.setTextVisible(False); rhythm.addWidget(self.break_progress,1)
        mission_inner.addLayout(rhythm); grid.addWidget(mission,2,0,1,2)
        chart,inner = self.panel("Attention signal")
        self.chart = Chart(); inner.addWidget(self.chart); grid.addWidget(chart,3,0)
        week,inner = self.panel("Daily focus · real sessions only")
        self.week = Chart(True); inner.addWidget(self.week); grid.addWidget(week,3,1)
        self.footer = QLabel("Break timer 00:00 · Face absence and uncalibrated time are excluded from focus.")
        self.footer.setWordWrap(True); grid.addWidget(self.footer,4,0,1,2)
        grid.setColumnStretch(0,1); grid.setColumnStretch(1,1)
        grid.setRowStretch(1,2); grid.setRowStretch(3,1)
        self.build_settings()
        history = QWidget(); h = QVBoxLayout(history)
        h.addWidget(QLabel("Saved session summaries · demo sessions are labelled and excluded from daily focus."))
        self.history = QTableWidget(0,7); self.history.setHorizontalHeaderLabels(["Started","Mode","Source","Focus","Distraction","Streak","Alerts"])
        self.history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history.setAlternatingRowColors(True)
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
        self.tabs.currentChanged.connect(self.fade_tab)

    def fade_tab(self,index):
        if self.settings.reduced_motion: return
        widget = self.tabs.widget(index)
        effect = QGraphicsOpacityEffect(widget); widget.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect,b'opacity',self)
        animation.setDuration(190); animation.setStartValue(.45); animation.setEndValue(1.)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: widget.setGraphicsEffect(None))
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

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
        spin('animation_fps','Animation frames per second',15,60)
        combo('fire_edges','Screen fire placement',['All edges','Sides','Bottom'])
        check('screen_fire','Fire around screen edges (click-through)')
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
        path,_ = QFileDialog.getOpenFileName(self,"Choose a trusted local model", "", "YOLO models (*.onnx *.weights *.pt)")
        if path: self.modelpath.setText(path)

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.settings.accent),self)
        if color.isValid(): self.settings.accent = color.name(); self.apply_theme()

    def save_settings(self):
        for key,w in self.fields.items():
            value=w.isChecked() if isinstance(w,QCheckBox) else w.currentText() if isinstance(w,QComboBox) else w.text() if isinstance(w,QLineEdit) else w.value()
            setattr(self.settings,key,int(value) if key=='phone_size' else value)
        self.settings.phone_model = self.modelpath.text().strip()
        self.settings = self.settings.validated(); self.engine.settings = self.settings
        self.store.save_settings(self.settings); self.apply_theme()
        self.screen_fire.clear()
        self.update_scene()
        self.notice.setText("Settings saved. Camera/model changes apply after Stop and Start. Calibrate after moving the camera.")
        if not self.settings.overlay: self.overlay.hide()
        from .windows import set_startup
        try:
            if QApplication.platformName()=='windows':set_startup(self.settings.startup)
            self.hotkey_status.setText(self.hotkey.register(self.settings.global_pause,self.settings.pause_shortcut))
            self.store.prune(self.settings.retention_days,self.sid)
        except OSError as exc:self.notice.setText(f'Settings saved; Windows preference could not be applied: {exc}')

    def apply_theme(self):
        accent = self.settings.accent
        if not QColor(accent).isValid(): accent = "#40dfcf"
        self.setStyleSheet(f"""
            QMainWindow {{ background:#080d19; }}
            QWidget {{ background:transparent; color:#eaf0ff; font-family:'Segoe UI'; font-size:13px; }}
            QFrame#panel {{ background:transparent; border:0; }}
            QWidget#settingsSheet {{ background:rgba(10,24,40,215); border:1px solid #3c536d; border-radius:16px; }}
            QFrame#panel QLabel, QFrame#panel QWidget {{ background:transparent; }}
            QLabel#brand {{ font-size:30px; font-weight:750; color:#eff9ff; }}
            QLabel#metric {{ font-size:29px; font-weight:700; }}
            QLabel#sectionTitle {{ font-size:14px; color:#bdc9e5; font-weight:600; }}
            QLabel#muted {{ color:#94a5c7; }}
            QLabel#notice {{ background:rgba(39,64,88,150); border:1px solid #385771; border-left:3px solid {accent}; padding:10px; border-radius:9px; }}
            QLabel#signalBadges {{ color:{accent}; background:rgba(26,67,75,90); border-radius:7px; padding:7px; }}
            QLabel#preview {{ background:#090f1d; border-radius:10px; color:#97a7c5; }}
            QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #30425d,stop:1 #1c2b43); border:1px solid #506783; border-radius:9px; padding:10px 13px; }}
            QPushButton:hover {{ border-color:{accent}; background:#344662; }}
            QPushButton:focus {{ border:2px solid {accent}; }}
            QPushButton:disabled {{ color:#6e7b92; background:#182032; }}
            QPushButton#primary {{ background:{accent}; color:#0d1420; font-weight:700; }}
            QPushButton#primary:disabled {{ background:#234b50; color:#7fa3ab; border-color:#365d67; }}
            QTabWidget::pane {{ border:0; }}
            QTabBar::tab {{ background:rgba(25,39,62,180); padding:12px 23px; margin-right:6px; border-top-left-radius:10px; border-top-right-radius:10px; border-bottom:2px solid transparent; }}
            QTabBar::tab:selected {{ background:rgba(58,81,112,190); color:{accent}; border-bottom:2px solid {accent}; }}
            QSpinBox,QDoubleSpinBox,QComboBox,QLineEdit {{ padding:7px; background:#202b43; border:1px solid #455674; border-radius:5px; }}
            QTableWidget {{ background:rgba(12,26,43,230);gridline-color:#34405c;alternate-background-color:#1c263c;border-radius:10px; }}
            QHeaderView::section {{ background:#283550; padding:9px; border:0; }}
            QScrollArea {{ border:0; }}
            QScrollBar:vertical {{ background:#121e31; width:9px; margin:0; }}
            QScrollBar::handle:vertical {{ background:#4a607e; min-height:30px; border-radius:4px; }}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0; }}
            QProgressBar {{ background:#111e31; border:1px solid #3d536e; border-radius:5px; max-height:10px; min-height:10px; }}
            QProgressBar::chunk {{ background:{accent}; border-radius:4px; }}
        """)
        self.chart.accent = self.week.accent = self.ring.accent = accent
        self.ring.reduced = self.settings.reduced_motion
        for m in (self.mascot,self.overlay):
            m.personality = self.settings.personality; m.reduced = self.settings.reduced_motion
            m.fire = self.settings.fire; m.intensity = self.settings.intensity
            m.name=self.settings.goblin_name; m.body_color=self.settings.goblin_color
            m.follow_cursor=self.settings.cursor_follow; m.poke_enabled=self.settings.poke_reaction
            m.timer.setInterval(round(1000/max(15,min(60,self.settings.animation_fps))))
        for panel in self.findChildren(GlassPanel):
            panel.accent = accent; panel.quiet = self.settings.style == 'Quiet graphite'; panel.update()
        scene=self.centralWidget()
        scene.scene_name=self.settings.background;scene.motion=self.settings.background_motion and not self.settings.reduced_motion
        scene.blur_enabled=self.settings.glass_blur;scene.update()
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
        self.preview.setProperty('demo',demo)
        self.engine = AttentionEngine(copy.deepcopy(self.settings))
        if demo: self.engine.settings.calibrated = True
        self.sid = self.store.start(self.settings.mode,demo)
        self.samples.clear(); self.last_sample = 0; self.last_state = "ready"
        self.last_tick = time.monotonic(); self.pause_button.setText("Pause")
        self.plan_started()
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
            self.overlay.hide(); self.calibration = None;self.phone_check=None
            self.screen_fire.clear(); self.preview_until = 0.
            if hasattr(self,'sound_effect'): self.sound_effect.stop()
            self.engine.take_break()
            self.pause_button.setText("Resume"); self.store.event(self.sid,"pause","User paused monitoring")
        elif not self.busy():
            self.paused = False; self.pause_button.setText("Pause")
            if not self.demo: self.start_worker()
            self.last_tick = time.monotonic(); self.show_overlay()

    def stop(self):
        self.preview_until = 0.; self.screen_fire.clear()
        if hasattr(self,'sound_effect'): self.sound_effect.stop()
        if self.worker: self.worker.stop()
        if self.sid is not None:
            self.store.checkpoint(self.sid,self.engine.summary(),True)
            self.sid = None
        self.paused = False; self.calibration = None;self.phone_check=None
        self.preview.clear(); self.preview.setText("Camera off / closing\nNo images are recorded.")
        self.preview.setProperty('demo',False)
        self.overlay.hide(); self.mascot.state = "ready"
        self.pause_button.setText("Pause"); self.start_button.setEnabled(True); self.demo_button.setEnabled(True)
        self.notice.setText("Monitoring stopped. Session saved locally.")
        self.refresh_history()

    def calibrate(self):
        if self.sid is None or self.demo or self.paused:
            self.notice.setText("Start a real camera session before calibration."); return
        self.engine.settings.calibrated = False
        self.calibration = (time.monotonic(),[])
        self.notice.setText("Calibrating: look naturally at the screen for 5 seconds. Keep your face still.")

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
        elif action == 'poke' and self.settings.poke_reaction:self.preview_reaction()

    def preview_reaction(self):
        self.preview_until = time.monotonic()+4
        self.update_scene(); self.show_overlay()
        self.shriek()
        QTimer.singleShot(4000,lambda: self.restore_mascot())

    def restore_mascot(self):
        self.update_scene()

    def update_scene(self):
        state = 'angry' if time.monotonic() < self.preview_until else self.engine.state if self.sid and not self.paused else 'ready'
        if time.monotonic()<getattr(self,'silenced_until',0):state='calming'
        self.mascot.state = self.overlay.state = state
        self.screen_fire.configure(state == 'angry' and self.settings.personality not in ('Chill Monitor','Motivational Coach'),self.settings)

    def take_break(self):
        if self.sid:
            self.engine.take_break(); self.store.event(self.sid,"break","User requested break")
            if not self.paused: self.pause()
        self.mascot.state = self.overlay.state = "break"; self.show_overlay()
        self.screen_fire.clear()
        self.notice.setText("Break time. Monitoring is paused. Stand, stretch, walk; press Resume when ready.")

    def shriek(self):
        if not self.settings.sound: return
        custom=Path(self.settings.custom_sound)
        path = custom if self.settings.custom_sound and custom.is_file() else data_dir()/f"goblin-{self.settings.personality.replace(' ','-')}.wav"
        if not path.exists():
            with wave.open(str(path),"wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
                audio = bytearray()
                for i in range(14000):
                    t = i/22050
                    base={'Angry Goblin':370,'Meme Machine':510,'Motivational Coach':270,'Sarcastic Supervisor':310,'Chill Monitor':190}.get(self.settings.personality,370)
                    value = math.sin(2*math.pi*(base*t+85*t*t)+1.4*math.sin(2*math.pi*26*t))
                    audio.extend(struct.pack("<h",int(9500*math.sin(math.pi*i/14000)*value)))
                w.writeframes(audio)
        if not hasattr(self,"sound_effect"):self.sound_effect = QSoundEffect(self)
        url=QUrl.fromLocalFile(str(path))
        if self.sound_effect.source()!=url:self.sound_effect.setSource(url)
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
            obs.phone_score=.8 if obs.phone else 0.;obs.phone_status='simulated';obs.light_level=128.
        elif self.worker:
            result = self.worker.take()
            if result:
                obs,image,stamp,latency = result
                self.last_frame = stamp
                self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
                self.signals.setText(f"Head ratios {obs.yaw:+.2f} / {obs.pitch:+.2f} · Iris {obs.gaze_x:.2f} / {obs.gaze_y:.2f}\n"
                    f"Phone {obs.phone_status} · score {obs.phone_score:.0%} · face light {obs.light_level:.0f}/255 · gamma {obs.light_gain:.2f}\nProcessing {latency*1000:.0f} ms")
                if self.calibration:
                    began,points = self.calibration
                    if obs.face and obs.eyes_open: points.append((obs.yaw,obs.pitch,obs.gaze_x,obs.gaze_y))
                    if now-began >= 5:
                        if len(points) >= 10:
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
        self.update_scene()
        self.state_label.setText(decision.state.capitalize()+"\nEstimated attention")
        self.ring.value = decision.confidence; self.ring.update()
        self.footer.setText(f"Break timer {duration(self.engine.since_break)} / {self.settings.break_minutes}m · Goal {self.settings.goal_minutes}m/day · "
            f"Distractions {self.engine.distractions} · Phone events {self.engine.phone_events} · "
            f"Absent {duration(self.engine.absent)} · Unobserved/grace {duration(self.engine.unknown)}\n{decision.reason}")
        for key,label in self.metrics.items():
            label.setText(str(self.engine.alerts) if key == "alerts" else duration(getattr(self.engine,key)))
        if decision.state != self.last_state:
            self.store.event(self.sid,"state",decision.state+": "+decision.reason); self.last_state = decision.state
        if decision.alert and now>=self.silenced_until:
            self.store.event(self.sid,"alert",self.settings.personality); self.shriek(); self.show_overlay()
            self.notice.setText(f'{self.settings.goblin_name}: {decision.reason}. Away evidence {self.engine.away:.1f}s; phone confidence {self.observation.phone_score:.0%}. Use False alarm if this is expected work.')
        if self.engine.active-self.last_sample >= 1:
            self.last_sample = self.engine.active; self.samples.append(decision.confidence)
            self.chart.values = list(self.samples); self.chart.update()
            self.store.sample(self.sid,self.engine.active,decision.confidence,decision.state)
            self.store.checkpoint(self.sid,self.engine.summary())
            self.refresh_daily()
            self.signal_badges.setText(f"Face {'visible' if self.observation.face else 'absent'}     Phone {'visible' if self.observation.phone else 'not detected / off'}     {'Demo' if self.demo else 'Camera live'}")
            remaining = max(0,self.settings.break_minutes*60-self.engine.since_break)
            self.break_label.setText(f'Next stretch · {duration(remaining)}')
            self.break_progress.setValue(round(self.engine.since_break/(self.settings.break_minutes*60)*100))
        if self.engine.break_due():
            self.store.event(self.sid,"reminder","Elapsed monitoring break reminder")
            self.take_break()
        self.update_workspace(decision)

    def refresh_history(self):
        rows = self.store.history(); self.history_ids=[r[0] for r in rows]; self.history.setRowCount(len(rows))
        for i,(sid,started,mode,demo,payload) in enumerate(rows):
            s = json.loads(payload)
            name,_,_=self.store.plan(sid)
            values = [started[:16].replace("T"," "),mode+' / '+name,"Demo" if demo else "Camera",duration(s.get("focus",0)),duration(s.get("distracted",0)),duration(s.get("longest",0)),str(s.get("alerts",0))]
            for j,v in enumerate(values): self.history.setItem(i,j,QTableWidgetItem(v))
        self.refresh_daily()
        if hasattr(self,'analytics_chart'):self.refresh_analytics()

    def refresh_daily(self):
        self.week.values = self.store.daily(); self.week.update()
        today_focus = self.week.values[-1][1] if self.week.values else 0
        self.goal_label.setText(f'Daily goal · {today_focus/60:.0f} / {self.settings.goal_minutes} min')
        self.goal_progress.setValue(round(min(100,today_focus/(self.settings.goal_minutes*60)*100)))

    def export(self):
        path,_ = QFileDialog.getSaveFileName(self,"Export summaries","focus-sessions.csv","CSV (*.csv)")
        if path: self.store.export(path); self.notice.setText("Session summaries exported. No camera frames included.")

    def closeEvent(self,event):
        self.stop()
        if self.busy():
            self.notice.setText("Releasing camera before closing…")
            event.ignore(); QTimer.singleShot(250,self.close); return
        self.hotkey.close()
        if self.tray:self.tray.hide()
        self.screen_fire.clear(); self.overlay.close(); self.store.close(); event.accept()
