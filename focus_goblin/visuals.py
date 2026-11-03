"""Native lightweight glass panels and smooth score movement."""
from pathlib import Path
import math
import time
from PySide6.QtCore import QRectF, Qt, QTimer, QPoint
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QRadialGradient, QPen, QImage, QPainterPath
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
    def __init__(self):
        super().__init__();self.scene_name='Waterfall';self.motion=True;self.blur_enabled=True
        self.scene_image=QImage();self.frosted=QImage();self.phase=0.;self.frames=0
        self.render_key=None
        self.waterfall=QImage(str(ASSETS/'waterfall.png'))
        self.scene_timer=QTimer(self);self.scene_timer.timeout.connect(self.advance);self.scene_timer.start(100)

    def advance(self):
        if not self.isVisible() or not self.motion:return
        self.phase+=.1;self.update()
        for panel in self.findChildren(GlassPanel):panel.update()

    def paintEvent(self,event):
        key=(self.size().width(),self.size().height(),self.scene_name,round(self.phase,2) if self.motion else 0.)
        if self.render_key==key and not self.scene_image.isNull():
            painter=QPainter(self);painter.drawImage(0,0,self.scene_image);painter.fillRect(self.rect(),QColor(3,11,22,90));return
        self.render_key=key
        image=QImage(self.size(),QImage.Format.Format_ARGB32_Premultiplied);image.fill(QColor('#091a25'))
        p=QPainter(image);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for x,y,color,size in [(.05,.1,'#145b65',580),(.88,.25,'#493766',610),(.48,.95,'#116b75',520)]:
            grad = QRadialGradient(self.width()*x,self.height()*y,size)
            c = QColor(color); c.setAlpha(130)
            grad.setColorAt(0,c); c.setAlpha(0); grad.setColorAt(1,c)
            p.fillRect(image.rect(),grad)
        if self.scene_name=='Waterfall' and not self.waterfall.isNull():
            scaled=self.waterfall.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
            ox=(scaled.width()-self.width())//2;oy=(scaled.height()-self.height())//2
            p.drawImage(self.rect(),scaled,self.rect().translated(ox,oy))
            for i in range(20):
                x=self.width()*(.6+.25*math.sin(i*4.3));y=(self.phase*17+i*83)%max(1,self.height())
                mist=QRadialGradient(x,y,70);mist.setColorAt(0,QColor(145,228,231,8));mist.setColorAt(1,QColor(145,228,231,0))
                p.fillRect(QRectF(x-70,y-70,140,140),mist)
        elif self.scene_name=='Waterfall':
            p.scale(self.width()/1000,self.height()/900)
            def shape(points,color):
                path=QPainterPath();path.moveTo(*points[0])
                for point in points[1:]:path.lineTo(*point)
                path.closeSubpath();p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(color));p.drawPath(path)
            shape([(0,410),(130,115),(220,260),(330,88),(450,255),(520,130),(650,310),(800,155),(1000,380),(1000,900),(0,900)],'#173448')
            shape([(0,590),(80,420),(190,480),(310,290),(420,380),(500,285),(650,420),(720,270),(850,360),(940,210),(1000,300),(1000,900),(0,900)],'#102d3b')
            shape([(0,900),(0,500),(100,380),(180,510),(330,420),(445,405),(490,655),(730,690),(1000,550),(1000,900)],'#0b2530')
            water=QLinearGradient(560,220,560,760)
            water.setColorAt(0,QColor('#53b5b9'));water.setColorAt(.45,QColor('#83dbd1'));water.setColorAt(1,QColor('#234b67'))
            p.setBrush(water);p.setPen(Qt.PenStyle.NoPen)
            path=QPainterPath();path.moveTo(535,250);path.cubicTo(550,390,520,470,530,630);path.cubicTo(560,700,630,700,680,710);path.lineTo(615,700);path.cubicTo(580,560,650,450,610,250);path.closeSubpath();p.drawPath(path)
            for i in range(28):
                x=540+i*2.4;offset=(self.phase*70+i*31)%360
                p.setPen(QPen(QColor(177,242,236,55),1.2));p.drawLine(int(x),int(260+offset),int(x+math.sin(i)*8),int(320+offset))
            river=QLinearGradient(0,650,0,900);river.setColorAt(0,QColor('#1b6173'));river.setColorAt(1,QColor('#0b2338'))
            p.setBrush(river);p.setPen(Qt.PenStyle.NoPen)
            path=QPainterPath();path.moveTo(535,660);path.cubicTo(600,745,230,770,150,900);path.lineTo(1000,900);path.cubicTo(820,810,820,730,660,665);path.closeSubpath();p.drawPath(path)
            for i in range(15):
                y=720+i*13+math.sin(self.phase+i)*2
                p.setPen(QPen(QColor(142,217,225,35),1));p.drawArc(QRectF(320-i*10,y,420+i*25,24),0,180*16)
            for x,y,r in [(570,670,190),(350,770,200),(850,410,150)]:
                mist=QRadialGradient(x,y,r);mist.setColorAt(0,QColor(132,210,213,45));mist.setColorAt(1,QColor(132,210,213,0));p.fillRect(QRectF(x-r,y-r,2*r,2*r),mist)
        p.end();self.scene_image=image
        if self.frosted.size()!=image.size() or self.frames%6==0:
            # Low-pass filtering of our own scene gives genuine frosted backdrop pixels.
            self.frosted=image.scaled(max(1,self.width()//18),max(1,self.height()//18),Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation).scaled(self.size(),Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
        self.frames+=1
        painter=QPainter(self);painter.drawImage(0,0,image)
        painter.fillRect(self.rect(),QColor(3,11,22,90))


class GlassPanel(QFrame):
    def __init__(self):
        super().__init__(); self.accent = '#40dfcf'; self.quiet = False

    def paintEvent(self,event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1,1,-1,-1)
        root=self.window().centralWidget() if hasattr(self.window(),'centralWidget') else None
        if root is not None and getattr(root,'blur_enabled',False) and not root.frosted.isNull():
            clip=QPainterPath();clip.addRoundedRect(r,20,20);p.setClipPath(clip)
            origin=self.mapTo(root,QPoint(0,0));p.drawImage(self.rect(),root.frosted,self.rect().translated(origin))
            p.setClipping(False)
        grad = QLinearGradient(r.topLeft(),r.bottomRight())
        grad.setColorAt(0,QColor(43,62,87,160 if not self.quiet else 250))
        grad.setColorAt(.48,QColor(22,35,57,185)); grad.setColorAt(1,QColor(15,24,43,200))
        p.setBrush(grad); p.setPen(QPen(QColor(154,186,228,65),1))
        p.drawRoundedRect(r,18,18)
        shine = QLinearGradient(0,0,self.width(),0)
        shine.setColorAt(0,QColor(255,255,255,0)); shine.setColorAt(.35,QColor(205,230,255,125)); shine.setColorAt(1,QColor(255,255,255,0))
        p.setPen(QPen(shine,1)); p.drawLine(20,2,self.width()-20,2)
