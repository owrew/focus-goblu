"""Desktop pet, anime poses, cave scenery and overlay choreography."""
import math
import time
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QLinearGradient, QCursor, QPainterPath, QPixmap
from PySide6.QtWidgets import QWidget, QApplication, QMenu
from .visuals import ASSETS

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
        self.nap_remaining = 0.
        self.greet_until = 0.
        self.state_started = time.monotonic()
        self.sprites = {}
        for name,poses in (
            ('anime-goblin.png',('idle','angry','drink','sleep')),
            ('anime-motion.png',('wake','run1','run2','greet')),
        ):
            sheet = QPixmap(str(ASSETS/name))
            if sheet.isNull():
                continue
            width,height = sheet.width()//2,sheet.height()//2
            for index,pose in enumerate(poses):
                sprite = sheet.copy(index%2*width,index//2*height,width,height)
                self.sprites[pose] = sprite.scaled(340,340,Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
        self._state = "ready"
        self._previous = None
        self._transition = 1.
        self._anger = 0.
        self._last_tick = time.monotonic()
        self.personality = "Angry Goblin"
        self.name='Grumble';self.body_color='#70d5ad';self.follow_cursor=True;self.poke_enabled=True
        self.pointer=(0.,0.);self.press_point=None
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
            self.setToolTip("Focus Goblin desktop pet · drag to move · right-click for controls · double-click to greet")
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
        self.state_started = time.monotonic()

    def animate(self):
        now = time.monotonic(); dt = min(.1,now-self._last_tick); self._last_tick = now
        self.phase += dt
        if self.follow_cursor:
            cursor=self.mapFromGlobal(QCursor.pos())
            target=(max(-1.,min(1.,(cursor.x()-self.width()/2)/160)),max(-1.,min(1.,(cursor.y()-self.height()/2)/160)))
            self.pointer=tuple(a+(b-a)*.18 for a,b in zip(self.pointer,target))
        self._transition = min(1.,self._transition+dt/.45)
        if self._transition >= 1: self._previous = None
        target_anger = 1. if self.state == 'angry' else .45 if self.state == 'warning' else .20 if self.state == 'watching' else 0.
        if self.personality in ('Chill Monitor','Motivational Coach'):target_anger*=.4
        self._anger += (target_anger-self._anger)*(1-math.exp(-dt*7))
        if self.overlay and self.anchor and self.drag is None:
            rect = self.screen().availableGeometry()
            age = now-self.state_started
            room_left = self.anchor.x()-rect.left()
            room_right = rect.right()-self.width()-self.anchor.x()
            side = -1 if room_left > room_right else 1
            duration = 2.6 if self.personality == 'Angry Goblin' else 2.2
            run = math.sin(math.pi*min(1.,age/duration))
            fierce = self.personality in ('Angry Goblin','Sarcastic Supervisor')
            travel = side*run*min(280,max(room_left,room_right)) if (
                self.state == 'angry' and fierce and self.intensity > 1 and not self.reduced) else 0
            x = max(rect.left(),min(rect.right()-self.width(),self.anchor.x()+travel))
            y = max(rect.top(),min(rect.bottom()-self.height(),self.anchor.y()))
            easing = 1 if self.reduced else 1-math.exp(-dt*7)
            self.move(round(self.x()+(x-self.x())*easing),round(self.y()+(y-self.y())*easing))
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
        if e.button() == Qt.MouseButton.LeftButton:
            self.press_point=e.globalPosition().toPoint()
            if self.overlay:self.drag = e.globalPosition().toPoint() - self.pos()

    def contextMenuEvent(self, event):
        if not self.overlay:
            return
        menu = QMenu(self)
        for label,key in [('Open dashboard','dashboard'),('Pause / resume monitoring','pause'),('Take a break','break'),('Sleep the goblin','sleep'),('Greet','wave'),('Stop monitoring and hide pet','stop'),('Hide pet','hide')]:
            item = menu.addAction(label)
            item.triggered.connect(lambda checked=False,k=key: self.action.emit(k))
        menu.exec(event.globalPos())

    def mouseMoveEvent(self, e):
        if self.drag is not None:
            self.move(e.globalPosition().toPoint()-self.drag)
            self.anchor = self.pos()

    def mouseReleaseEvent(self, e):
        if self.press_point is not None and (e.globalPosition().toPoint()-self.press_point).manhattanLength()<6 and self.poke_enabled:
            self.action.emit('poke')
        self.drag = None
        self.press_point=None

    def mouseDoubleClickEvent(self, e):
        self.press_point = None
        self.action.emit('wave')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scale = min(self.width()/390, self.height()/310)
        p.translate((self.width()-390*scale)/2,(self.height()-310*scale)/2)
        p.scale(scale,scale)
        blend = self._transition*self._transition*(3-2*self._transition)
        if self._previous is not None: p.setOpacity(blend)
        t = 0 if self.reduced else self.phase
        angry = self.state == "angry"
        sloth = self.state == "break"
        p.setPen(Qt.PenStyle.NoPen)
        def ellipse(x,y,w,h,color):
            p.setBrush(QColor(color)); p.drawEllipse(QRectF(x,y,w,h))
        cave = QPainterPath(QPointF(61,268))
        cave.cubicTo(74,224,69,176,109,152)
        cave.cubicTo(132,132,143,91,193,89)
        cave.cubicTo(240,90,244,117,269,135)
        cave.cubicTo(299,151,311,217,329,268)
        cave.closeSubpath()
        rock = QLinearGradient(83,103,310,271)
        rock.setColorAt(0,QColor('#506876')); rock.setColorAt(.47,QColor('#263647')); rock.setColorAt(1,QColor('#0c1525'))
        p.fillPath(cave,rock)
        p.setPen(QPen(QColor(146,189,198,140),1.4)); p.drawPath(cave)
        p.setPen(Qt.PenStyle.NoPen)
        ellipse(111,124,169,151,"#091220")
        glow = QColor(self.body_color)
        if not glow.isValid(): glow = QColor('#70d5ad')
        glow.setAlpha(100)
        ellipse(72,246,244,36,glow)
        ellipse(82,247,225,26,'#18283a')
        bob = math.sin(t*3)*3
        p.save(); p.translate(195,214+bob)
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
            p.restore()
            age = time.monotonic()-self.state_started
            greeting = time.monotonic() < self.greet_until
            fierce = self.personality in ('Angry Goblin','Sarcastic Supervisor')
            duration = 2.6 if self.personality == 'Angry Goblin' else 2.2
            running = angry and self.intensity > 1 and fierce and .25 < age < duration and not self.reduced
            pose = self.state if self.state in ('drink','sleep','wake') else (
                'run1' if running and int(age*9)%2 == 0 else 'run2' if running else
                'angry' if angry and fierce else 'greet' if greeting or angry else 'idle')
            sprite = self.sprites.get(pose,self.sprites.get('angry' if angry and fierce else 'idle'))
            if sprite is not None:
                emergence = self._anger if self.state not in ('sleep','drink','wake') else 1
                x = 195 + self.pointer[0]*6
                y = 160 + (1-emergence)*14 + bob
                if running:
                    y -= abs(math.sin(age*20))*12
                if pose == 'sleep':
                    y += 17
                if pose == 'wake' and not self.reduced:
                    y -= math.sin(min(1,age/2)*math.pi)*18
                scale = 1.0+.13*emergence
                if pose == 'sleep' and not self.reduced:
                    scale += math.sin(t*2)*.019
                p.save()
                p.translate(x,y)
                p.rotate(self.pointer[0]*2 if pose in ('idle','greet') and self.follow_cursor and not self.reduced else 0)
                if running:
                    screen = self.screen().availableGeometry()
                    anchor = self.anchor.x() if self.anchor else self.x()
                    facing_left = anchor-screen.left() > screen.right()-self.width()-anchor
                    if facing_left != (age > duration/2):
                        p.scale(-1,1)
                p.scale(scale,scale)
                p.drawPixmap(QRectF(-99,-99,198,198),sprite,QRectF(sprite.rect()))
                p.restore()
            if self.state in ('ready','focused','watching','warning','calming') and not greeting:
                # The cave lip occludes the feet until the pet steps outside.
                p.save(); p.setOpacity(p.opacity()*(1-self._anger))
                ellipse(103,249,184,23,'#18283a')
                p.restore()
            if self.state == 'sleep':
                p.setFont(QFont('Segoe UI',10,QFont.Weight.DemiBold))
                for i in range(3):
                    rise = (0.35+i*.30 if self.reduced else (t*.58+i*.33)%1)
                    p.save(); p.setOpacity(p.opacity()*math.sin(rise*math.pi))
                    x,y = 218+rise*73,159-rise*64
                    ellipse(x,y,13+i*4,13+i*4,'#537b99')
                    p.setPen(QColor('#dcf1ff')); p.drawText(QPointF(x+4,y+11),'z')
                    p.restore()
            if angry and fierce and age >= 2.2:
                self.draw_impact(p,t)
            if angry and fierce and self.fire:
                for i in range(5):
                    x = 72+i*61
                    rise = (t*1.3+i*.21)%1 if not self.reduced else .4
                    p.save(); p.setOpacity(p.opacity()*(1-rise))
                    ellipse(x+math.sin(rise*4)*16,262-rise*55,5,9,'#ffc879')
                    p.restore()
        if sloth:
            p.restore()
        if sloth:
            line = "Stand, stretch, take a short walk."
        elif self.state in ('drink','sleep'):
            left = math.ceil(self.nap_remaining)
            line = f"Nap  {left//60:02d}:{left%60:02d}"
        elif self.state == 'wake':
            line = "A big stretch. Back on duty."
        elif time.monotonic() < self.greet_until:
            line = f"{self.name} says hello."
        elif self.state == 'warning':
            line = "Still working on your task?"
        elif angry:
            line = LINES.get(self.personality,LINES["Angry Goblin"])[0]
        elif self.state == "calming":
            line = LINES.get(self.personality,LINES["Angry Goblin"])[1]
        else:
            line = f"{self.name} is watching."
        if not self.overlay or angry or sloth or self.state in ('warning','calming','drink','sleep','wake') or time.monotonic() < self.greet_until:
            p.setBrush(QColor("#172137")); p.setPen(QPen(QColor("#465574"),1))
            p.drawRoundedRect(QRectF(10,10,370,53),14,14)
            p.setPen(QColor("#f0f3ff")); p.setFont(QFont("Segoe UI",10,QFont.Weight.DemiBold))
            p.drawText(QRectF(20,13,350,46),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,line)
        p.setPen(QColor('#d1e7f2'));p.setFont(QFont('Segoe UI',9,QFont.Weight.DemiBold))
        p.drawText(QRectF(50,281,290,24),Qt.AlignmentFlag.AlignCenter,self.name)
        if self._previous is not None:
            p.resetTransform(); p.setOpacity(1-blend); p.drawPixmap(self.rect(),self._previous)
        p.end()

    def draw_impact(self, painter, phase):
        painter.save()
        painter.translate(289,229)
        painter.rotate(math.sin(phase*7)*12)
        painter.setPen(QPen(QColor('#d8be8c'),1.5))
        painter.setBrush(QColor('#172d40'))
        painter.drawRoundedRect(QRectF(-14,-22,25,21),4,4)
        painter.drawRoundedRect(QRectF(-7,7,25,21),4,4)
        painter.setPen(QPen(QColor('#f9b56e'),2))
        for i in range(7):
            angle = i*math.tau/7
            painter.drawLine(QPointF(math.cos(angle)*18,math.sin(angle)*14),
                             QPointF(math.cos(angle)*32,math.sin(angle)*26))
        painter.restore()
