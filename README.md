# Focus Goblin · local desktop MVP

A Windows-first Python application with webcam attention estimates, an original animated goblin desktop overlay, a sloth break reminder, and local session analytics. Version 0.1.0.

## Run on this computer

The project is in `C:\Users\awais\OneDrive\Downloads\Computer vision program\focus-goblin`.

1. Double-click **Launch Focus Goblin.cmd**. Dependencies are installed in `.venv` on this computer.
2. Try **camera-free demo** to see a repeating focus → phone/downward distraction → recovery cycle. Demo sessions are labelled and excluded from daily totals.
3. For actual use, Stop the demo, choose **Start camera**, then **Calibrate**. Look naturally at the screen for three seconds with your eyes open. Calibration requires at least 12 face samples and rejects unstable samples.
4. Brief glances are tolerated. Tune head/iris tolerance and warning/reaction delays in **Control room**. Higher tolerance is gentler. Paper mode allows downward work unless a phone is visible.
5. **Pause** closes the camera and freezes session accounting. **Resume** reopens it. **Stop / Goblin off** saves the session and hides the overlay. Escape has the same stop action when the dashboard has keyboard focus.
6. The goblin also lives on the desktop as a **transparent floating pet**, visible on launch with the camera off. It remains visible when the dashboard is minimized. Drag the cave to reposition it; right-click for controls; double-click to hide. **Show cave** restores it. Reduce motion, intensity, fire, or disable the overlay/pet in settings. Sound starts disabled.

## Fresh setup

Install 64-bit Python **3.11**. Python 3.14 on this computer is deliberately not used because this build pins the older MediaPipe FaceMesh API and its compatible NumPy/OpenCV versions.

```powershell
cd 'C:\path\to\focus-goblin'
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
.\.venv\Scripts\python.exe -m focus_goblin
# camera-free path
.\.venv\Scripts\python.exe -m focus_goblin --demo
```

Setup downloads dependencies. Normal use does not download models or send camera frames anywhere. The project folder can be in OneDrive; session data is stored separately under `%LOCALAPPDATA%\FocusGoblin`.

## Phone detection

Recommended: **YOLOv4-tiny COCO through OpenCV DNN**, no PyTorch. Its weights are about 23 MB. Run `download-phone-model.ps1` once if the `models` folder is missing. Select `models\yolov4-tiny.weights` in Control room, save, Stop and Start. Keep the matching `yolov4-tiny.cfg` beside it. The app processes phone detection every two seconds on 320×320 input, rather than every webcam frame.

The model is the standard upstream general object detector, not custom trained for your desk. A phone outside the frame cannot be detected. Small, occluded, dark, or edge-on phones may be missed. Test the camera framing yourself. A visible phone alone does not cause an alert.

