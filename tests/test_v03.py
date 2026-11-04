import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from focus_goblin.phone import TinyPhoneDetector
from focus_goblin.lighting import FaceLighting
from focus_goblin.storage import Store
from focus_goblin.ui import MainWindow
from focus_goblin.engine import AttentionEngine,Settings,Observation


def test_darknet_score_is_not_multiplied_twice_and_boxes_are_unletterboxed():
    row=np.zeros(85,dtype=np.float32);row[:4]=[.5,.5,.25,.25];row[4]=.4;row[72]=.4
    result=TinyPhoneDetector.decode([np.array([row])],1280,720,.325,0,91,416,.25)
    assert result['visible'] and abs(result['score']-.4)<.001
    assert result['boxes'][0][0][2]>300
    row[5+52]=.7
    assert not TinyPhoneDetector.decode([np.array([row])],1280,720,.325,0,91,416,.25)['visible']


def test_face_weighted_light_handles_dark_face_bright_background_without_mutating_input():
    frame=np.full((360,640,3),245,dtype=np.uint8);frame[70:290,200:440]=35
    before=frame.copy();lighting=FaceLighting();lighting.roi=(200,70,440,290)
    for _ in range(20):corrected=lighting.correct(frame,128)
    assert np.array_equal(frame,before)
    assert .55<=lighting.gamma<1 and corrected[150,320].mean()>frame[150,320].mean()
    assert corrected.max()<=255
    assert np.array_equal(lighting.correct(frame,enabled=False),frame)
    assert lighting.level == 35 and lighting.gamma == 1.


def test_false_alarm_quiet_period_does_not_fabricate_focus():
    engine=AttentionEngine(Settings(calibrated=True))
    for _ in range(100):engine.step(Observation(True,yaw=.5),.1)
    assert engine.alerts==1
    engine.dismiss_alert();focus=engine.focus
    for _ in range(200):engine.step(Observation(True,yaw=.5),.1)
    assert engine.alerts==1 and engine.focus==focus


def test_plans_export_and_delete_preserve_other_sessions(tmp_path):
    store=Store(tmp_path/'plans.sqlite3')
    first=store.start('Study');second=store.start('Work')
    tasks=[{'text':'Solve 3 equations','done':True}]
    store.save_plan(first,'Math',60,tasks)
    assert store.plan(first)==('Math',60,tasks)
    store.event(first,'false_alarm','Paper work')
    out=tmp_path/'all.json';store.export_all(out)
    assert len(json.loads(out.read_text())['sessions'])==2
    backup=tmp_path/'backup.sqlite3';store.backup(backup)
    store.delete_sessions([first]);assert len(store.history())==1 and store.history()[0][0]==second
    assert backup.is_file() and len(store.daily_range(30))==30
    store.close()


def test_task_enter_plan_feedback_and_customization(tmp_path):
    app=QApplication.instance() or QApplication([])
    window=MainWindow(Store(tmp_path/'ui.sqlite3'));window.show();window.start_demo();window.timer.stop()
    window.task_entry.setText('Read one chapter');window.add_task_and_start()
    assert window.task_list.count()==1 and window.store.plan(window.sid)[2][0]['text']=='Read one chapter'
    window.task_list.item(0).setCheckState(Qt.CheckState.Checked)
    assert window.store.plan(window.sid)[2][0]['done']
    window.false_alarm();assert window.store.events_for(window.sid)[0][1]=='false_alarm'
    window.fields['goblin_name'].setText('Zog');window.save_settings()
    assert window.overlay.name=='Zog' and window.settings.phone_enabled
    window.engine.active=window.session_length.value()*60+1
    window.tick();assert window.paused and window.plan_complete
    window.close();app.processEvents()
