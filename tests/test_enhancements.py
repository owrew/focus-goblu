import threading
import time
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from focus_goblin.engine import Settings
from focus_goblin.effects import ScreenFire
from focus_goblin.mascot import Mascot
from focus_goblin.vision import PhoneWorker


def test_edge_fire_click_through_fade_and_panic_cleanup():
    app = QApplication.instance() or QApplication([])
    fire = ScreenFire()
    fire.configure(True,Settings())
    assert len(fire.windows) == 4*len(app.screens())
    for window in fire.windows:
        assert window.windowFlags() & Qt.WindowType.WindowTransparentForInput
        assert window.width() == 76 or window.height() == 76
    fire.last -= .08; fire.tick()
    assert 0 < fire.amount < 1
    fire.configure(False,Settings())
    for _ in range(20): fire.last -= .1; fire.tick()
    assert not fire.windows and not fire.timer.isActive()
    fire.configure(True,Settings(fire_edges='Sides'))
    assert len(fire.windows) == 2*len(app.screens())
    fire.clear()


def test_character_state_blend_and_eased_return():
    app = QApplication.instance() or QApplication([])
    pet = Mascot(True); pet.show(); app.processEvents()
    pet.state = 'angry'
    assert pet._transition == 0 and pet._previous is not None
    for _ in range(15): pet._last_tick -= .05; pet.animate()
    assert pet._transition == 1 and pet._previous is None
    pet.move(pet.anchor.x()-120,pet.anchor.y())
    pet.state = 'focused'; pet._last_tick -= .05; pet.animate()
    assert pet.pos() != pet.anchor  # gradual travel home, not an instant snap
    pet.close()


def test_slow_phone_inference_does_not_block_frame_submission():
    entered,release = threading.Event(),threading.Event()
    class Detector:
        def detect(self,frame):
            entered.set(); release.wait(2)
            return {"visible":True,"boxes":[],"score":.8}
    class Status:
        def emit(self,text): pass
    worker = PhoneWorker(Detector(),.5,Status())
    try:
        import numpy as np
        first, second, latest = (np.zeros((2,2,3)) for _ in range(3))
        context = ((.5,.5),(0.,0.),False)
        worker.submit(first,*context); worker.start()
        assert entered.wait(1)
        worker.submit(second,*context); worker.submit(latest,*context)
        with worker.lock: assert worker.frame[0] is latest
        worker.result = time.monotonic()-5
        assert not worker.detection()['visible']
    finally:
        release.set(); worker.stop(); worker.join(2)
    assert not worker.is_alive()
