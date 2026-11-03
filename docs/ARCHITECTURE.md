# Architecture and feature specification

## v0.2 additions

Phone inference now runs in a separate PhoneWorker with one pending frame and stale-result expiry. Mascot transitions cache only their own rendered widget briefly in memory for crossfading; no camera/desktop image is saved. ScreenFire manages narrow transparent, input-transparent native windows at monitor edges. visuals.py provides native painted translucent glass panels and the demo-only sensor illustration. The dashboard uses the new generated logo, live goal/break progress and seven calendar-day bars. See RELEASE-v0.2.md for current behavior where it supersedes the v0.1 foundation below.

## Runtime architecture

`OpenCV camera → MediaPipe + optional YOLO → latest-frame mailbox → attention rules → dashboard / overlay / SQLite`

The main Qt thread owns widgets, rules, calibration and SQLite. VisionWorker owns the camera and model objects. Its mailbox holds at most one copied QImage/observation pair; the dashboard consumes the latest result on an 80 ms tick. Obsolete frames are replaced to prevent an ever-growing queue. Stop requests cooperative shutdown; close waits for capture to release. A permanently blocked camera driver can delay shutdown; Python cannot safely kill a native read in a thread.

The rule engine is independent of Qt and accepts injected observations/time increments. Model failure generates visible status; missing optional detector does not prevent face tracking. Camera failure becomes unknown time and leaves controls usable.

## UI/UX plan and design tokens

The cave is the signature visual, supported by a dense instrument-style observatory. The brief explicitly requests dark RGB/glass styling, so layered navy glass-look panels and neon accents are intentional. To avoid a generic all-identical-card dashboard, the cave/camera are larger primary regions; small statistic cards support them; lower charts hold the evidence.

- Abyss `#0d1221`, deep glass `#131b30`, upper glass `#202b46`, crystal teal `#40dfcf`, amethyst `#a58aff`, ember `#ff7355`.
- Segoe UI: 32 px brand, 29 px metrics, 14 px panel titles, 13 px controls/body.
- Left-aligned controls/data; central creature artwork; observed state and score directly beside it.
- Header always exposes camera state. Start/Pause/Stop/Calibrate stay outside the tabs. Observatory, Control room, Session archive, Privacy & limits are the four destinations.
- No camera access on launch. User starts it explicitly. Calibration and lack of usable signals are explained in place.
- Focus confidence is labelled estimated. Grace, absence and unobserved time remain visible. Demo carries a visible label and separate storage flag.
- Controls have keyboard focus styling. Reduced motion freezes character movement; sound is opt-in. Minimum main window size 980×720; content scales above that and settings scroll.

## Detection logic

1. Capture requested 1280×720 or 1920×1080. Report actual resolution. Resize to 640×360 for FaceMesh.
2. Use a single face, refined iris landmarks. Calculate normalized nose position relative to face and eye line as yaw/pitch proxies. Estimate iris centers within eye bounding landmarks. Very closed eyes suppress iris-only distraction decisions.
3. Calibrate median yaw/pitch/iris x/y over three seconds, at least 12 samples with eyes open. Reject excessive standard deviation. Calibration values are persisted locally.
4. Head deviation divided by head tolerance and iris deviation divided by gaze tolerance produce normalized signals. Attention score is clamped `1 - .42*head - .23*gaze`; it is a heuristic, not a calibrated probability.
5. Away means normalized head deviation >1 or open-eye iris deviation >1. Paper mode exempts downwards orientation without a visible phone. A phone alone never marks distraction.
6. Accumulate away time; looking down plus visible phone accumulates at 1.6×. Before warning threshold (default 4 s) time is grace/unknown. From warning threshold onward count likely distraction and one event per episode. At reaction threshold (8 s), animate angry reaction.
7. Count active alert notifications at most once per 20 s cooldown, including while the same episode persists. Animation continues during anger, while sound repeats only on cooldown. Refocus enters calming; 1.5 s stable recovery clears the away episode. Gaze jitter is handled temporally; no learned classifier or explicit landmark exponential filter is included yet.
8. Missing face counts absence. Invalid camera signal or missing calibration counts unknown and resets away timer. Unknown/absence never count as focus or trigger punitive alerts. Stable recovery frames count as estimated focus.
9. Remind after 30 minutes of monitoring by default. The sloth stretches and monitoring pauses. This is time-based, not a posture classifier.

## Storage schema

| Table | Columns | Role |
|---|---|---|
| settings | id (single row), payload JSON | preferences, coarse calibration baseline |
| sessions | id, started ISO timestamp, ended, mode, demo, summary JSON | aggregated durations, streak, event counts |
| events | id, session_id, at ISO timestamp, kind, detail | transitions, alerts, breaks, pauses |
| samples | id, session_id, elapsed seconds, confidence, state | sampled attention timeline |

Summary JSON includes active, focus, distracted, unknown, absent, longest, alerts, distractions and phone_events. Durations use monotonic increments; timestamps use local timezone-aware wall time. SQLite writes happen only in the UI thread with WAL and foreign keys enabled; checkpoints commit once per sampled second. On next launch, unfinished sessions retain the latest checkpoint, receive an interrupted event and a recovery timestamp as end marker; their actual last moment is not recoverable. No schema migration layer beyond additive create-if-missing exists yet.

The independent transparent desktop pet is visible on launch with the camera off. It stays visible while the dashboard is minimized. Right-click opens the dashboard, pauses/resumes, takes a break, stops or hides the pet. Its idle form has no rectangular caption panel. The cave and goblin are the visible silhouette; transparency surrounds them. Stop hides the pet as part of the panic action, and Show cave brings it back without reopening capture.

Changing session mode loads editable delay presets: Study 4/8 seconds, Work 5/10, Deep focus 3/6, Light monitoring 8/16 (warning/reaction). Saving applies the edited values.

## Feature breakdown

Capture/vision, calibrated inference, rule events, stateful animation, local analytics, preferences, privacy controls and packaging are separate concerns. Five personalities share the animation engine while changing reaction/recovery copy. The original goblin and sloth are QPainter vector drawings, so the MVP has no sprite downloads or external image dependencies. The overlay stays inside its own transparent window and moves relative to the user's cave anchor. It draws only its own fake phone/impact effects.
