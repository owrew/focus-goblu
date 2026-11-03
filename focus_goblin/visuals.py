"""Native lightweight glass panels and smooth score movement."""
from pathlib import Path
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QRadialGradient, QPen
from PySide6.QtWidgets import QWidget, QFrame, QLabel

ASSETS = Path(__file__).parent/'assets'


class CameraPreview(QLabel):
    def paintEvent(self,event):
        if not self.property('demo'):
            return super().paintEvent(event)
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2,2,-2,-2)
        p.fillRect(r,QColor('#091626'))
        cx,cy = self.width()/2,self.height()/2
        p.setPen(QPen(QColor('#26435c'),1,Qt.PenStyle.DashLine))
        p.drawLine(15,int(cy),self.width()-15,int(cy)); p.drawLine(int(cx),15,int(cx),self.height()-15)
        p.drawEllipse(QRectF(cx-86,cy-93,172,186))
        p.setPen(QPen(QColor('#5bdfc3'),2))
        p.drawRoundedRect(QRectF(cx-62,cy-78,124,146),44,44)
        for sign in (-1,1):
            p.drawEllipse(QRectF(cx+sign*28-13,cy-31,26,15))
            p.setBrush(QColor('#b1fff1')); p.drawEllipse(QRectF(cx+sign*28-3,cy-27,6,6)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(int(cx),int(cy-12),int(cx-5),int(cy+17))
        p.drawLine(int(cx-22),int(cy+39),int(cx+22),int(cy+39))
        p.setPen(QColor('#a989ec'))
        for dx,dy in [(-62,-78),(62,-78),(-62,68),(62,68)]:
            p.drawEllipse(QRectF(cx+dx-4,cy+dy-4,8,8))
        p.setPen(QColor('#c1d3eb'))
        p.drawText(QRectF(15,self.height()-37,self.width()-30,30),Qt.AlignmentFlag.AlignCenter,'Simulated signals · webcam is off')


class AuroraBackground(QWidget):
    def paintEvent(self,event):
        p = QPainter(self)
        p.fillRect(self.rect(),QColor('#080d19'))
        for x,y,color,size in [(.05,.1,'#145067',480),(.88,.25,'#423169',510),(.48,.95,'#15394c',420)]:
            grad = QRadialGradient(self.width()*x,self.height()*y,size)
            c = QColor(color); c.setAlpha(130)
            grad.setColorAt(0,c); c.setAlpha(0); grad.setColorAt(1,c)
            p.fillRect(self.rect(),grad)
        p.setPen(QPen(QColor(140,180,220,9),1))
        for x in range(0,self.width(),48): p.drawLine(x,0,x,self.height())
        for y in range(0,self.height(),48): p.drawLine(0,y,self.width(),y)


class GlassPanel(QFrame):
    def __init__(self):
        super().__init__(); self.accent = '#40dfcf'; self.quiet = False

    def paintEvent(self,event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1,1,-1,-1)
        grad = QLinearGradient(r.topLeft(),r.bottomRight())
        grad.setColorAt(0,QColor(43,62,87,205 if not self.quiet else 250))
        grad.setColorAt(.48,QColor(22,35,57,215)); grad.setColorAt(1,QColor(15,24,43,230))
        p.setBrush(grad); p.setPen(QPen(QColor(154,186,228,65),1))
        p.drawRoundedRect(r,18,18)
        shine = QLinearGradient(0,0,self.width(),0)
        shine.setColorAt(0,QColor(255,255,255,0)); shine.setColorAt(.35,QColor(205,230,255,125)); shine.setColorAt(1,QColor(255,255,255,0))
        p.setPen(QPen(shine,1)); p.drawLine(20,2,self.width()-20,2)
