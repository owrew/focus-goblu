# Focus Goblin 0.3.0

## Phone detection and lighting

The prior detector could stay disabled until a model was selected. Its Darknet decoder also multiplied OpenCV's already objectness-weighted class score by objectness again. Version 0.3 corrects that decoder and auto-loads the bundled **OpenCV YOLOX-S ONNX** model by default. It runs through OpenCV CPU, without PyTorch. Eco YOLOv4 and explicitly selected custom models remain available. YOLOX uses fixed 640 input; the 416/608 option applies to Eco only.

The preview now draws phone boxes and displays detector state, class score, luminance and gamma. Eight-second Phone Check collects candidate scores and can set a conservative threshold (minimum 15%). This is sensitivity tuning, not training or proof of identification. If no reliable candidate appears it reports failure, with framing/light suggestions. Camera-free demo scores are simulated and labelled.

Five COCO128 images with phone annotations were used as a small sanity check: Eco at 416 produced zero detections at threshold .25, Eco at 608 produced one, and YOLOX at 640 produced three candidates overlapping phone annotations (best IoUs .884, .456, .627). Two images were still missed. This is not a benchmark, independent evaluation or validation of the user's actual device. Test front/back views yourself with the whole phone in frame.

Automatic lighting uses the last face bounding region (central region before a face is found) to estimate luminance, gradually changes gamma, and applies gentle local contrast to the preview/face-inference image. Phone inference receives full-resolution, gamma-adjusted pixels. It never changes monitor brightness or room lighting. It cannot recover already clipped highlights or detail absent in a dark image. Driver auto exposure is requested on start; acceptance/unsupported status is shown. The driver may still choose its own exposure region.

478 face/iris landmarks are displayed when enabled. Head/iris observations are smoothed; face absence resets smoothing. Gaze calibration now allows five seconds and at least ten clear face samples. Head/gaze remain approximate landmark ratios, not calibrated screen-coordinate eye tracking or a medical assessment.

## Sessions and feedback

- Focus desk: name a session, select 1–480 minutes, type a task and press Enter to add it and start monitoring. Add task appends without starting. Check off and remove tasks; plans and completion state are saved alongside the session.
- The countdown uses active monitoring time and freezes on pause; it is not a measurement of productive cognition. At the goal, monitoring pauses. Resume permits overtime; Stop ends and saves the session.
- Alerts explain the contributing signal, accumulated away evidence and phone score. False alarm logs feedback and silences reactions for 30 seconds without inventing focus time or deleting the original event. Make rules gentler explicitly increases head/gaze tolerances.
- Native Windows global pause/resume: Ctrl+Alt+P by default, with alternatives in Settings. Conflicts are reported. The native message dispatch was tested. Tray menu provides dashboard/pause/stop/quit controls where the Windows tray is available.

## Companion and appearance

- Set a companion name and body color. Eyes follow the cursor; a tap triggers a four-second manual rage reaction without recording a camera distraction. Dragging still moves the pet. Double-tap now reacts; hide through its menu.
- Personalities differ in travel speed, arm gestures, generated-sound frequency and captions. Coach/Chill use gentler movement and suppress screen-edge fire.
- Import a local mono/stereo PCM WAV up to 20 MB. It is copied into the local data folder. Enable sound and save; the custom clip replaces generated rage sound.
- New generated waterfall landscape with subtly animated mist, rounded glass panels that blur that application's scene, RGB accent choice and reduced-motion controls. It does not blur/capture the real desktop, and is not a full-motion waterfall video. The image-generation prompt is in assets/WATERFALL.md.
- Settings are grouped into Camera & rules, Your goblin, Lighting & phone, Scene & system. Custom skins remain excluded as requested.

## History, data, installation and updates

- Weekly, monthly and 90-day real-session charts; session names and up to 200 recent events per selected session. Demo sessions stay excluded from real daily totals.
- Complete JSON export, CSV summaries, SQLite backup, selected-session deletion with confirmation/recovery backup, and optional retention in days (0 keeps all). Active sessions cannot be deleted through the UI. Backups contain personal session/task data and should be kept private. Retention acts when saved; it is not a daily background cleanup service.
- Per-user Windows installer with Start menu shortcut, optional desktop shortcut and opt-in startup. Startup leaves the camera off; pet-only launch hides the dashboard only when a tray icon is available. Uninstall preserves the local history/settings folder.
- The installer uses a stable application ID/path, allowing newer installers to upgrade the same installation. Settings includes an explicit picker for a trusted downloaded update installer. There is no hosted update server, automatic online version check, automatic download, or code-signing certificate in this release. Do not run update installers from untrusted sources.

## Checks and current limits

19 automated tests, compile check and dependency consistency check passed. Native Windows tests verified shortcut registration and WM_HOTKEY pause/resume, task persistence and a nonempty blurred backdrop. Views were rendered and inspected. Synthetic backlighting tests verified dark-face lifting without changing the original input frame. Public reference images and development UI captures are kept out of source deliverables; no raw webcam frames are stored.

The short 1280×720 camera test with YOLOX + lighting returned 26 observations (~3.0/sec), average capture/face loop ~351 ms, zero face-positive observations, and clean release. It does not validate a real seated user's gaze, phone, exposure success, multi-monitor behavior or the 12 FPS target. Motion refresh remains separate from camera inference. Better detection can cost CPU; use Eco or disable animated background/dense dots on slow hardware if needed.
