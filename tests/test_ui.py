import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from focus_goblin.storage import Store
from focus_goblin.ui import MainWindow


def test_demo_pause_stop_and_settings(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(Store(tmp_path/'ui.sqlite3'))
    window.show(); app.processEvents()
    assert window.overlay.isVisible()  # pet exists before any camera session
    assert window.overlay.grab().toImage().pixelColor(0,0).alpha() == 0
    window.showMinimized(); app.processEvents()
    assert window.overlay.isVisible()
    window.showNormal()
    window.start_demo()
    window.timer.stop()
    for i in range(350):
        window.last_tick -= .1
        window.tick()
    assert window.engine.alerts >= 1
    assert window.engine.focus > 0
    window.pause(); before = window.engine.active
    window.tick(); assert window.engine.active == before
    window.pause(); window.tick()
    window.save_settings()
    window.fields['mode'].setCurrentText('Light monitoring')
    assert window.fields['alert_seconds'].value() == 16
    window.stop(); assert window.sid is None and not window.overlay.isVisible()
    window.close(); app.processEvents()
