import argparse
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QLockFile
from .ui import MainWindow
from .storage import data_dir


def main():
    parser = argparse.ArgumentParser(description="Focus Goblin desktop app")
    parser.add_argument("--demo",action="store_true",help="Start simulated signals without accessing the camera")
    parser.add_argument('--pet-only',action='store_true',help='Show the companion with the camera off; hide dashboard')
    parser.add_argument("--self-test",metavar="REPORT",help="Verify packaged UI and MediaPipe without opening the camera; write JSON report")
    args = parser.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Focus Goblin")
    lock = QLockFile(str(data_dir()/'application.lock'))
    if not lock.tryLock(0):
        QMessageBox.information(None,'Focus Goblin is already open','Open the existing dashboard or right-click your desktop goblin. Close it before starting another copy.')
        return 0
    window = MainWindow(); window.show()
    if args.pet_only and window.overlay.isVisible() and window.tray:window.hide()
    if args.self_test:
        import json
        import time
        from pathlib import Path
        from PySide6.QtCore import QTimer
        report = {'ui_loaded':True,'logo_loaded':not window.windowIcon().isNull(),'global_pause_registered':window.hotkey.registered,'settings_tabs':window.tabs.count()}
        try:
            import mediapipe as mp
            with mp.solutions.face_mesh.FaceMesh(refine_landmarks=True,max_num_faces=1), mp.solutions.hands.Hands(model_complexity=0):
                report['face_mesh_initialized'] = True
                report['hands_initialized'] = True
            from .phone import find_phone_model, YoloXPhoneDetector
            import cv2
            import numpy as np
            model = find_phone_model()
            if model and model.suffix == '.onnx':
                cv2.setNumThreads(1)
                YoloXPhoneDetector(model).detect(np.zeros((360,640,3),dtype=np.uint8),include_objects=True)
                report['phone_model_inference'] = True
            window.settings.screen_fire = False
            window.sleep_goblin()
            window.nap_started -= 2
            window.update_scene()
            report['sleep_pose'] = window.overlay.state == 'sleep' and 'sleep' in window.overlay.sprites
            window.sleep_until = time.monotonic()-.01
            window.update_scene()
            report['wake_pose'] = window.overlay.state == 'wake' and 'wake' in window.overlay.sprites
        except Exception as exc:
            report['error'] = str(exc)
        Path(args.self_test).write_text(json.dumps(report,indent=2),encoding='utf-8')
        QTimer.singleShot(200,window.close)
    if args.demo: window.start_demo()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
