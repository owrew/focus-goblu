import os
import time
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog
from focus_goblin.engine import AttentionEngine, Observation, Settings
from focus_goblin.phone import aligned_with_look, near_hand
from focus_goblin.storage import Store
from focus_goblin.ui import MainWindow


def test_context_geometry_and_five_minute_threshold():
    box = (565,420,140,190)
    assert aligned_with_look(box,(.5,.35),(0,.4),(1280,720))
    assert not aligned_with_look(box,(.5,.35),(-.4,0),(1280,720))
    assert near_hand(box,[(.48,.76)],(1280,720))
    assert not near_hand(box,[(.25,.76)],(1280,720))
    engine = AttentionEngine(Settings(calibrated=True, alert_seconds=900, warning_seconds=600))
    assert (engine.settings.alert_seconds,engine.settings.warning_seconds) == (300,299)
    obs = Observation(face=True,pitch=.4,object_label="book",object_held=True)
    for _ in range(599):
        assert not engine.step(obs,.5).alert
    decision = engine.step(obs,.5)
    assert decision.alert and decision.reason == "Possible handheld book"


def test_nap_mutes_reactions_while_timer_and_evidence_continue(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(Store(tmp_path/"nap.sqlite3"))
    window.timer.stop()
    window.start_demo()
    assert {"idle","angry","drink","sleep","wake","run1","run2","greet"} <= window.overlay.sprites.keys()
    window.sleep_goblin()
    assert window.overlay.state == "drink" and 179 < window.overlay.nap_remaining <= 180
    window.nap_started -= 2
    for _ in range(140):
        window.last_tick -= .1
        window.tick()
    assert window.overlay.state == "sleep" and not window.screen_fire.windows
    assert window.engine.active > 13 and window.engine.distracted > 0 and window.engine.alerts == 0
    window.sleep_until = time.monotonic()-.01
    window.tick()
    assert window.overlay.state == "wake" and window.engine.away < 1
    assert any(kind=="pet_wake" for _,kind,_ in window.store.events_for(window.sid))
    window.close()
    app.processEvents()


def test_phone_check_counts_distinct_frames_and_requires_apply(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(Store(tmp_path/"phone.sqlite3"))
    window.timer.stop()
    window.phone_check = {"views":[],"scores":{},"start":10.,"deadline":16.,"suggestion":None}
    observation = Observation(phone_stamp=11.,phone_score=.4,phone_check_result=True)
    for _ in range(10):
        window.update_phone_check(observation,13.)
    assert len(window.phone_check["scores"]) == 1
    window.update_phone_check(None,16.)
    assert "Intermittent candidate (1/1" in window.phone_prompt.text()
    for start in (20.,30.):
        window.phone_check.update(start=start,deadline=start+6,scores={})
        for delta in (1.,2.,3.):
            window.update_phone_check(Observation(phone_stamp=start+delta,phone_score=.48,
                                                 phone_check_result=True),start+5)
        window.update_phone_check(None,start+6)
    assert window.phone_check["suggestion"] == .36
    assert window.settings.phone_confidence == .25
    window.advance_phone_check()
    assert window.settings.phone_confidence == .36 and window.phone_check is None
    window.close()
    app.processEvents()


def test_comparison_excludes_demos_and_exports_html(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    store = Store(tmp_path/"reports.sqlite3")
    for started,demo,focus in [("2026-11-04",False,180),("2026-10-28",False,60),("2026-11-04",True,900)]:
        sid = store.start("Study",demo)
        store.db.execute("UPDATE sessions SET started=? WHERE id=?",(started,sid))
        store.checkpoint(sid,{"focus":focus},end=True)
    current,prior = store.comparison(7,date(2026,11,4))
    assert current["focus"] == 180 and prior["focus"] == 60
    target = tmp_path/"report.html"
    monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *args:(str(target),"HTML"))
    window = MainWindow(store)
    window.export_comparison()
    assert "<th>Change</th>" in Path(target).read_text(encoding="utf-8")
    window.close()
    app.processEvents()
