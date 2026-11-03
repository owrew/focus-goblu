"""Deterministic rules. No Qt, camera, disk or wall-clock dependency."""
from dataclasses import dataclass, asdict
import math


@dataclass
class Settings:
    camera: int = 0
    resolution: str = "1280x720"
    fps: int = 12
    warning_seconds: float = 4.0
    alert_seconds: float = 8.0
    recovery_seconds: float = 1.5
    cooldown_seconds: float = 20.0
    head_tolerance: float = 0.22
    gaze_tolerance: float = 0.20
    break_minutes: int = 30
    personality: str = "Angry Goblin"
    accent: str = "#40dfcf"
    overlay: bool = True
    pet: bool = True
    reduced_motion: bool = False
    fire: bool = True
    screen_fire: bool = True
    fire_edges: str = 'All edges'
    animation_fps: int = 30
    sound: bool = False
    volume: int = 35
    intensity: int = 2
    phone_model: str = ""
    phone_confidence: float = 0.25
    phone_enabled: bool = True
    phone_backend: str = 'Balanced YOLOX'
    phone_size: int = 416
    auto_light: bool = True
    camera_auto_exposure: bool = True
    face_brightness: int = 128
    dense_landmarks: bool = True
    goblin_name: str = 'Grumble'
    goblin_color: str = '#70d5ad'
    cursor_follow: bool = True
    poke_reaction: bool = True
    custom_sound: str = ''
    global_pause: bool = True
    pause_shortcut: str = 'Ctrl+Alt+P'
    startup: bool = False
    background: str = 'Waterfall'
    background_motion: bool = True
    glass_blur: bool = True
    session_name: str = 'My focus session'
    session_minutes: int = 25
    retention_days: int = 0
    paper_mode: bool = False
    mode: str = "Study"
    goal_minutes: int = 60
    style: str = "Aurora glass"
    baseline: tuple = (0.0, 0.0, 0.5, 0.5)
    calibrated: bool = False

    def validated(self):
        s = Settings(**asdict(self))
        s.fps = max(5, min(20, int(s.fps)))
        s.warning_seconds = max(1.0, float(s.warning_seconds))
        s.alert_seconds = max(s.warning_seconds + 1, float(s.alert_seconds))
        s.break_minutes = max(1, int(s.break_minutes))
        s.cooldown_seconds = max(1.0, float(s.cooldown_seconds))
        s.head_tolerance = max(.03, float(s.head_tolerance))
        s.gaze_tolerance = max(.03, float(s.gaze_tolerance))
        s.phone_confidence = max(.1, min(.95, float(s.phone_confidence)))
        s.animation_fps = max(15,min(60,int(s.animation_fps)))
        s.goal_minutes = max(1,int(s.goal_minutes))
        s.goblin_name = str(s.goblin_name).strip()[:32] or 'Grumble'
        s.session_minutes = max(1,min(480,int(s.session_minutes)))
        s.face_brightness = max(70,min(180,int(s.face_brightness)))
        s.phone_size = 608 if int(s.phone_size) >= 608 else 416
        if s.fire_edges not in ('All edges','Sides','Bottom'): s.fire_edges = 'All edges'
        if len(s.baseline) != 4 or not all(math.isfinite(float(v)) for v in s.baseline):
            s.baseline = (0., 0., .5, .5)
            s.calibrated = False
        return s


@dataclass
class Observation:
    face: bool = False
    yaw: float = 0.0
    pitch: float = 0.0
    gaze_x: float = .5
    gaze_y: float = .5
    eyes_open: bool = True
    phone: bool = False
    valid: bool = True
    phone_score: float = 0.
    light_level: float = 0.
    light_gain: float = 1.
    phone_status: str = 'off'


@dataclass
class Decision:
    state: str
    confidence: float
    reason: str
    alert: bool = False


class AttentionEngine:
    def __init__(self, settings=None):
        self.settings = (settings or Settings()).validated()
        self.reset()

    def reset(self):
        self.away = self.stable = self.focus = self.distracted = 0.0
        self.unknown = self.absent = self.streak = self.longest = 0.0
        self.active = self.since_break = 0.0
        self.alerts = self.distractions = self.phone_events = 0
        self.last_alert = -1e9
        self.quiet_until=0.
        self.state = "ready"
        self._phone = False
        self._episode = False

    def step(self, o: Observation, dt: float) -> Decision:
        # A stalled camera is unobserved time, never a multi-second focus credit.
        dt = max(0.0, min(float(dt), .5))
        self.active += dt
        self.since_break += dt
        s = self.settings
        if not o.valid or not s.calibrated:
            self.unknown += dt
            self.away = self.stable = self.streak = 0
            self.state = "unknown"
            return Decision(self.state, 0, "Calibrate first" if not s.calibrated else "Camera signal unavailable")
        if o.phone and not self._phone:
            self.phone_events += 1
        self._phone = o.phone
        if not o.face:
            self.absent += dt
            self.away = self.stable = self.streak = 0
            self._episode = False
            self.state = "absent"
            return Decision(self.state, 0, "No face · away from desk or face obscured")
        by, bp, gx, gy = s.baseline
        head = max(abs(o.yaw-by), abs(o.pitch-bp)) / s.head_tolerance
        gaze = max(abs(o.gaze_x-gx), abs(o.gaze_y-gy)) / s.gaze_tolerance
        if not o.eyes_open:
            gaze = 0.0
        downward = o.pitch-bp > s.head_tolerance * .65 or o.gaze_y-gy > s.gaze_tolerance
        away = head > 1 or (gaze > 1 and o.eyes_open)
        if s.paper_mode and downward and not o.phone:
            away = False
        confidence = max(0., min(1., 1 - .42*head - .23*gaze))
        if away:
            self.away += dt * (1.6 if o.phone and downward else 1)
            self.stable = self.streak = 0
            if self.away >= s.warning_seconds:
                if not self._episode:
                    self.distractions += 1
                    self._episode = True
                self.distracted += dt
            else:
                self.unknown += dt  # grace period is not measured focus
            state = "angry" if self.away >= s.alert_seconds else "warning" if self.away >= s.warning_seconds else "watching"
            reason = "Looking down + phone visible" if downward and o.phone else "Head / gaze outside calibrated range"
        else:
            self.stable += dt
            self.focus += dt
            self.streak += dt
            self.longest = max(self.longest, self.streak)
            if self.stable >= s.recovery_seconds:
                self.away = 0
                self._episode = False
                state = "focused"
            else:
                state = "calming" if self.away else "focused"
            reason = "Within calibrated screen range"
        alert = state == "angry" and self.active-self.last_alert >= s.cooldown_seconds and self.active>=self.quiet_until
        if alert:
            self.alerts += 1
            self.last_alert = self.active
        self.state = state
        return Decision(state, confidence, reason, alert)

    def break_due(self):
        return self.since_break >= self.settings.break_minutes * 60

    def take_break(self):
        self.since_break = 0
        self.away = self.stable = self.streak = 0
        self._episode = False

    def dismiss_alert(self):
        self.away = self.stable = self.streak = 0.
        self._episode = False
        self.last_alert = self.active
        self.quiet_until=self.active+30
        self.state = 'focused'

    def summary(self):
        return {k: getattr(self, k) for k in (
            "active", "focus", "distracted", "unknown", "absent", "longest", "alerts", "distractions", "phone_events")}
