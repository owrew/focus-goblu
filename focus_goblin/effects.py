"""Bounded, click-through flame strips; never paints onto real desktop content."""
import math
import time
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient
from PySide6.QtWidgets import QApplication, QWidget


class FlameStrip(QWidget):
    def __init__(self, screen, edge):
        super().__init__()
        self.edge = edge
        self.phase = 0.
        self.strength = 0.
        self.reduced = False
        self.intensity = 2
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        r = screen.geometry()
        depth = 76
        if edge == 'bottom': self.setGeometry(r.left(),r.bottom()-depth+1,r.width(),depth)
        elif edge == 'top': self.setGeometry(r.left(),r.top(),r.width(),depth)
        elif edge == 'left': self.setGeometry(r.left(),r.top(),depth,r.height())
        else: self.setGeometry(r.right()-depth+1,r.top(),depth,r.height())

    def paintEvent(self,event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self.strength*.82)
        if self.edge == 'top': p.translate(self.width(),self.height()); p.rotate(180)
        elif self.edge == 'left': p.translate(0,self.height()); p.rotate(-90)
        elif self.edge == 'right': p.translate(self.width(),0); p.rotate(90)
        width = self.height() if self.edge in ('left','right') else self.width()
        depth = self.width() if self.edge in ('left','right') else self.height()
        t = 0 if self.reduced else self.phase
        glow = QLinearGradient(0,depth,0,0)
        glow.setColorAt(0,QColor(255,91,52,125)); glow.setColorAt(1,QColor(255,91,52,0))
        p.fillRect(QRectF(0,0,width,depth),glow)
        p.setPen(Qt.PenStyle.NoPen)
        spacing = 38 if self.intensity > 1 else 66
        for i in range(int(width/spacing)+2):
            x = i*spacing
            height = (25+23*(.5+.5*math.sin(t*3.8+i*1.7)))*(0.7+self.intensity*.13)
            sway = math.sin(t*2.7+i)*10
            path = QPainterPath(); path.moveTo(x-23,depth)
            path.cubicTo(x-34,depth-height*.35,x-4+sway,depth-height*.45,x+sway,depth-height)
            path.cubicTo(x+20+sway,depth-height*.45,x+31,depth-height*.3,x+22,depth)
            path.closeSubpath()
            fill = QLinearGradient(x,depth,x,depth-height)
            fill.setColorAt(0,QColor('#ffbd5c')); fill.setColorAt(.5,QColor('#ff704f')); fill.setColorAt(1,QColor('#fc496b'))
            p.setBrush(fill); p.drawPath(path)
            p.setBrush(QColor('#ffe4a1')); p.drawEllipse(QRectF(x-6,depth-height*.35,12,height*.5))
        p.end()


class ScreenFire:
    def __init__(self):
        self.windows = []
        self.amount = self.target = 0.
        self.last = time.monotonic()
        self.timer = QTimer(); self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        QApplication.instance().screenRemoved.connect(lambda screen: self.clear())
        QApplication.instance().screenAdded.connect(lambda screen: self.clear())

    def configure(self, active, settings):
        self.target = 1. if active and settings.overlay and settings.fire and settings.screen_fire else 0.
        if self.target and not self.windows:
            edges = ['bottom'] if settings.fire_edges == 'Bottom' else ['left','right'] if settings.fire_edges == 'Sides' else ['top','bottom','left','right']
            self.windows = [FlameStrip(screen,edge) for screen in QApplication.screens() for edge in edges]
        for w in self.windows:
            w.reduced = settings.reduced_motion; w.intensity = settings.intensity
        if self.target or self.windows:
            if not self.timer.isActive(): self.last = time.monotonic(); self.timer.start(33)

    def tick(self):
        now = time.monotonic(); dt = min(now-self.last,.1); self.last = now
        self.amount += (self.target-self.amount)*(1-math.exp(-dt*7))
        for w in self.windows:
            w.phase += dt; w.strength = self.amount
            if not w.isVisible(): w.show()
            w.update()
        if self.target == 0 and self.amount < .015:
            self.clear()

    def clear(self):
        self.timer.stop()
        for w in self.windows: w.close(); w.deleteLater()
        self.windows = []; self.amount = self.target = 0.
