# MVP roadmap

## Implemented foundation

1. Deterministic rules, local settings and SQLite summaries/events/samples.
2. OpenCV camera capture, MediaPipe face/iris pipeline, calibration, stale-signal handling, worker lifecycle.
3. Original cave/goblin/sloth vector artwork, animated state changes, transparent draggable desktop overlay, synthetic sound.
4. Observatory/dashboard, charts, archive, CSV export, pause/stop, personality and visual customization.
5. Optional CPU YOLOv4-tiny adapter and model setup; optional Ultralytics adapter.
6. Meaningful automated tests, documentation and Windows packaging script.

## Next validation milestone

On the actual i3/8 GB laptop, test camera framing under several light conditions, glasses, head movements, keyboard/paper work and visible/hidden phone examples. Measure achieved FPS and CPU/RAM with phone detector on/off. Tune defaults from labelled manual observations; avoid claiming accuracy from synthetic tests. Validate 720p negotiated capture and dual-monitor/DPI overlay behavior. Test sound and accessibility with the user's preferred intensity.

## Further implementation

- Move phone inference to its own worker, add adaptive throttling and per-backend timing charts.
- Upgrade legacy FaceMesh to current Tasks API with explicit model lifecycle; add geometric head-pose estimation and multi-point screen calibration if justified by measured accuracy.
- Add camera-specific calibration profiles and smoothing/quality gates for partial faces.
- Add optional user-supplied angry-goblin sticker/sprite packs, richer run/return choreography, local voice packs, tray controls and a configurable global stop hotkey.
- Add full historical daily/weekly filters, complete calendar bars, event browsing, data retention and schema migration controls.
- Audit/lock optional dependencies and model licensing, sign a tested Windows installer, run on a clean Windows VM before distribution.

No Android companion, cloud inference, medical assessment or automatic diagnosis is planned for this MVP.