Advanced optional alternative: install `requirements-phone.txt` and select a trusted local Ultralytics COCO `.pt` nano model. This installs the substantially heavier PyTorch stack. It is **not required** for the recommended detector. Do not load untrusted `.pt` files. Review [Ultralytics licensing](https://www.ultralytics.com/license) before distributing a build with that backend or its models. These optional dependencies are not included in the default packaged application.

## What works

- MediaPipe face and iris landmarks; relative head-direction and gaze estimates calibrated to your usual screen position.
- Timed distraction stages, keyboard-glance grace, stable recovery, cooldowns, paper mode, separate absence/unknown accounting.
- Requested 720p or 1080p capture; face inference and preview at 640×360; 5–20 processed frames/second selectable (12 default). The camera's actual negotiated resolution is displayed.
- Animated original vector goblin: cave, peeking/blinking, warning, angry bouncing/stomping, running overlay, impact star, cartoon broken phone and fire; recovery returns it to its cave anchor.
- Five personalities with different captions; optional locally generated cartoon shriek and adjustable volume. There is no recorded human scream or speech/TTS in this MVP.
- Dark gradient/glass-look dashboard, editable RGB accent, quieter alternate finish, score ring, recent attention line, daily bars, saved sessions, CSV export.
- SQLite events, sampled scores, periodic checkpoints, summaries, demo separation.
- Time-based break reminders: sloth rises from a chair and stretches; monitoring pauses until resumed.

## Limits and performance

This is an attention **proxy**, not a mind-reading or medical tool. Head pose is a normalized landmark ratio, not solvePnP angles in degrees. Iris position estimates are noisy, especially with glasses, dim light, low camera angles, or eye-only movements. There is no screen-coordinate gaze mapping, emotion/laughter inference, diagnosis, or detection of which phone app is open. Recalibrate after moving the camera, changing your seat, or switching monitor layout. Calibration is local and camera-specific only by user convention; no biometric identity is created.

The FPS setting is a target, not a guarantee. YOLO runs in the camera worker, so its inference can reduce face-update rate temporarily. Start with phone detection off to measure responsiveness, then enable it. The development camera negotiated 720p, but a short combined test achieved only about **3 observations/sec** in the current conditions with no face detected. Smooth operation at the 12 FPS target and real-user gaze/phone accuracy remain unverified. See `docs/VALIDATION.md` for checks actually performed. There is no automatic resource-based adaptation yet.

No global hotkey, tray/background service, startup registration, camera recording, website blocker, phone companion, custom sticker import, full desktop-wide particle field, or photorealistic sprite/voice pack is included. Overlay chaos stays inside its movable 390×310 transparent window and never manipulates actual desktop elements. Glass appearance uses gradients, not Windows compositor backdrop blur. Personality changes captions; motion/sound repertoire is shared. Daily bars show the last seven days with recorded sessions (not a complete calendar heatmap). CSV export covers the newest 100 summaries. Historical samples and events are retained in SQLite; the chart shows the current session's latest 300 samples.

Breaks measure elapsed monitoring time, not actual sitting. Face absence is not automatically counted as a confirmed break. **Take a break** resets the timer and pauses capture. A long camera stall is excluded from focus, and dt is capped to avoid over-crediting unobserved time.

## Data and privacy

`%LOCALAPPDATA%\FocusGoblin\focus.sqlite3` holds settings, coarse calibration values, timestamps, durations, scores and event labels. Raw frames exist only in memory. There is no video writer, screenshot capture, microphone capture, telemetry, cloud API, or raw-video storage option. The synthetic WAV effect is stored in the same local folder. SQLite is not encrypted. Local backups may include this folder depending on your backup settings.

To reset your history, close the app first, back up this folder if wanted, then remove `focus.sqlite3` and any accompanying `-wal`/`-shm` files. Settings/calibration are in that database too. The project never deletes your history automatically.

## Checks and Windows packaging

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q focus_goblin
powershell -NoProfile -ExecutionPolicy Bypass -File .\package.ps1
```

Packaging produces a folder build: `dist\FocusGoblin\FocusGoblin.exe`. Keep that whole folder together. Packaging bundles the MediaPipe assets. It excludes optional PyTorch/Ultralytics; the OpenCV tiny detector still works with external weights. Copy `models` alongside the build and select its `.weights` file. The binary is unsigned. Package size is substantial because Qt and MediaPipe are bundled. It is not an installer.

## Source layout

```text
focus_goblin/
  __main__.py       application entry
  engine.py         settings, observations, temporal rule state machine
  vision.py         camera/FaceMesh worker, bounded latest-frame handoff
  phone.py          OpenCV YOLOv4-tiny inference
  mascot.py         original procedural vector animation and overlay window
  ui.py             dashboard, calibration, controls, charts, sound
  storage.py        SQLite repository and CSV export
tests/              deterministic rules, storage and Qt demo integration
docs/               design/architecture, roadmap, validation
packaging/entry.py   PyInstaller entry
models/             optional downloaded external model assets
```

See `docs/ARCHITECTURE.md` for design, detection logic and schema; `docs/ROADMAP.md` for phased implementation and remaining work. Local files have been created; nothing has been published to GitHub. The project name follows the supplied brief and is not a trademark-availability claim. The earlier angry-goblin sticker was not attached to this chat, so this build uses independently drawn vector artwork.

Upstream references: [MediaPipe](https://github.com/google-ai-edge/mediapipe), [current Face Landmarker guide](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python) (newer Tasks API; this MVP pins legacy FaceMesh), [Darknet YOLOv4-tiny](https://github.com/AlexeyAB/darknet), [Qt for Python](https://doc.qt.io/qtforpython-6/). Third-party libraries/model assets retain their upstream terms; review those before public distribution.
