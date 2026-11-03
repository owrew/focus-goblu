import argparse
import sys
from PySide6.QtWidgets import QApplication
from .ui import MainWindow


def main():
    parser = argparse.ArgumentParser(description="Focus Goblin desktop app")
    parser.add_argument("--demo",action="store_true",help="Start simulated signals without accessing the camera")
    parser.add_argument("--self-test",metavar="REPORT",help="Verify packaged UI and MediaPipe without opening the camera; write JSON report")
    args = parser.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Focus Goblin")
    window = MainWindow(); window.show()
    if args.self_test:
        import json
        from pathlib import Path
        from PySide6.QtCore import QTimer
        report = {'ui_loaded':True}
        try:
            import mediapipe as mp
            with mp.solutions.face_mesh.FaceMesh(refine_landmarks=True,max_num_faces=1):
                report['face_mesh_initialized'] = True
        except Exception as exc:
            report['error'] = str(exc)
        Path(args.self_test).write_text(json.dumps(report,indent=2),encoding='utf-8')
        QTimer.singleShot(200,window.close)
    if args.demo: window.start_demo()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
