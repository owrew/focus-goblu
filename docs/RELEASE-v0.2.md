# Focus Goblin v0.2 · visual and motion upgrade

## Delivered

- New original goblin logo generated with the built-in image-generation tool; integrated into dashboard and Windows icon. Transparent PNG and full prompt are in `focus_goblin/assets`.
- Smoked glass panels with semi-transparent layers, fine highlights, teal/violet ambient light, a subtle grid and revised controls. Native painted glass appearance; no capture/blur of the desktop behind the app.
- Elapsed-time animation, adjustable 15–60 FPS target (30 default). States use a 450 ms eased crossfade; anger ramps gradually, desktop travel eases and recovery glides into the cave. Reduced motion remains available.
- Separate cartoon flame strips on every screen's top/bottom/sides, cubic shapes, gradient glow, eased appearance/removal and click-through window flags. Placement: all edges, sides, or bottom. Central work area stays open.
- Stop/pause immediately clears fire and stops sound. Reaction preview works during live/demo sessions and restores their current state afterward.
- Smooth attention gauge, graph fill/hover inspection, face/phone badges, real-session daily-goal progress, break countdown, seven-calendar-day bars including zero days. Demo data is excluded from real goals.
- Read-only archive, tab fades, single-instance guard, packaged logo assets.
- Independent phone worker: one pending frame, two-second inference interval, four-second result expiry. Face updates no longer wait for phone inference in the same loop.

## Verified

14 automated tests passed; compilation and dependency checks passed. New tests cover fire placement/input transparency/fade/panic cleanup, character blending/eased return, and submission while the phone detector is blocked.

The webcam negotiated 1280×720 with phone detection enabled. A steady spot check delivered 36 observations (~4.3/sec), average complete capture/face worker time ~239 ms, and clean capture release. The earlier spot check was ~3.0/sec; these are not controlled comparable trials. Zero faces were detected in the current scene, so gaze accuracy, real-phone accuracy and 12 camera FPS remain unverified. Animation refresh is independent from camera inference rate.

## Limits

Head/gaze remain approximate landmark ratios. Smiles/laughter, thoughts, daydreaming and specific phone apps are not classified. Sound is a synthetic cartoon shriek, not recorded acting/TTS. Characters use procedural artwork; the earlier sticker was not attached here. Fire uses 76-pixel edge strips, not a particle field over every pixel. Adaptive CPU throttling, a signed installer, voice/sprite packs and calibration profiles remain future work.

## Try it

Open `FocusGoblin-v0.2.exe` and select Preview reaction. Change fire placement in Control room, save, preview again. Drag the pet; minimize the dashboard; refocus through camera monitoring to see recovery. Screen fire can be disabled separately from pet fire. Start at 30 animation FPS; use 15 on a busy laptop. Camera starts only on request.
