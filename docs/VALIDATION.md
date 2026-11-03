# Local validation · 2026-11-03

## Verified

- Python 3.11.9 x64; PySide6 6.8.3; MediaPipe 0.10.21; OpenCV contrib 4.11.0; NumPy 1.26.4.
- `python -m pytest -q`: **11 passed**. Tests cover brief glances/recovery, phone-alone tolerance, combined-signal acceleration and cooldown, unknown/absence/calibration handling, accounting and break timer, paper mode, stalled dt, blink handling, SQLite/export/demo separation, interrupted-session recovery, and the Qt demo lifecycle.
- The Qt integration check also verifies the desktop pet is visible before monitoring, has transparent pixels around its silhouette, stays visible when the dashboard is minimized, and that session mode presets update thresholds.
- `python -m compileall -q focus_goblin`: passed.
- `python -m pip check`: no broken requirements.
- Actual local OpenCV YOLOv4-tiny weights loaded and processed a black image without a phone detection. Separate warm-up checks took roughly 94–219 ms per synthetic frame; these are development-machine spot checks, not an i3 benchmark or an accuracy score.
- MediaPipe detected one face with **478 refined landmarks** on Google's public reference portrait (`https://storage.googleapis.com/mediapipe-assets/portrait.jpg`). This checks model initialization/inference, not user-specific calibration accuracy.
- Actual webcam opened at **1280×720**. The worker released the camera cleanly in both tests. No camera frames were written to disk.
- A short combined webcam/FaceMesh/YOLO test produced 25 observations, about **3.0 observations/sec**, average complete worker loop ~363 ms (including camera read), after initialization. **Zero face-positive observations** occurred. This does not validate live face tracking, gaze accuracy, phone accuracy or target FPS with a person in view. Camera/environment/exposure and inference costs were not isolated.
- Windows Qt dashboard and individual character states rendered and were visually inspected. A shorter-screen clipping issue was repaired by making the observatory scrollable. The reference screenshot contains **simulated signals only**.
- A PyInstaller Windows folder build launched successfully; a camera-free packaged self-test reported `ui_loaded: true` and `face_mesh_initialized: true`, then exited normally. Build is unsigned and has not been tested on a clean second PC. Optional Ultralytics backend is not installed/tested.

## Needs the user's live acceptance test

1. Start camera, confirm live preview and actual negotiated resolution, calibrate while seated normally.
2. Brief keyboard glance should stay below warning; sustained side/downward gaze should advance warning/reaction after configured delays.
3. Select local YOLOv4-tiny weights, restart capture, hold a phone clearly within frame while looking down; confirm phone visibility and combined escalation. A phone held up while facing the screen should not independently cause an alert.
4. Refocus and verify recovery. Try paper mode, dim light, glasses, a second monitor and a different camera angle. Adjust tolerances rather than interpreting scores as measured concentration.
5. Enable sound at low volume to audition the synthetic shriek. Confirm the floating pet remains visible over other windows and when the dashboard is minimized; test right-click and drag on your DPI/multi-monitor arrangement.
6. Set break reminder to one minute for a quick sloth test; verify capture stops during the break and Resume works. Restore desired interval afterward.

Source and packaged versions need this same acceptance pass. No assertion of 12 FPS on an 8 GB/i3 laptop or validated clinical/productivity outcome is made.
