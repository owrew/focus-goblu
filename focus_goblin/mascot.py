"""Resolution-independent, original Qt vector animation. No external art needed."""
import math
import time
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QFont, QLinearGradient
from PySide6.QtWidgets import QWidget, QApplication, QMenu

LINES = {
    "Angry Goblin": ("THE TASK. IT MISSES YOU!", "Good. Back to work."),
    "Meme Machine": ("Phone side quest detected.", "Focus arc unlocked."),
    "Motivational Coach": ("One small step. You've got this.", "Nice return. Keep going."),
    "Sarcastic Supervisor": ("Fascinating. Is the phone doing the work?", "Productivity has rejoined the chat."),
    "Chill Monitor": ("Hey. Ready to come back?", "Welcome back, friend."),
}


class Mascot(QWidget):
    action = Signal(str)
    def __init__(self, overlay=False):
        super().__init__()
        self.overlay = overlay
        self._state = "ready"
        self._previous = None
        self._transition = 1.
        self._anger = 0.
        self._last_tick = time.monotonic()
        self.personality = "Angry Goblin"
        self.phase = 0.
        self.reduced = False
        self.fire = True
        self.intensity = 2
        self.drag = None
        self.anchor = None
        self.resize(310 if overlay else 390, 245 if overlay else 310)
        if overlay:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setToolTip("Focus Goblin desktop pet · drag to move · right-click for controls · double-click to hide")
            rect = QApplication.primaryScreen().availableGeometry()
            self.move(rect.right()-self.width()-20, rect.bottom()-self.height()-20)
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.animate)
        self.timer.start(33)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self,value):
        if value == self._state: return
        self._previous = self.grab() if self.isVisible() and not self.reduced else None
        self._transition = 0. if self._previous is not None else 1.
        self._state = value

    def animate(self):
        now = time.monotonic(); dt = min(.1,now-self._last_tick); self._last_tick = now
        self.phase += dt
        self._transition = min(1.,self._transition+dt/.45)
        if self._transition >= 1: self._previous = None
        target_anger = 1. if self.state == 'angry' else .35 if self.state == 'warning' else 0.
        self._anger += (target_anger-self._anger)*(1-math.exp(-dt*7))
        if self.overlay and self.anchor and self.drag is None:
            rect = self.screen().availableGeometry()
            travel = math.sin(self.phase*1.8)*min(260,rect.width()/4)*self._anger if self.intensity > 1 and not self.reduced else 0
            x = max(rect.left(),min(rect.right()-self.width(),self.anchor.x()+travel))
            easing = 1 if self.reduced else 1-math.exp(-dt*7)
            self.move(round(self.x()+(x-self.x())*easing),round(self.y()+(self.anchor.y()-self.y())*easing))
        self.update()

    def showEvent(self, event):
        self._last_tick = time.monotonic()
        self.timer.start(self.timer.interval())
        if self.overlay and self.anchor is None:
            self.anchor = self.pos()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def mousePressEvent(self, e):
        if self.overlay and e.button() == Qt.MouseButton.LeftButton:
            self.drag = e.globalPosition().toPoint() - self.pos()

    def contextMenuEvent(self, event):
        if not self.overlay:
            return
        menu = QMenu(self)
        for label,key in [('Open dashboard','dashboard'),('Pause / resume monitoring','pause'),('Take a break','break'),('Stop monitoring and hide pet','stop'),('Hide pet','hide')]:
            item = menu.addAction(label)
            item.triggered.connect(lambda checked=False,k=key: self.action.emit(k))
        menu.exec(event.globalPos())

    def mouseMoveEvent(self, e):
        if self.drag is not None:
            self.move(e.globalPosition().toPoint()-self.drag)
            self.anchor = self.pos()

    def mouseReleaseEvent(self, e):
        self.drag = None

    def mouseDoubleClickEvent(self, e):
        if self.overlay:
            self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.width()/390, self.height()/310)
        blend = self._transition*self._transition*(3-2*self._transition)
        if self._previous is not None: p.setOpacity(blend)
        t = 0 if self.reduced else self.phase
        angry = self.state == "angry"
        sloth = self.state == "break"
        p.setPen(Qt.PenStyle.NoPen)
        def ellipse(x,y,w,h,color):
            p.setBrush(QColor(color)); p.drawEllipse(QRectF(x,y,w,h))
        def poly(points,color):
            p.setBrush(QColor(color)); p.drawPolygon(QPolygonF([QPointF(x,y) for x,y in points]))
        # Cave, with layered crystal edges and a dark mouth.
        poly([(58,274),(76,169),(130,112),(248,116),(310,181),(333,274)],"#32394f")
        poly([(76,274),(95,185),(145,139),(233,142),(290,195),(311,274)],"#1c2337")
        ellipse(113,161,166,141,"#080c19")
        poly([(80,241),(99,205),(109,249)],"#a58aff")
        poly([(276,253),(294,215),(306,257)],"#40dfcf")
        p.setPen(QPen(QColor("#697592"),2)); p.drawLine(58,276,334,276)
        p.setPen(Qt.PenStyle.NoPen)
        bob = math.sin(t*3)*3
        x = 195 + (math.sin(t*5)*17 if angry and self.intensity > 1 else 0)
        y = 214+bob+16*(1-self._anger) if not sloth else 214+bob
        p.save(); p.translate(x,y)
        if angry and self.intensity > 1:
            p.rotate(math.sin(t*19)*5)
        if sloth:
            # Chair, rising sloth, and stretching arms.
            p.setPen(QPen(QColor("#9b89ce"),8)); p.drawLine(-42,20,42,20); p.drawLine(30,20,30,65)
            p.setPen(Qt.PenStyle.NoPen)
            p.translate(0,-16-abs(math.sin(t*2))*15)
            ellipse(-35,-12,70,72,"#99765a")
            ellipse(-47,-65,94,83,"#c9aa80")
            ellipse(-36,-53,72,55,"#eed9b2")
            for sign in (-1,1):
                ellipse(sign*21-12,-42,25,19,"#6e5146")
                ellipse(sign*21-4,-37,8,8,"#151826")
                p.setPen(QPen(QColor("#99765a"),14,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
                p.drawLine(sign*25,10,sign*68,int(-30-abs(math.sin(t*2))*25))
            p.setPen(Qt.PenStyle.NoPen); ellipse(-7,-23,14,9,"#402e2b")
        else:
            cool,hot = QColor('#70d5ad'),QColor('#ef757b')
            skin = QColor.fromRgbF(*[cool.getRgbF()[i]+(hot.getRgbF()[i]-cool.getRgbF()[i])*self._anger for i in range(3)]).name()
            # Boots run, arms stomp, head reacts.
            ellipse(-36,31+math.sin(t*12)*5,32,17,"#554779")
            ellipse(8,31-math.sin(t*12)*5,32,17,"#554779")
            ellipse(-41,-16,82,61,"#7462ad")
            poly([(-39,-56),(-86,-83),(-62,-20),(-33,-20)],skin)
            poly([(39,-56),(86,-83),(62,-20),(33,-20)],skin)
            ellipse(-57,-81,114,94,'#183744')
            ellipse(-54,-84,108,94,skin)
            ellipse(-38,-26,21,9,'#e69aa0' if angry else '#49b899')
            ellipse(18,-26,21,9,'#e69aa0' if angry else '#49b899')
            poly([(-38,-80),(-27,-108),(-10,-82)],"#c0f1c7")
            poly([(16,-84),(33,-108),(39,-76)],"#c0f1c7")
            eye_h = 2 if .12 < t%5.1 < .24 and not self.reduced else 23
            for sign in (-1,1):
                ellipse(sign*22-16,-52,32,eye_h,"#fff3ce")
                ellipse(sign*22-5+math.sin(t*1.2)*4,-48,10,max(2,eye_h-5),"#172431")
            p.setPen(QPen(QColor("#314233"),6,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
            p.drawLine(-38,-63,-9,-55 if angry else -65)
            p.drawLine(9,-55 if angry else -65,38,-63)
            p.setPen(Qt.PenStyle.NoPen)
            ellipse(-19,-15,38,28 if angry else 9,"#33273d")
            poly([(-13,-14),(-7,-1),(-2,-14)],"#fff6df")
            poly([(3,-14),(9,-1),(15,-14)],"#fff6df")
            arm = math.sin(t*11)*18 if angry else math.sin(t*2)*4
            p.setPen(QPen(QColor(skin),15,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
            p.drawLine(-35,2,-65,int(15-arm)); p.drawLine(35,2,65,int(15+arm))
            p.setPen(Qt.PenStyle.NoPen)
            if angry:
                # Two halves of a purely cartoon phone, and impact star.
                p.save(); p.translate(65,35); p.rotate(math.sin(t*6)*20)
                p.setBrush(QColor("#1a2138")); p.drawRoundedRect(QRectF(-14,-20,28,23),4,4)
                p.drawRoundedRect(QRectF(-10,9,28,23),4,4)
                p.setBrush(QColor("#7ce3ef")); p.drawRect(QRectF(-9,-15,18,12))
                p.restore()
                poly([(45,30),(57,21),(55,34),(70,32),(59,42),(63,55),(50,46),(40,53),(44,40),(32,37)],"#ffcc69")
        p.restore()
        if not sloth:
            p.save(); p.setOpacity(p.opacity()*(1-self._anger))
            ellipse(113,244,166,34,'#080c19')
            p.restore()
        if angry and self.fire:
            for i in range(7 if self.intensity > 1 else 3):
                fx = 42+i*47
                height = 34+abs(math.sin(t*7+i))*42
                poly([(fx-18,276),(fx-12,243),(fx,276-height),(fx+8,250),(fx+19,276)],"#ff7355")
                poly([(fx-9,276),(fx,254-height*.3),(fx+10,276)],"#ffd578")
        if sloth:
            line = "Stand, stretch, take a short walk."
        elif angry:
            line = LINES.get(self.personality,LINES["Angry Goblin"])[0]
        elif self.state == "calming":
            line = LINES.get(self.personality,LINES["Angry Goblin"])[1]
        else:
            line = "Your tiny guardian is watching."
        if not self.overlay or angry or sloth or self.state == 'calming':
            p.setBrush(QColor("#172137")); p.setPen(QPen(QColor("#465574"),1))
            p.drawRoundedRect(QRectF(10,10,370,53),14,14)
            p.setPen(QColor("#f0f3ff")); p.setFont(QFont("Segoe UI",10,QFont.Weight.DemiBold))
            p.drawText(QRectF(20,13,350,46),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,line)
        if self._previous is not None:
            p.resetTransform(); p.setOpacity(1-blend); p.drawPixmap(self.rect(),self._previous)
        p.end()
